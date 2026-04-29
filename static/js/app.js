/* Locks Manager — Global JS */

// ── Flash auto-dismiss ────────────────────────────────────
document.querySelectorAll('.alert').forEach(el => {
  setTimeout(() => el.remove(), 4500);
  el.addEventListener('click', () => el.remove());
});

// ── Mobile sidebar toggle ─────────────────────────────────
const sidebar = document.querySelector('.sidebar');
const menuBtn = document.querySelector('.menu-toggle');
const overlay = document.getElementById('sidebar-overlay');

function openSidebar() {
  sidebar && sidebar.classList.add('open');
  overlay && (overlay.style.display = 'block');
}
function closeSidebar() {
  sidebar && sidebar.classList.remove('open');
  overlay && (overlay.style.display = 'none');
}

menuBtn && menuBtn.addEventListener('click', openSidebar);
overlay && overlay.addEventListener('click', closeSidebar);

// ── Tab switching ─────────────────────────────────────────
document.querySelectorAll('[data-tab]').forEach(btn => {
  btn.addEventListener('click', () => {
    const target = btn.dataset.tab;
    const parent = btn.closest('[data-tabs-parent]') || document;

    parent.querySelectorAll('[data-tab]').forEach(b => b.classList.remove('active'));
    parent.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

    btn.classList.add('active');
    const content = parent.querySelector(`#tab-${target}`);
    content && content.classList.add('active');
  });
});

// ── Quarter selector ──────────────────────────────────────
document.querySelectorAll('.quarter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const group = btn.dataset.group;
    const isMulti = btn.dataset.multi === 'true';
    const hiddenField = document.querySelector(`input[name="${group}"]`);

    if (isMulti) {
      btn.classList.toggle('selected');
      const selected = [...document.querySelectorAll(`.quarter-btn[data-group="${group}"].selected`)]
        .map(b => b.dataset.value);
      // Update hidden checkboxes instead
    } else {
      document.querySelectorAll(`.quarter-btn[data-group="${group}"]`).forEach(b => b.classList.remove('selected'));
      btn.classList.add('selected');
      if (hiddenField) hiddenField.value = btn.dataset.value;
    }
  });
});

// ── Battery voltage → percentage live calc ────────────────
const voltageInput = document.getElementById('voltage-input');
const batteryPreview = document.getElementById('battery-preview');
const batteryPctDisplay = document.getElementById('battery-pct-display');

const MAX_V = 4.5;
const MIN_V = 2.7;

function calcPct(v) {
  return Math.max(0, Math.min(100, Math.round((v - MIN_V) / (MAX_V - MIN_V) * 100)));
}

function batteryColorClass(pct) {
  if (pct >= 75) return 'success';
  if (pct >= 50) return 'warning-light';
  if (pct >= 25) return 'warning';
  return 'danger';
}

if (voltageInput) {
  voltageInput.addEventListener('input', () => {
    const v = parseFloat(voltageInput.value);
    if (isNaN(v) || v < 0 || v > 5) return;
    const pct = calcPct(v);
    const color = batteryColorClass(pct);

    if (batteryPreview) {
      const fill = batteryPreview.querySelector('.battery-fill');
      if (fill) {
        fill.style.width = pct + '%';
        fill.className = `battery-fill ${color}`;
      }
    }

    if (batteryPctDisplay) {
      batteryPctDisplay.textContent = pct + '%';
      batteryPctDisplay.className = `battery-pct ${color}`;
    }
  });
}

// ── Confirm dangerous actions ─────────────────────────────
document.querySelectorAll('[data-confirm]').forEach(el => {
  el.addEventListener('click', e => {
    if (!confirm(el.dataset.confirm)) e.preventDefault();
  });
});

// ── Inline maintenance form save (quick-fill table) ───────
const quickSaveBtn = document.getElementById('quick-save-all');

if (quickSaveBtn) {
  quickSaveBtn.addEventListener('click', async () => {
    const rows = document.querySelectorAll('tr[data-lock-id]');
    const records = [];

    rows.forEach(row => {
      const lockId = row.dataset.lockId;
      const q = row.dataset.quarter;
      const yr = row.dataset.year;
      const status = row.querySelector('[data-field=status]')?.value;
      const annotations = row.querySelector('[data-field=annotations]')?.value;
      const technician = row.querySelector('[data-field=technician]')?.value;
      const supervisor = row.querySelector('[data-field=supervisor]')?.value;
      const date = row.querySelector('[data-field=maintenance_date]')?.value;
      const time = row.querySelector('[data-field=maintenance_time]')?.value;

      if (status) {
        records.push({ lock_id: lockId, quarter: q, year: yr,
                       status, annotations, technician, supervisor,
                       maintenance_date: date, maintenance_time: time,
                       maintenance_type: 'Preventivo' });
      }
    });

    if (!records.length) { alert('No hay filas con estado asignado para guardar.'); return; }

    if (!confirm(`¿Guardar ${records.length} registro(s) de mantenimiento?`)) return;

    quickSaveBtn.disabled = true;
    quickSaveBtn.textContent = 'Guardando…';

    try {
      const resp = await fetch('/maintenance/bulk', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ records })
      });
      const data = await resp.json();
      showFlash(`${data.saved} registros guardados.`, 'success');
    } catch {
      showFlash('Error al guardar. Intenta de nuevo.', 'danger');
    } finally {
      quickSaveBtn.disabled = false;
      quickSaveBtn.textContent = '💾 Guardar Todo';
    }
  });
}

// ── Show flash programmatically ───────────────────────────
function showFlash(msg, type = 'info') {
  let container = document.querySelector('.flash-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'flash-container';
    document.body.appendChild(container);
  }
  const el = document.createElement('div');
  el.className = `alert alert-${type}`;
  el.textContent = msg;
  container.appendChild(el);
  setTimeout(() => el.remove(), 4500);
}

// ── Sector edit modal ─────────────────────────────────────
document.querySelectorAll('[data-open-modal]').forEach(btn => {
  btn.addEventListener('click', () => {
    const id = btn.dataset.openModal;
    const modal = document.getElementById(id);
    modal && modal.classList.add('open');
  });
});

document.querySelectorAll('[data-close-modal]').forEach(btn => {
  btn.addEventListener('click', () => {
    const id = btn.dataset.closeModal;
    const modal = document.getElementById(id);
    modal && modal.classList.remove('open');
  });
});

document.querySelectorAll('.modal-overlay').forEach(modal => {
  modal.addEventListener('click', e => {
    if (e.target === modal) modal.classList.remove('open');
  });
});

// ── Lock selector: filter by sector ──────────────────────
const sectorSelect = document.getElementById('sector-filter-select');
const lockSelect = document.getElementById('lock-select');

if (sectorSelect && lockSelect) {
  sectorSelect.addEventListener('change', async () => {
    const sid = sectorSelect.value;
    const url = `/locks/api/list${sid ? '?sector_id=' + sid : ''}`;
    const resp = await fetch(url);
    const locks = await resp.json();

    lockSelect.innerHTML = '<option value="">— Seleccionar —</option>';
    locks.forEach(l => {
      const opt = document.createElement('option');
      opt.value = l.id;
      opt.textContent = `${l.room_code}${l.room_name ? ' — ' + l.room_name : ''}`;
      lockSelect.appendChild(opt);
    });
  });
}
