"""Métricas operativas para el operador."""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

AGV_SPEED = 1.5
ENERGY_TIME = 0.05
ENERGY_BRAKE = 0.02


@dataclass
class RouteMetrics:
    distance_m: float
    weighted_cost: float
    time_min: float
    energy_kwh: float
    avg_congestion: float
    hops: int


def path_distance(g: nx.Graph, path: list[int]) -> float:
    return sum(g[u][v].get("distancia", 0) for u, v in zip(path, path[1:]))


def path_metrics(g: nx.Graph, path: list[int]) -> RouteMetrics:
    if len(path) < 2:
        return RouteMetrics(0, 0, 0, 0, 0, len(path))
    dist = path_distance(g, path)
    cost = sum(g[u][v].get("peso", 0) for u, v in zip(path, path[1:]))
    congestions = [g[u][v].get("factor_congestion", 1.0) for u, v in zip(path, path[1:])]
    time_s = cost / AGV_SPEED
    brakes = max(0, len(path) - 2)
    energy = ENERGY_TIME * time_s + ENERGY_BRAKE * brakes
    return RouteMetrics(
        distance_m=round(dist, 2),
        weighted_cost=round(cost, 2),
        time_min=round(time_s / 60, 2),
        energy_kwh=round(energy, 4),
        avg_congestion=round(sum(congestions) / len(congestions), 2),
        hops=len(path),
    )


def savings_pct(bfs_cost: float, dijk_cost: float) -> float:
    if bfs_cost <= 0:
        return 0.0
    return round((bfs_cost - dijk_cost) / bfs_cost * 100, 1)
