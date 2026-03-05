import requests
import base64
import json
import os
import urllib3

urllib3.disable_warnings()

# -----------------------------
# ADO DETAILS
# -----------------------------
organization = "sc-ado-qa-op"
project = "ASIAQPR"
pat = "YOUR_PAT_TOKEN"

# -----------------------------
# INPUTS
# -----------------------------
CIID = "11111"
environment = "NON_PROD"   # NON_PROD or PROD
file_path = r"C:\Users\Rohith\Desktop\securefile.txt"

# -----------------------------
# AUTH
# -----------------------------
pat_token = base64.b64encode(f":{pat}".encode()).decode()

headers = {
    "Authorization": f"Basic {pat_token}",
    "Content-Type": "application/octet-stream"
}

# -----------------------------
# FILE NAME FORMAT
# -----------------------------
base_filename = os.path.splitext(os.path.basename(file_path))[0]
secure_file_name = f"{CIID}-{base_filename}-{environment}"

print("Secure file name:", secure_file_name)

# -----------------------------
# STEP 1 : UPLOAD SECURE FILE
# -----------------------------
upload_url = f"https://ado.global.standardchartered.com/{organization}/{project}/_apis/distributedtask/securefiles?name={secure_file_name}&api-version=7.1-preview.1"

with open(file_path, "rb") as f:
    file_data = f.read()

upload_response = requests.post(upload_url, headers=headers, data=file_data, verify=False)

if upload_response.status_code not in [200,201]:
    print("❌ Upload failed")
    print(upload_response.text)
    exit()

print("✅ Secure file uploaded")

secure_file_id = upload_response.json()["id"]

# -----------------------------
# STEP 2 : GROUP SELECTION
# -----------------------------
if environment == "NON_PROD":

    target_groups = [
        f"ADO-{CIID}-Engineer-review",
        f"ADO-{CIID}-Engineer-write"
    ]

else:

    target_groups = [
        f"ADO-{CIID}-PSS-review",
        f"ADO-{CIID}-PSS-write"
    ]

print("Target groups:", target_groups)

# -----------------------------
# STEP 3 : GET ALL GROUPS
# -----------------------------
graph_url = f"https://ado.global.standardchartered.com/{organization}/_apis/graph/groups?subjectTypes=vssgp&api-version=7.1-preview.1"

graph_headers = {
    "Authorization": f"Basic {pat_token}"
}

group_response = requests.get(graph_url, headers=graph_headers, verify=False)

if group_response.status_code != 200:
    print("❌ Failed to get groups")
    print(group_response.text)
    exit()

groups = group_response.json().get("value", [])

# -----------------------------
# STEP 4 : SECURITY NAMESPACE
# -----------------------------
security_namespace = "52d39943-cb85-4d7f-8fa8-c6baac873819"

for group in target_groups:

    descriptor = None

    for g in groups:
        if group.lower() in g["displayName"].lower():
            descriptor = g["descriptor"]
            break

    if descriptor is None:
        print(f"⚠ Group not found: {group}")
        continue

    print(f"✅ Found group: {group}")

    token = f"SecureFile/{project}/{secure_file_id}"

    security_url = f"https://ado.global.standardchartered.com/{organization}/_apis/accesscontrolentries/{security_namespace}?api-version=7.1-preview.1"

    body = {
        "token": token,
        "merge": True,
        "accessControlEntries": [
            {
                "descriptor": descriptor,
                "allow": 1,
                "deny": 0
            }
        ]
    }

    security_headers = {
        "Authorization": f"Basic {pat_token}",
        "Content-Type": "application/json"
    }

    permission_response = requests.post(
        security_url,
        headers=security_headers,
        data=json.dumps(body),
        verify=False
    )

    if permission_response.status_code in [200,201]:
        print(f"🔐 Permission added for {group}")
    else:
        print(f"❌ Failed permission for {group}")
        print(permission_response.text)

print("🎉 Script completed")
