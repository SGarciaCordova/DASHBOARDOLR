/* ═══════════════════════════════════════════════════════════════════
   Dashboard de Ubicaciones — JavaScript
   Chart.js charts, warehouse heatmap, modals, and client table
   ═══════════════════════════════════════════════════════════════════ */

// Injected from Python
const MASTER_DATA = /*UBICACIONES_DATA_PLACEHOLDER*/ {};
let currentViewKey = "General"; // Default view
let currentData = null;

// ── Chart.js Defaults ─────────────────────────────────────────────
Chart.defaults.color = '#94a3b8';
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.font.size = 11;
Chart.defaults.plugins.legend.display = false;

const CHART_COLORS = [
    '#6366f1', '#8b5cf6', '#a855f7', '#3b82f6', '#06b6d4',
    '#10b981', '#f59e0b', '#ef4444', '#ec4899', '#14b8a6'
];

let charts = {
    occupancy: null,
    topSkus: null,
    level: null
};

// ── Initialize on Load ───────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    // Basic validation
    if (!MASTER_DATA || !MASTER_DATA.views) {
        console.error("MASTER_DATA not loaded correctly");
        return;
    }

    initFilterPills();
    initClientSearch();

    // Initial Render
    switchView("General");
});

// ═══════════════════════════════════════════════════════════════════
//  VIEW SWITCHING LOGIC
// ═══════════════════════════════════════════════════════════════════

function initFilterPills() {
    const pills = document.querySelectorAll('.filter-pill');
    pills.forEach(pill => {
        pill.addEventListener('click', () => {
            const key = pill.getAttribute('data-key');
            if (key) switchView(key);
        });
    });
}

function switchView(key) {
    if (!MASTER_DATA.views[key]) {
        console.error(`View ${key} not found in MASTER_DATA`);
        return;
    }

    currentViewKey = key;
    currentData = MASTER_DATA.views[key];

    // 1. Update UI Active State
    document.querySelectorAll('.filter-pill').forEach(p => {
        if (p.getAttribute('data-key') === key) {
            p.classList.add('active');
        } else {
            p.classList.remove('active');
        }
    });

    // 2. Update Status Bar & Titles
    updateStatusBar();

    // 3. Render Content or Empty State
    const kpiSection = document.getElementById('kpiSection');
    const chartsSection = document.getElementById('chartsSection');
    const emptyState = document.getElementById('emptyState');

    if (currentData.has_data) {
        if (emptyState) emptyState.style.display = 'none';
        if (kpiSection) kpiSection.style.display = 'block';
        if (chartsSection) chartsSection.style.display = 'block';

        renderKPIs();
        renderCharts();
        renderHeatmap();
    } else {
        if (emptyState) emptyState.style.display = 'flex'; // Flex for centering
        if (kpiSection) kpiSection.style.display = 'none';
        if (chartsSection) chartsSection.style.display = 'none';
    }
}

function updateStatusBar() {
    const bar = document.getElementById('statusBar');
    if (!bar) return;

    if (currentData.has_data) {
        bar.className = 'status-bar connected';
        bar.innerHTML = `
            <span>✓ <strong>DATOS CARGADOS</strong> |
            Cliente: ${currentData.selected_client} |
            Ubicaciones Master: ${currentData.kpis.total_locations.toLocaleString()}</span>
        `;
    } else {
        bar.className = 'status-bar no-data';
        bar.innerHTML = `
            <span>⚠️ <strong>SIN DATOS</strong> |
            Cliente: ${currentData.selected_client} |
            Ubicaciones Master: ${(currentData.kpis.total_locations || 0).toLocaleString()}</span>
        `;
    }

    const chartsTitle = document.getElementById('chartsTitle');
    if (chartsTitle) {
        chartsTitle.textContent = `📈 Análisis — ${currentData.selected_client}`;
    }
}

// ═══════════════════════════════════════════════════════════════════
//  RENDERERS
// ═══════════════════════════════════════════════════════════════════

