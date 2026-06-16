"""
OBSOLETO — No usar. Ejecute main.py (Flask + HTML).
Ver _legacy/OBSOLETO.md

SmartRoute WMS — Aplicación web profesional (Streamlit)
Gestión de Almacenes Inteligentes · Optimización de rutas AGV

Ejecutar: py -3 -m streamlit run web_app.py
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.algoritmos import (
    bellman_ford_path,
    bfs_path,
    check_connectivity_ufds,
    dijkstra_path,
    floyd_warshall_hubs,
    kruskal_mst,
    prim_mst,
)
from src.grafo import NODE_COUNT, apply_traffic, build_graph, graph_stats, sector_hub_nodes
from src.metricas import path_metrics, savings_pct
from src import tema as T
from src import ui
from src.visualizer import plot_warehouse

# ── Configuración ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SmartRoute WMS | Gestión de Almacenes Inteligentes",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

OPERATIONAL_PAGES = {"operacion", "analisis", "infraestructura"}


@st.cache_resource
def get_base_graph():
    return build_graph()


def prepare_graph(franja: str, closed: set[tuple[int, int]]):
    g = copy.deepcopy(get_base_graph())
    for u, v in closed:
        if g.has_edge(u, v):
            g.remove_edge(u, v)
    apply_traffic(g, franja)
    return g


def init_state():
    defaults = {
        "page": "inicio",
        "results": None,
        "closed_edges": set(),
        "mst_edges": None,
        "infra_msg": "",
        "franja": "alta",
        "origin": 0,
        "dest": 1499,
        "contact_sent": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def run_route_calc(origin: int, dest: int, franja: str) -> None:
    g = prepare_graph(franja, st.session_state.closed_edges)
    if not check_connectivity_ufds(g, origin, dest):
        st.error("No hay ruta disponible entre origen y destino. Verifique los nodos seleccionados.")
        return
    bfs = bfs_path(g, origin, dest)
    dij = dijkstra_path(g, origin, dest)
    bf = bellman_ford_path(g, origin, dest)
    mst_e, mst_c, mst_ms = prim_mst(g)
    krus_e, krus_c, krus_ms = kruskal_mst(g)
    if not dij.ok:
        st.error(dij.msg)
        return
    mb = path_metrics(g, bfs.path)
    md = path_metrics(g, dij.path)
    save = savings_pct(mb.weighted_cost, md.weighted_cost)
    st.session_state.results = {
        "g": g, "bfs": bfs, "dij": dij, "bf": bf,
        "mb": mb, "md": md, "save": save,
        "mst_e": mst_e, "mst_c": mst_c, "mst_ms": mst_ms,
        "krus_c": krus_c, "krus_ms": krus_ms,
        "origin": origin, "dest": dest, "franja": franja,
    }
    st.session_state.mst_edges = mst_e


def render_sidebar_controls(base) -> tuple[int, int, str]:
    stats = graph_stats(base)
    with st.sidebar:
        st.markdown("### Panel de control")
        st.caption("Parámetros de simulación operativa")
        st.divider()

        franja = st.radio(
            "Nivel de tráfico",
            options=["baja", "media", "alta"],
            format_func=lambda x: f"{T.TRAFFIC_ICONS[x]} {T.TRAFFIC_LABELS[x]}",
            index=["baja", "media", "alta"].index(st.session_state.franja),
            key="sidebar_franja",
        )
        st.session_state.franja = franja

        st.divider()
        st.markdown("**Puntos de ruta**")
        origin = st.number_input(
            "Nodo origen (picking)",
            0, NODE_COUNT - 1,
            st.session_state.origin,
            key="sidebar_origin",
        )
        dest = st.number_input(
            "Nodo destino (despacho)",
            0, NODE_COUNT - 1,
            st.session_state.dest,
            key="sidebar_dest",
        )
        st.session_state.origin = int(origin)
        st.session_state.dest = int(dest)
        st.caption(
            f"Sector origen: **{base.nodes[int(origin)]['sector']}** · "
            f"Tipo destino: **{base.nodes[int(dest)]['tipo']}**"
        )

        st.divider()
        if st.button("✦ Calcular mejor ruta", use_container_width=True, type="primary"):
            run_route_calc(int(origin), int(dest), franja)
            st.toast("Ruta optimizada calculada correctamente.", icon="✅")

        if st.button("Asignar ruta al AGV", use_container_width=True):
            if st.session_state.results:
                st.success("Ruta asignada al robot AGV (simulación).")
            else:
                st.warning("Calcule una ruta antes de asignar.")

        st.divider()
        st.markdown("**Resumen del grafo**")
        c1, c2 = st.columns(2)
        c1.metric("Nodos", stats["nodos"])
        c2.metric("Aristas", stats["aristas"])
        st.caption("Layout 30 × 50 · Dataset sintético")

    return int(origin), int(dest), franja


def render_sidebar_minimal():
    with st.sidebar:
        st.markdown("### SmartRoute WMS")
        st.caption("Use la barra superior para navegar entre secciones.")
        st.divider()
        st.markdown(
            """
