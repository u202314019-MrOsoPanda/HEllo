"""Pruebas de lógica SmartRoute WMS (ejecutar: py -3 -m pytest tests/ -q)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.service import (  # noqa: E402
    calculate_route,
    calculate_route_preview,
    get_map_layout,
    health_check,
    infra_close_passage,
    infra_critical_passages,
    infra_mst,
    infra_reset,
    normalize_route_endpoints,
    run_validation_cases,
    search_inventory,
)
from server import app  # noqa: E402


def test_destino_nodo_cero():
    r = calculate_route("test", 101, 0, "alta")
    assert r["ok"] is True
    assert r["dest"] == 0
    assert r["dijk_path"]
    assert r["bfs_path"]


def test_intercambio_origen_destino():
    r = calculate_route("test", 0, 1499, "alta")
    assert r["ok"] is True
    assert r["normalizacion"]["swapped"] is True


def test_busqueda_producto():
    s = search_inventory("SSD", tipo="producto")
    assert s["ok"] is True
    assert s["count"] > 0


def test_api_route_y_mst():
    c = app.test_client()
    route = c.post("/api/route", json={"origin": 101, "dest": 0, "franja": "alta", "robot": "estandar"})
    assert route.status_code == 200
    assert route.json["ok"] is True
    assert route.json["map_image"]
    assert route.json["dijk_path"]

    mst = c.post("/api/infra/mst", json={"franja": "alta"})
    assert mst.status_code == 200
    assert mst.json["ok"] is True
    assert isinstance(mst.json["kruskal_cost"], (int, float))


def test_health():
    h = health_check()
    assert h["ok"] is True
    assert h["nodes"] == 1500
    assert "complexity" in h


def test_map_layout():
    layout = get_map_layout()
    assert layout["ok"] is True
    assert len(layout["nodes"]) == 1500


def test_route_preview_sin_imagen():
    r = calculate_route_preview("test-prev", 101, 0, "alta")
    assert r["ok"] is True
    assert r["preview"] is True
    assert not r["map_image"]
    assert "prim_mst" not in r["algorithms"]


def test_franja_baja():
    r = calculate_route("test-baja", 101, 0, "baja", include_image=False)
    assert r["ok"] is True


def test_franja_media():
    r = calculate_route("test-media", 437, 12, "media", include_image=False)
    assert r["ok"] is True


def test_origen_igual_destino():
    r = calculate_route("test", 500, 500, "alta")
    assert r["ok"] is False


def test_api_preview_endpoint():
    c = app.test_client()
    res = c.post("/api/route/preview", json={"origin": 101, "dest": 0, "franja": "alta"})
    assert res.status_code == 200
    assert res.json["ok"] is True
    assert res.json["preview"] is True


def test_api_map_layout():
    c = app.test_client()
    res = c.get("/api/map/layout")
    assert res.status_code == 200
    assert len(res.json["nodes"]) == 1500


def test_infra_critical_list():
    data = infra_critical_passages("test-crit", "alta", limit=5)
    assert data["ok"] is True
    assert data["total_estructurales"] == 1499
    assert len(data["estructurales"]) == 5
    assert len(data["congestionados"]) >= 1
    assert "pasillo" in data["estructurales"][0]


def test_api_critical_endpoint():
    c = app.test_client()
    res = c.post("/api/infra/critical", json={"franja": "alta", "limit": 8})
    assert res.status_code == 200
    assert res.json["ok"] is True
    assert res.json["estructurales"]


def test_infra_close_y_reset():
    sid = "test-infra"
    infra_reset(sid)
    m = infra_mst(sid, "alta")
    assert m["ok"] is True
    c = infra_close_passage(sid, "alta")
    assert c["ok"] is True
    infra_reset(sid)


def test_validation_cases():
    rows = run_validation_cases()
    assert len(rows) >= 8
    ok_rows = [r for r in rows if r.get("ok")]
    assert len(ok_rows) >= 6
    cp05 = next(r for r in rows if r["id"] == "CP-05")
    assert cp05["ok"] is False


def test_normalize_endpoints():
    o, d, meta = normalize_route_endpoints(0, 1499)
    assert meta["swapped"] is True