function renderKPIs() {
    const container = document.getElementById('kpiSection');
    if (!container) return;

    const k = currentData.kpis;

    // Dynamically build KPI HTML
    // We use innerHTML for simplicity as we trust the source (our own python code)
    const html = `
    <div class="section-title">📊 KPIs — ${currentData.selected_client}</div>
    <div class="grid-6">
        <div class="card" onclick="showModal('total_locations')">
            <div class="card-header"><div class="card-label">Total Ubicaciones<span class="card-sub">Location Master</span></div><div class="card-icon" style="background:rgba(99,102,241,.15);">📍</div></div>
            <div class="card-value" style="color:var(--indigo-light)">${k.total_locations.toLocaleString()}</div>
            <div class="card-change">Registradas en maestro</div>
        </div>
        <div class="card" onclick="showModal('occupied')">
            <div class="card-header"><div class="card-label">Ubicaciones Ocupadas<span class="card-sub">Con inventario</span></div><div class="card-icon" style="background:rgba(16,185,129,.15);">📦</div></div>
            <div class="card-value" style="color:var(--green)">${k.occupied_locations.toLocaleString()}</div>
            <div class="card-change">Con ≥1 ítem</div>
        </div>
        <div class="card" onclick="showModal('occupancy')">
            <div class="card-header"><div class="card-label">Ocupación<span class="card-sub">% del almacén</span></div><div class="card-icon" style="background:rgba(168,85,247,.15);">📊</div></div>
            <div class="card-value" style="color:var(--purple)">${k.occupancy_pct}%</div>
            <div class="card-change">${k.occupied_locations.toLocaleString()} / ${k.total_locations.toLocaleString()}</div>
        </div>
        <div class="card" onclick="showModal('skus')">
            <div class="card-header"><div class="card-label">SKUs Únicos<span class="card-sub">Productos distintos</span></div><div class="card-icon" style="background:rgba(59,130,246,.15);">🏷️</div></div>
            <div class="card-value" style="color:var(--blue)">${k.total_skus.toLocaleString()}</div>
            <div class="card-change">En inventario</div>
        </div>
        <div class="card" onclick="showModal('piezas')">
            <div class="card-header"><div class="card-label">Total Piezas<span class="card-sub">Inventario total</span></div><div class="card-icon" style="background:rgba(245,158,11,.15);">📦</div></div>
            <div class="card-value" style="color:var(--orange)">${k.total_piezas.toLocaleString()}</div>
            <div class="card-change">Piezas en almacén</div>
        </div>
        <div class="card" onclick="showModal('pasillos')">
            <div class="card-header"><div class="card-label">Pasillos Activos<span class="card-sub">Con ubicaciones</span></div><div class="card-icon" style="background:rgba(34,211,238,.15);">🏢</div></div>
            <div class="card-value" style="color:var(--cyan)">${k.pasillos_used}</div>
            <div class="card-change">Pasillos con inventario</div>
        </div>
    </div>
    `;

    container.innerHTML = html;
}

function renderCharts() {
    renderOccupancyChart();
    renderTopSkusChart();
    renderLevelChart();
}

// ═══════════════════════════════════════════════════════════════════
//  CHARTS
// ═══════════════════════════════════════════════════════════════════

function renderOccupancyChart() {
    const ctx = document.getElementById('occupancyChart');
    if (!ctx) return;

    if (charts.occupancy) {
        charts.occupancy.destroy();
        charts.occupancy = null;
    }

    if (!currentData.occupancy_by_pasillo || currentData.occupancy_by_pasillo.length === 0) return;

    const items = currentData.occupancy_by_pasillo;
    charts.occupancy = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: items.map(d => d.PASILLO),
            datasets: [{
                data: items.map(d => d.pct),
                backgroundColor: items.map(d => {
                    const pct = d.pct;
                    let hue;
                    if (pct <= 50) {
                        // Green (140) to Yellow (40)
                        hue = 140 - (pct / 50) * 100;
                    } else {
                        // Yellow (40) to Red (0)
                        hue = 40 - ((pct - 50) / 50) * 40;
                    }
                    return `hsl(${hue}, 80%, 45%)`;
                }),
                borderRadius: 4,
                barPercentage: 0.7,
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 500 }, // Sleek transition
            scales: {
                x: {
                    max: 100,
                    grid: { color: 'rgba(51,65,85,.3)' },
                    ticks: { callback: v => v + '%' }
                },
                y: {
                    grid: { display: false },
                    ticks: { font: { size: 10, weight: '600' } }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: ctx => {
                            const d = items[ctx.dataIndex];
                            return `${d.pct}% ocupado (${d.occupied}/${d.total})`;
                        }
                    }
                }
            }
        }
    });
}

