# Dashboard Instagram — Neon Giant Moving

Dashboard local de análisis de Instagram que corre en tu navegador.

## Requisitos
- Python 3.9+
- Cuenta Zernio con add-ons Analytics e Inbox activos
- API key de Anthropic (para generar ideas)

## Instalación (primera vez)

```
cd C:\Users\jeff\Projects\dashboard-instagram
.venv\Scripts\python -m pip install -r requirements.txt
```

## Correr el dashboard

```
.venv\Scripts\streamlit run app.py
```

Se abre en http://localhost:8501

## Refrescar datos

Desde el dashboard: botón **🔄 Refrescar datos** arriba a la derecha.

Desde terminal:
```
.venv\Scripts\python refresh.py
```

## Generar ideas

1. Abre el dashboard
2. Ve a la pestaña **💡 Ideas**
3. Click en **✨ Generar todas las ideas de Instagram**
4. Espera ~15-30 segundos

## Troubleshooting

| Error | Solución |
|-------|----------|
| `[401]` al refrescar | API key de Zernio expirada — genera nueva en zernio.com |
| `[402] Analytics add-on required` | Activa Analytics en Zernio |
| `[403] Inbox addon required` | Activa Inbox en Zernio |
| `ANTHROPIC_API_KEY` no encontrada | Verifica que `.env` tiene la key correcta |
| Dashboard no abre | El venv no se activó — usa la ruta completa `.venv\Scripts\streamlit` |
