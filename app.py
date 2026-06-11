import os
from flask import Flask, jsonify, render_template, request
from datetime import date
from data import get_results, get_next_draw
from recommender import recommend_multi

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)

LOTTERIES = {
    "loto6": {"name": "ロト6", "min": 1, "max": 43, "pick": 6, "bonus": 1},
    "loto7": {"name": "ロト7", "min": 1, "max": 37, "pick": 7, "bonus": 2},
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

    results = recommend_multi(
        ltype=ltype,
        max_n=lot["max"],
        pick=lot["pick"],
        bonus_count=lot["bonus"],
        modes=modes,
        fixed=fixed,
        count=count,
        target_date=date.today(),
    )
    return jsonify({"results": results, "draw": get_next_draw(ltype)})


@app.route("/api/results/<ltype>")
def api_results(ltype):
    if ltype not in LOTTERIES:
        return jsonify({"error": "Unknown lottery type"}), 400
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 50)), 100)
    return jsonify(get_results(ltype, page=page, per_page=per_page))


if __name__ == "__main__":
    app.run(debug=True, port=5001, use_reloader=False)
