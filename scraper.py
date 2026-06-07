"""미즈호 은행 공식 사이트에서 당첨 번호 스크래핑"""

import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

URLS = {
    "loto6": "https://www.mizuhobank.co.jp/takarakuji/loto/loto6/index.html",
    "loto7": "https://www.mizuhobank.co.jp/takarakuji/loto/loto7/index.html",
    "miniloto": "https://www.mizuhobank.co.jp/takarakuji/loto/miniloto/index.html",
}


def _parse_numbers(cells) -> list[int]:
    nums = []
    for c in cells:
        t = c.get_text(strip=True)
        if t.isdigit():
            nums.append(int(t))
    return nums


def fetch_loto6(limit: int = 10) -> list[dict]:
    url = "https://www.mizuhobank.co.jp/takarakuji/loto/loto6/index.html"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.encoding = "utf-8"
        soup = BeautifulSoup(res.text, "html.parser")
        results = []
        table = soup.find("table", class_="typeTK")
        if not table:
            table = soup.find("table")
        if not table:
            return []
        rows = table.find_all("tr")[1:]
        for row in rows[:limit]:
            cells = row.find_all("td")
            if len(cells) < 8:
                continue
            round_no = cells[0].get_text(strip=True).replace("第", "").replace("回", "")
            date = cells[1].get_text(strip=True)
            nums = []
            for c in cells[2:8]:
                t = c.get_text(strip=True)
                if t.isdigit():
                    nums.append(int(t))
            bonus_text = cells[8].get_text(strip=True) if len(cells) > 8 else ""
            bonus = [int(bonus_text)] if bonus_text.isdigit() else []
            if nums:
                results.append(
                    {"round": round_no, "date": date, "numbers": nums, "bonus": bonus}
                )
        return results
    except Exception as e:
        return [{"error": str(e)}]


def fetch_loto7(limit: int = 10) -> list[dict]:
    url = "https://www.mizuhobank.co.jp/takarakuji/loto/loto7/index.html"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.encoding = "utf-8"
        soup = BeautifulSoup(res.text, "html.parser")
        results = []
        table = soup.find("table", class_="typeTK")
        if not table:
            table = soup.find("table")
        if not table:
            return []
        rows = table.find_all("tr")[1:]
        for row in rows[:limit]:
            cells = row.find_all("td")
            if len(cells) < 9:
                continue
            round_no = cells[0].get_text(strip=True).replace("第", "").replace("回", "")
            date = cells[1].get_text(strip=True)
            nums = []
            for c in cells[2:9]:
                t = c.get_text(strip=True)
                if t.isdigit():
                    nums.append(int(t))
            bonus = []
            for c in cells[9:11]:
                t = c.get_text(strip=True)
                if t.isdigit():
                    bonus.append(int(t))
            if nums:
                results.append(
                    {"round": round_no, "date": date, "numbers": nums, "bonus": bonus}
                )
        return results
    except Exception as e:
        return [{"error": str(e)}]


def fetch_miniloto(limit: int = 10) -> list[dict]:
    url = "https://www.mizuhobank.co.jp/takarakuji/loto/miniloto/index.html"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.encoding = "utf-8"
        soup = BeautifulSoup(res.text, "html.parser")
        results = []
        table = soup.find("table", class_="typeTK")
        if not table:
            table = soup.find("table")
        if not table:
            return []
        rows = table.find_all("tr")[1:]
        for row in rows[:limit]:
            cells = row.find_all("td")
            if len(cells) < 7:
                continue
            round_no = cells[0].get_text(strip=True).replace("第", "").replace("回", "")
            date = cells[1].get_text(strip=True)
            nums = []
            for c in cells[2:7]:
                t = c.get_text(strip=True)
                if t.isdigit():
                    nums.append(int(t))
            bonus_text = cells[7].get_text(strip=True) if len(cells) > 7 else ""
            bonus = [int(bonus_text)] if bonus_text.isdigit() else []
            if nums:
                results.append(
                    {"round": round_no, "date": date, "numbers": nums, "bonus": bonus}
                )
        return results
    except Exception as e:
        return [{"error": str(e)}]


FETCHERS = {
    "loto6": fetch_loto6,
    "loto7": fetch_loto7,
    "miniloto": fetch_miniloto,
}
