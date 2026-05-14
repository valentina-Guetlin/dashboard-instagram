"""
Idea generation using Anthropic Claude with prompt caching.
"""
import json
import os
import re
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(override=True)

import anthropic
import cache
from idea_filters import filter_comments, filter_dms

_ID_PATTERN_LONG = re.compile(r"\b(post|comment|message)[\s_-]?id[:\s]*\d+\b", re.IGNORECASE)
_ID_PATTERN_LABELED = re.compile(r"\b(post|comment|message)\s+\d{10,}\b", re.IGNORECASE)
_ID_PATTERN_BARE = re.compile(r"\b\d{12,}\b")

SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "ideas_system.md").read_text(encoding="utf-8")


def _client():
    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def _strip_ids_from_text(text):
    text = _ID_PATTERN_LONG.sub(lambda m: m.group(1), text)
    text = _ID_PATTERN_LABELED.sub(lambda m: m.group(1), text)
    text = _ID_PATTERN_BARE.sub("", text)
    return text


def _build_notion_calendar_block():
    """Pull planned/posted content from Notion calendar to avoid duplicates."""
    try:
        import notion_sync
        items = notion_sync.get_calendar_items()
        if not items:
            return ""
        lines = ["## Content already planned or posted (do NOT duplicate these)"]
        for item in items:
            status = item.get("status", "")
            title = item.get("title", "")
            hook = item.get("hook", "")
            pillar = item.get("content_pillar", "")
            date = item.get("publish_date", "")
            summary = f"[{status}] {title}"
            if hook:
                summary += f" — Hook: \"{hook}\""
            if date:
                summary += f" ({date})"
            lines.append(f"- {summary}")
        return "\n".join(lines)
    except Exception:
        return ""


def _build_context_block(platform="instagram"):
    posts = cache.get_posts(platform, limit=50)
    posts_sorted = sorted(
        posts,
        key=lambda p: p.get("likeCount", p.get("likesCount", p.get("likes", 0))),
        reverse=True,
    )[:20]

    all_comments = cache.get_comments(platform=platform, days=90)
    filtered_comments = filter_comments(all_comments)[:200]

    demo_age = cache.get_demographics("age", platform)
    demo_gender = cache.get_demographics("gender", platform)
    demo_country = cache.get_demographics("country", platform)

    best_time = cache.get_best_time(platform)
    best_slots = sorted(best_time, key=lambda x: x["score"], reverse=True)[:5]

    lines = ["# ACCOUNT CONTEXT\n"]

    lines.append("## Top posts by engagement")
    for p in posts_sorted:
        caption = (p.get("content") or p.get("caption") or p.get("text") or "")[:200]
        likes = p.get("likeCount", p.get("likesCount", p.get("likes", 0)))
        comments_count = p.get("commentCount", p.get("commentsCount", p.get("comments", 0)))
        if caption:
            lines.append(f"- likes={likes} comments={comments_count} | {caption}")

    lines.append("\n## Recent substantive comments")
    for c in filtered_comments:
        cid = c.get("id", "")
        text = c.get("text", c.get("content", ""))
        post_id = c.get("postId", c.get("post_id", ""))
        lines.append(f"- [ID:{cid}][post:{post_id}] {text}")

    lines.append("\n## Audience demographics")
    if demo_age:
        lines.append(f"Age: {demo_age}")
    if demo_gender:
        lines.append(f"Gender: {demo_gender}")
    if demo_country:
        top_countries = dict(list(demo_country.items())[:5])
        lines.append(f"Top countries: {top_countries}")

    if best_slots:
        lines.append("\n## Best posting times")
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for s in best_slots:
            day_name = days[s["day_of_week"]] if s["day_of_week"] < 7 else str(s["day_of_week"])
            lines.append(f"- {day_name} {s['hour']}h (score: {s['score']:.2f})")

    if platform == "instagram":
        messages = cache.get_messages(days=30)
        filtered_msgs = filter_dms(messages)[:100]
        if filtered_msgs:
            lines.append("\n## Recent substantive DMs")
            for m in filtered_msgs:
                mid = m.get("id", "")
                text = m.get("text", m.get("content", ""))
                lines.append(f"- [ID:{mid}] {text}")

    # Notion calendar — what's already planned
    notion_block = _build_notion_calendar_block()
    if notion_block:
        lines.append(f"\n{notion_block}")

    return "\n".join(lines)


def _build_discards_block():
    discards = cache.get_recent_discards(50)
    if not discards:
        return ""
    lines = ["## Ideas que el usuario YA descartó previamente (NO repitas ni hagas variantes muy similares)"]
    for d in discards:
        reason = d.get("reason_quick", "")
        text = d.get("reason_text", "")
        reason_str = f"{reason}: {text}" if text else reason
        lines.append(f'- [{d.get("source_bucket")}] "{d.get("angle")}" — razón: {reason_str}')
    return "\n".join(lines)


def _call_claude(context_text, instruction, max_tokens=16000):
    client = _client()
    for attempt in range(4):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=max_tokens,
                system=SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": context_text,
                                "cache_control": {"type": "ephemeral"},
                            },
                            {
                                "type": "text",
                                "text": instruction,
                            },
                        ],
                    }
                ],
            )
            return response.content[0].text
        except anthropic.APIStatusError as e:
            if e.status_code in (529, 500, 502, 503) and attempt < 3:
                time.sleep([2, 3, 5, 9][attempt])
                continue
            raise


def _parse_ideas(raw_text):
    raw_text = raw_text.strip()
    # Strip markdown code fences if present
    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
    raw_text = re.sub(r"\s*```$", "", raw_text)
    # Find outermost JSON object
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start == -1 or end == -1:
        return []
    try:
        data = json.loads(raw_text[start:end + 1])
        ideas_list = data.get("ideas", [])
        for idea in ideas_list:
            for field in ("angle", "why_good_idea", "suggested_angle", "rationale"):
                if idea.get(field):
                    idea[field] = _strip_ids_from_text(idea[field])
        return ideas_list
    except json.JSONDecodeError:
        return []


def generate_all_ideas_ig():
    context = _build_context_block("instagram")
    discards = _build_discards_block()

    instruction = """Genera ideas de contenido para Instagram basadas en el contexto de arriba.

Distribución target:
- 10 ideas de `comments` (patrones en comentarios públicos)
- 5 ideas de `dms` (patrones en mensajes directos)
- 10 ideas de `top_content` (evoluciones del contenido con más engagement)

Recuerda: calidad sobre cantidad. Si no hay sustancia para un bucket, entrega menos.

"""
    if discards:
        instruction += discards

    instruction += "\n\nResponde SOLO con el JSON, sin texto adicional antes ni después."

    raw = _call_claude(context, instruction)
    ideas = _parse_ideas(raw)

    batch_id = str(uuid.uuid4())
    if ideas:
        cache.save_ideas(ideas, batch_id)
    return ideas


def generate_bucket(platform, bucket):
    context = _build_context_block(platform)
    discards = _build_discards_block()

    targets = {"comments": 10, "dms": 5, "top_content": 10}
    target = targets.get(bucket, 10)

    instruction = f"""Genera ideas de contenido para {platform} del bucket `{bucket}`.

Target: {target} ideas (entrega menos si no hay sustancia suficiente).

"""
    if discards:
        instruction += discards

    instruction += "\n\nResponde SOLO con el JSON, sin texto adicional antes ni después."

    raw = _call_claude(context, instruction)
    ideas = _parse_ideas(raw)

    batch_id = str(uuid.uuid4())
    if ideas:
        cache.save_ideas(ideas, batch_id)
    return ideas
