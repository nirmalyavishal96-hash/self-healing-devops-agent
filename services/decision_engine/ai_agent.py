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
            timeout=30  # FIXED timeout
        )
        return res.json().get("response", "")
    except Exception as e:
        print("LLM error:", e)
        return ""


def safe_llm_call(prompt):
    out = analyze_with_llm(prompt)

    if "Root Cause:" in out:
        return out

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


def call_healer(action):
    try:
        payload = {
            "alerts": [
                {
                    "labels": {
                        "alertname": action,
                        "instance": "ai-agent"
                    },
                    "status": "firing"
                }
            ]
        }

        requests.post("http://healer:5001/webhook", json=payload, timeout=10)
        print(f"Sent action to healer: {action}")

    except Exception as e:
        print("Healer call failed:", e)


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

            if last_trigger_timestamp == trigger_ts:
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

            print(f"DEBUG → Confidence={confidence}, Z-score={z_score}")

            #  FINAL DECISION LOGIC (FIXED)
            if z_score >= 5 or confidence >= 0.8:
                decision = "HIGH_TRAFFIC"
            elif z_score >= 3:
                decision = "MODERATE"
            else:
                decision = "IGNORE"

            print("\n=== FINAL DECISION ===")
            print(parsed)
            print("Decision:", decision)

            # CORRECT ALERT MAPPING
            if decision == "HIGH_TRAFFIC":
                call_healer("HighRequestRate")

            elif decision == "MODERATE":
                call_healer("HighRequestRate")

            print("=====================\n")

        except Exception as e:
            print("Agent error:", e)

        time.sleep(2)