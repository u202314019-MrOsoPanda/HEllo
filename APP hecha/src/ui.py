"""OBSOLETO — No usar. Interfaz actual: templates/ + static/. Ver _legacy/OBSOLETO.md."""

from __future__ import annotations

import streamlit as st

from src import tema as T

NAV_ITEMS = [
    ("inicio", "Inicio", "🏠"),
    ("operacion", "Operación", "🗺️"),
    ("analisis", "Análisis", "📊"),
    ("infraestructura", "Infraestructura", "🏗️"),
    ("acerca", "Acerca de", "👥"),
    ("info", "Información", "ℹ️"),
    ("contacto", "Contacto", "✉️"),
]


def inject_global_css() -> None:
    st.markdown(
        f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=Outfit:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {{
    font-family: 'DM Sans', 'Outfit', sans-serif;
}}

.stApp {{
    background: linear-gradient(165deg, {T.BG_DARK} 0%, #1e1430 40%, #152228 100%);
}}

.block-container {{
    padding-top: 1.2rem;
    max-width: 1280px;
}}

/* ── Hotbar ── */
.sr-hotbar {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: linear-gradient(90deg, {T.BG_PANEL} 0%, #32204a 50%, #1e3040 100%);
    border: 1px solid {T.PURPLE_MAIN};
    border-radius: 14px;
    padding: 0.55rem 1.25rem;
    margin-bottom: 1.25rem;
    box-shadow: 0 8px 32px rgba(0,0,0,0.35);
}}
.sr-brand {{
    display: flex;
    align-items: center;
    gap: 0.65rem;
    min-width: 200px;
}}
.sr-logo {{
    width: 38px; height: 38px;
    background: linear-gradient(135deg, {T.PURPLE_MAIN}, {T.GREEN_ACCENT});
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.1rem; font-weight: 700; color: white;
}}
.sr-brand-text h2 {{
    margin: 0; font-size: 1.05rem; font-weight: 700;
    color: {T.GREEN_LIGHT} !important; letter-spacing: 0.02em;
}}
.sr-brand-text span {{
    font-size: 0.72rem; color: {T.TEXT_MUTED}; display: block;
}}
.sr-status {{
    font-size: 0.75rem; color: {T.GREEN_MAIN};
    background: rgba(168,230,207,0.12);
    border: 1px solid {T.GREEN_ACCENT};
    border-radius: 20px;
    padding: 0.3rem 0.85rem;
    white-space: nowrap;
}}

/* Nav pills via Streamlit buttons */
div[data-testid="stHorizontalBlock"]:has(.sr-nav-marker) {{
    gap: 0.35rem !important;
}}
div[data-testid="stHorizontalBlock"]:has(.sr-nav-marker) .stButton > button {{
    background: transparent !important;
    color: {T.TEXT_SECONDARY} !important;
    border: 1px solid transparent !important;
    border-radius: 8px !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    padding: 0.45rem 0.65rem !important;
    transition: all 0.2s ease;
}}
div[data-testid="stHorizontalBlock"]:has(.sr-nav-marker) .stButton > button:hover {{
    background: rgba(112,88,152,0.35) !important;
    color: {T.TEXT_PRIMARY} !important;
    border-color: {T.PURPLE_MAIN} !important;
}}
div[data-testid="stHorizontalBlock"]:has(.sr-nav-marker) .stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, {T.PURPLE_MAIN}, #5a4580) !important;
    color: {T.TEXT_PRIMARY} !important;
    border-color: {T.PURPLE_LIGHT} !important;
    font-weight: 600 !important;
}}

