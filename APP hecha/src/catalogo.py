"""Catálogo de inventario: búsqueda, pasillos y contenido."""

from __future__ import annotations

from src.grafo import NODE_COUNT
from src.inventario import PRODUCTOS, icono_producto, nodo_detalle, stock_en_nodo


def pasillo_letra(col: int) -> str:
    return chr(65 + (col % 26))


def pasillo_id(sector: str, col: int) -> str:
    return f"{sector}-{pasillo_letra(col)}"


def pasillo_label(sector: str, col: int) -> str:
    return f"Pasillo {pasillo_letra(col)} · Sector {sector}"


class InventarioCatalog:
  """Índices en memoria para búsqueda rápida sobre el grafo base."""

  def __init__(self, g) -> None:
    self.g = g
    self.by_sku: dict[str, int] = {}
    self.by_product: dict[str, list[int]] = {}
    self.by_pasillo: dict[str, list[int]] = {}
    self.pasillo_meta: dict[str, dict] = {}
    self._build()

  def _build(self) -> None:
    for nid, d in self.g.nodes(data=True):
      if d["tipo"] != "ALMACEN":
        continue
      stock = stock_en_nodo(nid, d["sector"])
      sku = stock["sku"].upper()
      prod = stock["producto"].lower()
      self.by_sku[sku] = nid
      self.by_product.setdefault(prod, []).append(nid)
      pk = pasillo_id(d["sector"], d["col"])
      self.by_pasillo.setdefault(pk, []).append(nid)
      if pk not in self.pasillo_meta:
        self.pasillo_meta[pk] = {
          "id": pk,
          "sector": d["sector"],
          "letra": pasillo_letra(d["col"]),
          "label": pasillo_label(d["sector"], d["col"]),
          "col_base": d["col"],
        }

  def listar_pasillos(self, limit: int = 80) -> list[dict]:
    items = []
    for pk, meta in sorted(self.pasillo_meta.items()):
      nids = self.by_pasillo.get(pk, [])
      muestra = []
      for nid in nids[:4]:
        s = stock_en_nodo(nid, self.g.nodes[nid]["sector"])
        muestra.append({"nodo": nid, "producto": s["producto"], "sku": s["sku"], "disponible": s["disponible"]})
      items.append({
        **meta,
        "estantes": len(nids),
        "muestra": muestra,
      })
      if len(items) >= limit:
        break
    return items

  def contenido_pasillo(self, sector: str, letra: str) -> dict | None:
    letra = letra.upper()
    pk = f"{sector.upper()}-{letra}"
    if pk not in self.by_pasillo:
      return None
    productos = []
    for nid in sorted(self.by_pasillo[pk]):
      det = nodo_detalle(self.g, nid)
      productos.append({
        "nodo": nid,
        "ubicacion": det["ubicacion"],
        "producto": det["stock"]["producto"],
        "sku": det["stock"]["sku"],
        "disponible": det["stock"]["disponible"],
        "estado": det["stock"]["estado"],
      })
    return {
      **self.pasillo_meta[pk],
      "productos": productos,
      "total_skus": len(productos),
    }

  def contenido_desde_nodo(self, nid: int) -> dict | None:
    nid = max(0, min(NODE_COUNT - 1, nid))
    d = self.g.nodes[nid]
    return self.contenido_pasillo(d["sector"], pasillo_letra(d["col"]))

  def buscar(self, query: str, tipo: str = "all", limit: int = 25) -> dict:
    q = (query or "").strip()
    if not q:
      return {"ok": False, "error": "Escriba un nodo, SKU o nombre de producto."}

    ql = q.lower()
    qu = q.upper()
    hits: list[dict] = []
    seen: set[int] = set()

    def add(nid: int, match: str, score: int) -> None:
      if nid in seen or nid < 0 or nid >= NODE_COUNT:
        return
      seen.add(nid)
      det = nodo_detalle(self.g, nid)
      hits.append({
        "match": match,
        "score": score,
        "nodo": nid,
        "tipo": det["tipo"],
        "ubicacion": det["ubicacion"],
        "pasillo": pasillo_id(det["sector"], det["col"]),
        "producto": det["stock"]["producto"],
        "sku": det["stock"]["sku"],
        "disponible": det["stock"]["disponible"],
        "estado": det["stock"]["estado"],
      })

    if tipo in ("all", "nodo") and q.isdigit():
      add(int(q), "nodo", 100)

    if tipo in ("all", "sku"):
      if qu in self.by_sku:
        add(self.by_sku[qu], "sku", 95)
      for sku, nid in self.by_sku.items():
        if qu in sku and sku != qu:
          add(nid, "sku_parcial", 70)

    if tipo in ("all", "producto"):
      for prod, nids in self.by_product.items():
        if ql in prod:
          for nid in nids:
            add(nid, "producto", 80 if prod == ql else 60)

    hits.sort(key=lambda h: (-h["score"], h["nodo"]))
    hits = hits[:limit]

    return {
      "ok": True,
      "query": q,
      "tipo": tipo,
      "count": len(hits),
      "results": [{k: v for k, v in h.items() if k != "score"} for h in hits],
    }

  def pasillos_en_camino(self, g, path: list[int], franja: str) -> list[dict]:
    """Pasillos que cruza una ruta con inventario y tráfico."""
    orden: list[str] = []
    vistos: set[str] = set()
    for nid in path:
      d = g.nodes[nid]
      pk = pasillo_id(d["sector"], d["col"])
      if pk in vistos:
        continue
      vistos.add(pk)
      orden.append(pk)

    out = []
    for pk in orden:
      meta = self.pasillo_meta.get(pk)
      if not meta:
        continue
      nids = self.by_pasillo.get(pk, [])
      productos = []
      for nid in nids[:6]:
        s = stock_en_nodo(nid, g.nodes[nid]["sector"])
        productos.append({
          "nodo": nid,
          "producto": s["producto"],
          "sku": s["sku"],
          "disponible": s["disponible"],
        })
      # tráfico medio en aristas del pasillo (nodos INTERSECCION en esa columna/fila)
      congestiones = []
      for nid in path:
        d = g.nodes[nid]
        if pasillo_id(d["sector"], d["col"]) != pk:
          continue
        for _, v, ed in g.edges(nid, data=True):
          if v in path:
            congestiones.append(ed.get("factor_congestion", 1.0))
      trafico = round(sum(congestiones) / len(congestiones), 2) if congestiones else 1.0

      out.append({
        **meta,
        "en_ruta": True,
        "franja": franja,
        "trafico_promedio": trafico,
        "estantes": len(nids),
        "productos": productos,
      })
    return out

  def resumen_productos(self) -> dict:
    estados = {"OK": 0, "BAJO": 0, "CRITICO": 0}
    unidades_totales = 0
    for nids in self.by_product.values():
      s = stock_en_nodo(nids[0], self.g.nodes[nids[0]]["sector"])
      estados[s["estado"]] = estados.get(s["estado"], 0) + 1
      unidades_totales += s["disponible"] * len(nids)
    return {
      "tipos": len(self.by_product),
      "estantes": sum(len(v) for v in self.by_product.values()),
      "pasillos": len(self.pasillo_meta),
      "unidades_estimadas": unidades_totales,
      "por_estado": estados,
    }

  def listar_productos(self, q: str = "", limit: int = 60, offset: int = 0) -> dict:
    """Catálogo agrupado por nombre de producto."""
    ql = (q or "").strip().lower()
    items: list[dict] = []
    for prod_key in sorted(self.by_product.keys()):
      if ql and ql not in prod_key:
        continue
      nids = self.by_product[prod_key]
      nid = nids[0]
      det = nodo_detalle(self.g, nid)
      stock = det["stock"]
      items.append({
        "producto": stock["producto"],
        "icono": icono_producto(stock["producto"]),
        "sku": stock["sku"],
        "nodo": nid,
        "ubicaciones": len(nids),
        "disponible": stock["disponible"],
        "reservado": stock["reservado"],
        "unidades": stock["unidades"],
        "estado": stock["estado"],
        "pasillo": pasillo_id(det["sector"], det["col"]),
        "ubicacion": det["ubicacion"],
        "sector": det["sector"],
        "tipo": det["tipo"],
      })
    total = len(items)
    page = items[offset : offset + limit]
    return {"items": page, "total": total, "offset": offset, "limit": limit}
