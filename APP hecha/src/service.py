"""Capa de servicio — lógica de negocio para la API web."""

from __future__ import annotations

import base64
import copy
import io
from dataclasses import asdict
from functools import lru_cache

import matplotlib.pyplot as plt

from src.algoritmos import (
    bellman_ford_path,
    bfs_path,
    check_connectivity_ufds,
    dijkstra_path,
    floyd_warshall_hubs,
    kruskal_mst,
    prim_mst,
)
from src.catalogo import InventarioCatalog, pasillo_id, pasillo_label
from src.grafo import COLS, HEIGHT_M, NODE_COUNT, ROWS, WIDTH_M, apply_traffic, build_graph, graph_stats, sector_hub_nodes
from src.inventario import (
    PRODUCTOS,
    ROBOT_PROFILES,
    explicar_ruta,
    nodo_detalle,
    random_picking_despacho,
)
from src.metricas import RouteMetrics, path_metrics, savings_pct
from src.visualizer import plot_warehouse

ALGO_COMPLEXITY = {
    "bfs": {"time": "O(V + E)", "space": "O(V)", "use": "Ruta directa (saltos mínimos)"},
    "dijkstra": {"time": "O((V + E) log V)", "space": "O(V)", "use": "Ruta óptima con pesos ≥ 0"},
    "bellman_ford": {"time": "O(V × E)", "space": "O(V)", "use": "Validación de optimalidad"},
    "prim": {"time": "O(E log V)", "space": "O(V)", "use": "MST — red mínima de conexión"},
    "kruskal": {"time": "O(E log E)", "space": "O(V)", "use": "Verificación MST"},
    "floyd_warshall": {"time": "O(V³)", "space": "O(V²)", "use": "Distancias entre sectores"},
    "ufds": {"time": "O(α(V))", "space": "O(V)", "use": "Conectividad tras cierres"},
}

_TYPE_CODE = {"ALMACEN": "A", "DESPACHO": "D", "INTERSECCION": "I", "RECARGA": "R"}

_BASE_GRAPH = build_graph()
_CATALOG = InventarioCatalog(_BASE_GRAPH)
_SESSION: dict[str, set[tuple[int, int]]] = {}
_HISTORY: dict[str, list[dict]] = {}
_ROUTE_IMG_CACHE: dict[str, str] = {}
_MAX_IMG_CACHE = 64
_MAX_HISTORY = 3


def _closed(session_id: str) -> set[tuple[int, int]]:
    if session_id not in _SESSION:
        _SESSION[session_id] = set()
    return _SESSION[session_id]


def _closed_fingerprint(session_id: str) -> str:
    return ",".join(f"{u}-{v}" for u, v in sorted(_closed(session_id)))


def _trim_cache(cache: dict[str, str]) -> None:
    while len(cache) > _MAX_IMG_CACHE:
        cache.pop(next(iter(cache)))


def prepare_graph(franja: str, session_id: str):
    g = copy.deepcopy(_BASE_GRAPH)
    for u, v in _closed(session_id):
        if g.has_edge(u, v):
            g.remove_edge(u, v)
    apply_traffic(g, franja)
    return g


@lru_cache(maxsize=1)
def get_map_layout() -> dict:
    nodes: list[list] = []
    for n, d in _BASE_GRAPH.nodes(data=True):
        nodes.append([
            n,
            round(d["x"], 2),
            round(d["y"], 2),
            _TYPE_CODE.get(d["tipo"], "A"),
        ])
    return {
        "ok": True,
        "cols": COLS,
        "rows": ROWS,
        "width": WIDTH_M,
        "height": HEIGHT_M,
        "nodes": nodes,
    }


def get_defaults() -> dict:
    pair = random_picking_despacho(_BASE_GRAPH)
    o, d = pair["origin"], pair["dest"]
    return {
        "ok": True,
        "origin": o,
        "dest": d,
        "origin_detail": nodo_detalle(_BASE_GRAPH, o),
        "dest_detail": nodo_detalle(_BASE_GRAPH, d),
    }


def search_inventory(query: str, tipo: str = "all", limit: int = 25) -> dict:
    return _CATALOG.buscar(query, tipo=tipo, limit=limit)


def list_aisles(limit: int = 80) -> dict:
    return {"ok": True, "pasillos": _CATALOG.listar_pasillos(limit=limit)}


def get_aisle(sector: str, letra: str) -> dict:
    data = _CATALOG.contenido_pasillo(sector, letra)
    if not data:
        return {"ok": False, "error": f"No existe el pasillo {sector}-{letra.upper()}."}
    return {"ok": True, "pasillo": data}


