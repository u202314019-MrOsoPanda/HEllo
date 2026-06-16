/**
 * SmartRoute WMS — Cliente (operador / cliente final)
 */

const state = {
  franja: 'alta',
  robot: 'estandar',
  lastResult: null,
  lastParamsKey: null,
  loading: false,
  searchTipo: 'all',
  searchTimer: null,
  productosQuery: '',
  productosItems: [],
  previewTimer: null,
};

const HIST_KEY = 'smartroute_history';

const ANCHORS = { inicio: 'top', beneficios: 'beneficios', 'sobre-app': 'sobre-app', 'como-funciona': 'como-funciona' };
const FRANJA_LABELS = { baja: 'tranquilo', media: 'normal', alta: 'hora pico' };

const ROBOT_HINTS = {
  estandar: 'Uso general en pasillos.',
  pesado: 'Pallets y carga frágil — más lento, más cuidado.',
  express: 'Pedidos urgentes — mayor velocidad.',
  refrigerado: 'Componentes sensibles — rutas estables.',
};

// ── Parámetros y caché ────────────────────────────────────────────────────────

function parseNodeInput(id, fallback) {
  const raw = document.getElementById(id)?.value;
  const n = parseInt(String(raw).trim(), 10);
  if (Number.isNaN(n)) return fallback;
  return Math.max(0, Math.min(1499, n));
}

function getParams() {
  const checked = document.querySelector('input[name="franja"]:checked');
  if (checked) state.franja = checked.value;
  state.robot = document.getElementById('robotType').value;
  return {
    origin: parseNodeInput('origin', 101),
    dest: parseNodeInput('dest', 0),
    franja: state.franja,
    robot: state.robot,
  };
}

function paramsKey(p = getParams()) {
  return `${p.origin}|${p.dest}|${p.franja}|${p.robot}`;
}

function invalidateResult() {
  state.lastResult = null;
  state.lastParamsKey = null;
}

function validateParams(p) {
  if (p.origin === p.dest) {
    return 'El punto de recogida y el de entrega deben ser distintos.';
  }
  return null;
}

// ── Navegación ────────────────────────────────────────────────────────────────

function hideAllViews() {
  ['landing', 'operacion-view', 'productos-view'].forEach((id) => {
    document.getElementById(id)?.classList.remove('active');
  });
}

function setNavActive(name) {
  document.querySelectorAll('.nav-links button[data-nav]').forEach((b) => {
    b.classList.toggle('active', b.dataset.nav === name);
  });
}

function showLanding(anchor = 'inicio') {
  closeDrawer();
  hideAllViews();
  document.getElementById('landing').classList.add('active');
  const section = ANCHORS[anchor] ? anchor : 'inicio';
  const id = ANCHORS[anchor] || 'top';
  setNavActive(section);
  requestAnimationFrame(() => {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    else window.scrollTo({ top: 0, behavior: 'smooth' });
  });
}

function showOperacionView() {
  hideAllViews();
  document.getElementById('operacion-view').classList.add('active');
  setNavActive('operacion');
  window.scrollTo({ top: 0, behavior: 'auto' });
}

function showProductosView() {
  closeDrawer();
  hideAllViews();
  document.getElementById('productos-view').classList.add('active');
  setNavActive('productos');
  window.scrollTo({ top: 0, behavior: 'auto' });
  loadProductosCatalog(state.productosQuery);
}

async function openOperacion(autoCalc = false) {
  showOperacionView();
  const key = paramsKey();
  if (state.lastResult && state.lastParamsKey === key) {
    renderAll(state.lastResult);
    updateOpStatus(state.lastResult);
    return;
  }
  if (!state.lastResult) {
    showMapWelcome();
    updateOpStatus(null);
    document.getElementById('tripBar').style.display = 'none';
  }
  if (autoCalc && state.lastResult) {
    await calcularRuta();
  }
}

function loadLocalHistory() {
  try {
    return JSON.parse(localStorage.getItem(HIST_KEY) || '[]');
  } catch (_) {
    return [];
  }
}

function saveLocalHistory(data) {
  let h = loadLocalHistory();
  h.unshift({
    origin: data.origin,
    dest: data.dest,
    franja: data.franja,
    robot: data.robot,
    label: `${data.origen?.ubicacion || data.origin} → ${data.destino?.ubicacion || data.dest}`,
    savings_pct: data.metrics?.savings_pct,
    ts: Date.now(),
  });
  h = h.slice(0, 3);
  localStorage.setItem(HIST_KEY, JSON.stringify(h));
  renderHistoryBar(h);
}

function renderHistoryBar(serverHist) {
  const bar = document.getElementById('routeHistoryBar');
  const chips = document.getElementById('routeHistoryChips');
  if (!bar || !chips) return;
  const merged = [];
  const seen = new Set();
  [...(serverHist || []), ...loadLocalHistory()].forEach((item) => {
    const k = `${item.origin}|${item.dest}|${item.franja}|${item.robot}`;
    if (seen.has(k)) return;
    seen.add(k);
    merged.push(item);
  });
  const list = merged.slice(0, 3);
  if (!list.length) {
    bar.hidden = true;
    return;
  }
  bar.hidden = false;
  chips.innerHTML = list.map((h, i) => `
    <button type="button" class="history-chip" data-idx="${i}"
      data-origin="${h.origin}" data-dest="${h.dest}"
      data-franja="${h.franja || 'alta'}" data-robot="${h.robot || 'estandar'}"
      title="${h.label || ''}">
      ${h.origin}→${h.dest}${h.savings_pct != null ? ` (−${h.savings_pct}%)` : ''}
    </button>`).join('');
}

