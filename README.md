# Pythonissue

Got it! We need a Windows JSON format similar to the Linux one, while ensuring compatibility with Windows user and group management.

Step 1: Define Windows JSON Structure

This Windows JSON should follow the same pattern as Linux but formatted for Windows user and group management.

Windows User JSON (windows_user.json)

{
  "deploy_artifact": "https://artifactory_global.standardchartered.com/artifactory/generic-sc-release-local/po",
  "script": "windows_user_action.ps1",
  "build_id": 856825,
  "build_local_path": "C:\\Scripts",
  "listOfNodes": [
    {
      "targetNodes": "WIN-SRV01,WIN-SRV02",
      "taskArguments": "create|john.doe|John Doe|StrongP@ssw0rd|Administrators,Developers create|jane.smith|Jane Smith|AnotherP@ss|Users"
    }
  ]
}

Windows Group JSON (windows_group.json)

{
  "deploy_artifact": "https://artifactory_global.standardchartered.com/artifactory/generic-sc-release-local/po",
  "script": "windows_group_action.ps1",
  "build_id": 856825,
  "build_local_path": "C:\\Scripts",
  "listOfNodes": [
    {
      "targetNodes": "WIN-SRV01,WIN-SRV02",
      "taskArguments": "create|Developers|Group for development team create|Users|Standard user group"
    }
  ]
}

Step 2: Modify the Python Script for Windows

The Python script should extract taskArguments and convert them into a structured JSON file that PowerShell can process.

Updated Python Script (process_windows_users_groups.py)

import json
import sys
import argparse

def parse_task_arguments(task_arguments, entity_type):
    entities = []
    tasks = task_arguments.split(" create|")

    for task in tasks:
        if task.strip():
            details = task.split("|")
            if entity_type == "user":
                if len(details) >= 4:
                    entities.append({
                        "username": details[0],
                        "fullname": details[1],
                        "password": details[2],
                        "groups": details[3].split(",")
                    })
            elif entity_type == "group":
                if len(details) >= 2:
                    entities.append({
                        "groupname": details[0],
                        "description": details[1]
                    })

    return entities

def process_json(json_file, entity_type):
    try:
        with open(json_file, "r") as file:
            data = json.load(file)

        list_of_nodes = data.get("listOfNodes", [])

        for node in list_of_nodes:
            task_arguments = node.get("taskArguments", "")
            entities = parse_task_arguments(task_arguments, entity_type)

            output_file = f"C:\\Scripts\\{entity_type}s.json"
            with open(output_file, "w") as out_file:
                json.dump({f"{entity_type}s": entities}, out_file, indent=4)

        print(f"Processed {entity_type}s successfully.")
        sys.exit(0)

    except Exception as e:
        print(f"Error processing JSON: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--jsonFile", required=True, help="Path to JSON file")
    parser.add_argument("--entityType", required=True, choices=["user", "group"], help="Specify 'user' or 'group'")
    
    args = parser.parse_args()
    process_json(args.jsonFile, args.entityType)

Step 3: Modify PowerShell Scripts

PowerShell Script for Creating Users (windows_user_action.ps1)

param (
    [string]$jsonFilePath
)

# Read JSON file
$jsonContent = Get-Content -Raw -Path $jsonFilePath | ConvertFrom-Json

foreach ($user in $jsonContent.users) {
    $username = $user.username
    $fullname = $user.fullname
    $password = $user.password
    $groups = $user.groups

    if (-Not (Get-LocalUser -Name $username -ErrorAction SilentlyContinue)) {
        Write-Host "Creating user: $username"
        New-LocalUser -Name $username -Password (ConvertTo-SecureString -AsPlainText $password -Force) -FullName $fullname -Description "Created via automation"
    } else {
        Write-Host "User $username already exists. Skipping."
    }

    foreach ($group in $groups) {
        if (Get-LocalGroup -Name $group -ErrorAction SilentlyContinue) {
            Write-Host "Adding $username to group $group"
            Add-LocalGroupMember -Group $group -Member $username
        } else {
            Write-Host "Group $group does not exist. Skipping."
        }
    }
}

PowerShell Script for Creating Groups (windows_group_action.ps1)

param (
    [string]$jsonFilePath
)

# Read JSON file
$jsonContent = Get-Content -Raw -Path $jsonFilePath | ConvertFrom-Json

foreach ($group in $jsonContent.groups) {
    $groupName = $group.groupname
    $description = $group.description

    if (-Not (Get-LocalGroup -Name $groupName -ErrorAction SilentlyContinue)) {
        Write-Host "Creating group: $groupName"
        New-LocalGroup -Name $groupName -Description $description
    } else {
        Write-Host "Group $groupName already exists. Skipping."
    }
}

Step 4: Modify Azure DevOps Pipeline

Updated azure-pipeline.yml

parameters:
  - name: pipeline_action
    displayName: "Pick the correct action to execute"
    type: string
    values: ["create", "modify", "delete"]
    default: "create"

jobs:
  - job: WindowsUserGroupManagement
    timeoutInMinutes: 360
    pool:
      name: windows-pool
      demands:
        - Agent.OS -equals Windows

    steps:
      - task: Checkout@1
        displayName: "Checkout Code"

      - task: PowerShell@2
        displayName: "Download Scripts"
        inputs:
          targetType: 'inline'
          script: |
            Invoke-WebRequest -Uri "https://artifactory.example.com/windows_mgmt.zip" -OutFile "C:\Scripts\windows_mgmt.zip"
            Expand-Archive -Path "C:\Scripts\windows_mgmt.zip" -DestinationPath "C:\Scripts"

      - task: UsePythonVersion@0
        displayName: "Use Python 3.9"
        inputs:
          versionSpec: "3.9"
          addToPath: true

      - task: PythonScript@0
        displayName: "Process Users JSON"
        inputs:
          scriptPath: "C:\Scripts\process_windows_users_groups.py"
          arguments: "--jsonFile C:\Scripts\windows_user.json --entityType user"

      - task: PythonScript@0
        displayName: "Process Groups JSON"
        inputs:
          scriptPath: "C:\Scripts\process_windows_users_groups.py"
          arguments: "--jsonFile C:\Scripts\windows_group.json --entityType group"

      - task: PowerShell@2
        displayName: "Create Groups"
        inputs:
          targetType: 'filePath'
          filePath: "C:\Scripts\windows_group_action.ps1"
          arguments: "-jsonFilePath C:\Scripts\groups.json"

      - task: PowerShell@2
        displayName: "Create Users"
        inputs:
          targetType: 'filePath'
          filePath: "C:\Scripts\windows_user_action.ps1"
          arguments: "-jsonFilePath C:\Scripts\users.json"

      - task: puppet-infra@1
        displayName: 'Apply Puppet Configuration'
        inputs:
          authToken: '$(puppet_Secrets.puppetProd)'
          puppetHttpAPI: "https://puppet.example.com"
          puppetAPIPort: '8143'
          taskName: 'apply'
          taskInputFilepath: 'C:\Scripts\windows_users_groups.pp'
          puppetEnvironment: 'production'

Final Summary

✔ Windows JSON now matches Linux structure
✔ Updated Python script to parse taskArguments
✔ Added PowerShell scripts for user & group creation
✔ Integrated into Azure DevOps Pipeline

This ensures consistent Windows and Linux automation! Let me know if any refinements are needed. 🚀