def get_aisle_by_node(nid: int) -> dict:
    data = _CATALOG.contenido_desde_nodo(nid)
    if not data:
        return {"ok": False, "error": "Nodo sin pasillo de almacén asociado."}
    return {"ok": True, "pasillo": data}


def list_products(q: str = "", limit: int = 60, offset: int = 0) -> dict:
    data = _CATALOG.listar_productos(q=q, limit=limit, offset=offset)
    return {
        "ok": True,
        **data,
        "categorias": PRODUCTOS,
        "resumen": _CATALOG.resumen_productos(),
    }


def get_stats() -> dict:
    return graph_stats(_BASE_GRAPH)


def health_check() -> dict:
    g = prepare_graph("alta", "__health__")
    pair = random_picking_despacho(_BASE_GRAPH)
    o, d = pair["origin"], pair["dest"]
    dij = dijkstra_path(g, o, d)
    return {
        "ok": dij.ok,
        "nodes": NODE_COUNT,
        "pasillos_indexados": len(_CATALOG.pasillo_meta),
        "productos": len(_CATALOG.by_sku),
        "complexity": ALGO_COMPLEXITY,
        "port_hint": int(__import__("os").environ.get("PORT", "5000")),
    }


def get_node_info(nid: int) -> dict:
    return nodo_detalle(_BASE_GRAPH, nid)


def get_robots() -> list[dict]:
    return [{"id": k, **{kk: vv for kk, vv in v.items() if kk != "speed" and kk != "energy"}} for k, v in ROBOT_PROFILES.items()]


def random_route() -> dict:
    pair = random_picking_despacho(_BASE_GRAPH)
    return {
        "ok": True,
        "origin": pair["origin"],
        "dest": pair["dest"],
        "origin_detail": nodo_detalle(_BASE_GRAPH, pair["origin"]),
        "dest_detail": nodo_detalle(_BASE_GRAPH, pair["dest"]),
    }


def get_route_history(session_id: str) -> dict:
    return {"ok": True, "history": list(_HISTORY.get(session_id, []))}


def _push_history(session_id: str, entry: dict) -> None:
    hist = _HISTORY.setdefault(session_id, [])
    hist.insert(0, entry)
    del hist[_MAX_HISTORY:]


def _apply_robot(m: RouteMetrics, robot: str) -> RouteMetrics:
    p = ROBOT_PROFILES.get(robot, ROBOT_PROFILES["estandar"])
    return RouteMetrics(
        distance_m=m.distance_m,
        weighted_cost=m.weighted_cost,
        time_min=round(m.time_min / p["speed"], 2),
        energy_kwh=round(m.energy_kwh * p["energy"], 4),
        avg_congestion=m.avg_congestion,
        hops=m.hops,
    )


def fig_to_b64(fig: plt.Figure) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=90, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def _nearest_despacho(g, origin: int) -> int:
    import networkx as nx

    candidates = [n for n, d in g.nodes(data=True) if d["tipo"] == "DESPACHO"]
    if not candidates:
        raise ValueError("No hay muelles de despacho en el almacén.")
    return min(
        candidates,
        key=lambda n: nx.shortest_path_length(g, origin, n, weight="distancia"),
    )


def _nearest_almacen(g, dest: int) -> int:
    import networkx as nx

    candidates = [n for n, d in g.nodes(data=True) if d["tipo"] == "ALMACEN"]
    if not candidates:
        raise ValueError("No hay estantes de almacén.")
    return min(
        candidates,
        key=lambda n: nx.shortest_path_length(g, n, dest, weight="distancia"),
    )


def normalize_route_endpoints(origin: int, dest: int) -> tuple[int, int, dict]:
    """Ajusta origen/destino a estante → muelle cuando el usuario se equivoca."""
    meta: dict = {"swapped": False, "auto_dest": False, "auto_origin": False}
    orig_pre = nodo_detalle(_BASE_GRAPH, origin)
    dest_pre = nodo_detalle(_BASE_GRAPH, dest)

    if orig_pre["tipo"] == "DESPACHO" and dest_pre["tipo"] == "ALMACEN":
        origin, dest = dest, origin
        orig_pre, dest_pre = dest_pre, orig_pre
        meta["swapped"] = True

    if orig_pre["tipo"] not in ("ALMACEN", "INTERSECCION", "RECARGA"):
        try:
            origin = _nearest_almacen(_BASE_GRAPH, dest)
            orig_pre = nodo_detalle(_BASE_GRAPH, origin)
            meta["auto_origin"] = True
        except (ValueError, Exception):
            return origin, dest, {"error": "El origen debe ser un estante (ALMACEN). Busque por producto o nodo."}

    if dest_pre["tipo"] != "DESPACHO":
        try:
            dest = _nearest_despacho(_BASE_GRAPH, origin)
            meta["auto_dest"] = True
        except (ValueError, Exception):
            return origin, dest, {"error": "El destino debe ser un muelle de despacho."}

    return origin, dest, meta


