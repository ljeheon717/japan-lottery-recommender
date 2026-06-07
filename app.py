import os
from flask import Flask, jsonify, render_template, request
from datetime import date
from data import get_results, find_round
from recommender import recommend_multi
from storage import add_purchase, list_purchases, get_purchases_by_ids, delete_purchase

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)

LOTTERIES = {
    "loto6":    {"name": "ロト6",    "min": 1, "max": 43, "pick": 6, "bonus": 1},
    "loto7":    {"name": "ロト7",    "min": 1, "max": 37, "pick": 7, "bonus": 2},
    "miniloto": {"name": "ミニロト", "min": 1, "max": 31, "pick": 5, "bonus": 1},
}


@app.route("/")
def index():
    return render_template("index.html", lotteries=LOTTERIES)


@app.route("/api/generate/<ltype>/<int:count>", methods=["GET", "POST"])
def api_generate(ltype, count):
    if ltype not in LOTTERIES:
        return jsonify({"error": "Unknown lottery type"}), 400
    lot = LOTTERIES[ltype]
    count = min(max(count, 1), 10)

    body = request.get_json(silent=True) or {}
    modes = body.get("modes", ["random"])
    if not isinstance(modes, list) or not modes:
        modes = ["random"]

    fixed = []
    for v in body.get("fixed", []):
        try:
            n = int(v)
            if 1 <= n <= lot["max"]:
                fixed.append(n)
        except (ValueError, TypeError):
            pass

    mypick_pool = []
    if "mypick" in modes:
        purchase_ids = []
        for v in body.get("purchase_ids", []):
            try:
                purchase_ids.append(int(v))
            except (ValueError, TypeError):
                pass
        mypick_pool = get_purchases_by_ids(ltype, purchase_ids)

    results = recommend_multi(
        ltype=ltype,
        max_n=lot["max"],
        pick=lot["pick"],
        bonus_count=lot["bonus"],
        modes=modes,
        fixed=fixed,
        count=count,
        target_date=date.today(),
        mypick_pool=mypick_pool,
    )
    return jsonify({"results": results})


@app.route("/api/purchases", methods=["GET", "POST"])
def api_purchases():
    if request.method == "GET":
        ltype = request.args.get("ltype", "loto6")
        if ltype not in LOTTERIES:
            return jsonify({"error": "Unknown lottery type"}), 400
        return jsonify({"purchases": list_purchases(ltype)})

    body = request.get_json(silent=True) or {}
    ltype = body.get("ltype")
    round_no = str(body.get("round", "")).strip()
    if ltype not in LOTTERIES or not round_no:
        return jsonify({"error": "로또 종류와 회차를 입력해주세요"}), 400

    lot = LOTTERIES[ltype]
    numbers = []
    for v in body.get("numbers", []):
        try:
            n = int(v)
            if 1 <= n <= lot["max"] and n not in numbers:
                numbers.append(n)
        except (ValueError, TypeError):
            pass
    if len(numbers) != lot["pick"]:
        return jsonify({"error": f"{lot['pick']}개의 번호를 입력해주세요"}), 400
    numbers.sort()

    winning = find_round(ltype, round_no)
    match_count = len(set(numbers) & set(winning["numbers"])) if winning else None

    record = add_purchase(ltype, round_no, numbers, match_count)
    record["winning_numbers"] = winning["numbers"] if winning else None
    return jsonify(record)


@app.route("/api/purchases/<ltype>/<int:purchase_id>", methods=["DELETE"])
def api_delete_purchase(ltype, purchase_id):
    if ltype not in LOTTERIES:
        return jsonify({"error": "Unknown lottery type"}), 400
    if not delete_purchase(ltype, purchase_id):
        return jsonify({"error": "Not found"}), 404
    return jsonify({"ok": True})


@app.route("/api/results/<ltype>")
def api_results(ltype):
    if ltype not in LOTTERIES:
        return jsonify({"error": "Unknown lottery type"}), 400
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 50)), 100)
    return jsonify(get_results(ltype, page=page, per_page=per_page))


if __name__ == "__main__":
    app.run(debug=True, port=5001)