/* Cards & sections */
.sr-hero {{
    background: linear-gradient(135deg, {T.BG_CARD} 0%, #2a4a42 55%, {T.BG_PANEL} 100%);
    border: 1px solid {T.PURPLE_MAIN};
    border-radius: 18px;
    padding: 2rem 2.25rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 12px 40px rgba(0,0,0,0.25);
}}
.sr-hero h1 {{
    margin: 0 0 0.5rem;
    font-size: 2.15rem;
    font-weight: 700;
    color: {T.GREEN_LIGHT} !important;
    line-height: 1.2;
}}
.sr-hero .subtitle {{
    color: {T.TEXT_SECONDARY};
    font-size: 1.05rem;
    margin: 0 0 1rem;
    max-width: 720px;
}}
.sr-hero .badge-row {{
    display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 1rem;
}}
.sr-badge {{
    background: rgba(168,230,207,0.1);
    border: 1px solid {T.GREEN_ACCENT};
    color: {T.GREEN_MAIN};
    border-radius: 20px;
    padding: 0.25rem 0.75rem;
    font-size: 0.78rem;
    font-weight: 500;
}}
.sr-card {{
    background: {T.BG_CARD};
    border: 1px solid {T.PURPLE_MAIN};
    border-radius: 14px;
    padding: 1.35rem 1.5rem;
    height: 100%;
    transition: transform 0.2s, box-shadow 0.2s;
}}
.sr-card:hover {{
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(112,88,152,0.25);
}}
.sr-card h3 {{
    color: {T.GREEN_MAIN} !important;
    font-size: 1rem;
    margin: 0 0 0.5rem;
}}
.sr-card p {{
    color: {T.TEXT_SECONDARY};
    font-size: 0.9rem;
    margin: 0;
    line-height: 1.55;
}}
.sr-card .icon {{
    font-size: 1.75rem;
    margin-bottom: 0.65rem;
}}
.sr-section-title {{
    color: {T.GREEN_LIGHT} !important;
    font-size: 1.35rem;
    font-weight: 600;
    margin: 1.5rem 0 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid {T.PURPLE_MAIN};
}}
.sr-stat {{
    text-align: center;
    background: {T.BG_PANEL};
    border: 1px solid {T.PURPLE_MAIN};
    border-radius: 12px;
    padding: 1.1rem 0.75rem;
}}
.sr-stat .num {{
    font-size: 1.85rem;
    font-weight: 700;
    color: {T.GREEN_LIGHT};
    display: block;
}}
.sr-stat .lbl {{
    font-size: 0.78rem;
    color: {T.TEXT_MUTED};
    text-transform: uppercase;
    letter-spacing: 0.06em;
}}

/* Footer */
.sr-footer {{
    margin-top: 2.5rem;
    padding: 1.75rem 1.5rem 1rem;
    background: {T.BG_PANEL};
    border: 1px solid {T.PURPLE_MAIN};
    border-radius: 14px;
}}
.sr-footer h4 {{
    color: {T.GREEN_MAIN} !important;
    font-size: 0.9rem;
    margin: 0 0 0.65rem;
}}
.sr-footer p, .sr-footer li {{
    color: {T.TEXT_MUTED};
    font-size: 0.82rem;
    line-height: 1.6;
    margin: 0;
}}
.sr-footer ul {{ padding-left: 1.1rem; margin: 0; }}
.sr-footer-bottom {{
    margin-top: 1.25rem;
    padding-top: 1rem;
    border-top: 1px solid {T.PURPLE_MAIN};
    text-align: center;
    color: {T.TEXT_MUTED};
    font-size: 0.75rem;
}}

/* Metrics & sidebar */
[data-testid="stSidebar"] {{
    background: {T.BG_PANEL} !important;
    border-right: 1px solid {T.PURPLE_MAIN};
}}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{
    color: {T.GREEN_MAIN} !important;
}}
div[data-testid="stMetric"] {{
    background: {T.BG_CARD};
    border: 1px solid {T.PURPLE_MAIN};
    border-radius: 12px;
    padding: 0.85rem 1rem;
}}
div[data-testid="stMetric"] label {{ color: {T.TEXT_SECONDARY} !important; }}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
    color: {T.GREEN_LIGHT} !important;
    font-weight: 700;
}}
.stButton > button {{
    background: linear-gradient(135deg, {T.GREEN_BTN}, {T.GREEN_ACCENT});
    color: {T.BG_DARK};
    font-weight: 600;
    border: none;
    border-radius: 10px;
}}
.stButton > button:hover {{
    background: {T.GREEN_MAIN};
    color: {T.BG_DARK};
}}
.stTabs [data-baseweb="tab-list"] {{ gap: 6px; }}
.stTabs [data-baseweb="tab"] {{
    background: {T.BG_PANEL};
    color: {T.TEXT_SECONDARY};
    border-radius: 8px;
}}
.stTabs [aria-selected="true"] {{
    background: {T.PURPLE_MAIN} !important;
    color: {T.TEXT_PRIMARY} !important;
}}
h1, h2, h3 {{ color: {T.GREEN_MAIN} !important; }}

