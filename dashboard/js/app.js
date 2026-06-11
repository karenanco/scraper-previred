const MONTHS_ORDER = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
];

const COLORS = ['#1a73e8', '#e65100', '#2e7d32', '#6a1b9a', '#00838f', '#c62828', '#f9a825', '#4e342e'];

const CURRENCY_FIELDS = new Set([
  'renta_tope_afp', 'renta_tope_ips', 'renta_tope_cesantia',
  'apv_tope_mensual', 'apv_tope_anual', 'deposito_convenido_tope',
  'utm_valor', 'uta_valor', 'renta_minima_dependientes',
  'renta_minima_menores', 'renta_minima_casa_particular',
  'renta_minima_no_remuneracional'
]);

const LABELS = {
  uf_valor: 'UF', renta_tope_afp: 'Tope AFP', renta_tope_ips: 'Tope IPS',
  renta_tope_cesantia: 'Tope Cesantía',
  renta_minima_dependientes: 'Mín. Dependientes', renta_minima_menores: 'Mín. <18/>65',
  renta_minima_casa_particular: 'Mín. Casa Particular', renta_minima_no_remuneracional: 'Mín. No Remun.',
  apv_tope_mensual: 'APV Mensual', apv_tope_anual: 'APV Anual', deposito_convenido_tope: 'Dep. Convenido',
};

const PLOT_GROUPS = {
  'Valores UF y Topes': ['uf_valor', 'renta_tope_afp', 'renta_tope_ips', 'renta_tope_cesantia'],
  'Rentas Mínimas': ['renta_minima_dependientes', 'renta_minima_menores', 'renta_minima_casa_particular', 'renta_minima_no_remuneracional'],
  'APV y Depósito Convenido': ['apv_tope_mensual', 'apv_tope_anual', 'deposito_convenido_tope'],
};

const TRAMO_INFO = {
  '1 (A)': { color: '#1a73e8', desc: 'Ingresos más bajos' },
  '2 (B)': { color: '#2e7d32', desc: 'Ingresos medios-bajos' },
  '3 (C)': { color: '#e65100', desc: 'Ingresos medios' },
  '4 (D)': { color: '#6c757d', desc: 'Sin asignación' },
};

const PREVIRED_DISPLAY_COLS = [
  'mes', 'periodo_remuneracion', 'uf_valor', 'uf_fecha',
  'renta_tope_afp', 'renta_tope_ips', 'renta_tope_cesantia',
  'apv_tope_mensual', 'apv_tope_anual', 'deposito_convenido_tope',
  'utm_valor', 'uta_valor',
  'renta_minima_dependientes', 'renta_minima_menores',
  'renta_minima_casa_particular', 'renta_minima_no_remuneracional',
  'seguro_social_tasa', 'sis_tasa', 'salud_ccaf', 'salud_fonasa',
];

const PREVIRED_RENAME = {
  mes: 'Mes', periodo_remuneracion: 'Periodo',
  uf_valor: 'Valor UF', uf_fecha: 'Fecha UF',
  renta_tope_afp: 'Tope AFP', renta_tope_ips: 'Tope IPS',
  renta_tope_cesantia: 'Tope Cesantía',
  apv_tope_mensual: 'APV Mensual', apv_tope_anual: 'APV Anual',
  deposito_convenido_tope: 'Dep. Convenido',
  utm_valor: 'UTM', uta_valor: 'UTA',
  renta_minima_dependientes: 'R.Mín. Dependientes',
  renta_minima_menores: 'R.Mín. <18/>65',
  renta_minima_casa_particular: 'R.Mín. Casa Particular',
  renta_minima_no_remuneracional: 'R.Mín. No Remunerac.',
  seguro_social_tasa: 'Seg. Social', sis_tasa: 'SIS',
  salud_ccaf: 'CCAF', salud_fonasa: 'FONASA',
};

const UTM_RENAME = {
  mes: 'Mes', utm: 'UTM', uta: 'UTA',
  variacion_mensual: 'Var. Mensual', variacion_acumulada: 'Var. Acumulada',
  variacion_anual: 'Var. Anual',
};

let data = null;
let filteredPrevired = [];
let filteredUtm = [];
let charts = [];

function destroyCharts() {
  charts.forEach(c => c.destroy());
  charts = [];
}

