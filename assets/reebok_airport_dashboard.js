const K = /*DATA_PLACEHOLDER*/ {};

// Debug Check
if (!K || Object.keys(K).length === 0) {
    console.warn("REEBOK_DEBUG: K is empty or undefined");
    window.addEventListener('load', () => {
        const grid = document.getElementById('orderGrid');
        if (grid) grid.innerHTML = '<div style="color:red; padding:20px;">[DEBUG] Los datos de la operacion (K) estan vacios. Revise la inyeccion en Python.</div>';
    });
}

function getStatusInfo(item) {
    if (item.estado === 'LISTAS PARA EMBARQUE') return { code: 'ready', text: 'LISTA EMBARQUE', color: '#10b981' };
    const h = item._hours_left;
    if (h === undefined || h === null || item.estado === 'INGRESADO') return { code: 'pending', text: 'INGRESADO', color: '#8b5cf6' };
    if (h < 0) return { code: 'delayed', text: 'DEMORADO', color: '#ef4444' };
    if (h <= 4) return { code: 'risk', text: 'RIESGO ENTREGA', color: '#f59e0b' };
    return { code: 'on_time', text: 'A TIEMPO', color: '#3b82f6' };
}

function getProgressColor(p) {
    if (p < 40) return '#ef4444';
    if (p < 80) return '#f59e0b';
    return '#10b981';
}

function formatTime(hours) {
    if (hours === undefined || hours === null || isNaN(hours)) return '-';
    try {
        if (hours < 0) return Math.abs(hours).toFixed(0) + 'h retraso';
        if (hours > 24) return Math.floor(hours / 24) + 'd ' + Math.floor(hours % 24) + 'h';
        return hours.toFixed(0) + 'h restantes';
    } catch(e) {
        return '-';
    }
}

function renderAll(category = 'active') {
    // Determine which items to show
    let sourceItems = [];
    if (category === 'active') {
        sourceItems = [
            ...(K.demoras || []),
            ...(K.riesgo || []),
            ...(K.a_tiempo || []),
            ...(K.pending || [])
        ];
    } else if (category === 'demoras') {
        sourceItems = K.demoras || [];
    } else if (category === 'riesgo') {
        sourceItems = K.riesgo || [];
    } else if (category === 'atiempo') {
        sourceItems = K.a_tiempo || [];
    } else if (category === 'pending') {
        sourceItems = K.pending || [];
    } else if (category === 'ready') {
        sourceItems = K.ready || [];
    }

    const allOrders = sourceItems.map(o => {
        try {
            return { ...o, _status: getStatusInfo(o) };
        } catch(e) {
            console.error("Error processing order:", o, e);
            return null;
        }
    }).filter(o => o !== null);

    window._allOrders = allOrders;

    // Render order cards
    const grid = document.getElementById('orderGrid');
    if (grid) {
        if (allOrders.length === 0) {
            grid.innerHTML = `<div style="text-align:center; color:#64748b; padding:2rem; grid-column:1/-1;">No hay pedidos en la categoría: ${category}.</div>`;
        } else {
            grid.innerHTML = allOrders.map((o, i) => {
                const pct = o.pct_completitud || 0;
                const status = o._status;
                const deadline = o._deadline_nice || o.fecha || '-';
                const timeStr = formatTime(o._hours_left);
                const qtyReq = parseInt(o.cantidad_pedida || 0);
                const qtyPick = parseInt(o.cantidad_surtida || 0);
                                return `
                <div class="order-card ${status.code}" onclick="showModal(${i}, 'order')">
                    <div class="order-header">
                        <div>
                            <div class="order-cliente">${o.cliente || o.docto_id || 'Sin Cliente'}</div>
                            <div class="order-tipo">📄 Doc: ${o.docto_id || '-'}</div>
                        </div>
                        <span class="order-badge" style="background:${status.color}">${status.text}</span>
                    </div>
                    <div class="order-grid-details">
                        <div>
                            <div class="order-label">Fecha de Entrega</div>
                            <div class="order-val">${deadline.split(' ')[0] || '-'}</div>
                            ${deadline !== '-' ? `<div style="font-size:0.75rem; color:#64748b; margin-top:2px; font-weight:500;">⏰ ${deadline.split(' ')[1] || ''}</div>` : ''}
                        </div>
                        <div style="text-align:right">
                            <div class="order-label">Tiempo</div>
                            <div class="order-val" style="color:${status.code === 'delayed' ? '#ef4444' : 'inherit'}">${timeStr}</div>
                        </div>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width:${pct.toFixed(0)}%; background:${status.color}"></div>
                    </div>
                    <div class="progress-txt">
                        <span>${qtyPick.toLocaleString()} / ${qtyReq.toLocaleString()}</span>
                        <strong>${pct.toFixed(0)}%</strong>
                    </div>
                </div>
                `;
            }).join('');
        }
    }

    // Render Completed / Shipped (only on initial load or if we want it to persist)
    // We only update the list if it's the first render or we want it constant
    const compList = document.getElementById('completedList');
    if (compList) {
        const shipped = K.shipped || [];
        if (shipped.length === 0) {
            compList.innerHTML = '<div style="color:#64748b; text-align:center; margin-top:2rem;">Sin salidas recientes</div>';
        } else {
            compList.innerHTML = shipped.map((s, idx) => {
                const client = s.cliente || s.docto_id || 'N/A';
                const ref = s.referencia || '#N/A';
                const doctoId = s.docto_id || '-';
                const fecha = s.fecha || '';
                const pzas = s.completion_text || '';
                const pct = s.pct_completitud || 0;
                
                let dateDisp = '-', timeDisp = '-';
                if (fecha.includes(' ')) {
                    const [f, h] = fecha.split(' ');
                    timeDisp = h;
                    const d = f.split('-');
                    if (d.length === 3) dateDisp = `${d[2]}/${d[1]}/${d[0]}`;
                } else {
                    const d = fecha.split('-');
                    if (d.length === 3) dateDisp = `${d[2]}/${d[1]}/${d[0]}`;
                }
                
                return `
                <div class="comp-card" onclick="showModal(${idx}, 'shipped')" style="cursor:pointer;">
                    <div class="comp-client">${client}</div>
                    <div class="comp-meta-row">ID: ${doctoId} • Ref: ${ref}</div>
                    
                    <div class="progress-bar" style="height:4px; margin: 0.4rem 0 0.3rem 0;">
                        <div class="progress-fill" style="width:${pct.toFixed(0)}%; background:var(--green)"></div>
                    </div>
                    
                    <div class="comp-pzas">
                        <span>📦</span> ${pzas}
                        <strong style="color:var(--green)">${pct.toFixed(0)}%</strong>
                    </div>
 
                    <div class="comp-footer">
                        <div class="comp-time-big">
                            <span class="val-time">${timeDisp}</span>
                            <span class="val-date">${dateDisp}</span>
                        </div>
                    </div>
                </div>
                `;
            }).join('');
        }
    }
}

