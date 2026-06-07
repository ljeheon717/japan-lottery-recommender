// ── 상태 ──────────────────────────────────────────
let genType = 'loto6';
let genCount = 1;
let genModes = new Set(['random']);
let resType = 'loto6';
let currentPage = 1;
let totalPages = null;
let purchaseType = 'loto6';
let purchases = [];
let selectedPurchaseIds = new Set();

// ── 탭 전환 ──────────────────────────────────────
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById(tab.dataset.tab).classList.add('active');
    if (tab.dataset.tab === 'purchases') loadPurchaseList();
  });
});

// ── 내 구매 기록 ──────────────────────────────────
document.querySelectorAll('.ptype-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.ptype-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    purchaseType = btn.dataset.type;
    loadPurchaseList();
  });
});

async function loadPurchaseList() {
  const list = document.getElementById('purchase-list');
  list.innerHTML = `<div class="loading"><span class="spinner"></span> 불러오는 중...</div>`;
  try {
    const res = await fetch(`/api/purchases?ltype=${purchaseType}`);
    const data = await res.json();
    purchases = data.purchases || [];
    renderPurchaseList();
  } catch (e) {
    list.innerHTML = `<div class="error">구매 기록을 불러오지 못했습니다: ${e.message}</div>`;
  }
}

function renderPurchaseList() {
  const list = document.getElementById('purchase-list');
  if (!purchases.length) {
    list.innerHTML = `<div class="empty-msg">아직 등록된 ${LOTTO_LABEL[purchaseType] || purchaseType} 구매 기록이 없습니다.</div>`;
    return;
  }
  list.innerHTML = purchases.map(p => `
    <div class="purchase-row">
      <div class="purchase-meta">
        <span class="purchase-round">제 ${p.round} 회</span>
        <div class="numbers">
          ${p.numbers.map(n => ball(n, 'main')).join('')}
        </div>
      </div>
      ${matchBadge(p.match_count)}
      <button class="purchase-del-btn" data-id="${p.id}">삭제</button>
    </div>
  `).join('');
  list.querySelectorAll('.purchase-del-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = parseInt(btn.dataset.id);
      btn.disabled = true;
      try {
        await fetch(`/api/purchases/${purchaseType}/${id}`, { method: 'DELETE' });
        selectedPurchaseIds.delete(id);
        await loadPurchaseList();
      } catch (e) {
        btn.disabled = false;
      }
    });
  });
}

document.getElementById('purchase-add-btn').addEventListener('click', async () => {
  const msgEl = document.getElementById('purchase-add-msg');
  const btn = document.getElementById('purchase-add-btn');
  const round = document.getElementById('purchase-round').value.trim();
  const numbers = document.getElementById('purchase-numbers').value
    .split(',').map(s => parseInt(s.trim())).filter(n => !isNaN(n));

  if (!round) {
    msgEl.innerHTML = `<div class="error">회차를 입력해주세요.</div>`;
    return;
  }
  if (!numbers.length) {
    msgEl.innerHTML = `<div class="error">구매한 번호를 쉼표로 구분해 입력해주세요.</div>`;
    return;
  }

  btn.disabled = true;
  msgEl.innerHTML = '';
  try {
    const res = await fetch('/api/purchases', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ltype: purchaseType, round, numbers }),
    });
    const data = await res.json();
    if (!res.ok) {
      msgEl.innerHTML = `<div class="error">${data.error || '추가에 실패했습니다.'}</div>`;
      return;
    }
    document.getElementById('purchase-round').value = '';
    document.getElementById('purchase-numbers').value = '';
    await loadPurchaseList();
  } catch (e) {
    msgEl.innerHTML = `<div class="error">오류: ${e.message}</div>`;
  } finally {
    btn.disabled = false;
  }
});

// ── 버튼 그룹 ─────────────────────────────────────
document.querySelectorAll('.type-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.type-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    genType = btn.dataset.type;
    // 고정 번호 max 값 업데이트
    const maxMap = { loto6: 43, loto7: 37, miniloto: 31 };
    document.querySelectorAll('.fixed-input').forEach(inp => {
      inp.max = maxMap[genType] || 43;
      inp.placeholder = `1~${maxMap[genType] || 43}`;
    });
    if (genModes.has('mypick')) {
      selectedPurchaseIds.clear();
      loadMypickOptions();
    }
  });
});

document.querySelectorAll('.count-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.count-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    genCount = parseInt(btn.dataset.count);
  });
});

