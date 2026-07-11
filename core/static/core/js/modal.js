(function () {
  let modalEl, titleEl, messageEl, actionsEl, onConfirmCb;

  function ensureModal() {
    if (modalEl) return;
    modalEl = document.createElement('div');
    modalEl.id = 'app-modal';
    modalEl.className = 'app-modal hidden';
    modalEl.innerHTML = `
      <div class="app-modal-backdrop"></div>
      <div class="app-modal-box" role="dialog" aria-modal="true">
        <h2 class="app-modal-title"></h2>
        <p class="app-modal-message"></p>
        <div class="app-modal-actions"></div>
      </div>
    `;
    document.body.appendChild(modalEl);
    titleEl = modalEl.querySelector('.app-modal-title');
    messageEl = modalEl.querySelector('.app-modal-message');
    actionsEl = modalEl.querySelector('.app-modal-actions');
    modalEl.querySelector('.app-modal-backdrop').addEventListener('click', hideModal);
  }

  function hideModal() {
    if (modalEl) modalEl.classList.add('hidden');
    onConfirmCb = null;
  }

  function showModal({ title = 'تنبيه', message, okText = 'تمام', onOk }) {
    ensureModal();
    titleEl.textContent = title;
    messageEl.textContent = message;
    actionsEl.innerHTML = '';
    const btn = document.createElement('button');
    btn.className = 'btn btn-primary btn-big';
    btn.textContent = okText;
    btn.addEventListener('click', () => {
      hideModal();
      if (onOk) onOk();
    });
    actionsEl.appendChild(btn);
    modalEl.classList.remove('hidden');
  }

  function showConfirm({ title = 'متأكد؟', message, confirmText = 'أيوه', cancelText = 'لأ', onConfirm, onCancel }) {
    ensureModal();
    titleEl.textContent = title;
    messageEl.textContent = message;
    actionsEl.innerHTML = '';
    const cancelBtn = document.createElement('button');
    cancelBtn.className = 'btn btn-outline btn-big';
    cancelBtn.textContent = cancelText;
    cancelBtn.addEventListener('click', () => {
      hideModal();
      if (onCancel) onCancel();
    });
    const confirmBtn = document.createElement('button');
    confirmBtn.className = 'btn btn-primary btn-big';
    confirmBtn.textContent = confirmText;
    confirmBtn.addEventListener('click', () => {
      hideModal();
      if (onConfirm) onConfirm();
    });
    actionsEl.appendChild(cancelBtn);
    actionsEl.appendChild(confirmBtn);
    modalEl.classList.remove('hidden');
  }

  window.appAlert = (message, title) => new Promise((resolve) => {
    showModal({ title: title || 'تنبيه', message, onOk: resolve });
  });

  window.appConfirm = (message, title) => new Promise((resolve) => {
    showConfirm({
      title: title || 'متأكد؟',
      message,
      onConfirm: () => resolve(true),
      onCancel: () => resolve(false),
    });
  });
})();