function renderTopSkusChart() {
    const ctx = document.getElementById('topSkusChart');
    if (!ctx) return;

    if (charts.topSkus) {
        charts.topSkus.destroy();
        charts.topSkus = null;
    }

    if (!currentData.top_skus || currentData.top_skus.length === 0) return;

    const items = currentData.top_skus;
    charts.topSkus = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: items.map(d => d.label),
            datasets: [{
                data: items.map(d => d.cantidad),
                backgroundColor: CHART_COLORS,
                borderRadius: 6,
                barPercentage: 0.65,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 500 },
            scales: {
                y: { grid: { color: 'rgba(51,65,85,.3)' } },
                x: {
                    grid: { display: false },
                    ticks: { maxRotation: 45, font: { size: 9 } }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        title: ctx => items[ctx[0].dataIndex].desc,
                        label: ctx => `${items[ctx.dataIndex].cantidad.toLocaleString()} piezas`
                    }
                }
            }
        }
    });
}

function renderLevelChart() {
    const ctx = document.getElementById('levelChart');
    if (!ctx) return;

    if (charts.level) {
        charts.level.destroy();
        charts.level = null;
    }

    if (!currentData.distribution_by_level || currentData.distribution_by_level.length === 0) return;

    const items = currentData.distribution_by_level;
    charts.level = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: items.map(d => d.label),
            datasets: [{
                data: items.map(d => d.cantidad),
                backgroundColor: CHART_COLORS.slice(0, items.length),
                borderWidth: 0,
                hoverOffset: 8,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 500 },
            cutout: '55%',
            plugins: {
                legend: {
                    display: true,
                    position: 'right',
                    labels: { boxWidth: 12, padding: 10, font: { size: 10 } }
                },
                tooltip: {
                    callbacks: {
                        label: ctx => {
                            const total = items.reduce((a, b) => a + b.cantidad, 0);
                            const pct = ((ctx.parsed / total) * 100).toFixed(1);
                            return `${ctx.parsed.toLocaleString()} pzas (${pct}%)`;
                        }
                    }
                }
            }
        }
    });
}

// ═══════════════════════════════════════════════════════════════════
//  HEATMAP (Interactive: Zoom/Pan + Rack Detail)
// ═══════════════════════════════════════════════════════════════════

let heatmapState = { scale: 1, panning: false, pointX: 0, pointY: 0, startX: 0, startY: 0 };

