import json
from dotenv import load_dotenv

load_dotenv()

APPLE_HEALTH_FILE = "data/apple_health_daily.json"
OUTPUT_FILE = "data/loseit_daily.json"

NUTRITION_MAP = {
    "calories":      "dietary_energy",
    "carbohydrates": "carbohydrates",
    "protein":       "protein",
    "total_fat":     "total_fat",
    "saturated_fat": "saturated_fat",
    "sugar":         "dietary_sugar",
    "fiber":         "fiber",
    "cholesterol":   "cholesterol",
    "sodium":        "sodium",
}


def parse_nutrition():
    try:
        with open(APPLE_HEALTH_FILE) as f:
            apple = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Apple Health data not found. Run apple_health.py first.")

    date = apple["date"]
    metrics = apple["metrics"]

    nutrition = {}
    for label, key in NUTRITION_MAP.items():
        m = metrics.get(key)
        if m and m.get("total") is not None:
            nutrition[label] = {"value": m["total"], "units": m["units"]}
        else:
            nutrition[label] = {"value": None, "units": None}

    loseit_data = {
        "date": date,
        "source": "Apple Health (Lose It! sync)",
        "nutrition": nutrition,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(loseit_data, f, indent=2)

    print("=" * 60)
    print(f"LOSE IT NUTRITION — {date}")
    print("=" * 60)
    n = nutrition
    print(f"  Calories:        {n['calories']['value']} kcal")
    print(f"  Carbohydrates:   {n['carbohydrates']['value']} g")
    print(f"  Protein:         {n['protein']['value']} g")
    print(f"  Total Fat:       {n['total_fat']['value']} g")
    print(f"    Saturated Fat: {n['saturated_fat']['value']} g")
    print(f"  Sugar:           {n['sugar']['value']} g")
    print(f"  Fiber:           {n['fiber']['value']} g")
    print(f"  Cholesterol:     {n['cholesterol']['value']} mg")
    print(f"  Sodium:          {n['sodium']['value']} mg")
    print("=" * 60)
    print(f"Saved nutrition to {OUTPUT_FILE}")

    return loseit_data


if __name__ == "__main__":
    parse_nutrition()