function formatCurrency(val) {
  if (val == null || val === '' || (typeof val === 'number' && isNaN(val))) return '—';
  const n = typeof val === 'string' ? parseFloat(val.replace(/[$.]/g, '').replace(',', '.')) : val;
  if (isNaN(n)) return val;
  return '$' + Math.round(n).toLocaleString('es-CL');
}

function formatUF(val) {
  if (val == null || val === '' || (typeof val === 'number' && isNaN(val))) return '—';
  const n = typeof val === 'string' ? parseFloat(val.replace(/[$.]/g, '').replace(',', '.')) : val;
  if (isNaN(n)) return String(val);
  return '$' + n.toLocaleString('es-CL', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatPct(val) {
  if (val == null || val === '' || (typeof val === 'number' && isNaN(val))) return '—';
  return String(val).replace('R.I.', '').trim();
}

function sortMonths(rows) {
  return [...rows].sort((a, b) => {
    const ma = (a.mes || '').split(' ')[0];
    const mb = (b.mes || '').split(' ')[0];
    return MONTHS_ORDER.indexOf(ma) - MONTHS_ORDER.indexOf(mb);
  });
}

function getLast(rows, field) {
  for (let i = rows.length - 1; i >= 0; i--) {
    if (rows[i][field] != null && rows[i][field] !== '' && !(typeof rows[i][field] === 'number' && isNaN(rows[i][field]))) {
      return rows[i][field];
    }
  }
  return null;
}

function getAvailableMonths(rows) {
  return rows.map(r => r.mes).filter(Boolean);
}

function applyFilter(selectedMonths) {
  if (!data) return;
  if (!selectedMonths || selectedMonths.length === 0) {
    filteredPrevired = [...data.previred.rows];
    filteredUtm = [...data.utm.rows];
  } else {
    filteredPrevired = data.previred.rows.filter(r => selectedMonths.includes(r.mes));
    filteredUtm = data.utm.rows.filter(r => selectedMonths.includes(r.mes));
  }
  filteredPrevired = sortMonths(filteredPrevired);
  filteredUtm = sortMonths(filteredUtm);
}

function renderSidebar() {
  const container = document.getElementById('sidebar-filters');
  const months = getAvailableMonths(data.previred.rows);

  let html = '<label>Filtrar por Mes</label><div class="filter-checkboxes" id="month-checkboxes">';
  html += months.map(m => `
    <label>
      <input type="checkbox" value="${m.replace(/"/g, '&quot;')}" checked data-month>
      ${m}
    </label>
  `).join('');
  html += '</div>';
  html += '<div class="filter-actions">';
  html += '<button id="select-all">Todo</button>';
  html += '<button id="deselect-all">Ninguno</button>';
  html += '</div>';
  container.innerHTML = html;

  container.addEventListener('change', (e) => {
    if (e.target.dataset.month !== undefined) {
      updateFilterAndRender();
    }
  });

  document.getElementById('select-all').addEventListener('click', () => {
    document.querySelectorAll('[data-month]').forEach(cb => cb.checked = true);
    updateFilterAndRender();
  });
  document.getElementById('deselect-all').addEventListener('click', () => {
    document.querySelectorAll('[data-month]').forEach(cb => cb.checked = false);
    updateFilterAndRender();
  });

  const statsEl = document.getElementById('sidebar-stats');
  statsEl.innerHTML = `
    <p><strong>${data.previred.rows.length}</strong> meses con datos</p>
    <p>Fuente: Previred + SII</p>
    <p>Actualizado: ${data.last_updated || '—'}</p>
  `;
}

function updateFilterAndRender() {
  const checked = Array.from(document.querySelectorAll('[data-month]:checked')).map(cb => cb.value);
  applyFilter(checked);
  renderActiveTab();
}

function renderActiveTab() {
  const active = document.querySelector('.tab-btn.active');
  if (active) renderTab(active.dataset.tab);
}

function renderTab(tabId) {
  destroyCharts();

  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));

  const tabContent = document.getElementById('tab-' + tabId);
  const tabBtn = document.querySelector(`[data-tab="${tabId}"]`);
  if (tabContent) tabContent.classList.add('active');
  if (tabBtn) tabBtn.classList.add('active');

  switch (tabId) {
    case 'resumen': renderResumen(); break;
    case 'evolucion': renderEvolucion(); break;
    case 'afp': renderAFP(); break;
    case 'asignacion': renderAsignacion(); break;
    case 'datos': renderDatos(); break;
  }
}

