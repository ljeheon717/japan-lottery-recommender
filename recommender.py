"""
번호 추천 엔진
- random   : 순수 랜덤
- frequency: 전체 이력 빈도 가중치
- saju     : 음력 일진(천간) 오행 기반
- mypick   : 내 구매 기록의 번호 풀에서 조합 (낙첨 조합 번호는 우선 가중치 부여)
공통: 과거 당첨 조합 항상 제외, 고정 번호, 이전 회차 번호 간헐 포함
"""

import random
from collections import Counter
from datetime import date
from typing import Optional
from data import get_history, FALLBACK_DATA

# ── 오행 ──────────────────────────────────────────
_CHEONGAN = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
_OHANG_KO = {"木": "목(木)", "火": "화(火)", "土": "토(土)", "金": "금(金)", "水": "수(水)"}

RECENT_NUM_PROB = 0.4  # 최근 회차 번호 1개 포함 확률
MYPICK_LOSE_BOOST = 2.5  # 낙첨(당첨 번호 0개 일치) 조합의 번호 가중치 배수


def _ohang_groups(max_n: int) -> dict:
    size = max_n // 5
    groups = {}
    for i, oh in enumerate(["木", "火", "土", "金", "水"]):
        start = i * size + 1
        end = (i + 1) * size if i < 4 else max_n
        groups[oh] = list(range(start, end + 1))
    return groups


def _lunar_cheongan(solar_date: date) -> str:
    BASE = date(1984, 2, 2)
    diff = (solar_date - BASE).days % 10
    return _CHEONGAN[diff % 10]


def _get_ohang(d: date) -> str:
    cg = _lunar_cheongan(d)
    return {"갑": "木", "을": "木", "병": "火", "정": "火",
            "무": "土", "기": "土", "경": "金", "신": "金"}.get(cg, "水")


def _load_past_sets(ltype: str) -> set:
    data = get_history(ltype) or FALLBACK_DATA.get(ltype, [])
    return {frozenset(row["numbers"]) for row in data}


def _calc_freq(ltype: str, max_n: int) -> dict:
    data = get_history(ltype) or FALLBACK_DATA.get(ltype, [])
    counter = Counter()
    for row in data:
        for n in row["numbers"]:
            counter[n] += 1
    total = sum(counter.values()) or 1
    return {n: counter.get(n, 0) / total for n in range(1, max_n + 1)}


def _mypick_weights(max_n: int, pool: list) -> tuple:
    """
    선택한 구매 기록들의 번호로 가중치 맵 구성
    - 선택 기록 내 출현 빈도를 기본 가중치로 사용
    - 낙첨 조합(당첨 번호 0개 일치)에 포함된 번호는 MYPICK_LOSE_BOOST배 가산
      ("아직 안 나왔으니 나올 때가 됐다"는 관점에서 우선 추천)
    반환: (가중치 dict, 낙첨 조합 유래 번호 set, 선택 기록 수)
    """
    counter = Counter()
    lose_numbers = set()
    for rec in pool:
        nums = [n for n in rec.get("numbers", []) if 1 <= n <= max_n]
        for n in nums:
            counter[n] += 1
        if rec.get("match_count") == 0:
            lose_numbers.update(nums)

    weights = {}
    for n in range(1, max_n + 1):
        w = float(counter.get(n, 0))
        if n in lose_numbers:
            w = (w + 1.0) * MYPICK_LOSE_BOOST
        weights[n] = w if w > 0 else 0.05
    return weights, lose_numbers, len(pool)


def _recent_pool(ltype: str, max_n: int, last_n: int = 3) -> list:
    """최근 last_n 회차 당첨 번호 풀"""
    data = get_history(ltype) or FALLBACK_DATA.get(ltype, [])
    nums = []
    for row in data[:last_n]:
        nums.extend(row["numbers"])
    return list(set(n for n in nums if 1 <= n <= max_n))


