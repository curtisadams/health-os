import os
import re
import base64
import json
import glob as glob_module
import subprocess
import sys
from datetime import datetime
from flask import Flask, render_template, jsonify, Response, request
import anthropic
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
client = anthropic.Anthropic()

SUMMARY_FILE = "data/daily_summary.json"
PROFILE_FILE = "data/profile.json"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_profile_context():
    """Return a formatted string describing the user, or empty string if no profile."""
    try:
        with open(os.path.join(BASE_DIR, PROFILE_FILE)) as f:
            p = json.load(f)
    except FileNotFoundError:
        return ""
    if not p:
        return ""
    lines = ["\nAbout the user:"]
    for key, label in [
        ("name", "Name"), ("age", "Age"), ("sex", "Biological sex"),
        ("height", "Height"), ("weight", "Weight"),
        ("goals", "Health goals"), ("conditions", "Medical conditions"),
        ("medications", "Medications"), ("supplements", "Supplements"),
        ("notes", "Additional context"),
    ]:
        val = p.get(key, "").strip() if isinstance(p.get(key), str) else str(p.get(key, ""))
        if val and val not in ("", "None", "null"):
            lines.append(f"- {label}: {val}")
    return "\n".join(lines) if len(lines) > 1 else ""


@app.route("/api/profile", methods=["GET"])
def profile_get():
    path = os.path.join(BASE_DIR, PROFILE_FILE)
    try:
        with open(path) as f:
            return jsonify(json.load(f))
    except FileNotFoundError:
        return jsonify({})


@app.route("/api/profile", methods=["POST"])
def profile_save():
    data = request.json
    path = os.path.join(BASE_DIR, PROFILE_FILE)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return jsonify({"ok": True})


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/summary")
def summary():
    date = request.args.get("date")
    if date:
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
            return jsonify({"error": "Invalid date format"}), 400
        path = os.path.join(BASE_DIR, "data", "summaries", f"{date}.json")
    else:
        path = os.path.join(BASE_DIR, SUMMARY_FILE)
    try:
        with open(path) as f:
            return jsonify(json.load(f))
    except FileNotFoundError:
        return jsonify({"error": "No data found. Run a sync first."}), 404


@app.route("/api/dates")
def dates():
    summaries_dir = os.path.join(BASE_DIR, "data", "summaries")
    if not os.path.isdir(summaries_dir):
        return jsonify([])
    files = glob_module.glob(os.path.join(summaries_dir, "????-??-??.json"))
    dates_list = sorted(
        [os.path.basename(f).replace(".json", "") for f in files],
        reverse=True,
    )
    return jsonify(dates_list)


@app.route("/api/sync", methods=["GET", "POST"])
def sync():
    def generate():
        process = subprocess.Popen(
            [sys.executable, "run.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=BASE_DIR,
        )
        for line in iter(process.stdout.readline, ""):
            yield f"data: {json.dumps(line.rstrip())}\n\n"
        process.stdout.close()
        process.wait()
        yield f"data: {json.dumps('__DONE__')}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    messages = data.get("messages", [])

    try:
        with open(SUMMARY_FILE) as f:
            summary_data = json.load(f)
        health_context = json.dumps(summary_data, indent=2)
        date_str = summary_data.get("date", "unknown")
    except FileNotFoundError:
        health_context = "No health data available yet."
        date_str = "unknown"

    # Load all lab results
    labs_context = ""
    labs_dir = os.path.join(BASE_DIR, "data", "labs")
    if os.path.isdir(labs_dir):
        lab_files = sorted(glob_module.glob(os.path.join(labs_dir, "????-??-??.json")), reverse=True)
        if lab_files:
            labs_sections = []
            for lf in lab_files:
                try:
                    with open(lf) as f:
                        lab_data = json.load(f)
                    labs_sections.append(json.dumps(lab_data, indent=2))
                except Exception:
                    pass
            if labs_sections:
                labs_context = "\n\nLab results (all uploads, newest first):\n" + "\n---\n".join(labs_sections)

    profile_context = load_profile_context()

    system_prompt = f"""You are a personal health assistant with access to the user's latest data from their WHOOP, Apple Health, Lose It, and lab results.
{profile_context}

Here is their health data for {date_str}:
{health_context}{labs_context}

Help them understand their metrics, identify patterns, and give actionable insights. Be specific to their actual numbers, conversational, and honest. Keep responses concise — this is a mobile chat interface."""

    def generate():
        try:
            with client.messages.stream(
                model="claude-opus-4-6",
                max_tokens=1024,
                system=system_prompt,
                messages=messages,
            ) as stream:
                for text in stream.text_stream:
                    yield f"data: {json.dumps(text)}\n\n"
            yield f"data: {json.dumps('__DONE__')}\n\n"
        except Exception as e:
            yield f"data: {json.dumps(f'Error: {str(e)}')}\n\n"
            yield f"data: {json.dumps('__DONE__')}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/history")
