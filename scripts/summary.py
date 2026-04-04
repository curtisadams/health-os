import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

WHOOP_SUMMARY_FILE = "data/whoop_summary.json"
APPLE_HEALTH_FILE = "data/apple_health_daily.json"
LOSEIT_FILE = "data/loseit_daily.json"
OUTPUT_FILE = "data/daily_summary.json"

# Metrics from Apple Health where we want the total (cumulative)
CUMULATIVE_METRICS = {
    "step_count", "walking_running_distance", "active_energy",
    "basal_energy_burned", "apple_exercise_time", "apple_stand_hour",
}

# Metrics where we want the average (rates/levels)
AVERAGE_METRICS = {
    "resting_heart_rate", "heart_rate_variability", "blood_oxygen_saturation",
}


def load_json(path, label):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"  [WARNING] {label} not found at {path} — section omitted.")
        return None


def get_metric(metrics, key, use_average=False):
    m = metrics.get(key)
    if not m:
        return None
    return m["average"] if use_average else m["total"]


def build_summary():
    whoop = load_json(WHOOP_SUMMARY_FILE, "WHOOP summary")
    apple = load_json(APPLE_HEALTH_FILE, "Apple Health data")
    loseit = load_json(LOSEIT_FILE, "Lose It nutrition")

    # Determine date and warn on mismatch
    dates = {k: v["date"] for k, v in [("whoop", whoop), ("apple", apple), ("loseit", loseit)] if v}
    unique_dates = set(dates.values())
    if len(unique_dates) > 1:
        print(f"  [WARNING] Date mismatch across sources: {dates}")
    date = next(iter(dates.values())) if dates else datetime.now().strftime("%Y-%m-%d")

    # --- Recovery & Sleep & Strain from WHOOP ---
    recovery = whoop["recovery"] if whoop else None
    sleep = whoop["sleep"] if whoop else None
    strain = whoop["strain"] if whoop else None

    # --- Activity from Apple Health ---
    activity = None
    if apple:
        m = apple["metrics"]
        activity = {
            "steps": round(get_metric(m, "step_count") or 0),
            "distance_miles": round(get_metric(m, "walking_running_distance") or 0, 2),
            "active_energy_kcal": round(get_metric(m, "active_energy") or 0, 1),
            "basal_energy_kcal": round(get_metric(m, "basal_energy_burned") or 0, 1),
            "exercise_minutes": round(get_metric(m, "apple_exercise_time") or 0),
            "stand_hours": round(get_metric(m, "apple_stand_hour") or 0),
            "resting_heart_rate_bpm": get_metric(m, "resting_heart_rate", use_average=True),
            "hrv_ms": get_metric(m, "heart_rate_variability", use_average=True),
            "spo2_pct": get_metric(m, "blood_oxygen_saturation", use_average=True),
        }

    # --- Nutrition from Lose It ---
    nutrition = loseit["nutrition"] if loseit else None

    # --- Derived ---
    derived = None
    if activity and nutrition and nutrition["calories"]["value"] is not None:
        cal_in = nutrition["calories"]["value"]
        active = activity["active_energy_kcal"]
        basal = activity["basal_energy_kcal"]
        net = round(cal_in - active - basal)
        derived = {
            "net_calories_estimated": net,
            "net_calories_note": "dietary_energy - active_energy - basal_energy (basal and WHOOP calories may overlap)",
        }

    daily_summary = {
        "date": date,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "sources": {
            "whoop": WHOOP_SUMMARY_FILE,
            "apple_health": APPLE_HEALTH_FILE,
            "loseit": LOSEIT_FILE,
        },
        "recovery": recovery,
        "sleep": sleep,
        "strain": strain,
        "activity": activity,
        "nutrition": nutrition,
        "derived": derived,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(daily_summary, f, indent=2)

    print_summary(daily_summary)
    print(f"Saved summary to {OUTPUT_FILE}")

    return daily_summary


def fmt(val, decimals=0):
    if val is None:
        return "—"
    if decimals == 0:
        return f"{round(val):,}"
    return f"{round(val, decimals):,}"


def fmt_hm(hm):
    if not hm:
        return "—"
    return f"{hm['hours']}h {hm['minutes']}m"


def print_summary(s):
    print("\n" + "=" * 60)
    print(f"  DAILY HEALTH SUMMARY — {s['date']}")
    print("=" * 60)

    if s["recovery"]:
        r = s["recovery"]
        print(f"\n  RECOVERY (WHOOP)")
        print(f"    Recovery Score:       {fmt(r['recovery_score'])}%")
        print(f"    Resting Heart Rate:   {fmt(r['resting_heart_rate'])} bpm")
        print(f"    HRV (RMSSD):          {fmt(r['hrv_rmssd_milli'], 2)} ms")
        print(f"    SpO2:                 {fmt(r['spo2_percentage'], 2)}%")
        print(f"    Skin Temp:            {fmt(r['skin_temp_celsius'], 2)} °C")

    if s["sleep"]:
        sl = s["sleep"]
        print(f"\n  SLEEP (WHOOP)")
        print(f"    Performance:          {fmt(sl['sleep_performance_percentage'])}%  |  Consistency: {fmt(sl['sleep_consistency_percentage'])}%")
        print(f"    Efficiency:           {fmt(sl['sleep_efficiency_percentage'], 1)}%")
        print(f"    Total Sleep:          {fmt_hm(sl['total_sleep_duration'])}")
        print(f"    REM / Deep / Light:   {fmt_hm(sl['total_rem_sleep'])} / {fmt_hm(sl['total_deep_sleep'])} / {fmt_hm(sl['total_light_sleep'])}")
        print(f"    Respiratory Rate:     {fmt(sl['respiratory_rate'], 2)} breaths/min")
        print(f"    Disturbances:         {sl['disturbance_count']}")

    if s["strain"]:
        st = s["strain"]
        print(f"\n  STRAIN (WHOOP)")
        print(f"    Strain Score:         {fmt(st['strain_score'], 2)} / 21")
        print(f"    Avg / Max HR:         {fmt(st['average_heart_rate'])} / {fmt(st['max_heart_rate'])} bpm")
        print(f"    Calories Burned:      {fmt(st['calories_burned'])} kcal")

    if s["activity"]:
        a = s["activity"]
        print(f"\n  ACTIVITY (APPLE HEALTH)")
        print(f"    Steps:                {fmt(a['steps'])}")
        print(f"    Distance:             {fmt(a['distance_miles'], 2)} mi")
        print(f"    Active Energy:        {fmt(a['active_energy_kcal'])} kcal")
        print(f"    Basal Energy:         {fmt(a['basal_energy_kcal'])} kcal")
        print(f"    Exercise Time:        {fmt(a['exercise_minutes'])} min")
        print(f"    Stand Hours:          {fmt(a['stand_hours'])}")
        if a["resting_heart_rate_bpm"]:
            print(f"    Resting HR:           {fmt(a['resting_heart_rate_bpm'], 1)} bpm")
        if a["hrv_ms"]:
            print(f"    HRV:                  {fmt(a['hrv_ms'], 1)} ms")
        if a["spo2_pct"]:
            print(f"    SpO2:                 {fmt(a['spo2_pct'], 1)}%")

    if s["nutrition"]:
        n = s["nutrition"]
        def nv(key, decimals=1):
            v = n.get(key, {}).get("value")
            return "—" if v is None else round(v, decimals)
        print(f"\n  NUTRITION (LOSE IT)")
        print(f"    Calories In:          {nv('calories', 0)} kcal")
        print(f"    Carbs / Protein / Fat: {nv('carbohydrates')}g / {nv('protein')}g / {nv('total_fat')}g")
        print(f"    Sugar:                {nv('sugar')}g   Fiber: {nv('fiber')}g")
        print(f"    Sodium:               {nv('sodium', 0)}mg   Cholesterol: {nv('cholesterol', 0)}mg")

    if s["derived"]:
        d = s["derived"]
        net = d["net_calories_estimated"]
        sign = "+" if net > 0 else ""
        print(f"\n  DERIVED")
        print(f"    Net Calories (est.):  {sign}{net:,} kcal")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    build_summary()
