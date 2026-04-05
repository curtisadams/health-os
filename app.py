import os
import json
import subprocess
import sys
from flask import Flask, render_template, jsonify, Response, request
import anthropic
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
client = anthropic.Anthropic()

SUMMARY_FILE = "data/daily_summary.json"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/summary")
def summary():
    try:
        with open(SUMMARY_FILE) as f:
            return jsonify(json.load(f))
    except FileNotFoundError:
        return jsonify({"error": "No data found. Run a sync first."}), 404


@app.route("/api/sync", methods=["POST"])
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

    system_prompt = f"""You are a personal health assistant with access to the user's latest data from their WHOOP, Apple Health, and Lose It integrations.

Here is their health data for {date_str}:
{health_context}

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


if __name__ == "__main__":
    app.run(debug=True, port=5001, threaded=True)
