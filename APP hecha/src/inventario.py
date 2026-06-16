"""Inventario sintético y perfiles de robots AGV."""

from __future__ import annotations

import random

from src.grafo import NODE_COUNT, SECTORS, node_row_col

PRODUCTOS = [
    "Laptop Pro 15\"", "Monitor 27\"", "Teclado mecánico", "Mouse inalámbrico",
    "SSD 1TB", "Router Wi-Fi 6", "Auriculares BT", "Webcam 4K",
    "Tablet 11\"", "Hub USB-C", "Impresora láser", "Disco externo 2TB",
]

PRODUCTO_ICONOS = {
    "laptop": "💻", "monitor": "🖥️", "teclado": "⌨️", "mouse": "🖱️",
    "ssd": "💾", "router": "📡", "auriculares": "🎧", "webcam": "📷",
    "tablet": "📱", "hub": "🔌", "impresora": "🖨️", "disco": "💿",
}


def icono_producto(nombre: str) -> str:
    nl = nombre.lower()
    for clave, icono in PRODUCTO_ICONOS.items():
        if clave in nl:
            return icono
    return "📦"

ROBOT_PROFILES = {
    "estandar": {
        "label": "AGV Estándar",
        "icon": "🤖",
        "speed": 1.0,
        "energy": 1.0,
        "desc": "Equilibrio entre velocidad y consumo. Uso general en pasillos.",
    },
    "pesado": {
        "label": "AGV Carga pesada",
        "icon": "📦",
        "speed": 0.82,
        "energy": 1.25,
        "desc": "Para pallets y productos frágiles. Prioriza pasillos menos congestionados.",
    },
    "express": {
        "label": "AGV Express",
        "icon": "⚡",
        "speed": 1.22,
        "energy": 1.12,
        "desc": "Despachos urgentes. Más rápido, mayor consumo energético.",
    },
    "refrigerado": {
        "label": "AGV Refrigerado",
        "icon": "❄️",
        "speed": 0.9,
        "energy": 1.35,
        "desc": "Componentes sensibles a temperatura. Rutas cortas y estables.",
    },
}


def ubicacion_legible(nid: int, sector: str, row: int, col: int, tipo: str) -> str:
    nivel = (row % 4) + 1
    pasillo = chr(65 + (col % 26))
    tipo_txt = {
        "ALMACEN": "Estante",
        "DESPACHO": "Muelle despacho",
        "RECARGA": "Estación recarga",
        "INTERSECCION": "Cruce pasillos",
    }.get(tipo, tipo)
    return f"Sector {sector} · {tipo_txt} {pasillo}{nivel} · Fila {row + 1}, Col {col + 1}"


def stock_en_nodo(nid: int, sector: str) -> dict:
    """Stock sintético determinista por nodo."""
    nid = max(0, min(NODE_COUNT - 1, nid))
    base = (nid * 17 + ord(sector[0]) * 31) % 97
    unidades = 5 + (base % 80)
    reservado = min(unidades - 1, base % 12)
    disponible = max(1, unidades - reservado)
    return {
        "sku": f"SKU-{nid:05d}",
        "producto": PRODUCTOS[nid % len(PRODUCTOS)],
        "unidades": unidades,
        "disponible": disponible,
        "reservado": reservado,
        "estado": "OK" if unidades > 15 else ("BAJO" if unidades > 5 else "CRITICO"),
    }


def nodo_detalle(g, nid: int) -> dict:
    nid = max(0, min(NODE_COUNT - 1, nid))
    d = g.nodes[nid]
    stock = stock_en_nodo(nid, d["sector"])
    return {
        "id": nid,
        "sector": d["sector"],
        "tipo": d["tipo"],
        "row": d["row"],
        "col": d["col"],
        "x_m": round(d["x"], 1),
        "y_m": round(d["y"], 1),
        "ubicacion": ubicacion_legible(nid, d["sector"], d["row"], d["col"], d["tipo"]),
        "stock": stock,
    }


def random_picking_despacho(g) -> dict:
    """Origen en estante (ALMACEN) y destino en despacho."""
    almacen = [n for n, d in g.nodes(data=True) if d["tipo"] == "ALMACEN"]
    despacho = [n for n, d in g.nodes(data=True) if d["tipo"] == "DESPACHO"]
    if not almacen or not despacho:
        return {"origin": 0, "dest": min(NODE_COUNT - 1, 50)}
    for _ in range(20):
        o, d = random.choice(almacen), random.choice(despacho)
        if o != d:
            return {"origin": o, "dest": d}
    return {"origin": almacen[0], "dest": despacho[0]}


def explicar_ruta(
    *,
    franja: str,
    save_pct: float,
    mb: dict,
    md: dict,
    robot: str,
) -> dict:
    """Explicación en lenguaje de operador: ¿por qué SÍ esta ruta?"""
    perfil = ROBOT_PROFILES.get(robot, ROBOT_PROFILES["estandar"])
    razones_si = []
    razones_no_directa = []

    if save_pct > 0:
        razones_si.append(f"Ahorra <strong>{save_pct}%</strong> de costo frente a ir directo.")
    if md["avg_congestion"] < mb["avg_congestion"]:
        razones_si.append(
            f"Menos tráfico en pasillos: <strong>{md['avg_congestion']}</strong> vs "
            f"<strong>{mb['avg_congestion']}</strong> en la ruta directa."
        )
    if md["energy_kwh"] < mb["energy_kwh"]:
        razones_si.append(
            f"Menor consumo estimado: <strong>{md['energy_kwh']} kWh</strong> "
            f"(directa: {mb['energy_kwh']} kWh)."
        )
    if md["time_min"] <= mb["time_min"]:
        razones_si.append(f"Llega en <strong>{md['time_min']} min</strong> (óptimo para {perfil['label']}).")
    else:
        razones_si.append(
            f"Recorre más metros pero compensa con menos congestión en hora {franja}."
        )

    if perfil["speed"] != 1.0:
        razones_si.append(
            f"Perfil <strong>{perfil['label']}</strong>: {perfil['desc']}"
        )

    if mb["distance_m"] < md["distance_m"]:
        razones_no_directa.append(
            f"La ruta directa parece más corta ({mb['distance_m']} m), pero pasa por pasillos más saturados."
        )
    if mb["avg_congestion"] > md["avg_congestion"]:
        razones_no_directa.append("En hora pico, el camino con menos saltos no es el más rápido ni el más barato.")

    recomendar = save_pct > 0 or md["avg_congestion"] < mb["avg_congestion"]
    veredicto = "SÍ — use la ruta verde (recomendada)" if recomendar else "Revise — condiciones similares"

    return {
        "recomendar": recomendar,
        "veredicto": veredicto,
        "razones_si": razones_si or ["Ruta válida y conectada en el almacén."],
        "razones_no_directa": razones_no_directa or ["La ruta directa es viable pero menos eficiente operativamente."],
        "robot": perfil["label"],
    }