function renderResumen() {
  const container = document.getElementById('tab-resumen');
  const prev = filteredPrevired;
  const utm = filteredUtm;
  if (!prev.length) { container.innerHTML = noDataHTML(); return; }

  const last = prev[prev.length - 1];
  const lastMes = last.mes || '';

  let html = '<div class="section-title">Resumen Ejecutivo</div>';

  html += '<div class="kpi-grid">';
  html += kpiCard('UF', formatUF(last.uf_valor), last.uf_fecha || '');
  html += kpiCard('UTM', formatCurrency(getLast(utm, 'utm')), utm.length ? utm[utm.length - 1].mes : '');
  html += kpiCard('UTA', formatCurrency(getLast(utm, 'uta')), utm.length ? utm[utm.length - 1].mes : '');
  html += kpiCard('Tope AFP (90 UF)', formatCurrency(last.renta_tope_afp), lastMes, '#1a73e8');
  html += kpiCard('Tope IPS (60 UF)', formatCurrency(last.renta_tope_ips), lastMes, '#2e7d32');
  html += kpiCard('Tope Seg. Cesantía', formatCurrency(last.renta_tope_cesantia), lastMes, '#e65100');
  html += '</div>';

  html += '<div class="data-grid">';

  html += '<div class="table-wrap"><table>';
  html += '<thead><tr><th>Indicador</th><th>' + lastMes + '</th></tr></thead><tbody>';
  const indicators = [
    ['UF', formatUF(last.uf_valor)],
    ['UTM', formatCurrency(last.utm_valor)],
    ['UTA', formatCurrency(last.uta_valor)],
    ['Tope AFP (90 UF)', formatCurrency(last.renta_tope_afp)],
    ['Tope IPS (60 UF)', formatCurrency(last.renta_tope_ips)],
    ['Tope Seg. Cesantía', formatCurrency(last.renta_tope_cesantia)],
    ['APV Tope Mensual', formatCurrency(last.apv_tope_mensual)],
    ['APV Tope Anual', formatCurrency(last.apv_tope_anual)],
    ['Seguro Social', formatPct(last.seguro_social_tasa)],
    ['SIS', formatPct(last.sis_tasa)],
    ['Salud CCAF', formatPct(last.salud_ccaf)],
    ['Salud FONASA', formatPct(last.salud_fonasa)],
  ];
  indicators.forEach(([label, val]) => {
    html += `<tr><td><strong>${label}</strong></td><td>${val}</td></tr>`;
  });
  html += '</tbody></table></div>';

  html += '<div class="table-wrap"><table>';
  html += '<thead><tr><th>Categoría</th><th>' + lastMes + '</th></tr></thead><tbody>';
  const rents = [
    ['Dependientes', formatCurrency(last.renta_minima_dependientes)],
    ['Menores 18 / Mayores 65', formatCurrency(last.renta_minima_menores)],
    ['Casa Particular', formatCurrency(last.renta_minima_casa_particular)],
    ['No Remuneracional', formatCurrency(last.renta_minima_no_remuneracional)],
  ];
  rents.forEach(([label, val]) => {
    html += `<tr><td><strong>${label}</strong></td><td>${val}</td></tr>`;
  });
  html += '</tbody></table></div>';

  html += '</div>';
  container.innerHTML = html;
}

function renderEvolucion() {
  const container = document.getElementById('tab-evolucion');
  const prev = filteredPrevired;
  if (!prev.length) { container.innerHTML = noDataHTML(); return; }

  let html = '<div class="section-title">Evolución Mensual de Indicadores</div>';
  html += '<div id="evo-charts"></div>';

  if (filteredUtm.length) {
    html += '<div class="section-title" style="margin-top:1.5rem;">UTM - SII</div>';
    html += '<div class="chart-container"><canvas id="utm-chart"></canvas></div>';
  }

  container.innerHTML = html;

  Object.entries(PLOT_GROUPS).forEach(([title, cols], idx) => {
    const available = cols.filter(c => prev.some(r => r[c] != null && r[c] !== '' && !(typeof r[c] === 'number' && isNaN(r[c]))));
    if (available.length < 2) return;
    const chartId = 'evo-chart-' + idx;
    document.getElementById('evo-charts').innerHTML +=
      `<div class="chart-container"><div class="chart-title">${title}</div><canvas id="${chartId}"></canvas></div>`;
    createLineChart(chartId, prev, available);
  });

  if (filteredUtm.length) {
    createBarChart('utm-chart', filteredUtm, 'utm', '#1a73e8');
  }
}

