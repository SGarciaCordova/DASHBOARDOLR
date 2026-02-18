// ===================================================
// Reebok WMS Dashboard - JavaScript
// Data is injected from Python via placeholder replacement
// ===================================================

const K = /*REEBOK_KPI_DATA_PLACEHOLDER*/ {};
const ENTRADAS_DATA = /*REEBOK_ENTRADAS_PLACEHOLDER*/[];
const SURTIDO_DATA = /*REEBOK_SURTIDO_PLACEHOLDER*/[];
const CHART_ENTRADAS = /*REEBOK_CHART_ENTRADAS_PLACEHOLDER*/[];
const CHART_SURTIDO = /*REEBOK_CHART_SURTIDO_PLACEHOLDER*/[];
const CHART_TOP_SKUS = /*REEBOK_CHART_SKUS_PLACEHOLDER*/[];
const CHART_CALIDAD = /*REEBOK_CHART_CALIDAD_PLACEHOLDER*/[];
const CHART_TARIMAS_IN = /*REEBOK_CHART_TARIMAS_IN_PLACEHOLDER*/[];
const CHART_TARIMAS_OUT = /*REEBOK_CHART_TARIMAS_OUT_PLACEHOLDER*/[];
const CHART_ESTADO = /*REEBOK_CHART_ESTADO_PLACEHOLDER*/[];
const CHART_FILLRATE = /*REEBOK_CHART_FILLRATE_PLACEHOLDER*/[];

const COLORS = ['#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#06b6d4', '#6366f1', '#14b8a6', '#ef4444', '#84cc16'];
const chartOpts = { responsive: true, maintainAspectRatio: false };
const barGrid = { y: { beginAtZero: true, grid: { borderDash: [3, 3], color: '#e2e8f0' }, ticks: { font: { family: 'Inter' } } }, x: { grid: { display: false }, ticks: { font: { family: 'Inter' } } } };

// ===================================================
// 1. RENDER KPIs
// ===================================================

function renderKPIs() {
    function fmt(n) { return (n || 0).toLocaleString('es-MX'); }
    function fmtCompact(n) {
        if (!n) return '0';
        if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
        if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
        return n.toLocaleString('es-MX');
    }
    document.getElementById('kpi_recibos').innerText = fmt(K.total_recibos);
    document.getElementById('kpi_piezas_in').innerText = fmtCompact(K.piezas_recibidas);
    document.getElementById('kpi_skus').innerText = fmt(K.skus_unicos);
    document.getElementById('kpi_tarimas_in').innerText = fmt(K.tarimas_recibidas);
    document.getElementById('kpi_calidad').innerText = K.tasa_calidad + '%';
    document.getElementById('kpi_pedidos').innerText = fmt(K.total_pedidos);
    document.getElementById('kpi_piezas_out').innerText = fmtCompact(K.piezas_surtidas);
    document.getElementById('kpi_fillrate').innerText = K.fill_rate + '%';
    document.getElementById('kpi_tarimas_out').innerText = fmt(K.tarimas_despachadas);
    document.getElementById('kpi_completados').innerText = K.pct_completados + '%';
    document.getElementById('lastUpdate').innerText = '\u{1F550} ' + K.last_update;
}

// ===================================================
// 2. CHARTS (4 Inbound + 4 Outbound)
// ===================================================

