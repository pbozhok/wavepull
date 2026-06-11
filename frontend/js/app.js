'use strict';

const form         = document.getElementById('search-form');
const input        = document.getElementById('search-input');
const btn          = document.getElementById('search-btn');
const btnText      = btn.querySelector('.btn-text');
const btnLoading   = btn.querySelector('.btn-loading');
const errorEl      = document.getElementById('search-error');
const srcErrSec    = document.getElementById('source-errors');
const srcErrText   = document.getElementById('source-error-text');
const resultsSec   = document.getElementById('results-section');
const resultsList  = document.getElementById('results-list');
const resultsCount = document.getElementById('results-count');
const noResults    = document.getElementById('no-results');

// ── Search submission ─────────────────────────────────

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const query = input.value.trim();

  if (!query) {
    showError('Enter a song name, artist — title, or paste a URL.');
    return;
  }

  clearError();
  setLoading(true);
  await resetResults();

  try {
    const resp = await fetch('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    });

    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      showError(data.detail || `Search failed (${resp.status}).`);
      return;
    }

    const data = await resp.json();
    renderResults(data);
  } catch {
    showError('Network error — is the server running?');
  } finally {
    setLoading(false);
  }
});

// ── Render results ────────────────────────────────────

function renderResults(data) {
  if (data.source_errors && data.source_errors.length > 0) {
    srcErrText.textContent = '⚠ ' + data.source_errors.join(' · ');
    srcErrSec.hidden = false;
  }

  if (!data.results || data.results.length === 0) {
    noResults.hidden = false;
    return;
  }

  const count = data.results.length;
  resultsCount.textContent = `${count} result${count !== 1 ? 's' : ''}`;
  // T012 — pass stagger index; cap at 9 so last card's delay stays ≤ 540ms
  data.results.forEach((r, i) => resultsList.appendChild(buildCard(r, i)));
  resultsSec.hidden = false;
}

// T012 — accept index, set --i CSS custom property for stagger animation
function buildCard(result, index) {
  const li = document.createElement('li');
  li.className = 'result-card';
  li.style.setProperty('--i', Math.min(index, 9));

  const thumb = result.thumbnail_url
    ? `<img class="result-thumb" src="${esc(result.thumbnail_url)}" alt="" loading="lazy">`
    : `<div class="result-thumb-placeholder" aria-hidden="true">♪</div>`;

  const duration = result.duration_seconds
    ? `<span class="result-duration">${fmt(result.duration_seconds)}</span>`
    : '';

  li.innerHTML = `
    <a
      class="result-card-link"
      href="${esc(result.source_page_url)}"
      target="_blank"
      rel="noopener noreferrer"
      title="Open on ${esc(result.source)}"
    >
      ${thumb}
      <div class="result-meta">
        <div class="result-title">${esc(result.title)}</div>
        <div class="result-artist">${esc(result.artist)}</div>
        <div class="result-footer">
          <span class="source-badge source-${esc(result.source)}">${esc(result.source.toUpperCase())}</span>
          ${duration}
        </div>
      </div>
    </a>
    <button
      class="download-btn"
      aria-label="Download ${esc(result.title)}"
      data-url="${esc(result.source_page_url)}"
    >DL</button>
  `;

  li.querySelector('.download-btn').addEventListener('click', (e) => {
    e.stopPropagation();
    triggerDownload(result.source_page_url, e.currentTarget);
  });

  const imgEl = li.querySelector('.result-thumb');
  if (imgEl) {
    imgEl.addEventListener('error', function () {
      const placeholder = document.createElement('div');
      placeholder.className = 'result-thumb-placeholder';
      placeholder.setAttribute('aria-hidden', 'true');
      placeholder.textContent = '♪';
      this.replaceWith(placeholder);
    });
  }

  return li;
}

// ── Download ──────────────────────────────────────────

function triggerDownload(url, btn) {
  const card = btn.closest('.result-card');
  const orig = btn.textContent;
  btn.disabled = true;
  btn.textContent = '…';

  // T015 — ripple feedback on the card; remove after animation ends
  if (card) {
    card.classList.add('downloading');
    card.addEventListener('animationend', () => {
      card.classList.remove('downloading');
    }, { once: true });
  }

  const a = document.createElement('a');
  a.href = `/api/download?url=${encodeURIComponent(url)}`;
  a.style.display = 'none';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);

  setTimeout(() => {
    btn.disabled = false;
    btn.textContent = orig;
  }, 2500);
}

// ── Helpers ───────────────────────────────────────────

function setLoading(on) {
  btn.disabled = on;
  btnText.hidden = on;
  btnLoading.hidden = !on;
}

function showError(msg) {
  errorEl.textContent = msg;
  errorEl.hidden = false;
}

function clearError() {
  errorEl.textContent = '';
  errorEl.hidden = true;
}

// T011 — fade out existing results before clearing; resolves immediately if
// there are no results to animate out
async function resetResults() {
  if (!resultsSec.hidden && resultsList.children.length > 0) {
    resultsList.classList.add('results-exiting');
    await new Promise(r => setTimeout(r, 175));
    resultsList.classList.remove('results-exiting');
  }
  resultsSec.hidden = true;
  noResults.hidden = true;
  srcErrSec.hidden = true;
  srcErrText.textContent = '';
  resultsList.innerHTML = '';
}

function fmt(secs) {
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
}

function esc(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
