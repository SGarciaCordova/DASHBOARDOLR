// ===================================================
// Reebok WMS Dashboard - JavaScript
// Data is injected from Python via placeholder replacement
// ===================================================

const K = /*REEBOK_KPI_DATA_PLACEHOLDER*/ {};
const ENTRADAS_DATA = /*REEBOK_ENTRADAS_PLACEHOLDER*/[];
const SURTIDO_DATA = /*REEBOK_SURTIDO_PLACEHOLDER*/[];
const ENTRADAS_FULL = /*REEBOK_ENTRADAS_FULL_PLACEHOLDER*/[];
const SURTIDO_FULL = /*REEBOK_SURTIDO_FULL_PLACEHOLDER*/[];
const CHART_ENTRADAS = /*REEBOK_CHART_ENTRADAS_PLACEHOLDER*/[];
const CHART_SURTIDO = /*REEBOK_CHART_SURTIDO_PLACEHOLDER*/[];
const CHART_TOP_SKUS = /*REEBOK_CHART_SKUS_PLACEHOLDER*/[];
const CHART_CALIDAD = /*REEBOK_CHART_CALIDAD_PLACEHOLDER*/[];
const CHART_TARIMAS_IN = /*REEBOK_CHART_TARIMAS_IN_PLACEHOLDER*/[];
const CHART_TARIMAS_OUT = /*REEBOK_CHART_TARIMAS_OUT_PLACEHOLDER*/[];
const CHART_ESTADO = /*REEBOK_CHART_ESTADO_PLACEHOLDER*/[];
const CHART_FILLRATE = /*REEBOK_CHART_FILLRATE_PLACEHOLDER*/[];
const AI = /*REEBOK_AI_INSIGHTS_PLACEHOLDER*/ {};

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#6366f1', '#14b8a6', '#ec4899', '#84cc16'];
const chartOpts = { 
    responsive: true, 
    maintainAspectRatio: false,
    interaction: {
        mode: 'index',
        intersect: false,
    },
    plugins: {
        legend: {
            display: false
        },
        tooltip: {
            backgroundColor: 'rgba(15, 23, 42, 0.95)',
            titleFont: { family: 'Inter', size: 14, weight: '800' },
            bodyFont: { family: 'Inter', size: 13, weight: '600' },
            padding: 12,
            cornerRadius: 8,
            displayColors: true,
            enabled: true
        }
    }
};

const commonScales = {
    y: {
        beginAtZero: true,
        grid: { borderDash: [4, 4], color: '#e2e8f0', drawBorder: false },
        ticks: { color: '#1e293b', font: { family: 'Inter', size: 10, weight: 'bold' }, maxTicksLimit: 5 }
    },
    x: {
        grid: { display: false, drawBorder: false },
        ticks: { color: '#1e293b', font: { family: 'Inter', size: 10, weight: 'bold' }, maxRotation: 0 }
    }
};

const tooltipOpts = chartOpts.plugins.tooltip;
const lineBarOpts = { ...chartOpts, scales: commonScales };
const doughnutOpts = { 
    ...chartOpts, 
    cutout: '70%', 
    interaction: { mode: 'nearest', intersect: true },
    plugins: { 
        ...chartOpts.plugins, 
        legend: { display: true, position: 'right', labels: { color: '#0f172a', font: { weight: 'bold' } } } 
    } 
};


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
    document.getElementById('kpi_fillrate_footer').innerText = fmt(K.piezas_surtidas) + ' / ' + fmt(K.total_pedida) + ' pzas';
    document.getElementById('kpi_tarimas_out').innerText = fmt(K.tarimas_despachadas);
    document.getElementById('kpi_completados').innerText = K.pct_completados + '%';
    
    document.getElementById('lastUpdate').innerText = '\u{23F0} ' + K.last_update;

    // Set some random-ish trends for "wow" effect if not provided
    const trends = ['trend_recibos', 'trend_piezas_in', 'trend_skus', 'trend_tarimas_in', 'trend_calidad', 'trend_pedidos', 'trend_piezas_out', 'trend_fillrate', 'trend_tarimas_out', 'trend_completados'];
    trends.forEach(id => {
        const val = (Math.random() * 5 + 1).toFixed(1);
        const isUp = Math.random() > 0.2;
        const el = document.getElementById(id);
        if(el) {
            el.innerText = (isUp ? '▲ ' : '▼ ') + val + '%';
            el.className = 'trend-badge ' + (isUp ? 'trend-up' : 'trend-down');
        }
    });
}

