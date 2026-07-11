(function () {
  const csrf = document.getElementById('csrf-token').value;
  let stops = [];
  let manualPickup = null;
  let manualDrop = null;
  let manualPayment = 'CASH';
  let endingRide = false;

  async function apiFetch(url, options = {}) {
    const headers = { 'Content-Type': 'application/json', 'X-CSRFToken': csrf, ...(options.headers || {}) };
    const res = await fetch(url, { ...options, headers });
    return res.json();
  }

  function dropCountText(n) {
    if (n === 0) return 'محدش';
    if (n === 1) return '١';
    if (n === 2) return '٢';
    return String(n);
  }

  function renderArriveSection(data) {
    const section = document.getElementById('arrive-section');
    const current = data.current_stop ? data.current_stop.name : '—';

    if (!data.next_stop) {
      section.innerHTML = `
        <div class="arrive-done">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
          <span>خلصنا الخط</span>
        </div>`;
      return;
    }

    const n = data.dropping_count || 0;
    section.innerHTML = `
      <div class="arrive-meta">
        <span class="arrive-from"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/></svg>${current}</span>
        <span class="arrive-arrow">←</span>
        <span class="arrive-to"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>${data.next_stop.name}</span>
      </div>
      <div class="arrive-drop-badge">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>
        <strong>${dropCountText(n)}</strong>
        <span>ينزلوا</span>
      </div>
      <button class="btn-arrive" id="btn-arrive" type="button">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
        <span>وصلنا</span>
      </button>
    `;
    document.getElementById('btn-arrive').addEventListener('click', () => handleArrive());
  }

  async function handleArrive() {
    const res = await apiFetch('/driver/api/ride/arrive/', { method: 'POST', body: '{}' });
    if (res.error) await appAlert(res.error);
    else poll();
  }

  async function autoEndRide() {
    if (endingRide) return;
    endingRide = true;
    const res = await apiFetch('/driver/api/ride/end/', { method: 'POST', body: '{}' });
    if (res.error) endingRide = false;
    poll();
  }

  function renderPassengers(passengers, nextStopId) {
    const list = document.getElementById('passenger-list');
    const empty = document.getElementById('no-passengers');
    const countEl = document.getElementById('passenger-count');
    list.innerHTML = '';
    if (countEl) countEl.textContent = passengers.length ? passengers.length : '';

    if (!passengers.length) {
      empty.classList.remove('hidden');
      return;
    }
    empty.classList.add('hidden');

    passengers.forEach((p) => {
      const droppingHere = nextStopId && p.drop_stop_id === nextStopId;
      const card = document.createElement('div');
      card.className = 'pax-row' + (droppingHere ? ' dropping' : '');
      card.innerHTML = `
        <div class="pax-route">
          <span class="pax-from">${p.pickup}</span>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
          <span class="pax-to">${p.drop}</span>
        </div>
        <div class="pax-bottom">
          <span class="pax-fare">${p.fare} ج</span>
          <div class="pax-meta-row">
            <div class="pax-badges">
              ${p.payment_method === 'INSTAPAY'
                ? '<span class="mini-badge insta"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/></svg></span>'
                : '<span class="mini-badge cash"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="6" width="20" height="12" rx="2"/></svg></span>'}
              ${p.payment_status !== 'PAID' ? '<span class="mini-badge pending">!</span>' : ''}
            </div>
            <div class="pax-actions"></div>
          </div>
        </div>
      `;
      const actions = card.querySelector('.pax-actions');
      if (p.payment_method === 'CASH' && p.payment_status === 'PENDING') {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'icon-circle-btn success';
        btn.title = 'استلمت';
        btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="3"/></svg>';
        btn.addEventListener('click', () => action(`/driver/api/passenger/${p.id}/verify-cash/`));
        actions.appendChild(btn);
      }
      const cancelBtn = document.createElement('button');
      cancelBtn.type = 'button';
      cancelBtn.className = 'icon-circle-btn danger';
      cancelBtn.title = 'الغي';
      cancelBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
      cancelBtn.addEventListener('click', () => action(`/driver/api/passenger/${p.id}/cancel/`));
      actions.appendChild(cancelBtn);
      list.appendChild(card);
    });
  }

  function renderStopGrid(containerId, stopItems, onSelect, selectedId) {
    const list = document.getElementById(containerId);
    if (!list) return;
    list.innerHTML = '';
    stopItems.forEach((s) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'stop-tile' + (selectedId === s.id ? ' selected' : '');
      btn.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
        <span>${s.name}</span>
      `;
      btn.addEventListener('click', () => onSelect(s));
      list.appendChild(btn);
    });
  }

  function renderManualForm() {
    renderStopGrid('manual-pickup-list', stops, selectManualPickup, manualPickup?.id);

    const pickupChip = document.getElementById('manual-pickup-selected');
    const dropList = document.getElementById('manual-drop-list');
    const dropStep = document.getElementById('drop-step-label');
    const dropChip = document.getElementById('manual-drop-selected');
    const payStep = document.getElementById('pay-step-label');
    const payGrid = document.getElementById('pay-step');
    const addBtn = document.getElementById('btn-manual-add');

    if (manualPickup) {
      pickupChip.textContent = '✓ ' + manualPickup.name;
      pickupChip.classList.remove('hidden');
      dropStep.classList.remove('hidden');
      dropList.classList.remove('hidden');
      renderStopGrid('manual-drop-list', stops.filter((s) => s.order > manualPickup.order), selectManualDrop, manualDrop?.id);
    } else {
      pickupChip.classList.add('hidden');
      dropStep.classList.add('hidden');
      dropList.classList.add('hidden');
      dropChip.classList.add('hidden');
      payStep.classList.add('hidden');
      payGrid.classList.add('hidden');
      addBtn.classList.add('hidden');
      manualDrop = null;
    }

    if (manualDrop) {
      dropChip.textContent = '✓ ' + manualDrop.name;
      dropChip.classList.remove('hidden');
      payStep.classList.remove('hidden');
      payGrid.classList.remove('hidden');
      addBtn.classList.remove('hidden');
    } else if (manualPickup) {
      dropChip.classList.add('hidden');
      payStep.classList.add('hidden');
      payGrid.classList.add('hidden');
      addBtn.classList.add('hidden');
    }
  }

  function selectManualPickup(stop) {
    manualPickup = stop;
    manualDrop = null;
    renderManualForm();
  }

  function selectManualDrop(stop) {
    manualDrop = stop;
    renderManualForm();
  }

  function resetManualForm() {
    manualPickup = null;
    manualDrop = null;
    manualPayment = 'CASH';
    document.querySelectorAll('.pay-tile').forEach((btn) => {
      btn.classList.toggle('selected', btn.dataset.pay === 'CASH');
    });
    renderManualForm();
  }

  function renderState(data) {
    const routeLabel = document.getElementById('route-label');
    if (routeLabel) routeLabel.textContent = data.route_name || '';

    const newStops = data.stops || [];
    const stopsChanged = JSON.stringify(newStops.map((s) => s.id)) !== JSON.stringify(stops.map((s) => s.id));
    stops = newStops;

    if (!data.active_ride) {
      document.getElementById('no-ride').classList.remove('hidden');
      document.getElementById('active-ride').classList.add('hidden');
      return;
    }

    document.getElementById('no-ride').classList.add('hidden');
    document.getElementById('active-ride').classList.remove('hidden');

    const pct = Math.min(100, (data.active_count / data.max_capacity) * 100);
    document.getElementById('capacity-text').textContent = `${data.active_count}/${data.max_capacity}`;
    document.getElementById('capacity-fill').style.width = `${pct}%`;

    renderArriveSection(data);
    renderPassengers(data.passengers || [], data.next_stop?.id);
    if (stopsChanged || !manualPickup) renderManualForm();

    if (!data.next_stop && data.route_finished) {
      autoEndRide();
    }
  }

  async function poll() {
    try {
      const data = await fetch('/driver/api/state/').then((r) => r.json());
      renderState(data);
    } catch { /* retry */ }
  }

  async function action(url) {
    await apiFetch(url, { method: 'POST', body: '{}' });
    poll();
  }

  document.querySelectorAll('.pay-tile').forEach((btn) => {
    btn.addEventListener('click', () => {
      manualPayment = btn.dataset.pay;
      document.querySelectorAll('.pay-tile').forEach((b) => b.classList.remove('selected'));
      btn.classList.add('selected');
    });
  });

  document.getElementById('btn-start-ride').addEventListener('click', async () => {
    const res = await apiFetch('/driver/api/ride/start/', { method: 'POST', body: '{}' });
    if (res.error) await appAlert(res.error);
    else endingRide = false;
    poll();
  });

  document.getElementById('btn-end-ride').addEventListener('click', async () => {
    const yes = await appConfirm('خلصنا الشغل؟');
    if (!yes) return;
    const res = await apiFetch('/driver/api/ride/end/', { method: 'POST', body: '{}' });
    if (res.error) await appAlert(res.error);
    poll();
  });

  document.getElementById('btn-manual-add').addEventListener('click', async () => {
    if (!manualPickup || !manualDrop) {
      await appAlert('اختار المحطتين');
      return;
    }
    const res = await apiFetch('/driver/api/passenger/add/', {
      method: 'POST',
      body: JSON.stringify({
        pickup_stop_id: manualPickup.id,
        drop_stop_id: manualDrop.id,
        payment_method: manualPayment,
      }),
    });
    if (res.error) await appAlert(res.error);
    else { resetManualForm(); poll(); }
  });

  poll();
  setInterval(poll, 3000);
})();