function initCharts() {

    // === INBOUND 1: Entradas por Día (bar) ===
    try {
        new Chart(document.getElementById('chartEntradasDia').getContext('2d'), {
            type: 'bar',
            data: {
                labels: CHART_ENTRADAS.map(d => d.dia ? d.dia.slice(5) : '?'),
                datasets: [{
                    label: 'Registros',
                    data: CHART_ENTRADAS.map(d => d.total),
                    backgroundColor: '#3b82f6',
                    borderRadius: 6
                }, {
                    label: 'Piezas',
                    data: CHART_ENTRADAS.map(d => d.cantidad),
                    backgroundColor: '#93c5fd',
                    borderRadius: 6
                }]
            },
            options: { ...chartOpts, plugins: { legend: { labels: { font: { family: 'Inter', weight: '600' } } } }, scales: barGrid }
        });
    } catch (e) { console.error('Chart Entradas:', e); }

    // === INBOUND 2: Top SKUs (doughnut) ===
    try {
        new Chart(document.getElementById('chartSKUs').getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: CHART_TOP_SKUS.map(d => (d.descripcion || '?').toString().trim().slice(0, 20) + (d.descripcion?.length > 20 ? '...' : '')),
                datasets: [{
                    data: CHART_TOP_SKUS.map(d => d.total),
                    backgroundColor: COLORS,
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                ...chartOpts,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            font: { family: 'Inter', size: 9, weight: '500' },
                            padding: 8,
                            boxWidth: 8,
                            generateLabels: (chart) => {
                                const data = chart.data;
                                if (data.labels.length && data.datasets.length) {
                                    return data.labels.map((label, i) => {
                                        return {
                                            text: label,
                                            fillStyle: data.datasets[0].backgroundColor[i],
                                            hidden: false,
                                            index: i
                                        };
                                    });
                                }
                                return [];
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const fullLabel = CHART_TOP_SKUS[context.dataIndex].descripcion || '?';
                                const value = context.raw || 0;
                                return `${fullLabel}: ${value}`;
                            }
                        }
                    }
                }
            }
        });
    } catch (e) { console.error('Chart SKUs:', e); }

    // === INBOUND 3: Calidad (doughnut) ===
    try {
        const calColors = { 'A': '#10b981', 'B': '#f59e0b', 'C': '#ef4444' };
        new Chart(document.getElementById('chartCalidad').getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: CHART_CALIDAD.map(d => 'Calidad ' + d.tipo),
                datasets: [{ data: CHART_CALIDAD.map(d => d.total), backgroundColor: CHART_CALIDAD.map(d => calColors[d.tipo] || '#9ca3af'), borderWidth: 0 }]
            },
            options: { ...chartOpts, plugins: { legend: { position: 'bottom', labels: { font: { family: 'Inter', size: 11 }, padding: 10, boxWidth: 12 } } } }
        });
    } catch (e) { console.error('Chart Calidad:', e); }

    // === INBOUND 4: Tarimas Recibidas por Día (bar) ===
    try {
        new Chart(document.getElementById('chartTarimasIn').getContext('2d'), {
            type: 'bar',
            data: {
                labels: CHART_TARIMAS_IN.map(d => d.dia ? d.dia.slice(5) : '?'),
                datasets: [{ label: 'Tarimas', data: CHART_TARIMAS_IN.map(d => d.total), backgroundColor: '#ec4899', borderRadius: 6 }]
            },
            options: { ...chartOpts, plugins: { legend: { display: false } }, scales: barGrid }
        });
    } catch (e) { console.error('Chart Tarimas In:', e); }

    // === OUTBOUND 1: Surtido por Día (bar) ===
    try {
        new Chart(document.getElementById('chartSurtidoDia').getContext('2d'), {
            type: 'bar',
            data: {
                labels: CHART_SURTIDO.map(d => d.dia ? d.dia.slice(5) : '?'),
                datasets: [{
                    label: 'Registros',
                    data: CHART_SURTIDO.map(d => d.total),
                    backgroundColor: '#10b981',
                    borderRadius: 6
                }, {
                    label: 'Piezas',
                    data: CHART_SURTIDO.map(d => d.cantidad),
                    backgroundColor: '#6ee7b7',
                    borderRadius: 6
                }]
            },
            options: { ...chartOpts, plugins: { legend: { labels: { font: { family: 'Inter', weight: '600' } } } }, scales: barGrid }
        });
    } catch (e) { console.error('Chart Surtido:', e); }

    // === OUTBOUND 2: Fill Rate Distribution (bar horizontal) ===
    try {
        const frColors = { '100%': '#10b981', '90-99%': '#3b82f6', '70-89%': '#f59e0b', '50-69%': '#f97316', '<50%': '#ef4444' };
        new Chart(document.getElementById('chartFillRate').getContext('2d'), {
            type: 'bar',
            data: {
                labels: CHART_FILLRATE.map(d => d.rango),
                datasets: [{ label: 'Pedidos', data: CHART_FILLRATE.map(d => d.total), backgroundColor: CHART_FILLRATE.map(d => frColors[d.rango] || '#9ca3af'), borderRadius: 6 }]
            },
            options: { ...chartOpts, indexAxis: 'y', plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true, grid: { borderDash: [3, 3], color: '#e2e8f0' } }, y: { grid: { display: false } } } }
        });
    } catch (e) { console.error('Chart Fill Rate:', e); }

    // === OUTBOUND 3: Estado de Pedidos (doughnut) ===
    try {
        new Chart(document.getElementById('chartEstado').getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: CHART_ESTADO.map(d => d.estado),
                datasets: [{ data: CHART_ESTADO.map(d => d.total), backgroundColor: COLORS, borderWidth: 0 }]
            },
            options: { ...chartOpts, plugins: { legend: { position: 'bottom', labels: { font: { family: 'Inter', size: 10 }, padding: 6, boxWidth: 10 } } } }
        });
    } catch (e) { console.error('Chart Estado:', e); }

    // === OUTBOUND 4: Tarimas Despachadas por Día (bar) ===
    try {
        new Chart(document.getElementById('chartTarimasOut').getContext('2d'), {
            type: 'bar',
            data: {
                labels: CHART_TARIMAS_OUT.map(d => d.dia ? d.dia.slice(5) : '?'),
                datasets: [{ label: 'Tarimas', data: CHART_TARIMAS_OUT.map(d => d.total), backgroundColor: '#f59e0b', borderRadius: 6 }]
            },
            options: { ...chartOpts, plugins: { legend: { display: false } }, scales: barGrid }
        });
    } catch (e) { console.error('Chart Tarimas Out:', e); }
}

