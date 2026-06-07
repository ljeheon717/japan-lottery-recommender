// ── 상수 ──────────────────────────────────────────
const NUM_MAX   = { loto6: 43, loto7: 37, miniloto: 31 };
const PICK_CNT  = { loto6: 6,  loto7: 7,  miniloto: 5  };
const FIXED_MAX = { loto6: 5,  loto7: 6,  miniloto: 4  };
const MY_KEY    = 'myLottoNumbers';

// ── 상태 ──────────────────────────────────────────
let genType    = 'loto6';
let genCount   = 1;
let genModes   = new Set(['random']);
let resType    = 'loto6';
let myNumType  = 'loto6';
let currentPage  = 1;
let totalPages   = null;

// ── 탭 전환 ──────────────────────────────────────
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById(tab.dataset.tab).classList.add('active');
  });
});

// ── 로또 종류 (추천 탭) ───────────────────────────
document.querySelectorAll('.type-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.type-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    genType = btn.dataset.type;
    updateFixedInputs();
  });
});

// ── 세트 수 ───────────────────────────────────────
document.querySelectorAll('.count-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.count-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    genCount = parseInt(btn.dataset.count);
  });
});

// ── 추천 방식 (랜덤 단독 / 나머지 복수) ──────────
document.querySelectorAll('.mode-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const mode = btn.dataset.mode;
    if (mode === 'random') {
      // 랜덤: 단독 전용 — 다른 모드 모두 해제
      genModes.clear();
      genModes.add('random');
      document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    } else {
      // 비랜덤: 랜덤이 켜져 있으면 먼저 해제
      if (genModes.has('random')) {
        genModes.delete('random');
        document.querySelector('.mode-btn[data-mode="random"]').classList.remove('active');
      }
      if (genModes.has(mode)) {
        if (genModes.size > 1) {   // 마지막 하나는 해제 불가
          genModes.delete(mode);
          btn.classList.remove('active');
        }
      } else {
        genModes.add(mode);
        btn.classList.add('active');
      }
    }
  });
});

// ── 당첨 번호 종류 ────────────────────────────────
document.querySelectorAll('.rtype-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.rtype-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    resType = btn.dataset.type;
    currentPage = 1;
    totalPages  = null;
    document.getElementById('results-result').innerHTML = '';
    document.getElementById('pagination').innerHTML = '';
    document.getElementById('source-badge').innerHTML = '';
  });
});

// ── 내 번호 종류 ──────────────────────────────────
document.querySelectorAll('.mtype-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.mtype-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    myNumType = btn.dataset.type;
    updateMyNumInputs();
    renderMyNumbers();
  });
});

// ── 고정 번호 입력 (동적) ─────────────────────────
function updateFixedInputs() {
  const maxFixed  = FIXED_MAX[genType];
  const numMax    = NUM_MAX[genType];
  const container = document.getElementById('fixed-inputs-container');
  const hint      = document.getElementById('fixed-hint');
  hint.textContent = `(최대 ${maxFixed}개, 선택)`;
  container.innerHTML = '';
  for (let i = 0; i < maxFixed; i++) {
    const inp = document.createElement('input');
    inp.className   = 'fixed-input';
    inp.type        = 'number';
    inp.min         = 1;
    inp.max         = numMax;
    inp.placeholder = `1~${numMax}`;
    container.appendChild(inp);
  }
}
updateFixedInputs();

// ── 내 번호 입력 (동적) ───────────────────────────
function updateMyNumInputs() {
  const pick      = PICK_CNT[myNumType];
  const numMax    = NUM_MAX[myNumType];
  const container = document.getElementById('my-num-inputs-container');
  const hint      = document.getElementById('my-num-hint');
  hint.textContent = `(${pick}개 입력)`;
  container.innerHTML = '';
  for (let i = 0; i < pick; i++) {
    const inp = document.createElement('input');
    inp.className   = 'fixed-input';
    inp.type        = 'number';
    inp.min         = 1;
    inp.max         = numMax;
    inp.placeholder = `1~${numMax}`;
    container.appendChild(inp);
  }
}
updateMyNumInputs();

// ── 헬퍼 ─────────────────────────────────────────
function ball(n, cls) {
  return `<div class="ball ${cls}">${n}</div>`;
}

