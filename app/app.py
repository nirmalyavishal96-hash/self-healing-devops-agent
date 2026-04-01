from flask import Flask
import time
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os

app = Flask(__name__)

LOG_FILE = "/logs/app.log"

# Ensure log directory exists
os.makedirs('/logs', exist_ok=True)

def write_log(message):
    with open(LOG_FILE, "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")
        f.flush()

# Metrics
REQUEST_COUNT = Counter('app_requests_total', 'Total number of requests')

@app.route("/")
def home():
    REQUEST_COUNT.inc()
    write_log("INFO Home endpoint hit")
    return "Self-Healing DevOps App Running"

@app.route("/load")
def load():
    REQUEST_COUNT.inc()
    write_log("WARNING CPU spike simulation started")
    for _ in range(10**7):
        pass
    write_log("WARNING CPU spike simulation completed")
    return "CPU spike simulated!"

@app.route("/fail")
def fail():
    write_log("ERROR Application crash triggered")
    time.sleep(1)
    os._exit(1)

@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

if __name__ == "__main__":
    write_log("INFO Application started")
    app.run(host="0.0.0.0", port=5000)