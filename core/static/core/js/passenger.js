(function () {
  const csrf = document.getElementById('csrf-token').value;
  const screens = {
    waiting: document.getElementById('screen-waiting'),
    pickup: document.getElementById('screen-pickup'),
    pick: document.getElementById('screen-pick'),
    checkout: document.getElementById('screen-checkout'),
    done: document.getElementById('screen-done'),
  };

  let currentScreen = 'waiting';
  let state = {
    lat: null,
    lng: null,
    pickupStopId: null,
    rideId: null,
    instapayHandle: '',
    pickupStop: null,
    dropStopId: null,
    dropStopName: '',
    fare: null,
    allStops: [],
  };

  function showScreen(name) {
    currentScreen = name;
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
        { enableHighAccuracy: false, timeout: 8000, maximumAge: 60000 }
      );
    });
  }

  async function apiFetch(url, options = {}) {
    const headers = { 'Content-Type': 'application/json', 'X-CSRFToken': csrf, ...(options.headers || {}) };
    const res = await fetch(url, { ...options, headers });
    return res.json();
  }

  function buildActiveUrl() {
    let url = '/api/ride/active/?';
    const params = new URLSearchParams();
    if (state.lat != null && state.lng != null) {
      params.set('lat', state.lat);
      params.set('lng', state.lng);
    }
    if (state.pickupStopId) {
      params.set('pickup_stop_id', state.pickupStopId);
    }
    return `/api/ride/active/?${params.toString()}`;
  }

  function renderStopList(containerId, stops, onSelect) {
    const list = document.getElementById(containerId);
    list.innerHTML = '';
    stops.forEach((stop) => {
      const btn = document.createElement('button');
      btn.className = 'stop-btn';
      btn.innerHTML = `
        <svg class="icon-md" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>
        </svg>
        <span>${stop.name}</span>
        ${stop.cost && stop.cost !== '0.00' ? `<span style="margin-right:auto;color:var(--muted)">${stop.cost} ج</span>` : ''}
      `;
      btn.addEventListener('click', () => onSelect(stop));
      list.appendChild(btn);
    });
  }

  function renderPickScreen(data) {
    document.getElementById('pickup-info').innerHTML =
      `<div>من: <strong>${data.pickup_stop.name}</strong></div>` +
      `<div>الخط: ${data.route_name}</div>`;
    renderStopList('drop-list', data.drop_stops, selectDrop);
  }

  function renderPickupScreen(stops) {
    renderStopList('pickup-list', stops, selectPickup);
  }

  async function selectPickup(stop) {
    state.pickupStopId = stop.id;
    state.pickupStop = stop;
    state.lat = parseFloat(stop.lat);
    state.lng = parseFloat(stop.lng);
    await loadRideWithPickup();
  }

  async function loadRideWithPickup() {
    const data = await fetch(buildActiveUrl()).then((r) => r.json());
    if (!data.active || !data.pickup_stop) return;
    state.rideId = data.ride_id;
    state.instapayHandle = data.instapay_handle;
    if (!data.drop_stops.length) {
      appAlert('مفيش محطة نزول بعد كده.');
      return;
    }
    renderPickScreen(data);
    showScreen('pick');
  }

  async function pollActiveRide() {
    if (currentScreen === 'checkout' || currentScreen === 'done') return;

    try {
      const data = await fetch(buildActiveUrl()).then((r) => r.json());

      if (!data.active) {
        if (currentScreen !== 'pick' && currentScreen !== 'pickup') {
          document.getElementById('waiting-title').textContent = 'استنى شوية';
          document.getElementById('waiting-subtitle').textContent = 'السائق هيبدأ دلوقتي';
          showScreen('waiting');
        }
        return;
      }

      state.rideId = data.ride_id;
      state.instapayHandle = data.instapay_handle;
      state.allStops = data.all_stops || [];

      // Ride active — try GPS once if we don't have coords yet
      if (state.lat == null && !state.pickupStopId) {
        try {
          const loc = await getLocation();
          state.lat = loc.lat;
          state.lng = loc.lng;
          return pollActiveRide();
        } catch {
          // GPS blocked (common on HTTP) — manual pickup
          if (currentScreen === 'waiting') {
            renderPickupScreen(data.all_stops);
            showScreen('pickup');
          }
          return;
        }
      }

      if (data.needs_pickup && !state.pickupStopId) {
        if (currentScreen === 'waiting') {
          renderPickupScreen(data.all_stops);
          showScreen('pickup');
        }
        return;
      }

      if (data.pickup_stop && data.drop_stops) {
        if (!data.drop_stops.length) {
          if (currentScreen === 'waiting' || currentScreen === 'pickup') {
            appAlert('أنت في آخر محطة — مفيش نزول.');
          }
          return;
        }
        state.pickupStop = data.pickup_stop;
        state.pickupStopId = data.pickup_stop.id;
        if (currentScreen === 'waiting' || currentScreen === 'pickup') {
          renderPickScreen(data);
          showScreen('pick');
        }
      }
    } catch {
      if (currentScreen === 'waiting') showScreen('waiting');
    }
  }

  async function selectDrop(stop) {
    state.dropStopId = stop.id;
    state.dropStopName = stop.name;

    const body = {
      ride_id: state.rideId,
      drop_stop_id: stop.id,
      lat: state.lat,
      lng: state.lng,
    };
    if (state.pickupStopId) body.pickup_stop_id = state.pickupStopId;

    const preview = await apiFetch('/api/fare/preview/', {
      method: 'POST',
      body: JSON.stringify(body),
    });

    if (preview.error) {
      appAlert(preview.error);
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
    const body = {
      ride_id: state.rideId,
      drop_stop_id: state.dropStopId,
      lat: state.lat,
      lng: state.lng,
      payment_method: paymentMethod,
    };
    if (state.pickupStopId) body.pickup_stop_id = state.pickupStopId;

    const result = await apiFetch('/api/passenger/checkout/', {
      method: 'POST',
      body: JSON.stringify(body),
    });

    if (result.error) {
      appAlert(result.error);
      return;
    }

    showScreen('done');
    setTimeout(resetAndPoll, 2000);
  }

  function resetAndPoll() {
    state.pickupStopId = null;
    state.pickupStop = null;
    state.dropStopId = null;
    state.dropStopName = '';
    state.fare = null;
    state.lat = null;
    state.lng = null;
    document.getElementById('qr-section').classList.add('hidden');
    showScreen('waiting');
    pollActiveRide();
  }

  document.getElementById('btn-instapay').addEventListener('click', () => checkout('INSTAPAY'));
  document.getElementById('btn-cash').addEventListener('click', () => checkout('CASH'));

  pollActiveRide();
  setInterval(pollActiveRide, 3000);
})();
