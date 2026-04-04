import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

HEALTH_EXPORT_PATH = os.getenv("HEALTH_EXPORT_PATH")
OUTPUT_FILE = "data/apple_health_daily.json"


def load_export(date: str) -> dict:
    filename = f"HealthAutoExport-{date}.json"
    filepath = os.path.join(HEALTH_EXPORT_PATH, filename)
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"No export file found at: {filepath}")
    with open(filepath) as f:
        return json.load(f)


def parse_metrics(raw: dict) -> dict:
    metrics = {}
    for metric in raw["data"]["metrics"]:
        name = metric["name"]
        units = metric.get("units", "")
        data = metric.get("data", [])
        qty_values = [entry["qty"] for entry in data if "qty" in entry]
        metrics[name] = {
            "units": units,
            "data": data,
            "count": len(qty_values),
            "total": round(sum(qty_values), 4) if qty_values else None,
            "average": round(sum(qty_values) / len(qty_values), 4) if qty_values else None,
        }
    return metrics


def print_summary(date: str, metrics: dict):
    print("=" * 60)
    print(f"APPLE HEALTH SUMMARY — {date}")
    print(f"  {len(metrics)} metrics found")
    print("=" * 60)
    for name, m in sorted(metrics.items()):
        if m["count"] == 0:
            continue
        units = m["units"]
        total = m["total"]
        average = m["average"]
        count = m["count"]
        if count == 1:
            print(f"  {name}: {total} {units}")
        else:
            print(f"  {name}: total={total} {units}, avg={average} {units} ({count} readings)")
    print("=" * 60)


if __name__ == "__main__":
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"Parsing Apple Health export for {yesterday}...\n")

    raw = load_export(yesterday)
    metrics = parse_metrics(raw)

    output = {"date": yesterday, "metrics": metrics}

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Saved {len(metrics)} metrics to {OUTPUT_FILE}\n")

    print_summary(yesterday, metrics)
