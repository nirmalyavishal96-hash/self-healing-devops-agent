from flask import Flask, request
import os
import time

app = Flask(__name__)

failure_count = {}
handled_alerts = set()
alert_last_handled = {}

COOLDOWN_SECONDS = 30
RESTART_DELAY = 10


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

        if status == "resolved":
            handled_alerts.discard(alert_key)
            alert_last_handled.pop(alert_key, None)
            continue

        current_time = time.time()

        if alert_key in alert_last_handled:
            if current_time - alert_last_handled[alert_key] < COOLDOWN_SECONDS:
                print("Skipping due to cooldown...")
                continue

        alert_last_handled[alert_key] = current_time

        if alert_key in handled_alerts:
            print("Already handled, skipping...")
            continue

        handled_alerts.add(alert_key)

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
    print("Handling AppDown...")

    service = "self_healing_app"

    if not is_container_running(service):
        print("Restarting stopped container...")
        os.system(f"docker start {service}")
    else:
        print("App is running, no restart needed")


def handle_high_traffic():
    print("High traffic detected ")

    service = "self_healing_app"

    print("Action: Restarting to recover from overload...")
    os.system(f"docker restart {service}")



if __name__ == "__main__":
    print("Starting healer service...")
    app.run(host="0.0.0.0", port=5001)