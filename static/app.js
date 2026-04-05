// Tab navigation
function switchTab(name, btn) {
  document.querySelectorAll('.tab-content').forEach(el => {
    el.classList.add('hidden');
    el.classList.remove('active');
  });
  document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));
  const tab = document.getElementById('tab-' + name);
  tab.classList.remove('hidden');
  tab.classList.add('active');
  if (btn) btn.classList.add('active');
  if (name === 'labs') loadLabsHistory();
  if (name === 'profile') loadProfile();
}

// --- Dashboard ---

function fmt(val, decimals = 0) {
  if (val === null || val === undefined) return '--';
  const n = parseFloat(val);
  if (isNaN(n)) return '--';
  return decimals === 0 ? Math.round(n).toLocaleString() : n.toFixed(decimals);
}

function fmtHM(hm) {
  if (!hm) return '--';
  return `${hm.hours}h ${hm.minutes}m`;
}

function recoveryColor(score) {
  if (score >= 67) return 'green';
  if (score >= 34) return 'yellow';
  return 'red';
}

function set(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

// --- Offline support ---

function updateOnlineStatus() {
  const banner = document.getElementById('offline-banner');
  if (!banner) return;
  if (navigator.onLine) {
    banner.classList.add('hidden');
  } else {
    banner.classList.remove('hidden');
  }
}

window.addEventListener('online', () => { updateOnlineStatus(); loadDates(); });
window.addEventListener('offline', updateOnlineStatus);

// --- Morning Brief ---

function loadBrief(refresh = false) {
  const card = document.getElementById('brief-card');
  const text = document.getElementById('brief-text');
  if (!card || !text) return;

  if (refresh) {
    text.textContent = 'Regenerating...';
    card.classList.remove('hidden');
  }

  fetch(refresh ? '/api/brief?refresh=1' : '/api/brief')
    .then(r => r.json())
    .then(data => {
      if (data.error) { card.classList.add('hidden'); return; }
      text.textContent = data.brief;
      card.classList.remove('hidden');
    })
    .catch(() => card.classList.add('hidden'));
}

// --- Trends & Charts ---

let trendDays = 14;
const activeCharts = {};

function switchTrends(days, btn) {
  trendDays = days;
  document.querySelectorAll('.trend-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  loadTrends(days);
}

function loadTrends(days) {
  days = days || trendDays;
  document.getElementById('trends-loading').classList.remove('hidden');
  document.getElementById('trends-charts').classList.add('hidden');

  fetch(`/api/history?days=${days}`)
    .then(r => r.json())
    .then(data => renderCharts(data))
    .catch(() => {
      document.getElementById('trends-loading').textContent = 'Trends unavailable offline.';
    });
}

function fmtDateLabel(dateStr) {
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function makeChart(id, type, labels, values, color, unit, extra) {
  if (activeCharts[id]) { activeCharts[id].destroy(); }
  const ctx = document.getElementById(id);
  if (!ctx) return;

  const isBar = type === 'bar';
  activeCharts[id] = new Chart(ctx, {
    type,
    data: {
      labels,
      datasets: [{
        data: values,
        borderColor: color,
        backgroundColor: isBar ? color + '99' : color + '18',
        fill: !isBar,
        tension: 0.35,
        pointRadius: isBar ? 0 : 3,
        pointHoverRadius: isBar ? 0 : 6,
        pointBackgroundColor: extra?.pointColors || color,
        borderWidth: isBar ? 0 : 2,
        borderRadius: isBar ? 4 : 0,
        spanGaps: true,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: { label: c => `${c.raw ?? '—'} ${unit}` }
        }
      },
      scales: {
        x: {
          grid: { color: '#1e1e1e' },
          ticks: { color: '#555', font: { size: 10 }, maxRotation: 0, maxTicksLimit: 7 }
        },
        y: {
          grid: { color: '#1e1e1e' },
          ticks: { color: '#555', font: { size: 10 } },
          beginAtZero: isBar,
        }
      }
    }
  });
}

function renderCharts(data) {
  document.getElementById('trends-loading').classList.add('hidden');
  document.getElementById('trends-charts').classList.remove('hidden');

  const labels = data.map(d => fmtDateLabel(d.date));

  // Recovery — line with green/yellow/red points
  makeChart('chart-recovery', 'line', labels,
    data.map(d => d.recovery_score ?? null),
    '#3b82f6', '%', {
      pointColors: data.map(d => {
        const s = d.recovery_score;
        if (!s) return '#555';
        return s >= 67 ? '#22c55e' : s >= 34 ? '#eab308' : '#ef4444';
      })
    }
  );

  // HRV
  makeChart('chart-hrv', 'line', labels,
    data.map(d => d.hrv ? +d.hrv.toFixed(1) : null),
    '#a855f7', 'ms'
  );

  // Sleep hours — bar
  makeChart('chart-sleep', 'bar', labels,
    data.map(d => d.sleep_hours ?? null),
    '#6366f1', 'hrs'
  );

  // RHR
  makeChart('chart-rhr', 'line', labels,
    data.map(d => d.rhr ?? null),
    '#ef4444', 'bpm'
  );

  // Steps — bar
  makeChart('chart-steps', 'bar', labels,
    data.map(d => d.steps ?? null),
    '#22c55e', 'steps'
  );
}

// --- Date pagination ---

let availableDates = [];
let currentDateIndex = 0;

function loadDates() {
  fetch('/api/dates')
    .then(r => r.json())
    .then(dates => {
      availableDates = dates;
      currentDateIndex = 0;
      updateDateNav();
      loadDashboard(dates.length > 0 ? dates[0] : null);
    })
    .catch(() => loadDashboard(null));
}

function updateDateNav() {
  const prev = document.getElementById('date-prev');
  const next = document.getElementById('date-next');
  if (prev) prev.disabled = currentDateIndex >= availableDates.length - 1;
  if (next) next.disabled = currentDateIndex <= 0;
}

function changeDate(delta) {
  const newIndex = currentDateIndex + delta;
  if (newIndex < 0 || newIndex >= availableDates.length) return;
  currentDateIndex = newIndex;
  updateDateNav();
  loadDashboard(availableDates[currentDateIndex]);
}

function loadDashboard(date) {
  const url = date ? `/api/summary?date=${encodeURIComponent(date)}` : '/api/summary';

  document.getElementById('dashboard-loading').classList.remove('hidden');
  document.getElementById('dashboard-content').classList.add('hidden');
  document.getElementById('dashboard-error').classList.add('hidden');

  fetch(url)
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        document.getElementById('dashboard-loading').classList.add('hidden');
        const err = document.getElementById('dashboard-error');
        err.textContent = data.error;
        err.classList.remove('hidden');
        return;
      }
      renderDashboard(data);
    })
    .catch(() => {
      document.getElementById('dashboard-loading').classList.add('hidden');
      const err = document.getElementById('dashboard-error');
      err.textContent = 'Failed to load data. Is the server running?';
      err.classList.remove('hidden');
    });
}