**Secciones disponibles**

- **Operación** — Mapa y rutas en vivo  
- **Análisis** — Comparativa de algoritmos  
- **Infraestructura** — MST y conectividad  
- **Acerca de** — Equipo y proyecto  
- **Información** — Especificaciones técnicas  
- **Contacto** — Formulario de consultas  
            """
        )
        if st.button("Ir a Operación", use_container_width=True):
            st.session_state.page = "operacion"
            st.rerun()


# ── Páginas ─────────────────────────────────────────────────────────────────

def page_inicio():
    ui.hero(
        "Optimización inteligente de rutas AGV",
        "SmartRoute WMS es una plataforma formal de gestión de almacenes que modela "
        "su centro de distribución como un grafo de 1 500 nodos y calcula la ruta óptima "
        "considerando congestión dinámica, consumo energético y tiempos de tránsito.",
        badges=[
            "Logística 4.0",
            "7 algoritmos de grafos",
            "ODS 9 — Industria sostenible",
            "UPC · 1ACC0184",
        ],
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(ui.stat_box("1 500", "Nodos del almacén"), unsafe_allow_html=True)
    with c2:
        st.markdown(ui.stat_box("3 058", "Aristas (pasillos)"), unsafe_allow_html=True)
    with c3:
        st.markdown(ui.stat_box("20.8%", "Ahorro vs ruta directa"), unsafe_allow_html=True)
    with c4:
        st.markdown(ui.stat_box("7", "Algoritmos integrados"), unsafe_allow_html=True)

    st.markdown('<p class="sr-section-title">¿Por qué SmartRoute?</p>', unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)
    with f1:
        st.markdown(
            ui.feature_card(
                "🎯",
                "Decisiones operativas claras",
                "El operador visualiza en segundos la ruta recomendada frente a la ruta directa, "
                "con métricas de tiempo, energía y congestión promedio.",
            ),
            unsafe_allow_html=True,
        )
    with f2:
        st.markdown(
            ui.feature_card(
                "⚡",
                "Pesos dinámicos por tráfico",
                "Simula franjas de baja, media y alta congestión (incluyendo hora pico) "
                "para evaluar cómo cambia la decisión algorítmica en escenarios reales.",
            ),
            unsafe_allow_html=True,
        )
    with f3:
        st.markdown(
            ui.feature_card(
                "🏗️",
                "Infraestructura bajo control",
                "Analice pasillos críticos con MST (Prim/Kruskal), verifique conectividad "
                "con UFDS y obtenga costos entre sectores con Floyd-Warshall.",
            ),
            unsafe_allow_html=True,
        )

    st.markdown('<p class="sr-section-title">Comience aquí</p>', unsafe_allow_html=True)
    b1, b2, _ = st.columns([1, 1, 2])
    with b1:
        if st.button("▶ Ir a Operación", use_container_width=True, type="primary"):
            st.session_state.page = "operacion"
            st.rerun()
    with b2:
        if st.button("📊 Ver Análisis", use_container_width=True):
            st.session_state.page = "analisis"
            st.rerun()


def page_operacion(origin: int, dest: int, franja: str):
    ui.hero(
        "Centro de operaciones",
        f"Visualización del almacén en **{T.TRAFFIC_LABELS[franja].lower()}**. "
        "La ruta verde (Dijkstra) evita pasillos saturados; la amarilla (BFS) representa "
        "el camino con menos saltos.",
        badges=[f"Origen: nodo {origin}", f"Destino: nodo {dest}"],
    )

    res = st.session_state.results
    g_show = prepare_graph(franja, st.session_state.closed_edges)
    dijk_p = res["dij"].path if res else None
    bfs_p = res["bfs"].path if res else None

    col_map, col_kpi = st.columns([2.2, 1])
    with col_map:
        st.markdown('<div class="sr-panel">', unsafe_allow_html=True)
        fig = plot_warehouse(
            g_show,
            origin=origin,
            destination=dest,
            dijk_path=dijk_p,
            bfs_path=bfs_p,
            title=f"Mapa del almacén · {T.TRAFFIC_LABELS[franja]}",
        )
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)
        st.markdown("</div>", unsafe_allow_html=True)
        st.caption("■ Verde: ruta recomendada · ■ Amarillo: ruta directa · ■ Cuadrado: origen · ★ destino")

    with col_kpi:
        st.markdown('<div class="sr-panel">', unsafe_allow_html=True)
        st.markdown("##### Indicadores clave")
        if res:
            md, save = res["md"], res["save"]
            st.metric("Tiempo estimado", f"{md.time_min} min")
            st.metric("Distancia", f"{md.distance_m} m")
            st.metric("Ahorro operativo", f"{save}%")
            st.metric("Energía estimada", f"{md.energy_kwh} kWh")
            st.metric("Tráfico en ruta", f"{md.avg_congestion}")
            st.success(
                f"En {T.TRAFFIC_LABELS[franja].lower()}, la ruta optimizada reduce el costo "
                f"ponderado un **{save}%** respecto a la ruta directa."
            )
        else:
            st.metric("Tiempo estimado", "—")
            st.metric("Ahorro operativo", "—")
            st.info("Pulse **Calcular mejor ruta** en el panel lateral para obtener resultados.")
        st.markdown("</div>", unsafe_allow_html=True)


def page_analisis(franja: str):
    ui.hero(
        "Análisis comparativo",
        "Evaluación rigurosa entre la ruta directa (BFS) y la ruta optimizada (Dijkstra), "
        "con validación cruzada mediante Bellman-Ford.",
    )

    res = st.session_state.results
    if not res:
        st.warning("No hay resultados aún. Vaya a **Operación** y calcule una ruta, o use el panel lateral.")
        return

    mb, md, save, dij, bfs, bf = res["mb"], res["md"], res["save"], res["dij"], res["bfs"], res["bf"]

    df = pd.DataFrame([
        {
            "Tipo de ruta": "Recomendada (Dijkstra)",
            "Tiempo (min)": md.time_min,
            "Distancia (m)": md.distance_m,
            "Tráfico prom.": md.avg_congestion,
            "Energía (kWh)": md.energy_kwh,
            "Costo ponderado": round(md.weighted_cost, 2),
        },
        {
            "Tipo de ruta": "Directa (BFS)",
            "Tiempo (min)": mb.time_min,
            "Distancia (m)": mb.distance_m,
            "Tráfico prom.": mb.avg_congestion,
            "Energía (kWh)": mb.energy_kwh,
            "Costo ponderado": round(mb.weighted_cost, 2),
        },
    ])
    st.dataframe(df, use_container_width=True, hide_index=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Ahorro de costo", f"{save}%")
    c2.metric("Diferencia distancia", f"{abs(mb.distance_m - md.distance_m):.1f} m")
    bf_ok = abs(bf.cost - dij.cost) < 0.1
    c3.metric("Validación Bellman-Ford", "Coincide ✓" if bf_ok else "Revisar")

    st.markdown('<p class="sr-section-title">Interpretación</p>', unsafe_allow_html=True)
    st.markdown(
        f"""