function renderAFP() {
  const container = document.getElementById('tab-afp');
  const prev = filteredPrevired;
  const monthsWithAFP = prev.filter(r => r.afp_tasas && typeof r.afp_tasas === 'object');
  if (!monthsWithAFP.length) {
    container.innerHTML = '<div class="empty-state">No hay datos de tasas AFP disponibles.</div>';
    return;
  }

  let html = '<div class="section-title">Tasas de Cotización AFP</div>';
  html += '<div class="select-wrap">';
  html += `<label><strong>Seleccionar Mes:</strong> <select id="afp-month-select">`;
  monthsWithAFP.forEach(r => {
    html += `<option value="${r.mes}">${r.mes}</option>`;
  });
  html += '</select></label></div>';

  html += '<div id="afp-content"></div>';
  container.innerHTML = html;

  document.getElementById('afp-month-select').addEventListener('change', () => renderAFPData());
  renderAFPData();
}

function renderAFPData() {
  const sel = document.getElementById('afp-month-select');
  if (!sel) return;
  const mes = sel.value;
  const row = filteredPrevired.find(r => r.mes === mes);
  if (!row || !row.afp_tasas) return;

  const afpData = row.afp_tasas;
  const content = document.getElementById('afp-content');
  let html = '<div class="data-grid">';

  html += '<div class="table-wrap"><table>';
  html += '<thead><tr><th>AFP</th><th>Trabajador</th><th>Empleador</th><th>Total</th><th>Independiente</th></tr></thead><tbody>';
  const afpRows = Object.entries(afpData);
  afpRows.forEach(([afp, tasas]) => {
    if (typeof tasas === 'object') {
      html += `<tr><td><strong>${afp}</strong></td><td>${tasas.trabajador || ''}</td><td>${tasas.empleador || ''}</td><td>${tasas.total || ''}</td><td>${tasas.independiente || ''}</td></tr>`;
    }
  });
  html += '</tbody></table></div>';

  html += `<div class="chart-container"><canvas id="afp-chart"></canvas></div>`;
  html += '</div>';

  html += '<div class="kpi-row">';
  html += kpiCard('Seguro Social', formatPct(row.seguro_social_tasa), mes, '#00838f');
  html += kpiCard('SIS', formatPct(row.sis_tasa), mes, '#6a1b9a');
  html += kpiCard('Salud CCAF / FONASA', `${formatPct(row.salud_ccaf)} / ${formatPct(row.salud_fonasa)}`, mes, '#2e7d32');
  html += '</div>';

  content.innerHTML = html;

  createAFPGroupBar('afp-chart', afpRows);
}

function renderAsignacion() {
  const container = document.getElementById('tab-asignacion');
  const prev = filteredPrevired;
  const monthsWithAF = prev.filter(r => r.asignacion_familiar && typeof r.asignacion_familiar === 'object');
  if (!monthsWithAF.length) {
    container.innerHTML = '<div class="empty-state">No hay datos de asignación familiar disponibles.</div>';
    return;
  }

  let html = '<div class="section-title">Asignación Familiar - Tramos</div>';
  html += '<div class="select-wrap">';
  html += `<label><strong>Seleccionar Mes:</strong> <select id="af-month-select">`;
  monthsWithAF.forEach(r => {
    html += `<option value="${r.mes}">${r.mes}</option>`;
  });
  html += '</select></label></div>';

  html += '<div id="af-content"></div>';
  container.innerHTML = html;

  document.getElementById('af-month-select').addEventListener('change', () => renderAsignacionData());
  renderAsignacionData();
}