def _build_route_payload(
    g,
    *,
    origin: int,
    dest: int,
    franja: str,
    robot: str,
    norm: dict,
    include_image: bool,
    include_mst: bool,
    session_id: str,
) -> dict:
    bfs = bfs_path(g, origin, dest)
    dij = dijkstra_path(g, origin, dest)
    bf = bellman_ford_path(g, origin, dest)

    if not dij.ok:
        return {"ok": False, "error": dij.msg}

    mb = _apply_robot(path_metrics(g, bfs.path), robot)
    md = _apply_robot(path_metrics(g, dij.path), robot)
    save = savings_pct(mb.weighted_cost, md.weighted_cost)
    perfil = ROBOT_PROFILES[robot]

    algorithms: dict = {
        "bfs": {"cost": round(bfs.cost, 2), "ms": round(bfs.elapsed_ms, 2), "hops": len(bfs.path)},
        "dijkstra": {"cost": round(dij.cost, 2), "ms": round(dij.elapsed_ms, 2), "hops": len(dij.path)},
        "bellman_ford": {
            "cost": round(bf.cost, 2),
            "ms": round(bf.elapsed_ms, 2),
            "hops": len(bf.path),
            "valid": abs(bf.cost - dij.cost) < 0.1,
        },
    }

    if include_mst:
        mst_e, mst_c, mst_ms = prim_mst(g)
        _, krus_c, krus_ms = kruskal_mst(g)
        algorithms["prim_mst"] = {"cost": round(mst_c, 2), "ms": round(mst_ms, 2), "edges": len(mst_e)}
        algorithms["kruskal_mst"] = {"cost": round(krus_c, 2), "ms": round(krus_ms, 2)}

    map_b64 = ""
    if include_image:
        img_key = f"{session_id}|{origin}|{dest}|{franja}|{robot}|{_closed_fingerprint(session_id)}"
        if img_key in _ROUTE_IMG_CACHE:
            map_b64 = _ROUTE_IMG_CACHE[img_key]
        else:
            fig = plot_warehouse(
                g,
                origin=origin,
                destination=dest,
                dijk_path=dij.path,
                bfs_path=bfs.path,
                title=f"{md.time_min} min · {md.distance_m} m · {perfil['label']}",
            )
            map_b64 = fig_to_b64(fig)
            _ROUTE_IMG_CACHE[img_key] = map_b64
            _trim_cache(_ROUTE_IMG_CACHE)

    orig_det = nodo_detalle(g, origin)
    dest_det = nodo_detalle(g, dest)
    explicacion = explicar_ruta(
        franja=franja,
        save_pct=save,
        mb=asdict(mb),
        md=asdict(md),
        robot=robot,
    )
    pasillos_ruta = _CATALOG.pasillos_en_camino(g, dij.path, franja)

    routes_match = abs(bfs.cost - dij.cost) < 0.05 and bfs.path == dij.path

    return {
        "ok": True,
        "origin": origin,
        "dest": dest,
        "franja": franja,
        "robot": robot,
        "robot_label": perfil["label"],
        "map_image": map_b64,
        "dijk_path": dij.path,
        "bfs_path": bfs.path,
        "routes_match": routes_match,
        "preview": not include_image,
        "metrics": {
            "dijkstra": asdict(md),
            "bfs": asdict(mb),
            "savings_pct": save,
        },
        "explicacion": explicacion,
        "pasillos_ruta": pasillos_ruta,
        "normalizacion": norm,
        "origen": orig_det,
        "destino": dest_det,
        "algorithms": algorithms,
        "complexity": ALGO_COMPLEXITY,
    }


