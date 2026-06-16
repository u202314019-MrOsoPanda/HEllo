#!/usr/bin/env python3
"""Genera tabla markdown de casos de prueba CP para el README."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.service import run_validation_cases  # noqa: E402


def main() -> None:
    rows = run_validation_cases()
    print("| Caso | Origen | Destino | Franja | OK | Ahorro % | Dijkstra ms | BFS ms | Coinciden |")
    print("|------|--------|---------|--------|-----|----------|-------------|--------|-----------|")
    for r in rows:
        if not r.get("ok"):
            print(
                f"| {r['id']} | {r['origin']} | {r['dest']} | {r['franja']} | NO | — | — | — | {r.get('error', 'error')} |"
            )
            continue
        match = "Si" if r.get("routes_match") else "No"
        print(
            f"| {r['id']} | {r['origin']} | {r['dest']} | {r['franja']} | SI | "
            f"{r.get('save_pct', '—')} | {r.get('dijk_ms', '—')} | {r.get('bfs_ms', '—')} | {match} |"
        )


if __name__ == "__main__":
    main()
