"""
번호 추천 엔진
- random   : 순수 랜덤 (단독 전용)
- frequency: 전체 이력 빈도 가중치
- saju     : 음력 일진(천간) 오행 기반
- lucky    : 최근 3회차 출현 번호 중 1개를 행운 번호로 보장 포함, 나머지는 무작위
- oddeven  : 전체 이력 당첨 번호의 홀짝 비율을 분석해 가장 빈번한 비율로 구성
- exclude1 : 무작위로 한 번 추출한 번호를 후보에서 제외한 뒤 최종 추출
- exclude2 : 무작위 추출을 두 번 해서 나온 번호를 모두 제외한 뒤 최종 추출
공통: 과거 당첨 조합 항상 제외, 고정 번호
"""

import random
from collections import Counter
from datetime import date
from typing import Optional
from data import get_history, get_all_history, FALLBACK_DATA

# ── 오행 ──────────────────────────────────────────
_CHEONGAN = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
_OHANG_KO = {"木": "목(木)", "火": "화(火)", "土": "토(土)", "金": "금(金)", "水": "수(水)"}

RECENT_NUM_PROB    = 0.4   # 최근 회차 번호 1개 포함 확률 (단독 모드, lucky 이외)
LUCKY_COMBINED_PROB = 0.35  # 복수 모드 조합 시 행운 번호 포함 확률 (안 나와도 됨)


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
    # 전체 과거 회차를 대상으로 제외 (최근 회차 한정 아님)
    data = get_all_history(ltype) or FALLBACK_DATA.get(ltype, [])
    return {frozenset(row["numbers"]) for row in data}


def _calc_freq(ltype: str, max_n: int) -> dict:
    # 빈도는 전체 이력 기준
    data = get_all_history(ltype) or FALLBACK_DATA.get(ltype, [])
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


def _build_excluded(pool, fixed, pick, rounds) -> set:
    """rounds회만큼 pick개씩 무작위 추출해 나온 번호를 '제외 집합'으로 반환.
    - fixed(고정/행운) 번호는 추출 및 제외 대상에서 빼 항상 보존한다.
    - 최종 추출에 필요한 개수(need)는 항상 후보로 남기도록 제외량을 제한한다."""
    excluded = set()
    base = [n for n in pool if n not in fixed]
    need = pick - len(fixed)
    for _ in range(max(rounds, 0)):
        avail = [n for n in base if n not in excluded]
        room = len(avail) - need        # 최종 픽에 need개는 남겨야 함
        if room <= 0:
            break
        k = min(pick, room)
        excluded.update(random.sample(avail, k))
    return excluded


def _odd_even_ratio(ltype: str) -> Optional[tuple]:
    """전체 이력을 분석해 가장 빈번한 (홀수 개수, 짝수 개수) 비율 반환"""
    rows = get_all_history(ltype) or FALLBACK_DATA.get(ltype, [])
    if not rows:
        return None
    counter = Counter()
    for row in rows:
        nums = row["numbers"]
        odd = sum(1 for n in nums if n % 2 == 1)
        counter[(odd, len(nums) - odd)] += 1
    top = counter.most_common(1)
    return top[0][0] if top else None


def _pick_by_ratio(candidates, fixed, need, ratio) -> list:
    """목표 (홀수 개수, 짝수 개수) 비율에 최대한 맞춰 candidates에서 need개 선택
    (fixed에 이미 포함된 번호의 홀짝 구성도 비율 계산에 반영)"""
    target_odd, target_even = ratio
    fixed_odd = sum(1 for n in fixed if n % 2 == 1)

    need_odd  = max(0, min(need, target_odd - fixed_odd))
    need_even = need - need_odd

    odd_pool  = [n for n in candidates if n % 2 == 1]
    even_pool = [n for n in candidates if n % 2 == 0]
    n_odd  = min(need_odd, len(odd_pool))
    n_even = min(need_even, len(even_pool))

    chosen = random.sample(odd_pool, n_odd) + random.sample(even_pool, n_even)

    shortfall = need - len(chosen)
    if shortfall > 0:
        remaining = [n for n in candidates if n not in chosen]
        chosen += random.sample(remaining, shortfall)
    return chosen


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
    ratio = _odd_even_ratio(ltype)

    # 제외 추출은 세트별이 아니라 한 번만 수행 — 모든 세트가 같은 제외 번호를 공유
    exclude_rounds = 2 if "exclude2" in modes else (1 if "exclude1" in modes else 0)
    excluded = _build_excluded(list(range(1, max_n + 1)), fixed, pick, exclude_rounds) if exclude_rounds else set()

    results = []
    for _ in range(count):
        if len(modes) == 1:
            mode = modes[0]
            r = _pick_one(max_n, pick, bonus_count, mode,
                          fixed, past_sets, freq, ohang, ohang_groups, recent, ratio, today, excluded)
            r["mode"] = mode
        else:
            r = _pick_combined(max_n, pick, bonus_count, modes,
                               fixed, past_sets, freq, ohang, ohang_groups, recent, ratio, today, excluded)
            r["mode"] = "+".join(modes)
        results.append(r)
    return results


