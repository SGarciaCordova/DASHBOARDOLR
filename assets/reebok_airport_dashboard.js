const K = /*DATA_PLACEHOLDER*/ {};

function renderLists() {
    // 1. Críticos (Demoras + Riesgo)
    const critContainer = document.getElementById('list-critical');
    if (critContainer) {
        // Merge Demoras and Riesgo
        const criticalItems = [...K.demoras.map(i => ({ ...i, type: 'critical' })), ...K.riesgo.map(i => ({ ...i, type: 'warning' }))];

        // Sort by hours left (ascending - most urgent first)
        criticalItems.sort((a, b) => a._hours_left - b._hours_left);

        if (criticalItems.length === 0) {
            critContainer.innerHTML = '<div style="padding:1rem; text-align:center; color:#64748b;">✅ Todo en orden. Sin pedidos críticos.</div>';
        } else {
            critContainer.innerHTML = criticalItems.map(item => `
                <div class="list-item ${item.type}">
                    <div>
                        <div class="item-main">${item.docto_id} <span style="font-weight:400; color:#64748b;">| ${item.cliente}</span></div>
                        <div class="item-sub">Deadline: ${item._deadline_nice}</div>
                    </div>
                    <div style="text-align:right;">
                        <span class="tag ${item.type === 'critical' ? 'red' : 'orange'}">
                            ${item._hours_left.toFixed(1)}h
                        </span>
                        <div class="item-sub" style="margin-top:2px;">${item.referencia}</div>
                    </div>
                </div>
            `).join('');
        }
    }

    // 2. Salidas Recientes
    const shipContainer = document.getElementById('list-shipped');
    if (shipContainer) {
        const shippedItems = K.shipped || [];
        if (shippedItems.length === 0) {
            shipContainer.innerHTML = '<div style="padding:1rem; text-align:center; color:#64748b;">Sin salidas recientes.</div>';
        } else {
            shipContainer.innerHTML = shippedItems.map(item => `
                <div class="list-item ok">
                    <div>
                        <div class="item-main">${item.docto_id}</div>
                        <div class="item-sub">${item.fecha} ${item.hora || ''}</div>
                    </div>
                    <div style="text-align:right;">
                        <span class="tag blue">ENVIADO</span>
                        <div class="item-sub">${item.referencia}</div>
                    </div>
                </div>
            `).join('');
        }
    }

    // 3. Pendientes (Ingresados) - New Section
    const pendingContainer = document.getElementById('list-pending');
    if (pendingContainer) {
        const pendingItems = K.pending || []; // We need to pass this from Python
        if (pendingItems.length === 0) {
            pendingContainer.innerHTML = '<div style="padding:1rem; text-align:center; color:#64748b;">No hay pedidos pendientes.</div>';
        } else {
            pendingContainer.innerHTML = pendingItems.map(item => `
                <div class="list-item">
                    <div>
                        <div class="item-main">${item.docto_id} <span class="tag" style="background:#f1f5f9; color:#64748b;">${item.estado}</span></div>
                        <div class="item-sub">${item.cliente}</div>
                    </div>
                     <div style="text-align:right;">
                        <div class="item-main">${item.fecha}</div>
                        <div class="item-sub">${item.referencia}</div>
                    </div>
                </div>
             `).join('');
        }
    }
}

// Modal Logic
function showModal(type) {
    const box = document.getElementById('modalBox');
    const title = document.getElementById('modalTitle');
    const content = document.getElementById('modalContent');
    const overlay = document.getElementById('modalOverlay');

    let html = '';
    let titleText = '';

    if (type === 'demoras') {
        titleText = '🚨 Pedidos Demorados (<0h)';
        html = buildTable(K.demoras);
    } else if (type === 'riesgo') {
        titleText = '⚠️ Pedidos en Riesgo (0-4h)';
        html = buildTable(K.riesgo);
    } else if (type === 'atiempo') {
        titleText = '✅ Pedidos A Tiempo (>4h)';
        html = buildTable(K.a_tiempo);
    } else if (type === 'shipped') {
        titleText = '🛫 Últimas Salidas';
        html = buildTable(K.shipped, true);
    } else if (type === 'pending') {
        titleText = '📋 Pedidos Pendientes (Ingresados)';
        html = buildTable(K.pending); // Reuse table logic
    }

    title.textContent = titleText;
    content.innerHTML = html;

    overlay.classList.add('active');
    box.style.display = 'block';
}

function buildTable(items, isShipped = false) {
    if (!items || items.length === 0) return '<p style="text-align:center; padding:1rem;">Sin datos.</p>';

    return `
    <table style="width:100%; border-collapse:collapse; font-size:0.85rem;">
        <thead>
            <tr style="background:#f8fafc; text-align:left; border-bottom:2px solid #e2e8f0;">
                <th style="padding:0.75rem;">Doc ID</th>
                <th style="padding:0.75rem;">Cliente</th>
                <th style="padding:0.75rem;">Referencia</th>
                <th style="padding:0.75rem;">${isShipped ? 'Fecha Salida' : 'Deadline'}</th>
                <th style="padding:0.75rem;">${isShipped ? 'Estado' : 'Horas Restantes'}</th>
                <th style="padding:0.75rem;">% Completion</th>
            </tr>
        </thead>
        <tbody>
            ${items.map(i => `
                <tr style="border-bottom:1px solid #f1f5f9;">
                    <td style="padding:0.75rem; font-weight:600;">${i.docto_id}</td>
                    <td style="padding:0.75rem;">${i.cliente}</td>
                    <td style="padding:0.75rem;">${i.referencia}</td>
                    <td style="padding:0.75rem;">${isShipped ? (i.fecha + ' ' + (i.hora || '')) : i._deadline_nice}</td>
                    <td style="padding:0.75rem;">
                        ${isShipped
            ? '<span class="tag green">ENVIADO</span>'
            : `<span style="font-weight:700; color:${i._hours_left < 0 ? '#ef4444' : (i._hours_left <= 4 ? '#f59e0b' : '#10b981')}">${i._hours_left.toFixed(1)}h</span>`
        }
                    </td>
                     <td style="padding:0.75rem;">${i.pct_completitud ? i.pct_completitud.toFixed(1) + '%' : '-'}</td>
                </tr>
            `).join('')}
        </tbody>
    </table>
    `;
}

function closeModal() {
    document.getElementById('modalOverlay').classList.remove('active');
    document.getElementById('modalBox').style.display = 'none';
}

document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

// Initialize
renderLists();
