import time
import requests
from dotenv import load_dotenv
import os

load_dotenv(override=True)

BASE_URL = "https://api.zernio.com/v1"
RETRY_DELAYS = [2, 3, 5, 9]


def _headers():
    return {"Authorization": f"Bearer {os.environ['ZERNIO_API_KEY']}"}


def _get(path, params=None):
    url = f"{BASE_URL}{path}"
    for attempt, delay in enumerate(RETRY_DELAYS + [None]):
        try:
            r = requests.get(url, headers=_headers(), params=params, timeout=30)
            if r.status_code in (429, 500, 502, 503, 504) and delay is not None:
                time.sleep(delay)
                continue
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            if delay is None:
                raise
            time.sleep(delay)
    raise RuntimeError(f"Failed after retries: {path}")


def _account_id():
    return os.environ["ZERNIO_ACCOUNT_ID"]


# --- Cross-platform ---

def list_accounts(platform="instagram"):
    return _get("/accounts", {"platform": platform})


def get_account_health(account_id=None):
    aid = account_id or _account_id()
    return _get(f"/accounts/{aid}/health")


def get_daily_metrics(account_id=None, platform="instagram"):
    aid = account_id or _account_id()
    return _get("/analytics/daily-metrics", {"accountId": aid, "platform": platform})


def get_best_time_to_post(account_id=None, platform="instagram"):
    aid = account_id or _account_id()
    return _get("/analytics/best-time", {"accountId": aid, "platform": platform})


def get_posting_frequency(account_id=None, platform="instagram"):
    aid = account_id or _account_id()
    return _get("/analytics/posting-frequency", {"accountId": aid, "platform": platform})


def get_content_decay(account_id=None, platform="instagram"):
    aid = account_id or _account_id()
    return _get("/analytics/content-decay", {"accountId": aid, "platform": platform})


def list_inbox_comments(account_id=None, platform="instagram"):
    aid = account_id or _account_id()
    return _get("/inbox/comments", {"accountId": aid, "platform": platform})


def get_post_comments(post_id, account_id=None):
    aid = account_id or _account_id()
    return _get(f"/inbox/comments/{post_id}", {"accountId": aid})


def get_usage_stats(account_id=None):
    aid = account_id or _account_id()
    return _get("/usage-stats", {"accountId": aid})


# --- Instagram only ---

def get_account_insights(account_id=None):
    aid = account_id or _account_id()
    return _get("/analytics/instagram/account-insights", {"accountId": aid})


def get_demographics(account_id=None, platform="instagram"):
    aid = account_id or _account_id()
    if platform == "instagram":
        return _get("/analytics/instagram/demographics", {"accountId": aid})
    return {}  # Facebook demographics endpoint not yet supported by Zernio


def get_follower_history(account_id=None):
    aid = account_id or _account_id()
    return _get("/analytics/instagram/follower-history", {"accountId": aid})


def list_conversations(account_id=None):
    aid = account_id or _account_id()
    return _get("/inbox/conversations", {"accountId": aid})


def get_conversation_messages(conversation_id, account_id=None):
    aid = account_id or _account_id()
    return _get(f"/inbox/conversations/{conversation_id}/messages", {"accountId": aid})


# --- Write endpoints (explicit user action only) ---

def _post(path, payload=None, params=None):
    url = f"{BASE_URL}{path}"
    for attempt, delay in enumerate(RETRY_DELAYS + [None]):
        try:
            r = requests.post(url, headers=_headers(), json=payload, params=params, timeout=30)
            if r.status_code in (429, 500, 502, 503, 504) and delay is not None:
                time.sleep(delay)
                continue
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            if delay is None:
                raise
            time.sleep(delay)
    raise RuntimeError(f"Failed after retries: {path}")


def reply_to_comment(comment_id, text, account_id=None):
    """Send a reply to an Instagram or Facebook comment."""
    aid = account_id or _account_id()
    return _post(
        "/inbox/comments/reply",
        payload={"commentId": comment_id, "accountId": aid, "message": text},
    )
