
import time
import json
import os
import requests  

BASELINE_FILE = "/shared/baseline.json"
TRIGGER_FILE = "/shared/anomaly_trigger.json"

WARMUP_COUNT = 20
MIN_VALID_RPS = 2
MIN_SEED_RPS = 100
MAX_LEARNING_DEVIATION_PERCENT = 0.25  #  RELATIVE FIX

FREEZE_BASELINE = True


def load_baseline():
    if not os.path.exists(BASELINE_FILE):
        return {"count": 0, "mean": 0, "m2": 0}
    try:
        with open(BASELINE_FILE, "r") as f:
            return json.load(f)
    except:
        return {"count": 0, "mean": 0, "m2": 0}


def save_baseline(baseline):
    try:
        with open(BASELINE_FILE, "w") as f:
            json.dump(baseline, f)
    except:
        pass


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
        res = requests.get(
            "http://prometheus:9090/api/v1/query?query=rate(app_requests_total[10s])"
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

            if value < MIN_VALID_RPS:
                print("Ignoring low traffic (not suitable for baseline)")
                time.sleep(5)
                continue

            mean = baseline["mean"]
            std = get_std(baseline)
            threshold = mean + max(2 * std, 30)

            print(f"Baseline mean: {mean:.2f}, std: {std:.2f}, threshold: {threshold:.2f}")

            #  WARMUP PHASE
            if baseline["count"] < WARMUP_COUNT:

                # INITIAL SEED
                if baseline["count"] == 0:
                    if value < MIN_SEED_RPS:
                        print("Waiting for stable high traffic to start baseline...")
                        time.sleep(5)
                        continue

                    print("Initial seed value (valid traffic)")
                    baseline = update_baseline(baseline, value)
                    save_baseline(baseline)
                    time.sleep(5)
                    continue

                # INITIAL LEARNING
                if baseline["count"] < 5:
                    deviation = abs(value - mean) / mean if mean > 0 else 0

                    if deviation > MAX_LEARNING_DEVIATION_PERCENT:
                        print("Skipping unstable initial value")
                    else:
                        print("Stable initial learning")
                        baseline = update_baseline(baseline, value)

                    save_baseline(baseline)
                    time.sleep(5)
                    continue

                # WARMUP LEARNING
                deviation = abs(value - mean) / mean if mean > 0 else 0

                if deviation > MAX_LEARNING_DEVIATION_PERCENT:
                    print("Skipping spike during warmup (not learning)")
                    time.sleep(5)
                    continue

                print("Warmup learning (stable traffic)")
                baseline = update_baseline(baseline, value)
                save_baseline(baseline)
                time.sleep(5)
                continue

            # AFTER WARMUP
            if std == 0:
                print("Std is zero, continue learning...")
                baseline = update_baseline(baseline, value)
                save_baseline(baseline)
                time.sleep(5)
                continue

            # ANOMALY DETECTION
            is_anomaly = value > threshold

            if is_anomaly:
                z_score, confidence = compute_confidence(value, mean, std)

                if confidence < 0.5:
                    print("Low confidence anomaly ignored")
                else:
                    print("Adaptive anomaly detected!")
                    print(f"Z-score: {z_score:.2f}, Confidence: {confidence}")

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

            else:
                if not FREEZE_BASELINE:
                    baseline = update_baseline(baseline, value)
                    save_baseline(baseline)
                else:
                    print("Baseline frozen (no learning)")

            time.sleep(5)

        except Exception as e:
            print("Detector error:", e)
            time.sleep(5)