<div class="sr-panel">
<p style="color:{T.TEXT_SECONDARY}; line-height:1.7; margin:0;">
La ruta directa recorre <strong>{mb.distance_m} m</strong> con tráfico promedio
<strong>{mb.avg_congestion}</strong>. La ruta recomendada recorre
<strong>{md.distance_m} m</strong> con tráfico <strong>{md.avg_congestion}</strong>,
generando un ahorro de <strong>{save}%</strong> en costo operativo ponderado.<br><br>
<strong>Bellman-Ford</strong> reporta costo {bf.cost:.2f}
({'coincide con Dijkstra' if bf_ok else 'difiere — revisar grafo'}).
Menos frenadas implican menor consumo eléctrico, alineado al <strong>ODS 9</strong>.
</p>
</div>
        """,
        unsafe_allow_html=True,
    )

    fig = plot_warehouse(
        res["g"], origin=res["origin"], destination=res["dest"],
        dijk_path=dij.path, bfs_path=bfs.path,
        title="Comparación visual: BFS vs Dijkstra",
    )
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


def page_infraestructura(franja: str):
    ui.hero(
        "Infraestructura y conectividad",
        "Herramientas para planificadores: pasillos críticos (MST), simulación de cierres "
        "y matriz de costos entre sectores.",
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🔍 Pasillos críticos (MST)", use_container_width=True):
            g = prepare_graph(franja, st.session_state.closed_edges)
            pe, pc, _ = prim_mst(g)
            kc, _, _ = kruskal_mst(g)
            st.session_state.mst_edges = pe
            st.session_state.infra_msg = (
                f"**MST:** {len(pe)} aristas · Costo Prim: **{pc:.2f}** · "
                f"Kruskal: **{kc:.2f}** · "
                f"{'Validación OK ✓' if abs(pc - kc) < 0.01 else 'Difieren'}"
            )
    with c2:
        if st.button("🚧 Simular cierre de pasillo", use_container_width=True):
            g = prepare_graph(franja, st.session_state.closed_edges)
            pe, _, _ = prim_mst(g)
            if pe:
                u, v = pe[0]
                st.session_state.closed_edges.add((u, v))
                st.session_state.closed_edges.add((v, u))
                g2 = prepare_graph(franja, st.session_state.closed_edges)
                hubs = sector_hub_nodes(g2)
                ok = check_connectivity_ufds(g2, hubs["A"], hubs["DESPACHO"])
                st.session_state.infra_msg = (
                    f"**UFDS:** Pasillo **{u}–{v}** cerrado. "
                    f"Sector A → Despacho: **{'Conectado ✓' if ok else 'DESCONECTADO ⚠️'}**"
                )
    with c3:
        if st.button("📐 Matriz entre sectores", use_container_width=True):
            g = prepare_graph(franja, st.session_state.closed_edges)
            matrix, ms = floyd_warshall_hubs(g, sector_hub_nodes(g))
            labels = list(matrix.keys())
            rows = []
            for a in labels:
                row = {
                    b: round(matrix[a][b], 1) if matrix[a][b] != float("inf") else None
                    for b in labels
                }
                row["Desde"] = a
                rows.append(row)
            st.session_state.infra_msg = "matrix"
            st.session_state.floyd_df = pd.DataFrame(rows).set_index("Desde")
            st.session_state.floyd_ms = ms

    if st.session_state.closed_edges:
        if st.button("↩ Restaurar pasillos cerrados"):
            st.session_state.closed_edges = set()
            st.session_state.infra_msg = "Pasillos restaurados."
            st.rerun()

    if st.session_state.infra_msg:
        if st.session_state.infra_msg == "matrix":
            st.markdown('<p class="sr-section-title">Floyd-Warshall — costos entre sectores</p>', unsafe_allow_html=True)
            st.dataframe(st.session_state.get("floyd_df"), use_container_width=True)
            st.caption(f"Tiempo de cálculo: {st.session_state.get('floyd_ms', 0):.2f} ms")
        else:
            st.markdown(f'<div class="sr-panel">{st.session_state.infra_msg}</div>', unsafe_allow_html=True)

    if st.session_state.mst_edges:
        fig = plot_warehouse(
            prepare_graph(franja, st.session_state.closed_edges),
            mst_edges=st.session_state.mst_edges,
            title="Pasillos críticos — Árbol de expansión mínima (MST)",
        )
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)


def page_acerca():
    ui.hero(
        "Acerca de nosotros",
        "SmartRoute WMS nace como proyecto académico del curso Complejidad Algorítmica (1ACC0184) "
        "en la Universidad Peruana de Ciencias Aplicadas, orientado a resolver problemas reales "
        "de logística robotizada mediante teoría de grafos.",
    )

    st.markdown('<p class="sr-section-title">Nuestra misión</p>', unsafe_allow_html=True)
    st.markdown(
        f"""
