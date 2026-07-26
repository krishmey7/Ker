/**
 * Paiement KibaWallet — Mobile Money USSD (RDC).
 */
function kerKibaPay(planType, amountLabel) {
  const mobile = document.getElementById('kiba-mobile')?.value?.trim();
  if (!mobile) {
    alert('Indiquez votre numéro Mobile Money (+243…)');
    return;
  }

  const statusEl = document.getElementById('kiba-status');
  if (statusEl) {
    statusEl.textContent = 'Envoi de la demande de paiement…';
    statusEl.classList.remove('hidden');
    statusEl.style.display = 'block';
  }

  const csrf = document.querySelector('[name=csrfmiddlewaretoken]')?.value
    || document.cookie.match(/csrftoken=([^;]+)/)?.[1];

  fetch('/payments/api/kiba/create/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrf || '',
    },
    body: JSON.stringify({ plan_type: planType, mobile_number: mobile }),
  })
    .then((r) => r.json().then((d) => ({ ok: r.ok, d })))
    .then(({ ok, d }) => {
      if (!ok) throw new Error(d.error || 'Paiement impossible');
      if (statusEl) statusEl.textContent = d.message || 'Validez l\'USSD sur votre téléphone.';
      kerKibaPoll(d.transaction_id, statusEl);
    })
    .catch((err) => {
      if (statusEl) statusEl.textContent = err.message;
      else alert(err.message);
    });
}

function kerKibaPoll(transactionId, statusEl) {
  let attempts = 0;
  const maxAttempts = 12;

  const tick = () => {
    attempts += 1;
    fetch(`/payments/api/kiba/status/${transactionId}/`, { credentials: 'same-origin' })
      .then((r) => r.json())
      .then((d) => {
        if (d.status === 'COMPLETED' || d.status === 'SUCCEEDED') {
          if (statusEl) statusEl.textContent = d.message || 'Paiement confirmé ❤️';
          setTimeout(() => { window.location.href = '/game/play/'; }, 1200);
          return;
        }
        if (d.status === 'FAILED') {
          if (statusEl) statusEl.textContent = d.message || 'Paiement refusé.';
          return;
        }
        if (attempts < maxAttempts) {
          setTimeout(tick, 15000);
        } else if (statusEl) {
          statusEl.textContent = 'Toujours en attente — vérifiez l\'USSD ou réessayez.';
        }
      })
      .catch(() => {
        if (attempts < maxAttempts) setTimeout(tick, 15000);
      });
  };

  setTimeout(tick, 15000);
}
