import time
import os

LOG_FILE = "/logs/app.log"

seen_events = set()

def analyze_log(line):
    line = line.lower()

    if "error" in line and "crash" in line:
        return {
            "issue": "Application Crash",
            "reason": "App process terminated unexpectedly",
            "action": "Restart service",
            "severity": "HIGH"
        }

    elif "cpu spike" in line:
        return {
            "issue": "High CPU Usage",
            "reason": "Heavy computation detected",
            "action": "Scale service or optimize code",
            "severity": "MEDIUM"
        }

    return None


def follow_logs():
    print("AI Agent started...", flush=True)

    # Wait until log file exists
    while not os.path.exists(LOG_FILE):
        time.sleep(1)

    with open(LOG_FILE, "r") as f:
        # IMPORTANT: start from END (ignore old logs)
        f.seek(0, os.SEEK_END)

        while True:
            line = f.readline()

            if not line:
                time.sleep(1)
                continue

            process_line(line)


def process_line(line):
    result = analyze_log(line)

    if result:
        key = result['issue'] + str(time.time())

        #  unique key per event (not blocking future events)
        if key in seen_events:
            return

        seen_events.add(key)

        print("\n=== AI ANALYSIS ===", flush=True)
        print(f"Issue     : {result['issue']}", flush=True)
        print(f"Reason    : {result['reason']}", flush=True)
        print(f"Action    : {result['action']}", flush=True)
        print(f"Severity  : {result['severity']}", flush=True)
        print("====================\n", flush=True)


if __name__ == "__main__":
    follow_logs()