<div class="sr-panel">
<p style="color:{T.TEXT_SECONDARY}; line-height:1.75; margin:0;">
Demostrar que las técnicas de complejidad algorítmica — BFS, Dijkstra, MST, UFDS y Floyd-Warshall —
tienen impacto directo en la operación diaria de un almacén inteligente. Nuestra plataforma traduce
esos algoritmos en decisiones comprensibles para operadores y planificadores logísticos.
</p>
</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<p class="sr-section-title">Equipo de desarrollo</p>', unsafe_allow_html=True)
    team = [
        ("Joseph Manuel Chavez Viera", "U202314019", "Arquitectura del grafo y algoritmos de rutas"),
        ("Gianfranco Jared Durand Vega", "U202312614", "Métricas operativas y validación"),
        ("Mario Alonso Fernandez Seer", "U202317807", "Interfaz, visualización y documentación"),
    ]
    for name, code, role in team:
        st.markdown(
            f'<div class="sr-team-member"><strong>{name}</strong> · <span>{code}</span><br>'
            f'<span>{role}</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<p class="sr-section-title">Contexto académico</p>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            ui.feature_card(
                "🎓",
                "Universidad Peruana de Ciencias Aplicadas",
                "Carrera de Ciencias de la Computación · Sección 3202 · "
                "Profesor: John Edward Arias Orihuela · Periodo 2026-10.",
            ),
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            ui.feature_card(
                "📋",
                "Trabajo Final TB2",
                "Entregable que integra informe teórico, aplicativo funcional, validación "
                "con casos de prueba CP-01 a CP-08 y exposición en semana 15.",
            ),
            unsafe_allow_html=True,
        )


