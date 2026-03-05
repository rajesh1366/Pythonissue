import requests
import base64
import json
import os
import urllib3

urllib3.disable_warnings()

# ---------------- CONFIG ----------------

organization = "sc-ado-qa-op"
project = "ASIAQPR"
pat = "YOUR_PAT_TOKEN"

file_path = r"C:\Users\Rohith\Desktop\11111-test-NON_PROD-08.txt"

# ----------------------------------------

secure_file_name = os.path.splitext(os.path.basename(file_path))[0]

print("Secure file name:", secure_file_name)

# Extract CIID
ciid = secure_file_name.split("-")[0]

# Detect environment
if "NON_PROD" in secure_file_name:
    environment = "NON_PROD"
else:
    environment = "PROD"

print("CIID:", ciid)
print("Environment:", environment)

# ---------------- AUTH ----------------

auth = base64.b64encode(f":{pat}".encode()).decode()

headers = {
    "Authorization": f"Basic {auth}",
    "Content-Type": "application/octet-stream"
}

# ---------------- STEP 1 : Upload Secure File ----------------

upload_url = f"https://ado.global.standardchartered.com/{organization}/{project}/_apis/distributedtask/securefiles?name={secure_file_name}&api-version=7.1-preview.1"

with open(file_path, "rb") as f:
    response = requests.post(upload_url, headers=headers, data=f, verify=False)

if response.status_code not in [200, 201]:
    print("Upload failed")
    print(response.text)
    exit()

secure_file_id = response.json()["id"]

print("Secure file uploaded successfully")

# ---------------- STEP 2 : Get All Groups ----------------

graph_url = f"https://vssps.ado.global.standardchartered.com/{organization}/_apis/graph/groups?subjectTypes=vssgp&api-version=7.1-preview.1"

group_response = requests.get(graph_url, headers={"Authorization": f"Basic {auth}"}, verify=False)

groups = group_response.json()["value"]

# ---------------- STEP 3 : Filter Correct Groups ----------------

target_groups = []

for g in groups:

    name = g["displayName"]

    if environment == "NON_PROD":

        if name in [
            f"ADO-{ciid}-Engineer-review",
            f"ADO-{ciid}-Engineer-write"
        ]:
            target_groups.append(g)

    else:

        if name in [
            f"ADO-{ciid}-PSS-review",
            f"ADO-{ciid}-PSS-write"
        ]:
            target_groups.append(g)

print("Groups that will be assigned:")

for g in target_groups:
    print(g["displayName"])

# ---------------- STEP 4 : Assign Permissions ----------------

security_namespace = "52d39943-cb85-4d7f-8fa8-c6baac873819"

security_url = f"https://ado.global.standardchartered.com/{organization}/_apis/accesscontrolentries/{security_namespace}?api-version=7.1-preview.1"

headers_json = {
    "Authorization": f"Basic {auth}",
    "Content-Type": "application/json"
}

for g in target_groups:

    descriptor = g["descriptor"]

    body = {
        "token": f"SecureFile/{project}/{secure_file_id}",
        "merge": True,
        "accessControlEntries": [
            {
                "descriptor": descriptor,
                "allow": 1,
                "deny": 0
            }
        ]
    }

    perm_response = requests.post(
        security_url,
        headers=headers_json,
        data=json.dumps(body),
        verify=False
    )

    if perm_response.status_code in [200, 201]:
        print("Permission assigned to:", g["displayName"])
    else:
        print("Permission failed:", g["displayName"])
        print(perm_response.text)

print("Script completed successfully")
