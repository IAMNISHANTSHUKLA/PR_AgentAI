/**
 * PR AgentAI — Dashboard Frontend Logic
 */

const API_BASE = '';

// ── State ─────────────────────────────────────────────────────────────
let currentResult = null;
let activeFilter = 'all';

// ── DOM Ready ─────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  loadSamples();
  checkHealth();
});

// ── Health Check ──────────────────────────────────────────────────────
async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    const data = await res.json();
    const dot = document.getElementById('statusDot');
    const text = document.getElementById('statusText');
    
    if (data.api_key_set) {
      dot.style.background = 'var(--verdict-approve)';
      text.textContent = `${data.model_fast.split('-').slice(0, 3).join('-')} ready`;
    } else {
      dot.style.background = 'var(--severity-critical)';
      text.textContent = 'API key missing';
    }
  } catch (e) {
    console.error('Health check failed:', e);
  }
}

// ── Load Samples ──────────────────────────────────────────────────────
async function loadSamples() {
  try {
    const res = await fetch(`${API_BASE}/api/samples`);
    const data = await res.json();
    const container = document.getElementById('sampleButtons');
    
    data.samples.forEach(sample => {
      const btn = document.createElement('button');
      btn.className = 'btn btn-secondary';
      btn.textContent = `📄 ${sample.name}`;
      btn.onclick = () => loadSampleDiff(sample.filename);
      container.appendChild(btn);
    });
  } catch (e) {
    console.error('Failed to load samples:', e);
  }
}

// ── Load Sample Diff ──────────────────────────────────────────────────
async function loadSampleDiff(filename) {
  try {
    const res = await fetch(`${API_BASE}/api/samples/load`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sample: filename }),
    });
    const data = await res.json();
    document.getElementById('diffInput').value = data.diff;
  } catch (e) {
    console.error('Failed to load sample:', e);
  }
}

