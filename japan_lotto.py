#!/usr/bin/env python3
"""日本ロット番号推薦プログラム / 일본 로또 번호 추천 프로그램"""

import random
import sys
from datetime import datetime

LOTTERIES = {
    "1": {
        "name": "ロト6 (Loto 6)",
        "min": 1,
        "max": 43,
        "pick": 6,
        "bonus": 1,
        "desc": "1~43에서 6개 선택",
    },
    "2": {
        "name": "ロト7 (Loto 7)",
        "min": 1,
        "max": 37,
        "pick": 7,
        "bonus": 2,
        "desc": "1~37에서 7개 선택",
    },
    "3": {
        "name": "ミニロト (Mini Loto)",
        "min": 1,
        "max": 31,
        "pick": 5,
        "bonus": 1,
        "desc": "1~31에서 5개 선택",
    },
}

BANNER = """
╔══════════════════════════════════════════╗
║   🎰  日本ロット 番号推薦  🎰             ║
║       일본 로또 번호 추천 프로그램        ║
╚══════════════════════════════════════════╝
"""

def pick_numbers(lottery: dict) -> tuple[list[int], list[int]]:
    pool = list(range(lottery["min"], lottery["max"] + 1))
    main = sorted(random.sample(pool, lottery["pick"]))
    remaining = [n for n in pool if n not in main]
    bonus = sorted(random.sample(remaining, lottery["bonus"]))
    return main, bonus

def format_numbers(numbers: list[int], width: int = 3) -> str:
    return "  ".join(f"{n:>{width}}" for n in numbers)

def display_result(lottery: dict, main: list[int], bonus: list[int], idx: int):
    w = len(str(lottery["max"]))
    print(f"  [{idx}]  본번호: {format_numbers(main, w)}   "
          f"보너스: {format_numbers(bonus, w)}")

def run():
    print(BANNER)
    print("로또 종류를 선택하세요:\n")
    for key, lot in LOTTERIES.items():
        print(f"  {key}. {lot['name']}  ({lot['desc']})")
    print("  0. 종료\n")

    while True:
        choice = input("선택 (0~3): ").strip()
        if choice == "0":
            print("\n행운을 빕니다! 幸運を祈ります！ 🍀\n")
            sys.exit(0)
        if choice in LOTTERIES:
            break
        print("  올바른 번호를 입력하세요.")

    lottery = LOTTERIES[choice]

    while True:
        try:
            count = int(input(f"\n몇 세트 생성할까요? (1~10): ").strip())
            if 1 <= count <= 10:
                break
        except ValueError:
            pass
        print("  1~10 사이의 숫자를 입력하세요.")

    seed_input = input("\n시드 고정? (엔터 = 랜덤, 숫자 입력 = 고정): ").strip()
    if seed_input.isdigit():
        random.seed(int(seed_input))
        print(f"  시드: {seed_input}")
    else:
        random.seed(datetime.now().microsecond)

    print(f"\n{'─'*50}")
    print(f"  {lottery['name']}  추천 번호  ({count}세트)")
    print(f"{'─'*50}")
    for i in range(1, count + 1):
        main, bonus = pick_numbers(lottery)
        display_result(lottery, main, bonus, i)
    print(f"{'─'*50}")
    print("\n  ※ 이 번호는 무작위로 생성된 것입니다.")
    print("  ※ 当選を保証するものではありません。\n")

if __name__ == "__main__":
    run()