function renderDashboard(data) {
  document.getElementById('dashboard-loading').classList.add('hidden');
  document.getElementById('dashboard-content').classList.remove('hidden');
  loadBrief();
  loadTrends();

  // Date
  if (data.date) {
    document.getElementById('header-date').textContent = data.date;
  }

  // Recovery
  if (data.recovery) {
    const r = data.recovery;
    const score = Math.round(r.recovery_score);
    const scoreEl = document.getElementById('d-recovery-score');
    scoreEl.textContent = score;
    scoreEl.className = 'recovery-score ' + recoveryColor(score);
    set('d-hrv', fmt(r.hrv_rmssd_milli, 1));
    set('d-rhr', fmt(r.resting_heart_rate));
    set('d-spo2', fmt(r.spo2_percentage, 1));
    set('d-temp', fmt(r.skin_temp_celsius, 1));
  }

  // Sleep
  if (data.sleep) {
    const s = data.sleep;
    set('d-sleep-duration', fmtHM(s.total_sleep_duration));
    document.getElementById('d-sleep-perf').textContent = fmt(s.sleep_performance_percentage) + '% perf';
    document.getElementById('d-sleep-eff').textContent = fmt(s.sleep_efficiency_percentage, 1) + '% eff';
    set('d-rem', fmtHM(s.total_rem_sleep));
    set('d-deep', fmtHM(s.total_deep_sleep));
    set('d-light', fmtHM(s.total_light_sleep));
    set('d-disturbances', fmt(s.disturbance_count));
    set('d-resp', fmt(s.respiratory_rate, 1));
  }

  // Strain
  if (data.strain) {
    const st = data.strain;
    set('d-strain', fmt(st.strain_score, 1));
    set('d-strain-calories', fmt(st.calories_burned) + ' kcal');
    set('d-avg-hr', fmt(st.average_heart_rate));
    set('d-max-hr', fmt(st.max_heart_rate));
  }

  // Activity
  if (data.activity) {
    const a = data.activity;
    set('d-steps', fmt(a.steps));
    set('d-distance', fmt(a.distance_miles, 2));
    set('d-active-cal', fmt(a.active_energy_kcal));
    set('d-exercise', fmt(a.exercise_minutes));
    set('d-stand', fmt(a.stand_hours));
  }

  // Nutrition
  if (data.nutrition) {
    const n = data.nutrition;
    const calIn = n.calories?.value;
    set('d-cal-in', calIn !== null && calIn !== undefined ? fmt(calIn) : '--');
    set('d-carbs', n.carbohydrates?.value !== null ? fmt(n.carbohydrates?.value, 1) : '--');
    set('d-protein', n.protein?.value !== null ? fmt(n.protein?.value, 1) : '--');
    set('d-fat', n.total_fat?.value !== null ? fmt(n.total_fat?.value, 1) : '--');
  }

  // Net calories
  if (data.derived && data.derived.net_calories_estimated !== null) {
    const net = data.derived.net_calories_estimated;
    const netEl = document.getElementById('d-net-cal');
    netEl.textContent = (net > 0 ? '+' : '') + fmt(net);
    netEl.classList.toggle('negative', net > 0); // positive net = ate more than burned
  }
}

