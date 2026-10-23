/**
 * MUJVERSE — Core Client-side Scripts
 * Provides CSRF helpers for fetch, alert auto-dismiss, and UI interactions.
 */

document.addEventListener("DOMContentLoaded", function () {
  // ── Auto-dismiss bootstrap alerts after 5 seconds ──
  const alerts = document.querySelectorAll(".alert-dismissible");
  alerts.forEach(function (alert) {
    setTimeout(function () {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) {
        bsAlert.close();
      }
    }, 5000);
  });
});

/**
 * Get cookie value by name (used for Django CSRF token).
 * @param {string} name
 * @returns {string|null}
 */
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === name + "=") {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

/**
 * Helper to make authenticated POST/PUT/DELETE fetch calls with Django CSRF.
 * @param {string} url
 * @param {object} data
 * @param {string} method
 * @returns {Promise<any>}
 */
async function fetchWithCsrf(url, data = {}, method = "POST") {
  const csrftoken = getCookie("csrftoken");
  const response = await fetch(url, {
    method: method,
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrftoken,
      "X-Requested-With": "XMLHttpRequest",
    },
    body: JSON.stringify(data),
  });
  return response.json();
}