function modeLabel(mode) {
  const map = { random: '🎲 랜덤', frequency: '📊 빈도', saju: '☯️ 오행', lucky: '🍀 행운' };
  return mode.split('+').map(m => map[m] || m).join(' + ');
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
  const end   = Math.min(total_pages, page + 2);
  let pages   = '';
  if (start > 1) pages += `<button class="page-btn" data-page="1">1</button>`;
  if (start > 2) pages += `<span class="page-ellipsis">…</span>`;
  for (let p = start; p <= end; p++) {
    pages += `<button class="page-btn ${p === page ? 'active' : ''}" data-page="${p}">${p}</button>`;
  }
  if (end < total_pages - 1) pages += `<span class="page-ellipsis">…</span>`;
  if (end < total_pages)     pages += `<button class="page-btn" data-page="${total_pages}">${total_pages}</button>`;

  const totalInfo = total
    ? `<span class="page-info">총 ${total.toLocaleString()}회 · ${page}/${total_pages} 페이지</span>`
    : `<span class="page-info">${page} 페이지</span>`;

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
  const el  = document.getElementById('generate-result');
  const btn = document.getElementById('generate-btn');

  const fixed = [];
  document.querySelectorAll('#fixed-inputs-container .fixed-input').forEach(inp => {
    const v = parseInt(inp.value);
    if (!isNaN(v) && v >= 1) fixed.push(v);
  });

  btn.disabled = true;
  el.innerHTML = `<div class="loading"><span class="spinner"></span> 생성 중...</div>`;

  try {
    const res = await fetch(`/api/generate/${genType}/${genCount}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ modes: [...genModes], fixed }),
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
  const el       = document.getElementById('results-result');
  const fetchBtn = document.getElementById('fetch-btn');
  fetchBtn.disabled = true;
  el.innerHTML = `<div class="loading"><span class="spinner"></span> 데이터 가져오는 중...</div>`;

  try {
    const res  = await fetch(`/api/results/${resType}?page=${page}&per_page=50`);
    const data = await res.json();
    currentPage = page;
    totalPages  = data.total_pages;

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

// ── 내 번호 기록 ──────────────────────────────────
function loadMyData() {
  try { return JSON.parse(localStorage.getItem(MY_KEY) || '{}'); }
  catch { return {}; }
}

function saveMyData(data) {
  localStorage.setItem(MY_KEY, JSON.stringify(data));
}

function renderMyNumbers() {
  const data = loadMyData();
  const list = data[myNumType] || [];
  const el   = document.getElementById('my-numbers-list');
  const typeLabel = { loto6: 'ロト6', loto7: 'ロト7', miniloto: 'ミニロト' };

  if (!list.length) {
    el.innerHTML = '<div class="empty-state">저장된 번호가 없습니다.</div>';
    return;
  }

  el.innerHTML = list.slice().reverse().map((entry, dispIdx) => {
    const actualIdx = list.length - 1 - dispIdx;
    return `
      <div class="my-number-row">
        <div class="my-number-header">
          <span class="my-number-meta">
            <span class="round-badge">${typeLabel[myNumType]}</span>
            <span class="result-date">${entry.date}</span>
          </span>
          <button class="delete-btn" data-idx="${actualIdx}">✕</button>
        </div>
        <div class="numbers">
          ${entry.numbers.map(n => ball(n, 'main')).join('')}
        </div>
      </div>
    `;
  }).join('');

  document.querySelectorAll('.delete-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const idx  = parseInt(btn.dataset.idx);
      const data = loadMyData();
      data[myNumType].splice(idx, 1);
      saveMyData(data);
      renderMyNumbers();
    });
  });
}
renderMyNumbers();

document.getElementById('save-my-btn').addEventListener('click', () => {
  const inputs  = document.querySelectorAll('#my-num-inputs-container .fixed-input');
  const numbers = [];
  const numMax  = NUM_MAX[myNumType];
  const msg     = document.getElementById('my-save-msg');

  inputs.forEach(inp => {
    const v = parseInt(inp.value);
    if (!isNaN(v) && v >= 1 && v <= numMax) numbers.push(v);
  });

  const unique = [...new Set(numbers)].sort((a, b) => a - b);

  if (unique.length < 1) {
    msg.innerHTML = '<div class="error" style="margin-top:10px">번호를 1개 이상 입력해주세요.</div>';
    setTimeout(() => { msg.innerHTML = ''; }, 2000);
    return;
  }

  const data  = loadMyData();
  if (!data[myNumType]) data[myNumType] = [];

  const today = new Date().toISOString().slice(0, 10);
  data[myNumType].push({ date: today, numbers: unique });
  saveMyData(data);

  inputs.forEach(inp => { inp.value = ''; });
  msg.innerHTML = '<div class="save-success">✅ 저장되었습니다.</div>';
  setTimeout(() => { msg.innerHTML = ''; }, 2000);

  renderMyNumbers();
});