def _combined_weights(candidates, modes, freq, ohang, ohang_groups, ratio=None) -> list:
    """각 방식의 가중치를 합산해 통합 점수 산출.
    각 모드 기여분을 정규화 후 더하는 방식 — 특정 모드가 압도하지 않도록 밸런스 조정.
    (lucky는 가중치가 아니라 확률적 포함 방식이므로 여기서는 다루지 않음)"""
    import math

    avg_freq = (sum(freq.values()) / len(freq)) if freq else 0.02
    ohang_nums = set(ohang_groups.get(ohang, [])) if ohang else set()

    odd_bias = even_bias = 0.0
    if "oddeven" in modes and ratio:
        target_odd, target_even = ratio
        total = (target_odd + target_even) or 1
        odd_bias  = (target_odd  / total - 0.5) * 0.6   # ±0.3 범위
        even_bias = (target_even / total - 0.5) * 0.6

    # random/lucky/exclude* 는 가중치 점수에 기여하지 않으므로 평준화 분모에서 제외
    active = [m for m in modes if m not in ("random", "lucky", "exclude1", "exclude2")]
    n_active = max(len(active), 1)

    weights = []
    for n in candidates:
        score = 0.0
        if "frequency" in modes and freq:
            # 평균 빈도 대비 상대 비율 → −0.5 ~ +0.5 범위 정규화
            f = freq.get(n, avg_freq)
            score += max(-0.5, min(0.5, (f / avg_freq) - 1.0))
        if "saju" in modes:
            score += 0.5 if n in ohang_nums else -0.1
        if "oddeven" in modes and ratio:
            score += odd_bias if n % 2 == 1 else even_bias
        # 각 모드 수만큼 나눠 영향 평준화, 최솟값 0.2 보장
        w = max(0.2, 1.0 + score / n_active)
        weights.append(math.sqrt(w))   # sqrt 압축으로 극단값 완화
    return weights


def _pick_combined(max_n, pick, bonus_count, modes,
                   fixed, past_sets, freq, ohang, ohang_groups, recent, ratio, today,
                   excluded=None) -> dict:
    pool = list(range(1, max_n + 1))
    excluded = excluded or set()
    retries = 0

    # lucky가 조합에 포함된 경우: LUCKY_COMBINED_PROB 확률로만 포함 (안 나와도 됨)
    # lucky가 없는 조합: 기존처럼 RECENT_NUM_PROB 확률로 1개만 간헐적으로 포함
    # (제외 추출 번호는 행운 번호 후보에서도 빼서 제외 일관성 유지)
    lucky_num = None
    if "lucky" in modes:
        if recent and random.random() < LUCKY_COMBINED_PROB:
            cand_lucky = [n for n in set(recent) if n not in fixed and n not in excluded]
            if cand_lucky and len(fixed) < pick:
                lucky_num = random.choice(cand_lucky)
    elif recent and random.random() < RECENT_NUM_PROB:
        cand_lucky = [n for n in set(recent) if n not in fixed and n not in excluded]
        if cand_lucky and len(fixed) < pick - 1:
            lucky_num = random.choice(cand_lucky)

    effective_fixed = list(fixed)
    if lucky_num and lucky_num not in effective_fixed:
        effective_fixed.append(lucky_num)

    while True:
        need = pick - len(effective_fixed)
        candidates = [n for n in pool if n not in effective_fixed and n not in excluded]
        weights = _combined_weights(candidates, modes, freq, ohang, ohang_groups, ratio)
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
                                    ohang, freq, ohang_groups, ratio, retries - 1, max_n, today, excluded)
    return {"numbers": nums, "bonus": bonus, "reason": reason}


def _build_combined_reason(nums, modes, fixed, lucky_num, ohang, freq,
                            ohang_groups, ratio, retries, max_n, today, excluded=None) -> list:
    reasons = []
    if fixed:
        reasons.append(f"고정 번호 {fixed} 포함")

    if "exclude1" in modes or "exclude2" in modes:
        rounds = 2 if "exclude2" in modes else 1
        reasons.append(f"🚫 제외 추출 기여 — 무작위 {rounds}회 추출 번호를 후보에서 제외 후 구성")
        if excluded:
            reasons.append(f"제외된 번호: {sorted(excluded)}")

    if "lucky" in modes:
        if lucky_num:
            reasons.append(f"🍀 행운 번호 {lucky_num}번 포함 — 최근 3회차 출현 번호 중 1개 (약 35% 확률)")
        else:
            reasons.append("🍀 행운 번호 — 이번 조합엔 미포함 (다른 방식으로 균형 구성)")
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

    if "oddeven" in modes and ratio:
        odd_n  = sum(1 for n in nums if n % 2 == 1)
        even_n = len(nums) - odd_n
        reasons.append(f"⚖️ 홀짝 비율 기여 — 전체 이력 분석 결과 홀 {ratio[0]} : 짝 {ratio[1]} 비율이 가장 빈번 (이번 조합 — 홀 {odd_n} : 짝 {even_n})")

    if "random" in modes and len(modes) > 1:
        reasons.append("랜덤 가중치 포함")
    elif "random" in modes:
        reasons.append("순수 무작위 추출")

    if retries > 0:
        reasons.append(f"과거 당첨 조합 {retries}회 제외 후 선택")
    return reasons


