"""
당첨 번호 데이터 관리
- 파일 캐시 없음 (Vercel 서버리스 환경 대응)
- 모듈 레벨 메모리 캐시 (warm Lambda 재사용)
- lottolyzer.com 실시간 스크래핑
"""

import re
import ssl
import urllib.request
from typing import Optional

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
}

LYZER_URLS = {
    "loto6":    "https://lottolyzer.com/history/japan/loto-6/page/{page}/per-page/50",
    "loto7":    "https://lottolyzer.com/history/japan/loto-7/page/{page}/per-page/50",
    "miniloto": "https://lottolyzer.com/history/japan/mini-loto/page/{page}/per-page/50",
}

BONUS_COUNTS = {"loto6": 1, "loto7": 2, "miniloto": 1}

FALLBACK_DATA = {
    "loto6": [
        {"round": "2109", "date": "2026-06-07", "numbers": [3, 11, 18, 26, 35, 42], "bonus": [20]},
        {"round": "2108", "date": "2026-06-04", "numbers": [2, 5, 10, 15, 28, 43], "bonus": [27]},
        {"round": "2107", "date": "2026-06-01", "numbers": [5, 8, 27, 32, 36, 39], "bonus": [38]},
        {"round": "2106", "date": "2026-05-28", "numbers": [1, 6, 17, 27, 34, 43], "bonus": [24]},
        {"round": "2105", "date": "2026-05-25", "numbers": [3, 12, 19, 24, 32, 41], "bonus": [8]},
    ],
    "loto7": [
        {"round": "701", "date": "2026-06-06", "numbers": [4, 9, 15, 20, 26, 32, 37], "bonus": [12, 23]},
        {"round": "700", "date": "2026-05-30", "numbers": [3, 8, 14, 19, 25, 31, 37], "bonus": [11, 22]},
        {"round": "699", "date": "2026-05-23", "numbers": [2, 9, 15, 20, 26, 32, 36], "bonus": [7, 18]},
        {"round": "698", "date": "2026-05-16", "numbers": [4, 10, 16, 21, 27, 33, 35], "bonus": [13, 24]},
        {"round": "697", "date": "2026-05-09", "numbers": [1, 6, 12, 17, 23, 29, 34], "bonus": [9, 20]},
    ],
    "miniloto": [
        {"round": "1306", "date": "2026-06-03", "numbers": [4, 11, 18, 25, 30], "bonus": [9]},
        {"round": "1305", "date": "2026-05-27", "numbers": [3, 10, 17, 24, 29], "bonus": [8]},
        {"round": "1304", "date": "2026-05-20", "numbers": [5, 12, 19, 22, 31], "bonus": [14]},
        {"round": "1303", "date": "2026-05-13", "numbers": [2, 9, 15, 21, 28], "bonus": [6]},
        {"round": "1302", "date": "2026-05-06", "numbers": [7, 13, 18, 25, 30], "bonus": [11]},
    ],
}

# 모듈 레벨 메모리 캐시 (warm Lambda에서 재사용)
_mem: dict = {}


def _fetch_page(ltype: str, page: int) -> list:
    from bs4 import BeautifulSoup
    url = LYZER_URLS[ltype].format(page=page)
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        r = urllib.request.urlopen(req, timeout=8, context=_SSL_CTX)
        soup = BeautifulSoup(r.read().decode("utf-8", errors="replace"), "html.parser")
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
            date = cells[1].get_text(strip=True)
            nums_raw = cells[2].get_text(strip=True)
            bonus_raw = cells[3].get_text(strip=True)

            nums = sorted([int(n) for n in nums_raw.split(",") if n.strip().isdigit()])
            bonus = sorted([int(n) for n in bonus_raw.split(",") if n.strip().isdigit()])
            if nums:
                results.append({"round": round_no, "date": date,
                                 "numbers": nums, "bonus": bonus})
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
