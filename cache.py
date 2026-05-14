import sqlite3
import json
import os
from pathlib import Path

DB_PATH = Path(__file__).parent / "data.nosync" / "cache.db"


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS account_snapshot (
            platform TEXT PRIMARY KEY,
            data TEXT,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS account_health (
            platform TEXT PRIMARY KEY,
            data TEXT,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS account_insights_30d (
            platform TEXT PRIMARY KEY,
            data TEXT,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS daily_metrics (
            date TEXT,
            platform TEXT,
            data TEXT,
            PRIMARY KEY (date, platform)
        );

        CREATE TABLE IF NOT EXISTS demographics_age (
            bucket TEXT,
            platform TEXT,
            value REAL,
            updated_at TEXT,
            PRIMARY KEY (bucket, platform)
        );

        CREATE TABLE IF NOT EXISTS demographics_gender (
            bucket TEXT,
            platform TEXT,
            value REAL,
            updated_at TEXT,
            PRIMARY KEY (bucket, platform)
        );

        CREATE TABLE IF NOT EXISTS demographics_country (
            bucket TEXT,
            platform TEXT,
            value REAL,
            updated_at TEXT,
            PRIMARY KEY (bucket, platform)
        );

        CREATE TABLE IF NOT EXISTS demographics_city (
            bucket TEXT,
            platform TEXT,
            value REAL,
            updated_at TEXT,
            PRIMARY KEY (bucket, platform)
        );

        CREATE TABLE IF NOT EXISTS posts (
            id TEXT PRIMARY KEY,
            platform TEXT,
            data TEXT,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS comments (
            id TEXT PRIMARY KEY,
            post_id TEXT,
            platform TEXT,
            data TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            data TEXT,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT,
            data TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS best_time (
            day_of_week INTEGER,
            hour INTEGER,
            platform TEXT,
            score REAL,
            updated_at TEXT,
            PRIMARY KEY (day_of_week, hour, platform)
        );

        CREATE TABLE IF NOT EXISTS posting_frequency (
            posts_per_week REAL,
            platform TEXT,
            data TEXT,
            updated_at TEXT,
            PRIMARY KEY (posts_per_week, platform)
        );

        CREATE TABLE IF NOT EXISTS content_decay (
            bucket_order INTEGER,
            platform TEXT,
            data TEXT,
            updated_at TEXT,
            PRIMARY KEY (bucket_order, platform)
        );

        CREATE TABLE IF NOT EXISTS follower_history (
            date TEXT,
            platform TEXT,
            followers INTEGER,
            PRIMARY KEY (date, platform)
        );

        CREATE TABLE IF NOT EXISTS ideas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            generated_at TEXT,
            batch_id TEXT,
            source_bucket TEXT NOT NULL DEFAULT 'top_content',
            platforms TEXT,
            angle TEXT,
            format TEXT,
            rationale TEXT,
            basis_post_ids TEXT,
            basis_comment_ids TEXT,
            basis_message_ids TEXT,
            evidence_quotes TEXT,
            why_good_idea TEXT,
            suggested_angle TEXT,
            discarded INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS idea_discards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            idea_id INTEGER,
            angle TEXT,
            source_bucket TEXT,
            platform TEXT,
            discarded_at TEXT,
            reason_quick TEXT,
            reason_text TEXT
        );

        CREATE TABLE IF NOT EXISTS refresh_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT,
            finished_at TEXT,
            status TEXT,
            error TEXT
        );

        CREATE TABLE IF NOT EXISTS transcriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id TEXT,
            transcript TEXT,
            created_at TEXT
        );
    """)

    conn.commit()
    conn.close()


def _migrate_add_column(conn, table, column, col_type):
    c = conn.cursor()
    c.execute(f"PRAGMA table_info({table})")
    cols = [row["name"] for row in c.fetchall()]
    if column not in cols:
        c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")


# --- Writers ---

def upsert_meta(key, value):
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()


def get_meta(key):
    conn = get_conn()
    row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else None


def upsert_account_snapshot(platform, data):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO account_snapshot (platform, data, updated_at) VALUES (?,?,?)",
        (platform, json.dumps(data), now)
    )
    conn.commit()
    conn.close()


def get_account_snapshot(platform="instagram"):
    conn = get_conn()
    row = conn.execute("SELECT data FROM account_snapshot WHERE platform=?", (platform,)).fetchone()
    conn.close()
    return json.loads(row["data"]) if row else None


def upsert_account_health(platform, data):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO account_health (platform, data, updated_at) VALUES (?,?,?)",
        (platform, json.dumps(data), now)
    )
    conn.commit()
    conn.close()


def get_account_health(platform="instagram"):
    conn = get_conn()
    row = conn.execute("SELECT data FROM account_health WHERE platform=?", (platform,)).fetchone()
    conn.close()
    return json.loads(row["data"]) if row else None


def upsert_insights(platform, data):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO account_insights_30d (platform, data, updated_at) VALUES (?,?,?)",
        (platform, json.dumps(data), now)
    )
    conn.commit()
    conn.close()


def get_insights(platform="instagram"):
    conn = get_conn()
    row = conn.execute("SELECT data FROM account_insights_30d WHERE platform=?", (platform,)).fetchone()
    conn.close()
    return json.loads(row["data"]) if row else None


def upsert_daily_metrics(date_str, platform, data):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO daily_metrics (date, platform, data) VALUES (?,?,?)",
        (date_str, platform, json.dumps(data))
    )
    conn.commit()
    conn.close()


def get_daily_metrics(platform="instagram", days=90):
    conn = get_conn()
    rows = conn.execute(
        "SELECT date, data FROM daily_metrics WHERE platform=? ORDER BY date DESC LIMIT ?",
        (platform, days)
    ).fetchall()
    conn.close()
    return [{"date": r["date"], **json.loads(r["data"])} for r in rows]


def upsert_demographics(dim, platform, buckets):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    table = f"demographics_{dim}"
    conn = get_conn()
    conn.execute(f"DELETE FROM {table} WHERE platform=?", (platform,))
    for bucket, value in buckets.items():
        conn.execute(
            f"INSERT OR REPLACE INTO {table} (bucket, platform, value, updated_at) VALUES (?,?,?,?)",
            (bucket, platform, value, now)
        )
    conn.commit()
    conn.close()


def get_demographics(dim, platform="instagram"):
    table = f"demographics_{dim}"
    conn = get_conn()
    rows = conn.execute(
        f"SELECT bucket, value FROM {table} WHERE platform=? ORDER BY value DESC",
        (platform,)
    ).fetchall()
    conn.close()
    return {r["bucket"]: r["value"] for r in rows}


def upsert_post(post_id, platform, data):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO posts (id, platform, data, updated_at) VALUES (?,?,?,?)",
        (post_id, platform, json.dumps(data), now)
    )
    conn.commit()
    conn.close()


def get_posts(platform="instagram", limit=200):
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, data FROM posts WHERE platform=? ORDER BY updated_at DESC LIMIT ?",
        (platform, limit)
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = json.loads(r["data"])
        d["id"] = r["id"]
        result.append(d)
    return result


def upsert_comment(comment_id, post_id, platform, data, created_at=None):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO comments (id, post_id, platform, data, created_at) VALUES (?,?,?,?,?)",
        (comment_id, post_id, platform, json.dumps(data), created_at or "")
    )
    conn.commit()
    conn.close()


def get_comments(post_id=None, platform="instagram", days=90):
    from datetime import datetime, timezone, timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    conn = get_conn()
    # Include rows with empty created_at (Zernio doesn't always provide timestamps)
    if post_id:
        rows = conn.execute(
            "SELECT id, data FROM comments WHERE post_id=? AND platform=? AND (created_at>=? OR created_at='' OR created_at IS NULL)",
            (post_id, platform, cutoff)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, data FROM comments WHERE platform=? AND (created_at>=? OR created_at='' OR created_at IS NULL)",
            (platform, cutoff)
        ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = json.loads(r["data"])
        d["id"] = r["id"]
        # Normalize text field — Zernio uses "message"; older data may use "text"/"content"
        if not d.get("text") and not d.get("content"):
            d["text"] = d.get("message", "")
        result.append(d)
    return result


def upsert_conversation(conv_id, data):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO conversations (id, data, updated_at) VALUES (?,?,?)",
        (conv_id, json.dumps(data), now)
    )
    conn.commit()
    conn.close()


def upsert_message(msg_id, conv_id, data, created_at=None):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO messages (id, conversation_id, data, created_at) VALUES (?,?,?,?)",
        (msg_id, conv_id, json.dumps(data), created_at or "")
    )
    conn.commit()
    conn.close()


def get_messages(days=30):
    from datetime import datetime, timezone, timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, conversation_id, data FROM messages WHERE created_at>=? ORDER BY created_at DESC",
        (cutoff,)
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = json.loads(r["data"])
        d["id"] = r["id"]
        d["conversation_id"] = r["conversation_id"]
        result.append(d)
    return result


def upsert_best_time(day_of_week, hour, platform, score):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO best_time (day_of_week, hour, platform, score, updated_at) VALUES (?,?,?,?,?)",
        (day_of_week, hour, platform, score, now)
    )
    conn.commit()
    conn.close()


def get_best_time(platform="instagram"):
    conn = get_conn()
    rows = conn.execute(
        "SELECT day_of_week, hour, score FROM best_time WHERE platform=?",
        (platform,)
    ).fetchall()
    conn.close()
    return [{"day_of_week": r["day_of_week"], "hour": r["hour"], "score": r["score"]} for r in rows]


def upsert_posting_frequency(posts_per_week, platform, data):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO posting_frequency (posts_per_week, platform, data, updated_at) VALUES (?,?,?,?)",
        (posts_per_week, platform, json.dumps(data), now)
    )
    conn.commit()
    conn.close()


def get_posting_frequency(platform="instagram"):
    conn = get_conn()
    rows = conn.execute(
        "SELECT posts_per_week, data FROM posting_frequency WHERE platform=? ORDER BY posts_per_week",
        (platform,)
    ).fetchall()
    conn.close()
    return [{"posts_per_week": r["posts_per_week"], **json.loads(r["data"])} for r in rows]


def upsert_content_decay(bucket_order, platform, data):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO content_decay (bucket_order, platform, data, updated_at) VALUES (?,?,?,?)",
        (bucket_order, platform, json.dumps(data), now)
    )
    conn.commit()
    conn.close()


def upsert_follower_history(date_str, platform, followers):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO follower_history (date, platform, followers) VALUES (?,?,?)",
        (date_str, platform, followers)
    )
    conn.commit()
    conn.close()


def get_follower_history(platform="instagram", days=90):
    conn = get_conn()
    rows = conn.execute(
        "SELECT date, followers FROM follower_history WHERE platform=? ORDER BY date DESC LIMIT ?",
        (platform, days)
    ).fetchall()
    conn.close()
    return [{"date": r["date"], "followers": r["followers"]} for r in rows]


def log_refresh(started_at, finished_at, status, error=None):
    conn = get_conn()
    conn.execute(
        "INSERT INTO refresh_log (started_at, finished_at, status, error) VALUES (?,?,?,?)",
        (started_at, finished_at, status, error)
    )
    conn.commit()
    conn.close()


def get_last_refresh():
    conn = get_conn()
    row = conn.execute(
        "SELECT finished_at, status FROM refresh_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# --- Ideas ---

def save_ideas(ideas_list, batch_id):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    conn = get_conn()
    for idea in ideas_list:
        conn.execute("""
            INSERT INTO ideas (generated_at, batch_id, source_bucket, platforms, angle, format,
                rationale, basis_post_ids, basis_comment_ids, basis_message_ids,
                evidence_quotes, why_good_idea, suggested_angle, discarded)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,0)
        """, (
            now, batch_id,
            idea.get("source_bucket", "top_content"),
            json.dumps(idea.get("platforms", ["instagram"])),
            idea.get("angle", ""),
            idea.get("format", ""),
            idea.get("rationale", ""),
            json.dumps(idea.get("basis_post_ids", [])),
            json.dumps(idea.get("basis_comment_ids", [])),
            json.dumps(idea.get("basis_message_ids", [])),
            json.dumps(idea.get("evidence_quotes", [])),
            idea.get("why_good_idea", ""),
            idea.get("suggested_angle", ""),
        ))
    conn.commit()
    conn.close()


def get_active_ideas(platform="instagram", source_bucket=None):
    conn = get_conn()
    query = "SELECT * FROM ideas WHERE discarded=0 AND platforms LIKE ?"
    params = [f'%"{platform}"%']
    if source_bucket:
        query += " AND source_bucket=?"
        params.append(source_bucket)
    query += " ORDER BY generated_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        for field in ("platforms", "basis_post_ids", "basis_comment_ids", "basis_message_ids", "evidence_quotes"):
            if d.get(field):
                try:
                    d[field] = json.loads(d[field])
                except Exception:
                    pass
        result.append(d)
    return result


def discard_idea(idea_id, reason_quick, reason_text=""):
    from datetime import datetime, timezone
    conn = get_conn()
    row = conn.execute("SELECT angle, source_bucket, platforms FROM ideas WHERE id=?", (idea_id,)).fetchone()
    if not row:
        conn.close()
        return
    platforms = json.loads(row["platforms"] or '["instagram"]')
    platform = platforms[0] if platforms else "instagram"
    conn.execute("UPDATE ideas SET discarded=1 WHERE id=?", (idea_id,))
    conn.execute("""
        INSERT INTO idea_discards (idea_id, angle, source_bucket, platform, discarded_at, reason_quick, reason_text)
        VALUES (?,?,?,?,?,?,?)
    """, (
        idea_id, row["angle"], row["source_bucket"], platform,
        datetime.now(timezone.utc).isoformat(), reason_quick, reason_text
    ))
    conn.commit()
    conn.close()


def get_recent_discards(limit=50):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM idea_discards ORDER BY discarded_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
