import requests
import base64
import os

organization = "your-organization"
project = "your-project"
pat = "your-pat-token"

file_path = r"C:\Users\Rohith\Desktop\securefile.txt"
file_name = os.path.basename(file_path)

url = f"https://dev.azure.com/{organization}/{project}/_apis/distributedtask/securefiles?name={file_name}&api-version=7.1-preview.1"

# Encode PAT
pat_token = base64.b64encode(f":{pat}".encode()).decode()

headers = {
    "Authorization": f"Basic {pat_token}",
    "Content-Type": "application/octet-stream"
}

# Read file
with open(file_path, "rb") as f:
    file_content = f.read()

# Upload secure file
response = requests.post(url, headers=headers, data=file_content)

if response.status_code in [200, 201]:
    print("✅ Secure file uploaded successfully")
    print(response.json())
else:
    print("❌ Upload failed")
    print(response.status_code)
    print(response.text)
