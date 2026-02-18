// Placeholder for injected data
const K = /*KPI_DATA_PLACEHOLDER*/ {};
const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];
const STATUS_COLORS = /*STATUS_COLORS_PLACEHOLDER*/ {};

function initCharts() {
    // Compliance Donut
    if (K.comp_chart.length) {
        new Chart(document.getElementById('compChart'), {
            type: 'doughnut',
            data: { labels: K.comp_chart.map(d => d.Estado), datasets: [{ data: K.comp_chart.map(d => d.Cantidad), backgroundColor: ['#10b981', '#ef4444'], borderWidth: 0 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 9 } } } } }
        });
    }
    // Volume Bar (Updated to Piezas)
    if (K.trend_data.length) {
        new Chart(document.getElementById('volChart'), {
            type: 'bar',
            data: { labels: K.trend_data.map(d => 'W' + d.SEMANA), datasets: [{ data: K.trend_data.map(d => d.Total_Piezas), backgroundColor: '#3b82f6', borderRadius: 4 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
        });
    }
    // Trend & OTD Lines
    if (K.weekly_data.length) {
        new Chart(document.getElementById('trendChart'), {
            type: 'bar',
            data: {
                labels: K.weekly_data.map(d => 'S' + d.SEMANA),
                datasets: [
                    {
                        type: 'line',
                        label: 'Piezas',
                        data: K.weekly_data.map(d => d.Surtido || 0),
                        borderColor: '#8b5cf6',
                        yAxisID: 'y',
                        tension: 0.4,
                        borderWidth: 2,
                        pointRadius: 2
                    },
                    {
                        type: 'bar',
                        label: 'Órdenes',
                        data: K.weekly_data.map(d => d.Ordenes),
                        backgroundColor: '#e2e8f0',
                        yAxisID: 'y1',
                        borderRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { display: false },
                    y1: { display: false, grid: { display: false } }
                }
            }
        });
        new Chart(document.getElementById('otdChart'), {
            type: 'line',
            data: { labels: K.weekly_data.map(d => 'S' + d.SEMANA), datasets: [{ data: K.weekly_data.map(d => d.OTD * 100), borderColor: '#8b5cf6', backgroundColor: 'rgba(139,92,246,0.1)', tension: 0.4, fill: true }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { min: 0, max: 110 } } }
        });
    }
    // Type Distribution
    if (K.vol_data.length) {
        new Chart(document.getElementById('tipoChart'), {
            type: 'pie',
            data: { labels: K.vol_data.map(d => d['TIPO DE MERCANCIA']), datasets: [{ data: K.vol_data.map(d => d.Total_Piezas), backgroundColor: COLORS, borderWidth: 0 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 9 } } } } }
        });
    }
    // Status Distribution
    if (K.status_data.length) {
        new Chart(document.getElementById('statusChart'), {
            type: 'doughnut',
            data: {
                labels: K.status_data.map(d => d.Status),
                datasets: [{
                    data: K.status_data.map(d => d.Cantidad),
                    backgroundColor: K.status_data.map(d => STATUS_COLORS[d.Status] || '#cbd5e1'),
                    borderWidth: 0
                }]
            },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 9 } } } } }
        });
    }
    // Client Bar
    if (K.client_data.length) {
        new Chart(document.getElementById('clientChart'), {
            type: 'bar',
            data: { labels: K.client_data.map(d => d.CLIENTE), datasets: [{ data: K.client_data.map(d => d.Total_Piezas), backgroundColor: '#8b5cf6', borderRadius: 4 }] },
            options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
        });
    }
    // Pipeline
    if (K.pipeline_data.length) {
        new Chart(document.getElementById('pipeChart'), {
            type: 'bar',
            data: { labels: K.pipeline_data.map(d => d.Etapa), datasets: [{ data: K.pipeline_data.map(d => d.Piezas), backgroundColor: COLORS, borderRadius: 4 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
        });
    }
}

function toggleTech() {
    const t = document.getElementById('modalTech');
    t.style.display = t.style.display === 'block' ? 'none' : 'block';
}


let modalChartInstance = null;

function renderModalChart(type, d) {
    const ctx = document.getElementById('modalChartCanvas').getContext('2d');
    if (modalChartInstance) { modalChartInstance.destroy(); }

    // Default Chart Config
    let config = null;

    if (type === 'cumpl_72h') {
        config = {
            type: 'doughnut',
            data: { labels: ['A Tiempo', 'Fuera de SLA'], datasets: [{ data: [d.cumple, d.total - d.cumple], backgroundColor: ['#10b981', '#ef4444'], borderWidth: 0 }] },
            options: { responsive: true, maintainAspectRatio: false, cutout: '75%', plugins: { legend: { position: 'right', labels: { boxWidth: 10, usePointStyle: true } } } }
        };
    } else if (type === 'report_time') {
        // Fallback if accessed via URL or legacy
        config = {
            type: 'doughnut',
            data: { labels: ['A Tiempo', 'Tarde'], datasets: [{ data: [d.on_time, d.late || 0], backgroundColor: ['#3b82f6', '#ef4444'], borderWidth: 0 }] },
            options: { responsive: true, maintainAspectRatio: false, cutout: '75%', plugins: { legend: { position: 'right' } } }
        };
    } else if (type === 'tiempo_ing') {
        // Gauge-like or simple Bar for avg
        config = {
            type: 'bar',
            data: { labels: ['Mín', 'Promedio', 'Máx'], datasets: [{ data: [d.min, d.promedio, d.max], backgroundColor: ['#10b981', '#3b82f6', '#f59e0b'], borderRadius: 4 }] },
            options: { responsive: true, maintainAspectRatio: false, indexAxis: 'y', plugins: { legend: { display: false } } }
        };
    } else if (type === 'vol_recib') {
        config = {
            type: 'pie',
            data: { labels: ['Calzado', 'Ropa/Otros', 'Tarimas'], datasets: [{ data: [d.calzado, d.otros, d.tarimas], backgroundColor: ['#3b82f6', '#8b5cf6', '#64748b'], borderWidth: 0 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'right', labels: { boxWidth: 10 } } } }
        };
    } else if (type === 'tiempo_extra') {
        config = {
            type: 'doughnut',
            data: { labels: ['En SLA', 'Breach (>72h)'], datasets: [{ data: [d.total - d.excedidos, d.excedidos], backgroundColor: ['#e5e7eb', '#ef4444'], borderWidth: 0 }] },
            options: { responsive: true, maintainAspectRatio: false, cutout: '75%', plugins: { legend: { position: 'right', labels: { boxWidth: 10, usePointStyle: true } } } }
        };
    } else if (type === 'efic_desc') {
        config = {
            type: 'doughnut',
            data: { labels: ['En Meta (≤2d)', 'Fuera de Meta'], datasets: [{ data: [d.en_meta, d.sobre_meta], backgroundColor: ['#10b981', '#f59e0b'], borderWidth: 0 }] },
            options: { responsive: true, maintainAspectRatio: false, cutout: '75%', plugins: { legend: { position: 'right', labels: { boxWidth: 10, usePointStyle: true } } } }
        };
    } else if (type === 'audit_quality') {
        config = {
            type: 'doughnut',
            data: { labels: ['Aprobado', 'Fallido'], datasets: [{ data: [d.passed, d.total - d.passed], backgroundColor: ['#10b981', '#f59e0b'], borderWidth: 0 }] },
            options: { responsive: true, maintainAspectRatio: false, cutout: '75%', plugins: { legend: { position: 'right', labels: { boxWidth: 10, usePointStyle: true } } } }
        };
    } else if (type === 'pct_surtido') {
        config = {
            type: 'doughnut',
            data: { labels: ['Surtido', 'Pendiente'], datasets: [{ data: [d.surtido, d.pendiente], backgroundColor: ['#10b981', '#e5e7eb'], borderWidth: 0 }] },
            options: { responsive: true, maintainAspectRatio: false, cutout: '75%', plugins: { legend: { position: 'right', labels: { boxWidth: 10, usePointStyle: true } } } }
        };
    } else if (type === 'avance_etapa') {
        config = {
            type: 'bar',
            data: { labels: ['Surtido', 'Etiquetado', 'Distrib.', 'Audit.'], datasets: [{ data: [d.surtido, d.etiquetado, d.distribucion, d.auditoria], backgroundColor: ['#3b82f6', '#8b5cf6', '#f59e0b', '#10b981'], borderRadius: 4 }] },
            options: { responsive: true, maintainAspectRatio: false, scales: { y: { max: 100 } }, plugins: { legend: { display: false } } }
        };
    } else if (type === 'cumpl_entrega') {
        config = {
            type: 'doughnut',
            data: { labels: ['A Tiempo', 'Tarde'], datasets: [{ data: [d.on_time, d.late], backgroundColor: ['#8b5cf6', '#ef4444'], borderWidth: 0 }] },
            options: { responsive: true, maintainAspectRatio: false, cutout: '75%', plugins: { legend: { position: 'right', labels: { boxWidth: 10, usePointStyle: true } } } }
        };
    } else if (type === 'backlog') {
        // Dynamic labels from all_status
        const labels = Object.keys(d.all_status || {});
        const values = Object.values(d.all_status || {});
        config = {
            type: 'doughnut',
            data: { labels: labels, datasets: [{ data: values, backgroundColor: ['#10b981', '#ef4444', '#f59e0b', '#3b82f6', '#64748b'], borderWidth: 0 }] },
            options: { responsive: true, maintainAspectRatio: false, cutout: '75%', plugins: { legend: { position: 'right', labels: { boxWidth: 10, font: { size: 10 } } } } }
        };
    } else if (type === 'vol_surtido') {
        config = {
            type: 'bar',
            data: {
                labels: (d.by_week || []).map(x => 'S' + x.SEMANA),
                datasets: [
                    {
                        type: 'line',
                        label: 'Piezas',
                        data: (d.by_week || []).map(x => x.Surtido),
                        borderColor: '#8b5cf6',
                        backgroundColor: '#8b5cf6',
                        yAxisID: 'y',
                        tension: 0.4,
                        borderWidth: 2,
                        pointRadius: 3
                    },
                    {
                        type: 'bar',
                        label: 'Órdenes',
                        data: (d.by_week || []).map(x => x.Ordenes),
                        backgroundColor: '#e5e7eb',
                        yAxisID: 'y1',
                        borderRadius: 4,
                        barThickness: 20
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: true, position: 'bottom' } },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: { display: true, text: 'Piezas' },
                        grid: { display: false }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: { display: true, text: 'Órdenes' },
                        grid: { drawOnChartArea: false }
                    }
                }
            }
        };
    } else if (type === 'desemp_cliente') {
        config = {
            type: 'bar',
            data: { labels: d.map(x => x.CLIENTE.substring(0, 10) + '...'), datasets: [{ data: d.map(x => x.Piezas), backgroundColor: '#3b82f6', borderRadius: 4 }] },
            options: { responsive: true, maintainAspectRatio: false, indexAxis: 'y', plugins: { legend: { display: false } } }
        };
    } else if (type === 'wip_metrics') {
        // New WIP Histogram Chart
        const labels = Object.keys(d.distribution || {});
        const values = Object.values(d.distribution || {});
        config = {
            type: 'bar',
            data: { labels: labels, datasets: [{ label: 'Órdenes', data: values, backgroundColor: '#3b82f6', borderRadius: 4 }] },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, title: { display: true, text: 'Cantidad de Órdenes' } },
                    x: { title: { display: true, text: '% de Avance' } }
                }
            }
        };
    }

    // Render if config exists, else hide canvas
    const container = document.querySelector('.chart-container');
    if (config) {
        container.style.display = 'block';
        modalChartInstance = new Chart(ctx, config);
    } else {
        container.style.display = 'none';
    }
}

