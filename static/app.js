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

function loadDashboard() {
  fetch('/api/summary')
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

function handleChatKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
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

function sendMessage() {
  if (chatStreaming) return;
  const input = document.getElementById('chat-input');
  const text = input.value.trim();
  if (!text) return;

  input.value = '';
  input.style.height = 'auto';
  document.getElementById('chat-send').disabled = true;

  chatHistory.push({ role: 'user', content: text });
  appendMessage('user', text);

  chatStreaming = true;
  const assistantEl = appendMessage('assistant', '', true);

  let buffer = '';

  const es = new EventSource('/api/chat?_t=' + Date.now());

  // We need POST not GET for SSE — use fetch + ReadableStream instead
  es.close();

  fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages: chatHistory }),
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
              document.getElementById('chat-send').disabled = false;
              return;
            }
            buffer += msg;
            assistantEl.textContent = buffer;
            document.getElementById('chat-messages').scrollTop = 99999;
          } catch {}
        }
        read();
      });
    }
    read();
  }).catch(() => {
    assistantEl.textContent = 'Error connecting to server.';
    assistantEl.classList.remove('streaming');
    chatStreaming = false;
    document.getElementById('chat-send').disabled = false;
  });
}

// Auto-resize textarea
document.addEventListener('DOMContentLoaded', () => {
  const textarea = document.getElementById('chat-input');
  if (textarea) {
    textarea.addEventListener('input', function () {
      this.style.height = 'auto';
      this.style.height = Math.min(this.scrollHeight, 120) + 'px';
    });
  }
  loadDashboard();
});
