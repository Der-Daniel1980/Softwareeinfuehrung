/* SysIntro – app.js */
(function () {
  'use strict';

  // ─── CSRF Setup ────────────────────────────────────────────────────────────
  function getCsrfToken() {
    // Read from meta tag (set server-side from cookie in base.html)
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : '';
  }

  // Configure HTMX to send CSRF token on all non-GET requests
  document.addEventListener('htmx:configRequest', function (evt) {
    const method = (evt.detail.verb || 'GET').toUpperCase();
    if (method !== 'GET') {
      evt.detail.headers['X-CSRF-Token'] = getCsrfToken();
    }
  });

  // ─── HTMX Error Handler ────────────────────────────────────────────────────
  document.addEventListener('htmx:responseError', function (evt) {
    const status = evt.detail.xhr.status;
    const text = evt.detail.xhr.responseText || '';
    let msg = `Fehler ${status}`;
    try {
      const json = JSON.parse(text);
      if (json.detail) msg = json.detail;
    } catch (_) {}
    showFlash('error', msg);
  });

  // ─── Flash Message Helper ──────────────────────────────────────────────────
  function showFlash(type, message) {
    const container = document.getElementById('flash-container');
    if (!container) return;

    const colorMap = {
      success: 'bg-green-50 border-green-400 text-green-800',
      error: 'bg-red-50 border-red-400 text-red-800',
      warning: 'bg-amber-50 border-amber-400 text-amber-800',
      info: 'bg-blue-50 border-blue-400 text-blue-800',
    };
    const colors = colorMap[type] || colorMap.info;

    const div = document.createElement('div');
    div.className = `border-l-4 p-4 rounded mb-2 ${colors} flex justify-between items-start`;
    div.innerHTML = `
      <span>${escapeHtml(message)}</span>
      <button type="button" onclick="this.parentElement.remove()" class="ml-4 text-lg leading-none opacity-60 hover:opacity-100">&times;</button>
    `;
    container.appendChild(div);

    // Auto-remove after 6 seconds
    setTimeout(() => div.remove(), 6000);
  }

  window.showFlash = showFlash;

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // ─── Autosave Indicator ────────────────────────────────────────────────────
  // Called by HTMX events on field inputs
  window.autosaveIndicator = {
    timers: {},
    show: function (fieldKey, state) {
      const el = document.getElementById('autosave-' + fieldKey.replace(/\./g, '_'));
      if (!el) return;
      el.classList.remove('saving', 'saved', 'error', 'fade-out');
      el.classList.add(state);
      if (state === 'saving') {
        el.textContent = '…';
      } else if (state === 'saved') {
        el.textContent = '✓ Gespeichert';
        clearTimeout(this.timers[fieldKey]);
        this.timers[fieldKey] = setTimeout(() => {
          el.classList.add('fade-out');
        }, 3000);
      } else if (state === 'error') {
        el.textContent = '✗ Fehler beim Speichern';
      }
    },
  };

  // HTMX before/after events for autosave
  document.addEventListener('htmx:beforeRequest', function (evt) {
    const el = evt.detail.elt;
    const fieldKey = el.dataset.fieldKey;
    if (fieldKey && el.closest('.autosave-field')) {
      window.autosaveIndicator.show(fieldKey, 'saving');
    }
  });

  document.addEventListener('htmx:afterRequest', function (evt) {
    const el = evt.detail.elt;
    const fieldKey = el.dataset.fieldKey;
    if (fieldKey && el.closest('.autosave-field')) {
      const success = evt.detail.successful;
      window.autosaveIndicator.show(fieldKey, success ? 'saved' : 'error');
    }
  });

  // ─── Conditional Field Toggler ─────────────────────────────────────────────
  // Watches a "parent" field and shows/hides dependent fields
  window.initConditionalFields = function () {
    document.querySelectorAll('[data-conditional-on]').forEach(function (depEl) {
      const parentKey = depEl.dataset.conditionalOn;
      const expectedVal = depEl.dataset.conditionalEquals;
      const safeKey = parentKey.replace(/\./g, '_');
      const parentEl = document.querySelector('[data-field-key="' + parentKey + '"]');

      function toggle(val) {
        const show = val === expectedVal;
        depEl.style.display = show ? '' : 'none';
        // Enable/disable inputs inside to avoid submitting hidden required fields
        depEl.querySelectorAll('input, textarea, select').forEach(function (inp) {
          inp.disabled = !show;
        });
      }

      if (parentEl) {
        // Determine current value
        let currentVal = '';
        if (parentEl.type === 'radio') {
          const checked = document.querySelector('[data-field-key="' + parentKey + '"]:checked');
          currentVal = checked ? checked.value : '';
        } else {
          currentVal = parentEl.value || '';
        }
        toggle(currentVal);

        // Listen for changes on all inputs with this field key
        document.querySelectorAll('[data-field-key="' + parentKey + '"]').forEach(function (inp) {
          inp.addEventListener('change', function () {
            let val = '';
            if (inp.type === 'radio') {
              const checked = document.querySelector('[data-field-key="' + parentKey + '"]:checked');
              val = checked ? checked.value : '';
            } else {
              val = inp.value;
            }
            toggle(val);
          });
          inp.addEventListener('input', function () {
            toggle(inp.value);
          });
        });
      } else {
        // Parent not found — keep hidden until parent is filled
        depEl.style.display = 'none';
      }
    });
  };

  // ─── Demo Login Fill ───────────────────────────────────────────────────────
  window.fillDemoLogin = function (email, password) {
    const emailInput = document.getElementById('email');
    const passInput = document.getElementById('password');
    if (emailInput) emailInput.value = email;
    if (passInput) passInput.value = password || 'demo1234';
  };

  // ─── Section sidebar active on scroll ─────────────────────────────────────
  function initSectionScroll() {
    const sections = document.querySelectorAll('section[id^="section-"]');
    const links = document.querySelectorAll('.section-link');
    if (!sections.length || !links.length) return;

    const observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            const id = entry.target.id;
            links.forEach(function (link) {
              link.classList.toggle('section-active', link.getAttribute('href') === '#' + id);
            });
          }
        });
      },
      { threshold: 0.2, rootMargin: '-80px 0px 0px 0px' }
    );

    sections.forEach(function (s) {
      observer.observe(s);
    });
  }

  // ─── Pflichtfeld counter ────────────────────────────────────────────────────
  window.updateRequiredCounter = function () {
    const counter = document.getElementById('required-counter');
    if (!counter) return;
    let total = 0;
    let filled = 0;
    document.querySelectorAll('.required-field').forEach(function (wrapper) {
      total++;
      const inp = wrapper.querySelector('input:not([type=radio]):not([type=checkbox]), textarea, select');
      const radio = wrapper.querySelector('input[type=radio]:checked');
      const checkbox = wrapper.querySelectorAll('input[type=checkbox]:checked');
      if (radio) {
        filled++;
      } else if (checkbox.length > 0) {
        filled++;
      } else if (inp && inp.value && inp.value.trim() !== '') {
        filled++;
      }
    });
    const open = total - filled;
    counter.textContent = `Noch ${open} von ${total} Pflichtfeldern offen`;
    counter.className = open > 0
      ? 'text-sm font-medium text-amber-700 bg-amber-50 px-3 py-1 rounded'
      : 'text-sm font-medium text-green-700 bg-green-50 px-3 py-1 rounded';

    // Update submit button
    const submitBtn = document.getElementById('submit-btn');
    if (submitBtn) {
      submitBtn.disabled = open > 0;
      submitBtn.title = open > 0 ? `Noch ${open} Pflichtfeld(er) ausfüllen` : '';
    }
  };

  // ─── Section checkmarks ─────────────────────────────────────────────────────
  window.updateSectionCheckmarks = function () {
    document.querySelectorAll('section[id^="section-"]').forEach(function (section) {
      const sectionName = section.id.replace('section-', '');
      const checkmark = document.getElementById('check-' + sectionName);
      if (!checkmark) return;
      const required = section.querySelectorAll('.required-field');
      if (required.length === 0) {
        checkmark.textContent = '✓';
        checkmark.className = 'text-green-500 ml-1';
        return;
      }
      let allFilled = true;
      required.forEach(function (wrapper) {
        const inp = wrapper.querySelector('input:not([type=radio]):not([type=checkbox]), textarea, select');
        const radio = wrapper.querySelector('input[type=radio]:checked');
        const checkbox = wrapper.querySelectorAll('input[type=checkbox]:checked');
        if (!radio && checkbox.length === 0 && (!inp || !inp.value || inp.value.trim() === '')) {
          allFilled = false;
        }
      });
      checkmark.textContent = allFilled ? '✓' : '';
      checkmark.className = allFilled ? 'text-green-500 ml-1' : 'text-gray-300 ml-1';
    });
  };

  // Init on load
  document.addEventListener('DOMContentLoaded', function () {
    initSectionScroll();
    if (typeof window.initConditionalFields === 'function') {
      window.initConditionalFields();
    }
    // Initial counter if on edit page
    if (document.getElementById('required-counter')) {
      window.updateRequiredCounter();
      window.updateSectionCheckmarks();

      // Watch all field inputs for counter updates
      document.querySelectorAll('.autosave-field input, .autosave-field textarea, .autosave-field select').forEach(function (inp) {
        inp.addEventListener('change', function () {
          window.updateRequiredCounter();
          window.updateSectionCheckmarks();
        });
        inp.addEventListener('input', function () {
          window.updateRequiredCounter();
          window.updateSectionCheckmarks();
        });
      });
    }
  });

  // ─── Search filter helper for catalog/tables ──────────────────────────────
  window.filterTable = function (inputId, tableId) {
    const input = document.getElementById(inputId);
    const table = document.getElementById(tableId);
    if (!input || !table) return;
    const rows = table.querySelectorAll('tbody tr');
    const val = input.value.toLowerCase();
    rows.forEach(function (row) {
      row.style.display = row.textContent.toLowerCase().includes(val) ? '' : 'none';
    });
  };

})();