function showModal(type) {
    // Format: [Title, BodyHtml, TechLogic, SourceCols]
    const T = {
        'cumpl_72h': () => {
            const d = K.cumpl_72h;
            renderModalChart('cumpl_72h', d);
            return ['⏰ SLA Compliance (72h)',
                `<div class="info-box">${d.cumple} de ${d.total} cumplen SLA = ${d.pct.toFixed(1)}%</div><div class="info-section"><div class="info-title">🎯 Meta</div><div class="info-box" style="color:${d.pct >= 95 ? '#10b981' : '#ef4444'}">Meta: 95% | Actual: ${d.pct.toFixed(1)}%</div></div>`,
                'Conteo directo de Columna "CUMPLIMIENTO" (CUMPLE vs NO). Vacíos excluidos.', 'CUMPLIMIENTO 72 HORAS (Columna AK)'];
        },
        'tiempo_ing': () => {
            const d = K.tiempo_ing;
            renderModalChart('tiempo_ing', d);
            return ['⏱️ Dock to Stock Time',
                `<div class="info-box">Promedio: ${d.promedio.toFixed(1)} días</div><ul class="info-list"><li>Mín: ${d.min} días</li><li>Max: ${d.max} días</li><li>Total: ${d.total} pedimentos</li></ul>`,
                'Promedio de días desde Llegada hasta Inicio de Proceso.', 'FECHA DE LLEGADA, FECHA EN PROCESO'];
        },
        'vol_recib': () => {
            const d = K.vol_recib;
            renderModalChart('vol_recib', d);
            return ['📦 Inbound Volume',
                `<div class="info-box">${d.piezas.toLocaleString()} piezas en ${d.cajas.toLocaleString()} cajas</div><ul class="info-list"><li>Calzado: ${d.calzado.toLocaleString()}</li><li>Ropa/Otros: ${d.otros.toLocaleString()}</li><li>Tarimas: ${d.tarimas.toLocaleString()}</li></ul>`,
                'Suma de piezas y cajas del manifiesto.', 'PIEZAS CALZADO, PIEZAS ROPA, TOTAL CAJAS'];
        },
        'tiempo_extra': () => {
            const d = K.tiempo_extra;
            renderModalChart('tiempo_extra', d);
            return ['⚠️ SLA Breach (Overtime)',
                `<div class="info-box" style="border-color:#ef4444">${d.excedidos} operaciones excedieron 72h (${d.pct_excedido.toFixed(1)}%)</div>`,
                'Conteo de operaciones marcadas como NO en SLA.', 'CUMPLIMIENTO 72 HORAS (Columna AK)'];
        },
        'efic_desc': () => {
            const d = K.efic_desc;
            renderModalChart('efic_desc', d);
            return ['🚛 Unloading Efficiency',
                `<div class="info-box">${d.eficiencia.toFixed(1)}% procesados en ≤2 días</div><ul class="info-list"><li>En Meta: ${d.en_meta}</li><li>Sobre Meta: ${d.sobre_meta}</li></ul>`,
                'Arribos procesados dentro del objetivo de 2 días.', 'FECHA LLEGADA, FECHA PROCESO'];
        },
        'pct_surtido': () => {
            const d = K.pct_surtido;
            renderModalChart('pct_surtido', d);
            return ['📊 Fill Rate',
                `<div class="info-box">${d.surtido.toLocaleString()} de ${d.total.toLocaleString()} piezas surtidas</div><ul class="info-list"><li>Pendiente: ${d.pendiente.toLocaleString()} piezas</li><li>Órdenes: ${d.ordenes_validas || 0}</li></ul>`,
                'Promedio de (Piezas Surtidas / Total Piezas) por orden.', 'TOTAL DE PIEZAS (G), PIEZAS SURTIDAS (J)'];
        },
        'avance_etapa': () => {
            const d = K.avance_etapa;
            renderModalChart('avance_etapa', d);
            return ['📈 Pipeline Velocity',
                `<ul class="info-list"><li>Surtido: ${d.surtido.toFixed(1)}%</li><li>Etiquetado: ${d.etiquetado.toFixed(1)}%</li><li>Distribución: ${d.distribucion.toFixed(1)}%</li><li>Auditoría: ${d.auditoria.toFixed(1)}%</li></ul><div class="info-box">Total: ${d.total_ordenes} órdenes activas</div>`,
                'Progreso promedio % en todas las órdenes activas.', '%, %.1, %.2, %.3 (Columnas K, M, O, Q)'];
        },
        'cumpl_entrega': () => {
            const d = K.cumpl_entrega;
            renderModalChart('cumpl_entrega', d);
            return ['🎯 OTIF (On Time In Full)',
                `<div class="info-box">${d.on_time} de ${d.total} a tiempo = ${d.pct.toFixed(1)}%</div><ul class="info-list"><li>A tiempo: ${d.on_time}</li><li>Tarde: ${d.late}</li></ul>`,
                'Fecha Entrega Real ≤ Fecha Promesa.', 'FECHA / HORA ENTREGADO (U), FECHA A ENTREGAR (R)'];
        },
        'audit_quality': () => {
            const d = K.audit_quality;
            renderModalChart('audit_quality', d);
            const br = Object.entries(d.breakdown || {}).map(([k, v]) => `<li>${k}: ${v} registro(s)</li>`).join('');
            return ['📊 Fulfillment Completion',
                `<div class="info-box">Tasa de Cumplimiento: ${d.pct.toFixed(1)}%</div>
                     <ul class="info-list"><li>100% Completados: ${d.passed}</li><li>Total Surtidos: ${d.total}</li></ul>
                     <div class="info-title">Incompletos (Detalle):</div>
                     <ul class="info-list">${br || '<li>Ninguno (100% perfecto)</li>'}</ul>`,
                'Promedio de % EN PROCESO COMPLETO de todos los surtidos.', '% EN PROCESO COMPLETO (Col V)'];
        },
        'backlog': () => {
            const d = K.backlog;
            renderModalChart('backlog', d);
            const st = Object.entries(d.all_status || {}).map(([k, v]) => `<li>${k}: ${v}</li>`).join('');
            return ['📋 Order Backlog',
                `<div class="info-box" style="border-color:${d.critical > 0 ? '#ef4444' : '#e5e7eb'}">${d.display_backlog} órdenes requieren atención.</div>
                     <div class="info-title">Global: ${d.total} Activas</div>
                     <ul class="info-list"><li>Críticas (Fuera de Tiempo): ${d.critical}</li><li>En Tiempo: ${d.on_track}</li><li>Otras: ${d.pendiente}</li></ul>
                     <div class="info-title">Desglose Detallado:</div><ul class="info-list">${st || '<li>Sin datos</li>'}</ul>`,
                'Órdenes no entregadas. "Backlog" usa lógica: Fecha Promesa Vencida = Demorado.', 'FECHA A ENTREGAR (R), STATUS CALCULADO'];
        },
        'vol_surtido': () => {
            const d = K.vol_surtido;
            renderModalChart('vol_surtido', d);

            const wk = (d.by_week || []).map(w => `<li>S${w.SEMANA}: ${w.Surtido.toLocaleString()} pzas (${w.Ordenes} ord)</li>`).join('');
            const avgTicket = d.ordenes > 0 ? Math.round(d.surtido / d.ordenes) : 0;

            // --- Generate Executive Summary Analysis ---
            let executiveSummary = "<div class='exec-summary'><i>Sin suficientes datos históricos para un análisis de tendencia.</i></div>";

            if (d.by_week && d.by_week.length >= 2) {
                const cur = d.by_week[d.by_week.length - 1];
                const prev = d.by_week[d.by_week.length - 2];

                const volChange = ((cur.Surtido - prev.Surtido) / prev.Surtido) * 100;
                const ordChange = ((cur.Ordenes - prev.Ordenes) / prev.Ordenes) * 100;
                const ticketChange = cur.Ordenes > 0 && prev.Ordenes > 0 ?
                    (((cur.Surtido / cur.Ordenes) - (prev.Surtido / prev.Ordenes)) / (prev.Surtido / prev.Ordenes)) * 100 : 0;

                const volIcon = volChange > 0 ? "📈" : (volChange < 0 ? "📉" : "➡️");
                const ordIcon = ordChange > 0 ? "▲" : "▼";

                let narrative = "";
                if (volChange > 5 && ordChange > 5) {
                    narrative = "Observamos una <strong>expansión general</strong> de la operación. Tanto el volumen de piezas como la cantidad de pedidos aumentaron, indicando una demanda saludable.";
                } else if (volChange < -5 && ordChange < -5) {
                    narrative = "Se registra una <strong>desaceleración general</strong>. La baja en piezas y pedidos sugiere un periodo de menor actividad logística.";
                } else if (volChange > 5 && ordChange < -5) {
                    narrative = "A pesar de procesar <strong>menos órdenes</strong>, el volumen físico creció. Esto indica una <strong>consolidación de pedidos</strong> (Ticket Promedio más alto), optimizando el picking.";
                } else if (volChange < -5 && ordChange > 5) {
                    narrative = "La operación muestra <strong>fragmentación</strong> (E-commerce/Retail pequeño). Atendimos más órdenes pero movimos menos piezas, lo que implica mayor esfuerzo operativo por unidad.";
                } else {
                    narrative = "La operación se mantiene estable con variaciones transaccionales menores.";
                }

                executiveSummary = `
                    <div class="exec-summary">
                        <div class="exec-header">📝 ANÁLISIS EJECUTIVO (S${cur.SEMANA} vs S${prev.SEMANA})</div>
                        <div class="exec-body">
                            ${narrative}
                            ${Math.abs(ticketChange) > 10 ? `<br><br>💡 Nota: La densidad de surtido varió un <strong>${ticketChange > 0 ? '+' : ''}${ticketChange.toFixed(1)}%</strong>.` : ''}
                        </div>
                        <div class="exec-footer">
                            <span>Piezas: <b class="${volChange >= 0 ? 'text-green' : 'text-red'}">${volIcon} ${Math.abs(volChange).toFixed(1)}%</b></span>
                            <span>Ordenes: <b class="${ordChange >= 0 ? 'text-green' : 'text-red'}">${ordIcon} ${Math.abs(ordChange).toFixed(1)}%</b></span>
                        </div>
                    </div>
                `;
            }

            return ['📦 Outbound Throughput',
                `${executiveSummary}
                 <div class="info-box">${d.surtido.toLocaleString()} piezas en ${d.ordenes} órdenes</div>
                 <div class="info-box" style="margin-top:0.5rem; background:#f3f4f6; color:#4b5563;">🎟️ Ticket Promedio Global: <strong>${avgTicket}</strong> pzas/orden</div>
                 <div class="info-title">Desglose Semanal:</div><ul class="info-list">${wk || '<li>Sin datos</li>'}</ul>`,
                'Análisis comparativo de volumen vs transaccionalidad por semana.', 'PIEZAS SURTIDAS, FECHA, CLIENTE'];
        },
        'notifications': () => {
            const d = K.alerts;
            renderModalChart(null, null);
            const rows = d.alerts.map(a => {
                const isGood = a.icon === '📈';
                const cls = isGood ? 'alert-good' : 'alert-bad';
                return `
                            <div class="alert-item ${cls}">
                                <span style="font-size:1.1rem;">${a.icon}</span>
                                <span style="flex:1;">${a.message}</span>
                            </div>
                        `;
            }).join('');
            return ['🔔 Centro de Notificaciones',
                `<div class="info-title">Semana Actual vs Semana Anterior:</div>
                     <div style="margin-top:0.5rem;">${rows || '<div class="info-box">No hay alertas activas en este periodo.</div>'}</div>`,
                'Comparativa WoW (Week-over-Week) y Monitoreo de SLA.', 'FECHA, SLA_THRESHOLD, KPI_WoW'];
        },
        'desemp_cliente': () => {
            const d = K.desemp_cliente;
            renderModalChart('desemp_cliente', d);
            const rows = d.map(r => `<li>${r.CLIENTE}: ${r.Piezas.toLocaleString()} pzas | OTD: ${r.OTD.toFixed(0)}%</li>`).join('');
            return ['👤 Client Performance', `<ul class="info-list">${rows || '<li>Sin datos</li>'}</ul>`,
                'Volumen y OTD agregado por Cliente.', 'CLIENTE, TOTAL PIEZAS, Lógica OTIF'];
        },
        'risk_prediction': () => {
            const d = K.risk_prediction;
            renderModalChart(null, null);
            // Build detail table of at-risk pedimentos
            let tableHtml = '';
            if (d.at_risk && d.at_risk.length > 0) {
                tableHtml = `<div style="margin-top:0.75rem;">
                            <div style="font-weight:700; font-size:0.85rem; margin-bottom:0.5rem;">📋 Pedimentos en Riesgo:</div>
                            <div style="max-height:220px; overflow-y:auto;">
                            <table style="width:100%; border-collapse:collapse; font-size:0.78rem;">
                                <thead>
                                    <tr style="background:#f1f5f9; text-align:left;">
                                        <th style="padding:6px 8px; border-bottom:2px solid #e2e8f0;">Pedimento</th>
                                        <th style="padding:6px 8px; border-bottom:2px solid #e2e8f0;">Tipo Mercancía</th>
                                        <th style="padding:6px 8px; border-bottom:2px solid #e2e8f0;">Llegada</th>
                                        <th style="padding:6px 8px; border-bottom:2px solid #e2e8f0;">Horas</th>
                                        <th style="padding:6px 8px; border-bottom:2px solid #e2e8f0;">Nivel</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${d.at_risk.map(r => {
                    const levelColor = r.risk_level === 'Critical' ? '#ef4444' : '#f59e0b';
                    const levelBg = r.risk_level === 'Critical' ? '#fef2f2' : '#fffbeb';
                    const levelText = r.risk_level === 'Critical' ? '🔴 Crítico' : '⚠️ Alto';
                    return `<tr style="border-bottom:1px solid #f1f5f9;">
                                            <td style="padding:6px 8px; font-weight:600;">${r.PEDIMENTO || '-'}</td>
                                            <td style="padding:6px 8px;">${r['TIPO DE MERCANCIA'] || '-'}</td>
                                            <td style="padding:6px 8px; color:#64748b;">${r.fecha_llegada_str || '-'}</td>
                                            <td style="padding:6px 8px; font-weight:600;">${r.hours_elapsed}h</td>
                                            <td style="padding:4px 8px;"><span style="background:${levelBg}; color:${levelColor}; padding:2px 8px; border-radius:12px; font-size:0.7rem; font-weight:700;">${levelText}</span></td>
                                        </tr>`;
                }).join('')}
                                </tbody>
                            </table>
                            </div>
                        </div>`;
            } else {
                tableHtml = `<div style="background:#f0fdf4; padding:0.75rem; border-radius:8px; text-align:center; color:#166534; font-weight:600; margin-top:0.5rem;">✅ No hay pedimentos en riesgo alto actualmente.</div>`;
            }
            return ['📥 SLA Inbound Risk (Riesgo de Entrada)',
                `<div style="background:#eff6ff; border:1px solid #93c5fd; padding:0.75rem; border-radius:8px; margin-bottom:1rem; color:#1e40af; font-size:0.8rem;">
                        📋 <strong>¿Qué mide?</strong> Pedimentos en riesgo de exceder <strong>72 horas SLA</strong> desde su llegada hasta ser procesados.
                     </div>
                     <div class="info-box" style="border-color:#be185d;">${d.high_risk_count} pedimentos en riesgo alto</div>
                     <ul class="info-list">
                        <li>🔴 Críticos (>75% del SLA consumido): ${d.critical_count || 0}</li>
                        <li>⚠️ Alto Riesgo (>50% del SLA): ${d.high_risk_count || 0}</li>
                        <li>📊 Total Evaluados: ${d.risk_count || 0}</li>
                     </ul>
                     ${tableHtml}
                     <div style="background:#f0fdf4; border:1px solid #86efac; padding:0.6rem; border-radius:8px; margin-top:0.75rem; color:#166534; font-size:0.75rem;">
                        💡 El Panel de Operaciones mide riesgo de <strong>entrega</strong> (surtidos con <24h y <70% avance). Esta métrica mide riesgo de <strong>procesamiento de entrada</strong> (SLA 72h).
                     </div>`,
                'Heurística basada en horas transcurridas desde FECHA DE LLEGADA vs umbral 72h SLA. Score ≥75 = Alto Riesgo.', 'FECHA DE LLEGADA, FECHA ENVIO DE REPORTE, CAJAS'];
        },
        'wip_metrics': () => {
            const d = K.wip_metrics;
            renderModalChart('wip_metrics', d);
            return ['🚧 Active Work In Progress (WIP)',
                `<div class="info-box">${d.ordenes} órdenes activas en piso.</div>
                     <ul class="info-list">
                        <li>Avance Promedio: ${d.avance.toFixed(1)}%</li>
                        <li>Piezas por Surtir: ${d.piezas_pendientes.toLocaleString()}</li>
                        <li>Total en Proceso: ${d.total_wip_count} (Inc. Pendientes)</li>
                     </ul>`,
                'Métricas exclusivas para órdenes con estatus EN PROCESO o PENDIENTE.', 'PIEZAS SURTIDAS / TOTAL PIEZAS'];
        }
    };
    if (T[type]) {
        const [title, body, logic, cols] = T[type]();
        document.getElementById('modalTitle').textContent = title;
        document.getElementById('modalContent').innerHTML = body;

        // Update Tech Details
        document.getElementById('modalTech').innerHTML = `
                    <span class="tech-title">🔍 Lógica de Cálculo:</span> ${(logic || 'N/A')}<br><br>
                    <span class="tech-title">📊 Columnas Fuente:</span> 
                    ${(cols || '').split(',').map(c => `<span class="tech-tag">${c.trim()}</span>`).join('')}
                `;
        document.getElementById('modalTech').style.display = 'none'; // Reset to hidden

        document.getElementById('modalOverlay').classList.add('active');
        document.getElementById('modalBox').style.display = 'block';
    }
}

