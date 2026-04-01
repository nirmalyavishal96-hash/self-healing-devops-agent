import os
import time

def collect_logs():
    logs = os.popen("docker logs self_healing_app --tail 20").read()
    return logs

def analyze_logs(logs):
    logs_lower = logs.lower()

    if "error" in logs_lower:
        return "Error detected in logs"
    elif "exit" in logs_lower:
        return "Application crash detected"
    elif "exception" in logs_lower:
        return "Exception found in logs"
    return "System normal"

def main():
    print("Log Analyzer started...")

    while True:
        logs = collect_logs()
        result = analyze_logs(logs)

        print("Log Analysis:", result)
        print("-" * 50)

        time.sleep(10)

if __name__ == "__main__":
    main()