function renderAsignacionData() {
  const sel = document.getElementById('af-month-select');
  if (!sel) return;
  const mes = sel.value;
  const row = filteredPrevired.find(r => r.mes === mes);
  if (!row || !row.asignacion_familiar) return;

  const afData = row.asignacion_familiar;
  const content = document.getElementById('af-content');

  let html = `<div style="font-size:0.9rem;color:var(--gray-500);margin-bottom:0.8rem;">${mes}</div>`;

  html += '<div class="tramo-grid">';
  const sorted = Object.entries(afData).sort(([a], [b]) => a.localeCompare(b));
  sorted.forEach(([key, vals]) => {
    const info = TRAMO_INFO[key] || { color: '#212529', desc: '' };
    const monto = vals.monto || '';
    const req = vals.requisito || '';
    html += `<div class="tramo-card" style="border-top:3px solid ${info.color};">`;
    html += `<div class="tramo-title">${key}</div>`;
    html += `<div class="tramo-desc">${info.desc}</div>`;
    html += `<div class="tramo-monto">${monto}</div>`;
    html += `<div class="tramo-req">${req}</div>`;
    html += '</div>';
  });
  html += '</div>';

  html += '<div class="table-wrap"><table>';
  html += '<thead><tr><th>Tramo</th><th>Monto</th><th>Requisito de Renta</th></tr></thead><tbody>';
  sorted.forEach(([key, vals]) => {
    html += `<tr><td><strong>${key}</strong></td><td>${vals.monto || ''}</td><td>${vals.requisito || ''}</td></tr>`;
  });
  html += '</tbody></table></div>';

  content.innerHTML = html;
}

function renderDatos() {
  const container = document.getElementById('tab-datos');
  const prev = filteredPrevired;
  if (!prev.length) { container.innerHTML = noDataHTML(); return; }

  let html = '<div class="section-title">Tabla Completa - Indicadores Previred</div>';
  html += '<div class="table-wrap" style="margin-bottom:2rem;"><table>';
  html += '<thead><tr>';
  const displayCols = PREVIRED_DISPLAY_COLS.filter(c => c in prev[0]);
  displayCols.forEach(c => { html += `<th>${PREVIRED_RENAME[c] || c}</th>`; });
  html += '</tr></thead><tbody>';
  prev.forEach(row => {
    html += '<tr>';
    displayCols.forEach(c => {
      let val = row[c];
      if (val == null || val === '' || (typeof val === 'number' && isNaN(val))) {
        html += '<td>—</td>';
      } else if (c === 'uf_valor') {
        html += `<td>${formatUF(val)}</td>`;
      } else if (CURRENCY_FIELDS.has(c)) {
        html += `<td>${formatCurrency(val)}</td>`;
      } else {
        html += `<td>${val}</td>`;
      }
    });
    html += '</tr>';
  });
  html += '</tbody></table></div>';

  if (filteredUtm.length) {
    html += '<div class="section-title">UTM / UTA / IPC - SII</div>';
    html += '<div class="table-wrap"><table>';
    html += '<thead><tr>';
    const utmCols = ['mes', 'utm', 'uta', 'variacion_mensual', 'variacion_acumulada', 'variacion_anual'];
    utmCols.forEach(c => { html += `<th>${UTM_RENAME[c] || c}</th>`; });
    html += '</tr></thead><tbody>';
    filteredUtm.forEach(row => {
      html += '<tr>';
      utmCols.forEach(c => {
        let val = row[c];
        if (val == null || val === '' || (typeof val === 'number' && isNaN(val))) {
          html += '<td>—</td>';
        } else if (c === 'utm' || c === 'uta') {
          html += `<td>${formatCurrency(val)}</td>`;
        } else {
          html += `<td>${val}</td>`;
        }
      });
      html += '</tr>';
    });
    html += '</tbody></table></div>';
  }

  container.innerHTML = html;
}

function createLineChart(canvasId, rows, cols) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const labels = rows.map(r => r.mes);
  const datasets = cols.map((col, i) => ({
    label: LABELS[col] || col,
    data: rows.map(r => r[col]),
    borderColor: COLORS[i % COLORS.length],
    backgroundColor: COLORS[i % COLORS.length] + '20',
    fill: false,
    tension: 0.2,
    pointRadius: 4,
    pointHoverRadius: 6,
    borderWidth: 2.5,
  }));

  const chart = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { boxWidth: 12, padding: 12, font: { family: 'Inter, sans-serif', size: 11 } } },
        tooltip: {
          mode: 'index',
          intersect: false,
          callbacks: {
            label: ctx => {
              const val = ctx.raw;
              if (val == null || isNaN(val)) return '';
              return ctx.dataset.label + ': $' + Math.round(val).toLocaleString('es-CL');
            }
          }
        }
      },
      scales: {
        x: { grid: { color: '#f0f0f0' }, ticks: { font: { size: 11 } } },
        y: {
          grid: { color: '#f0f0f0' },
          ticks: {
            font: { size: 11 },
            callback: val => '$' + Math.round(val).toLocaleString('es-CL')
          }
        }
      },
      interaction: { mode: 'index', intersect: false },
    }
  });
  charts.push(chart);
}

