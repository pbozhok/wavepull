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

// ── Metadata modal elements ───────────────────────────

const metadataModal   = document.getElementById('metadata-modal');
const metadataForm    = document.getElementById('metadata-form');
const metaUrl         = document.getElementById('meta-url');
const metaTitle       = document.getElementById('meta-title');
const metaArtist      = document.getElementById('meta-artist');
const metaAlbum       = document.getElementById('meta-album');
const metaYear        = document.getElementById('meta-year');
const metaError       = document.getElementById('meta-error');
const metaDownloadBtn = document.getElementById('meta-download-btn');
const metaCancelBtn   = document.getElementById('meta-cancel-btn');

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
    >DL</button>
  `;

  li.querySelector('.download-btn').addEventListener('click', (e) => {
    e.stopPropagation();
    openMetadataModal(result, e.currentTarget);
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

// ── Metadata modal ────────────────────────────────────

function openMetadataModal(result, triggerEl) {
  metaUrl.value    = result.source_page_url;
  metaTitle.value  = result.title;
  metaArtist.value = result.artist;
  metaAlbum.value  = '';
  metaYear.value   = '';
  metaError.hidden = true;
  metaError.textContent = '';
  metadataModal.showModal();
  positionModal(triggerEl);
}

function positionModal(triggerEl) {
  if (!triggerEl || window.innerWidth < 600) {
    metadataModal.style.margin = '';
    metadataModal.style.top    = '';
    metadataModal.style.left   = '';
    return;
  }

  const tr = triggerEl.getBoundingClientRect();
  const mw = metadataModal.offsetWidth;
  const mh = metadataModal.offsetHeight;

  // Align right edge of modal with right edge of button; appear below
  let top  = tr.bottom + 6;
  let left = tr.right - mw;

  // Flip above if clipped at bottom
  if (top + mh > window.innerHeight - 8) top = tr.top - mh - 6;
  if (top < 8) top = 8;

  // Keep inside horizontal bounds
  if (left < 8) left = 8;
  if (left + mw > window.innerWidth - 8) left = window.innerWidth - mw - 8;

  metadataModal.style.margin = '0';
  metadataModal.style.top    = `${top}px`;
  metadataModal.style.left   = `${left}px`;
}

function closeMetadataModal() {
  metadataModal.close();
  metadataForm.reset();
}

metaCancelBtn.addEventListener('click', closeMetadataModal);

// Close only when both mousedown AND mouseup land on the backdrop.
// Without this, dragging text inside the panel and releasing outside fires
// a click on the dialog element and wrongly closes the modal.
let backdropMousedown = false;
metadataModal.addEventListener('mousedown', (e) => {
  backdropMousedown = e.target === metadataModal;
});
metadataModal.addEventListener('click', (e) => {
  if (e.target === metadataModal && backdropMousedown) closeMetadataModal();
});

// Reset form when dialog closes via Escape or any other path
metadataModal.addEventListener('close', () => {
  metadataForm.reset();
  metaError.hidden = true;
});

metadataForm.addEventListener('submit', (e) => {
  e.preventDefault();
  submitDownload();
});

async function submitDownload() {
  const url    = metaUrl.value;
  const title  = metaTitle.value.trim();
  const artist = metaArtist.value.trim();
  const album  = metaAlbum.value.trim();
  const year   = metaYear.value.trim();

  if (!title) {
    showMetaError('Title is required.');
    return;
  }
  if (year && !/^\d{4}$/.test(year)) {
    showMetaError('Year must be a 4-digit number (e.g. 1992).');
    return;
  }

  setMetaLoading(true);
  metaError.hidden = true;

  try {
    const resp = await fetch('/api/download', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, title, artist, album, year }),
    });

    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}));
      const detail = data.detail;
      showMetaError(
        typeof detail === 'string'
          ? detail
          : `Download failed (${resp.status}).`
      );
      return;
    }

    const blob     = await resp.blob();
    const filename = parseFilename(resp.headers.get('content-disposition') || '');
    const a        = document.createElement('a');
    a.href         = URL.createObjectURL(blob);
    a.download     = filename;
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(a.href);

    closeMetadataModal();
  } catch {
    showMetaError('Network error — is the server running?');
  } finally {
    setMetaLoading(false);
  }
}

function setMetaLoading(on) {
  metaDownloadBtn.disabled = on;
  metaDownloadBtn.querySelector('.btn-text').hidden = on;
  metaDownloadBtn.querySelector('.btn-loading').hidden = !on;
}

function showMetaError(msg) {
  metaError.textContent = msg;
  metaError.hidden = false;
}

function parseFilename(cd) {
  const utf8 = cd.match(/filename\*=UTF-8''([^;\s]+)/i);
  if (utf8) return decodeURIComponent(utf8[1]);
  const plain = cd.match(/filename="([^"]+)"/i);
  if (plain) return plain[1];
  return 'download';
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