def calculate_route(
    session_id: str,
    origin: int,
    dest: int,
    franja: str,
    robot: str = "estandar",
    *,
    include_image: bool = True,
    include_mst: bool = True,
) -> dict:
    origin = max(0, min(NODE_COUNT - 1, int(origin)))
    dest = max(0, min(NODE_COUNT - 1, int(dest)))
    robot = robot if robot in ROBOT_PROFILES else "estandar"
    franja = franja if franja in ("baja", "media", "alta") else "alta"

    if origin == dest:
        return {"ok": False, "error": "El punto de recogida y el de entrega deben ser distintos."}

    origin, dest, norm = normalize_route_endpoints(origin, dest)
    if norm.get("error"):
        return {"ok": False, "error": norm["error"]}

    g = prepare_graph(franja, session_id)
    if not check_connectivity_ufds(g, origin, dest):
        return {"ok": False, "error": "No hay ruta disponible entre origen y destino."}

    result = _build_route_payload(
        g,
        origin=origin,
        dest=dest,
        franja=franja,
        robot=robot,
        norm=norm,
        include_image=include_image,
        include_mst=include_mst,
        session_id=session_id,
    )
    if result.get("ok") and include_image:
        _push_history(
            session_id,
            {
                "origin": result["origin"],
                "dest": result["dest"],
                "franja": franja,
                "robot": robot,
                "label": f"{result['origen']['ubicacion']} → {result['destino']['ubicacion']}",
                "savings_pct": result["metrics"]["savings_pct"],
            },
        )
        result["history"] = list(_HISTORY.get(session_id, []))
    return result


def calculate_route_preview(session_id: str, origin: int, dest: int, franja: str, robot: str = "estandar") -> dict:
    return calculate_route(
        session_id,
        origin,
        dest,
        franja,
        robot,
        include_image=False,
        include_mst=False,
    )


def run_validation_cases() -> list[dict]:
    """Casos CP para documentación y pruebas."""
    cases = [
        {"id": "CP-01", "origin": 101, "dest": 0, "franja": "baja", "robot": "estandar"},
        {"id": "CP-02", "origin": 0, "dest": 1499, "franja": "alta", "robot": "estandar"},
        {"id": "CP-03", "origin": 437, "dest": 12, "franja": "media", "robot": "estandar"},
        {"id": "CP-04", "origin": 250, "dest": 48, "franja": "alta", "robot": "express"},
        {"id": "CP-05", "origin": 800, "dest": 800, "franja": "alta", "robot": "estandar"},
        {"id": "CP-06", "origin": 600, "dest": 5, "franja": "alta", "robot": "pesado"},
        {"id": "CP-07", "origin": 101, "dest": 0, "franja": "alta", "robot": "estandar"},
        {"id": "CP-08", "origin": 0, "dest": 1499, "franja": "baja", "robot": "refrigerado"},
    ]
    rows = []
    for c in cases:
        r = calculate_route(
            "__validation__",
            c["origin"],
            c["dest"],
            c["franja"],
            c["robot"],
            include_image=False,
            include_mst=(c["id"] == "CP-04"),
        )
        row = {**c, "ok": r.get("ok"), "error": r.get("error")}
        if r.get("ok"):
            md = r["metrics"]["dijkstra"]
            mb = r["metrics"]["bfs"]
            row.update({
                "dijk_cost": md["weighted_cost"],
                "bfs_cost": mb["weighted_cost"],
                "save_pct": r["metrics"]["savings_pct"],
                "dijk_ms": r["algorithms"]["dijkstra"]["ms"],
                "bfs_ms": r["algorithms"]["bfs"]["ms"],
                "routes_match": r.get("routes_match"),
                "dijk_cong": md["avg_congestion"],
                "bfs_cong": mb["avg_congestion"],
            })
            if c["id"] == "CP-04" and "prim_mst" in r["algorithms"]:
                row["mst_edges"] = r["algorithms"]["prim_mst"]["edges"]
        rows.append(row)
    return rows


def _describe_edge(g, u: int, v: int) -> dict:
    du, dv = g.nodes[u], g.nodes[v]
    ed = g[u][v]
    tipo = ed.get("tipo_pasillo", "SECUNDARIO")
    sectors = sorted({du.get("sector", "?"), dv.get("sector", "?")})
    sector_str = " · ".join(sectors)
    if du.get("col") == dv.get("col"):
        pasillo = pasillo_label(du["sector"], du["col"])
        pasillo_id_str = pasillo_id(du["sector"], du["col"])
    elif du.get("row") == dv.get("row"):
        pasillo = f"Corredor horizontal · Sectores {sector_str} · Fila {du.get('row')}"
        pasillo_id_str = f"CORR-H-{u}-{v}"
    else:
        pasillo = f"Corredor vertical · Sectores {sector_str} · Col {du.get('col')}"
        pasillo_id_str = f"CORR-V-{u}-{v}"
    return {
        "nodos": f"{u}–{v}",
        "pasillo": pasillo,
        "pasillo_id": pasillo_id_str,
        "tipo": tipo,
        "peso": round(ed.get("peso", 0), 2),
        "congestion": round(ed.get("factor_congestion", 1), 2),
        "distancia_m": round(ed.get("distancia", 0), 2),
        "sector": sector_str,
    }


