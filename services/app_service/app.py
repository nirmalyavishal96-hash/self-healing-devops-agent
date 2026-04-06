from flask import Flask, request, g
import time
import logging
import json
import os
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

# -------------------------------
# LOG SETUP (PRODUCTION SAFE)
# -------------------------------


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Go to project root
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "../../"))

LOG_DIR = os.path.join(PROJECT_ROOT, "logging", "app_logs")

os.makedirs(LOG_DIR, exist_ok=True)

log_file = os.path.join(LOG_DIR, "app.log")

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "level": record.levelname,
            "service": "app_service",
            "message": record.getMessage(),
            "endpoint": getattr(record, "endpoint", None),
            "latency": getattr(record, "latency", None)
        }
        return json.dumps(log_record)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# IMPORTANT FIXES
file_handler = logging.FileHandler(log_file, delay=False)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(JsonFormatter())

logger.addHandler(file_handler)
logger.propagate = False  # prevent duplicate logs

# ALSO PRINT TO STDOUT (VERY IMPORTANT FOR K8s)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(JsonFormatter())
logger.addHandler(stream_handler)

# -------------------------------
# PROMETHEUS METRICS
# -------------------------------
REQUEST_COUNT = Counter(
    'app_requests_total',
    'Total number of requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'app_request_latency_seconds',
    'Request latency',
    ['endpoint']
)

# -------------------------------
# REQUEST TRACKING
# -------------------------------
@app.before_request
def start_timer():
    g.start_time = time.time()

@app.after_request
def log_request(response):
    latency = time.time() - g.start_time

    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.path,
        status=response.status_code
    ).inc()

    REQUEST_LATENCY.labels(request.path).observe(latency)

    logger.info(
        f"{request.method} {request.path}",
        extra={
            "endpoint": request.path,
            "latency": round(latency, 4)
        }
    )

    return response

# -------------------------------
# ROUTES
# -------------------------------
@app.route("/")
def home():
    return "AIOps App Running"

@app.route("/load")
def load():
    logger.warning("CPU spike simulation started")
    for _ in range(10**6):
        pass
    logger.warning("CPU spike simulation completed")
    return "CPU spike simulated!"

@app.route("/fail")
def fail():
    try:
        x = 1 / 0
    except Exception as e:
        logger.error(f"Application crash: {str(e)}")
        os._exit(1)

@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

# -------------------------------
# ENTRYPOINT
# -------------------------------
if __name__ == "__main__":
    logger.info("Application started")
    app.run(host="0.0.0.0", port=5000)