async function applyHistoryItem(item) {
  document.getElementById('origin').value = item.origin;
  document.getElementById('dest').value = item.dest;
  if (item.franja) {
    state.franja = item.franja;
    const radio = document.querySelector(`input[name="franja"][value="${item.franja}"]`);
    if (radio) {
      radio.checked = true;
      document.querySelectorAll('.traffic-opt').forEach((el) => {
        el.classList.toggle('selected', el.dataset.franja === item.franja);
      });
    }
  }
  if (item.robot) {
    state.robot = item.robot;
    document.getElementById('robotType').value = item.robot;
    document.getElementById('robotHint').textContent = ROBOT_HINTS[item.robot] || '';
  }
  invalidateResult();
  await updateStockPreview();
  await calcularRuta();
}

function showMapWelcome() {
  const hist = loadLocalHistory();
  const histBtn = hist.length
    ? `<button type="button" class="btn btn-outline" id="welcomeLast">Última ruta (${hist[0].origin}→${hist[0].dest})</button>`
    : '';
  document.getElementById('mapContainer').innerHTML = `
    <div class="map-welcome">
      <div class="map-welcome-icon" aria-hidden="true">🗺️</div>
      <h3>Bienvenido al mapa del almacén</h3>
      <p>Configure origen y destino en <strong>Planificar ruta</strong>, o use una acción rápida:</p>
      <div class="welcome-actions">
        <button type="button" class="btn btn-primary" id="welcomeCalc">Calcular ruta</button>
        <button type="button" class="btn btn-outline" id="welcomeRandom">Ruta aleatoria</button>
        ${histBtn}
      </div>
      <p class="welcome-hint">Tras calcular: <strong>clic</strong> en el mapa = origen · <strong>Shift+clic</strong> = destino · arrastre para mover · rueda para zoom</p>
    </div>`;
  document.getElementById('welcomeCalc')?.addEventListener('click', () => calcularRuta());
  document.getElementById('welcomeRandom')?.addEventListener('click', onRandom);
  document.getElementById('welcomeLast')?.addEventListener('click', () => applyHistoryItem(hist[0]));
}

function handleNav(name, ev) {
  if (ev) ev.preventDefault();
  if (name === 'operacion') {
    openOperacion(false);
    return;
  }
  if (name === 'productos') {
    showProductosView();
    return;
  }
  showLanding(name);
}

document.body.addEventListener('click', (e) => {
  const nav = e.target.closest('[data-nav]');
  if (!nav) return;
  if (nav.id === 'headerPanelBtn') return;
  handleNav(nav.dataset.nav, e);
});

document.getElementById('btnBackHome')?.addEventListener('click', (e) => {
  e.preventDefault();
  showLanding('inicio');
});

// ── Acordeón ────────────────────────────────────────────────────────────────────

document.querySelectorAll('.acc-head').forEach((head) => {
  head.addEventListener('click', () => {
    const item = head.closest('.acc-item');
    const open = item.classList.contains('open');
    document.querySelectorAll('.acc-item').forEach((i) => i.classList.remove('open'));
    if (!open) item.classList.add('open');
  });
});

document.querySelectorAll('.op-tab').forEach((tab) => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.op-tab').forEach((t) => t.classList.remove('active'));
    document.querySelectorAll('.op-tab-panel').forEach((p) => p.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById(`tab-${tab.dataset.tab}`).classList.add('active');
  });
});

// ── Drawer ───────────────────────────────────────────────────────────────────

const drawer = document.getElementById('drawer');
const overlay = document.getElementById('drawerOverlay');

function openDrawer() { drawer.classList.add('open'); overlay.classList.add('open'); document.body.style.overflow = 'hidden'; }
function closeDrawer() { drawer.classList.remove('open'); overlay.classList.remove('open'); document.body.style.overflow = ''; }

['headerPanelBtn', 'btnHeroPanel', 'btnOpenDrawerOp'].forEach((id) => {
  document.getElementById(id)?.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    openDrawer();
  });
});
document.getElementById('drawerClose').addEventListener('click', closeDrawer);
overlay.addEventListener('click', closeDrawer);

// ── Hero grid ───────────────────────────────────────────────────────────────

(function () {
  const grid = document.getElementById('warehouseGrid');
  if (!grid) return;
  const route = new Set([24, 25, 26, 38, 50, 62, 74, 86, 98, 99, 100]);
  for (let i = 0; i < 96; i++) {
    const s = document.createElement('span');
    if (i === 24) s.className = 'origin';
    else if (i === 100) s.className = 'dest';
    else if (route.has(i)) s.className = 'route';
    grid.appendChild(s);
  }
})();

// ── Formulario ────────────────────────────────────────────────────────────────

document.getElementById('trafficOptions').addEventListener('click', (e) => {
  const opt = e.target.closest('.traffic-opt');
  if (!opt) return;
  const radio = opt.querySelector('input[type="radio"]');
  if (radio) {
    radio.checked = true;
    state.franja = radio.value;
    document.querySelectorAll('.traffic-opt').forEach((el) => {
      el.classList.toggle('selected', el.dataset.franja === state.franja);
    });
    invalidateResult();
    clearTimeout(state.previewTimer);
    if (document.getElementById('operacion-view').classList.contains('active')) {
      state.previewTimer = setTimeout(refreshPreview, 450);
    }
  }
});

document.getElementById('robotType').addEventListener('change', (e) => {
  state.robot = e.target.value;
  document.getElementById('robotHint').textContent = ROBOT_HINTS[state.robot] || '';
  invalidateResult();
});

async function apiPost(url, body = {}) {
  const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || `Error del servidor (${res.status})`);
  }
  return data;
}

async function fetchNode(nid) {
  return fetch(`/api/node/${nid}`).then((r) => r.json());
}

