"""Modelo del almacén — grafo 30×50 (1500 nodos)."""

from __future__ import annotations

import math

import networkx as nx
import numpy as np

ROWS, COLS = 30, 50
NODE_COUNT = ROWS * COLS
WIDTH_M, HEIGHT_M = 120.0, 80.0
SECTORS = ["A", "B", "C", "D", "E", "F", "G", "H"]


def node_id(row: int, col: int) -> int:
    return row * COLS + col


def node_row_col(nid: int) -> tuple[int, int]:
    return divmod(nid, COLS)


def build_graph(seed: int = 42) -> nx.Graph:
    rng = np.random.default_rng(seed)
    dispatch_cols = set(rng.choice(COLS, size=50, replace=False))
    recharge_cols = set(rng.choice(COLS, size=30, replace=False))

    g = nx.Graph()
    for row in range(ROWS):
        for col in range(COLS):
            nid = node_id(row, col)
            x = col * (WIDTH_M / (COLS - 1)) if COLS > 1 else 0
            y = row * (HEIGHT_M / (ROWS - 1)) if ROWS > 1 else 0
            if row <= 1 and col in dispatch_cols:
                tipo = "DESPACHO"
            elif row >= ROWS - 2 and col in recharge_cols:
                tipo = "RECARGA"
            elif row % 5 == 0 or col % 10 == 0:
                tipo = "INTERSECCION"
            else:
                tipo = "ALMACEN"
            sector_idx = min(7, (row // 8) * 4 + (col // 13))
            g.add_node(nid, x=x, y=y, tipo=tipo, sector=SECTORS[sector_idx], row=row, col=col)

    for row in range(ROWS):
        for col in range(COLS):
            u = node_id(row, col)
            for dr, dc in ((0, 1), (1, 0)):
                nr, nc = row + dr, col + dc
                if nr < ROWS and nc < COLS:
                    v = node_id(nr, nc)
                    du = g.nodes[u]["x"] - g.nodes[v]["x"]
                    dv = g.nodes[u]["y"] - g.nodes[v]["y"]
                    dist = math.hypot(du, dv)
                    if row % 5 == 0 or col % 10 == 0:
                        ptype = "PRINCIPAL"
                    elif g.nodes[u]["tipo"] == "DESPACHO" or g.nodes[v]["tipo"] == "DESPACHO":
                        ptype = "ACCESO_DESPACHO"
                    else:
                        ptype = "SECUNDARIO"
                    g.add_edge(u, v, distancia=round(dist, 3), tipo_pasillo=ptype, peso=dist)

    return g


def apply_traffic(g: nx.Graph, franja: str) -> None:
    table = {
        "baja": {"PRINCIPAL": 1.0, "SECUNDARIO": 1.0, "ACCESO_DESPACHO": 1.1},
        "media": {"PRINCIPAL": 2.0, "SECUNDARIO": 1.3, "ACCESO_DESPACHO": 1.8},
        "alta": {"PRINCIPAL": 4.5, "SECUNDARIO": 1.5, "ACCESO_DESPACHO": 3.5},
    }
    factors = table[franja]
    for u, v, d in g.edges(data=True):
        c = factors.get(d.get("tipo_pasillo", "SECUNDARIO"), 1.0)
        dist = d.get("distancia", 1.0)
        d["peso"] = round(dist * c, 4)
        d["factor_congestion"] = c


def sector_hub_nodes(g: nx.Graph) -> dict[str, int]:
    """Un nodo representativo por sector para Floyd-Warshall."""
    hubs: dict[str, int] = {}
    for sector in SECTORS:
        candidates = [n for n, d in g.nodes(data=True) if d["sector"] == sector and d["tipo"] == "INTERSECCION"]
        if not candidates:
            candidates = [n for n, d in g.nodes(data=True) if d["sector"] == sector]
        hubs[sector] = candidates[len(candidates) // 2]
    dispatch = [n for n, d in g.nodes(data=True) if d["tipo"] == "DESPACHO"]
    hubs["DESPACHO"] = dispatch[0] if dispatch else 0
    return hubs


def graph_stats(g: nx.Graph) -> dict:
    weights = [d.get("peso", 0) for _, _, d in g.edges(data=True)]
    congestions = [d.get("factor_congestion", 1.0) for _, _, d in g.edges(data=True)]
    return {
        "nodos": g.number_of_nodes(),
        "aristas": g.number_of_edges(),
        "peso_prom": round(sum(weights) / len(weights), 2) if weights else 0,
        "congestion_prom": round(sum(congestions) / len(congestions), 2) if congestions else 0,
    }