// Modal Logic
function showModal(idx, type) {
    const overlay = document.getElementById('modalOverlay');
    const box = document.getElementById('modalBox');
    const title = document.getElementById('modalTitle');
    const content = document.getElementById('modalContent');

    let o = null;
    if (type === 'order' && window._allOrders && window._allOrders[idx]) {
        o = window._allOrders[idx];
    } else if (type === 'shipped' && K.shipped && K.shipped[idx]) {
        o = K.shipped[idx];
    }

    if (o) {
        title.textContent = o.cliente || o.docto_id || 'Detalle de Orden';
        
        // Status fallback if not in object (for shipped)
        const statusText = o._status ? o._status.text : 'COMPLETADO';
        const statusColor = o._status ? o._status.color : '#10b981';
        const deadlineLabel = o._deadline_nice ? 'Fecha Entrega' : 'Fecha Operación';
        const deadlineVal = o._deadline_nice || o.fecha || '-';

        content.innerHTML = `
            <div class="modal-row"><span class="modal-label">Documento</span><span class="modal-value">${o.docto_id || '-'}</span></div>
            <div class="modal-row"><span class="modal-label">Referencia</span><span class="modal-value">${o.referencia || '-'}</span></div>
            <div class="modal-row"><span class="modal-label">Cliente</span><span class="modal-value">${o.cliente || '-'}</span></div>
            <div class="modal-row"><span class="modal-label">Estado</span><span class="modal-value" style="color:${statusColor}">${statusText}</span></div>
            <div class="modal-row"><span class="modal-label">Fecha de Ingreso</span><span class="modal-value">${o.fecha} ${o.hora || ''}</span></div>
            <div class="modal-row"><span class="modal-label">${deadlineLabel}</span><span class="modal-value">${deadlineVal}</span></div>
            <div class="modal-row"><span class="modal-label">Ubicación</span><span class="modal-value">${o.ubicacion || '-'}</span></div>
            <div class="modal-row"><span class="modal-label">Partidas</span><span class="modal-value">${o.partidas || '-'}</span></div>
            <div class="modal-row"><span class="modal-label">Avance</span><span class="modal-value">${(o.pct_completitud || 0).toFixed(1)}%</span></div>
            <div class="modal-row"><span class="modal-label">Cant. Pedida</span><span class="modal-value">${parseInt(o.cantidad_pedida || 0).toLocaleString()}</span></div>
            <div class="modal-row"><span class="modal-label">Cant. Surtida</span><span class="modal-value">${parseInt(o.cantidad_surtida || 0).toLocaleString()}</span></div>
        `;
    }

    // Disable scroll
    document.body.style.overflow = "hidden";
    document.documentElement.style.overflow = "hidden";

    overlay.classList.add('active');
    if (box) box.style.display = 'block';
}

function filterGrid(category) {
    // Just re-render with the category
    renderAll(category);
    
    // Add visual feedback to the clicked stat card
    const cards = document.querySelectorAll('.stat-card');
    cards.forEach(c => c.classList.remove('active-filter'));
    
    // Find the clicked card using the onclick attribute as a hint
    // (A bit hacky since we don't have IDs, but reliable for this structure)
    cards.forEach(c => {
        if (c.getAttribute('onclick').includes(`'${category}'`)) {
            c.classList.add('active-filter');
        }
    });
}

// Keeping showCategoryModal for backward compatibility if needed, but pointing to filterGrid
function showCategoryModal(type) {
    filterGrid(type);
}

function closeModal() {
    // Restore scroll
    document.body.style.overflow = "auto";
    document.documentElement.style.overflow = "auto";

    document.getElementById('modalOverlay').classList.remove('active');
    const box = document.getElementById('modalBox');
    if (box) box.style.display = 'none';
}

document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => renderAll());
} else {
    renderAll();
}