async function updateStockPreview() {
  try {
    const o = document.getElementById('origin').value;
    const d = document.getElementById('dest').value;
    const [oi, di] = await Promise.all([fetchNode(o), fetchNode(d)]);
    document.getElementById('previewOriginLoc').textContent = oi.ubicacion;
    document.getElementById('previewOriginSku').textContent = `${oi.stock.producto} · ${oi.stock.sku}`;
    document.getElementById('previewOriginStock').textContent = `${oi.stock.disponible} uds (${oi.stock.estado})`;
    document.getElementById('previewDestLoc').textContent = di.ubicacion;
  } catch (_) { /* offline */ }
}

async function aplicarRutaAleatoria() {
  const data = await fetch('/api/random-route').then((r) => r.json());
  if (!data.ok || data.origin === undefined) {
    throw new Error('No se pudo generar ruta aleatoria');
  }
  document.getElementById('origin').value = data.origin;
  document.getElementById('dest').value = data.dest;
  invalidateResult();
  await updateStockPreview();
  return data;
}

// ── Calcular ruta ─────────────────────────────────────────────────────────────

function showMapLoading() {
  document.getElementById('mapContainer').innerHTML = `
    <div class="map-loading">
      <span class="loading"></span>
      <p><strong>Trazando ruta en el almacén…</strong></p>
      <p class="map-loading-sub">Como un GPS: calculando el mejor camino entre estantes</p>
    </div>`;
}

function showMapError(msg) {
  document.getElementById('mapContainer').innerHTML = `<div class="map-error alert alert-error">${msg}</div>`;
}

function updateOpStatus(data) {
  const el = document.getElementById('opStatus');
  if (!data) {
    el.textContent = 'Configure origen, destino y robot — pulse Calcular.';
    return;
  }
  let extra = '';
  const n = data.normalizacion;
  if (n?.swapped) extra = ' · Origen/destino corregidos';
  if (n?.auto_dest) extra += ' · Muelle más cercano';
  el.textContent = `${data.robot_label} · ${FRANJA_LABELS[data.franja]} · Nodo ${data.origin} → ${data.dest}${extra}`;
}

async function calcularRuta() {
  if (state.loading) return;

  const params = getParams();
  const err = validateParams(params);
  if (err) {
    showOperacionView();
    showMapError(err);
    updateOpStatus(null);
    return;
  }

  state.loading = true;
  showOperacionView();
  closeDrawer();
  showMapLoading();
  document.getElementById('opStatus').textContent = 'Calculando…';

  const btns = ['btnCalcular', 'btnCalcOp', 'btnCalcFromOp'].map((id) => document.getElementById(id)).filter(Boolean);
  btns.forEach((b) => { b.disabled = true; });

  try {
    const data = await apiPost('/api/route', params);
    if (!data.ok) {
      showMapError(data.error);
      updateOpStatus(null);
      invalidateResult();
      return;
    }
    state.lastResult = data;
    document.getElementById('origin').value = data.origin;
    document.getElementById('dest').value = data.dest;
    state.lastParamsKey = paramsKey({
      origin: data.origin,
      dest: data.dest,
      franja: params.franja,
      robot: params.robot,
    });
    saveLocalHistory(data);
    if (data.history) renderHistoryBar(data.history);
    renderAll(data);
    updateOpStatus(data);
  } catch (err) {
    console.error(err);
    updateOpStatus(null);
    invalidateResult();
    const msg = String(err.message || '');
    const isServer = msg && !msg.includes('Failed to fetch');
    document.getElementById('opStatus').textContent = isServer ? 'Error del servidor.' : 'Sin conexión al servidor.';
    showMapError(isServer
      ? `<strong>${msg}</strong><br>Cierre todas las ventanas del servidor, ejecute <code>run.bat</code> y abra <a href="http://127.0.0.1:5000">http://127.0.0.1:5000</a> (no abra el HTML directamente).`
      : 'Ejecute <code>py -3 main.py</code> en la carpeta <strong>APP hecha</strong> y abra <strong>http://127.0.0.1:5000</strong> (no abra el HTML directo).');
  } finally {
    state.loading = false;
    btns.forEach((b) => { b.disabled = false; });
  }
}

function renderAll(data) {
  renderMap(data);
  renderTripBar(data);
  renderStock(data);
  renderVerdict(data);
  renderKpis(data);
  renderAnalisis(data);
  renderPasillosRuta(data);
  const heroKpi = document.getElementById('heroKpiValue');
  if (heroKpi) heroKpi.textContent = `−${data.metrics.savings_pct}%`;
}

function renderMap(data) {
  const container = document.getElementById('mapContainer');
  if (window.SmartRouteMap && data.dijk_path) {
    SmartRouteMap.setPickHandler((nid, role) => {
      document.getElementById(role === 'dest' ? 'dest' : 'origin').value = nid;
      invalidateResult();
      updateStockPreview();
      document.getElementById('opStatus').textContent = `Nodo ${nid} asignado como ${role === 'dest' ? 'entrega' : 'recogida'} — pulse Calcular.`;
    });
    SmartRouteMap.mount(container, data).catch(() => {
      container.innerHTML = `<img src="data:image/png;base64,${data.map_image}" alt="Mapa del almacén">`;
    });
    return;
  }
  if (data.map_image) {
    container.innerHTML = `<img src="data:image/png;base64,${data.map_image}" alt="Mapa del almacén">`;
  }
}

async function refreshPreview() {
  const params = getParams();
  if (validateParams(params)) return;
  try {
    const data = await apiPost('/api/route/preview', params);
    if (!data.ok) return;
    document.getElementById('kpiTime').textContent = `${data.metrics.dijkstra.time_min} min`;
    document.getElementById('kpiDist').textContent = `${data.metrics.dijkstra.distance_m} m`;
    document.getElementById('kpiSave').textContent = `${data.metrics.savings_pct}%`;
    document.getElementById('kpiEnergy').textContent = `${data.metrics.dijkstra.energy_kwh} kWh`;
    document.getElementById('kpiTraffic').textContent = data.metrics.dijkstra.avg_congestion;
    const status = document.getElementById('opStatus');
    if (status && state.lastResult) {
      status.textContent = `Vista previa (${FRANJA_LABELS[params.franja]}): ahorro ${data.metrics.savings_pct}% — pulse Calcular para actualizar mapa.`;
    }
  } catch (_) { /* */ }
}