document.querySelectorAll('.mode-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const mode = btn.dataset.mode;
    if (genModes.has(mode)) {
      if (genModes.size > 1) {      // 최소 1개는 유지
        genModes.delete(mode);
        btn.classList.remove('active');
      }
    } else {
      // 기본값 랜덤만 선택된 상태에서 다른 방식 첫 선택 → 랜덤 해제
      if (genModes.size === 1 && genModes.has('random') && mode !== 'random') {
        genModes.delete('random');
        document.querySelector('.mode-btn[data-mode="random"]').classList.remove('active');
      }
      genModes.add(mode);
      btn.classList.add('active');
    }
    syncMypickPanel();
  });
});

function syncMypickPanel() {
  const panel = document.getElementById('mypick-panel');
  if (genModes.has('mypick')) {
    panel.classList.remove('hidden');
    loadMypickOptions();
  } else {
    panel.classList.add('hidden');
  }
}

let mypickOptions = [];

async function loadMypickOptions() {
  const list = document.getElementById('mypick-list');
  list.innerHTML = `<div class="empty-msg">불러오는 중...</div>`;
  try {
    const res = await fetch(`/api/purchases?ltype=${genType}`);
    const data = await res.json();
    mypickOptions = data.purchases || [];
    selectedPurchaseIds = new Set([...selectedPurchaseIds].filter(id => mypickOptions.some(p => p.id === id)));
    renderMypickPanel();
  } catch (e) {
    list.innerHTML = `<div class="empty-msg">구매 기록을 불러오지 못했습니다.</div>`;
  }
}

function renderMypickPanel() {
  const list = document.getElementById('mypick-list');
  if (!mypickOptions.length) {
    list.innerHTML = `<div class="empty-msg">'내 구매 기록' 탭에서 ${LOTTO_LABEL[genType] || genType} 기록을 먼저 추가해주세요.</div>`;
    return;
  }
  list.innerHTML = mypickOptions.map(p => `
    <label class="mypick-row">
      <input type="checkbox" data-id="${p.id}" ${selectedPurchaseIds.has(p.id) ? 'checked' : ''} />
      <span class="purchase-round">제 ${p.round} 회</span>
      <span>${p.numbers.join(', ')}</span>
      ${matchBadge(p.match_count)}
    </label>
  `).join('');
  list.querySelectorAll('input[type="checkbox"]').forEach(cb => {
    cb.addEventListener('change', () => {
      const id = parseInt(cb.dataset.id);
      if (cb.checked) selectedPurchaseIds.add(id);
      else selectedPurchaseIds.delete(id);
    });
  });
}

document.querySelectorAll('.rtype-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.rtype-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    resType = btn.dataset.type;
    currentPage = 1;
    totalPages = null;
    document.getElementById('results-result').innerHTML = '';
    document.getElementById('pagination').innerHTML = '';
    document.getElementById('source-badge').innerHTML = '';
  });
});

// ── 헬퍼 ─────────────────────────────────────────
const LOTTO_LABEL = { loto6: 'ロト6', loto7: 'ロト7', miniloto: 'ミニロト' };

function ball(n, cls) {
  return `<div class="ball ${cls}">${n}</div>`;
}

function modeLabel(mode) {
  const map = { random: '🎲 랜덤', frequency: '📊 빈도', saju: '☯️ 오행', mypick: '🗂️ 내 조합' };
  // 복수 방식은 "frequency+saju" 형태로 옴
  return mode.split('+').map(m => map[m] || m).join(' + ');
}

function matchBadge(matchCount) {
  if (matchCount === null || matchCount === undefined) {
    return `<span class="match-badge unknown">비교 불가</span>`;
  }
  if (matchCount === 0) {
    return `<span class="match-badge lose">낙첨 (일치 0개)</span>`;
  }
  return `<span class="match-badge hit">일치 ${matchCount}개</span>`;
}

function renderSets(sets) {
  return sets.map((s, i) => `
    <div class="result-set">
      <div class="set-header">
        <span class="set-label">#${i + 1}</span>
        <span class="mode-tag">${modeLabel(s.mode || 'random')}</span>
      </div>
      <div class="numbers">
        ${s.numbers.map(n => ball(n, 'main')).join('')}
        <span class="divider">|</span>
        ${s.bonus.map(n => ball(n, 'bonus')).join('')}
      </div>
      ${s.reason && s.reason.length ? `
        <div class="reason">
          ${s.reason.map(r => `<span class="reason-item">• ${r}</span>`).join('')}
        </div>
      ` : ''}
    </div>
  `).join('');
}

function renderResults(rows) {
  return rows.map(r => `
    <div class="result-row">
      <div class="result-header">
        <span class="round-badge">제 ${r.round} 회</span>
        <span class="result-date">${r.date}</span>
      </div>
      <div class="numbers">
        ${r.numbers.map(n => ball(n, 'main')).join('')}
        <span class="divider">|</span>
        ${r.bonus.map(n => ball(n, 'bonus')).join('')}
      </div>
    </div>
  `).join('');
}

