"""
AI-powered comment reply suggestions for Neon Giant Moving.
Claude reads the comment, the post context, and past replies to suggest
a real, on-brand response in Vale's voice.
"""
import os
import time
import json

from dotenv import load_dotenv
load_dotenv(override=True)

import anthropic
import cache

SYSTEM_PROMPT = """Eres el asistente de Vale, dueña de Neon Giant Moving — una empresa de mudanzas en el noroeste del estado de Washington (condados Skagit, Whatcom, Snohomish y King). El slogan es "The moving company your realtor actually trusts."

Tu trabajo es redactar respuestas a comentarios de Instagram y Facebook que suenen exactamente como Vale: cálida, directa, profesional pero sin ser rígida, con personalidad. Neon Giant es una empresa de confianza con más de 1,000 mudanzas y cero atajos.

## Reglas de tono
- Escribe como habla Vale: natural, sin jerga corporativa
- Inglés americano casual (la audiencia es local, PNW)
- Cortas: 1-3 oraciones máximo
- Si el comentario es una pregunta, responde la pregunta
- Si el comentario es un elogio, agradece con calidez y añade algo real (no solo "gracias!")
- Si el comentario es una queja o problema, reconoce, muestra empatía, ofrece siguiente paso
- Si el comentario pide precio o disponibilidad, dirige al teléfono (360.588.4700) o a que manden DM
- NO uses emojis excesivos (1 máximo, solo si encaja)
- NO uses frases genéricas como "¡Gracias por tu comentario!" o "We appreciate your feedback"
- SÍ usa el nombre del comentador si está disponible

## Sobre el negocio
- Servicio: mudanzas residenciales y comerciales, junk removal
- Zonas: Skagit, Whatcom, Snohomish, King County (Washington State)
- Contacto: 360.588.4700 | DM en Instagram
- Realtors son socios clave — muchos clientes vienen referidos por agentes inmobiliarios
- El equipo es pequeño, de confianza, sin subcontratistas

## Formato de salida
Responde SOLO con el texto de la respuesta, sin comillas, sin explicaciones. Listo para copiar y pegar o enviar directamente."""


def _get_past_replies(limit=20):
    """Pull past owner replies from cached comments to learn voice."""
    conn = cache.get_conn()
    rows = conn.execute(
        "SELECT data FROM comments ORDER BY created_at DESC LIMIT 500"
    ).fetchall()
    conn.close()

    past = []
    for row in rows:
        try:
            d = json.loads(row["data"])
            replies = d.get("replies", d.get("ownerReplies", []))
            if isinstance(replies, list):
                for r in replies:
                    text = r.get("text") or r.get("content") or r.get("message", "")
                    if text and len(text) > 10:
                        past.append(text)
            # Also check if comment itself is from the owner
            owner_name = d.get("from", {}).get("name", "") if isinstance(d.get("from"), dict) else ""
            if d.get("isOwner") or d.get("fromOwner") or d.get("username") in ("neongiantmoving",) or owner_name in ("neongiantmoving", "Neon Giant Moving"):
                text = d.get("text") or d.get("content") or d.get("message", "")
                if text and len(text) > 10:
                    past.append(text)
        except Exception:
            pass
    return past[:limit]


def generate_reply(comment_text, post_caption="", commenter_name="", platform="instagram"):
    """
    Generate a suggested reply for a comment.
    Returns the reply text string.
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    past_replies = _get_past_replies(20)

    context_parts = []

    if past_replies:
        context_parts.append("## Ejemplos de respuestas anteriores de Vale (para aprender su voz)")
        for r in past_replies[:10]:
            context_parts.append(f'- "{r}"')

    if post_caption:
        context_parts.append(f"\n## Post al que responde este comentario\n{post_caption[:300]}")

    context_parts.append(f"\n## Comentario a responder")
    if commenter_name:
        context_parts.append(f"De: {commenter_name}")
    context_parts.append(f'"{comment_text}"')

    context_parts.append(f"\nPlataforma: {platform}")
    context_parts.append("\nRedacta UNA respuesta. Solo el texto, sin comillas ni explicaciones.")

    user_message = "\n".join(context_parts)

    for attempt in range(4):
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=200,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )
            return response.content[0].text.strip().strip('"').strip("'")
        except anthropic.APIStatusError as e:
            if e.status_code in (529, 500, 502, 503) and attempt < 3:
                time.sleep([2, 3, 5, 9][attempt])
                continue
            raise

    raise RuntimeError("Failed to generate reply after retries")


def generate_replies_for_post(post_id, platform="instagram"):
    """
    Generate suggested replies for all comments on a post.
    Returns dict: {comment_id: suggested_reply_text}
    """
    comments = cache.get_comments(post_id=post_id, platform=platform)

    # Get post caption for context
    posts = cache.get_posts(platform, 200)
    post = next((p for p in posts if p.get("id") == post_id), {})
    caption = post.get("caption", post.get("text", "")) or ""

    suggestions = {}
    for comment in comments:
        cid = comment.get("id", "")
        text = comment.get("text") or comment.get("content") or comment.get("message", "")
        author = comment.get("username") or (comment.get("from", {}) or {}).get("name", "") or comment.get("author", "")

        if not text or not cid:
            continue

        # Skip very short or obvious non-reply comments
        if len(text.strip()) < 3:
            continue

        try:
            suggestion = generate_reply(
                comment_text=text,
                post_caption=caption,
                commenter_name=author,
                platform=platform,
            )
            suggestions[cid] = suggestion
        except Exception as e:
            suggestions[cid] = f"[Error generating reply: {e}]"

    return suggestions
