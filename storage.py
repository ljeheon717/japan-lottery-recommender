"""
구매 기록 저장소 (SQLite)
- 로컬 실행: 프로젝트 루트의 purchases.db 파일에 저장 (영구 보존)
- Vercel 서버리스: 파일시스템이 읽기 전용이므로 /tmp 에 저장 (인스턴스 재시작 시 초기화됨)
"""

import json
import os
import sqlite3

if os.environ.get("VERCEL"):
    DB_PATH = "/tmp/purchases.db"
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "purchases.db")


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ltype TEXT NOT NULL,
            round TEXT NOT NULL,
            numbers TEXT NOT NULL,
            match_count INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    return conn


def _row_to_dict(row) -> dict:
    return {
        "id": row[0],
        "ltype": row[1],
        "round": row[2],
        "numbers": json.loads(row[3]),
        "match_count": row[4],
        "created_at": row[5],
    }


def add_purchase(ltype: str, round_no: str, numbers: list, match_count) -> dict:
    conn = _conn()
    try:
        cur = conn.execute(
            "INSERT INTO purchases (ltype, round, numbers, match_count) VALUES (?, ?, ?, ?)",
            (ltype, round_no, json.dumps(numbers), match_count),
        )
        conn.commit()
        row = conn.execute(
            "SELECT id, ltype, round, numbers, match_count, created_at "
            "FROM purchases WHERE id = ?",
            (cur.lastrowid,),
        ).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def list_purchases(ltype: str) -> list:
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT id, ltype, round, numbers, match_count, created_at "
            "FROM purchases WHERE ltype = ? ORDER BY id DESC",
            (ltype,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_purchases_by_ids(ltype: str, ids: list) -> list:
    ids = [i for i in ids if isinstance(i, int)]
    if not ids:
        return []
    conn = _conn()
    try:
        placeholders = ",".join("?" for _ in ids)
        rows = conn.execute(
            f"SELECT id, ltype, round, numbers, match_count, created_at "
            f"FROM purchases WHERE ltype = ? AND id IN ({placeholders})",
            [ltype, *ids],
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def delete_purchase(ltype: str, purchase_id: int) -> bool:
    conn = _conn()
    try:
        cur = conn.execute(
            "DELETE FROM purchases WHERE id = ? AND ltype = ?", (purchase_id, ltype)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()
