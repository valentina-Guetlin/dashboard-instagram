"""
Refresh all data from Zernio into the local SQLite cache.
Run: .venv/Scripts/python refresh.py
"""
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
load_dotenv(override=True)

import zernio_client as z
import cache


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def _refresh_platform(platform, account_id):
    log(f"\n=== {platform.upper()} (account: {account_id}) ===")

    # --- Account snapshot ---
    try:
        accounts = z.list_accounts(platform)
        acct = next((a for a in accounts.get("accounts", []) if a["_id"] == account_id), None)
        if acct:
            cache.upsert_account_snapshot(platform, acct)
            log(f"  Account: @{acct.get('username')} ({acct.get('followersCount')} followers)")
    except Exception as e:
        log(f"  Account snapshot failed: {e}")

    # --- Health ---
    try:
        health = z.get_account_health(account_id)
        cache.upsert_account_health(platform, health)
    except Exception as e:
        log(f"  Health failed: {e}")

    # --- Account insights (Instagram only) ---
    if platform == "instagram":
        try:
            insights = z.get_account_insights(account_id)
            cache.upsert_insights(platform, insights)
            log("  Insights saved")
        except Exception as e:
            log(f"  Insights failed: {e}")

    # --- Daily metrics ---
    try:
        metrics = z.get_daily_metrics(account_id, platform)
        # API returns {"dailyData": [...]} — each item has date + nested metrics{}
        days = (metrics.get("dailyData") or metrics.get("data") or
                metrics.get("metrics") or (metrics if isinstance(metrics, list) else []))
        for day in days:
            date_str = day.get("date", day.get("day", ""))
            if date_str:
                # Flatten nested metrics{} into the top-level row
                row = {k: v for k, v in day.items() if k != "metrics"}
                row.update(day.get("metrics", {}))
                cache.upsert_daily_metrics(date_str, platform, row)
        log(f"  {len(days)} days of metrics")
    except Exception as e:
        log(f"  Daily metrics failed: {e}")

    # --- Demographics (Instagram only for city; Facebook has age/gender/country) ---
    try:
        if platform == "instagram":
            demo = z.get_demographics(account_id)
            raw = demo if isinstance(demo, dict) else {}
            # API returns {"demographics": {"age": [{"dimension": "18-24", "value": N}, ...]}}
            demo_data = raw.get("demographics", raw)  # top-level OR nested under "demographics"
            for dim in ("age", "gender", "country", "city"):
                buckets = demo_data.get(dim, raw.get(dim, raw.get(f"{dim}Distribution", {})))
                if isinstance(buckets, list):
                    buckets = {
                        item.get("dimension", item.get("label", item.get("name", str(i)))): item.get("value", item.get("count", 0))
                        for i, item in enumerate(buckets)
                    }
                if buckets:
                    cache.upsert_demographics(dim, platform, buckets)
            log("  Demographics saved")
        elif platform == "facebook":
            log("  Demographics: skipped (no Facebook-specific endpoint yet)")
    except Exception as e:
        log(f"  Demographics failed: {e}")

    # --- Follower history (Instagram only) ---
    if platform == "instagram":
        try:
            hist = z.get_follower_history(account_id)
            entries = hist if isinstance(hist, list) else hist.get("data", [])
            for entry in entries:
                date_str = entry.get("date", "")
                followers = entry.get("followers", entry.get("count", 0))
                if date_str:
                    cache.upsert_follower_history(date_str, platform, followers)
            log(f"  {len(entries)} follower history entries")
        except Exception as e:
            log(f"  Follower history failed: {e}")

    # --- Best time to post ---
    try:
        best = z.get_best_time_to_post(account_id, platform)
        # API returns {"slots": [{day_of_week, hour, avg_engagement, post_count}]}
        entries = (best.get("slots") or best.get("data") or
                   (best if isinstance(best, list) else []))
        for entry in entries:
            dow = entry.get("day_of_week", entry.get("dayOfWeek", 0))
            hour = entry.get("hour", 0)
            score = entry.get("avg_engagement", entry.get("score", entry.get("engagementRate", 0)))
            cache.upsert_best_time(dow, hour, platform, score)
        log(f"  {len(entries)} best-time slots")
    except Exception as e:
        log(f"  Best time failed: {e}")

    # --- Posting frequency ---
    try:
        freq = z.get_posting_frequency(account_id, platform)
        # API returns {"frequency": [{posts_per_week, avg_engagement_rate, avg_engagement}]}
        entries = (freq.get("frequency") or freq.get("data") or
                   (freq if isinstance(freq, list) else []))
        for entry in entries:
            ppw = entry.get("posts_per_week", entry.get("postsPerWeek", 0))
            cache.upsert_posting_frequency(ppw, platform, entry)
        log(f"  {len(entries)} frequency entries")
    except Exception as e:
        log(f"  Posting frequency failed: {e}")

    # --- Content decay ---
    try:
        decay = z.get_content_decay(account_id, platform)
        entries = decay if isinstance(decay, list) else decay.get("data", [])
        for i, entry in enumerate(entries):
            cache.upsert_content_decay(i, platform, entry)
        log(f"  {len(entries)} decay entries")
    except Exception as e:
        log(f"  Content decay failed: {e}")

    # --- Inbox comments (posts + drilldown) ---
    try:
        inbox = z.list_inbox_comments(account_id, platform)
        posts_raw = inbox if isinstance(inbox, list) else inbox.get("data", inbox.get("posts", []))
        log(f"  {len(posts_raw)} posts with comments")
        for post in posts_raw:
            post_id = post.get("postId", post.get("id", post.get("_id", "")))
            if not post_id:
                continue
            cache.upsert_post(post_id, platform, post)
            try:
                detail = z.get_post_comments(post_id, account_id)
                comments_raw = detail if isinstance(detail, list) else detail.get("data", detail.get("comments", []))
                for c in comments_raw:
                    cid = c.get("id", c.get("_id", ""))
                    created = c.get("createdAt", c.get("created_at", ""))
                    if cid:
                        cache.upsert_comment(cid, post_id, platform, c, created)
            except Exception:
                pass
    except Exception as e:
        log(f"  Inbox comments failed: {e}")

    # --- DMs / conversations (Instagram only) ---
    if platform == "instagram":
        try:
            convs = z.list_conversations(account_id)
            conv_list = convs if isinstance(convs, list) else convs.get("data", convs.get("conversations", []))
            log(f"  {len(conv_list)} DM conversations")
            for conv in conv_list:
                cid = conv.get("id", conv.get("_id", ""))
                if not cid:
                    continue
                cache.upsert_conversation(cid, conv)
                try:
                    msgs = z.get_conversation_messages(cid, account_id)
                    msg_list = msgs if isinstance(msgs, list) else msgs.get("data", msgs.get("messages", []))
                    for m in msg_list:
                        mid = m.get("id", m.get("_id", ""))
                        created = m.get("createdAt", m.get("created_at", ""))
                        if mid:
                            cache.upsert_message(mid, cid, m, created)
                except Exception:
                    pass
        except Exception as e:
            log(f"  DMs failed: {e}")


def refresh():
    cache.init_db()
    started_at = datetime.now(timezone.utc).isoformat()
    error_msg = None

    try:
        ig_id = os.environ["ZERNIO_ACCOUNT_ID"]
        fb_id = os.environ.get("ZERNIO_ACCOUNT_ID_FACEBOOK", "")

        _refresh_platform("instagram", ig_id)

        if fb_id:
            _refresh_platform("facebook", fb_id)

        log("\nRefresh complete!")

    except Exception as e:
        error_msg = str(e)
        log(f"ERROR: {e}")
        raise

    finally:
        finished_at = datetime.now(timezone.utc).isoformat()
        status = "error" if error_msg else "ok"
        cache.log_refresh(started_at, finished_at, status, error_msg)


if __name__ == "__main__":
    refresh()
