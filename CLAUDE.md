# CLAUDE.md — Dashboard Instagram Neon Giant Moving

## Proyecto
Dashboard local de análisis de Instagram para @neongiantmoving.
Lee datos desde Zernio API, los cachea en SQLite local, y genera ideas de contenido con Claude Sonnet.

## Stack
- Python + Streamlit 1.39 (UI)
- SQLite (cache local en data.nosync/cache.db)
- Zernio API (datos de Instagram)
- Anthropic SDK 0.97 + httpx 0.28.1 (generación de ideas)

## Archivos clave
- `app.py` — UI principal (7 tabs)
- `refresh.py` — trae datos de Zernio y los guarda en SQLite
- `zernio_client.py` — cliente REST para Zernio con retry/backoff
- `cache.py` — read/write de SQLite (18 tablas)
- `ideas.py` — generación de ideas con Claude (prompt caching)
- `idea_filters.py` — filtros para comentarios/DMs triviales
- `prompts/ideas_system.md` — system prompt de ideas (NO modificar sin cuidado)

## Variables de entorno (.env)
- `ZERNIO_API_KEY` — API key de Zernio (sk_...)
- `ZERNIO_ACCOUNT_ID` — ID de cuenta Instagram en Zernio (6a04aaf75e333c05295ec629)
- `ZERNIO_ACCOUNT_ID_FACEBOOK` — ID de cuenta Facebook en Zernio (6a04b8785e333c05295fa955)
- `ANTHROPIC_API_KEY` — API key de Anthropic para generar ideas
- `DASHBOARD_TZ` — America/Los_Angeles

## Reglas importantes
- `load_dotenv(override=True)` en TODOS los archivos que usan env vars
- NO llamar endpoints de escritura de Zernio (posts_create, messages_send, etc)
- NO integrar TikTok
- El dashboard es solo lectura
- anthropic==0.97.0 + httpx==0.28.1 (versiones fijas, no actualizar sin probar)
- st.image usa `use_column_width=True` (Streamlit 1.39, no use_container_width)

## Correr
```
.venv\Scripts\streamlit run app.py
```

## Add-ons Zernio requeridos
- Analytics — métricas, demografía, best time, etc.
- Inbox — comentarios y DMs

Si ves [402] o [403], el usuario necesita activar el add-on en zernio.com.