function renderTripBar(data) {
  const m = data.metrics.dijkstra;
  const bar = document.getElementById('tripBar');
  bar.style.display = 'block';
  document.getElementById('tripTitle').textContent = `${m.time_min} min al muelle`;
  document.getElementById('tripTime').textContent = `${m.time_min} min`;
  document.getElementById('tripDist').textContent = `${m.distance_m} m`;
  document.getElementById('tripRobot').textContent = data.robot_label;
  document.getElementById('tripOriginLabel').textContent = data.origen.ubicacion;
  document.getElementById('tripDestLabel').textContent = data.destino.ubicacion;
}

function stockStatusClass(estado) {
  return `stock-status status-${String(estado).toLowerCase().replace(/í/g, 'i')}`;
}

function renderStock(data) {
  const o = data.origen;
  const d = data.destino;
  document.getElementById('stockCard').style.display = 'block';
  document.getElementById('stockOriginLoc').textContent = o.ubicacion;
  document.getElementById('stockOriginSku').textContent = `${o.stock.producto} · ${o.stock.sku}`;
  document.getElementById('stockOriginUnits').textContent = `${o.stock.disponible} uds`;
  const st = document.getElementById('stockOriginStatus');
  st.textContent = `Stock: ${o.stock.estado}`;
  st.className = stockStatusClass(o.stock.estado);

  const destCard = document.getElementById('stockDestCard');
  destCard.style.display = 'block';
  document.getElementById('stockDestLoc').textContent = d.ubicacion;
  document.getElementById('stockDestTipo').textContent = d.tipo === 'DESPACHO'
    ? 'Muelle de despacho'
    : `Destino · ${d.tipo}`;
}

function renderVerdict(data) {
  const ex = data.explicacion;
  const card = document.getElementById('verdictCard');
  card.style.display = 'block';
  const badge = document.getElementById('verdictBadge');
  badge.textContent = ex.veredicto;
  badge.className = `verdict-badge ${ex.recomendar ? 'yes' : 'maybe'}`;

  document.getElementById('verdictYes').innerHTML = ex.razones_si.map((r) => `<li>${r}</li>`).join('');
  document.getElementById('verdictNo').innerHTML = ex.razones_no_directa.map((r) => `<li>${r}</li>`).join('');
}

function renderKpis(data) {
  const m = data.metrics.dijkstra;
  document.getElementById('kpiTime').textContent = `${m.time_min} min`;
  document.getElementById('kpiDist').textContent = `${m.distance_m} m`;
  document.getElementById('kpiSave').textContent = `${data.metrics.savings_pct}%`;
  document.getElementById('kpiEnergy').textContent = `${m.energy_kwh} kWh`;
  document.getElementById('kpiTraffic').textContent = m.avg_congestion;
}

function renderAnalisis(data) {
  const mb = data.metrics.bfs;
  const md = data.metrics.dijkstra;
  const alg = data.algorithms || {};
  const matchNote = data.routes_match
    ? '<p class="small match-note">En esta franja BFS y Dijkstra coinciden: tráfico uniforme o misma ruta óptima.</p>'
    : '<p class="small match-note">Rutas divergen: Dijkstra evita pasillos más congestionados.</p>';
  document.getElementById('analisisContent').innerHTML = `
    <div class="compare-cards">
      <div class="compare-card recommended">
        <h4>✓ Ruta verde (recomendada)</h4>
        <p><strong>${md.time_min} min</strong> · ${md.distance_m} m · Tráfico ${md.avg_congestion}</p>
        <p class="small">Menos congestión — ideal en hora pico.</p>
      </div>
      <div class="compare-card direct">
        <h4>Ruta amarilla (directa)</h4>
        <p><strong>${mb.time_min} min</strong> · ${mb.distance_m} m · Tráfico ${mb.avg_congestion}</p>
        <p class="small">Menos curvas, pero más pasillos saturados.</p>
      </div>
    </div>
    <div class="panel" style="margin-top:1rem;">
      <p style="color:var(--text-secondary);font-size:0.92rem;line-height:1.7;">
        <strong>¿Por qué sí la verde?</strong> Ahorro del <strong>${data.metrics.savings_pct}%</strong> en costo operativo.
        El robot <strong>${data.robot_label}</strong> llega con menos frenadas y menor consumo.
      </p>
    </div>
    <div class="panel algo-panel" style="margin-top:1rem;">
      <p class="eyebrow eyebrow-purple">ALGORITMOS EJECUTADOS (Python)</p>
      <table class="data-table algo-table">
        <thead><tr><th>Técnica</th><th>Costo</th><th>Tiempo</th><th>Uso</th></tr></thead>
        <tbody>
          <tr><td>BFS</td><td>${alg.bfs?.cost ?? '—'}</td><td>${alg.bfs?.ms ?? '—'} ms</td><td>Ruta directa (amarilla)</td></tr>
          <tr><td>Dijkstra</td><td>${alg.dijkstra?.cost ?? '—'}</td><td>${alg.dijkstra?.ms ?? '—'} ms</td><td>Ruta recomendada (verde)</td></tr>
          <tr><td>Bellman-Ford</td><td>${alg.bellman_ford?.cost ?? '—'}</td><td>${alg.bellman_ford?.ms ?? '—'} ms</td><td>Validación ${alg.bellman_ford?.valid ? '✓' : '—'}</td></tr>
          <tr><td>Prim (MST)</td><td>${alg.prim_mst?.cost ?? '—'}</td><td>${alg.prim_mst?.ms ?? '—'} ms</td><td>Red mínima del almacén (no es ruta AGV)</td></tr>
          <tr><td>Kruskal (MST)</td><td>${alg.kruskal_mst?.cost ?? '—'}</td><td>${alg.kruskal_mst?.ms ?? '—'} ms</td><td>Verificación del MST</td></tr>
        </tbody>
      </table>
      <p class="small" style="margin-top:0.5rem;color:var(--text-muted);">UFDS y Floyd-Warshall: pestaña <strong>Pasillos críticos</strong>.</p>
      ${matchNote}
    </div>`;
}