function showChartModal(type) {
    // Format: [Title, BodyHtml, Logic, Cols]
    // Ensure no chart conflicts
    const container = document.querySelector('.chart-container');
    if (container) container.style.display = 'none';

    const T = {
        'comp': () => ['📈 SLA Compliance 72h', K.comp_chart.map(d => `<li>${d.Estado}: ${d.Cantidad}</li>`).join(''), 'Agrupado por estatus de cumplimiento.', 'CUMPLIMIENTO 72 HORAS'],
        'vol': () => ['📦 Inbound Volume (Weekly)', K.trend_data.map(d => `<li>S${d.SEMANA}: ${d.Total_Piezas.toLocaleString()} piezas</li>`).join(''), 'Suma de piezas por Número de Semana.', 'PIEZAS [CALZADO+ROPA], SEMANA'],
        'trend': () => ['📉 Outbound Throughput', K.weekly_data.map(d => `<li>S${d.SEMANA}: ${d.Ordenes} ord / ${(d.Surtido || 0).toLocaleString()} pzas</li>`).join(''), 'Conteo de Órdenes y Piezas por Semana.', 'PEDIMENTO, PIEZAS SURTIDAS, SEMANA'],
        'otd': () => ['🎯 OTIF Performance', K.weekly_data.map(d => `<li>S${d.SEMANA}: ${(d.OTD * 100).toFixed(1)}%</li>`).join(''), 'Promedio de Cumplimiento por Semana.', 'FECHA [ENTREGADO vs A ENTREGAR]'],
        'tipo': () => ['📦 SKU Mix Distribution', K.vol_data.map(d => `<li>${d['TIPO DE MERCANCIA']}: ${d.Total_Piezas.toLocaleString()}</li>`).join(''), 'Suma de piezas por Tipo. Ceros filtrados.', 'TIPO DE MERCANCIA'],
        'status': () => ['🏷️ Order Status Mix', K.status_data.map(d => `<li>${d.Status}: ${d.Cantidad}</li>`).join(''), 'Conteo agrupado por Estatus. Vacíos filtrados.', 'STATUS DE SURTIDO'],
        'clientes': () => ['👤 Top Clients Volume', K.client_data.map(d => `<li>${d.CLIENTE}: ${d.Total_Piezas.toLocaleString()}</li>`).join(''), 'Total de Piezas por Cliente (Top 5).', 'CLIENTE, TOTAL DE PIEZAS'],
        'pipeline': () => ['📊 Fulfillment Pipeline', K.pipeline_data.map(d => `<li>${d.Etapa}: ${d.Piezas.toLocaleString()} (${d.Porcentaje})</li>`).join(''), 'Suma de piezas por Etapa del Embudo.', '%, %.1, %.2, %.3']
    };
    if (T[type]) {
        const [title, items, logic, cols] = T[type]();
        document.getElementById('modalTitle').textContent = title;
        document.getElementById('modalContent').innerHTML = `<ul class="info-list">${items || '<li>Sin datos</li>'}</ul>`;

        // Update Tech Details
        document.getElementById('modalTech').innerHTML = `
                    <span class="tech-title">🔍 Lógica Visual:</span> ${(logic || 'Visualización Agregada')}<br><br>
                    <span class="tech-title">📊 Dimensiones:</span> 
                    ${(cols || '').split(',').map(c => `<span class="tech-tag">${c.trim()}</span>`).join('')}
                `;
        document.getElementById('modalTech').style.display = 'none';

        document.getElementById('modalOverlay').classList.add('active');
        document.getElementById('modalBox').style.display = 'block';
    }
}

function closeModal() {
    document.getElementById('modalOverlay').classList.remove('active');
    document.getElementById('modalBox').style.display = 'none';
}

document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

initCharts();
