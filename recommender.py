"""
번호 추천 엔진
- random   : 순수 랜덤 (단독 전용)
- frequency: 전체 이력 빈도 가중치
- saju     : 음력 일진(천간) 오행 기반
- lucky    : 최근 3회차 출현 번호 중 1개를 행운 번호로 보장 포함, 나머지는 무작위
공통: 과거 당첨 조합 항상 제외, 고정 번호
"""

import random
from collections import Counter
from datetime import date
from typing import Optional
from data import get_history, FALLBACK_DATA

# ── 오행 ──────────────────────────────────────────
_CHEONGAN = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
_OHANG_KO = {"木": "목(木)", "火": "화(火)", "土": "토(土)", "金": "금(金)", "水": "수(水)"}

RECENT_NUM_PROB = 0.4  # 최근 회차 번호 1개 포함 확률 (lucky 이외 모드에서만 적용)


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


def _recent_pool(ltype: str, max_n: int, last_n: int = 3) -> list:
    """최근 last_n 회차 당첨 번호 풀 (중복 포함 — lucky 가중치용)"""
    data = get_history(ltype) or FALLBACK_DATA.get(ltype, [])
    nums = []
    for row in data[:last_n]:
        nums.extend(n for n in row["numbers"] if 1 <= n <= max_n)
    return nums


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
) -> list[dict]:
    if not modes:
        modes = ["random"]

    max_fixed = pick - 1
    fixed = [f for f in (fixed or []) if 1 <= f <= max_n][:max_fixed]
    if len(fixed) >= pick:
        fixed = fixed[:pick - 1]

    past_sets = _load_past_sets(ltype)
    freq = _calc_freq(ltype, max_n)
    today = target_date or date.today()
    ohang = _get_ohang(today)
    ohang_groups = _ohang_groups(max_n)
    recent = _recent_pool(ltype, max_n)

    results = []
    for _ in range(count):
        if len(modes) == 1:
            mode = modes[0]
            r = _pick_one(max_n, pick, bonus_count, mode,
                          fixed, past_sets, freq, ohang, ohang_groups, recent, today)
            r["mode"] = mode
        else:
            r = _pick_combined(max_n, pick, bonus_count, modes,
                               fixed, past_sets, freq, ohang, ohang_groups, recent, today)
            r["mode"] = "+".join(modes)
        results.append(r)
    return results


def _combined_weights(candidates, modes, freq, ohang, ohang_groups) -> list:
    """각 방식의 가중치를 곱해 통합 점수 산출
    (lucky는 가중치가 아니라 1개 보장 포함 방식이므로 여기서는 다루지 않음)"""
    weights = []
    ohang_nums = set(ohang_groups.get(ohang, [])) if ohang else set()

    for n in candidates:
        w = 1.0
        if "frequency" in modes:
            w *= (freq.get(n, 0) + 0.001) * 1000
        if "saju" in modes:
            w *= 3.0 if n in ohang_nums else 1.0
        if "random" in modes:
            w *= 1.0
        weights.append(w)
    return weights


def _pick_combined(max_n, pick, bonus_count, modes,
                   fixed, past_sets, freq, ohang, ohang_groups, recent, today) -> dict:
    pool = list(range(1, max_n + 1))
    retries = 0

    # lucky가 조합에 포함된 경우: 최근 3회차 출현 번호 중 1개를 100% 보장 포함
    # (가중치 방식이 아니라 "딱 1개만" 포함하는 방식 — 다른 모드와 조합해도 동일)
    # lucky가 없는 조합: 기존처럼 40% 확률로 1개만 간헐적으로 포함
    lucky_num = None
    if "lucky" in modes:
        if recent:
            cand_lucky = [n for n in set(recent) if n not in fixed]
            if cand_lucky and len(fixed) < pick:
                lucky_num = random.choice(cand_lucky)
    elif recent and random.random() < RECENT_NUM_PROB:
        cand_lucky = [n for n in set(recent) if n not in fixed]
        if cand_lucky and len(fixed) < pick - 1:
            lucky_num = random.choice(cand_lucky)

    effective_fixed = list(fixed)
    if lucky_num and lucky_num not in effective_fixed:
        effective_fixed.append(lucky_num)

    while True:
        need = pick - len(effective_fixed)
        candidates = [n for n in pool if n not in effective_fixed]
        weights = _combined_weights(candidates, modes, freq, ohang, ohang_groups)
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
                                    ohang, freq, ohang_groups, retries - 1, max_n, today)
    return {"numbers": nums, "bonus": bonus, "reason": reason}


def _build_combined_reason(nums, modes, fixed, lucky_num, ohang, freq,
                            ohang_groups, retries, max_n, today) -> list:
    reasons = []
    if fixed:
        reasons.append(f"고정 번호 {fixed} 포함")

    if "lucky" in modes:
        if lucky_num:
            reasons.append(f"🍀 행운 번호 {lucky_num}번 포함 — 최근 3회차 출현 번호 중 1개만 선택")
        else:
            reasons.append("🍀 행운 번호 — 최근 회차 데이터가 없어 다른 방식으로 대체")
    elif lucky_num:
        reasons.append(f"이전 회차 당첨 번호 {lucky_num} 포함 (행운 적용)")

    if "frequency" in modes and freq:
        top_nums = {n for n, _ in sorted(freq.items(), key=lambda x: -x[1])[:10]}
        hot = [n for n in nums if n in top_nums]
        if hot:
            pcts_str = ", ".join(f"{n}번({round(freq[n]*100,1)}%)" for n in hot)
            reasons.append(f"고빈도 기여: {pcts_str}")

    if "saju" in modes and ohang:
        ohang_ko = _OHANG_KO.get(ohang, ohang)
        cg = _lunar_cheongan(today)
        ohang_nums = [n for n in nums if n in ohang_groups.get(ohang, [])]
        reasons.append(f"오행 기여 — 오늘 일진: {cg}일 → {ohang_ko}")
        if ohang_nums:
            reasons.append(f"오행 해당 번호: {ohang_nums}")

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

    # lucky 모드: 최근 3회차 출현 번호 중 1개를 100% 보장 포함 (그 이상은 가중치 적용 안 함)
    # 그 외 모드: 40% 확률로 1개만 간헐적으로 포함
    lucky_num = None
    if mode == "lucky":
        if recent:
            cand_lucky = [n for n in set(recent) if n not in fixed]
            if cand_lucky and len(fixed) < pick:
                lucky_num = random.choice(cand_lucky)
    elif recent and random.random() < RECENT_NUM_PROB:
        cand_lucky = [n for n in set(recent) if n not in fixed]
        if cand_lucky and len(fixed) < pick - 1:
            lucky_num = random.choice(cand_lucky)

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
        # random / lucky(행운 번호 1개는 이미 fixed에 보장 포함됨) — 나머지는 순수 무작위
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

    if mode == "lucky":
        if lucky_num:
            reasons.append(f"🍀 행운 번호 {lucky_num}번 포함 — 최근 3회차 출현 번호 중 1개만 선택")
            reasons.append("나머지 번호는 순수 무작위 추출")
        else:
            reasons.append("최근 회차 데이터가 없어 전체 무작위로 추출")

    else:
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
