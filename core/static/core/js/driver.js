(function () {
  const csrf = document.getElementById('csrf-token').value;
  let stops = [];
  let manualPickup = null;
  let manualDrop = null;
  let manualPayment = 'CASH';
  let lastState = null;

  const ICONS = {
    cash: '<svg class="icon-md" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="3"/></svg>',
    cancel: '<svg class="icon-md" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
    pin: '<svg class="icon-md" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>',
  };

  async function apiFetch(url, options = {}) {
    const headers = { 'Content-Type': 'application/json', 'X-CSRFToken': csrf, ...(options.headers || {}) };
    const res = await fetch(url, { ...options, headers });
    return res.json();
  }

  function paymentBadge(method) {
    return method === 'INSTAPAY'
      ? '<span class="badge badge-instapay">إنستا</span>'
      : '<span class="badge badge-cash">كاش</span>';
  }

  function statusBadge(status) {
    return status === 'PAID'
      ? '<span class="badge badge-paid">اتدفع</span>'
      : '<span class="badge badge-pending">لسه</span>';
  }

  function dropCountText(n) {
    if (n === 0) return 'محدش هينزل';
    if (n === 1) return 'واحد هينزل';
    if (n === 2) return 'اتنين هينزلوا';
    return `${n} هينزلوا`;
  }

  function renderArriveSection(data) {
    const section = document.getElementById('arrive-section');
    const current = data.current_stop ? data.current_stop.name : 'لسه ما وصلناش';
    const currentHtml = `<p class="arrive-current">${ICONS.pin} آخر محطة: <strong>${current}</strong></p>`;

    if (!data.next_stop) {
      section.innerHTML = currentHtml + '<p class="big-hint">خلصنا كل المحطات</p>';
      return;
    }

    const n = data.dropping_count || 0;
    const names = (data.dropping_at_next || []).map((p) => p.drop).join('، ');
    const dropHint = n > 0
      ? `<p class="arrive-drop-hint">${dropCountText(n)} هنا: ${names}</p>`
      : `<p class="arrive-drop-hint">${dropCountText(n)}</p>`;

    section.innerHTML = `
      ${currentHtml}
      <p class="arrive-next-label">المحطة الجاية</p>
      <p class="arrive-next-name">${data.next_stop.name}</p>
      ${dropHint}
      <button class="btn btn-primary btn-big" id="btn-arrive" type="button">
        ${ICONS.pin}
        وصلنا ${data.next_stop.name}
      </button>
    `;

    document.getElementById('btn-arrive').addEventListener('click', () => handleArrive(data));
  }

  async function handleArrive(data) {
    const res = await apiFetch('/driver/api/ride/arrive/', { method: 'POST', body: '{}' });
    if (res.error) {
      await appAlert(res.error);
      return;
    }
    poll();
  }

  function renderPassengers(passengers, nextStopId) {
    const list = document.getElementById('passenger-list');
    const empty = document.getElementById('no-passengers');
    list.innerHTML = '';

    if (!passengers.length) {
      empty.classList.remove('hidden');
      return;
    }
    empty.classList.add('hidden');

    passengers.forEach((p) => {
      const droppingHere = nextStopId && p.drop_stop_id === nextStopId;
      const card = document.createElement('div');
      card.className = 'passenger-card' + (droppingHere ? ' dropping-soon' : '');
      card.innerHTML = `
        <div class="passenger-route">${p.pickup} ← ${p.drop}</div>
        ${droppingHere ? '<div class="drop-soon-badge">هينزل في المحطة الجاية</div>' : ''}
        <div class="passenger-meta">
          <span class="fare-tag">${p.fare} ج</span>
          ${paymentBadge(p.payment_method)}
          ${statusBadge(p.payment_status)}
        </div>
        <div class="passenger-actions"></div>
      `;
      const actions = card.querySelector('.passenger-actions');

      if (p.payment_method === 'CASH' && p.payment_status === 'PENDING') {
        const verifyBtn = document.createElement('button');
        verifyBtn.className = 'btn btn-primary btn-sm btn-icon';
        verifyBtn.innerHTML = ICONS.cash + ' استلمت';
        verifyBtn.addEventListener('click', () => action(`/driver/api/passenger/${p.id}/verify-cash/`));
        actions.appendChild(verifyBtn);
      }

      const cancelBtn = document.createElement('button');
      cancelBtn.className = 'btn btn-danger btn-sm btn-icon';
      cancelBtn.innerHTML = ICONS.cancel + ' الغي';
      cancelBtn.addEventListener('click', () => action(`/driver/api/passenger/${p.id}/cancel/`));
      actions.appendChild(cancelBtn);

      list.appendChild(card);
    });
  }

  function renderStopButtons(containerId, stopItems, onSelect, selectedId) {
    const list = document.getElementById(containerId);
    list.innerHTML = '';
    stopItems.forEach((s) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'stop-btn' + (selectedId === s.id ? ' selected' : '');
      btn.innerHTML = `
        <svg class="icon-md" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>
        </svg>
        <span>${s.name}</span>
      `;
      btn.addEventListener('click', () => onSelect(s));
      list.appendChild(btn);
    });
  }

  function renderManualForm() {
    renderStopButtons('manual-pickup-list', stops, selectManualPickup, manualPickup?.id);

    const pickupLabel = document.getElementById('manual-pickup-selected');
    const dropSection = document.getElementById('manual-drop-list');
    const dropLabel = document.getElementById('manual-drop-selected');

    if (manualPickup) {
      pickupLabel.textContent = '✓ من: ' + manualPickup.name;
      pickupLabel.classList.remove('hidden');
      dropSection.classList.remove('hidden');
      const dropStops = stops.filter((s) => s.order > manualPickup.order);
      renderStopButtons('manual-drop-list', dropStops, selectManualDrop, manualDrop?.id);
    } else {
      pickupLabel.classList.add('hidden');
      dropSection.classList.add('hidden');
      dropLabel.classList.add('hidden');
      manualDrop = null;
    }

    if (manualDrop) {
      dropLabel.textContent = '✓ ينزل: ' + manualDrop.name;
      dropLabel.classList.remove('hidden');
    } else {
      dropLabel.classList.add('hidden');
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
    document.querySelectorAll('.pay-btn').forEach((btn) => {
      btn.classList.toggle('selected', btn.dataset.pay === 'CASH');
    });
    renderManualForm();
  }

  function renderState(data) {
    lastState = data;
    document.getElementById('route-label').textContent = data.route_name || '';

    const newStops = data.stops || [];
    const stopsChanged = JSON.stringify(newStops.map((s) => s.id)) !== JSON.stringify(stops.map((s) => s.id));
    stops = newStops;

    if (!data.active_ride) {
      document.getElementById('no-ride').classList.remove('hidden');
      document.getElementById('active-ride').classList.add('hidden');
      if (stopsChanged) renderManualForm();
      return;
    }

    document.getElementById('no-ride').classList.add('hidden');
    document.getElementById('active-ride').classList.remove('hidden');

    const pct = Math.min(100, (data.active_count / data.max_capacity) * 100);
    document.getElementById('capacity-text').textContent =
      `${data.active_count} من ${data.max_capacity}`;
    document.getElementById('capacity-fill').style.width = `${pct}%`;

    renderArriveSection(data);
    renderPassengers(data.passengers || [], data.next_stop?.id);
    if (stopsChanged || !manualPickup) renderManualForm();
  }

  async function poll() {
    try {
      const data = await fetch('/driver/api/state/').then((r) => r.json());
      renderState(data);
    } catch {
      // retry
    }
  }

  async function action(url) {
    await apiFetch(url, { method: 'POST', body: '{}' });
    poll();
  }

  document.querySelectorAll('.pay-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      manualPayment = btn.dataset.pay;
      document.querySelectorAll('.pay-btn').forEach((b) => b.classList.remove('selected'));
      btn.classList.add('selected');
    });
  });

  document.getElementById('btn-start-ride').addEventListener('click', async () => {
    const res = await apiFetch('/driver/api/ride/start/', { method: 'POST', body: '{}' });
    if (res.error) await appAlert(res.error);
    poll();
  });

  document.getElementById('btn-end-ride').addEventListener('click', async () => {
    const yes = await appConfirm('خلصنا الشغل النهاردة؟');
    if (!yes) return;
    const res = await apiFetch('/driver/api/ride/end/', { method: 'POST', body: '{}' });
    if (res.error) await appAlert(res.error);
    poll();
  });

  document.getElementById('btn-manual-add').addEventListener('click', async () => {
    if (!manualPickup || !manualDrop) {
      await appAlert('اختار منين وفين ينزل — اضغط على المحطة');
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
    if (res.error) {
      await appAlert(res.error);
      return;
    }
    resetManualForm();
    poll();
  });

  poll();
  setInterval(poll, 3000);
})();
