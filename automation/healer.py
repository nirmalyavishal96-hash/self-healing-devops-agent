from flask import Flask, request
import os
import time

app = Flask(__name__)

# Track failures
failure_count = {}

# Track handled alerts
handled_alerts = set()

# Track last execution time (cooldown control)
alert_last_handled = {}
COOLDOWN_SECONDS = 30


@app.route("/webhook", methods=["POST"])
def webhook():
    print("WEBHOOK HIT")

    data = request.json

    for alert in data.get("alerts", []):
        labels = alert.get("labels", {})
        alert_name = labels.get("alertname")
        instance = labels.get("instance")
        status = alert.get("status")

        alert_key = f"{alert_name}_{instance}"

        print(f"Alert received: {alert_key}, status: {status}")

        # Handle resolved alerts
        if status == "resolved":
            handled_alerts.discard(alert_key)
            alert_last_handled.pop(alert_key, None)
            print(f"Alert resolved and cleared: {alert_key}")
            continue

        current_time = time.time()

        # LIVENESS FIX: If app is DOWN → always try recovery
        if alert_name == "AppDown":
            if not is_container_running("self_healing_app"):
                print("App is DOWN → forcing recovery (bypass cooldown)")
            else:
                # Apply cooldown only if app is already running
                if alert_key in alert_last_handled:
                    last_time = alert_last_handled[alert_key]
                    if current_time - last_time < COOLDOWN_SECONDS:
                        print("Skipping due to cooldown...")
                        continue

        # Mark execution time
        alert_last_handled[alert_key] = current_time

        # Dedup check
        if alert_key in handled_alerts:
            print("Already handled, skipping...")
            continue

        handled_alerts.add(alert_key)

        # Decision logic
        if alert_name == "AppDown":
            handle_app_down()

        elif alert_name == "HighRequestRate":
            handle_high_traffic()

    return "OK", 200


def is_container_running(service):
    result = os.popen(
        f"docker ps --filter name={service} --format '{{{{.Names}}}}'"
    ).read()
    return service in result


def handle_app_down():
    print("Executing handle_app_down()")

    service = "self_healing_app"

    failure_count[service] = failure_count.get(service, 0) + 1

    print(f"{service} failure count: {failure_count[service]}")

    if failure_count[service] <= 3:
        if not is_container_running(service):
            print("Action: Restarting container...")
            os.system(f"docker start {service}")
        else:
            print("Container already running, no action needed")
    else:
        print("Escalation: Too many failures, stopping retries")
        failure_count[service] = 0


def handle_high_traffic():
    print("High traffic detected")
    print("Action: Scale up (simulated)")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)