function renderPasillosRuta(data) {
  const el = document.getElementById('pasillosContent');
  if (!el) return;
  const pasillos = data.pasillos_ruta || [];
  if (!pasillos.length) {
    el.innerHTML = '<div class="alert alert-info">No hay datos de pasillos para esta ruta.</div>';
    return;
  }
  el.innerHTML = pasillos.map((p) => `
    <div class="pasillo-card">
      <h4>${p.label}</h4>
      <p class="pasillo-meta">
        ${p.estantes} estantes · Tráfico ${p.trafico_promedio} (${FRANJA_LABELS[data.franja] || data.franja})
      </p>
      <div class="pasillo-products">
        ${(p.productos || []).map((pr) => `
          <div class="pasillo-product">
            <span><strong>Nodo ${pr.nodo}</strong> · ${pr.producto} <em>${pr.sku}</em></span>
            <span>${pr.disponible} uds</span>
          </div>`).join('')}
      </div>
    </div>`).join('');
}

// ── Catálogo productos ────────────────────────────────────────────────────────

function sortProductos(items, mode) {
  const list = [...items];
  switch (mode) {
    case 'stock-desc':
      return list.sort((a, b) => b.disponible - a.disponible);
    case 'stock-asc':
      return list.sort((a, b) => a.disponible - b.disponible);
    case 'sector':
      return list.sort((a, b) => `${a.sector}${a.producto}`.localeCompare(`${b.sector}${b.producto}`));
    default:
      return list.sort((a, b) => a.producto.localeCompare(b.producto));
  }
}

function renderProductosKpis(resumen) {
  if (!resumen) return;
  document.getElementById('kpiTipos').textContent = resumen.tipos;
  document.getElementById('kpiEstantes').textContent = resumen.estantes;
  document.getElementById('kpiOk').textContent = resumen.por_estado?.OK ?? '—';
  const bajo = (resumen.por_estado?.BAJO ?? 0) + (resumen.por_estado?.CRITICO ?? 0);
  document.getElementById('kpiBajo').textContent = bajo;
}

function renderProductoCard(p) {
  const st = String(p.estado).toLowerCase();
  return `
    <article class="producto-card" data-nodo="${p.nodo}" data-producto="${encodeURIComponent(p.producto)}" tabindex="0">
      <span class="producto-sector">Sector ${p.sector}</span>
      <div class="producto-card-head">
        <div class="producto-card-icon">${p.icono || '📦'}</div>
        <div>
          <h4>${p.producto}</h4>
          <p class="sku">${p.sku}</p>
        </div>
      </div>
      <div class="producto-meta">
        <span>Nodo <strong>${p.nodo}</strong></span>
        <span>Pasillo <strong>${p.pasillo}</strong></span>
        <span><strong>${p.disponible}</strong> uds</span>
        <span><strong>${p.ubicaciones}</strong> ubic.</span>
      </div>
      <p class="producto-meta" style="margin-top:0.35rem;font-size:0.76rem;">${p.ubicacion}</p>
      <span class="producto-estado status-${st}">Stock ${p.estado}</span>
      <div class="producto-card-actions">
        <button type="button" class="btn-card-primary" data-action="recoger" data-nodo="${p.nodo}">Recoger aquí</button>
        <button type="button" class="btn-card-nav" data-action="navegar" data-nodo="${p.nodo}">Ir a Navegar</button>
        <button type="button" data-action="detalle" data-nodo="${p.nodo}">Ver pasillo</button>
      </div>
    </article>`;
}

function renderProductosGrid() {
  const grid = document.getElementById('productosGrid');
  const sort = document.getElementById('productosSort')?.value || 'nombre';
  const items = sortProductos(state.productosItems, sort);
  if (!items.length) {
    grid.innerHTML = '<div class="alert alert-info">Sin resultados. Pruebe otro término o pulse Ver todos.</div>';
    return;
  }
  grid.innerHTML = items.map(renderProductoCard).join('');
}

function renderProductosChips(categorias, activeQ) {
  const el = document.getElementById('productosChips');
  if (!el || !categorias?.length) return;
  const chips = categorias.map((c) => {
    const active = activeQ && c.toLowerCase().includes(activeQ.toLowerCase()) ? ' active' : '';
    return `<button type="button" class="chip-producto${active}" data-chip="${encodeURIComponent(c)}">${c}</button>`;
  });
  el.innerHTML = chips.join('');
}