// --- Labs ---

let selectedLabFile = null;

function handleFileSelect(e) {
  selectedLabFile = e.target.files[0];
  if (!selectedLabFile) return;
  document.getElementById('upload-filename').textContent = selectedLabFile.name;
  document.getElementById('upload-area').classList.add('has-file');
  document.getElementById('process-btn').classList.remove('hidden');
  document.getElementById('labs-upload-error').classList.add('hidden');
}

function processLabs() {
  if (!selectedLabFile) return;
  document.getElementById('process-btn').classList.add('hidden');
  document.getElementById('labs-processing').classList.remove('hidden');
  document.getElementById('labs-upload-error').classList.add('hidden');

  const form = new FormData();
  form.append('pdf', selectedLabFile);

  fetch('/api/labs/upload', { method: 'POST', body: form })
    .then(r => r.json())
    .then(data => {
      document.getElementById('labs-processing').classList.add('hidden');
      if (data.error) {
        const err = document.getElementById('labs-upload-error');
        err.textContent = data.error;
        err.classList.remove('hidden');
        document.getElementById('process-btn').classList.remove('hidden');
        return;
      }
      // Reset upload UI
      selectedLabFile = null;
      document.getElementById('lab-file-input').value = '';
      document.getElementById('upload-filename').textContent = '';
      document.getElementById('upload-area').classList.remove('has-file');
      // Render and refresh history
      renderLabResult(data);
      loadLabsHistory();
    })
    .catch(() => {
      document.getElementById('labs-processing').classList.add('hidden');
      const err = document.getElementById('labs-upload-error');
      err.textContent = 'Upload failed. Is the server running?';
      err.classList.remove('hidden');
      document.getElementById('process-btn').classList.remove('hidden');
    });
}

function loadLabsHistory() {
  fetch('/api/labs')
    .then(r => r.json())
    .then(list => {
      const row = document.getElementById('labs-history-row');
      const sel = document.getElementById('labs-date-select');
      if (!list.length) { row.classList.add('hidden'); return; }
      row.classList.remove('hidden');
      sel.innerHTML = list.map(l =>
        `<option value="${l.date}">${l.date} (${l.count} markers)</option>`
      ).join('');
      // Load most recent if results not already showing
      if (!document.getElementById('labs-results').hasChildNodes()) {
        loadLabResult(list[0].date);
      }
    });
}

function loadLabResult(date) {
  fetch(`/api/labs/${date}`)
    .then(r => r.json())
    .then(data => renderLabResult(data));
}