function renderPagination(page, total_pages, total) {
  if (!total_pages || total_pages <= 1) {
    document.getElementById('pagination').innerHTML = '';
    return;
  }
  const start = Math.max(1, page - 2);
  const end = Math.min(total_pages, page + 2);
  let pages = '';
  if (start > 1) pages += `<button class="page-btn" data-page="1">1</button>`;
  if (start > 2) pages += `<span class="page-ellipsis">…</span>`;
  for (let p = start; p <= end; p++) {
    pages += `<button class="page-btn ${p === page ? 'active' : ''}" data-page="${p}">${p}</button>`;
  }
  if (end < total_pages - 1) pages += `<span class="page-ellipsis">…</span>`;
  if (end < total_pages) pages += `<button class="page-btn" data-page="${total_pages}">${total_pages}</button>`;

  const totalInfo = total
    ? `<span class="page-info">총 ${total.toLocaleString()}회 · ${page}/${total_pages} 페이지</span>`
    : `<span class="page-info">${page} 페이지 (↻ 전체 갱신 시 전체 이력 표시)</span>`;

  document.getElementById('pagination').innerHTML = `
    <div class="pagination">
      ${totalInfo}
      <div class="page-btns">
        <button class="page-btn nav" data-page="${page - 1}" ${page <= 1 ? 'disabled' : ''}>‹</button>
        ${pages}
        <button class="page-btn nav" data-page="${page + 1}" ${page >= total_pages ? 'disabled' : ''}>›</button>
      </div>
    </div>
  `;
  document.querySelectorAll('.page-btn:not([disabled])').forEach(btn => {
    btn.addEventListener('click', () => {
      const p = parseInt(btn.dataset.page);
      if (p >= 1 && (!total_pages || p <= total_pages)) fetchResults(p);
    });
  });
}

function sourceBadge(source, total) {
  const map = {
    live:   ['badge-live',   '🟢 실시간'],
    cache:  ['badge-cache',  '🔵 캐시'],
    sample: ['badge-sample', '🟡 샘플'],
  };
  const [cls, label] = map[source] || ['badge-sample', source];
  const totalStr = total ? ` · ${total.toLocaleString()}회 이력` : '';
  document.getElementById('source-badge').innerHTML =
    `<span class="badge ${cls}">${label}${totalStr}</span>`;
}

// ── 번호 생성 ─────────────────────────────────────
document.getElementById('generate-btn').addEventListener('click', async () => {
  const el = document.getElementById('generate-result');
  const btn = document.getElementById('generate-btn');

  // 고정 번호 수집
  const fixed = [];
  document.querySelectorAll('.fixed-input').forEach(inp => {
    const v = parseInt(inp.value);
    if (!isNaN(v) && v >= 1) fixed.push(v);
  });

  btn.disabled = true;
  el.innerHTML = `<div class="loading"><span class="spinner"></span> 생성 중...</div>`;

  const payload = { modes: [...genModes], fixed };
  if (genModes.has('mypick')) payload.purchase_ids = [...selectedPurchaseIds];

  try {
    const res = await fetch(`/api/generate/${genType}/${genCount}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    el.innerHTML = renderSets(data.results);
  } catch (e) {
    el.innerHTML = `<div class="error">생성 실패: ${e.message}</div>`;
  } finally {
    btn.disabled = false;
  }
});

// ── 당첨 번호 조회 ────────────────────────────────
async function fetchResults(page = 1) {
  const el = document.getElementById('results-result');
  const fetchBtn = document.getElementById('fetch-btn');
  fetchBtn.disabled = true;
  el.innerHTML = `<div class="loading"><span class="spinner"></span> 데이터 가져오는 중...</div>`;

  try {
    const res = await fetch(`/api/results/${resType}?page=${page}&per_page=50`);
    const data = await res.json();
    currentPage = page;
    totalPages = data.total_pages;

    if (!data.results?.length) {
      el.innerHTML = `<div class="error">데이터를 가져올 수 없습니다.</div>`;
      return;
    }
    sourceBadge(data.source, data.total);
    el.innerHTML = renderResults(data.results);
    renderPagination(currentPage, data.total_pages, data.total);
  } catch (e) {
    el.innerHTML = `<div class="error">오류: ${e.message}</div>`;
  } finally {
    fetchBtn.disabled = false;
  }
}

document.getElementById('fetch-btn').addEventListener('click', () => fetchResults(currentPage));
