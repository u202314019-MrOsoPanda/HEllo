"""Servidor web SmartRoute WMS — Flask + HTML."""

from __future__ import annotations

import logging
import os
import secrets
import sys
import traceback
from pathlib import Path

from flask import Flask, jsonify, render_template, request, session

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import service

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("smartroute")

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "smartroute-wms-dev-key-2026")


@app.errorhandler(Exception)
def handle_unexpected_error(exc):
    log.error("Error no controlado: %s\n%s", exc, traceback.format_exc())
    return jsonify({"ok": False, "error": str(exc)}), 500


@app.after_request
def no_cache_static(resp):
    if request.path.startswith("/static/"):
        resp.headers["Cache-Control"] = "no-cache"
    return resp


def _sid() -> str:
    if "sid" not in session:
        session["sid"] = secrets.token_hex(8)
    return session["sid"]


@app.route("/")
def index():
    return render_template("index.html")


@app.get("/api/productos")
def api_productos():
    q = request.args.get("q", "")
    limit = min(120, int(request.args.get("limit", 60)))
    offset = max(0, int(request.args.get("offset", 0)))
    return jsonify(service.list_products(q=q, limit=limit, offset=offset))


@app.get("/api/health")
def api_health():
    try:
        return jsonify(service.health_check())
    except Exception as exc:
        log.exception("health failed")
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.get("/api/defaults")
def api_defaults():
    return jsonify(service.get_defaults())


@app.get("/api/search")
def api_search():
    q = request.args.get("q", "")
    tipo = request.args.get("tipo", "all")
    limit = min(50, int(request.args.get("limit", 25)))
    return jsonify(service.search_inventory(q, tipo=tipo, limit=limit))


@app.get("/api/pasillos")
def api_pasillos():
    limit = min(120, int(request.args.get("limit", 80)))
    return jsonify(service.list_aisles(limit=limit))


@app.get("/api/pasillo")
def api_pasillo():
    nodo = request.args.get("nodo")
    if nodo is not None:
        return jsonify(service.get_aisle_by_node(int(nodo)))
    sector = request.args.get("sector", "")
    letra = request.args.get("letra", "")
    if sector and letra:
        return jsonify(service.get_aisle(sector, letra))
    return jsonify({"ok": False, "error": "Indique ?sector=A&letra=B o ?nodo=123"})


@app.get("/api/stats")
def api_stats():
    return jsonify(service.get_stats())


@app.get("/api/robots")
def api_robots():
    return jsonify(service.get_robots())


@app.get("/api/random-route")
def api_random_route():
    return jsonify(service.random_route())


@app.get("/api/map/layout")
def api_map_layout():
    return jsonify(service.get_map_layout())


@app.get("/api/history")
def api_history():
    return jsonify(service.get_route_history(_sid()))


@app.get("/api/validation")
def api_validation():
    return jsonify({"ok": True, "cases": service.run_validation_cases()})


@app.get("/api/node/<int:nid>")
def api_node(nid: int):
    return jsonify(service.get_node_info(nid))


@app.post("/api/route")
def api_route():
    data = request.get_json(force=True) or {}
    try:
        result = service.calculate_route(
            _sid(),
            data.get("origin", 0),
            data.get("dest", 1499),
            data.get("franja", "alta"),
            data.get("robot", "estandar"),
        )
        return jsonify(result)
    except Exception as exc:
        log.exception("route failed")
        return jsonify({"ok": False, "error": f"Error interno: {exc}"}), 500


@app.post("/api/route/preview")
def api_route_preview():
    data = request.get_json(force=True) or {}
    try:
        result = service.calculate_route_preview(
            _sid(),
            data.get("origin", 0),
            data.get("dest", 1499),
            data.get("franja", "alta"),
            data.get("robot", "estandar"),
        )
        return jsonify(result)
    except Exception as exc:
        log.exception("preview failed")
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.post("/api/infra/mst")
def api_mst():
    data = request.get_json(force=True) or {}
    return jsonify(service.infra_mst(_sid(), data.get("franja", "alta")))


@app.post("/api/infra/critical")
def api_critical():
    data = request.get_json(force=True) or {}
    limit = min(30, int(data.get("limit", 18)))
    return jsonify(service.infra_critical_passages(_sid(), data.get("franja", "alta"), limit=limit))


@app.post("/api/infra/close")
def api_close():
    data = request.get_json(force=True) or {}
    return jsonify(service.infra_close_passage(_sid(), data.get("franja", "alta")))


@app.post("/api/infra/reset")
def api_reset():
    return jsonify(service.infra_reset(_sid()))


@app.post("/api/infra/floyd")
def api_floyd():
    data = request.get_json(force=True) or {}
    return jsonify(service.infra_floyd(_sid(), data.get("franja", "alta")))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
