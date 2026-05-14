"""
Sync Neon Giant's Notion Instagram Calendar into the local SQLite cache.
Database: 📱 Instagram Calendar — Neon Giant
ID: a57c77db-eab5-4aab-9ad3-208d0f5ae599

Setup: add NOTION_TOKEN to .env
  1. Go to https://www.notion.so/my-integrations
  2. Create a new integration → copy the Internal Integration Secret
  3. Open the Instagram Calendar database in Notion
  4. Click ··· → Connections → add your integration
  5. Paste token into .env as NOTION_TOKEN=secret_...
"""
import os
import json
from datetime import datetime, timezone

from dotenv import load_dotenv
load_dotenv(override=True)

NOTION_DB_ID = "a57c77dbeab54aab9ad3208d0f5ae599"

STATUS_ORDER = ["Idea", "Scripting", "Filming", "Editing", "Ready to Post", "Posted"]


def _get_client():
    token = os.environ.get("NOTION_TOKEN", "")
    if not token:
        raise RuntimeError(
            "NOTION_TOKEN not set. Add it to .env — see notion_sync.py for instructions."
        )
    from notion_client import Client
    return Client(auth=token)


def _extract_text(prop):
    if prop is None:
        return ""
    t = prop.get("type", "")
    if t == "title":
        return "".join(r["plain_text"] for r in prop.get("title", []))
    if t == "rich_text":
        return "".join(r["plain_text"] for r in prop.get("rich_text", []))
    if t == "select":
        sel = prop.get("select")
        return sel["name"] if sel else ""
    if t == "date":
        d = prop.get("date")
        if d:
            return d.get("start", "")
    return ""


def _page_to_row(page):
    props = page.get("properties", {})
    return {
        "notion_id": page["id"].replace("-", ""),
        "url": page.get("url", ""),
        "title": _extract_text(props.get("Post Title")),
        "status": _extract_text(props.get("Status")),
        "format": _extract_text(props.get("Format")),
        "content_pillar": _extract_text(props.get("Content Pillar")),
        "publish_date": _extract_text(props.get("Publish Date")),
        "hook": _extract_text(props.get("Hook")),
        "caption_notes": _extract_text(props.get("Caption Notes")),
        "cta": _extract_text(props.get("CTA")),
        "collab": _extract_text(props.get("Collab / Feature")),
        "synced_at": datetime.now(timezone.utc).isoformat(),
    }


def _ensure_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notion_calendar (
            notion_id   TEXT PRIMARY KEY,
            url         TEXT,
            title       TEXT,
            status      TEXT,
            format      TEXT,
            content_pillar TEXT,
            publish_date TEXT,
            hook        TEXT,
            caption_notes TEXT,
            cta         TEXT,
            collab      TEXT,
            synced_at   TEXT
        )
    """)
    conn.commit()


def sync():
    """Pull all pages from the Notion calendar into the local cache."""
    import cache
    client = _get_client()

    all_pages = []
    cursor = None
    while True:
        kwargs = {"database_id": NOTION_DB_ID, "page_size": 100}
        if cursor:
            kwargs["start_cursor"] = cursor
        resp = client.databases.query(**kwargs)
        all_pages.extend(resp.get("results", []))
        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")

    conn = cache.get_conn()
    _ensure_table(conn)
    for page in all_pages:
        row = _page_to_row(page)
        conn.execute("""
            INSERT INTO notion_calendar (
                notion_id, url, title, status, format, content_pillar,
                publish_date, hook, caption_notes, cta, collab, synced_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(notion_id) DO UPDATE SET
                url=excluded.url,
                title=excluded.title,
                status=excluded.status,
                format=excluded.format,
                content_pillar=excluded.content_pillar,
                publish_date=excluded.publish_date,
                hook=excluded.hook,
                caption_notes=excluded.caption_notes,
                cta=excluded.cta,
                collab=excluded.collab,
                synced_at=excluded.synced_at
        """, (
            row["notion_id"], row["url"], row["title"], row["status"],
            row["format"], row["content_pillar"], row["publish_date"],
            row["hook"], row["caption_notes"], row["cta"],
            row["collab"], row["synced_at"],
        ))
    conn.commit()
    conn.close()
    return len(all_pages)


def get_calendar_items(status_filter=None):
    """
    Return calendar rows from local cache.
    status_filter: list of statuses to include, e.g. ["Idea", "Scripting"]
                   None = all statuses
    """
    import cache
    conn = cache.get_conn()
    try:
        _ensure_table(conn)
        if status_filter:
            placeholders = ",".join("?" * len(status_filter))
            rows = conn.execute(
                f"SELECT * FROM notion_calendar WHERE status IN ({placeholders}) ORDER BY publish_date ASC, title ASC",
                status_filter,
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM notion_calendar ORDER BY publish_date ASC, title ASC"
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []
    finally:
        conn.close()


def is_configured():
    return bool(os.environ.get("NOTION_TOKEN", "").strip())