def infra_critical_passages(session_id: str, franja: str, limit: int = 18) -> dict:
    """Lista en texto los pasillos críticos: estructurales (MST) y más congestionados."""
    g = prepare_graph(franja, session_id)
    pe, pc, ms = prim_mst(g)
    _, kc, _ = kruskal_mst(g)

    mst_items: list[dict] = []
    for u, v in pe:
        item = _describe_edge(g, u, v)
        item["motivo"] = (
            "Forma parte del MST (árbol de expansión mínima): "
            "si se cierra, puede desconectar zonas del almacén."
        )
        mst_items.append(item)
    mst_items.sort(key=lambda x: x["peso"], reverse=True)

    cong_items: list[dict] = []
    for u, v, d in g.edges(data=True):
        if d.get("tipo_pasillo") not in ("PRINCIPAL", "ACCESO_DESPACHO"):
            continue
        item = _describe_edge(g, u, v)
        item["motivo"] = (
            f"Corredor {item['tipo']} con congestión {item['congestion']}× "
            f"en franja {franja} — Dijkstra intenta evitarlo en hora pico."
        )
        cong_items.append(item)
    cong_items.sort(key=lambda x: (x["congestion"], x["peso"]), reverse=True)

    franja_txt = {"baja": "tranquila", "media": "normal", "alta": "hora pico"}.get(franja, franja)
    resumen = (
        f"Pasillos críticos en franja {franja_txt}: "
        f"hay {len(pe)} conexiones estructurales (MST) que sostienen la red del almacén "
        f"y {len(cong_items)} corredores principales con alta congestión. "
        f"A continuación se listan los más relevantes (sin mapa)."
    )

    return {
        "ok": True,
        "franja": franja,
        "resumen": resumen,
        "mst": {
            "aristas": len(pe),
            "costo_prim": round(pc, 2),
            "costo_kruskal": round(kc, 2),
            "validacion_ok": abs(pc - kc) < 0.01,
            "ms": round(ms, 2),
        },
        "estructurales": mst_items[:limit],
        "congestionados": cong_items[:limit],
        "total_estructurales": len(pe),
        "total_congestionados": len(cong_items),
    }


def infra_mst(session_id: str, franja: str) -> dict:
    """Estadísticas MST — usar infra_critical_passages para el listado completo."""
    data = infra_critical_passages(session_id, franja, limit=0)
    m = data["mst"]
    return {
        "ok": True,
        "message": f"MST: {m['aristas']} aristas · Prim: {m['costo_prim']:.2f} · Kruskal: {m['costo_kruskal']:.2f} · "
        f"{'Validación OK' if m['validacion_ok'] else 'Difieren'}",
        "prim_cost": m["costo_prim"],
        "kruskal_cost": m["costo_kruskal"],
        "edges": m["aristas"],
        "ms": m["ms"],
    }


def infra_close_passage(session_id: str, franja: str) -> dict:
    g = prepare_graph(franja, session_id)
    pe, _, _ = prim_mst(g)
    if not pe:
        return {"ok": False, "error": "No se encontraron aristas MST."}
    u, v = pe[0]
    closed = _closed(session_id)
    closed.add((u, v))
    closed.add((v, u))
    _ROUTE_IMG_CACHE.clear()
    g2 = prepare_graph(franja, session_id)
    hubs = sector_hub_nodes(g2)
    ok = check_connectivity_ufds(g2, hubs["A"], hubs["DESPACHO"])
    return {
        "ok": True,
        "message": f"Pasillo {u}–{v} cerrado. Sector A → Despacho: {'Conectado' if ok else 'DESCONECTADO'}",
        "connected": ok,
        "closed_count": len(closed) // 2,
    }


def infra_reset(session_id: str) -> dict:
    _SESSION[session_id] = set()
    _ROUTE_IMG_CACHE.clear()
    return {"ok": True, "message": "Pasillos restaurados."}


def infra_floyd(session_id: str, franja: str) -> dict:
    g = prepare_graph(franja, session_id)
    matrix, ms = floyd_warshall_hubs(g, sector_hub_nodes(g))
    rows = []
    for a, cols in matrix.items():
        row = {"desde": a}
        for b, val in cols.items():
            row[b] = None if val == float("inf") else round(val, 1)
        rows.append(row)
    return {"ok": True, "matrix": rows, "ms": round(ms, 2)}