function renderLabResult(data) {
  const container = document.getElementById('labs-results');
  container.innerHTML = '';

  const biomarkers = data.biomarkers || [];
  if (!biomarkers.length) {
    container.innerHTML = '<p class="labs-empty">No biomarkers found.</p>';
    return;
  }

  // Group by category
  const groups = {};
  biomarkers.forEach(b => {
    const cat = b.category || 'Other';
    if (!groups[cat]) groups[cat] = [];
    groups[cat].push(b);
  });

  Object.entries(groups).forEach(([category, markers]) => {
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `<div class="card-header">${category}</div>`;

    const table = document.createElement('div');
    table.className = 'labs-table';
    markers.forEach(b => {
      const row = document.createElement('div');
      row.className = `labs-row status-${(b.status || 'normal').toLowerCase()}`;
      row.innerHTML = `
        <span class="labs-name">${b.name}</span>
        <span class="labs-value">${b.value ?? '—'} <span class="labs-unit">${b.unit || ''}</span></span>
        <span class="labs-range">${b.reference_range || ''}</span>
        <span class="labs-status">${b.status || ''}</span>
      `;
      table.appendChild(row);
    });
    card.appendChild(table);
    container.appendChild(card);
  });
}

// --- Sync ---

let syncing = false;

function startSync() {
  if (syncing) return;
  syncing = true;

  const btn = document.getElementById('sync-btn');
  const btnText = document.getElementById('sync-btn-text');
  const log = document.getElementById('sync-log');

  btn.className = 'sync-button syncing';
  btnText.textContent = 'Syncing...';
  log.innerHTML = '';
  log.classList.remove('hidden');

  const es = new EventSource('/api/sync');

  es.onmessage = function (e) {
    const msg = JSON.parse(e.data);
    if (msg === '__DONE__') {
      es.close();
      syncing = false;
      btn.className = 'sync-button done';
      btnText.textContent = 'Done ✓';
      const line = document.createElement('div');
      line.className = 'log-line done';
      line.textContent = '✓ Sync complete';
      log.appendChild(line);
      log.scrollTop = log.scrollHeight;
      loadDashboard();
      setTimeout(() => {
        btn.className = 'sync-button';
        btnText.textContent = 'Sync Now';
      }, 3000);
      return;
    }
    if (msg.trim() === '') return;
    const line = document.createElement('div');
    line.className = 'log-line';
    line.textContent = msg;
    log.appendChild(line);
    log.scrollTop = log.scrollHeight;
  };

  es.onerror = function () {
    es.close();
    syncing = false;
    btn.className = 'sync-button error';
    btnText.textContent = 'Error';
    const line = document.createElement('div');
    line.className = 'log-line error';
    line.textContent = '✗ Sync failed';
    log.appendChild(line);
    setTimeout(() => {
      btn.className = 'sync-button';
      btnText.textContent = 'Sync Now';
    }, 3000);
  };
}

// --- Chat ---

let chatHistory = [];
let chatStreaming = false;
let chatAbortController = null;

function handleChatKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    handleSendBtn();
  }
}

function handleSendBtn() {
  if (chatStreaming) {
    stopChat();
  } else {
    sendMessage();
  }
}

function stopChat() {
  if (chatAbortController) chatAbortController.abort();
}

function appendMessage(role, text, streaming = false) {
  const welcome = document.querySelector('.chat-welcome');
  if (welcome) welcome.remove();

  const msgs = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'message ' + role;
  if (streaming) div.classList.add('streaming');
  div.textContent = text;
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
  return div;
}

function setChatSendBtn(mode) {
  const btn = document.getElementById('chat-send');
  if (mode === 'stop') {
    btn.textContent = '■';
    btn.classList.add('stop');
    btn.disabled = false;
  } else {
    btn.textContent = '↑';
    btn.classList.remove('stop');
    btn.disabled = false;
  }
}

