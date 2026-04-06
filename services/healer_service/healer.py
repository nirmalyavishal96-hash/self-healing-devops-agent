from flask import Flask, request
from kubernetes import client, config
import time

app = Flask(__name__)

# Load Kubernetes config
try:
    config.load_incluster_config()
except:
    config.load_kube_config()

v1 = client.CoreV1Api()

# -------------------------------
#  COOLDOWN CONFIG 
# -------------------------------
LAST_ACTION = 0
COOLDOWN = 60  # seconds


def can_heal():
    global LAST_ACTION
    current_time = time.time()

    if current_time - LAST_ACTION < COOLDOWN:
        print("Cooldown active, skipping healing...")
        return False

    LAST_ACTION = current_time
    return True


def restart_pod(label_selector):
    pods = v1.list_namespaced_pod(
        namespace="default",
        label_selector=label_selector
    )

    for pod in pods.items:
        print(f"Deleting pod: {pod.metadata.name}")
        v1.delete_namespaced_pod(
            name=pod.metadata.name,
            namespace="default"
        )


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    for alert in data.get("alerts", []):
        alert_name = alert["labels"].get("alertname")

        print(f"Received alert: {alert_name}")

        #  APPLY COOLDOWN HERE
        if not can_heal():
            return "Cooldown active", 200

        if alert_name == "AppDown":
            restart_pod("app=app-service")

        elif alert_name == "HighRequestRate":
            restart_pod("app=app-service")

    return "OK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)