// ── 상수 ──────────────────────────────────────────
const NUM_MAX   = { loto6: 43, loto7: 37, miniloto: 31 };
const PICK_CNT  = { loto6: 6,  loto7: 7,  miniloto: 5  };
const FIXED_MAX = { loto6: 5,  loto7: 6,  miniloto: 4  };
const HIST_KEY  = 'lotteryHistory';

// ── 상태 ──────────────────────────────────────────
let genType    = 'loto6';
let genCount   = 1;
let genModes   = new Set(['random']);
let resType    = 'loto6';
let histType   = 'loto6';
let currentPage  = 1;
let totalPages   = null;

// ── 탭 전환 ──────────────────────────────────────
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById(tab.dataset.tab).classList.add('active');
    if (tab.dataset.tab === 'history') renderHistory();
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
      genModes.clear();
      genModes.add('random');
      document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    } else {
      if (genModes.has('random')) {
        genModes.delete('random');
        document.querySelector('.mode-btn[data-mode="random"]').classList.remove('active');
      }
      if (genModes.has(mode)) {
        if (genModes.size > 1) {
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

// ── 이력 로또 종류 ────────────────────────────────
document.querySelectorAll('.htype-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.htype-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    histType = btn.dataset.type;
    updateHistInputs();
    renderHistory();
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

// ── 이력 번호 입력 (동적) ─────────────────────────
function updateHistInputs() {
  const pick      = PICK_CNT[histType];
  const numMax    = NUM_MAX[histType];
  const container = document.getElementById('hist-num-inputs-container');
  const hint      = document.getElementById('hist-num-hint');
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
updateHistInputs();

// ── 헬퍼 ─────────────────────────────────────────
function ball(n, cls) {
  return `<div class="ball ${cls}">${n}</div>`;
}

function modeLabel(mode) {
  const map = { random: '🎲 랜덤', frequency: '📊 빈도', saju: '☯️ 오행', lucky: '🍀 행운', oddeven: '⚖️ 홀짝' };
  return mode.split('+').map(m => map[m] || m).join(' + ');
}

function renderDrawInfo(draw) {
  if (!draw || !draw.round) return '';
  const dateStr = draw.draw_date
    ? `${draw.draw_date}${draw.weekday ? ` (${draw.weekday})` : ''}`
    : '미정';
  return `
    <div class="draw-info">
      <div class="draw-info-item">
        <span class="draw-info-label">응모 회차</span>
        <span class="draw-info-value">제 ${draw.round} 회</span>
      </div>
      <div class="draw-info-item">
        <span class="draw-info-label">추첨 · 당첨 발표일</span>
        <span class="draw-info-value">${dateStr}</span>
      </div>
    </div>`;
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
    el.innerHTML = renderDrawInfo(data.draw) + renderSets(data.results);
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

// ── 이력 기록 ─────────────────────────────────────
const winCache = {};  // { ltype: { "round": { numbers, bonus } } }

function loadHistory() {
  try { return JSON.parse(localStorage.getItem(HIST_KEY) || '{}'); }
  catch { return {}; }
}

function saveHistory(data) {
  localStorage.setItem(HIST_KEY, JSON.stringify(data));
}

async function fetchWinData(ltype) {
  if (winCache[ltype]) return winCache[ltype];
  const map = {};
  for (let page = 1; page <= 2; page++) {
    try {
      const res  = await fetch(`/api/results/${ltype}?page=${page}&per_page=50`);
      const data = await res.json();
      if (!data.results?.length) break;
      data.results.forEach(r => {
        map[String(r.round)] = { numbers: r.numbers, bonus: r.bonus || [] };
      });
      if (data.results.length < 50) break;
    } catch { break; }
  }
  winCache[ltype] = map;
  return map;
}

// 일본 로또 등수 판정
function prizeLabel(ltype, matchCount, bonusMatchCount) {
  if (ltype === 'loto6') {
    if (matchCount === 6)                         return '🏆 1등';
    if (matchCount === 5 && bonusMatchCount >= 1) return '🥈 2등';
    if (matchCount === 5)                         return '🥉 3등';
    if (matchCount === 4)                         return '4등';
    if (matchCount === 3)                         return '5등';
  } else if (ltype === 'loto7') {
    if (matchCount === 7)                         return '🏆 1등';
    if (matchCount === 6 && bonusMatchCount >= 2) return '🥈 2등';
    if (matchCount === 6 && bonusMatchCount >= 1) return '🥉 3등';
    if (matchCount === 6)                         return '4등';
    if (matchCount === 5 && bonusMatchCount >= 1) return '5등';
    if (matchCount === 5)                         return '6등';
    if (matchCount === 4)                         return '7등';
  } else if (ltype === 'miniloto') {
    if (matchCount === 5)                         return '🏆 1등';
    if (matchCount === 4 && bonusMatchCount >= 1) return '🥈 2등';
    if (matchCount === 4)                         return '🥉 3등';
    if (matchCount === 3)                         return '4등';
    if (matchCount === 2)                         return '5등';
  }
  return null;
}

async function renderHistory() {
  const data    = loadHistory();
  const entries = (data[histType] || []).slice().reverse();
  const el      = document.getElementById('history-list');
  const typeLabel = { loto6: 'ロト6', loto7: 'ロト7', miniloto: 'ミニロト' };

  if (!entries.length) {
    el.innerHTML = '<div class="empty-state">저장된 이력이 없습니다.<br><span style="font-size:0.82rem;color:#4a5568">회차 번호와 구매한 번호를 입력하면 당첨 여부를 확인할 수 있습니다.</span></div>';
    return;
  }

  el.innerHTML = `<div class="loading"><span class="spinner"></span> 당첨 번호 확인 중...</div>`;
  const winData = await fetchWinData(histType);

  el.innerHTML = entries.map((entry, dispIdx) => {
    const actualIdx = (data[histType].length - 1) - dispIdx;
    const winRound  = winData[String(entry.round)];

    if (!winRound) {
      return `
        <div class="history-row">
          <div class="history-header">
            <div class="history-meta">
              <span class="round-badge">제 ${entry.round} 회</span>
              <span class="ltype-tag">${typeLabel[histType]}</span>
              <span class="result-date">${entry.saved}</span>
              <span class="match-badge match-unknown">미확인</span>
            </div>
            <button class="delete-btn" data-idx="${actualIdx}">✕</button>
          </div>
          <div class="hist-num-row">
            <span class="row-label">내 번호</span>
            <div class="numbers">${entry.numbers.map(n => ball(n, 'main')).join('')}</div>
          </div>
          <div class="hist-num-row">
            <span class="row-label">당첨</span>
            <span class="win-pending">최근 100회차 이내 데이터가 없습니다</span>
          </div>
        </div>`;
    }

    const winSet   = new Set(winRound.numbers);
    const bonusSet = new Set(winRound.bonus);
    const matchCount      = entry.numbers.filter(n => winSet.has(n)).length;
    const bonusMatchCount = entry.numbers.filter(n => bonusSet.has(n)).length;
    const prize = prizeLabel(histType, matchCount, bonusMatchCount);

    const badgeCls  = matchCount >= 5 ? 'match-high' : matchCount >= 3 ? 'match-mid' : 'match-low';
    const badgeHtml = prize
      ? `<span class="prize-badge">${prize}</span><span class="match-badge ${badgeCls}">${matchCount}개 일치</span>`
      : `<span class="match-badge ${badgeCls}">${matchCount}개 일치</span>`;

    return `
      <div class="history-row">
        <div class="history-header">
          <div class="history-meta">
            <span class="round-badge">제 ${entry.round} 회</span>
            <span class="ltype-tag">${typeLabel[histType]}</span>
            <span class="result-date">${entry.saved}</span>
            ${badgeHtml}
          </div>
          <button class="delete-btn" data-idx="${actualIdx}">✕</button>
        </div>
        <div class="hist-num-row">
          <span class="row-label">내 번호</span>
          <div class="numbers">
            ${entry.numbers.map(n => ball(n, winSet.has(n) ? 'main matched' : 'main')).join('')}
          </div>
        </div>
        <div class="hist-num-row">
          <span class="row-label">당첨 번호</span>
          <div class="numbers">
            ${winRound.numbers.map(n => ball(n, entry.numbers.includes(n) ? 'winning matched' : 'winning')).join('')}
            ${winRound.bonus?.length
              ? `<span class="divider">|</span>${winRound.bonus.map(n => ball(n, 'bonus')).join('')}`
              : ''}
          </div>
        </div>
      </div>`;
  }).join('');

  el.querySelectorAll('.delete-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const idx = parseInt(btn.dataset.idx);
      const d   = loadHistory();
      d[histType].splice(idx, 1);
      saveHistory(d);
      renderHistory();
    });
  });
}

document.getElementById('save-hist-btn').addEventListener('click', async () => {
  const roundInput = document.getElementById('hist-round-input');
  const round      = parseInt(roundInput.value);
  const numMax     = NUM_MAX[histType];
  const msg        = document.getElementById('hist-save-msg');

  if (isNaN(round) || round < 1) {
    msg.innerHTML = '<div class="error" style="margin-top:10px">회차 번호를 입력해주세요.</div>';
    setTimeout(() => { msg.innerHTML = ''; }, 2500);
    return;
  }

  const inputs  = document.querySelectorAll('#hist-num-inputs-container .fixed-input');
  const numbers = [];
  inputs.forEach(inp => {
    const v = parseInt(inp.value);
    if (!isNaN(v) && v >= 1 && v <= numMax) numbers.push(v);
  });
  const unique = [...new Set(numbers)].sort((a, b) => a - b);

  if (unique.length < 1) {
    msg.innerHTML = '<div class="error" style="margin-top:10px">번호를 1개 이상 입력해주세요.</div>';
    setTimeout(() => { msg.innerHTML = ''; }, 2500);
    return;
  }

  const data = loadHistory();
  if (!data[histType]) data[histType] = [];

  if (data[histType].find(e => e.round === round)) {
    msg.innerHTML = '<div class="error" style="margin-top:10px">이미 저장된 회차입니다.</div>';
    setTimeout(() => { msg.innerHTML = ''; }, 2500);
    return;
  }

  const today = new Date().toISOString().slice(0, 10);
  data[histType].push({ round, numbers: unique, saved: today });
  saveHistory(data);

  delete winCache[histType];  // 저장 후 캐시 초기화 → 다음 렌더 시 재조회

  roundInput.value = '';
  inputs.forEach(inp => { inp.value = ''; });
  msg.innerHTML = '<div class="save-success">✅ 저장되었습니다.</div>';
  setTimeout(() => { msg.innerHTML = ''; }, 2500);

  renderHistory();
});