def page_info(stats: dict):
    ui.hero(
        "Información técnica",
        "Especificaciones del dataset, algoritmos implementados y referencias del modelo de grafos "
        "utilizado en SmartRoute WMS.",
    )

    st.markdown('<p class="sr-section-title">Dataset del almacén</p>', unsafe_allow_html=True)
    spec = pd.DataFrame([
        {"Atributo": "Nodos |V|", "Valor": stats["nodos"]},
        {"Atributo": "Aristas |E|", "Valor": stats["aristas"]},
        {"Atributo": "Layout", "Valor": "30 filas × 50 columnas"},
        {"Atributo": "Dimensiones físicas", "Valor": "120 m × 80 m"},
        {"Atributo": "Tipo de grafo", "Valor": "No dirigido, ponderado"},
        {"Atributo": "Origen del dataset", "Valor": "Sintético (benchmark Azadeh et al., 2019)"},
        {"Atributo": "Peso de arista", "Valor": "Distancia × factor de congestión dinámico"},
    ])
    st.dataframe(spec, use_container_width=True, hide_index=True)

    st.markdown('<p class="sr-section-title">Algoritmos implementados</p>', unsafe_allow_html=True)
    algos = pd.DataFrame([
        {"Algoritmo": "BFS", "Uso en WMS": "Ruta directa (menos saltos)", "Complejidad": "O(V+E)"},
        {"Algoritmo": "Dijkstra", "Uso en WMS": "Ruta óptima con pesos dinámicos", "Complejidad": "O((V+E) log V)"},
        {"Algoritmo": "Bellman-Ford", "Uso en WMS": "Validación de costos mínimos", "Complejidad": "O(VE)"},
        {"Algoritmo": "Prim", "Uso en WMS": "MST — pasillos críticos", "Complejidad": "O(E log V)"},
        {"Algoritmo": "Kruskal", "Uso en WMS": "Validación cruzada del MST", "Complejidad": "O(E log E)"},
        {"Algoritmo": "UFDS", "Uso en WMS": "Conectividad tras cierres", "Complejidad": "O(α(V))"},
        {"Algoritmo": "Floyd-Warshall", "Uso en WMS": "Costos entre sectores", "Complejidad": "O(V³)"},
    ])
    st.dataframe(algos, use_container_width=True, hide_index=True)

    st.markdown('<p class="sr-section-title">Rendimiento en ejecución</p>', unsafe_allow_html=True)
    res = st.session_state.results
    if res:
        perf = pd.DataFrame([
            {"Algoritmo": "BFS", "Costo": round(res["bfs"].cost, 2), "Tiempo (ms)": res["bfs"].elapsed_ms, "Nodos en ruta": len(res["bfs"].path)},
            {"Algoritmo": "Dijkstra", "Costo": round(res["dij"].cost, 2), "Tiempo (ms)": res["dij"].elapsed_ms, "Nodos en ruta": len(res["dij"].path)},
            {"Algoritmo": "Bellman-Ford", "Costo": round(res["bf"].cost, 2), "Tiempo (ms)": res["bf"].elapsed_ms, "Nodos en ruta": len(res["bf"].path)},
            {"Algoritmo": "Prim (MST)", "Costo": round(res["mst_c"], 2), "Tiempo (ms)": res["mst_ms"], "Nodos en ruta": "—"},
        ])
        st.dataframe(perf, use_container_width=True, hide_index=True)
    else:
        st.info("Calcule una ruta en **Operación** para ver tiempos de ejecución en vivo.")

    st.markdown('<p class="sr-section-title">Limitaciones del modelo</p>', unsafe_allow_html=True)
    st.markdown(
        f"""
<div class="sr-panel">
<ul style="color:{T.TEXT_SECONDARY}; line-height:1.8;">
<li>No incluye planificación multi-robot (MAPF).</li>
<li>No modela restricciones físicas del AGV (giro, carga máxima).</li>
<li>La congestión es sintética por franja horaria, no datos IoT en tiempo real.</li>
<li>El grafo es estático salvo cierres simulados manualmente.</li>
</ul>
</div>
        """,
        unsafe_allow_html=True,
    )