function renderHeatmap() {
    const container = document.getElementById('heatmapGrid');
    if (!container) return;

    container.innerHTML = `
        <div class="heatmap-wrapper" id="heatmapWrapper">
            <div class="heatmap-viewport" id="heatmapViewport"></div>
            <div class="heatmap-controls">
                <button class="zoom-btn" onclick="zoomHeatmap(0.2)">+</button>
                <button class="zoom-btn" onclick="zoomHeatmap(-0.2)">−</button>
                <button class="zoom-btn" onclick="resetHeatmap()">↺</button>
            </div>
        </div>
        <div class="rack-panel" id="rackPanel">
            <div class="rack-header">
                <div class="rack-title" id="rackTitle">Pasillo X - Pos Y</div>
                <div class="rack-subtitle">Detalle por nivel</div>
            </div>
            <div class="rack-levels" id="rackLevels"></div>
            <button class="close-panel-btn" onclick="closeRackPanel()">Cerrar Panel</button>
        </div>
    `;

    const viewport = document.getElementById('heatmapViewport');
    const wrapper = document.getElementById('heatmapWrapper');

    if (!currentData.heatmap || !currentData.heatmap.pasillos || !currentData.heatmap.pasillos.length) {
        viewport.innerHTML = '<div style="text-align:center;padding:5rem;color:#94a3b8;">Mapa no disponible</div>';
        return;
    }

    const { pasillos, max_position, cells } = currentData.heatmap;

    const step = max_position > 48 ? 4 : max_position > 32 ? 2 : 1;
    const positions = [];
    for (let p = 1; p <= max_position; p += step) positions.push(p);

    // Build lookup with level data
    const lookup = {};
    let maxQty = 0;
    cells.forEach(c => {
        const colIndex = Math.round((c.position - 1) / step);
        const roundedPos = 1 + (colIndex * step);
        const key = c.pasillo + '-' + roundedPos;

        if (!lookup[key]) lookup[key] = { qty: 0, levels: {} };
        lookup[key].qty += c.qty;

        if (c.levels) {
            for (let l in c.levels) {
                const lvl = parseInt(l);
                lookup[key].levels[lvl] = (lookup[key].levels[lvl] || 0) + c.levels[l];
            }
        }
        if (lookup[key].qty > maxQty) maxQty = lookup[key].qty;
    });

    // Grid
    viewport.style.display = 'grid';
    viewport.style.gridTemplateColumns = '40px repeat(' + positions.length + ', 40px)';
    viewport.style.gap = '2px';
    viewport.style.padding = '20px';

    // Header
    viewport.appendChild(document.createElement('div'));
    positions.forEach(function (p) {
        var h = document.createElement('div');
        h.className = 'heatmap-header';
        h.textContent = p;
        viewport.appendChild(h);
    });

    // Rows
    pasillos.forEach(function (pasillo) {
        var lbl = document.createElement('div');
        lbl.className = 'heatmap-row-label';
        lbl.textContent = pasillo;
        viewport.appendChild(lbl);

        positions.forEach(function (pos) {
            var key = pasillo + '-' + pos;
            var data = lookup[key];
            var cell = document.createElement('div');
            cell.className = 'heatmap-cell';

            if (data && data.qty > 0) {
                var ratio = data.qty / maxQty;
                if (ratio <= 0.25) cell.classList.add('low');
                else if (ratio <= 0.5) cell.classList.add('medium');
                else if (ratio <= 0.75) cell.classList.add('high');
                else cell.classList.add('full');

                cell.title = pasillo + '-' + pos + ': ' + data.qty.toLocaleString() + ' pzas';
                (function (pa, po, d) {
                    cell.onclick = function () { openRackPanel(pa, po, d); };
                })(pasillo, pos, data);
            } else {
                cell.classList.add('empty');
            }
            viewport.appendChild(cell);
        });
    });

    // Pan/Zoom
    heatmapState = { scale: 1, panning: false, pointX: 0, pointY: 0, startX: 0, startY: 0 };

    wrapper.onmousedown = function (e) {
        e.preventDefault();
        heatmapState.panning = true;
        heatmapState.startX = e.clientX - heatmapState.pointX;
        heatmapState.startY = e.clientY - heatmapState.pointY;
        viewport.style.cursor = 'grabbing';
    };
    window.addEventListener('mousemove', function (e) {
        if (!heatmapState.panning) return;
        e.preventDefault();
        heatmapState.pointX = e.clientX - heatmapState.startX;
        heatmapState.pointY = e.clientY - heatmapState.startY;
        applyHeatmapTransform();
    });
    window.addEventListener('mouseup', function () {
        heatmapState.panning = false;
        var vp = document.getElementById('heatmapViewport');
        if (vp) vp.style.cursor = 'grab';
    });
}

function applyHeatmapTransform() {
    var vp = document.getElementById('heatmapViewport');
    if (vp) vp.style.transform = 'translate(' + heatmapState.pointX + 'px, ' + heatmapState.pointY + 'px) scale(' + heatmapState.scale + ')';
}

function zoomHeatmap(delta) {
    heatmapState.scale += delta;
    if (heatmapState.scale < 0.5) heatmapState.scale = 0.5;
    if (heatmapState.scale > 3) heatmapState.scale = 3;
    applyHeatmapTransform();
}

function resetHeatmap() {
    heatmapState = { scale: 1, panning: false, pointX: 0, pointY: 0, startX: 0, startY: 0 };
    applyHeatmapTransform();
}

function openRackPanel(pasillo, pos, data) {
    var panel = document.getElementById('rackPanel');
    var title = document.getElementById('rackTitle');
    var levelsC = document.getElementById('rackLevels');
    if (!panel || !title || !levelsC) return;

    title.textContent = 'Ubicacion ' + pasillo + '-' + pos;
    levelsC.innerHTML = '';

    var maxLevelQty = 0;
    for (var l = 1; l <= 6; l++) {
        var q = (data.levels && data.levels[l]) ? data.levels[l] : 0;
        if (q > maxLevelQty) maxLevelQty = q;
    }

    for (var l = 6; l >= 1; l--) {
        var qty = (data.levels && data.levels[l]) ? data.levels[l] : 0;
        var barW = maxLevelQty > 0 ? Math.round((qty / maxLevelQty) * 100) : 0;
        var div = document.createElement('div');
        div.className = 'rack-level';
        div.innerHTML = '<div class="level-num">L' + l + '</div>' +
            '<div class="level-qty">' + (qty > 0 ? qty.toLocaleString() : '-') + '</div>' +
            '<div class="level-bar" style="width:' + barW + '%;"></div>';
        levelsC.appendChild(div);
    }
    panel.classList.add('open');
}

