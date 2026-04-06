import time
import requests

ML_URL = "http://ml-service:6000/predict"
HEALER_URL = "http://healer-service:5001/webhook"

COOLDOWN = 120  # increased for stability
last_action_time = 0


def can_act():
    global last_action_time
    now = time.time()

    if now - last_action_time < COOLDOWN:
        print("Cooldown active...", flush=True)
        return False

    last_action_time = now
    return True


def call_ml(metric_value):
    try:
        res = requests.post(
            ML_URL,
            json={"metric": metric_value},
            timeout=5
        )
        return res.json().get("result", "UNKNOWN")
    except Exception as e:
        print("ML call failed:", e, flush=True)
        return "UNKNOWN"


def call_healer(alert_name):
    try:
        payload = {
            "alerts": [
                {
                    "labels": {
                        "alertname": alert_name
                    },
                    "status": "firing"
                }
            ]
        }

        requests.post(HEALER_URL, json=payload, timeout=10)
        print(f"Sent to healer: {alert_name}", flush=True)

    except Exception as e:
        print("Healer call failed:", e, flush=True)


def fetch_metric():
    try:
        res = requests.get(
            "http://prometheus:9090/api/v1/query",
            params={
                "query": "rate(app_requests_total[1m])"
            },
            timeout=5
        )

        data = res.json()
        results = data.get("data", {}).get("result", [])

        if not results:
            print("No metrics yet...", flush=True)
            return None

        value = float(results[0]["value"][1])
        return value

    except Exception as e:
        print("Prometheus fetch error:", e, flush=True)
        return None


if __name__ == "__main__":
    print("AI Decision Engine started...", flush=True)

    while True:
        try:
            metric_value = fetch_metric()

            # IGNORE INVALID DATA
            if metric_value is None or metric_value < 0.1:
                print("Skipping invalid/low metric...", flush=True)
                time.sleep(5)
                continue

            print(f"Metric value: {metric_value}", flush=True)

            ml_result = call_ml(metric_value)
            print(f"ML Result: {ml_result}", flush=True)

            if ml_result == "ANOMALY":
                if can_act():
                    call_healer("HighRequestRate")
                else:
                    print("Skipped due to cooldown", flush=True)

            else:
                print("System normal", flush=True)

        except Exception as e:
            print("Error:", e, flush=True)

        time.sleep(5)