async function showProductoDetalle(nodo) {
  const panel = document.getElementById('productoDetalle');
  const content = document.getElementById('productoDetalleContent');
  if (!panel || !content) return;
  panel.hidden = false;
  content.innerHTML = '<p class="detalle-placeholder">Cargando detalle…</p>';
  document.querySelectorAll('.producto-card').forEach((c) => {
    c.classList.toggle('selected', c.dataset.nodo === String(nodo));
  });
  try {
    const [node, pas] = await Promise.all([
      fetch(`/api/node/${nodo}`).then((r) => r.json()),
      fetch(`/api/pasillo?nodo=${nodo}`).then((r) => r.json()),
    ]);
    const icon = state.productosItems.find((p) => p.nodo === Number(nodo))?.icono || '📦';
    const pasilloHtml = pas.ok && pas.pasillo?.productos?.length
      ? pas.pasillo.productos.slice(0, 8).map((pr) =>
        `<div>· Nodo ${pr.nodo} — ${pr.producto} (${pr.disponible} uds)</div>`).join('')
      : '<div>Sin más referencias en este pasillo.</div>';
    content.innerHTML = `
      <div class="detalle-head">
        <span class="detalle-icon">${icon}</span>
        <div>
          <h3>${node.stock.producto}</h3>
          <p class="sku">${node.stock.sku}</p>
        </div>
      </div>
      <div class="detalle-rows">
        <div><span>Ubicación</span><strong>${node.ubicacion}</strong></div>
        <div><span>Pasillo</span><strong>${pas.ok ? pas.pasillo.id : '—'}</strong></div>
        <div><span>Disponible</span><strong>${node.stock.disponible} uds</strong></div>
        <div><span>Reservado</span><strong>${node.stock.reservado} uds</strong></div>
        <div><span>Estado</span><strong>${node.stock.estado}</strong></div>
      </div>
      <p class="eyebrow eyebrow-purple" style="margin-bottom:0.4rem;">EN ESTE PASILLO</p>
      <div class="detalle-pasillo-list">${pasilloHtml}</div>
      <div class="detalle-actions">
        <button type="button" class="btn-purple" id="btnDetalleRecoger" data-nodo="${nodo}">Usar como recogida</button>
        <button type="button" class="btn btn-outline" id="btnDetalleRuta" data-nodo="${nodo}">Calcular ruta al muelle</button>
      </div>`;
    document.getElementById('btnDetalleRecoger')?.addEventListener('click', () => seleccionarProducto(nodo));
    document.getElementById('btnDetalleRuta')?.addEventListener('click', async () => {
      seleccionarProducto(nodo, false);
      closeDrawer();
      await calcularRuta();
    });
  } catch (_) {
    content.innerHTML = '<p class="detalle-placeholder">No se pudo cargar el detalle.</p>';
  }
}

async function loadProductosCatalog(q = '') {
  const grid = document.getElementById('productosGrid');
  const stats = document.getElementById('productosStats');
  if (!grid) return;
  state.productosQuery = q;
  grid.innerHTML = '<div class="alert alert-info">Cargando productos…</div>';
  try {
    const url = `/api/productos?limit=120${q ? `&q=${encodeURIComponent(q)}` : ''}`;
    const data = await fetch(url).then((r) => r.json());
    if (!data.ok) throw new Error('API');
    state.productosItems = data.items || [];
    renderProductosKpis(data.resumen);
    renderProductosChips(data.categorias, q);
    stats.textContent = `${data.total} tipos · ${data.items.length} en pantalla${q ? ` · «${q}»` : ''} · ${data.resumen?.pasillos ?? '—'} pasillos`;
    renderProductosGrid();
    if (!data.items.length) {
      grid.innerHTML = '<div class="alert alert-info">Sin resultados. Pruebe otro término o pulse Ver todos.</div>';
    }
  } catch (_) {
    stats.textContent = 'Sin conexión al servidor.';
    grid.innerHTML = '<div class="alert alert-error">Ejecute <code>py -3 main.py</code> y recargue la página.</div>';
  }
}

function seleccionarProducto(nodo, openPanel = true) {
  document.getElementById('origin').value = nodo;
  invalidateResult();
  updateStockPreview();
  if (openPanel) openDrawer();
}

async function irANavegarDesdeProducto(nodo) {
  document.getElementById('origin').value = nodo;
  invalidateResult();
  await updateStockPreview();
  showOperacionView();
  await calcularRuta();
}

document.getElementById('productosGrid')?.addEventListener('click', (e) => {
  const action = e.target.closest('[data-action]');
  if (action) {
    e.stopPropagation();
    const nodo = action.dataset.nodo;
    if (action.dataset.action === 'recoger') seleccionarProducto(nodo);
    if (action.dataset.action === 'detalle') showProductoDetalle(nodo);
    if (action.dataset.action === 'navegar') irANavegarDesdeProducto(nodo);
    return;
  }
  const card = e.target.closest('.producto-card[data-nodo]');
  if (card) showProductoDetalle(card.dataset.nodo);
});

document.getElementById('productosGrid')?.addEventListener('keydown', (e) => {
  if (e.key !== 'Enter') return;
  const card = e.target.closest('.producto-card[data-nodo]');
  if (card) showProductoDetalle(card.dataset.nodo);
});

document.getElementById('productosSort')?.addEventListener('change', renderProductosGrid);

document.getElementById('btnProductosSearch')?.addEventListener('click', () => {
  loadProductosCatalog(document.getElementById('productosSearch')?.value.trim() || '');
});

document.getElementById('btnProductosClear')?.addEventListener('click', () => {
  const inp = document.getElementById('productosSearch');
  if (inp) inp.value = '';
  loadProductosCatalog('');
});

document.getElementById('productosSearch')?.addEventListener('input', () => {
  clearTimeout(state.searchTimer);
  state.searchTimer = setTimeout(() => {
    loadProductosCatalog(document.getElementById('productosSearch')?.value.trim() || '');
  }, 320);
});

document.getElementById('productosChips')?.addEventListener('click', (e) => {
  const chip = e.target.closest('.chip-producto[data-chip]');
  if (!chip) return;
  const name = decodeURIComponent(chip.dataset.chip);
  const inp = document.getElementById('productosSearch');
  if (inp) inp.value = name;
  loadProductosCatalog(name);
});

// ── Pasillos críticos (texto) / UFDS / Floyd ─────────────────────────────────