function closeRackPanel() {
    var panel = document.getElementById('rackPanel');
    if (panel) panel.classList.remove('open');
}

function showTooltip() { }
function hideTooltip() { }

// ═══════════════════════════════════════════════════════════════════
//  CLIENT SEARCH / TABLE
// ═══════════════════════════════════════════════════════════════════

function initClientSearch() {
    const input = document.getElementById('clientSearch');
    if (!input) return;
    input.addEventListener('input', function () {
        const filter = this.value.toLowerCase();
        const rows = document.querySelectorAll('#clientTableBody tr');
        rows.forEach(row => {
            const name = row.querySelector('td:nth-child(2)');
            if (name) {
                row.style.display = name.textContent.toLowerCase().includes(filter) ? '' : 'none';
            }
        });
    });
}

// ═══════════════════════════════════════════════════════════════════
//  MODALS
// ═══════════════════════════════════════════════════════════════════

let modalChart = null;

function showModal(type) {
    const overlay = document.getElementById('modalOverlay');
    const box = document.getElementById('modalBox');
    const title = document.getElementById('modalTitle');
    const body = document.getElementById('modalContent');
    const chartCanvas = document.getElementById('modalChartCanvas');

    if (!overlay || !box) return;

    // Destroy previous chart
    if (modalChart) { modalChart.destroy(); modalChart = null; }

    let modalTitle = '';
    let modalHTML = '';
    let chartConfig = null;

    // Safety check if we have data
    if (!currentData || !currentData.kpis) return;

    switch (type) {
        case 'total_locations':
            modalTitle = '📍 Total de Ubicaciones';
            modalHTML = buildKpiDetail('Total de ubicaciones registradas en el maestro', currentData.kpis.total_locations, 'ubicaciones');
            break;

        case 'occupied':
            modalTitle = '📦 Ubicaciones Ocupadas';
            modalHTML = buildKpiDetail('Ubicaciones con al menos 1 ítem de inventario', currentData.kpis.occupied_locations, 'ubicaciones ocupadas');
            break;

        case 'occupancy':
            modalTitle = '📊 Porcentaje de Ocupación';
            modalHTML = `<div style="font-size:2.5rem;font-weight:800;text-align:center;color:#6366f1;margin:20px 0">${currentData.kpis.occupancy_pct}%</div>
                <p style="text-align:center;color:#94a3b8">Ocupadas: ${currentData.kpis.occupied_locations} / Total: ${currentData.kpis.total_locations}</p>`;
            chartConfig = buildGaugeChart(currentData.kpis.occupancy_pct);
            break;

        case 'skus':
            modalTitle = '🏷️ SKUs Únicos';
            modalHTML = buildKpiDetail('SKUs distintos encontrados en inventario', currentData.kpis.total_skus, 'SKUs');
            break;

        case 'piezas':
            modalTitle = '📦 Total de Piezas';
            modalHTML = buildKpiDetail('Suma total de piezas en inventario', currentData.kpis.total_piezas, 'piezas');
            break;

        case 'pasillos':
            modalTitle = '🏢 Pasillos Utilizados';
            modalHTML = buildKpiDetail('Pasillos con al menos 1 ubicación ocupada', currentData.kpis.pasillos_used, 'pasillos');
            if (currentData.occupancy_by_pasillo) {
                modalHTML += '<table><thead><tr><th>Pasillo</th><th>Ocupadas</th><th>Total</th><th>%</th></tr></thead><tbody>';
                // Only show first 8 to avoid huge scroll
                currentData.occupancy_by_pasillo.slice(0, 8).forEach(d => {
                    modalHTML += `<tr><td><strong>${d.PASILLO}</strong></td><td>${d.occupied}</td><td>${d.total}</td><td>${d.pct}%</td></tr>`;
                });
                modalHTML += '</tbody></table><div style="text-align:center;font-size:0.8rem;color:#64748b;margin-top:5px">Mostrando top 8</div>';
            }
            break;

        default:
            modalTitle = 'Detalle';
            modalHTML = '<p>Sin información adicional</p>';
    }

    title.textContent = modalTitle;
    body.innerHTML = modalHTML;

    if (chartConfig && chartCanvas) {
        chartCanvas.parentElement.style.display = 'block';
        modalChart = new Chart(chartCanvas, chartConfig);
    } else if (chartCanvas) {
        chartCanvas.parentElement.style.display = 'none';
    }

    overlay.style.display = 'block';
    box.style.display = 'block';
}

