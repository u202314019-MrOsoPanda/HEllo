/**
 * Mapa interactivo SVG — zoom, pan, clic en nodos, tooltips.
 */
window.SmartRouteMap = (function () {
  const COLORS = { A: '#6d5b9a', D: '#ec4899', I: '#64748b', R: '#22d3ee' };
  const nodeCache = new Map();

  let layout = null;
  let onPick = null;
  let mountState = null;

  async function ensureLayout() {
    if (layout) return layout;
    const res = await fetch('/api/map/layout');
    layout = await res.json();
    return layout;
  }

  function pathD(path, pos) {
    const pts = path.filter((n) => pos[n]);
    if (pts.length < 2) return '';
    return pts.map((n, i) => `${i ? 'L' : 'M'}${pos[n][0]},${pos[n][1]}`).join(' ');
  }

  async function nodeLabel(nid) {
    if (nodeCache.has(nid)) return nodeCache.get(nid);
    try {
      const d = await fetch(`/api/node/${nid}`).then((r) => r.json());
      const label = `Nodo ${nid} · ${d.ubicacion}\n${d.stock.producto} (${d.stock.disponible} uds)`;
      nodeCache.set(nid, label);
      return label;
    } catch (_) {
      return `Nodo ${nid}`;
    }
  }

  function drawPaths(g, routeData, pos, before) {
    const ref = before || null;
    if (routeData.bfs_path?.length > 1) {
      const p = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      p.setAttribute('d', pathD(routeData.bfs_path, pos));
      p.setAttribute('class', 'path-bfs');
      g.insertBefore(p, ref);
    }
    if (routeData.dijk_path?.length > 1) {
      const p = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      p.setAttribute('d', pathD(routeData.dijk_path, pos));
      p.setAttribute('class', 'path-dijk');
      g.insertBefore(p, ref);
    }
    if (routeData.origin != null && pos[routeData.origin]) {
      const [x, y] = pos[routeData.origin];
      const m = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      m.setAttribute('x', x - 1.8);
      m.setAttribute('y', y - 1.8);
      m.setAttribute('width', 3.6);
      m.setAttribute('height', 3.6);
      m.setAttribute('class', 'marker-origin');
      g.insertBefore(m, ref);
    }
    if (routeData.dest != null && pos[routeData.dest]) {
      const [x, y] = pos[routeData.dest];
      const m = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
      const s = 2.2;
      m.setAttribute(
        'points',
        `${x},${y - s} ${x + s},${y + s * 0.6} ${x - s},${y + s * 0.6}`,
      );
      m.setAttribute('class', 'marker-dest');
      g.insertBefore(m, ref);
    }
  }

  async function mount(container, routeData) {
    await ensureLayout();
    const { width: W, height: H, nodes } = layout;
    const pos = {};
    nodes.forEach(([id, x, y]) => {
      pos[id] = [x, y];
    });

    container.innerHTML = '';
    const wrap = document.createElement('div');
    wrap.className = 'interactive-map-wrap';

    const toolbar = document.createElement('div');
    toolbar.className = 'map-toolbar';
    toolbar.innerHTML = `
      <button type="button" data-zoom="in" aria-label="Acercar mapa">+</button>
      <button type="button" data-zoom="out" aria-label="Alejar mapa">−</button>
      <button type="button" data-zoom="reset" aria-label="Restablecer vista">⊙</button>
      <span class="map-toolbar-hint">Clic: origen · Shift+clic: destino · Rueda: zoom</span>`;

    const tip = document.createElement('div');
    tip.className = 'map-tooltip';
    tip.hidden = true;
    tip.setAttribute('role', 'tooltip');

    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    svg.setAttribute('class', 'interactive-map');
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', 'Mapa interactivo del almacén con rutas');

    let scale = 1;
    let panX = 0;
    let panY = 0;
    let dragging = false;
    let lastX = 0;
    let lastY = 0;

    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    g.setAttribute('class', 'map-transform');

    const bg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    bg.setAttribute('width', W);
    bg.setAttribute('height', H);
    bg.setAttribute('class', 'map-bg');
    g.appendChild(bg);

    const dots = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    dots.setAttribute('class', 'map-dots');
    nodes.forEach(([id, x, y, t], i) => {
      if (i % 3 !== 0) return;
      const c = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      c.setAttribute('cx', x);
      c.setAttribute('cy', y);
      c.setAttribute('r', 0.4);
      c.setAttribute('fill', COLORS[t] || COLORS.A);
      c.setAttribute('opacity', '0.45');
      dots.appendChild(c);
    });
    g.appendChild(dots);

    const pathsG = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    pathsG.setAttribute('class', 'map-paths');
    g.appendChild(pathsG);
    drawPaths(pathsG, routeData, pos, null);

    const clickLayer = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    clickLayer.setAttribute('class', 'map-click-layer');
    nodes.forEach(([id, x, y]) => {
      const hit = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      hit.setAttribute('cx', x);
      hit.setAttribute('cy', y);
      hit.setAttribute('r', 1.4);
      hit.setAttribute('fill', 'transparent');
      hit.setAttribute('data-nid', String(id));
      hit.style.cursor = 'crosshair';
      hit.addEventListener('mouseenter', async (ev) => {
        tip.hidden = false;
        tip.textContent = 'Cargando…';
        const rect = wrap.getBoundingClientRect();
        tip.style.left = `${ev.clientX - rect.left + 12}px`;
        tip.style.top = `${ev.clientY - rect.top + 12}px`;
        tip.textContent = await nodeLabel(id);
      });
      hit.addEventListener('mouseleave', () => {
        tip.hidden = true;
      });
      clickLayer.appendChild(hit);
    });
    g.appendChild(clickLayer);

    function applyTransform() {
      g.setAttribute('transform', `translate(${panX},${panY}) scale(${scale})`);
    }

    svg.addEventListener('wheel', (e) => {
      e.preventDefault();
      scale *= e.deltaY < 0 ? 1.12 : 0.9;
      scale = Math.max(0.6, Math.min(10, scale));
      applyTransform();
    }, { passive: false });

    svg.addEventListener('mousedown', (e) => {
      if (e.button !== 0) return;
      dragging = true;
      lastX = e.clientX;
      lastY = e.clientY;
      svg.classList.add('panning');
    });
    window.addEventListener('mousemove', (e) => {
      if (!dragging) return;
      panX += (e.clientX - lastX) / scale;
      panY += (e.clientY - lastY) / scale;
      lastX = e.clientX;
      lastY = e.clientY;
      applyTransform();
    });
    window.addEventListener('mouseup', () => {
      dragging = false;
      svg.classList.remove('panning');
    });

    clickLayer.addEventListener('click', (e) => {
      const t = e.target.closest('[data-nid]');
      if (!t || !onPick) return;
      e.stopPropagation();
      const nid = parseInt(t.dataset.nid, 10);
      onPick(nid, e.shiftKey ? 'dest' : 'origin');
    });

    svg.appendChild(g);
    wrap.appendChild(toolbar);
    wrap.appendChild(svg);
    wrap.appendChild(tip);
    container.appendChild(wrap);

    toolbar.addEventListener('click', (e) => {
      const z = e.target.dataset?.zoom;
      if (!z) return;
      if (z === 'in') scale = Math.min(10, scale * 1.25);
      else if (z === 'out') scale = Math.max(0.6, scale / 1.25);
      else {
        scale = 1;
        panX = 0;
        panY = 0;
      }
      applyTransform();
    });

    mountState = { container, pathsG, pos, wrap };
    applyTransform();
    return mountState;
  }

  function update(routeData) {
    if (!mountState) return;
    const { pathsG, pos } = mountState;
    pathsG.innerHTML = '';
    drawPaths(pathsG, routeData, pos, null);
  }

  function setPickHandler(fn) {
    onPick = fn;
  }

  return { mount, update, setPickHandler, ensureLayout };
})();
