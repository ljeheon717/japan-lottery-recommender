# 🎰 日本ロット 番号推薦 (Japan Lottery Recommender)

[한국어](README.md) | [English](README.en.md) | [日本語](README.ja.md)

A web application for generating number recommendations and looking up winning numbers for Japanese lotteries (ロト6 / ロト7 / ミニロト).

**Demo → [Vercel deployment URL]**

---

## Key Features

### Number Recommendation
| Feature | Description |
|------|------|
| 🎲 **Random** | Pure random selection |
| 📊 **Frequency-based** | Weights numbers by how often they have appeared in the full winning history |
| ☯️ **Five Elements (Saju)-based** | Determines the Five Elements (木火土金水) from today's lunar day stem (天干) and prioritizes the corresponding number group |
| 🗂️ **My Number Combo** | Builds combinations from numbers in your saved purchase records; numbers from losing combinations (zero matches with the winning numbers) get a higher weight and are prioritized |
| 🔀 **Multi-mode combination** | When multiple modes are selected, their weights are combined to produce optimal numbers |
| 📌 **Fixed numbers** | Manually specify up to 3 numbers to always include |
| 🔒 **Exclude past winning combinations** | Combinations that have already won are automatically excluded and regenerated |
| 🍀 **Lucky number** | 40% chance to automatically include one number from the last 3 draws |
| 💬 **Recommendation reasoning** | Displays a detailed explanation of the basis for each set's number selection |

### My Purchase Records
- Save records of which round you played and which numbers you bought (stored in a server-side SQLite DB)
- Automatically looks up the winning numbers for that round and shows a "lost" / "matched" badge with the match count
- Select saved records to use as the number pool for the "My Number Combo" recommendation mode

### Winning Number Lookup
- Real-time lookup of recent winning numbers for ロト6 / ロト7 / ミニロト
- Browse past draws via pagination
- Data source: [lottolyzer.com](https://lottolyzer.com)

---

## Tech Stack

| Category | Technology |
|------|------|
| Backend | Python 3.9+, Flask |
| Frontend | Vanilla JS, HTML5, CSS3 |
| Scraping | BeautifulSoup4, urllib |
| Deployment | Vercel (Serverless Python) |

---

## System Architecture

```
Browser
  │
  ├── GET /                              → Renders index.html
  ├── POST /api/generate                 → Number recommendation (recommender.py)
  ├── GET /api/results                   → Winning number lookup (data.py → scrapes lottolyzer.com)
  └── GET·POST·DELETE /api/purchases     → Manage purchase records (storage.py → SQLite)

recommender.py
  ├── random mode: random.sample()
  ├── frequency mode: weighted sampling based on appearance frequency
  ├── saju mode: day stem → prioritizes the corresponding Five Elements group
  ├── mypick mode: samples from selected purchase records' number pool, with extra weight for losing combinations
  └── multi-mode: combines (multiplies) weights from each mode → integrated sampling

data.py
  ├── get_results()  : real-time scraping per page
  ├── get_history()  : history for the recommendation engine (in-memory cache)
  └── find_round()   : looks up the winning numbers for a specific round (used to grade purchase records)

storage.py
  └── SQLite-backed CRUD for purchase records (add_purchase / list_purchases / delete_purchase, etc.)
```

---

## File Structure

```
lotto/
├── api/
│   └── index.py          # Vercel serverless entry point
├── static/
│   ├── app.js            # Frontend logic
│   └── style.css         # Styles
├── templates/
│   └── index.html        # Single-page UI
├── app.py                # Flask app & routing
├── data.py               # Scraping & data management
├── recommender.py        # Number recommendation engine
├── storage.py            # SQLite-backed purchase record storage
├── vercel.json           # Vercel deployment config
├── requirements.txt
└── README.md
```

---

## API Specification

### `POST /api/generate/<ltype>/<count>`
Generate number recommendations

| Parameter | Location | Description |
|----------|------|------|
| `ltype` | path | `loto6` / `loto7` / `miniloto` |
| `count` | path | Number of sets to generate (1–10) |
| `modes` | body | Array of recommendation modes `["random","frequency","saju","mypick"]` |
| `fixed` | body | Array of fixed numbers (up to 3) |
| `purchase_ids` | body | When using `mypick` mode, an array of purchase record IDs to build the combination from |

**Example response**
```json
{
  "results": [
    {
      "numbers": [2, 14, 21, 26, 33, 40],
      "bonus": [18],
      "mode": "frequency+saju",
      "reason": [
        "High-frequency contribution: #26 (2.5%), #33 (2.4%)",
        "Five Elements contribution — today's day stem: 庚 → Metal (金)",
        "Numbers matching the Five Elements: [26, 33]"
      ]
    }
  ]
}
```

### `GET /api/results/<ltype>?page=1&per_page=50`
Look up winning numbers

| Parameter | Description |
|----------|------|
| `page` | Page number (default 1) |
| `per_page` | Number of results per page (default 50, max 100) |

### `GET /api/purchases?ltype=<ltype>`
List your purchase records (including the match count vs. the winning numbers for each round)

### `POST /api/purchases`
Add a purchase record — `{ "ltype", "round", "numbers" }`
Automatically looks up the winning numbers for the round and stores the computed match count (`match_count`)

### `DELETE /api/purchases/<ltype>/<id>`
Delete a purchase record

---

## Five Elements Logic Details

| Day Stem (天干) | Five Element | ロト6 number range |
|------|------|-----------------|
| 甲 乙 | Wood (木) | 1 – 8 |
| 丙 丁 | Fire (火) | 9 – 17 |
| 戊 己 | Earth (土) | 18 – 26 |
| 庚 辛 | Metal (金) | 27 – 34 |
| 壬 癸 | Water (水) | 35 – 43 |

> Day stem calculation basis: number of elapsed days from 1984-02-02 (甲子日) mod 10

---

## Running Locally

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the server
python app.py

# 3. Access in your browser
http://localhost:5001
```

---

## Deploying to Vercel

```bash
# 1. Install the Vercel CLI
npm i -g vercel

# 2. Deploy from the project root
cd lotto
vercel

# 3. Subsequent updates
vercel --prod
```

> **Note:** The Vercel free plan has a 10-second function timeout.
> Winning number lookups scrape lottolyzer.com in real time, so the first load takes about 1–3 seconds.
> "My Purchase Records" are stored in SQLite (`purchases.db`) and persist permanently when run locally. However, Vercel's serverless filesystem is ephemeral (`/tmp`), so records are wiped whenever the instance restarts — to persist them in production you'd need an external DB such as Vercel Postgres.

---

## Lottery Type Rules

| Name | Number Range | Main Numbers | Bonus | Draw Day |
|------|-----------|--------|--------|--------|
| ロト6 | 1 – 43 | 6 | 1 | Mon · Thu |
| ロト7 | 1 – 37 | 7 | 2 | Fri |
| ミニロト | 1 – 31 | 5 | 1 | Tue |

---

## Disclaimer

This application was created for **entertainment purposes**.
The number recommendation algorithm does not guarantee winnings, and any lottery purchase should be made at your own discretion and responsibility.

---

*Built with Flask & Vercel*
