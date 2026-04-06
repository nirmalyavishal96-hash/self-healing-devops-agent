import time
import os

LOG_FILE = "/logs/app.log"

def follow():
    print("Real-time File Log Analyzer started...", flush=True)

    while not os.path.exists(LOG_FILE):
        print("Waiting for log file...", flush=True)
        time.sleep(1)

    with open(LOG_FILE, "r") as f:
        f.seek(0, os.SEEK_END)

        while True:
            line = f.readline()

            if not line:
                time.sleep(0.5)
                continue

            line_lower = line.lower()

            if "error" in line_lower:
                print("ALERT: Application crash detected", flush=True)

            elif "warning" in line_lower:
                print("WARNING detected", flush=True)

            else:
                print("LOG:", line.strip(), flush=True)

if __name__ == "__main__":
    follow()