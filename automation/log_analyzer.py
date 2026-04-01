import time
import os

LOG_FILE = "/app/app.log"

def wait_for_log_file():
    print("Waiting for log file...")
    while not os.path.exists(LOG_FILE):
        time.sleep(1)

def tail_logs():
    print("Real-time File Log Analyzer started...")

    with open(LOG_FILE, "r") as f:
        f.seek(0, 2)  # move to end of file

        while True:
            line = f.readline()

            if not line:
                time.sleep(1)
                continue

            line_lower = line.lower()

            if "error" in line_lower:
                print("ALERT: Application crash detected")

            elif "warning" in line_lower:
                print("WARNING detected")

            else:
                print("LOG:", line.strip())

if __name__ == "__main__":
    wait_for_log_file()
    tail_logs()