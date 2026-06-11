"""
당첨 번호 데이터 관리
- 파일 캐시 없음 (Vercel 서버리스 환경 대응)
- 모듈 레벨 메모리 캐시 (warm Lambda 재사용)
- lottolyzer.com 실시간 스크래핑 (requests 라이브러리)
"""

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from datetime import date, datetime, timedelta

import requests as _req
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Referer": "https://lottolyzer.com/",
}

LYZER_URLS = {
    "loto6":    "https://en.lottolyzer.com/history/japan/lotto-6/page/{page}/per-page/50/summary-view",
    "loto7":    "https://en.lottolyzer.com/history/japan/lotto-7/page/{page}/per-page/50/summary-view",
    "miniloto": "https://en.lottolyzer.com/history/japan/mini-loto/page/{page}/per-page/50/summary-view",
}

BONUS_COUNTS = {"loto6": 1, "loto7": 2, "miniloto": 1}

# 실제 당첨 번호 (스크래핑 실패 시 표시)
FALLBACK_DATA = {
    "loto6": [
        {"round": "2108", "date": "2026-06-04", "numbers": [2,  5, 10, 15, 28, 43], "bonus": [27]},
        {"round": "2107", "date": "2026-06-01", "numbers": [5,  8, 27, 32, 36, 39], "bonus": [38]},
        {"round": "2106", "date": "2026-05-28", "numbers": [1,  6, 17, 27, 34, 43], "bonus": [24]},
        {"round": "2105", "date": "2026-05-25", "numbers": [5, 26, 28, 30, 36, 40], "bonus": [32]},
        {"round": "2104", "date": "2026-05-21", "numbers": [18, 19, 21, 25, 28, 34], "bonus": [4]},
        {"round": "2103", "date": "2026-05-18", "numbers": [1,  2,  4,  5,  8, 38], "bonus": [39]},
        {"round": "2102", "date": "2026-05-14", "numbers": [18, 21, 25, 28, 30, 43], "bonus": [8]},
    ],
    "loto7": [
        {"round": "680", "date": "2026-06-05", "numbers": [9, 10, 22, 26, 27, 31, 36], "bonus": [20, 29]},
        {"round": "679", "date": "2026-05-29", "numbers": [3, 12, 18, 21, 25, 30, 35], "bonus": [8,  17]},
        {"round": "678", "date": "2026-05-22", "numbers": [4,  7, 15, 19, 23, 28, 33], "bonus": [11, 24]},
        {"round": "677", "date": "2026-05-15", "numbers": [1,  8, 14, 20, 26, 32, 37], "bonus": [6,  16]},
        {"round": "676", "date": "2026-05-08", "numbers": [2,  9, 16, 22, 28, 33, 36], "bonus": [13, 25]},
    ],
    "miniloto": [
        {"round": "1389", "date": "2026-06-02", "numbers": [5, 10, 12, 29, 30], "bonus": [20]},
        {"round": "1388", "date": "2026-05-26", "numbers": [1, 12, 16, 22, 23], "bonus": [21]},
        {"round": "1387", "date": "2026-05-19", "numbers": [1, 10, 17, 20, 31], "bonus": [23]},
        {"round": "1386", "date": "2026-05-12", "numbers": [12, 21, 25, 27, 31], "bonus": [28]},
        {"round": "1385", "date": "2026-05-05", "numbers": [1, 10, 21, 28, 31], "bonus": [11]},
    ],
}

# 모듈 레벨 메모리 캐시 (warm Lambda에서 재사용)
_mem: dict = {}