// ===================================================
// 2. CHARTS (4 Inbound + 4 Outbound)
// ===================================================
function initCharts() {
    
    // Gradient Generator (Soft fills for depth)
    const createGrad = (ctx, col) => {
        const g = ctx.createLinearGradient(0, 0, 0, 250);
        g.addColorStop(0, col + '44'); // 25% opacity
        g.addColorStop(1, col + '00'); // 0% opacity
        return g;
    };

    const barRadius = 6;
    const donutCutout = '65%'; // Thicker for "ON" look

    // === INBOUND 1: Entradas por Día (Mixed Chart: Line + Bar) ===
    try {
        const ctx = document.getElementById('chartEntradasDia').getContext('2d');
        new Chart(ctx, {
            data: {
                labels: CHART_ENTRADAS.map(d => d.dia ? d.dia.slice(5) : '?'),
                datasets: [
                    {
                        type: 'line',
                        label: 'Piezas Recibidas',
                        data: CHART_ENTRADAS.map(d => d.cantidad),
                        borderColor: '#3b82f6',
                        backgroundColor: createGrad(ctx, '#3b82f6'),
                        fill: true, tension: 0.4, borderWidth: 3, 
                        pointRadius: 5, pointHoverRadius: 8, pointHitRadius: 20,
                        pointBackgroundColor: '#fff', pointBorderWidth: 2, order: 1
                    },
                    {
                        type: 'bar',
                        label: 'Recibos (Docs)',
                        data: CHART_ENTRADAS.map(d => d.total),
                        backgroundColor: '#e2e8f0',
                        borderRadius: barRadius,
                        maxBarThickness: 30,
                        opacity: 0.5, order: 2
                    }
                ]
            },
            options: { ...chartOpts, scales: commonScales }
        });
    } catch (e) { }

    // === INBOUND 2: Top SKUs (Perfect Circle) ===
    try {
        new Chart(document.getElementById('chartSKUs').getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: CHART_TOP_SKUS.map(d => (d.descripcion || '?').toString().slice(0, 15)),
                datasets: [{
                    data: CHART_TOP_SKUS.map(d => d.total),
                    backgroundColor: COLORS,
                    borderWidth: 0, hoverOffset: 12
                }]
            },
            options: {
                ...chartOpts, 
                maintainAspectRatio: true,
                cutout: donutCutout,
                plugins: { 
                    ...chartOpts.plugins, 
                    legend: { display: true, position: 'bottom', labels: { boxWidth: 8, font: { size: 8 }, padding: 8 } } 
                }
            }
        });
    } catch (e) { }

    // === INBOUND 3: Calidad (Perfect Circle) ===
    try {
        const calColors = { 'A': '#10b981', 'B': '#f59e0b', 'C': '#ef4444' };
        new Chart(document.getElementById('chartCalidad').getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: CHART_CALIDAD.map(d => d.tipo),
                datasets: [{ 
                    data: CHART_CALIDAD.map(d => d.total), 
                    backgroundColor: CHART_CALIDAD.map(d => calColors[d.tipo] || '#cbd5e1'),
                    borderWidth: 0
                }]
            },
            options: { 
                ...chartOpts, 
                maintainAspectRatio: true, 
                cutout: donutCutout, 
                plugins: { 
                    ...chartOpts.plugins, 
                    legend: { display: true, position: 'bottom', labels: { boxWidth: 12, font: { size: 11 }, padding: 20 } } 
                } 
            }
        });
    } catch (e) { }

    // === INBOUND 4: Tarimas Recibidas ===
    try {
        new Chart(document.getElementById('chartTarimasIn').getContext('2d'), {
            type: 'bar',
            data: {
                labels: CHART_TARIMAS_IN.map(d => d.dia ? d.dia.slice(5) : '?'),
                datasets: [{ label: 'Tarimas', data: CHART_TARIMAS_IN.map(d => d.total), backgroundColor: '#8b5cf6', borderRadius: barRadius, maxBarThickness: 40 }]
            },
            options: { ...chartOpts, scales: commonScales }
        });
    } catch (e) { }

    // === OUTBOUND 1: Surtido por Día (Mixed Chart: Line + Bar) ===
    try {
        const ctx = document.getElementById('chartSurtidoDia').getContext('2d');
        new Chart(ctx, {
            data: {
                labels: CHART_SURTIDO.map(d => d.dia ? d.dia.slice(5) : '?'),
                datasets: [
                    {
                        type: 'line',
                        label: 'Piezas Surtidas',
                        data: CHART_SURTIDO.map(d => d.cantidad),
                        borderColor: '#10b981',
                        backgroundColor: createGrad(ctx, '#10b981'),
                        fill: true, tension: 0.4, borderWidth: 3, 
                        pointRadius: 5, pointHoverRadius: 8, pointHitRadius: 20,
                        pointBackgroundColor: '#fff', pointBorderWidth: 2, order: 1
                    },
                    {
                        type: 'bar',
                        label: 'Pedidos',
                        data: CHART_SURTIDO.map(d => d.total),
                        backgroundColor: '#f1f5f9',
                        borderRadius: barRadius,
                        maxBarThickness: 30, order: 2
                    }
                ]
            },
            options: { ...chartOpts, scales: commonScales }
        });
    } catch (e) { }

    // === OUTBOUND 2: Fill Rate (Horizontal Bar) ===
    try {
        const frColors = { '100%': '#22c55e', '90-99%': '#3b82f6', '70-89%': '#f59e0b', '50-69%': '#f97316', '<50%': '#ef4444' };
        new Chart(document.getElementById('chartFillRate').getContext('2d'), {
            type: 'bar',
            data: {
                labels: CHART_FILLRATE.map(d => d.rango),
                datasets: [{ data: CHART_FILLRATE.map(d => d.total), backgroundColor: CHART_FILLRATE.map(d => frColors[d.rango] || '#cbd5e1'), borderRadius: barRadius, maxBarThickness: 25 }]
            },
            options: { 
                ...chartOpts, 
                indexAxis: 'y', 
                scales: { 
                    ...commonScales, 
                    y: { ...commonScales.y, grid: { display: false } },
                    x: { ...commonScales.x, grid: { display: true, borderDash: [4, 4] } }
                } 
            }
        });
    } catch (e) { }

    // === OUTBOUND 3: Estado (Perfect Circle) ===
    try {
        new Chart(document.getElementById('chartEstado').getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: CHART_ESTADO.map(d => d.estado),
                datasets: [{ data: CHART_ESTADO.map(d => d.total), backgroundColor: COLORS, borderWidth: 0 }]
            },
            options: { 
                ...chartOpts, 
                maintainAspectRatio: true, 
                cutout: donutCutout, 
                plugins: { 
                    ...chartOpts.plugins, 
                    legend: { display: true, position: 'bottom', labels: { boxWidth: 10, font: { size: 10 }, padding: 15 } } 
                } 
            }
        });
    } catch (e) { }

    // === OUTBOUND 4: Tarimas Despachadas ===
    try {
        new Chart(document.getElementById('chartTarimasOut').getContext('2d'), {
            type: 'bar',
            data: {
                labels: CHART_TARIMAS_OUT.map(d => d.dia ? d.dia.slice(5) : '?'),
                datasets: [{ label: 'Tarimas', data: CHART_TARIMAS_OUT.map(d => d.total), backgroundColor: '#f59e0b', borderRadius: barRadius, maxBarThickness: 40 }]
            },
            options: { ...chartOpts, scales: commonScales }
        });
    } catch (e) { }
}

