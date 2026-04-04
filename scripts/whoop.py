import os
import json
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("WHOOP_CLIENT_ID")
CLIENT_SECRET = os.getenv("WHOOP_CLIENT_SECRET")
REDIRECT_URI = os.getenv("WHOOP_REDIRECT_URI")

TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
API_BASE = "https://api.prod.whoop.com/developer/v2"
TOKENS_FILE = "data/whoop_tokens.json"

def load_tokens():
    with open(TOKENS_FILE) as f:
        return json.load(f)

def save_tokens(tokens):
    with open(TOKENS_FILE, "w") as f:
        json.dump(tokens, f, indent=2)

def refresh_access_token(refresh_token):
    response = requests.post(TOKEN_URL, data={
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    })
    tokens = response.json()
    if "access_token" in tokens:
        save_tokens(tokens)
        print("Tokens refreshed successfully.")
        return tokens
    else:
        print(f"Error refreshing tokens: {tokens}")
        return None

def get_headers():
    tokens = load_tokens()
    return {"Authorization": f"Bearer {tokens['access_token']}"}

def fetch(url):
    """GET a WHOOP API URL, auto-refreshing on 401. Returns parsed JSON or raises on error."""
    headers = get_headers()
    response = requests.get(url, headers=headers)
    if response.status_code == 401:
        print("Token expired, refreshing...")
        tokens = load_tokens()
        new_tokens = refresh_access_token(tokens["refresh_token"])
        if new_tokens:
            headers = get_headers()
            response = requests.get(url, headers=headers)
        else:
            raise RuntimeError("Token refresh failed.")
    if not response.ok:
        raise RuntimeError(f"Request to {url} failed [{response.status_code}]: {response.text}")
    if not response.text.strip():
        raise RuntimeError(f"Empty response from {url} [{response.status_code}]")
    return response.json()

def get_recovery():
    return fetch(f"{API_BASE}/recovery")

def get_sleep():
    return fetch(f"{API_BASE}/activity/sleep")

def get_strain():
    return fetch(f"{API_BASE}/cycle")

DATA_FILE = "data/whoop_daily.json"
SUMMARY_FILE = "data/whoop_summary.json"

def ms_to_hours_minutes(ms):
    total_minutes = ms // 60000
    return {"hours": total_minutes // 60, "minutes": total_minutes % 60}

def parse_daily_summary():
    with open(DATA_FILE) as f:
        data = json.load(f)

    r = data["recovery"]["records"][0]
    s = data["sleep"]["records"][0]
    c = data["strain"]["records"][0]

    stage = s["score"]["stage_summary"]
    sleep_duration_ms = stage["total_in_bed_time_milli"] - stage["total_awake_time_milli"]

    daily_summary = {
        "date": r["created_at"][:10],
        "recovery": {
            "recovery_score": r["score"]["recovery_score"],
            "resting_heart_rate": r["score"]["resting_heart_rate"],
            "hrv_rmssd_milli": r["score"]["hrv_rmssd_milli"],
            "spo2_percentage": r["score"]["spo2_percentage"],
            "skin_temp_celsius": r["score"]["skin_temp_celsius"],
        },
        "sleep": {
            "sleep_performance_percentage": s["score"]["sleep_performance_percentage"],
            "sleep_efficiency_percentage": s["score"]["sleep_efficiency_percentage"],
            "sleep_consistency_percentage": s["score"]["sleep_consistency_percentage"],
            "respiratory_rate": s["score"]["respiratory_rate"],
            "disturbance_count": stage["disturbance_count"],
            "total_sleep_duration": ms_to_hours_minutes(sleep_duration_ms),
            "total_rem_sleep": ms_to_hours_minutes(stage["total_rem_sleep_time_milli"]),
            "total_deep_sleep": ms_to_hours_minutes(stage["total_slow_wave_sleep_time_milli"]),
            "total_light_sleep": ms_to_hours_minutes(stage["total_light_sleep_time_milli"]),
        },
        "strain": {
            "strain_score": c["score"]["strain"],
            "average_heart_rate": c["score"]["average_heart_rate"],
            "max_heart_rate": c["score"]["max_heart_rate"],
            "calories_burned": round(c["score"]["kilojoule"] / 4.184),
        },
    }

    with open(SUMMARY_FILE, "w") as f:
        json.dump(daily_summary, f, indent=2)

    print("\n" + "=" * 60)
    print(f"WHOOP DAILY SUMMARY — {daily_summary['date']}")
    print("=" * 60)

    rec = daily_summary["recovery"]
    print("\n  RECOVERY")
    print(f"    Recovery Score:       {rec['recovery_score']}%")
    print(f"    Resting Heart Rate:   {rec['resting_heart_rate']} bpm")
    print(f"    HRV (RMSSD):          {rec['hrv_rmssd_milli']:.2f} ms")
    print(f"    SpO2:                 {rec['spo2_percentage']:.2f}%")
    print(f"    Skin Temp:            {rec['skin_temp_celsius']:.2f} °C")

    slp = daily_summary["sleep"]
    td = slp["total_sleep_duration"]
    rem = slp["total_rem_sleep"]
    deep = slp["total_deep_sleep"]
    light = slp["total_light_sleep"]
    print("\n  SLEEP")
    print(f"    Performance:          {slp['sleep_performance_percentage']}%")
    print(f"    Efficiency:           {slp['sleep_efficiency_percentage']:.1f}%")
    print(f"    Consistency:          {slp['sleep_consistency_percentage']}%")
    print(f"    Respiratory Rate:     {slp['respiratory_rate']:.2f} breaths/min")
    print(f"    Disturbances:         {slp['disturbance_count']}")
    print(f"    Total Sleep:          {td['hours']}h {td['minutes']}m")
    print(f"    REM Sleep:            {rem['hours']}h {rem['minutes']}m")
    print(f"    Deep Sleep:           {deep['hours']}h {deep['minutes']}m")
    print(f"    Light Sleep:          {light['hours']}h {light['minutes']}m")

    str_ = daily_summary["strain"]
    print("\n  STRAIN")
    print(f"    Strain Score:         {str_['strain_score']:.2f}")
    print(f"    Avg Heart Rate:       {str_['average_heart_rate']} bpm")
    print(f"    Max Heart Rate:       {str_['max_heart_rate']} bpm")
    print(f"    Calories Burned:      {str_['calories_burned']} kcal")

    print("\n" + "=" * 60)
    print(f"Saved summary to {SUMMARY_FILE}")

if __name__ == "__main__":
    print("Fetching WHOOP data...\n")

    recovery = get_recovery()
    sleep = get_sleep()
    strain = get_strain()

    whoop_data = {
        "recovery": recovery,
        "sleep": sleep,
        "strain": strain,
    }

    with open(DATA_FILE, "w") as f:
        json.dump(whoop_data, f, indent=2)
    print(f"Saved full WHOOP data to {DATA_FILE}\n")

    print("=" * 60)
    print("WHOOP DAILY DATA")
    print("=" * 60)
    for section, data in whoop_data.items():
        print(f"\n--- {section.upper()} ---")
        print(json.dumps(data, indent=2))
    print("\n" + "=" * 60)

    parse_daily_summary()