function createBarChart(canvasId, rows, field, color) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const labels = rows.map(r => r.mes);
  const values = rows.map(r => r[field]);

  const chart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: color,
        borderRadius: 2,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => '$' + Math.round(ctx.raw).toLocaleString('es-CL')
          }
        }
      },
      scales: {
        x: { grid: { display: false }, ticks: { font: { size: 11 } } },
        y: {
          grid: { color: '#f0f0f0' },
          ticks: {
            font: { size: 11 },
            callback: val => '$' + Math.round(val).toLocaleString('es-CL')
          }
        }
      },
    }
  });
  charts.push(chart);
}

function createAFPGroupBar(canvasId, afpRows) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  const labels = afpRows.map(([afp]) => afp);
  const roles = ['Trabajador', 'Empleador', 'Total', 'Independiente'];
  const colors = ['#66bb6a', '#42a5f5', '#ffa726', '#ef5350'];
  const datasets = roles.map((role, i) => ({
    label: role,
    data: afpRows.map(([, tasas]) => {
      const v = tasas[role.toLowerCase()];
      if (!v) return 0;
      const cleaned = String(v).replace('%', '').replace(',', '.').trim();
      return parseFloat(cleaned) || 0;
    }),
    backgroundColor: colors[i],
    borderRadius: 2,
  }));

  const chart = new Chart(ctx, {
    type: 'bar',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { boxWidth: 12, padding: 12, font: { size: 11, family: 'Inter, sans-serif' } } },
        tooltip: {
          callbacks: {
            label: ctx => ctx.dataset.label + ': ' + ctx.raw.toFixed(2) + '%'
          }
        }
      },
      scales: {
        x: { grid: { display: false }, ticks: { font: { size: 10 } } },
        y: {
          grid: { color: '#f0f0f0' },
          ticks: { font: { size: 11 }, callback: val => val + '%' }
        }
      },
    }
  });
  charts.push(chart);
}

function kpiCard(label, value, delta, color) {
  const deltaHTML = delta ? `<div class="kpi-delta">${delta}</div>` : '';
  const style = color ? `style="color:${color};"` : '';
  return `<div class="kpi-card"><div class="kpi-label">${label}</div><div class="kpi-value" ${style}>${value}</div>${deltaHTML}</div>`;
}

function noDataHTML() {
  return '<div class="no-data"><div class="emoji">📊</div><p>No hay datos disponibles para los filtros seleccionados.</p></div>';
}

Chart.defaults.font.family = "'Inter', -apple-system, sans-serif";

async function init() {
  try {
    const res = await fetch('data.json');
    data = await res.json();
  } catch (e) {
    document.body.innerHTML = `
      <div style="display:flex;align-items:center;justify-content:center;height:100vh;flex-direction:column;gap:1rem;color:var(--gray-500);">
        <div style="font-size:3rem;">📊</div>
        <h2 style="font-weight:600;">No hay datos disponibles</h2>
        <p>Ejecuta primero el scraper o genera data.json con:</p>
        <code style="background:var(--gray-100);padding:0.5rem 1rem;border-radius:8px;">python dashboard/generate_data.py</code>
      </div>
    `;
    return;
  }

  if (!data.previred || !data.previred.rows.length) {
    document.body.innerHTML = `
      <div style="display:flex;align-items:center;justify-content:center;height:100vh;flex-direction:column;gap:1rem;color:var(--gray-500);">
        <div style="font-size:3rem;">📊</div>
        <h2 style="font-weight:600;">No hay datos</h2>
        <p>El archivo data.json no contiene registros.</p>
      </div>
    `;
    return;
  }

  applyFilter(getAvailableMonths(data.previred.rows));

  renderSidebar();

  const rangeText = `${filteredPrevired[0].mes} a ${filteredPrevired[filteredPrevired.length - 1].mes} · ${filteredPrevired.length} meses disponibles`;
  document.getElementById('range-text').textContent = rangeText;

  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => renderTab(btn.dataset.tab));
  });

  renderTab('resumen');
}

document.addEventListener('DOMContentLoaded', init);