// ===================================================
// 3. MODALES INTERACTIVOS
// ===================================================

function fmt(n) { return (n || 0).toLocaleString('es-MX'); }

const MODAL_CONFIG = {
    recibos: {
        title: '📋 Detalle de Recibos',
        desc: 'Últimos documentos de entrada recibidos en almacén.',
        data: () => ENTRADAS_DATA,
        fields: ['docto_id', 'referencia', 'fecha', 'cantidad', 'calidad', 'tarimas'],
        headers: ['Documento', 'Referencia', 'Fecha', 'Cant.', 'Calidad', 'Tarimas']
    },
    piezas_in: {
        title: '📦 Piezas Recibidas',
        summary: () => `<div class="info-row"><span class="info-label">Total acumulado</span><span class="info-val">${fmt(K.piezas_recibidas)} piezas</span></div><div class="info-row"><span class="info-label">En ${fmt(K.total_recibos)} recibos</span><span class="info-val">${K.total_recibos > 0 ? fmt(Math.round(K.piezas_recibidas / K.total_recibos)) + ' pzas/recibo' : '-'}</span></div>`,
        data: () => ENTRADAS_DATA,
        fields: ['docto_id', 'sku', 'cantidad'],
        headers: ['Documento', 'SKU', 'Cantidad']
    },
    skus: {
        title: '🏷️ SKUs Únicos Recibidos',
        summary: () => `<div class="info-row"><span class="info-label">Productos distintos</span><span class="info-val">${fmt(K.skus_unicos)}</span></div>`,
        data: () => CHART_TOP_SKUS,
        fields: ['descripcion', 'total'],
        headers: ['Producto', 'Cantidad Total']
    },
    tarimas_in: {
        title: '🎨 Tarimas Recibidas',
        summary: () => `<div class="info-row"><span class="info-label">Pallets procesados</span><span class="info-val">${fmt(K.tarimas_recibidas)}</span></div>`,
        data: () => ENTRADAS_DATA,
        fields: ['docto_id', 'fecha', 'tarimas'],
        headers: ['Documento', 'Fecha', 'Tarimas']
    },
    calidad: {
        title: '✅ Tasa de Calidad',
        summary: () => `<div class="info-row"><span class="info-label">Producto calidad A</span><span class="info-val">${K.tasa_calidad}%</span></div>`,
        data: () => CHART_CALIDAD,
        fields: ['tipo', 'total'],
        headers: ['Calidad', 'Registros']
    },
    pedidos: {
        title: '📑 Detalle de Pedidos',
        desc: 'Últimas órdenes de surtido procesadas.',
        data: () => SURTIDO_DATA,
        fields: ['docto_id', 'referencia', 'fecha', 'hora', 'cantidad_pedida', 'cantidad_surtida', 'estado'],
        headers: ['Pedido', 'Referencia', 'Fecha', 'Hora', 'Cant. Pedida', 'Surtido', 'Estado']
    },
    piezas_out: {
        title: '📤 Piezas Surtidas',
        summary: () => `<div class="info-row"><span class="info-label">Total despachado</span><span class="info-val">${fmt(K.piezas_surtidas)} piezas</span></div>`,
        data: () => SURTIDO_DATA,
        fields: ['docto_id', 'cantidad_surtida', 'fill_rate'],
        headers: ['Pedido', 'Surtido', 'Fill Rate']
    },
    fillrate: {
        title: '🚀 Avance de Surtido',
        summary: () => `<div class="info-row"><span class="info-label">Progreso actual</span><span class="info-val" style="font-size:1.5rem;color:${K.fill_rate >= 95 ? 'var(--green)' : K.fill_rate >= 80 ? 'var(--orange)' : 'var(--blue)'}">${K.fill_rate}%</span></div><div class="info-row"><span class="info-label">Meta</span><span class="info-val">100%</span></div>`,
        data: () => SURTIDO_DATA,
        fields: ['docto_id', 'fecha', 'hora', 'cantidad_pedida', 'cantidad_surtida', 'fill_rate', 'estado'],
        headers: ['Pedido', 'Fecha', 'Hora', 'Cant. Pedida', 'Surtido', '% Avance', 'Estado']
    },
    tarimas_out: {
        title: '🚛 Tarimas Despachadas',
        summary: () => `<div class="info-row"><span class="info-label">Pallets enviados</span><span class="info-val">${fmt(K.tarimas_despachadas)}</span></div>`,
        data: () => SURTIDO_DATA,
        fields: ['docto_id', 'fecha', 'hora', 'tarimas'],
        headers: ['Pedido', 'Fecha', 'Hora', 'Tarimas']
    },
    completados: {
        title: '🏁 Pedidos Completados',
        summary: () => `<div class="info-row"><span class="info-label">Tasa de finalización</span><span class="info-val">${K.pct_completados}%</span></div>`,
        data: () => SURTIDO_DATA,
        fields: ['docto_id', 'referencia', 'fecha', 'hora', 'estado', 'fill_rate'],
        headers: ['Pedido', 'Referencia', 'Fecha', 'Hora', 'Estado', 'Fill Rate']
    }
};