def _fetch_page(ltype: str, page: int) -> list:
    url = LYZER_URLS[ltype].format(page=page)
    try:
        resp = _req.get(url, headers=HEADERS, timeout=7, verify=False)
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table")
        if not table:
            return []

        results = []
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 4:
                continue
            round_no = cells[0].get_text(strip=True)
            if not round_no.isdigit():
                continue
            date      = cells[1].get_text(strip=True)
            nums_raw  = cells[2].get_text(strip=True)
            bonus_raw = cells[3].get_text(strip=True)

            nums  = sorted([int(n) for n in nums_raw.split(",")  if n.strip().isdigit()])
            bonus = sorted([int(n) for n in bonus_raw.split(",") if n.strip().isdigit()])
            if nums:
                results.append({"round": round_no, "date": date, "numbers": nums, "bonus": bonus})
        return results
    except Exception:
        return []


def _get_cached(ltype: str, pages: int = 2) -> list:
    """메모리 캐시 우선, 없으면 최근 pages페이지 스크래핑"""
    if ltype in _mem:
        return _mem[ltype]
    rows = []
    for p in range(1, pages + 1):
        page_data = _fetch_page(ltype, p)
        rows.extend(page_data)
        if len(page_data) < 50:
            break
    if rows:
        _mem[ltype] = rows
    return rows or FALLBACK_DATA.get(ltype, [])


def get_results(ltype: str, page: int = 1, per_page: int = 50) -> dict:
    """페이지네이션 결과 반환 — 요청 페이지 실시간 스크래핑"""
    rows = _fetch_page(ltype, page)
    if rows:
        has_next = len(rows) >= 50
        return {
            "results": rows,
            "total": None,
            "page": page,
            "per_page": per_page,
            "total_pages": page + 1 if has_next else page,
            "source": "live",
        }
    fallback = FALLBACK_DATA.get(ltype, [])
    return {
        "results": fallback,
        "total": len(fallback),
        "page": 1,
        "per_page": per_page,
        "total_pages": 1,
        "source": "sample",
    }


def get_history(ltype: str) -> list:
    """추천 엔진용 이력 데이터 (메모리 캐시)"""
    return _get_cached(ltype, pages=2)


# ── 추첨 일정 ──────────────────────────────────────
# weekday(): 월=0, 화=1, 수=2, 목=3, 금=4, 토=5, 일=6
DRAW_WEEKDAYS = {
    "loto6":    (0, 3),   # 月曜・木曜
    "loto7":    (4,),     # 金曜
    "miniloto": (1,),     # 火曜
}
_KO_WEEKDAY = ["월", "화", "수", "목", "금", "토", "일"]


def _parse_date(s: str):
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%d-%b-%Y", "%d %b %Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except (ValueError, AttributeError):
            continue
    return None


def _next_weekday(after: date, weekdays: tuple) -> date | None:
    """`after` 다음 날부터 가장 가까운 추첨 요일을 반환"""
    d = after + timedelta(days=1)
    for _ in range(14):
        if d.weekday() in weekdays:
            return d
        d += timedelta(days=1)
    return None


def get_next_draw(ltype: str) -> dict | None:
    """이번에 응모하는(다음) 회차 번호와 추첨·발표일을 계산.

    일본 로또는 추첨일 저녁에 당첨 번호가 발표되므로 추첨일 = 당첨 발표일.
    최신 당첨 회차 +1 을 다음 응모 회차로, 최신 추첨일 이후 첫 추첨 요일을
    다음 추첨일로 본다.
    """
    weekdays = DRAW_WEEKDAYS.get(ltype)
    if not weekdays:
        return None

    rows = get_history(ltype) or FALLBACK_DATA.get(ltype, [])
    if not rows:
        return None

    latest = max(
        rows,
        key=lambda r: int(r["round"]) if str(r.get("round", "")).isdigit() else -1,
    )
    if not str(latest.get("round", "")).isdigit():
        return None
    next_round = int(latest["round"]) + 1

    base = _parse_date(latest.get("date", "")) or (date.today() - timedelta(days=1))
    draw_dt = _next_weekday(base, weekdays)

    return {
        "round": next_round,
        "draw_date": draw_dt.isoformat() if draw_dt else None,
        "weekday": _KO_WEEKDAY[draw_dt.weekday()] if draw_dt else None,
        "after_round": latest["round"],
        "after_date": latest.get("date"),
    }