function closeModal() {
    const overlay = document.getElementById('modalOverlay');
    const box = document.getElementById('modalBox');
    if (overlay) overlay.style.display = 'none';
    if (box) box.style.display = 'none';
    if (modalChart) { modalChart.destroy(); modalChart = null; }
}

function buildKpiDetail(description, value, unit) {
    return `<div style="text-align:center;padding:20px;">
        <div style="font-size:3rem;font-weight:800;color:#6366f1">${typeof value === 'number' ? value.toLocaleString() : value}</div>
        <div style="font-size:.85rem;color:#94a3b8;margin-top:8px">${unit}</div>
        <div style="font-size:.75rem;color:#64748b;margin-top:16px">${description}</div>
    </div>`;
}

function buildGaugeChart(pct) {
    return {
        type: 'doughnut',
        data: {
            datasets: [{
                data: [pct, 100 - pct],
                backgroundColor: ['#6366f1', '#1e293b'],
                borderWidth: 0,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '70%',
            rotation: -90,
            circumference: 180,
            plugins: { legend: { display: false }, tooltip: { enabled: false } }
        }
    };
}

// ── Chart modal (expanded view) ─────────────────────────────────
function showChartModal(chartType) {
    const overlay = document.getElementById('modalOverlay');
    const box = document.getElementById('modalBox');
    const title = document.getElementById('modalTitle');
    const body = document.getElementById('modalContent');
    const chartCanvas = document.getElementById('modalChartCanvas');

    if (!overlay || !box) return;
    if (modalChart) { modalChart.destroy(); modalChart = null; }

    let chartConfig = null;
    let modalTitle = '';

    switch (chartType) {
        case 'occupancy':
            modalTitle = '📊 Ocupación por Pasillo (Detalle)';
            if (currentData.occupancy_by_pasillo) {
                chartConfig = {
                    type: 'bar',
                    data: {
                        labels: currentData.occupancy_by_pasillo.map(d => d.PASILLO),
                        datasets: [{
                            data: currentData.occupancy_by_pasillo.map(d => d.pct),
                            backgroundColor: currentData.occupancy_by_pasillo.map(d => {
                                const pct = d.pct;
                                let hue;
                                if (pct <= 50) {
                                    hue = 140 - (pct / 50) * 100;
                                } else {
                                    hue = 40 - ((pct - 50) / 50) * 40;
                                }
                                return `hsl(${hue}, 80%, 45%)`;
                            }),
                            borderRadius: 4,
                        }]
                    },
                    options: {
                        indexAxis: 'y',
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            x: { max: 100, grid: { color: 'rgba(51,65,85,.3)' }, ticks: { callback: v => v + '%' } },
                            y: { grid: { display: false } }
                        }
                    }
                };
            }
            break;

        case 'skus':
            modalTitle = '🏷️ Top SKUs (Detalle)';
            if (currentData.top_skus) {
                chartConfig = {
                    type: 'bar',
                    data: {
                        labels: currentData.top_skus.map(d => d.label),
                        datasets: [{
                            data: currentData.top_skus.map(d => d.cantidad),
                            backgroundColor: CHART_COLORS,
                            borderRadius: 6,
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: { grid: { color: 'rgba(51,65,85,.3)' } },
                            x: { grid: { display: false }, ticks: { maxRotation: 45, font: { size: 9 } } }
                        }
                    }
                };
            }
            break;

        case 'levels':
            modalTitle = '📶 Distribución por Nivel (Detalle)';
            if (currentData.distribution_by_level) {
                chartConfig = {
                    type: 'doughnut',
                    data: {
                        labels: currentData.distribution_by_level.map(d => d.label),
                        datasets: [{
                            data: currentData.distribution_by_level.map(d => d.cantidad),
                            backgroundColor: CHART_COLORS,
                            borderWidth: 0,
                            hoverOffset: 10,
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        cutout: '50%',
                        plugins: {
                            legend: { display: true, position: 'right', labels: { boxWidth: 12, padding: 10 } }
                        }
                    }
                };
            }
            break;
    }

    title.textContent = modalTitle;
    body.innerHTML = '';

    if (chartConfig && chartCanvas) {
        chartCanvas.parentElement.style.display = 'block';
        chartCanvas.parentElement.style.height = '300px';
        modalChart = new Chart(chartCanvas, chartConfig);
    }

    overlay.style.display = 'block';
    box.style.display = 'block';
}