# ── 공개 API ──────────────────────────────────────
def recommend_multi(
    ltype: str,
    max_n: int,
    pick: int,
    bonus_count: int,
    modes: list,
    fixed: Optional[list] = None,
    count: int = 1,
    target_date: Optional[date] = None,
    mypick_pool: Optional[list] = None,
) -> list[dict]:
    """
    modes: ['random', 'frequency', 'saju', 'mypick'] 중 복수 선택
    각 mode별로 count개 생성 → 그룹으로 반환
    과거 당첨 조합 제외는 항상 적용

    mypick_pool: 'mypick' 모드 선택 시, 사용자가 고른 구매 기록 목록
                 [{"numbers": [...], "match_count": int|None}, ...]
                 해당 기록들의 번호를 조합 풀로 사용하고,
                 낙첨(0개 일치) 기록의 번호는 가중치를 높여 우선 추천한다
    """
    if not modes:
        modes = ["random"]

    fixed = [f for f in (fixed or []) if 1 <= f <= max_n][:3]
    if len(fixed) >= pick:
        fixed = fixed[:pick - 1]

    past_sets = _load_past_sets(ltype)
    freq = _calc_freq(ltype, max_n)
    today = target_date or date.today()
    ohang = _get_ohang(today)
    ohang_groups = _ohang_groups(max_n)
    recent = _recent_pool(ltype, max_n)

    mypick_weights = mypick_lose = None
    mypick_count = 0
    if "mypick" in modes:
        mypick_weights, mypick_lose, mypick_count = _mypick_weights(max_n, mypick_pool or [])

    mypick_ctx = (mypick_weights, mypick_lose, mypick_count)

    results = []
    for _ in range(count):
        if len(modes) == 1 and "mypick" not in modes:
            mode = modes[0]
            r = _pick_one(max_n, pick, bonus_count, mode,
                          fixed, past_sets, freq, ohang, ohang_groups, recent, today)
            r["mode"] = mode
        else:
            # 복수 방식 / mypick 포함: 통합 가중치로 단일 세트 생성
            r = _pick_combined(max_n, pick, bonus_count, modes,
                               fixed, past_sets, freq, ohang, ohang_groups, recent, today,
                               mypick_ctx)
            r["mode"] = "+".join(modes)
        results.append(r)
    return results


def _combined_weights(candidates, modes, freq, ohang, ohang_groups, mypick_ctx) -> list:
    """각 방식의 가중치를 곱해 통합 점수 산출"""
    weights = []
    ohang_nums = set(ohang_groups.get(ohang, [])) if ohang else set()
    mypick_weights = mypick_ctx[0] if mypick_ctx else None

    for n in candidates:
        w = 1.0
        if "frequency" in modes:
            # 빈도: 정규화된 출현률 (0.001 ~ 1)
            w *= (freq.get(n, 0) + 0.001) * 1000
        if "saju" in modes:
            # 오행: 해당 그룹이면 3배 가산
            w *= 3.0 if n in ohang_nums else 1.0
        if "mypick" in modes and mypick_weights:
            # 내 구매 기록 풀의 출현 빈도 + 낙첨 조합 번호 가산
            w *= mypick_weights.get(n, 0.05)
        if "random" in modes:
            w *= 1.0
        weights.append(w)
    return weights


def _pick_combined(max_n, pick, bonus_count, modes,
                   fixed, past_sets, freq, ohang, ohang_groups, recent, today,
                   mypick_ctx=None) -> dict:
    pool = list(range(1, max_n + 1))
    retries = 0

    lucky_num = None
    if recent and random.random() < RECENT_NUM_PROB:
        candidates_lucky = [n for n in recent if n not in fixed]
        if candidates_lucky and len(fixed) < pick - 1:
            lucky_num = random.choice(candidates_lucky)

    effective_fixed = list(fixed)
    if lucky_num and lucky_num not in effective_fixed:
        effective_fixed.append(lucky_num)

    while True:
        need = pick - len(effective_fixed)
        candidates = [n for n in pool if n not in effective_fixed]
        weights = _combined_weights(candidates, modes, freq, ohang, ohang_groups, mypick_ctx)
        chosen = _weighted_sample(candidates, weights, need)
        nums = sorted(effective_fixed + chosen)
        retries += 1
        if frozenset(nums) not in past_sets:
            break
        if retries > 1000:
            break

    remaining = [n for n in pool if n not in nums]
    bonus = sorted(random.sample(remaining, bonus_count))
    reason = _build_combined_reason(nums, modes, fixed, lucky_num,
                                    ohang, freq, ohang_groups, retries - 1, max_n, today,
                                    mypick_ctx)
    return {"numbers": nums, "bonus": bonus, "reason": reason}


def _build_combined_reason(nums, modes, fixed, lucky_num, ohang, freq,
                            ohang_groups, retries, max_n, today, mypick_ctx=None) -> list:
    reasons = []
    if fixed:
        reasons.append(f"고정 번호 {fixed} 포함")
    if lucky_num:
        reasons.append(f"이전 회차 당첨 번호 {lucky_num} 포함 (행운 적용)")

    # 빈도 기여
    if "frequency" in modes and freq:
        top_nums = {n for n, _ in sorted(freq.items(), key=lambda x: -x[1])[:10]}
        hot = [n for n in nums if n in top_nums]
        if hot:
            pcts_str = ", ".join(f"{n}번({round(freq[n]*100,1)}%)" for n in hot)
            reasons.append(f"고빈도 기여: {pcts_str}")

    # 오행 기여
    if "saju" in modes and ohang:
        ohang_ko = _OHANG_KO.get(ohang, ohang)
        cg = _lunar_cheongan(today)
        ohang_nums = [n for n in nums if n in ohang_groups.get(ohang, [])]
        reasons.append(f"오행 기여 — 오늘 일진: {cg}일 → {ohang_ko}")
        if ohang_nums:
            reasons.append(f"오행 해당 번호: {ohang_nums}")

    # 내 구매 기록 기여
    if "mypick" in modes and mypick_ctx:
        mypick_weights, lose_numbers, pool_count = mypick_ctx
        if pool_count:
            reasons.append(f"내 구매 기록 {pool_count}건의 번호 풀에서 조합")
            mine = [n for n in nums if mypick_weights and mypick_weights.get(n, 0) > 0.05]
            if mine:
                reasons.append(f"구매 기록 포함 번호: {mine}")
            lose_hit = [n for n in nums if n in lose_numbers]
            if lose_hit:
                reasons.append(f"낙첨 조합(당첨 0개 일치) 번호 우선 반영: {lose_hit}")
        else:
            reasons.append("선택된 구매 기록이 없어 무작위로 보완")

    # 랜덤이 포함된 경우
    if "random" in modes and len(modes) > 1:
        reasons.append("랜덤 가중치 포함")
    elif "random" in modes:
        reasons.append("순수 무작위 추출")

    if retries > 0:
        reasons.append(f"과거 당첨 조합 {retries}회 제외 후 선택")
    return reasons