.sr-panel {{
    background: {T.BG_CARD};
    border: 1px solid {T.PURPLE_MAIN};
    border-radius: 14px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
}}
.sr-team-member {{
    background: {T.BG_PANEL};
    border: 1px solid {T.PURPLE_MAIN};
    border-radius: 12px;
    padding: 1rem 1.15rem;
    margin-bottom: 0.75rem;
}}
.sr-team-member strong {{ color: {T.GREEN_LIGHT}; }}
.sr-team-member span {{ color: {T.TEXT_MUTED}; font-size: 0.85rem; }}

.sr-contact-box {{
    background: linear-gradient(145deg, {T.BG_CARD}, {T.BG_PANEL});
    border: 1px solid {T.GREEN_ACCENT};
    border-radius: 14px;
    padding: 1.5rem;
}}
.sr-contact-box h3 {{ color: {T.GREEN_LIGHT} !important; margin-top: 0; }}
</style>
        """,
        unsafe_allow_html=True,
    )


def render_hotbar(current: str) -> str:
    """Barra superior con logo y navegación. Devuelve la página seleccionada."""
    st.markdown(
        f"""
<div class="sr-hotbar">
  <div class="sr-brand">
    <div class="sr-logo">SR</div>
    <div class="sr-brand-text">
      <h2>SmartRoute WMS</h2>
      <span>Gestión de Almacenes Inteligentes</span>
    </div>
  </div>
  <div class="sr-status">● Sistema operativo</div>
</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sr-nav-marker"></div>', unsafe_allow_html=True)
    cols = st.columns(len(NAV_ITEMS))
    for col, (slug, label, icon) in zip(cols, NAV_ITEMS):
        with col:
            is_active = slug == current
            if st.button(
                f"{icon} {label}",
                key=f"nav_{slug}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state.page = slug
                st.rerun()
    return st.session_state.page


def render_footer() -> None:
    st.markdown(
        f"""
<div class="sr-footer">
  <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1.5rem;">
    <div>
      <h4>SmartRoute WMS</h4>
      <p>Plataforma de optimización de rutas AGV para centros de distribución tecnológicos. Proyecto académico TB2 — 1ACC0184.</p>
    </div>
    <div>
      <h4>Enlaces rápidos</h4>
      <ul>
        <li>Operación y mapa en tiempo real</li>
        <li>Comparativa BFS vs Dijkstra</li>
        <li>Análisis de infraestructura (MST)</li>
      </ul>
    </div>
    <div>
      <h4>Universidad</h4>
      <p>Universidad Peruana de Ciencias Aplicadas<br>
      Ciencias de la Computación · Sección 3202<br>
      Periodo 2026-10</p>
    </div>
  </div>
  <div class="sr-footer-bottom">
    © 2026 SmartRoute WMS · Joseph Chavez · Gianfranco Durand · Mario Fernandez · Todos los derechos reservados
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def hero(title: str, subtitle: str, badges: list[str] | None = None) -> None:
    badges_html = ""
    if badges:
        badges_html = '<div class="badge-row">' + "".join(
            f'<span class="sr-badge">{b}</span>' for b in badges
        ) + "</div>"
    st.markdown(
        f'<div class="sr-hero"><h1>{title}</h1><p class="subtitle">{subtitle}</p>{badges_html}</div>',
        unsafe_allow_html=True,
    )


def feature_card(icon: str, title: str, text: str) -> str:
    return f"""
<div class="sr-card">
  <div class="icon">{icon}</div>
  <h3>{title}</h3>
  <p>{text}</p>
</div>"""


def stat_box(value: str, label: str) -> str:
    return f'<div class="sr-stat"><span class="num">{value}</span><span class="lbl">{label}</span></div>'