function renderCriticalList(data) {
  const el = document.getElementById('criticalList');
  if (!el || !data?.ok) return;

  const row = (p, i) => `
    <li class="critical-item">
      <strong>${i + 1}. ${p.pasillo}</strong>
      <span class="critical-meta">Nodos ${p.nodos} · ${p.tipo} · c=${p.congestion} · ${p.distancia_m} m</span>
      <p class="critical-motivo">${p.motivo}</p>
    </li>`;

  const mst = data.mst || {};
  el.innerHTML = `
    <div class="alert alert-success critical-resumen">${data.resumen}</div>
    <div class="critical-stats panel">
      <span>MST: <strong>${mst.aristas}</strong> aristas</span>
      <span>Prim: <strong>${mst.costo_prim}</strong></span>
      <span>Kruskal: <strong>${mst.costo_kruskal}</strong></span>
      <span>${mst.validacion_ok ? '✓ Validación OK' : '—'}</span>
    </div>
    <div class="critical-section panel">
      <h4>🏗️ Estructuralmente críticos (MST)</h4>
      <p class="small">Top ${data.estructurales.length} de ${data.total_estructurales} — red mínima del almacén.</p>
      <ol class="critical-list">${data.estructurales.map(row).join('')}</ol>
    </div>
    <div class="critical-section panel">
      <h4>🚦 Más congestionados (franja ${FRANJA_LABELS[data.franja] || data.franja})</h4>
      <p class="small">Top ${data.congestionados.length} de ${data.total_congestionados} corredores principales.</p>
      <ol class="critical-list">${data.congestionados.map(row).join('')}</ol>
    </div>`;
}

async function loadPasillosCriticos() {
  const list = document.getElementById('criticalList');
  const msg = document.getElementById('infraMessage');
  if (list) list.innerHTML = '<div class="map-loading"><span class="loading"></span> Analizando pasillos…</div>';
  if (msg) msg.innerHTML = '';
  try {
    const data = await apiPost('/api/infra/critical', { franja: getParams().franja });
    if (!data.ok) throw new Error(data.error || 'Error');
    renderCriticalList(data);
  } catch (e) {
    if (list) list.innerHTML = '';
    if (msg) msg.innerHTML = `<div class="alert alert-error">${e.message || 'No se pudo cargar la lista.'}</div>`;
  }
}

document.getElementById('btnCritical')?.addEventListener('click', () => {
  document.querySelector('.op-tab[data-tab="infra"]')?.click();
  loadPasillosCriticos();
});

document.querySelector('.op-tab[data-tab="infra"]')?.addEventListener('click', () => {
  const list = document.getElementById('criticalList');
  if (list && !list.innerHTML.trim()) loadPasillosCriticos();
});

document.getElementById('btnClose').addEventListener('click', async () => {
  try {
    const data = await apiPost('/api/infra/close', { franja: getParams().franja });
    document.getElementById('infraMessage').innerHTML =
      `<div class="alert alert-${data.ok ? 'success' : 'error'}">${data.ok ? data.message : data.error}</div>`;
    invalidateResult();
  } catch (_) { /* */ }
});

document.getElementById('btnReset').addEventListener('click', async () => {
  try {
    const data = await apiPost('/api/infra/reset');
    document.getElementById('infraMessage').innerHTML = `<div class="alert alert-success">${data.message}</div>`;
    document.getElementById('criticalList').innerHTML = '';
    invalidateResult();
    loadPasillosCriticos();
  } catch (_) { /* */ }
});

document.getElementById('btnFloyd')?.addEventListener('click', async () => {
  document.querySelector('.op-tab[data-tab="infra"]')?.click();
  const msg = document.getElementById('infraMessage');
  msg.innerHTML = '<div class="map-loading"><span class="loading"></span> Calculando Floyd-Warshall…</div>';
  try {
    const data = await apiPost('/api/infra/floyd', { franja: getParams().franja });
    if (!data.ok) throw new Error(data.error);
    const rows = data.matrix.map((r) => {
      const cols = Object.entries(r).filter(([k]) => k !== 'desde').map(([, v]) => v ?? '∞');
      return `<tr><td><strong>${r.desde}</strong></td>${cols.map((v) => `<td>${v}</td>`).join('')}</tr>`;
    }).join('');
    msg.innerHTML = `
      <div class="alert alert-success">Floyd-Warshall · ${data.ms} ms · distancias mínimas entre sectores (hubs)</div>
      <div class="panel" style="overflow-x:auto;margin-top:0.75rem;">
        <table class="data-table"><thead><tr><th>Desde</th><th>A</th><th>B</th><th>C</th><th>D</th><th>E</th><th>F</th><th>G</th><th>H</th><th>DESPACHO</th></tr></thead>
        <tbody>${rows}</tbody></table>
      </div>`;
  } catch (e) {
    msg.innerHTML = `<div class="alert alert-error">${e.message || 'Error Floyd-Warshall'}</div>`;
  }
});

// ── Eventos ───────────────────────────────────────────────────────────────────

function asignarAGV() {
  if (state.lastResult) alert(`Robot ${state.lastResult.robot_label} enviado por la ruta verde (simulación).`);
  else alert('Calcule una ruta primero.');
}

document.getElementById('btnCalcular').addEventListener('click', () => calcularRuta());
document.getElementById('btnCalcOp').addEventListener('click', () => calcularRuta());
document.getElementById('btnCalcFromOp').addEventListener('click', () => calcularRuta());
document.getElementById('btnAsignar').addEventListener('click', asignarAGV);
document.getElementById('btnUsarRuta')?.addEventListener('click', asignarAGV);

