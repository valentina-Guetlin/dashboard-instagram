"""
Dashboard local de análisis de Instagram + Facebook - Neon Giant Moving
Run: .venv/Scripts/streamlit run app.py
"""
import os
import re
import json
from datetime import datetime, timezone

from dotenv import load_dotenv
load_dotenv(override=True)

import streamlit as st

# On Streamlit Cloud there's no .env — pull secrets into os.environ instead
try:
    for _k, _v in st.secrets.items():
        if isinstance(_v, str) and _k not in os.environ:
            os.environ[_k] = _v
except Exception:
    pass
import plotly.graph_objects as go
import plotly.express as px

import cache
import ideas as idea_engine
import replies as reply_engine
import zernio_client as z_client
import notion_sync

st.set_page_config(
    page_title="Neon Giant · Social Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

cache.init_db()

_ID_PATTERN_BARE = re.compile(r"\b\d{12,}\b")

DISCARD_REASONS = [
    "Already covered",
    "Not interested",
    "Too basic",
    "Not my style",
    "Other",
]

PLATFORM_COLORS = {
    "instagram": "#e33b93",
    "facebook": "#22aee4",
}

LOGO_PATH = r"C:\Users\jeff\OneDrive - BackBreakers PNW\Neon Giant\Logo Designs\Tina's Neon Giant Logos\HorizontalLogo\RGB\NeonGiant_HorizontalLogo-NoGlow-NoBckgrd_RGB.png"


def _inject_brand_css():
    # Background image (aurora) — load if file exists, else fallback to solid dark
    import base64, pathlib
    _bg_path = pathlib.Path(__file__).parent / "assets" / "background.png"
    if _bg_path.exists():
        _bg_b64 = base64.b64encode(_bg_path.read_bytes()).decode()
        st.markdown(
            "<style>"
            ".stApp {"
            f'background-image: url("data:image/png;base64,{_bg_b64}");'
            "background-size: cover;"
            "background-position: center top;"
            "background-attachment: fixed;"
            "background-repeat: no-repeat;"
            "color: #f0f0f0;"
            "}"
            ".stApp::before {"
            'content: "";'
            "position: fixed;"
            "inset: 0;"
            "background: rgba(0,0,0,0.62);"
            "pointer-events: none;"
            "z-index: 0;"
            "}"
            ".main .block-container, section[data-testid='stSidebar'] > div:first-child {"
            "position: relative; z-index: 1;"
            "}"
            "</style>",
            unsafe_allow_html=True,
        )

    st.markdown("""
    <style>
    /* ══ Neon Giant Brand Theme ══════════════════════════════════════════════ */

    .stApp { background-color: #0d0d0d; color: #f0f0f0; }

    .main .block-container {
        background-color: transparent;
        padding-top: 0.5rem;
        max-width: 1400px;
    }

    /* Top bar */
    header[data-testid="stHeader"] {
        background-color: #0d0d0d;
        border-bottom: 2px solid #e33b93;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #111111;
        border-right: 1px solid #222;
    }

    /* Headings */
    h1, h2, h3, h4, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #f0f0f0 !important;
    }

    /* Brand banner */
    .ng-banner {
        background: linear-gradient(135deg, #0d0d0d 0%, #1a0a12 100%);
        border-bottom: 2px solid #e33b93;
        padding: 0.75rem 1rem;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 1rem;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #111111;
        border-bottom: 2px solid #e33b93;
        gap: 2px;
        padding: 0 0.5rem;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        color: #888;
        border: none;
        border-radius: 4px 4px 0 0;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.15s;
    }

    .stTabs [data-baseweb="tab"]:hover {
        color: #e33b93;
        background-color: #1a1a1a;
    }

    .stTabs [aria-selected="true"] {
        background-color: #e33b93 !important;
        color: #fff !important;
    }

    .stTabs [data-baseweb="tab-panel"] {
        background-color: transparent;
        padding-top: 1rem;
    }

    /* Metric cards */
    [data-testid="metric-container"] {
        background-color: #161616 !important;
        border: 1px solid #2a2a2a;
        border-left: 3px solid #e33b93;
        border-radius: 8px;
        padding: 0.75rem 1rem !important;
    }

    [data-testid="stMetricValue"] {
        color: #e33b93 !important;
        font-size: 1.6rem !important;
        font-weight: 700 !important;
    }

    [data-testid="stMetricLabel"] {
        color: #aaa !important;
        font-size: 0.78rem !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Buttons */
    .stButton > button {
        background-color: #e33b93 !important;
        color: #fff !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        transition: all 0.2s !important;
    }

    .stButton > button:hover {
        background-color: #c0306e !important;
        box-shadow: 0 4px 14px rgba(227, 59, 147, 0.45) !important;
        transform: translateY(-1px);
    }

    .stButton > button:active { transform: translateY(0); }

    /* Form submit buttons — secondary style */
    .stFormSubmitButton > button {
        background-color: #22aee4 !important;
        color: #fff !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
    }

    .stFormSubmitButton > button:hover {
        background-color: #1a8fbf !important;
        box-shadow: 0 4px 14px rgba(34, 174, 228, 0.4) !important;
    }

    /* Text inputs */
    .stTextInput input, .stTextArea textarea {
        background-color: #1a1a1a !important;
        border: 1px solid #333 !important;
        color: #f0f0f0 !important;
        border-radius: 6px !important;
    }

    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #e33b93 !important;
        box-shadow: 0 0 0 2px rgba(227, 59, 147, 0.2) !important;
    }

    /* Selectbox */
    .stSelectbox [data-baseweb="select"] > div,
    .stSelectbox [data-baseweb="select"] > div:hover {
        background-color: #1a1a1a !important;
        border-color: #333 !important;
        color: #f0f0f0 !important;
    }

    /* Radio */
    .stRadio label { color: #bbb !important; }
    .stRadio [data-baseweb="radio"]:has(input:checked) label { color: #e33b93 !important; }

    /* Dividers */
    hr { border-color: #222 !important; }

    /* Expanders */
    details > summary {
        background-color: #161616 !important;
        border: 1px solid #2a2a2a !important;
        border-radius: 6px !important;
        color: #f0f0f0 !important;
        padding: 0.5rem 0.75rem !important;
    }

    details[open] > summary { border-radius: 6px 6px 0 0 !important; }

    details > div {
        background-color: #111111 !important;
        border: 1px solid #2a2a2a !important;
        border-top: none !important;
        border-radius: 0 0 6px 6px !important;
        padding: 0.75rem !important;
    }

    /* Caption */
    .stCaption, small, caption { color: #777 !important; }

    /* Alert boxes */
    [data-baseweb="notification"] {
        background-color: #161616 !important;
        border-radius: 6px !important;
    }

    /* Spinner */
    [data-testid="stSpinner"] > div {
        border-top-color: #e33b93 !important;
    }

    /* Profile image — square for thumbnails, round for avatars */
    [data-testid="stImage"] img { border-radius: 6px; }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #111; }
    ::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #e33b93; }
    </style>
    """, unsafe_allow_html=True)

PLATFORM_LABELS = {
    "instagram": "📸 Instagram",
    "facebook": "👍 Facebook",
}

NOTION_DB_ID = "5e7597b6-0745-48a8-b009-96cfc21fb728"  # Instagram Calendar — Neon Giant

HAS_FACEBOOK = bool(os.environ.get("ZERNIO_ACCOUNT_ID_FACEBOOK", ""))


def _strip_ids(text):
    if not text:
        return text
    return _ID_PATTERN_BARE.sub("", str(text))


def _fmt_num(n):
    if n is None:
        return "—"
    try:
        n = float(n)
        if n >= 1_000_000:
            return f"{n/1_000_000:.1f}M"
        if n >= 1_000:
            return f"{n/1_000:.1f}K"
        return str(int(n))
    except Exception:
        return str(n)


def _selected_platforms():
    """Return list of platforms based on sidebar selector."""
    sel = st.session_state.get("platform_select", "Both" if HAS_FACEBOOK else "Instagram")
    if sel in ("Instagram",):
        return ["instagram"]
    if sel in ("Facebook",):
        return ["facebook"]
    return ["instagram", "facebook"] if HAS_FACEBOOK else ["instagram"]


# ─── Header ─────────────────────────────────────────────────────────────────

_PLOTLY_DARK = dict(
    paper_bgcolor="#111111",
    plot_bgcolor="#161616",
    font_color="#f0f0f0",
    xaxis=dict(gridcolor="#222", zerolinecolor="#333"),
    yaxis=dict(gridcolor="#222", zerolinecolor="#333"),
)


def render_header():
    # Brand logo bar
    logo_col, title_col = st.columns([1, 6])
    with logo_col:
        try:
            st.image(LOGO_PATH, width=180)
        except Exception:
            st.markdown("**Neon Giant**")
    with title_col:
        st.markdown(
            '<p style="color:#888;font-size:0.85rem;margin:0;padding-top:0.5rem;">'
            'The moving company your realtor actually trusts &nbsp;·&nbsp; Social Dashboard</p>',
            unsafe_allow_html=True,
        )

    st.markdown(
        '<hr style="border:none;border-top:2px solid #e33b93;margin:0.5rem 0 0.75rem 0;">',
        unsafe_allow_html=True,
    )

    platforms_to_show = ["instagram", "facebook"] if HAS_FACEBOOK else ["instagram"]
    num_acct_cols = len(platforms_to_show)
    all_cols = st.columns([2] * num_acct_cols + [3, 2])
    acct_cols = all_cols[:num_acct_cols]
    col_status = all_cols[num_acct_cols]
    col_buttons = all_cols[num_acct_cols + 1]

    for col, platform in zip(acct_cols, platforms_to_show):
        snap = cache.get_account_snapshot(platform)
        accent = PLATFORM_COLORS[platform]
        with col:
            if snap:
                pic = snap.get("profilePicture", "")
                username = snap.get("username", "neongiantmoving")
                followers = snap.get("followersCount", "")
                display = snap.get("displayName", username)
                label = "📸" if platform == "instagram" else "👍"
                pic_col, info_col = st.columns([1, 3])
                with pic_col:
                    if pic:
                        st.image(pic, width=52, use_column_width=False)
                with info_col:
                    st.markdown(
                        f'<span style="color:{accent};font-weight:700;">{label} {display}</span>',
                        unsafe_allow_html=True,
                    )
                    if followers:
                        st.caption(f"@{username} · **{_fmt_num(followers)}** followers")
                    else:
                        st.caption(f"@{username}")
            else:
                label = "📸 Instagram" if platform == "instagram" else "👍 Facebook"
                st.markdown(f'<span style="color:{accent};font-weight:700;">{label}</span>', unsafe_allow_html=True)
                st.caption("No data yet")

    with col_status:
        last = cache.get_last_refresh()
        if last:
            ts = last.get("finished_at", "")
            status = last.get("status", "")
            dot = "🟢" if status == "ok" else "🔴"
            st.markdown(f"{dot} **Last updated**")
            try:
                dt = datetime.fromisoformat(ts).strftime("%m/%d/%Y %H:%M")
                st.caption(dt)
            except Exception:
                st.caption(ts)
        else:
            st.markdown("⚪ **No data yet**")
            st.caption("Click Refresh to start")

    with col_buttons:
        if st.button("🔄 Refresh data", use_container_width=True):
            with st.spinner("Refreshing..."):
                try:
                    import refresh as r
                    r.refresh()
                    st.success("Data updated!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # Platform selector
    if HAS_FACEBOOK:
        options = ["Instagram", "Facebook", "Both"]
        default = "Both"
    else:
        options = ["Instagram"]
        default = "Instagram"

    st.radio(
        "Platform",
        options=options,
        index=options.index(st.session_state.get("platform_select", default)),
        key="platform_select",
        horizontal=True,
        label_visibility="collapsed",
    )

    st.markdown('<hr style="border:none;border-top:1px solid #222;margin:0.5rem 0;">', unsafe_allow_html=True)


# ─── Tab 1: Resumen ──────────────────────────────────────────────────────────

def _sum_daily(platform, keys, days=30):
    """Sum numeric fields from daily_metrics over the last N days."""
    daily = cache.get_daily_metrics(platform, days)
    totals = {k: 0 for k in keys}
    for row in daily:
        for k in keys:
            try:
                totals[k] += float(row.get(k) or 0)
            except (TypeError, ValueError):
                pass
    return totals


def render_resumen():
    st.subheader("Summary — last 30 days")
    platforms = _selected_platforms()

    for platform in platforms:
        if len(platforms) > 1:
            st.markdown(
                f'<h4 style="color:{PLATFORM_COLORS[platform]};margin-top:1rem;">'
                f'{PLATFORM_LABELS[platform]}</h4>',
                unsafe_allow_html=True,
            )

        insights = cache.get_insights(platform)
        snap = cache.get_account_snapshot(platform)
        daily_agg = _sum_daily(platform, ["reach", "impressions", "views", "likes",
                                          "comments", "shares", "clicks", "saves",
                                          "total_interactions", "accounts_engaged"])

        if not insights and not snap and not any(daily_agg.values()):
            st.info(f"No data for {platform}. Click Refresh.")
            continue

        raw = insights or {}
        nested = raw.get("metrics", {}) if isinstance(raw, dict) else {}

        def _val(key, fallback=0):
            # 1. nested insights format: metrics.key.total
            if key in nested and isinstance(nested[key], dict):
                v = nested[key].get("total")
                if v is not None:
                    return v
            # 2. flat insights
            flat = raw.get("data", raw.get("insights", raw)) if isinstance(raw, dict) else {}
            v = flat.get(key, flat.get(key.replace("_", "")))
            if v is not None:
                return v
            # 3. aggregated daily metrics
            return daily_agg.get(key, fallback)

        followers = (snap or {}).get("followersCount") or 0

        if platform == "instagram":
            metrics = [
                ("👥 Followers", _fmt_num(followers)),
                ("📣 Reach", _fmt_num(_val("reach"))),
                ("👁️ Views", _fmt_num(_val("views") or _val("impressions"))),
                ("🤝 Engaged Accounts", _fmt_num(_val("accounts_engaged") or _val("total_interactions"))),
                ("💥 Interactions", _fmt_num(_val("total_interactions"))),
                ("❤️ Likes", _fmt_num(_val("likes"))),
                ("💬 Comments", _fmt_num(_val("comments"))),
                ("↗️ Shares", _fmt_num(_val("shares"))),
            ]
        else:
            metrics = [
                ("👥 Followers", _fmt_num(followers) if followers else "—"),
                ("📣 Reach", _fmt_num(_val("reach"))),
                ("👁️ Impressions", _fmt_num(_val("impressions") or _val("views"))),
                ("❤️ Likes", _fmt_num(_val("likes"))),
                ("💬 Comments", _fmt_num(_val("comments"))),
                ("↗️ Shares", _fmt_num(_val("shares"))),
                ("💾 Saves", _fmt_num(_val("saves"))),
                ("🖱️ Clicks", _fmt_num(_val("clicks"))),
            ]

        cols = st.columns(4)
        for i, (label, value) in enumerate(metrics):
            with cols[i % 4]:
                st.metric(label=label, value=value)

        if len(platforms) > 1:
            st.markdown('<hr style="border:none;border-top:1px solid #1a1a1a;margin:1rem 0;">', unsafe_allow_html=True)


# ─── Tab 2: Trends ───────────────────────────────────────────────────────────

_METRIC_META = {
    "reach":        {"label": "Reach",        "emoji": "📣", "group": "audience"},
    "impressions":  {"label": "Impressions",   "emoji": "👁️",  "group": "audience"},
    "views":        {"label": "Views",         "emoji": "▶️",  "group": "audience"},
    "likes":        {"label": "Likes",         "emoji": "❤️",  "group": "engagement"},
    "comments":     {"label": "Comments",      "emoji": "💬", "group": "engagement"},
    "shares":       {"label": "Shares",        "emoji": "↗️",  "group": "engagement"},
    "saves":        {"label": "Saves",         "emoji": "💾", "group": "engagement"},
    "clicks":       {"label": "Clicks",        "emoji": "🖱️",  "group": "engagement"},
    "accounts_engaged": {"label": "Engaged Accounts", "emoji": "🤝", "group": "engagement"},
}


def _rolling_avg(values, window=7):
    """Simple rolling average, returns list same length as input."""
    out = []
    for i in range(len(values)):
        start = max(0, i - window + 1)
        chunk = [v for v in values[start:i+1] if v is not None]
        out.append(sum(chunk) / len(chunk) if chunk else 0)
    return out


def _wow_delta(values):
    """Week-over-week % change: last 7 days vs prior 7 days."""
    if len(values) < 14:
        return None
    recent = sum(v for v in values[-7:] if v)
    prior = sum(v for v in values[-14:-7] if v)
    if prior == 0:
        return None
    return (recent - prior) / prior * 100


def render_tendencia():
    st.subheader("Trends")
    platforms = _selected_platforms()

    # Collect all available metrics across platforms
    all_data = {}
    for platform in platforms:
        daily = cache.get_daily_metrics(platform, 90)
        if not daily:
            continue
        daily_sorted = sorted(daily, key=lambda x: x.get("date", ""))
        all_data[platform] = daily_sorted

    if not all_data:
        st.info("No trend data. Click Refresh.")
        return

    # Find which metrics have data
    available_metrics = set()
    for rows in all_data.values():
        for d in rows:
            available_metrics.update(
                k for k in d if k != "date" and isinstance(d[k], (int, float)) and d[k] > 0
            )
    known = [k for k in _METRIC_META if k in available_metrics]

    # Controls row
    col_m, col_days, col_avg = st.columns([4, 2, 2])
    with col_m:
        selected = st.multiselect(
            "Metrics to compare",
            options=known,
            default=known[:3] if known else [],
            format_func=lambda k: f"{_METRIC_META[k]['emoji']} {_METRIC_META[k]['label']}",
            key="trend_metrics",
        )
    with col_days:
        days_back = st.selectbox("Period", [30, 60, 90], index=1, key="trend_days")
    with col_avg:
        show_avg = st.checkbox("7-day rolling avg", value=True, key="trend_avg")

    if not selected:
        st.info("Select at least one metric above.")
        return

    # WoW summary cards
    summary_cols = st.columns(min(len(selected), 4))
    for i, metric in enumerate(selected[:4]):
        meta = _METRIC_META.get(metric, {})
        with summary_cols[i]:
            for platform in platforms:
                rows = all_data.get(platform, [])
                vals = [d.get(metric, 0) for d in rows]
                delta = _wow_delta(vals)
                total_recent = sum(vals[-7:]) if vals else 0
                delta_str = f"{delta:+.1f}% vs prior week" if delta is not None else "—"
                st.metric(
                    label=f"{meta.get('emoji','')} {meta.get('label', metric)} ({PLATFORM_LABELS[platform]})",
                    value=_fmt_num(total_recent),
                    delta=delta_str,
                )

    st.markdown("---")

    # One chart per metric
    for metric in selected:
        meta = _METRIC_META.get(metric, {})
        fig = go.Figure()

        for platform in platforms:
            rows = all_data.get(platform, [])
            if not rows:
                continue
            # Trim to selected period
            rows_trimmed = rows[-days_back:]
            dates = [d.get("date", "") for d in rows_trimmed]
            vals = [d.get(metric, 0) for d in rows_trimmed]
            color = PLATFORM_COLORS[platform]
            plabel = PLATFORM_LABELS[platform]

            fig.add_trace(go.Bar(
                x=dates, y=vals,
                name=plabel,
                marker_color=color,
                opacity=0.55,
                showlegend=True,
            ))

            if show_avg:
                avg = _rolling_avg(vals)
                fig.add_trace(go.Scatter(
                    x=dates, y=avg,
                    name=f"{plabel} 7d avg",
                    mode="lines",
                    line=dict(color=color, width=2),
                    showlegend=True,
                ))

        fig.update_layout(
            title=dict(
                text=f"{meta.get('emoji','')} {meta.get('label', metric)}",
                font=dict(size=15, color="#f0f0f0"),
            ),
            height=220,
            margin=dict(t=40, b=20, l=40, r=20),
            hovermode="x unified",
            barmode="group",
            legend=dict(orientation="h", yanchor="top", y=1.15, bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
            **_PLOTLY_DARK,
        )
        st.plotly_chart(fig, use_container_width=True)

    # Follower growth (Instagram only)
    if "instagram" in platforms:
        fh = cache.get_follower_history("instagram", days_back)
        if fh:
            fh_sorted = sorted(fh, key=lambda x: x.get("date", ""))[-days_back:]
            fig_f = go.Figure()
            fig_f.add_trace(go.Scatter(
                x=[f["date"] for f in fh_sorted],
                y=[f["followers"] for f in fh_sorted],
                mode="lines+markers",
                name="Followers",
                fill="tozeroy",
                line=dict(color=PLATFORM_COLORS["instagram"], width=2),
                fillcolor="rgba(227,59,147,0.1)",
            ))
            fig_f.update_layout(
                title=dict(text="📸 Follower growth", font=dict(size=15, color="#f0f0f0")),
                height=200, margin=dict(t=40, b=20, l=40, r=20),
                hovermode="x unified",
                **_PLOTLY_DARK,
            )
            st.plotly_chart(fig_f, use_container_width=True)


# ─── Tab 3: Audiencia ────────────────────────────────────────────────────────

def render_audiencia():
    st.subheader("Audience demographics")
    platforms = _selected_platforms()

    platform_tabs = st.tabs([PLATFORM_LABELS[p] for p in platforms])

    for ptab, platform in zip(platform_tabs, platforms):
        with ptab:
            all_dims = ["age", "gender", "country"]
            if platform == "instagram":
                all_dims.append("city")
            labels = {"age": "Age", "gender": "Gender", "country": "Countries", "city": "Cities"}

            # Only show tabs that have data
            dims_with_data = [(d, cache.get_demographics(d, platform)) for d in all_dims]
            dims_available = [(d, data) for d, data in dims_with_data if data]

            if not dims_available:
                st.info(
                    "No audience demographics available yet. Zernio requires the **Analytics** add-on. "
                    "Try Refresh — if still empty, enable the add-on at zernio.com."
                    + (" (Facebook demographics not supported by Zernio)" if platform == "facebook" else "")
                )
                continue

            dim_tabs = st.tabs([labels[d] for d, _ in dims_available])
            for dtab, (dim, data) in zip(dim_tabs, dims_available):
                with dtab:
                    if not data:
                        st.info(f"No {labels[dim].lower()} data.")
                        continue
                    df_data = {"Category": list(data.keys()), "Value": list(data.values())}
                    color = PLATFORM_COLORS[platform]
                    if dim in ("age", "gender"):
                        fig = px.bar(df_data, x="Category", y="Value",
                                     color_discrete_sequence=[color])
                    else:
                        fig = px.bar(df_data, x="Value", y="Category", orientation="h",
                                     color_discrete_sequence=[color])
                        fig.update_layout(yaxis=dict(autorange="reversed", gridcolor="#222"))
                    fig.update_layout(height=380, **_PLOTLY_DARK)
                    st.plotly_chart(fig, use_container_width=True)


# ─── Tab 4: Posts ────────────────────────────────────────────────────────────

def _render_comment_with_reply(comment, post_caption, platform, account_id):
    """Render a single comment with AI reply suggestion + send button."""
    cid = comment.get("id", "")
    text = comment.get("text") or comment.get("content") or comment.get("message", "") or ""
    author = comment.get("username") or comment.get("from", {}).get("name", "") or comment.get("author", "someone")

    st.markdown(f"**{author}**: {text}")

    suggest_key = f"suggestion_{cid}"
    sent_key = f"sent_{cid}"

    if st.session_state.get(sent_key):
        st.success("✅ Respuesta enviada")
        return

    col_btn, _ = st.columns([2, 4])
    with col_btn:
        if st.button("✨ Suggest reply", key=f"suggest_btn_{cid}", use_container_width=True):
            with st.spinner("Claude is drafting a reply..."):
                try:
                    suggestion = reply_engine.generate_reply(
                        comment_text=text,
                        post_caption=post_caption,
                        commenter_name=author,
                        platform=platform,
                    )
                    st.session_state[suggest_key] = suggestion
                except Exception as e:
                    st.error(f"Error: {e}")

    if suggest_key in st.session_state:
        with st.form(key=f"reply_form_{cid}"):
            reply_text = st.text_area(
                "Reply (edit before sending if needed)",
                value=st.session_state[suggest_key],
                height=80,
                key=f"reply_text_{cid}",
            )
            col_send, col_copy, col_cancel = st.columns([2, 2, 2])
            with col_send:
                send = st.form_submit_button("📤 Send reply", use_container_width=True)
            with col_copy:
                copy = st.form_submit_button("📋 Copy only", use_container_width=True)
            with col_cancel:
                cancel = st.form_submit_button("Cancel", use_container_width=True)

            if send and reply_text.strip():
                try:
                    z_client.reply_to_comment(cid, reply_text.strip(), account_id)
                    st.session_state[sent_key] = True
                    del st.session_state[suggest_key]
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not send: {e}. Copy the text and reply manually.")

            if copy:
                st.session_state[f"copied_{cid}"] = reply_text
                st.info("Text ready — copy it from the field above and paste it in Instagram/Facebook.")

            if cancel:
                del st.session_state[suggest_key]
                st.rerun()


def render_posts():
    st.subheader("Posts by performance")
    platforms = _selected_platforms()

    sort_by = st.selectbox("Sort by", ["likes", "comments", "reach", "views"], index=0)

    all_posts = []
    for platform in platforms:
        posts = cache.get_posts(platform, 100)
        for p in posts:
            p["_platform"] = platform
        all_posts.extend(posts)

    if not all_posts:
        st.info("No posts cached. Click Refresh.")
        return

    def _sort_key(p):
        for k in [sort_by, sort_by + "Count", sort_by.capitalize()]:
            if k in p and p[k] is not None:
                try:
                    return float(p[k])
                except Exception:
                    pass
        return 0

    sorted_posts = sorted(all_posts, key=_sort_key, reverse=True)

    ig_account_id = os.environ.get("ZERNIO_ACCOUNT_ID", "")
    fb_account_id = os.environ.get("ZERNIO_ACCOUNT_ID_FACEBOOK", "")

    for post in sorted_posts[:40]:
        pid = post.get("id", "")
        platform = post.get("_platform", "instagram")
        caption = post.get("content", post.get("caption", post.get("text", ""))) or ""
        likes = post.get("likeCount", post.get("likesCount", post.get("likes", 0))) or 0
        n_comments = post.get("commentCount", post.get("commentsCount", post.get("comments", 0))) or 0
        permalink = post.get("permalink", post.get("url", ""))
        thumbnail = post.get("picture", post.get("thumbnailUrl", post.get("thumbnail", post.get("mediaUrl", ""))))
        badge = "📸" if platform == "instagram" else "👍"
        account_id = ig_account_id if platform == "instagram" else fb_account_id

        with st.container():
            c1, c2, c3 = st.columns([1, 4, 1])
            with c1:
                if thumbnail:
                    st.image(thumbnail, width=80)
            with c2:
                st.markdown(f"{badge} **{caption[:120]}{'...' if len(caption) > 120 else ''}**")
                st.caption(f"❤️ {_fmt_num(likes)} · 💬 {_fmt_num(n_comments)}")
                if permalink:
                    st.markdown(f"[Ver post]({permalink})")
            with c3:
                if st.button("💬 Comments", key=f"comments_{platform}_{pid}"):
                    key = f"show_comments_{platform}_{pid}"
                    st.session_state[key] = not st.session_state.get(key, False)

            if st.session_state.get(f"show_comments_{platform}_{pid}", False):
                post_comments = cache.get_comments(post_id=pid, platform=platform)
                if post_comments:
                    st.caption(f"{len(post_comments)} comment(s) · Click '✨ Suggest reply' on any")
                    for comment in post_comments[:20]:
                        with st.container():
                            _render_comment_with_reply(comment, caption, platform, account_id)
                            st.markdown("---")
                else:
                    st.caption("No comments cached for this post.")

            st.divider()


# ─── Tab 5: Cuándo publicar ──────────────────────────────────────────────────

def render_cuando():
    st.subheader("Best time to post")
    platforms = _selected_platforms()

    days_long = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    days_short = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    hours = list(range(24))

    cols = st.columns(len(platforms))
    for col, platform in zip(cols, platforms):
        with col:
            best = cache.get_best_time(platform)
            accent = PLATFORM_COLORS[platform]
            st.markdown(
                f'<span style="color:{accent};font-weight:700;">{PLATFORM_LABELS[platform]}</span>',
                unsafe_allow_html=True,
            )
            if not best:
                st.info("No data. Click Refresh.")
                continue

            matrix = [[0.0] * 24 for _ in range(7)]
            for entry in best:
                dow = entry.get("day_of_week", 0)
                h = entry.get("hour", 0)
                score = entry.get("score", 0)
                if 0 <= dow < 7 and 0 <= h < 24:
                    matrix[dow][h] = score

            colorscale = [[0, "#0d0d0d"], [0.5, "#6a1a45"], [1.0, "#e33b93"]] if platform == "instagram" else [[0, "#0d0d0d"], [0.5, "#0d4a65"], [1.0, "#22aee4"]]
            fig = go.Figure(data=go.Heatmap(
                z=matrix,
                x=[f"{h}h" for h in hours],
                y=days_short,
                colorscale=colorscale,
                showscale=True,
                colorbar=dict(thickness=10, len=0.8, tickfont=dict(color="#888", size=10)),
                hovertemplate="<b>%{y} %{x}</b><br>Score: %{z:.1f}<extra></extra>",
            ))
            fig.update_layout(
                height=300, margin=dict(l=40, r=60, t=10, b=30),
                paper_bgcolor="#111111", plot_bgcolor="#111111",
                font_color="#f0f0f0",
                xaxis=dict(tickfont=dict(size=9)),
                yaxis=dict(tickfont=dict(size=10)),
            )
            st.plotly_chart(fig, use_container_width=True)

            # Top 5 best slots as a readable list
            slots_flat = []
            for entry in best:
                dow = entry.get("day_of_week", 0)
                h = entry.get("hour", 0)
                score = entry.get("score", 0)
                if score > 0 and 0 <= dow < 7:
                    am_pm = f"{h}:00" if h < 12 else (f"12:00pm" if h == 12 else f"{h-12}:00pm")
                    am_pm = f"{h}:00am" if h < 12 else am_pm
                    slots_flat.append((score, days_long[dow], h, am_pm))
            slots_flat.sort(reverse=True)

            if slots_flat:
                st.markdown(
                    f'<p style="font-size:0.8rem;color:{accent};font-weight:600;margin:0.25rem 0;">📌 Top slots</p>',
                    unsafe_allow_html=True,
                )
                for score, day, hour, label in slots_flat[:5]:
                    st.markdown(
                        f'<div style="padding:0.3rem 0.6rem;margin:0.2rem 0;background:#161616;'
                        f'border-left:3px solid {accent};border-radius:4px;font-size:0.85rem;">'
                        f'<strong>{day}</strong> a las <strong>{label}</strong>'
                        f'<span style="float:right;color:#666;font-size:0.75rem;">score {score:.0f}</span></div>',
                        unsafe_allow_html=True,
                    )


# ─── Tab 6: Frecuencia ───────────────────────────────────────────────────────

def render_frecuencia():
    st.subheader("Posting frequency vs engagement")
    platforms = _selected_platforms()

    fig = go.Figure()
    has_data = False

    for platform in platforms:
        freq = cache.get_posting_frequency(platform)
        if not freq:
            continue
        has_data = True
        x = [f.get("posts_per_week", 0) for f in freq]
        y = [f.get("avgEngagement", f.get("engagement", f.get("engagementRate", 0))) for f in freq]
        fig.add_trace(go.Scatter(
            x=x, y=y, mode="markers+lines",
            name=PLATFORM_LABELS[platform],
            marker=dict(size=10, color=PLATFORM_COLORS[platform]),
            line=dict(color=PLATFORM_COLORS[platform]),
        ))

    if not has_data:
        st.info("No frequency data. Click Refresh.")
        return

    fig.update_layout(
        xaxis_title="Posts per week",
        yaxis_title="Average engagement",
        height=400,
        **_PLOTLY_DARK,
    )
    st.plotly_chart(fig, use_container_width=True)


# ─── Tab 7: Ideas ────────────────────────────────────────────────────────────

def render_ideas():
    st.subheader("💡 Content ideas")

    platform_options = ["instagram"]
    if HAS_FACEBOOK:
        platform_options.append("facebook")

    platform = st.radio(
        "Platform",
        options=platform_options,
        format_func=lambda x: PLATFORM_LABELS[x],
        horizontal=True,
        key="ideas_platform",
    )

    col_btn, col_cost = st.columns([2, 3])
    with col_btn:
        label = f"✨ Generate {PLATFORM_LABELS[platform]} ideas"
        gen_all = st.button(label, use_container_width=True)
    with col_cost:
        st.caption("~$0.10–0.30 USD per full generation")

    if gen_all:
        with st.spinner("Claude is analyzing your content... (~15-30 seconds)"):
            try:
                generated = idea_engine.generate_all_ideas_ig() if platform == "instagram" else idea_engine.generate_all_ideas_ig()
                st.success(f"{len(generated)} ideas generated!")
                st.rerun()
            except Exception as e:
                st.error(f"Error generating ideas: {e}")

    buckets = [("comments", "💬 From comments"), ("top_content", "🏆 From top content")]
    if platform == "instagram":
        buckets.insert(1, ("dms", "📩 From DMs"))

    for bucket_key, bucket_label in buckets:
        bucket_ideas = cache.get_active_ideas(platform, bucket_key)
        with st.expander(f"{bucket_label} — {len(bucket_ideas)} active ideas", expanded=True):
            col_regen, _ = st.columns([2, 4])
            with col_regen:
                if st.button(f"🔄 Regenerate", key=f"regen_{platform}_{bucket_key}"):
                    with st.spinner("Regenerating..."):
                        try:
                            new_ideas = idea_engine.generate_bucket(platform, bucket_key)
                            st.success(f"{len(new_ideas)} new ideas!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

            if not bucket_ideas:
                st.caption("No ideas yet. Click Generate to get started.")
                continue

            for idea in bucket_ideas:
                _render_idea_card(idea)

    with st.expander("🗑️ Recently discarded", expanded=False):
        discards = cache.get_recent_discards(20)
        if not discards:
            st.caption("Nothing discarded yet.")
        for d in discards:
            st.markdown(f"- **{d.get('angle', '')}** — *{d.get('reason_quick', '')}*")
            if d.get("reason_text"):
                st.caption(f"  {d['reason_text']}")


def _render_idea_card(idea):
    idea_id = idea.get("id")
    angle = _strip_ids(idea.get("angle", "Untitled"))
    fmt = idea.get("format", "")
    evidence = idea.get("evidence_quotes") or []
    why = _strip_ids(idea.get("why_good_idea", ""))
    suggested = _strip_ids(idea.get("suggested_angle", ""))

    with st.container():
        st.markdown(f"#### {angle}")
        if fmt:
            st.caption(f"Format: {fmt}")

        if evidence:
            st.markdown("**Inspired by:**")
            for quote in (evidence if isinstance(evidence, list) else [evidence]):
                st.markdown(f"> *{quote}*")

        if why:
            st.markdown(f"**Why this works:** {why}")

        if suggested:
            st.markdown(f"**Suggested angle:** {suggested}")

        if st.button(f"✕ Discard", key=f"discard_btn_{idea_id}"):
            st.session_state[f"discard_modal_{idea_id}"] = True

        if st.session_state.get(f"discard_modal_{idea_id}"):
            with st.form(key=f"discard_form_{idea_id}"):
                st.markdown("**Why are you discarding this idea?**")
                reason = st.selectbox("Reason", DISCARD_REASONS, key=f"reason_sel_{idea_id}")
                reason_text = st.text_input("Details (optional)", key=f"reason_txt_{idea_id}")
                col_confirm, col_cancel = st.columns(2)
                with col_confirm:
                    confirm = st.form_submit_button("Discard")
                with col_cancel:
                    cancel = st.form_submit_button("Cancel")
                if confirm:
                    cache.discard_idea(idea_id, reason, reason_text)
                    st.session_state[f"discard_modal_{idea_id}"] = False
                    st.rerun()
                if cancel:
                    st.session_state[f"discard_modal_{idea_id}"] = False
                    st.rerun()

        st.divider()


# ─── Tab 8: Notion Calendar ───────────────────────────────────────────────────

_STATUS_COLORS = {
    "Idea": "#555",
    "Scripting": "#b8860b",
    "Filming": "#c05000",
    "Editing": "#6a0dad",
    "Ready to Post": "#22aee4",
    "Posted": "#2a9d4e",
}

_PILLAR_EMOJI = {
    "Brand Story": "📖",
    "Client Results": "⭐",
    "Education": "🎓",
    "Culture & Team": "🤝",
    "Realtor Content": "🏡",
    "Vale On Camera": "🎙️",
}


def render_notion():
    st.subheader("📅 Notion Content Calendar")

    col_sync, col_filter, _ = st.columns([2, 3, 3])
    with col_sync:
        if notion_sync.is_configured():
            if st.button("🔄 Sync Notion", use_container_width=True):
                with st.spinner("Syncing from Notion..."):
                    try:
                        n = notion_sync.sync()
                        st.success(f"Synced {n} items from Notion!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Sync error: {e}")
        else:
            st.caption("Add `NOTION_TOKEN` to `.env` to enable live sync")

    all_statuses = notion_sync.STATUS_ORDER
    with col_filter:
        selected_statuses = st.multiselect(
            "Filter by status",
            options=all_statuses,
            default=["Idea", "Scripting", "Filming", "Editing", "Ready to Post"],
            key="notion_status_filter",
        )

    items = notion_sync.get_calendar_items(status_filter=selected_statuses or None)

    if not items:
        st.info("No calendar items found.")
        return

    # Group by status
    from collections import defaultdict
    by_status = defaultdict(list)
    for item in items:
        by_status[item["status"]].append(item)

    for status in notion_sync.STATUS_ORDER:
        group = by_status.get(status, [])
        if not group:
            continue
        color = _STATUS_COLORS.get(status, "#888")
        label = f"<span style='background:{color};color:#fff;padding:2px 8px;border-radius:4px;font-size:0.8rem'>{status}</span>"
        with st.expander(f"{label} — {len(group)} item{'s' if len(group) != 1 else ''}", expanded=(status in ("Idea", "Scripting"))):
            for item in group:
                _render_notion_card(item)


def _render_notion_card(item):
    title = item.get("title") or "Untitled"
    fmt = item.get("format") or ""
    pillar = item.get("content_pillar") or ""
    publish_date = item.get("publish_date") or ""
    hook = item.get("hook") or ""
    caption = item.get("caption_notes") or ""
    cta = item.get("cta") or ""
    collab = item.get("collab") or ""
    url = item.get("url") or ""

    pillar_icon = _PILLAR_EMOJI.get(pillar, "")

    # Header row
    meta_parts = []
    if fmt:
        meta_parts.append(f"**{fmt}**")
    if pillar:
        meta_parts.append(f"{pillar_icon} {pillar}")
    if publish_date:
        meta_parts.append(f"📆 {publish_date}")
    if cta:
        meta_parts.append(f"CTA: *{cta}*")

    cols = st.columns([5, 1])
    with cols[0]:
        st.markdown(f"#### {title}")
        if meta_parts:
            st.caption(" · ".join(meta_parts))
        if hook:
            st.markdown(f"**Hook:** {hook}")
        if caption:
            st.markdown(f"**Caption notes:** {caption}")
        if collab:
            st.caption(f"Collab / Feature: {collab}")
    with cols[1]:
        if url:
            st.link_button("Open in Notion →", url)

    st.divider()


# ─── Tab 9: Competitors ───────────────────────────────────────────────────────

_COMPETITORS = [
    {
        "handle": "@roadwaymoving",
        "name": "Roadway Moving",
        "location": "New York, NY",
        "followers": "51K+",
        "why_winning": "Celebrity & influencer collabs (Julianne Hough, etc.) showing real moves. Authentic team footage. High production value with relatable hooks.",
        "top_content": "Celeb move reveals, time-lapses of full apartments cleared in under 1 hour, crew culture videos",
        "engagement_signal": "⭐⭐⭐⭐⭐ — Comments + saves on every reel",
        "steal_this": "Film a full-move time-lapse with a realtor client. Tag each other. Both audiences see it.",
        "url": "https://www.instagram.com/roadwaymoving/",
    },
    {
        "handle": "@luckymoving",
        "name": "Lucky Moving (formerly Pearson Moving)",
        "location": "Owner-led account",
        "followers": "Growing fast",
        "why_winning": "Owner-run account that posts raw, educational, direct-to-camera content. The Pearson playbook generated $60K in sales in 90 days from Instagram alone — same strategy under the new brand.",
        "top_content": "\"Why you should hire a moving company\" explainer reels, office day-in-the-life, moving tips",
        "engagement_signal": "⭐⭐⭐⭐⭐ — High comment rate, shares on tips",
        "steal_this": "Vale on camera doing the exact same format — owner explaining real decisions. Your voice is your competitive edge.",
        "url": "https://www.instagram.com/luckymoving/",
    },
    {
        "handle": "@jkmoving",
        "name": "JK Moving Services",
        "location": "Sterling, VA",
        "followers": "10K+",
        "why_winning": "Humor-forward content: what happens when you DON'T hire pros. Relatable fails that make people share with friends who are moving.",
        "top_content": "\"Things people do when they move themselves\" comedic reels, before/after damage prevention",
        "engagement_signal": "⭐⭐⭐⭐ — Very high share rate on funny content",
        "steal_this": "A reel showing what happens when someone ignores move-day prep tips — with a warm punchline at the end.",
        "url": "https://www.instagram.com/jkmoving/",
    },
    {
        "handle": "@twomenandatruck",
        "name": "Two Men and a Truck (National)",
        "location": "National franchise",
        "followers": "9.5K",
        "why_winning": "Consistent posting cadence, branded visuals, franchise-wide storytelling. Strong on testimonials and team culture.",
        "top_content": "Customer thank-you posts, team spotlights, move-day tips carousels",
        "engagement_signal": "⭐⭐⭐ — Steady but not viral-level",
        "steal_this": "Their team spotlight format is easy to replicate — introduce one crew member per week with 3 fun facts.",
        "url": "https://www.instagram.com/twomenandatruck/",
    },
    {
        "handle": "@cribmovers",
        "name": "Crib Movers",
        "location": "Multi-market",
        "followers": "Growing",
        "why_winning": "Simple formula: job footage + trending music + text overlay naming the move type. No talking. Repeated consistently = algorithm loves it.",
        "top_content": "Silent time-lapse reels with trending audio, move-type text callouts",
        "engagement_signal": "⭐⭐⭐⭐ — High reach from trending audio",
        "steal_this": "One reel per completed move. No editing needed — just film load-in, speed it up, add trending audio, text overlay: '3-bedroom Skagit Valley move. 4 hours.'",
        "url": "https://www.instagram.com/cribmovers/",
    },
    {
        "handle": "@dumbomoving",
        "name": "Dumbo Moving + Storage",
        "location": "New York, NY",
        "followers": "8K+",
        "why_winning": "Educational YouTube strategy that converts searchers. On Instagram they use carousels to answer specific moving questions from real customers.",
        "top_content": "FAQ carousels, moving cost breakdowns, \"what to ask your mover\" guides",
        "engagement_signal": "⭐⭐⭐⭐ — High saves on educational carousels",
        "steal_this": "A carousel titled '5 questions to ask before you pay a moving deposit' — highly shareable, positions you as the trusted expert.",
        "url": "https://www.instagram.com/dumbomoving/",
    },
    {
        "handle": "@goodgreekmoving",
        "name": "Good Greek Moving & Storage",
        "location": "Florida",
        "followers": "5K+",
        "why_winning": "Community involvement content (charity walks, local events) that drives comments and emotional shares. Makes the brand feel human.",
        "top_content": "Charity event coverage, community spotlights, behind-the-scenes of team culture",
        "engagement_signal": "⭐⭐⭐⭐ — Comments spike on community/human content",
        "steal_this": "Film Neon Giant at a local Skagit Valley community event — farmers market, fundraiser, anything. Community = comments.",
        "url": "https://www.instagram.com/goodgreekmoving/",
    },
    {
        "handle": "@luxurymovers",
        "name": "Luxury Movers",
        "location": "Multi-market",
        "followers": "Growing",
        "why_winning": "All job footage, all the time. Team laughing and working hard. Makes followers feel like they know the crew before hiring.",
        "top_content": "Crew having fun on the job, difficult move challenges shown with humor, wrap/pack technique videos",
        "engagement_signal": "⭐⭐⭐⭐ — Shares from people tagging friends who need movers",
        "steal_this": "Film Dane and the crew on a hard job — steep driveway, piano, 3rd floor no elevator. Show the challenge + the solution. The comment section writes itself.",
        "url": "https://www.instagram.com/luxurymovers/",
    },
    {
        "handle": "@collegehunkshaulingjunk",
        "name": "College Hunks Hauling Junk",
        "location": "National franchise",
        "followers": "20K+",
        "why_winning": "Junk removal before/after videos are inherently satisfying and go viral. Comment section full of people tagging friends to \"finally clean out the garage.\"",
        "top_content": "Before/after junk removal, donation drop-offs, extreme cleanouts",
        "engagement_signal": "⭐⭐⭐⭐⭐ — Viral save + share rate on satisfying before/afters",
        "steal_this": "Every junk removal job = one reel. Film the pile before, show the empty space after. That's it. People cannot stop watching these.",
        "url": "https://www.instagram.com/collegehunkshaulingjunk/",
    },
    {
        "handle": "@ecomoversmoving",
        "name": "Eco Movers Moving & Storage",
        "location": "Seattle, WA (King County)",
        "followers": "1.5K+ / 651 posts",
        "why_winning": "Most-reviewed mover in Washington state. Brand themselves as sustainable + stress-free. Active Reels presence, consistent posting cadence — more output than most local movers in the region.",
        "top_content": "Reels on move-day tips, sustainability angle, customer stories, team culture",
        "engagement_signal": "⭐⭐⭐⭐ — Active posting, Reels-first strategy, strong local brand",
        "steal_this": "They own the 'stress-free' positioning in Seattle. Neon Giant owns 'the one your realtor trusts' in Skagit/Whatcom — lean into that differentiation hard every time you post.",
        "url": "https://www.instagram.com/ecomoversmoving/",
    },
]

_WHAT_GOES_VIRAL = [
    ("🎬 Time-lapse full moves", "Full house load-in sped up to 60 seconds. Proves competence instantly. High share rate because people send to friends who are moving."),
    ("😂 Moving fails / humor", "What happens when you DON'T hire pros. Relatable content that makes people tag friends. Comments write themselves."),
    ("🔍 Educational carousels", "\"5 questions to ask before booking a mover\" — high save rate. People bookmark and share to friends planning moves."),
    ("⭐ Owner on camera", "Founder telling a real story, explaining a real decision. Most trusted format. High comment rate when it's genuine."),
    ("🏠 Before / after junk removal", "Algorithmically satisfying. Comment section full of tags. One per job = consistent content."),
    ("🤝 Collab with realtors", "Both audiences cross-pollinate. High trust signal. Realtor endorsement in video = instant credibility."),
    ("👷 Crew spotlights", "Introduce one team member. 3 fun facts. People follow because they feel like they know the crew."),
    ("😤 Challenging moves", "3rd floor, no elevator, 400-lb sectional. Showing the hard job and crushing it = massive comment engagement."),
]


def render_competitors():
    st.subheader("🔍 Competitor Intelligence")
    st.caption("10 moving companies doing well on Instagram — what's working and how to replicate it for Neon Giant.")

    st.markdown("---")
    st.markdown("### 🔥 What goes viral in the moving industry")

    cols = st.columns(2)
    for i, (title, desc) in enumerate(_WHAT_GOES_VIRAL):
        with cols[i % 2]:
            st.markdown(f"**{title}**")
            st.caption(desc)
            st.markdown("")

    st.markdown("---")
    st.markdown("### 📱 Accounts to watch & steal from")

    for comp in _COMPETITORS:
        with st.expander(f"{comp['handle']} — {comp['name']} · {comp['location']}", expanded=False):
            col_info, col_steal = st.columns([3, 2])
            with col_info:
                st.markdown(f"**Followers:** {comp['followers']}")
                st.markdown(f"**Engagement signal:** {comp['engagement_signal']}")
                st.markdown(f"**Why they're winning:**")
                st.markdown(comp["why_winning"])
                st.markdown(f"**Top content:**")
                st.markdown(comp["top_content"])
            with col_steal:
                st.markdown(
                    f"""<div style="background:#0d2a0d;border-left:3px solid #2a9d4e;padding:12px;border-radius:6px;">
                    <div style="color:#2a9d4e;font-size:0.8rem;font-weight:700;margin-bottom:6px;">💡 STEAL THIS FOR NEON GIANT</div>
                    <div style="color:#e0e0e0;font-size:0.9rem;">{comp['steal_this']}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
                st.markdown("")
                st.link_button(f"View {comp['handle']} on Instagram →", comp["url"])

    st.markdown("---")
    st.markdown("### 🎯 Your engagement goal: raving fans")
    st.markdown("""
The accounts above that get **comments, shares, and saves** — not just likes — all do the same 3 things:

1. **They show real humans doing hard work** — The crew IS the content. Every job is a story.
2. **They teach something** — Educational carousels get saved and shared to friends who are moving.
3. **They are specific to their market** — PNW angles: rain moves, ferry routes, steep driveways, Skagit Valley landmarks.

**Neon Giant's unfair advantages:**
- Vale on camera — owner-led accounts outperform branded accounts 3:1 on trust
- Realtor relationships — built-in collab partners that most movers don't have
- Junk removal — before/after content that writes itself
- The Giant Knowledge series — already differentiating from every competitor in this list
""")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    _inject_brand_css()
    render_header()

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
        "📊 Overview",
        "📈 Trends",
        "👥 Audience",
        "🖼️ Posts",
        "🕐 Best Time to Post",
        "📅 Frequency",
        "💡 Ideas",
        "📅 Notion Calendar",
        "🔍 Competitors",
    ])

    with tab1:
        render_resumen()
    with tab2:
        render_tendencia()
    with tab3:
        render_audiencia()
    with tab4:
        render_posts()
    with tab5:
        render_cuando()
    with tab6:
        render_frecuencia()
    with tab7:
        render_ideas()
    with tab8:
        render_notion()
    with tab9:
        render_competitors()


if __name__ == "__main__":
    main()
