"""Generación rápida de gráficos para la app web."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import networkx as nx

from src import tema as T


def plot_warehouse(
    g: nx.Graph,
    *,
    origin: int | None = None,
    destination: int | None = None,
    dijk_path: list[int] | None = None,
    bfs_path: list[int] | None = None,
    mst_edges: list[tuple[int, int]] | None = None,
    title: str = "Mapa del almacén",
) -> plt.Figure:
    pos = {n: (d["x"], d["y"]) for n, d in g.nodes(data=True)}
    fig, ax = plt.subplots(figsize=(11, 5.5), facecolor=T.BG_DARK)
    ax.set_facecolor(T.BG_DARK)

    # Fondo: muestra de nodos (rápido) en lugar de todas las aristas
    sample = list(g.nodes)[::3]
    ax.scatter(
        [pos[n][0] for n in sample],
        [pos[n][1] for n in sample],
        c="#3d2a5c",
        s=4,
        alpha=0.5,
        zorder=1,
    )

    if mst_edges:
        for u, v in mst_edges[:400]:
            if u in pos and v in pos:
                x1, y1 = pos[u]
                x2, y2 = pos[v]
                ax.plot([x1, x2], [y1, y2], color=T.ROUTE_MST, linewidth=0.7, alpha=0.5, zorder=2)

    if bfs_path and len(bfs_path) > 1:
        xs = [pos[n][0] for n in bfs_path if n in pos]
        ys = [pos[n][1] for n in bfs_path if n in pos]
        ax.plot(xs, ys, color=T.ROUTE_BFS, linewidth=2.0, linestyle="--", label="Ruta directa", zorder=4)

    if dijk_path and len(dijk_path) > 1:
        xs = [pos[n][0] for n in dijk_path if n in pos]
        ys = [pos[n][1] for n in dijk_path if n in pos]
        ax.plot(xs, ys, color=T.ROUTE_DIJK, linewidth=2.4, label="Ruta recomendada", zorder=5)

    if origin is not None and origin in pos:
        ax.scatter(*pos[origin], c=T.ORIGIN_COLOR, s=120, marker="s", edgecolors="white", linewidths=1, zorder=6)
    if destination is not None and destination in pos:
        ax.scatter(*pos[destination], c=T.DEST_COLOR, s=140, marker="*", edgecolors="white", linewidths=1, zorder=6)

    ax.set_title(title, color=T.GREEN_MAIN, fontsize=12, pad=10)
    ax.tick_params(colors=T.TEXT_MUTED, labelsize=6)
    for spine in ax.spines.values():
        spine.set_color(T.PURPLE_MAIN)
    if dijk_path or bfs_path:
        ax.legend(facecolor=T.BG_CARD, edgecolor=T.PURPLE_MAIN, labelcolor=T.TEXT_PRIMARY, fontsize=8, loc="upper right")
    ax.set_aspect("equal", adjustable="box")
    fig.tight_layout()
    return fig
