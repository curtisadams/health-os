# health-os

A personal health data pipeline that pulls from multiple sources — WHOOP, Apple Health, and Lose It — normalizes everything into clean daily summaries, and lays the groundwork for unified health insights.

This is my first attempt at vibe coding — building something with AI tools end-to-end to see what's actually possible. The goal is simple: make something useful to me, learn how these tools work in practice, and figure out what I can build when I'm not limited by what I already know how to code.

## What it does

Most health apps keep your data siloed. This project connects them:

- **WHOOP** — pulls recovery score, HRV, resting heart rate, SpO2, sleep stages, strain, and calories via the WHOOP v2 API
- **Apple Health** — parses daily exports from the Health Auto Export app, capturing 30+ metrics including steps, active energy, heart rate, nutrition, and more
- **Lose It** *(in progress)* — nutrition and calorie tracking data
- **Daily summary** *(in progress)* — unified view across all sources for a given day

Each source writes to a clean JSON file in `data/` that can be consumed by downstream scripts, dashboards, or LLM-based health coaching tools.

## Project structure

```
health-os/
├── scripts/
│   ├── whoop.py           # Fetches and parses WHOOP recovery, sleep, and strain
│   ├── apple_health.py    # Parses Apple Health daily export JSON
│   ├── loseit.py          # Lose It nutrition data (in progress)
│   └── summary.py         # Unified daily summary (in progress)
├── data/
│   ├── whoop_daily.json        # Raw WHOOP API responses (all fields)
│   ├── whoop_summary.json      # Parsed WHOOP daily summary
│   └── apple_health_daily.json # Parsed Apple Health metrics
└── .env                   # API credentials and file paths (not committed)
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

Early stage — data collection and parsing is working for WHOOP and Apple Health. The next phase is building the unified daily summary and exploring how to surface insights from the combined data.
