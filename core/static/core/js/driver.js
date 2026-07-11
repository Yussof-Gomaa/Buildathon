(function () {
  const csrf = document.getElementById('csrf-token').value;
  let stops = [];
  let pollTimer = null;

  async function apiFetch(url, options = {}) {
    const headers = { 'Content-Type': 'application/json', 'X-CSRFToken': csrf, ...(options.headers || {}) };
    const res = await fetch(url, { ...options, headers });
    return res.json();
  }

  function paymentBadge(method) {
    return method === 'INSTAPAY'
      ? '<span class="badge badge-instapay">إنستاباي</span>'
      : '<span class="badge badge-cash">نقدي</span>';
  }

  function statusBadge(status) {
    return status === 'PAID'
      ? '<span class="badge badge-paid">مدفوع</span>'
      : '<span class="badge badge-pending">بانتظار التحقق</span>';
  }

  function renderPassengers(passengers) {
    const list = document.getElementById('passenger-list');
    const empty = document.getElementById('no-passengers');
    list.innerHTML = '';

    if (!passengers.length) {
      empty.classList.remove('hidden');
      return;
    }
    empty.classList.add('hidden');

    passengers.forEach((p) => {
      const card = document.createElement('div');
      card.className = 'passenger-card';
      card.innerHTML = `
        <div class="passenger-route">${p.pickup} → ${p.drop}</div>
        <div class="passenger-meta">
          <span>${p.fare} ج</span>
          ${paymentBadge(p.payment_method)}
          ${statusBadge(p.payment_status)}
        </div>
        <div class="passenger-actions"></div>
      `;
      const actions = card.querySelector('.passenger-actions');

      if (p.payment_method === 'CASH' && p.payment_status === 'PENDING') {
        const verifyBtn = document.createElement('button');
        verifyBtn.className = 'btn btn-primary btn-sm';
        verifyBtn.textContent = 'تحقق نقدي';
        verifyBtn.addEventListener('click', () => action(`/driver/api/passenger/${p.id}/verify-cash/`));
        actions.appendChild(verifyBtn);
      }

      const dropBtn = document.createElement('button');
      dropBtn.className = 'btn btn-outline btn-sm';
      dropBtn.textContent = 'نزل';
      dropBtn.addEventListener('click', () => action(`/driver/api/passenger/${p.id}/drop/`));
      actions.appendChild(dropBtn);

      const cancelBtn = document.createElement('button');
      cancelBtn.className = 'btn btn-danger btn-sm';
      cancelBtn.textContent = 'إلغاء';
      cancelBtn.addEventListener('click', () => action(`/driver/api/passenger/${p.id}/cancel/`));
      actions.appendChild(cancelBtn);

      list.appendChild(card);
    });
  }

  function fillStopSelects() {
    const pickup = document.getElementById('manual-pickup');
    const drop = document.getElementById('manual-drop');
    pickup.innerHTML = '<option value="">نقطة الالتقاط</option>';
    drop.innerHTML = '<option value="">نقطة النزول</option>';
    stops.forEach((s) => {
      pickup.innerHTML += `<option value="${s.id}">${s.name}</option>`;
      drop.innerHTML += `<option value="${s.id}">${s.name}</option>`;
    });
  }

  function renderState(data) {
    document.getElementById('route-label').textContent = data.route_name || '';

    if (!data.active_ride) {
      document.getElementById('no-ride').classList.remove('hidden');
      document.getElementById('active-ride').classList.add('hidden');
      stops = data.stops || [];
      fillStopSelects();
      return;
    }

    document.getElementById('no-ride').classList.add('hidden');
    document.getElementById('active-ride').classList.remove('hidden');

    const pct = Math.min(100, (data.active_count / data.max_capacity) * 100);
    document.getElementById('capacity-text').textContent =
      `${data.active_count} / ${data.max_capacity} راكب`;
    document.getElementById('capacity-fill').style.width = `${pct}%`;

    stops = data.stops || [];
    fillStopSelects();
    renderPassengers(data.passengers || []);
  }

  async function poll() {
    try {
      const data = await fetch('/driver/api/state/').then((r) => r.json());
      renderState(data);
    } catch {
      // silent retry
    }
  }

  async function action(url) {
    await apiFetch(url, { method: 'POST', body: '{}' });
    poll();
  }

  document.getElementById('btn-start-ride').addEventListener('click', async () => {
    const res = await apiFetch('/driver/api/ride/start/', { method: 'POST', body: '{}' });
    if (res.error) alert(res.error);
    poll();
  });

  document.getElementById('btn-end-ride').addEventListener('click', async () => {
    if (!confirm('إنهاء الرحلة؟')) return;
    const res = await apiFetch('/driver/api/ride/end/', { method: 'POST', body: '{}' });
    if (res.error) alert(res.error);
    poll();
  });

  document.getElementById('btn-manual-add').addEventListener('click', async () => {
    const pickupId = document.getElementById('manual-pickup').value;
    const dropId = document.getElementById('manual-drop').value;
    const payment = document.getElementById('manual-payment').value;
    if (!pickupId || !dropId) {
      alert('اختر نقطة الالتقاط والنزول');
      return;
    }
    const res = await apiFetch('/driver/api/passenger/add/', {
      method: 'POST',
      body: JSON.stringify({
        pickup_stop_id: pickupId,
        drop_stop_id: dropId,
        payment_method: payment,
      }),
    });
    if (res.error) alert(res.error);
    poll();
  });

  poll();
  pollTimer = setInterval(poll, 3000);
})();