def _pick_one(max_n, pick, bonus_count, mode,
              fixed, past_sets, freq, ohang, ohang_groups, recent, today) -> dict:
    pool = list(range(1, max_n + 1))
    retries = 0

    # 이전 회차 번호 간헐 포함 (40% 확률, fixed에 자리가 있을 때)
    lucky_num = None
    if recent and random.random() < RECENT_NUM_PROB:
        candidates = [n for n in recent if n not in fixed]
        if candidates and len(fixed) < pick - 1:
            lucky_num = random.choice(candidates)

    effective_fixed = list(fixed)
    if lucky_num and lucky_num not in effective_fixed:
        effective_fixed.append(lucky_num)

    while True:
        nums = _sample(pool, pick, effective_fixed, mode, freq, ohang, ohang_groups, max_n)
        retries += 1
        if frozenset(nums) not in past_sets:
            break
        if retries > 1000:
            break

    remaining = [n for n in pool if n not in nums]
    bonus = sorted(random.sample(remaining, bonus_count))
    reason = _build_reason(nums, mode, fixed, lucky_num, ohang, freq, retries - 1, max_n, today)
    return {"numbers": nums, "bonus": bonus, "reason": reason}


def _sample(pool, pick, fixed, mode, freq, ohang, ohang_groups, max_n) -> list:
    need = pick - len(fixed)
    candidates = [n for n in pool if n not in fixed]

    if mode == "frequency" and freq:
        weights = [freq.get(n, 0) + 0.001 for n in candidates]
        chosen = _weighted_sample(candidates, weights, need)

    elif mode == "saju" and ohang and ohang_groups:
        primary = [n for n in ohang_groups.get(ohang, []) if n not in fixed]
        secondary = [n for n in candidates if n not in primary]
        n_primary = min(len(primary), need)
        chosen = random.sample(primary, n_primary)
        if n_primary < need:
            chosen += random.sample(secondary, need - n_primary)

    else:
        chosen = random.sample(candidates, need)

    return sorted(fixed + chosen)


def _weighted_sample(population, weights, k) -> list:
    chosen, pop, wts = [], list(population), list(weights)
    for _ in range(k):
        total = sum(wts)
        r, cumul = random.uniform(0, total), 0
        for i, w in enumerate(wts):
            cumul += w
            if r <= cumul:
                chosen.append(pop.pop(i))
                wts.pop(i)
                break
    return chosen


def _build_reason(nums, mode, fixed, lucky_num, ohang, freq, retries, max_n, today) -> list:
    reasons = []

    if fixed:
        reasons.append(f"고정 번호 {fixed} 포함")

    if lucky_num:
        reasons.append(f"이전 회차 당첨 번호 {lucky_num} 포함 (행운 적용)")

    if mode == "frequency" and freq:
        top_nums = {n for n, _ in sorted(freq.items(), key=lambda x: -x[1])[:10]}
        hot = [n for n in nums if n in top_nums]
        if hot:
            pcts_str = ", ".join(f"{n}번({round(freq[n]*100,1)}%)" for n in hot)
            reasons.append(f"고빈도 번호: {pcts_str}")
        cold = sorted(nums, key=lambda n: freq.get(n, 0))[:2]
        reasons.append(f"저빈도 균형 번호: {cold}")

    elif mode == "saju" and ohang:
        ohang_ko = _OHANG_KO.get(ohang, ohang)
        cg = _lunar_cheongan(today)
        ohang_nums = [n for n in nums if n in _ohang_groups(max_n).get(ohang, [])]
        reasons.append(f"오늘 일진: {cg}일 → 오행 {ohang_ko}")
        if ohang_nums:
            reasons.append(f"오행 해당 번호: {ohang_nums}")

    else:
        reasons.append("순수 무작위 추출")

    if retries > 0:
        reasons.append(f"과거 당첨 조합 {retries}회 제외 후 선택")

    return reasons
