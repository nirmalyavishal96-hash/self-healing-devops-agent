import time
import json
import os
import requests

BASELINE_FILE = "/shared/baseline.json"
TRIGGER_FILE = "/shared/anomaly_trigger.json"

WARMUP_COUNT = 5
MIN_VALID_RPS = 1
MIN_SEED_RPS = 5
MAX_LEARNING_DEVIATION_PERCENT = 0.5

#  FIX 1: Strong anomaly cooldown (prevents re-trigger spam)
LAST_ANOMALY_TIME = 0
ANOMALY_COOLDOWN = 60  # seconds

LAST_VALUES = []
LAST_METRIC = None


def load_baseline():
    if not os.path.exists(BASELINE_FILE):
        return {"count": 0, "mean": 0, "m2": 0}
    try:
        with open(BASELINE_FILE, "r") as f:
            return json.load(f)
    except:
        return {"count": 0, "mean": 0, "m2": 0}


def save_baseline(baseline):
    with open(BASELINE_FILE, "w") as f:
        json.dump(baseline, f)


def update_baseline(baseline, value):
    baseline["count"] += 1
    delta = value - baseline["mean"]
    baseline["mean"] += delta / baseline["count"]
    delta2 = value - baseline["mean"]
    baseline["m2"] += delta * delta2
    return baseline


def get_std(baseline):
    if baseline["count"] < 2:
        return 0
    return (baseline["m2"] / (baseline["count"] - 1)) ** 0.5


def compute_confidence(value, mean, std):
    if std == 0:
        if mean > 0 and value > mean * 2:
            return 5, 0.8
        return 0, 0.0

    z = (value - mean) / std

    if z < 2:
        return z, 0.0
    elif z < 3:
        return z, 0.5
    elif z < 5:
        return z, 0.7
    else:
        return z, 0.9


def fetch_metric():
    try:
        query = "rate(app_requests_total[30s])"
        res = requests.get(
            f"http://prometheus:9090/api/v1/query?query={query}"
        )
        data = res.json()

        if data["data"]["result"]:
            return float(data["data"]["result"][0]["value"][1])

        return None
    except Exception as e:
        print("Prometheus fetch error:", e)
        return None


if __name__ == "__main__":
    print("Adaptive Anomaly Detector started...")

    baseline = load_baseline()

    while True:
        try:
            value = fetch_metric()

            if value is None:
                print("No metric yet...")
                time.sleep(5)
                continue

            print(f"\nMetric value (RPS): {value:.2f}")

            # Ignore unrealistic spikes
            if value > 2000:
                print("Ignoring unrealistic spike")
                time.sleep(5)
                continue

            #  Ignore very low traffic
            if value < MIN_VALID_RPS:
                print("Ignoring low traffic")
                time.sleep(5)
                continue

            #  FIX 2: stale metric handling (non-blocking)
            if LAST_METRIC is not None and abs(value - LAST_METRIC) < 1:
                print("Stale metric (allowed)")
            LAST_METRIC = value

            #  FIX 3: spike-after-idle protection
            if LAST_METRIC is not None and LAST_METRIC < 5 and value > 500:
                print("Ignoring spike after idle")
                LAST_METRIC = value
                time.sleep(5)
                continue

            mean = baseline["mean"]
            std = get_std(baseline)
            threshold = mean + (2 * std)

            print(f"Baseline mean: {mean:.2f}, std: {std:.2f}, threshold: {threshold:.2f}")

            # -------- BASELINE LEARNING --------
            if baseline["count"] < WARMUP_COUNT:

                if baseline["count"] == 0:
                    if value < MIN_SEED_RPS:
                        print("Waiting for stable traffic...")
                        time.sleep(5)
                        continue

                    print("Initial seed")
                    baseline = update_baseline(baseline, value)
                    save_baseline(baseline)
                    time.sleep(5)
                    continue

                deviation = abs(value - mean) / mean if mean > 0 else 0

                if deviation > MAX_LEARNING_DEVIATION_PERCENT:
                    print("Skipping unstable value (early stage)")
                    time.sleep(5)
                    continue

                print("Learning baseline")
                baseline = update_baseline(baseline, value)
                save_baseline(baseline)
                time.sleep(5)
                continue

            # -------- SPIKE DETECTION --------
            LAST_VALUES.append(value)
            if len(LAST_VALUES) > 3:
                LAST_VALUES.pop(0)

            consistent_spike = (
                len(LAST_VALUES) == 3 and all(v > threshold for v in LAST_VALUES)
            )

            if not consistent_spike:
                print("No consistent spike")
                time.sleep(5)
                continue

            # FIX 4: HARD COOLDOWN (prevents repeated triggers)
            current_time = time.time()
            if current_time - LAST_ANOMALY_TIME < ANOMALY_COOLDOWN:
                print("Skipping duplicate anomaly (cooldown)")
                time.sleep(5)
                continue

            LAST_ANOMALY_TIME = current_time

            # -------- FINAL ANOMALY --------
            z_score, confidence = compute_confidence(value, mean, std)

            print("Adaptive anomaly detected!")

            data = {
                "timestamp": int(time.time()),
                "metric": value,
                "mean": mean,
                "std": std,
                "z_score": z_score,
                "confidence": confidence
            }

            with open(TRIGGER_FILE, "w") as f:
                json.dump(data, f)

            time.sleep(5)

        except Exception as e:
            print("Detector error:", e)
            time.sleep(5)