def page_contacto():
    ui.hero(
        "Contáctanos",
        "¿Tiene consultas sobre la plataforma, la integración con su almacén o el proyecto académico? "
        "Complete el formulario y nuestro equipo responderá a la brevedad.",
    )

    col_form, col_info = st.columns([1.4, 1])
    with col_form:
        st.markdown('<div class="sr-contact-box">', unsafe_allow_html=True)
        st.markdown("##### Formulario de contacto")
        with st.form("contact_form", clear_on_submit=True):
            nombre = st.text_input("Nombre completo *", placeholder="Ej. Juan Pérez")
            email = st.text_input("Correo electrónico *", placeholder="ejemplo@upc.edu.pe")
            empresa = st.text_input("Empresa / Institución", placeholder="Opcional")
            asunto = st.selectbox(
                "Asunto",
                ["Consulta general", "Demo del sistema", "Integración WMS", "Proyecto académico", "Otro"],
            )
            mensaje = st.text_area(
                "Mensaje *",
                placeholder="Describa su consulta...",
                height=140,
            )
            enviado = st.form_submit_button("Enviar mensaje", use_container_width=True, type="primary")
            if enviado:
                if nombre and email and mensaje:
                    st.session_state.contact_sent = True
                    st.success(f"Gracias, **{nombre}**. Su mensaje ha sido registrado. Responderemos a **{email}**.")
                else:
                    st.error("Complete los campos obligatorios marcados con *.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_info:
        st.markdown(
            f"""
<div class="sr-contact-box">
<h3>Datos de contacto</h3>
<p style="color:{T.TEXT_SECONDARY}; line-height:1.8;">
<strong style="color:{T.GREEN_LIGHT}">Universidad Peruana de Ciencias Aplicadas</strong><br>
Campus San Isidro · Lima, Perú<br><br>
<strong style="color:{T.GREEN_LIGHT}">Correo del equipo</strong><br>
smartroute.wms@upc.edu.pe<br><br>
<strong style="color:{T.GREEN_LIGHT}">Horario de atención</strong><br>
Lunes a viernes · 9:00 – 18:00<br><br>
<strong style="color:{T.GREEN_LIGHT}">Curso</strong><br>
1ACC0184 — Complejidad Algorítmica
</p>
</div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            ui.feature_card(
                "💬",
                "Soporte técnico",
                "Para incidencias con la simulación o el cálculo de rutas, incluya captura "
                "de pantalla y los nodos origen/destino utilizados.",
            ),
            unsafe_allow_html=True,
        )


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    init_state()
    ui.inject_global_css()

    page = ui.render_hotbar(st.session_state.page)
    st.session_state.page = page

    base = get_base_graph()
    stats = graph_stats(base)

    if page in OPERATIONAL_PAGES:
        origin, dest, franja = render_sidebar_controls(base)
    else:
        render_sidebar_minimal()
        origin = st.session_state.origin
        dest = st.session_state.dest
        franja = st.session_state.franja

    if page == "inicio":
        page_inicio()
    elif page == "operacion":
        page_operacion(origin, dest, franja)
    elif page == "analisis":
        page_analisis(franja)
    elif page == "infraestructura":
        page_infraestructura(franja)
    elif page == "acerca":
        page_acerca()
    elif page == "info":
        page_info(stats)
    elif page == "contacto":
        page_contacto()

    ui.render_footer()


if __name__ == "__main__":
    main()