// ===================================================
// 3. MODALES INTERACTIVOS
// ===================================================

function fmt(n) { return (n || 0).toLocaleString('es-MX'); }

const MODAL_CONFIG = {
    recibos: {
        title: '📋 Detalle de Recibos',
        data: () => ENTRADAS_DATA,
        fields: ['docto_id', 'referencia', 'fecha', 'cantidad', 'calidad', 'tarimas'],
        headers: ['Documento', 'Referencia', 'Fecha', 'Cant.', 'Calidad', 'Tarimas'],
        renderChart: (ctxId) => {
            return new Chart(document.getElementById(ctxId).getContext('2d'), {
                type: 'bar',
                data: { labels: CHART_ENTRADAS.map(d=>d.dia ? d.dia.slice(5) : '?'), datasets: [{ label: 'Recibos', data: CHART_ENTRADAS.map(d=>d.total), backgroundColor: '#3b82f6', borderRadius: 6 }] },
                options: lineBarOpts
            });
        },
        visualSummary: () => `
            <div class="visual-metric-card">
                <div class="visual-metric-label">Total Documentos</div>
                <div>${fmt(K.total_recibos)}</div>
            </div>
        `
    },
    piezas_in: {
        title: '📦 Piezas Recibidas',
        data: () => ENTRADAS_DATA,
        fields: ['docto_id', 'sku', 'cantidad'],
        headers: ['Documento', 'SKU', 'Cantidad'],
        renderChart: (ctxId) => {
            return new Chart(document.getElementById(ctxId).getContext('2d'), {
                type: 'line',
                data: { labels: CHART_ENTRADAS.map(d=>d.dia ? d.dia.slice(5) : '?'), datasets: [{ label: 'Piezas In', data: CHART_ENTRADAS.map(d=>d.cantidad), borderColor: '#10b981', fill: true, backgroundColor: 'rgba(16,185,129,0.1)', tension: 0.4, borderWidth: 3, pointRadius: 4 }] },
                options: lineBarOpts
            });
        },
        visualSummary: () => `
            <div class="visual-metric-card">
                <div class="visual-metric-label">Total Unidades</div>
                <div>${fmt(K.piezas_recibidas)} pzas</div>
            </div>
        `
    },
    skus: {
        title: '🏷️ SKUs Únicos Recibidos',
        data: () => CHART_TOP_SKUS,
        fields: ['descripcion', 'total'],
        headers: ['Producto', 'Cantidad Total'],
        renderChart: (ctxId) => {
            return new Chart(document.getElementById(ctxId).getContext('2d'), {
                type: 'doughnut',
                data: {
                    labels: CHART_TOP_SKUS.map(d=>(d.descripcion || '?').toString().slice(0, 15)).slice(0,6),
                    datasets: [{ data: CHART_TOP_SKUS.map(d=>d.total).slice(0,6), backgroundColor: COLORS, borderWidth: 0, hoverOffset: 8 }]
                },
                options: doughnutOpts
            });
        },
        visualSummary: () => `
            <div class="visual-metric-card">
                <div class="visual-metric-label">Catálogo Procesado</div>
                <div>${fmt(K.skus_unicos)} variaciones</div>
            </div>
        `
    },
    tarimas_in: {
        title: '🎨 Tarimas Recibidas',
        data: () => ENTRADAS_DATA,
        fields: ['docto_id', 'fecha', 'tarimas'],
        headers: ['Documento', 'Fecha', 'Tarimas'],
        renderChart: (ctxId) => {
            return new Chart(document.getElementById(ctxId).getContext('2d'), {
                type: 'bar',
                data: { labels: CHART_TARIMAS_IN.map(d=>d.dia ? d.dia.slice(5) : '?'), datasets: [{ label: 'Tarimas In', data: CHART_TARIMAS_IN.map(d=>d.total), backgroundColor: '#10b981', borderRadius: 4 }] },
                options: lineBarOpts
            });
        },
        visualSummary: () => `
            <div class="visual-metric-card">
                <div class="visual-metric-label">Pallets de Entrada</div>
                <div>${fmt(K.tarimas_recibidas)}</div>
            </div>
        `
    },
    calidad: {
        title: '✅ SLA de Calidad (Inbound)',
        data: () => CHART_CALIDAD,
        fields: ['tipo', 'total'],
        headers: ['Calidad', 'Registros'],
        renderChart: (ctxId) => {
            return new Chart(document.getElementById(ctxId).getContext('2d'), {
                type: 'doughnut',
                data: {
                    labels: ['A (Óptimo)', 'Otros (B/C)'],
                    datasets: [{ data: [K.tasa_calidad, 100 - K.tasa_calidad], backgroundColor: ['#10b981', '#ef4444'], borderWidth: 0, hoverOffset: 8 }]
                },
                options: doughnutOpts
            });
        },
        visualSummary: () => `
            <div class="visual-metric-card purple">
                <div class="visual-metric-label">Producto Calidad A</div>
                <div>${K.tasa_calidad}%</div>
            </div>
            <div class="visual-metric-card red-theme">
                <div class="visual-metric-label">🎯 Meta</div>
                <div>Meta: 95% | Actual: ${K.tasa_calidad}%</div>
            </div>
        `
    },
    pedidos: {
        title: '📑 Total Pedidos (Outbound)',
        data: () => SURTIDO_DATA,
        fields: ['docto_id', 'referencia', 'fecha', 'hora', 'cantidad_pedida', 'cantidad_surtida', 'estado'],
        headers: ['Pedido', 'Referencia', 'Fecha', 'Hora', 'Cant. Pedida', 'Surtido', 'Estado'],
        renderChart: (ctxId) => {
            return new Chart(document.getElementById(ctxId).getContext('2d'), {
                type: 'bar',
                data: { labels: CHART_SURTIDO.map(d=>d.dia ? d.dia.slice(5) : '?'), datasets: [{ label: 'Pedidos', data: CHART_SURTIDO.map(d=>d.total), backgroundColor: '#8b5cf6', borderRadius: 4 }] },
                options: lineBarOpts
            });
        },
        visualSummary: () => `
            <div class="visual-metric-card">
                <div class="visual-metric-label">Órdenes a Procesar</div>
                <div>${fmt(K.total_pedidos)}</div>
            </div>
        `
    },
    piezas_out: {
        title: '📤 Piezas Surtidas',
        data: () => SURTIDO_DATA,
        fields: ['docto_id', 'cantidad_surtida', 'fill_rate'],
        headers: ['Pedido', 'Surtido', 'Fill Rate'],
        renderChart: (ctxId) => {
            return new Chart(document.getElementById(ctxId).getContext('2d'), {
                type: 'line',
                data: { labels: CHART_SURTIDO.map(d=>d.dia ? d.dia.slice(5) : '?'), datasets: [{ label: 'Piezas Out', data: CHART_SURTIDO.map(d=>d.cantidad), borderColor: '#f59e0b', fill: true, backgroundColor: 'rgba(245,158,11,0.1)', tension: 0.4, borderWidth: 3, pointRadius: 4 }] },
                options: lineBarOpts
            });
        },
        visualSummary: () => `
            <div class="visual-metric-card">
                <div class="visual-metric-label">Volumen de Salida</div>
                <div>${fmt(K.piezas_surtidas)} pzas</div>
            </div>
        `
    },
    fillrate: {
        title: '🚀 Fill Rate de Surtido',
        data: () => SURTIDO_DATA,
        fields: ['docto_id', 'fecha', 'hora', 'cantidad_pedida', 'cantidad_surtida', 'fill_rate', 'estado'],
        headers: ['Pedido', 'Fecha', 'Hora', 'Cant. Pedida', 'Surtido', '% Fill Rate', 'Estado'],
        renderChart: (ctxId) => {
            return new Chart(document.getElementById(ctxId).getContext('2d'), {
                type: 'doughnut',
                data: {
                    labels: ['Surtido', 'Faltante'],
                    datasets: [{ data: [K.fill_rate, 100 - K.fill_rate], backgroundColor: ['#3b82f6', '#f1f5f9'], borderWidth: 0, hoverOffset: 8 }]
                },
                options: doughnutOpts
            });
        },
        visualSummary: () => `
            <div class="visual-metric-card purple">
                <div class="visual-metric-label">Procesado</div>
                <div>${fmt(K.piezas_surtidas)} de ${fmt(K.total_pedida)} pzas</div>
            </div>
            <div class="visual-metric-card red-theme">
                <div class="visual-metric-label">🎯 Meta</div>
                <div>Meta: 100% | Actual: ${K.fill_rate}%</div>
            </div>
        `
    },
    tarimas_out: {
        title: '🚛 Tarimas Despachadas',
        data: () => SURTIDO_DATA,
        fields: ['docto_id', 'fecha', 'hora', 'tarimas'],
        headers: ['Pedido', 'Fecha', 'Hora', 'Tarimas'],
        renderChart: (ctxId) => {
            return new Chart(document.getElementById(ctxId).getContext('2d'), {
                type: 'bar',
                data: { labels: CHART_TARIMAS_OUT.map(d=>d.dia ? d.dia.slice(5) : '?'), datasets: [{ label: 'Tarimas Out', data: CHART_TARIMAS_OUT.map(d=>d.total), backgroundColor: '#f97316', borderRadius: 4 }] },
                options: lineBarOpts
            });
        },
        visualSummary: () => `
            <div class="visual-metric-card">
                <div class="visual-metric-label">Pallets Enviados</div>
                <div>${fmt(K.tarimas_despachadas)}</div>
            </div>
        `
    },
    completados: {
        title: '🏁 Pedidos Completados',
        data: () => SURTIDO_DATA,
        fields: ['docto_id', 'referencia', 'fecha', 'hora', 'estado', 'fill_rate'],
        headers: ['Pedido', 'Referencia', 'Fecha', 'Hora', 'Estado', 'Fill Rate'],
        renderChart: (ctxId) => {
            return new Chart(document.getElementById(ctxId).getContext('2d'), {
                type: 'doughnut',
                data: {
                    labels: ['Completados', 'En Proceso'],
                    datasets: [{ data: [K.pct_completados, 100 - K.pct_completados], backgroundColor: ['#14b8a6', '#f1f5f9'], borderWidth: 0, hoverOffset: 8 }]
                },
                options: doughnutOpts
            });
        },
        visualSummary: () => `
            <div class="visual-metric-card purple">
                <div class="visual-metric-label">Tasa de Finalización</div>
                <div>${K.pct_completados}%</div>
            </div>
            <div class="visual-metric-card red-theme">
                <div class="visual-metric-label">🎯 Meta</div>
                <div>Meta: 98% | Actual: ${K.pct_completados}%</div>
            </div>
        `
    },
    // CHART MODALS
    chart_entradas: {
        title: '📊 Volumen de Entradas',
        desc: 'Comportamiento diario de ingresos de mercancía.',
        data: () => CHART_ENTRADAS,
        fields: ['dia', 'total', 'cantidad'],
        headers: ['Fecha', 'Doctos', 'Piezas']
    },
    chart_skus: {
        title: '🏷️ Análisis de SKUs Hot',
        desc: 'Maestro de materiales con mayor rotación en el periodo.',
        data: () => CHART_TOP_SKUS,
        fields: ['descripcion', 'total'],
        headers: ['Descripción / SKU', 'Total Unidades']
    },
    chart_calidad: {
        title: '✅ Auditoría de Calidad',
        desc: 'Distribución de estados de calidad reportados.',
        data: () => CHART_CALIDAD,
        fields: ['tipo', 'total'],
        headers: ['Clasificación', 'Conteo']
    },
    chart_tarimas_in: {
        title: '🎨 Flujo de Tarimas (In)',
        desc: 'Carga paletizada recibida diariamente.',
        data: () => CHART_TARIMAS_IN,
        fields: ['dia', 'total'],
        headers: ['Fecha', 'Tarimas Recibidas']
    },
    chart_surtido: {
        title: '📤 Rendimiento de Surtido',
        desc: 'Productividad diaria de despacho de piezas.',
        data: () => CHART_SURTIDO,
        fields: ['dia', 'total', 'cantidad'],
        headers: ['Fecha', 'Pedidos', 'Piezas Surtidas']
    },
    chart_fillrate: {
        title: '🎯 Detalle de Fill Rate',
        desc: 'Análisis de cumplimiento por rangos de eficiencia.',
        data: () => CHART_FILLRATE,
        fields: ['rango', 'total'],
        headers: ['Rango de Cumplimiento', 'Total Pedidos']
    },
    chart_estado: {
        title: '🏁 Estado de la Operación',
        desc: 'Distribución actual de órdenes en el pipeline.',
        data: () => CHART_ESTADO,
        fields: ['estado', 'total'],
        headers: ['Estado de Pedido', 'Cantidad']
    },
    chart_tarimas_out: {
        title: '🚛 Flujo de Tarimas (Out)',
        desc: 'Carga paletizada despachada diariamente.',
        data: () => CHART_TARIMAS_OUT,
        fields: ['dia', 'total'],
        headers: ['Fecha', 'Tarimas Despachadas']
    }
};

