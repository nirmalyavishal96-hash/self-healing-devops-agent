from flask import Flask
import time
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os
app = Flask(__name__)

# Metrics
REQUEST_COUNT = Counter('app_requests_total', 'Total number of requests')

@app.route("/")
def home():
    REQUEST_COUNT.inc()
    return "Self-Healing DevOps App Running "

@app.route("/load")
def load():
    REQUEST_COUNT.inc()
    for _ in range(10**7):
        pass
    return "CPU spike simulated!"


@app.route("/fail")
def fail():
    os._exit(1)   

@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)