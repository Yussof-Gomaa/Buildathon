(function () {
  const csrf = document.getElementById('csrf-token').value;
  const screens = {
    waiting: document.getElementById('screen-waiting'),
    pick: document.getElementById('screen-pick'),
    checkout: document.getElementById('screen-checkout'),
    done: document.getElementById('screen-done'),
  };

  let state = {
    lat: null,
    lng: null,
    rideId: null,
    instapayHandle: '',
    pickupStop: null,
    dropStopId: null,
    dropStopName: '',
    fare: null,
  };

  let pollTimer = null;

  function showScreen(name) {
    Object.values(screens).forEach((s) => s.classList.remove('active'));
    screens[name].classList.add('active');
  }

  function getLocation() {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error('no geo'));
        return;
      }
      navigator.geolocation.getCurrentPosition(
        (pos) => resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
        () => reject(new Error('denied')),
        { enableHighAccuracy: true, timeout: 10000 }
      );
    });
  }

  async function apiFetch(url, options = {}) {
    const headers = { 'Content-Type': 'application/json', 'X-CSRFToken': csrf, ...(options.headers || {}) };
    const res = await fetch(url, { ...options, headers });
    return res.json();
  }

  async function pollActiveRide() {
    try {
      let url = '/api/ride/active/';
      if (state.lat != null) {
        url += `?lat=${state.lat}&lng=${state.lng}`;
      }
      const data = await fetch(url).then((r) => r.json());

      if (!data.active) {
        showScreen('waiting');
        return;
      }

      if (data.needs_location) {
        try {
          const loc = await getLocation();
          state.lat = loc.lat;
          state.lng = loc.lng;
          return pollActiveRide();
        } catch {
          showScreen('waiting');
          return;
        }
      }

      state.rideId = data.ride_id;
      state.instapayHandle = data.instapay_handle;
      state.pickupStop = data.pickup_stop;
      renderPickScreen(data);
      showScreen('pick');
    } catch {
      showScreen('waiting');
    }
  }

  function renderPickScreen(data) {
    document.getElementById('pickup-info').innerHTML =
      `<div>من: <strong>${data.pickup_stop.name}</strong></div>` +
      `<div>المسار: ${data.route_name}</div>`;

    const list = document.getElementById('drop-list');
    list.innerHTML = '';
    data.drop_stops.forEach((stop) => {
      const btn = document.createElement('button');
      btn.className = 'stop-btn';
      btn.innerHTML = `
        <svg class="icon-md" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>
        </svg>
        <span>${stop.name}</span>
        <span style="margin-right:auto;color:var(--muted)">${stop.cost} ج</span>
      `;
      btn.addEventListener('click', () => selectDrop(stop));
      list.appendChild(btn);
    });
  }

  async function selectDrop(stop) {
    state.dropStopId = stop.id;
    state.dropStopName = stop.name;

    const preview = await apiFetch('/api/fare/preview/', {
      method: 'POST',
      body: JSON.stringify({
        ride_id: state.rideId,
        drop_stop_id: stop.id,
        lat: state.lat,
        lng: state.lng,
      }),
    });

    if (preview.error) {
      alert(preview.error);
      return;
    }

    state.fare = preview.fare;
    document.getElementById('fare-amount').innerHTML = `${preview.fare} <span>جنيه</span>`;
    document.getElementById('checkout-info').innerHTML =
      `<div>من: <strong>${preview.pickup_stop_name}</strong></div>` +
      `<div>إلى: <strong>${preview.drop_stop_name}</strong></div>`;

    const qrText = encodeURIComponent(`ادفع ${preview.fare} جنيه إلى ${state.instapayHandle}`);
    document.getElementById('qr-image').src = `/qr/?text=${qrText}`;
    document.getElementById('qr-section').classList.remove('hidden');

    showScreen('checkout');
  }

  async function checkout(paymentMethod) {
    const result = await apiFetch('/api/passenger/checkout/', {
      method: 'POST',
      body: JSON.stringify({
        ride_id: state.rideId,
        drop_stop_id: state.dropStopId,
        lat: state.lat,
        lng: state.lng,
        payment_method: paymentMethod,
      }),
    });

    if (result.error) {
      alert(result.error);
      return;
    }

    showScreen('done');
    setTimeout(resetAndPoll, 2000);
  }

  function resetAndPoll() {
    state.dropStopId = null;
    state.dropStopName = '';
    state.fare = null;
    document.getElementById('qr-section').classList.add('hidden');
    showScreen('waiting');
    pollActiveRide();
  }

  document.getElementById('btn-instapay').addEventListener('click', () => checkout('INSTAPAY'));
  document.getElementById('btn-cash').addEventListener('click', () => checkout('CASH'));

  async function init() {
    try {
      const loc = await getLocation();
      state.lat = loc.lat;
      state.lng = loc.lng;
    } catch {
      // Will retry when ride becomes active
    }
    pollActiveRide();
    pollTimer = setInterval(pollActiveRide, 3000);
  }

  init();
})();