document.getElementById('btnVerDirecta')?.addEventListener('click', () => {
  if (!state.lastResult) return;
  const mb = state.lastResult.metrics.bfs;
  alert(
    `Ruta directa (amarilla):\n` +
    `• ${mb.time_min} min · ${mb.distance_m} m\n` +
    `• Tráfico promedio: ${mb.avg_congestion}\n` +
    `• Más congestión — no recomendada en hora pico.`
  );
});

async function onRandom() {
  try {
    await aplicarRutaAleatoria();
    await calcularRuta();
  } catch (e) {
    console.error(e);
    alert('No se pudo generar ruta aleatoria. ¿Está el servidor activo?');
  }
}

document.getElementById('btnRandom').addEventListener('click', onRandom);
document.getElementById('btnRandomOp').addEventListener('click', onRandom);

function onCoordsChange() {
  invalidateResult();
  updateStockPreview();
}

document.getElementById('origin').addEventListener('input', onCoordsChange);
document.getElementById('dest').addEventListener('input', onCoordsChange);

document.querySelectorAll('.search-filter').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.search-filter').forEach((b) => b.classList.remove('active'));
    btn.classList.add('active');
    state.searchTipo = btn.dataset.searchTipo;
    runSearch();
  });
});

function getSearchQuery() {
  return (document.getElementById('searchQuery')?.value
    || document.getElementById('searchQueryOp')?.value || '').trim();
}

function syncSearchInputs(q) {
  const a = document.getElementById('searchQuery');
  const b = document.getElementById('searchQueryOp');
  if (a) a.value = q;
  if (b) b.value = q;
}

async function runSearch() {
  const q = getSearchQuery();
  syncSearchInputs(q);
  const box = document.getElementById('searchResults');
  const boxOp = document.getElementById('searchResultsOp');
  const targets = [box, boxOp].filter(Boolean);
  if (!q) {
    targets.forEach((t) => { t.innerHTML = ''; });
    return;
  }
  try {
    const data = await fetch(`/api/search?q=${encodeURIComponent(q)}&tipo=${state.searchTipo}`).then((r) => r.json());
    const html = (!data.ok || !data.results?.length)
      ? '<div class="search-hit"><span>Sin resultados. Pruebe otro término.</span></div>'
      : data.results.map((r) => `
      <div class="search-hit" data-nodo="${r.nodo}" data-tipo="${r.tipo}">
        <strong>Nodo ${r.nodo} · ${r.producto}</strong>
        <span>${r.ubicacion}</span>
        <em>${r.sku} · ${r.disponible} uds · Pasillo ${r.pasillo}</em>
      </div>`).join('');
    targets.forEach((t) => { t.innerHTML = html; });
  } catch (_) {
    const err = '<div class="search-hit"><span>Servidor no disponible.</span></div>';
    targets.forEach((t) => { t.innerHTML = err; });
  }
}

function bindSearchResults(el) {
  el?.addEventListener('click', async (e) => {
    const hit = e.target.closest('.search-hit[data-nodo]');
    if (!hit) return;
    const nodo = hit.dataset.nodo;
    const tipo = hit.dataset.tipo;
    if (tipo === 'DESPACHO') {
      document.getElementById('dest').value = nodo;
    } else {
      document.getElementById('origin').value = nodo;
    }
    invalidateResult();
    await updateStockPreview();
    if (!document.getElementById('operacion-view').classList.contains('active')) {
      openDrawer();
    }
  });
}

document.getElementById('searchQuery')?.addEventListener('input', () => {
  clearTimeout(state.searchTimer);
  state.searchTimer = setTimeout(runSearch, 280);
});
document.getElementById('searchQueryOp')?.addEventListener('input', () => {
  clearTimeout(state.searchTimer);
  state.searchTimer = setTimeout(runSearch, 280);
});
document.getElementById('btnSearchOp')?.addEventListener('click', runSearch);

bindSearchResults(document.getElementById('searchResults'));
bindSearchResults(document.getElementById('searchResultsOp'));

async function initApp() {
  document.getElementById('robotHint').textContent = ROBOT_HINTS.estandar;
  SmartRouteMap?.setPickHandler((nid, role) => {
    document.getElementById(role === 'dest' ? 'dest' : 'origin').value = nid;
    invalidateResult();
    updateStockPreview();
  });
  renderHistoryBar(loadLocalHistory());
  document.getElementById('routeHistoryChips')?.addEventListener('click', (e) => {
    const chip = e.target.closest('.history-chip');
    if (!chip) return;
    applyHistoryItem({
      origin: parseInt(chip.dataset.origin, 10),
      dest: parseInt(chip.dataset.dest, 10),
      franja: chip.dataset.franja,
      robot: chip.dataset.robot,
    });
  });
  const nav = document.getElementById('navLinks');
  nav?.addEventListener('keydown', (e) => {
    const buttons = [...nav.querySelectorAll('button')];
    const idx = buttons.indexOf(document.activeElement);
    if (e.key === 'ArrowRight' && idx >= 0) {
      e.preventDefault();
      buttons[(idx + 1) % buttons.length].focus();
    }
    if (e.key === 'ArrowLeft' && idx >= 0) {
      e.preventDefault();
      buttons[(idx - 1 + buttons.length) % buttons.length].focus();
    }
  });
  try {
    const health = await fetch('/api/health').then((r) => r.json());
    if (!health.ok) throw new Error('health');
  } catch (_) {
    console.warn('Servidor no disponible — ejecute py -3 main.py');
  }
  try {
    const hist = await fetch('/api/history').then((r) => r.json());
    if (hist.ok && hist.history?.length) renderHistoryBar(hist.history);
  } catch (_) { /* */ }
  try {
    const data = await fetch('/api/defaults').then((r) => r.json());
    if (data.ok) {
      document.getElementById('origin').value = data.origin;
      document.getElementById('dest').value = data.dest;
    }
  } catch (_) { /* */ }
  await updateStockPreview();
}

initApp();
