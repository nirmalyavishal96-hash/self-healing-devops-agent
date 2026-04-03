
import time
import requests
import os
import json

OLLAMA_URL = "http://172.17.0.1:11434/api/generate"
LOG_FILE = "/logs/app.log"
TRIGGER_FILE = "/shared/anomaly_trigger.json"

last_trigger_timestamp = None
last_processed_time = 0

COOLDOWN = 30


def wait_for_ollama():
    print("Waiting for Ollama...")
    for _ in range(5):
        try:
            if requests.get("http://172.17.0.1:11434").status_code == 200:
                print("Ollama ready")
                return
        except:
            pass
        time.sleep(2)
    print("Continuing without strict Ollama dependency...")


def get_recent_logs(lines=20):
    if not os.path.exists(LOG_FILE):
        return ""
    try:
        with open(LOG_FILE, "r") as f:
            return "".join(f.readlines()[-lines:])
    except:
        return ""


def read_trigger_file():
    try:
        with open(TRIGGER_FILE, "r") as f:
            return json.load(f)
    except:
        return None


def analyze_with_llm(prompt):
    try:
        res = requests.post(
            OLLAMA_URL,
            json={
                "model": "phi3:mini",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1}
            },
            timeout=5   # reduced timeout for faster fallback
        )
        return res.json().get("response", "")
    except Exception as e:
        print("LLM error:", e)
        return ""


def safe_llm_call(prompt):
    out = analyze_with_llm(prompt)

    if "Root Cause:" in out:
        return out

    #  fallback
    return """Root Cause: Traffic spike detected
Fix: Scale or rate limit requests
Severity: MEDIUM"""


def clean_output(text):
    result = {"Root Cause": "UNKNOWN", "Fix": "UNKNOWN", "Severity": "MEDIUM"}

    for line in text.split("\n"):
        if line.startswith("Root Cause"):
            result["Root Cause"] = line.split(":", 1)[1].strip()
        elif line.startswith("Fix"):
            result["Fix"] = line.split(":", 1)[1].strip()
        elif line.startswith("Severity"):
            sev = line.split(":", 1)[1].strip().upper()
            if "HIGH" in sev:
                result["Severity"] = "HIGH"
            elif "LOW" in sev:
                result["Severity"] = "LOW"
            else:
                result["Severity"] = "MEDIUM"

    return result


if __name__ == "__main__":
    print("AI Agent started")
    wait_for_ollama()

    while True:
        try:
            if not os.path.exists(TRIGGER_FILE):
                time.sleep(2)
                continue

            data = read_trigger_file()
            if not data:
                time.sleep(2)
                continue

            trigger_ts = data.get("timestamp", 0)

            if last_trigger_timestamp is not None and str(trigger_ts) == str(last_trigger_timestamp):
                time.sleep(1)
                continue

            current_time = time.time()

            if current_time - last_processed_time < COOLDOWN:
                print("Cooldown active...")
                time.sleep(2)
                continue

            print("\nNEW TRIGGER DETECTED")

            last_trigger_timestamp = trigger_ts
            last_processed_time = current_time

            confidence = data.get("confidence", 0)
            z_score = data.get("z_score", 0)

            logs = get_recent_logs()

            prompt = f"""
Metric anomaly detected.
Confidence: {confidence}
Z-score: {z_score}

Logs:
{logs}

FORMAT:
Root Cause:
Fix:
Severity:
"""

            raw = safe_llm_call(prompt)
            parsed = clean_output(raw)

            # DECISION ENGINE
            score = 0

            if confidence >= 0.8:
                score += 3
            elif confidence >= 0.5:
                score += 2
            elif confidence > 0:
                score += 1

            print(f"DEBUG → Confidence={confidence}, Score={score}")

            if score >= 5:
                decision = "RESTART"
            elif score >= 3:
                decision = "ESCALATE"
            else:
                decision = "IGNORE"

            print("\n=== FINAL DECISION ===")
            print(parsed)
            print("Decision:", decision)
            print("=====================\n")

        except Exception as e:
            print("Agent error:", e)

        time.sleep(2)