function sendMessage() {
  if (chatStreaming) return;
  const input = document.getElementById('chat-input');
  const text = input.value.trim();
  if (!text) return;

  input.value = '';
  input.style.height = 'auto';

  chatHistory.push({ role: 'user', content: text });
  appendMessage('user', text);

  chatStreaming = true;
  setChatSendBtn('stop');

  const assistantEl = appendMessage('assistant', '', true);
  let buffer = '';

  chatAbortController = new AbortController();

  fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages: chatHistory }),
    signal: chatAbortController.signal,
  }).then(res => {
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let partial = '';

    function read() {
      reader.read().then(({ done, value }) => {
        if (done) return;
        partial += decoder.decode(value, { stream: true });
        const lines = partial.split('\n');
        partial = lines.pop();
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const msg = JSON.parse(line.slice(6));
            if (msg === '__DONE__') {
              assistantEl.classList.remove('streaming');
              chatHistory.push({ role: 'assistant', content: buffer });
              chatStreaming = false;
              chatAbortController = null;
              setChatSendBtn('send');
              return;
            }
            buffer += msg;
            assistantEl.textContent = buffer;
            document.getElementById('chat-messages').scrollTop = 99999;
          } catch {}
        }
        read();
      }).catch(err => {
        if (err.name === 'AbortError') {
          assistantEl.classList.remove('streaming');
          if (buffer) chatHistory.push({ role: 'assistant', content: buffer });
        }
        chatStreaming = false;
        chatAbortController = null;
        setChatSendBtn('send');
      });
    }
    read();
  }).catch(err => {
    if (err.name !== 'AbortError') {
      assistantEl.textContent = 'Error connecting to server.';
    }
    assistantEl.classList.remove('streaming');
    chatStreaming = false;
    chatAbortController = null;
    setChatSendBtn('send');
  });
}

// --- Profile ---

const PROFILE_FIELDS = ['name','age','sex','height','weight','goals','conditions','medications','supplements','notes'];

function loadProfile() {
  fetch('/api/profile')
    .then(r => r.json())
    .then(data => {
      PROFILE_FIELDS.forEach(key => {
        const el = document.getElementById('p-' + key);
        if (el && data[key] != null) el.value = data[key];
      });
    });
}

function saveProfile() {
  const data = {};
  PROFILE_FIELDS.forEach(key => {
    const el = document.getElementById('p-' + key);
    if (el) data[key] = el.value.trim();
  });

  const btn = document.getElementById('profile-save-btn');
  const saved = document.getElementById('profile-saved');
  btn.disabled = true;

  fetch('/api/profile', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
    .then(r => r.json())
    .then(() => {
      saved.classList.remove('hidden');
      setTimeout(() => { saved.classList.add('hidden'); btn.disabled = false; }, 2000);
    })
    .catch(() => { btn.disabled = false; });
}

// --- Tooltips (click-based ⓘ icons)
(function () {
  const tip = document.createElement('div');
  tip.className = 'tooltip';

  let activeBtn = null;

  function position(btn) {
    const r = btn.getBoundingClientRect();
    const margin = 8;
    tip.style.width = '260px';
    const th = tip.offsetHeight || 70;
    let left = r.left + r.width / 2 - 130;
    let top = r.top - th - margin;
    if (top < margin) top = r.bottom + margin;
    left = Math.max(margin, Math.min(left, window.innerWidth - 260 - margin));
    tip.style.left = left + 'px';
    tip.style.top = top + 'px';
  }

  function showTip(text, btn) {
    tip.textContent = text;
    tip.classList.add('visible');
    activeBtn = btn;
    // defer position so offsetHeight is accurate
    requestAnimationFrame(() => position(btn));
  }

  function hideTip() {
    tip.classList.remove('visible');
    activeBtn = null;
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('app').appendChild(tip);

    // Inject ⓘ button into every [data-tooltip] element
    document.querySelectorAll('[data-tooltip]').forEach(el => {
      const btn = document.createElement('button');
      btn.className = 'info-btn';
      btn.setAttribute('aria-label', 'More info');
      btn.textContent = 'ⓘ';
      el.appendChild(btn);
    });
  });

  document.addEventListener('click', e => {
    const btn = e.target.closest('.info-btn');
    if (btn) {
      e.stopPropagation();
      if (btn === activeBtn) {
        hideTip();
      } else {
        const text = btn.closest('[data-tooltip]').dataset.tooltip;
        showTip(text, btn);
      }
      return;
    }
    hideTip();
  });
})();

// Auto-resize textarea + init
document.addEventListener('DOMContentLoaded', () => {
  updateOnlineStatus();

  const textarea = document.getElementById('chat-input');
  if (textarea) {
    textarea.addEventListener('input', function () {
      this.style.height = 'auto';
      this.style.height = Math.min(this.scrollHeight, 120) + 'px';
    });
  }
  loadDates();
});