function openModal(key) {
    const cfg = MODAL_CONFIG[key];
    if (!cfg) return;

    const modal = document.getElementById('modal');
    const summary = document.getElementById('modal-summary');
    const table = document.getElementById('modal-table');

    document.getElementById('modal-title').innerText = cfg.title;
    summary.innerHTML = cfg.summary ? cfg.summary() : (cfg.desc ? `<p style="color:var(--muted);margin-bottom:0.5rem;">${cfg.desc}</p>` : '');

    const data = cfg.data();

    let html = '<thead><tr>';
    cfg.headers.forEach(h => html += `<th>${h}</th>`);
    html += '</tr></thead><tbody>';

    (Array.isArray(data) ? data : []).slice(0, 30).forEach(row => {
        html += '<tr>';
        cfg.fields.forEach(f => {
            let val = row[f];
            if (val === null || val === undefined || val === '') val = '—';
            if (f === 'fecha' && val !== '—') { try { val = new Date(val).toLocaleDateString('es-MX'); } catch (e) { } }
            if (f === 'fill_rate' && val !== '—') val = parseFloat(val).toFixed(1) + '%';
            if (f === 'calidad' && val !== '—') val = `<span class="pill ${val.toString().trim().toUpperCase() === 'A' ? 'pill-green' : 'pill-orange'}">${val}</span>`;
            if (f === 'estado' && val !== '—') val = `<span class="pill pill-blue">${val}</span>`;
            if (typeof val === 'number') val = fmt(val);
            html += `<td>${val}</td>`;
        });
        html += '</tr>';
    });

    if (!data || data.length === 0) {
        html += `<tr><td colspan="${cfg.headers.length}" style="text-align:center;color:var(--muted);padding:1.5rem;">Sin datos</td></tr>`;
    }

    html += '</tbody>';
    table.innerHTML = html;
    modal.classList.add('active');
}

function closeModal() {
    document.getElementById('modal').classList.remove('active');
}

document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

// ===================================================
// 4. INIT
// ===================================================

renderKPIs();
initCharts();