// ── Submit Review ─────────────────────────────────────────────────────
async function submitReview() {
  const diff = document.getElementById('diffInput').value.trim();
  const prId = document.getElementById('prIdInput').value.trim() || 'PR-001';

  if (!diff) {
    alert('Please paste a PR diff or load a sample first.');
    return;
  }

  // Show loading
  const overlay = document.getElementById('loadingOverlay');
  overlay.classList.add('active');
  document.getElementById('reviewBtn').disabled = true;

  // Animate LangGraph pipeline stages
  const stages = [
    '📥 Intake node — validating input...',
    '🔒 Security Agent node — deep analysis...',
    '📐 Quality Agent node — code review...',
    '📝 Documentation Agent node — checking docs...',
    '📊 Aggregate node — computing scores...',
    '🏛️ Verdict node — determining outcome...'
  ];
  let stageIdx = 0;
  const agentEl = document.getElementById('loadingAgent');
  const agentInterval = setInterval(() => {
    agentEl.textContent = stages[stageIdx % stages.length];
    stageIdx++;
  }, 2500);

  try {
    const res = await fetch(`${API_BASE}/api/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ diff, pr_id: prId }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Review failed');
    }

    currentResult = await res.json();
    renderResults(currentResult);
  } catch (e) {
    console.error('Review failed:', e);
    alert(`Review failed: ${e.message}`);
  } finally {
    clearInterval(agentInterval);
    overlay.classList.remove('active');
    document.getElementById('reviewBtn').disabled = false;
  }
}

// ── Render Results ────────────────────────────────────────────────────
function renderResults(data) {
  const panel = document.getElementById('resultsPanel');
  panel.classList.add('active');
  panel.scrollIntoView({ behavior: 'smooth', block: 'start' });

  renderGraph();
  renderVerdict(data);
  renderScores(data);
  renderFindings(data);
  renderTiming(data);
}

// ── LangGraph Pipeline Visualization ──────────────────────────────────
async function renderGraph() {
  try {
    const res = await fetch(`${API_BASE}/api/graph`);
    const data = await res.json();
    const container = document.getElementById('mermaidGraph');
    container.innerHTML = '';
    const { svg } = await mermaid.render('graphSvg', data.mermaid);
    container.innerHTML = svg;
  } catch (e) {
    console.error('Failed to render graph:', e);
    document.getElementById('graphCard').style.display = 'none';
  }
}

function toggleGraph() {
  const body = document.getElementById('graphBody');
  const btn = document.getElementById('graphToggle');
  if (body.style.display === 'none') {
    body.style.display = 'block';
    btn.textContent = 'Hide';
  } else {
    body.style.display = 'none';
    btn.textContent = 'Show';
  }
}

// ── Verdict Banner ────────────────────────────────────────────────────
function renderVerdict(data) {
  const container = document.getElementById('verdictBanner');
  const verdictIcons = {
    approve: '✅',
    comment: '⚠️',
    request_changes: '🚫',
  };
  const verdictLabels = {
    approve: 'Approved',
    comment: 'Needs Discussion',
    request_changes: 'Changes Required',
  };

  container.className = `verdict-banner ${data.verdict}`;
  container.innerHTML = `
    <div class="verdict-icon">${verdictIcons[data.verdict] || '🤖'}</div>
    <div class="verdict-content">
      <h2>${verdictLabels[data.verdict] || data.verdict}</h2>
      <p>Overall Score: <strong>${data.overall_score}/100</strong> &nbsp;·&nbsp; 
         ${data.total_findings} findings (${data.critical_findings} critical/high) &nbsp;·&nbsp;
         ${(data.duration_ms / 1000).toFixed(1)}s total</p>
    </div>
  `;
}

// ── Score Rings ───────────────────────────────────────────────────────
function renderScores(data) {
  const container = document.getElementById('scoreSection');
  
  // Overall score ring
  const circumference = 2 * Math.PI * 48;
  const offset = circumference - (data.overall_score / 100) * circumference;
  const scoreColor = data.overall_score >= 70 ? 'var(--verdict-approve)' 
    : data.overall_score >= 40 ? 'var(--verdict-comment)' 
    : 'var(--severity-critical)';

  // Agent score bars
  const agentBars = data.agents.map(agent => `
    <div class="agent-score-row">
      <div class="agent-score-label">${agent.agent}</div>
      <div class="agent-score-bar">
        <div class="agent-score-fill" style="width: ${agent.score}%"></div>
      </div>
      <div class="agent-score-value" style="color: ${
        agent.score >= 70 ? 'var(--verdict-approve)' : 
        agent.score >= 40 ? 'var(--verdict-comment)' : 'var(--severity-critical)'
      }">${agent.score}</div>
    </div>
  `).join('');

  container.innerHTML = `
    <div class="score-ring">
      <svg viewBox="0 0 120 120">
        <circle class="ring-bg" cx="60" cy="60" r="48"/>
        <circle class="ring-fill" cx="60" cy="60" r="48"
          stroke="${scoreColor}"
          stroke-dasharray="${circumference}"
          stroke-dashoffset="${offset}"/>
      </svg>
      <div class="score-text">
        <span class="score-value" style="color: ${scoreColor}">${data.overall_score}</span>
        <span class="score-label">Score</span>
      </div>
    </div>
    <div class="agent-scores">${agentBars}</div>
  `;
}

// ── Findings List ─────────────────────────────────────────────────────
function renderFindings(data) {
  // Flatten all findings across agents
  const allFindings = [];
  data.agents.forEach(agent => {
    (agent.findings || []).forEach(finding => {
      allFindings.push({ ...finding, agent: agent.agent });
    });
  });

  // Sort by severity
  const severityOrder = { critical: 0, high: 1, medium: 2, low: 3, info: 4 };
  allFindings.sort((a, b) => (severityOrder[a.severity] || 5) - (severityOrder[b.severity] || 5));

  // Count by severity
  const counts = {};
  allFindings.forEach(f => {
    counts[f.severity] = (counts[f.severity] || 0) + 1;
  });

  // Render filter chips
  const filterContainer = document.getElementById('severityFilters');
  const severities = ['all', 'critical', 'high', 'medium', 'low', 'info'];
  filterContainer.innerHTML = severities.map(s => {
    const count = s === 'all' ? allFindings.length : (counts[s] || 0);
    if (s !== 'all' && count === 0) return '';
    return `<button class="filter-chip ${activeFilter === s ? 'active' : ''}" 
              onclick="filterFindings('${s}')">${s} (${count})</button>`;
  }).join('');

  // Render findings
  const container = document.getElementById('findingsList');
  const filtered = activeFilter === 'all' ? allFindings 
    : allFindings.filter(f => f.severity === activeFilter);

  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">🎉</div>
        <h3>No Issues Found</h3>
        <p>This code looks clean! No findings match the current filter.</p>
      </div>`;
    return;
  }

  container.innerHTML = filtered.map(f => `
    <div class="finding-card ${f.severity}">
      <div class="finding-header">
        <span class="severity-badge ${f.severity}">${f.severity}</span>
        <span class="finding-agent-badge">🤖 ${f.agent}</span>
        <span class="finding-title">${escapeHtml(f.title)}</span>
        <span class="finding-file">${escapeHtml(f.file)}${f.line ? ':' + f.line : ''}</span>
      </div>
      <div class="finding-body">${escapeHtml(f.description)}</div>
      ${f.suggestion ? `
        <div class="finding-suggestion">
          <strong>💡 Suggestion:</strong> ${escapeHtml(f.suggestion)}
        </div>` : ''}
    </div>
  `).join('');

  document.getElementById('findingsCount').textContent = allFindings.length;
}

function filterFindings(severity) {
  activeFilter = severity;
  if (currentResult) renderFindings(currentResult);
}

// ── Timing Stats ──────────────────────────────────────────────────────
function renderTiming(data) {
  const container = document.getElementById('timingStats');
  const cards = [
    { value: `${(data.duration_ms / 1000).toFixed(1)}s`, label: 'Total Time' },
    ...data.agents.map(a => ({
      value: `${(a.duration_ms / 1000).toFixed(1)}s`,
      label: a.agent.charAt(0).toUpperCase() + a.agent.slice(1),
    })),
  ];

  container.innerHTML = cards.map(c => `
    <div class="timing-card">
      <div class="timing-value">${c.value}</div>
      <div class="timing-label">${c.label}</div>
    </div>
  `).join('');
}

// ── Utilities ─────────────────────────────────────────────────────────
function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function clearResults() {
  currentResult = null;
  activeFilter = 'all';
  document.getElementById('resultsPanel').classList.remove('active');
  document.getElementById('diffInput').value = '';
}

// ── Preload graph on page load ────────────────────────────────────────
async function preloadGraph() {
  try {
    const res = await fetch(`${API_BASE}/api/graph`);
    await res.json(); // just warm the cache
  } catch (e) { /* ignore */ }
}
preloadGraph();