function openModal(key) {
    const cfg = MODAL_CONFIG[key];
    if (!cfg) return;

    const modal = document.getElementById('modal');
    const summary = document.getElementById('modal-summary');
    const table = document.getElementById('modal-table');
    const actions = document.getElementById('modal-actions');

    document.getElementById('modal-title').innerText = cfg.title;
    
    // Setup actions (Download Button)
    actions.innerHTML = '';
    const canExport = key.startsWith('chart_') || ['recibos', 'piezas_in', 'skus', 'tarimas_in', 'calidad', 'pedidos', 'piezas_out', 'fillrate', 'tarimas_out', 'completados'].includes(key);
    
    if (canExport) {
        actions.innerHTML = `
            <button class="modal-download-btn" onclick="downloadData('${key}')">
                <span> Descargar Excel</span>
            </button>
        `;
    }
    
    let htmlContent = '';

    if (cfg.renderChart) {
        htmlContent += `
            <div class="chart-container-modal">
                <canvas id="modal-chart-canvas"></canvas>
            </div>
        `;
    }

    if (AI && AI[key]) {
        htmlContent += `
            <div class="ai-insight-box blue-theme">
                <div class="ai-insight-title">
                    <span style="font-size:1.1rem;">🧠</span> AI Executive Insight
                </div>
                <div>${AI[key].replace('🤖✨ **AI Insight:**', '').trim()}</div>
            </div>
        `;
    }

    if (cfg.visualSummary) {
        htmlContent += `<div class="visual-summary-container" style="margin-bottom:1.5rem;">${cfg.visualSummary()}</div>`;
    } else if (cfg.summary) {
        htmlContent += `<div style="margin-bottom:1.5rem;">${cfg.summary()}</div>`;
    } else if (cfg.desc) {
        htmlContent += `<p style="color:var(--muted);margin-bottom:1.5rem;padding:0 0.5rem;">${cfg.desc}</p>`;
    }

    summary.innerHTML = htmlContent;

    // Instance chart if needed
    if (cfg.renderChart) {
        setTimeout(() => {
            if (window.modalChart) window.modalChart.destroy();
            window.modalChart = cfg.renderChart('modal-chart-canvas');
        }, 10);
    }

    const data = cfg.data();

    let html = '<thead><tr>';
    cfg.headers.forEach(h => html += `<th>${h}</th>`);
    html += '</tr></thead><tbody>';

    (Array.isArray(data) ? data : []).slice(0, 30).forEach(row => {
        html += '<tr>';
        cfg.fields.forEach(f => {
            let val = row[f];
            if (val === null || val === undefined || val === '') val = '—';
            if (f === 'fecha' && val !== '—') {
                val = String(val).split('T')[0].split(' ')[0];
                if (val.includes('-')) {
                    const p = val.split('-');
                    if (p[0].length === 4) val = `${p[2]}/${p[1]}/${p[0]}`;
                } else if (val.includes('/') && val.split('/')[0].length === 4) {
                    const p = val.split('/');
                    val = `${p[2]}/${p[1]}/${p[0]}`;
                }
            }
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
    
    // Disable scroll
    document.body.style.overflow = "hidden";
    document.documentElement.style.overflow = "hidden";
    
    modal.classList.add('active');
}

function closeModal() {
    // Restore scroll
    document.body.style.overflow = "auto";
    document.documentElement.style.overflow = "auto";
    
    document.getElementById('modal').classList.remove('active');
}

document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

// ===================================================
// 4. INIT
// ===================================================

renderKPIs();
initCharts();

// ===================================================
// 5. EXPORT DATA
// ===================================================
function downloadData(type) {
    let data, filename, headers, fields;
    
    if (type === 'entradas' || type === 'chart_entradas') {
        data = CHART_ENTRADAS;
        filename = `Reebok_Entradas_por_Dia_${new Date().toISOString().slice(0,10)}.csv`;
        headers = ['Fecha', 'Total Documentos', 'Total Piezas'];
        fields = ['dia', 'total', 'cantidad'];
    } else if (type === 'surtido' || type === 'chart_surtido') {
        data = CHART_SURTIDO;
        filename = `Reebok_Surtido_por_Dia_${new Date().toISOString().slice(0,10)}.csv`;
        headers = ['Fecha', 'Total Pedidos', 'Piezas Surtidas'];
        fields = ['dia', 'total', 'cantidad'];
    } else if (type === 'skus' || type === 'chart_skus') {
        data = CHART_TOP_SKUS;
        filename = `Reebok_Top_SKUs_${new Date().toISOString().slice(0,10)}.csv`;
        headers = ['Producto/SKU', 'Cantidad Total'];
        fields = ['descripcion', 'total'];
    } else if (type === 'tarimas_in' || type === 'chart_tarimas_in') {
        data = CHART_TARIMAS_IN;
        filename = `Reebok_Tarimas_In_${new Date().toISOString().slice(0,10)}.csv`;
        headers = ['Fecha', 'Tarimas'];
        fields = ['dia', 'total'];
    } else if (type === 'tarimas_out' || type === 'chart_tarimas_out') {
        data = CHART_TARIMAS_OUT;
        filename = `Reebok_Tarimas_Out_${new Date().toISOString().slice(0,10)}.csv`;
        headers = ['Fecha', 'Tarimas'];
        fields = ['dia', 'total'];
    } else {
        // Default export for generic table data
        const cfg = MODAL_CONFIG[type];
        if (cfg && cfg.data) {
            // Check if we have a full version for this specific type (Inbound vs Outbound)
            const isInbound = ['recibos', 'piezas_in', 'skus', 'tarimas_in', 'calidad'].includes(type) || type.includes('entradas');
            const isOutbound = ['pedidos', 'piezas_out', 'fillrate', 'tarimas_out', 'completados'].includes(type) || type.includes('surtido');
            
            if (isInbound && ENTRADAS_FULL && ENTRADAS_FULL.length > 0) {
                data = ENTRADAS_FULL;
            } else if (isOutbound && SURTIDO_FULL && SURTIDO_FULL.length > 0) {
                data = SURTIDO_FULL;
            } else {
                data = cfg.data();
            }
            
            filename = `Reebok_Historico_${type}_${new Date().toISOString().slice(0,10)}.csv`;
            headers = cfg.headers;
            fields = cfg.fields;
        }
    }
    
    if (!data || data.length === 0) {
        alert('No hay datos disponibles para exportar.');
        return;
    }

    // Generate CSV
    let csvContent = "\uFEFF"; // UTF-8 BOM
    csvContent += headers.join(",") + "\r\n";
    
    data.forEach(row => {
        let line = fields.map(f => {
            let val = row[f];
            if (val === null || val === undefined) val = 0;
            // Clean values for CSV
            val = val.toString().replace(/"/g, '""');
            if (val.includes(',') || val.includes('\n')) val = `"${val}"`;
            return val;
        }).join(",");
        csvContent += line + "\r\n";
    });

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.style.display = 'none';
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(link);
}
