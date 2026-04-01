from flask import Flask
import time
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os
import logging

app = Flask(__name__)

# Setup logging to file
logging.basicConfig(
    filename='/app/app.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)

# Metrics
REQUEST_COUNT = Counter('app_requests_total', 'Total number of requests')

@app.route("/")
def home():
    REQUEST_COUNT.inc()
    logging.info("Home endpoint hit")
    return "Self-Healing DevOps App Running"

@app.route("/load")
def load():
    REQUEST_COUNT.inc()
    logging.warning("CPU spike simulation started")
    for _ in range(10**7):
        pass
    logging.warning("CPU spike simulation completed")
    return "CPU spike simulated!"

@app.route("/fail")
def fail():
    logging.error("Application crash triggered!")
    time.sleep(1)  # ensure log is written before exit
    os._exit(1)

@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

if __name__ == "__main__":
    logging.info("Application started")
    app.run(host="0.0.0.0", port=5000)