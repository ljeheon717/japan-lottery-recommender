// ── 상태 ──────────────────────────────────────────
let genType = 'loto6';
let genCount = 1;
let genModes = new Set(['random']);
let resType = 'loto6';
let currentPage = 1;
let totalPages = null;

// ── 탭 전환 ──────────────────────────────────────
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById(tab.dataset.tab).classList.add('active');
  });
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
  });
});

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
function ball(n, cls) {
  return `<div class="ball ${cls}">${n}</div>`;
}

function modeLabel(mode) {
  const map = { random: '🎲 랜덤', frequency: '📊 빈도', saju: '☯️ 오행' };
  // 복수 방식은 "frequency+saju" 형태로 옴
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
