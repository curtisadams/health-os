# health-os

A personal health data pipeline that pulls from multiple sources — WHOOP, Apple Health, and Lose It — normalizes everything into clean daily summaries, and lays the groundwork for unified health insights.

This is my first attempt at vibe coding — building something with AI tools end-to-end to see what's actually possible. The goal is simple: make something useful to me, learn how these tools work in practice, and figure out what I can build when I'm not limited by what I already know how to code.

## What it does

Most health apps keep your data siloed. This project connects them:

- **WHOOP** — pulls recovery score, HRV, resting heart rate, SpO2, sleep stages, strain, and calories via the WHOOP v2 API
- **Apple Health** — parses daily exports from the Health Auto Export app, capturing 30+ metrics including steps, active energy, heart rate, and more
- **Lose It** — nutrition data (calories, macros, fiber, sodium, cholesterol) extracted from Apple Health where it syncs automatically
- **Daily summary** — unified view across all sources printed to terminal and saved to JSON

Run the whole pipeline with a single command:

```bash
python3 run.py
```

Each source writes to a clean JSON file in `data/` that can be consumed by downstream scripts, dashboards, or LLM-based health coaching tools.

## Project structure

```
health-os/
├── run.py                       # Single entrypoint — runs the full pipeline
├── scripts/
│   ├── whoop.py                 # Fetches and parses WHOOP recovery, sleep, and strain
│   ├── apple_health.py          # Parses Apple Health daily export JSON
│   ├── loseit.py                # Extracts nutrition data from Apple Health
│   └── summary.py               # Unified daily summary across all sources
├── data/
│   ├── whoop_daily.json         # Raw WHOOP API responses (all fields)
│   ├── whoop_summary.json       # Parsed WHOOP daily summary
│   ├── apple_health_daily.json  # Parsed Apple Health metrics (30+ fields)
│   ├── loseit_daily.json        # Nutrition summary
│   └── daily_summary.json       # Unified daily summary across all sources
└── .env                         # API credentials and file paths (not committed)
```

## Data sources

| Source | Method | Cadence |
|---|---|---|
| WHOOP | OAuth2 API (v2) | On demand |
| Apple Health | Health Auto Export → iCloud JSON | Daily |
| Lose It | TBD | TBD |

## Setup

1. Clone the repo and create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install requests python-dotenv
   ```

2. Copy `.env.example` to `.env` and fill in your credentials:
   ```
   WHOOP_CLIENT_ID=...
   WHOOP_CLIENT_SECRET=...
   WHOOP_REDIRECT_URI=http://localhost:8080/callback
   HEALTH_EXPORT_PATH=/path/to/Health Auto Export/Health_daily
   ```

3. Authenticate with WHOOP (one-time OAuth flow), then run:
   ```bash
   python3 scripts/whoop.py
   python3 scripts/apple_health.py
   ```

## Status

The core pipeline is complete. All four scripts run end-to-end with `python3 run.py`. The next phase is doing something interesting with the data — trends over time, LLM-based daily coaching, or a simple dashboard.
