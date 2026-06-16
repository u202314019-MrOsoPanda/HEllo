# SmartRoute WMS — Aplicación Web

Plataforma de **Gestión de Almacenes Inteligentes** para el operador final. Toda la lógica de grafos, rutas e inventario está en **Python**; la interfaz es HTML/CSS/JS que consume la API Flask.

## Requisitos

- Python 3.10+
- Navegador web (Chrome, Edge, Firefox)

## Instalación y ejecución

```powershell
cd "APP hecha"
py -3 -m pip install -r requirements.txt
py -3 main.py
```

O en Windows: **doble clic en `run.bat`** (cierra servidores viejos en el puerto antes de iniciar).

Se abre en: **http://127.0.0.1:5000** (no abrir el HTML directamente).

Puerto alternativo:

```powershell
set PORT=5055
py -3 main.py
```

## Arquitectura

| Capa | Tecnología |
|------|------------|
| Interfaz | HTML5 + CSS3 + JavaScript (`static/js/map.js` mapa SVG interactivo) |
| Servidor | Flask (`server.py`) |
| Lógica de negocio | `src/service.py`, `src/catalogo.py`, `src/inventario.py` |
| Algoritmos | `src/algoritmos.py`, `src/grafo.py`, `src/metricas.py` |
| Gráficos | SVG interactivo + Matplotlib PNG (caché) |

## Navegación (hotbar)

| Enlace | Función |
|--------|---------|
| **Inicio** | Landing, hero, beneficios, cómo funciona |
| **Beneficios** | Ventajas para el operador |
| **Productos** | Catálogo, búsqueda, KPIs, **Ir a Navegar** |
| **Navegar** | Mapa interactivo, historial, KPIs, pasillos |
| **Sobre la app** | Contexto + instrucciones `run.bat` |
| **Planificar ruta** | Panel lateral: robot, tráfico, origen/destino |

## Secciones principales

### Productos
- KPIs, búsqueda, chips, ordenación, detalle de pasillo
- **Recoger aquí** · **Ir a Navegar** · **Calcular ruta al muelle**

### Navegar (operación)
- **Mapa SVG interactivo**: zoom (rueda), arrastre, clic = origen, Shift+clic = destino, tooltip con stock
- Pantalla de bienvenida con acciones rápidas
- **Historial** de las 3 últimas rutas (sesión + navegador)
- Vista previa al cambiar franja (`/api/route/preview`)
- Barra de viaje, veredicto, pestañas Comparar / Pasillos en ruta / **Infraestructura** (UFDS, Floyd)

### Planificar ruta (panel)
- Robot, tráfico, stock, búsqueda, ruta aleatoria

## API REST (Python)

| Endpoint | Descripción |
|----------|-------------|
| `POST /api/route` | Ruta completa + mapa + paths SVG + historial |
| `POST /api/route/preview` | Métricas rápidas sin imagen |
| `GET /api/map/layout` | Layout 1500 nodos para mapa interactivo |
| `GET /api/history` | Últimas rutas de la sesión |
| `GET /api/validation` | Casos CP automatizados |
| `GET /api/productos` | Catálogo con resumen |
| `GET /api/search?q=` | Búsqueda |
| `GET /api/pasillo?nodo=` | Contenido del pasillo |
| `GET /api/node/<id>` | Detalle de nodo |
| `GET /api/random-route` | Par aleatorio |
| `POST /api/infra/critical` | Lista en texto: pasillos estructurales (MST) y congestionados |
| `POST /api/infra/mst` | Estadísticas MST (Prim/Kruskal) |
| `POST /api/infra/close` | Simular cierre UFDS |
| `POST /api/infra/reset` | Restaurar pasillos |
| `POST /api/infra/floyd` | Matriz Floyd-Warshall |
| `GET /api/health` | Estado + complejidad algorítmica |

## Pruebas

```powershell
py -3 -m pytest tests/ -q
py -3 scripts/generar_validacion.py
```

## Archivos obsoletos

No usar `web_app.py` ni `src/ui.py` (Streamlit). Ver `_legacy/OBSOLETO.md`.

## Equipo

Joseph Chavez · Gianfranco Durand · Mario Fernandez — 1ACC0184 UPC 2026-10
