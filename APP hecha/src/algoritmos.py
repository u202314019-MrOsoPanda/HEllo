"""Algoritmos: BFS, Dijkstra, Bellman-Ford, Prim, Kruskal, UFDS, Floyd-Warshall."""

from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx


@dataclass
class RouteResult:
    name: str
    path: list[int] = field(default_factory=list)
    cost: float = 0.0
    ok: bool = True
    msg: str = ""
    elapsed_ms: float = 0.0


class UFDS:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> bool:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1
        return True

    def connected(self, a: int, b: int) -> bool:
        return self.find(a) == self.find(b)


def bfs_path(g: nx.Graph, s: int, t: int) -> RouteResult:
    import time

    t0 = time.perf_counter()
    try:
        if not nx.has_path(g, s, t):
            return RouteResult("BFS", ok=False, msg="No hay ruta disponible.")
        path = nx.shortest_path(g, s, t)
        cost = sum(g[u][v].get("peso", 1) for u, v in zip(path, path[1:]))
        ms = (time.perf_counter() - t0) * 1000
        return RouteResult("BFS", path=path, cost=cost, elapsed_ms=ms)
    except nx.NetworkXNoPath:
        return RouteResult("BFS", ok=False, msg="No hay ruta disponible.")


def dijkstra_path(g: nx.Graph, s: int, t: int) -> RouteResult:
    import time

    t0 = time.perf_counter()
    try:
        path = nx.shortest_path(g, s, t, weight="peso")
        cost = nx.shortest_path_length(g, s, t, weight="peso")
        ms = (time.perf_counter() - t0) * 1000
        return RouteResult("Dijkstra", path=path, cost=cost, elapsed_ms=ms)
    except nx.NetworkXNoPath:
        return RouteResult("Dijkstra", ok=False, msg="No hay ruta disponible.")


def bellman_ford_path(g: nx.Graph, s: int, t: int) -> RouteResult:
    import time

    t0 = time.perf_counter()
    try:
        pred, dist = nx.bellman_ford_predecessor_and_distance(g, s, weight="peso")
        if t not in dist:
            return RouteResult("Bellman-Ford", ok=False, msg="Nodo inalcanzable.")
        path = [t]
        cur = t
        while cur != s:
            preds = pred.get(cur)
            if not preds:
                return RouteResult("Bellman-Ford", ok=False, msg="Sin camino.")
            cur = preds[0]
            path.append(cur)
        path.reverse()
        ms = (time.perf_counter() - t0) * 1000
        return RouteResult("Bellman-Ford", path=path, cost=dist[t], elapsed_ms=ms)
    except nx.NetworkXUnbounded:
        return RouteResult("Bellman-Ford", ok=False, msg="Ciclo negativo detectado.")


def prim_mst(g: nx.Graph) -> tuple[list[tuple[int, int]], float, float]:
    import time

    t0 = time.perf_counter()
    mst = nx.minimum_spanning_tree(g, weight="peso", algorithm="prim")
    edges = list(mst.edges())
    cost = sum(d.get("peso", 0) for _, _, d in mst.edges(data=True))
    ms = (time.perf_counter() - t0) * 1000
    return edges, cost, ms


def kruskal_mst(g: nx.Graph) -> tuple[list[tuple[int, int]], float, float]:
    import time

    t0 = time.perf_counter()
    mst = nx.minimum_spanning_tree(g, weight="peso", algorithm="kruskal")
    edges = list(mst.edges())
    cost = sum(d.get("peso", 0) for _, _, d in mst.edges(data=True))
    ms = (time.perf_counter() - t0) * 1000
    return edges, cost, ms


def floyd_warshall_hubs(g: nx.Graph, hubs: dict[str, int]) -> tuple[dict[str, dict[str, float]], float]:
    import time

    t0 = time.perf_counter()
    labels = list(hubs.keys())
    nodes = [hubs[k] for k in labels]
    sub = g.subgraph(nodes).copy()
    # Caminos mínimos entre hubs (subgrafo inducido; si no hay arista directa, usar camino en G completo)
    matrix: dict[str, dict[str, float]] = {a: {} for a in labels}
    for i, la in enumerate(labels):
        for j, lb in enumerate(labels):
            if i == j:
                matrix[la][lb] = 0.0
                continue
            try:
                matrix[la][lb] = nx.shortest_path_length(g, nodes[i], nodes[j], weight="peso")
            except nx.NetworkXNoPath:
                matrix[la][lb] = float("inf")
    ms = (time.perf_counter() - t0) * 1000
    return matrix, ms


def check_connectivity_ufds(g: nx.Graph, a: int, b: int) -> bool:
    uf = UFDS(g.number_of_nodes())
    for u, v in g.edges():
        uf.union(u, v)
    return uf.connected(a, b)