def _pick_one(max_n, pick, bonus_count, mode,
              fixed, past_sets, freq, ohang, ohang_groups, recent, ratio, today,
              excluded=None) -> dict:
    pool = list(range(1, max_n + 1))
    excluded = excluded or set()
    retries = 0

    # lucky 모드: 최근 3회차 출현 번호 중 1개를 100% 보장 포함 (그 이상은 가중치 적용 안 함)
    # 그 외 모드: 40% 확률로 1개만 간헐적으로 포함
    # (제외 추출 번호는 행운 번호 후보에서도 빼서 제외 일관성 유지)
    lucky_num = None
    if mode == "lucky":
        if recent:
            cand_lucky = [n for n in set(recent) if n not in fixed and n not in excluded]
            if cand_lucky and len(fixed) < pick:
                lucky_num = random.choice(cand_lucky)
    elif recent and random.random() < RECENT_NUM_PROB:
        cand_lucky = [n for n in set(recent) if n not in fixed and n not in excluded]
        if cand_lucky and len(fixed) < pick - 1:
            lucky_num = random.choice(cand_lucky)

    effective_fixed = list(fixed)
    if lucky_num and lucky_num not in effective_fixed:
        effective_fixed.append(lucky_num)

    while True:
        nums = _sample(pool, pick, effective_fixed, mode, freq, ohang, ohang_groups, max_n, ratio, excluded)
        retries += 1
        if frozenset(nums) not in past_sets:
            break
        if retries > 1000:
            break

    remaining = [n for n in pool if n not in nums]
    bonus = sorted(random.sample(remaining, bonus_count))
    reason = _build_reason(nums, mode, fixed, lucky_num, ohang, freq, ratio, retries - 1, max_n, today, excluded)
    return {"numbers": nums, "bonus": bonus, "reason": reason}


def _sample(pool, pick, fixed, mode, freq, ohang, ohang_groups, max_n, ratio=None, excluded=None) -> list:
    excluded = excluded or set()
    need = pick - len(fixed)
    candidates = [n for n in pool if n not in fixed and n not in excluded]

    if mode == "frequency" and freq:
        weights = [freq.get(n, 0) + 0.001 for n in candidates]
        chosen = _weighted_sample(candidates, weights, need)

    elif mode == "saju" and ohang and ohang_groups:
        primary = [n for n in ohang_groups.get(ohang, []) if n not in fixed and n not in excluded]
        secondary = [n for n in candidates if n not in primary]
        n_primary = min(len(primary), need)
        chosen = random.sample(primary, n_primary)
        if n_primary < need:
            chosen += random.sample(secondary, need - n_primary)

    elif mode == "oddeven" and ratio:
        chosen = _pick_by_ratio(candidates, fixed, need, ratio)

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


def _build_reason(nums, mode, fixed, lucky_num, ohang, freq, ratio, retries, max_n, today, excluded=None) -> list:
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

        elif mode == "oddeven":
            if ratio:
                odd_n  = sum(1 for n in nums if n % 2 == 1)
                even_n = len(nums) - odd_n
                reasons.append(f"⚖️ 전체 이력 분석 — 홀수 {ratio[0]}개 : 짝수 {ratio[1]}개 비율이 가장 빈번")
                reasons.append(f"이 비율 기준으로 구성 (이번 조합 — 홀 {odd_n}개 : 짝 {even_n}개)")
            else:
                reasons.append("최근 회차 데이터가 없어 무작위로 추출")

        elif mode in ("exclude1", "exclude2"):
            rounds = 2 if mode == "exclude2" else 1
            reasons.append(f"🚫 제외 추출 — 무작위로 {rounds}회 추출한 번호를 후보에서 제외 후 최종 추출")
            if excluded:
                reasons.append(f"제외된 번호: {sorted(excluded)}")
            reasons.append("제외 후 남은 번호 중 무작위 추출")

        else:
            reasons.append("순수 무작위 추출")

    if retries > 0:
        reasons.append(f"과거 당첨 조합 {retries}회 제외 후 선택")

    return reasons
