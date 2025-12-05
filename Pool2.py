import requests
import csv
from datetime import datetime, timedelta
import base64

# ====== CONFIGURATION ======
ORG = "your-org"           # Your ADO organization
POOL_ID = 123              # Agent Pool ID
PAT = "your_PAT_here"      # PAT directly in script
API_VERSION = "7.1-preview.1"
# ===========================

# Create authentication header
auth_header = base64.b64encode(f":{PAT}".encode()).decode()

# Last 24 hours filter
end_time = datetime.utcnow()
start_time = end_time - timedelta(hours=24)

# API URL (no project needed)
url = f"https://dev.azure.com/{ORG}/_apis/distributedtask/pools/{POOL_ID}/jobrequests?api-version={API_VERSION}"

headers = {"Authorization": f"Basic {auth_header}"}

response = requests.get(url, headers=headers)
data = response.json()

rows = []

for job in data.get("value", []):
    assign_time = job.get("assignTime")

    # Filter for last 24 hours
    if assign_time:
        assign_dt = datetime.fromisoformat(assign_time.replace("Z", "+00:00"))
        if assign_dt < start_time:
            continue

    rows.append([
        job.get("requestId"),
        job.get("queueTime"),
        job.get("assignTime"),
        job.get("finishTime"),
        job.get("result"),
        job.get("agent", {}).get("name"),
        job.get("owner", {}).get("name"),
        job.get("definition", {}).get("name"),
    ])

# Write to CSV
with open("agent_pool_jobs.csv", "w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow([
        "Job ID", "Queue Time", "Assign Time", "Finish Time",
        "Result", "Agent Name", "Triggered By", "Pipeline Name"
    ])
    writer.writerows(rows)

print("Saved: agent_pool_jobs.csv")