def history():
    days = min(int(request.args.get("days", 14)), 90)
    summaries_dir = os.path.join(BASE_DIR, "data", "summaries")
    if not os.path.isdir(summaries_dir):
        return jsonify([])
    files = sorted(
        glob_module.glob(os.path.join(summaries_dir, "????-??-??.json")),
        reverse=True,
    )[:days]
    result = []
    for f in sorted(files):  # ascending for chart display
        try:
            with open(f) as fp:
                d = json.load(fp)
            entry = {"date": d.get("date")}
            if d.get("recovery"):
                entry["recovery_score"] = d["recovery"].get("recovery_score")
                entry["hrv"] = d["recovery"].get("hrv_rmssd_milli")
                entry["rhr"] = d["recovery"].get("resting_heart_rate")
            if d.get("sleep"):
                hm = d["sleep"].get("total_sleep_duration")
                if hm:
                    entry["sleep_hours"] = round(
                        hm.get("hours", 0) + hm.get("minutes", 0) / 60, 2
                    )
                entry["sleep_performance"] = d["sleep"].get("sleep_performance_percentage")
            if d.get("strain"):
                entry["strain"] = d["strain"].get("strain_score")
            if d.get("activity"):
                entry["steps"] = d["activity"].get("steps")
            result.append(entry)
        except Exception:
            pass
    return jsonify(result)


@app.route("/api/brief")
def brief():
    refresh = request.args.get("refresh") == "1"
    today = datetime.now().strftime("%Y-%m-%d")
    briefs_dir = os.path.join(BASE_DIR, "data", "briefs")
    brief_path = os.path.join(briefs_dir, f"{today}.txt")

    if not refresh and os.path.exists(brief_path):
        with open(brief_path) as f:
            return jsonify({"brief": f.read(), "cached": True})

    try:
        with open(os.path.join(BASE_DIR, SUMMARY_FILE)) as f:
            summary_data = json.load(f)
        health_context = json.dumps(summary_data, indent=2)
    except FileNotFoundError:
        return jsonify({"error": "No health data. Run a sync first."}), 404

    labs_context = ""
    labs_dir = os.path.join(BASE_DIR, "data", "labs")
    if os.path.isdir(labs_dir):
        lab_files = sorted(glob_module.glob(os.path.join(labs_dir, "????-??-??.json")), reverse=True)
        if lab_files:
            try:
                with open(lab_files[0]) as f:
                    labs_context = f"\n\nMost recent lab results:\n{json.dumps(json.load(f), indent=2)}"
            except Exception:
                pass

    profile_context = load_profile_context()

    prompt = f"""Based on this health data, write a 2-3 sentence morning brief. Lead with the most important insight — recovery, sleep quality, or a standout metric. Be specific about the numbers. End with one concrete recommendation for today. No greeting, no sign-off.
{profile_context}

{health_context}{labs_context}"""

    try:
        message = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        brief_text = message.content[0].text.strip()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    os.makedirs(briefs_dir, exist_ok=True)
    with open(brief_path, "w") as f:
        f.write(brief_text)

    return jsonify({"brief": brief_text, "cached": False})


@app.route("/api/labs/upload", methods=["POST"])
def labs_upload():
    if "pdf" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["pdf"]
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "File must be a PDF"}), 400

    pdf_b64 = base64.standard_b64encode(file.read()).decode("utf-8")

    prompt = """Extract every biomarker from this lab report and return ONLY a JSON object — no explanation, no markdown, just raw JSON — in this exact structure:
{
  "date": "YYYY-MM-DD",
  "biomarkers": [
    {
      "name": "biomarker name",
      "value": 123.4,
      "unit": "mg/dL",
      "reference_range": "< 100",
      "status": "optimal|normal|borderline|high|low",
      "category": "Cardiovascular|Metabolic|Hormones|Blood|Vitamins|Inflammation|Other"
    }
  ]
}
Use the collection date for "date". For "status": use "optimal" if clearly in the best range, "normal" if within reference range, "borderline" if near the edge, "high" or "low" if outside range. If a field is not available use null."""

    try:
        message = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=8192,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        raw = message.content[0].text.strip()
        # Extract the JSON object robustly — find the outermost { ... }
        start = raw.find('{')
        end = raw.rfind('}')
        if start == -1 or end == -1:
            return jsonify({"error": "Claude did not return a JSON object", "raw": raw[:500]}), 500
        result = json.loads(raw[start:end + 1])
    except json.JSONDecodeError as e:
        return jsonify({"error": f"Extraction failed: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Extraction failed: {str(e)}"}), 500

    date = result.get("date") or datetime.now().strftime("%Y-%m-%d")
    labs_dir = os.path.join(BASE_DIR, "data", "labs")
    os.makedirs(labs_dir, exist_ok=True)
    result["date"] = date
    result["extracted_at"] = datetime.now().isoformat(timespec="seconds")
    path = os.path.join(labs_dir, f"{date}.json")
    with open(path, "w") as f:
        json.dump(result, f, indent=2)

    return jsonify(result)


@app.route("/api/labs")
def labs_list():
    labs_dir = os.path.join(BASE_DIR, "data", "labs")
    if not os.path.isdir(labs_dir):
        return jsonify([])
    files = glob_module.glob(os.path.join(labs_dir, "????-??-??.json"))
    results = []
    for f in sorted(files, reverse=True):
        try:
            with open(f) as fp:
                data = json.load(fp)
            results.append({
                "date": data.get("date"),
                "count": len(data.get("biomarkers", [])),
            })
        except Exception:
            pass
    return jsonify(results)


@app.route("/api/labs/<date>")
def labs_get(date):
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
        return jsonify({"error": "Invalid date"}), 400
    path = os.path.join(BASE_DIR, "data", "labs", f"{date}.json")
    try:
        with open(path) as f:
            return jsonify(json.load(f))
    except FileNotFoundError:
        return jsonify({"error": "Not found"}), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, threaded=True)
