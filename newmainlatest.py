import os
import json
import yaml
import sys
from prettytable import PrettyTable

# Function to load YAML and JSON files from environment variables
def load_configuration():
    compute_file = os.getenv("computeFilePath")  # Get YAML file path from env
    state_file = os.getenv("stateFilePath")  # Get JSON file path from env

    if not compute_file or not state_file:
        print("Error: Environment variables 'computeFilePath' and 'stateFilePath' must be set.")
        sys.exit(1)

    try:
        with open(compute_file, "r") as file:
            yaml_data = yaml.safe_load(file)
        
        with open(state_file, "r") as file:
            json_data = json.load(file)

        return yaml_data, json_data

    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

# Function to process compute machines & their states
def process_machines():
    yaml_data, _ = load_configuration()

    machines = yaml_data.get("computeMachines", [])
    if not machines:
        print("No compute machines found in configuration.")
        return []

    print("Processing compute machines and their states:")
    table = PrettyTable(["Machine Name", "State"])

    for machine in machines:
        name = machine.get("name", "Unknown")
        state = machine.get("state", "Unknown")
        table.add_row([name, state])

    print(table)
    return machines

# Function to process os_groups from compute data
def process_os_groups():
    yaml_data, _ = load_configuration()
    compute_data = yaml_data.get("computeMachines", {})

    groups = []

    for compute in compute_data:
        compute_name = compute.get("name", "Unknown")

        if "os_groups" in compute:
            for group in compute["os_groups"]:
                group_name = group.get('group-name', 'Unknown')
                description = group.get('group-desc', 'No description')
                user_list = group.get('user-list', [])
                user_list_action = group.get('user-list-action', '')

                groups.append({
                    "compute_name": compute_name,
                    "group_name": group_name,
                    "description": description,
                    "user_list": user_list,
                    "user_list_action": user_list_action
                })

    save_json("groups", groups)
    generate_group_report(groups)

# Function to save extracted data into JSON files
def save_json(entity_type, data):
    output_file = f"C:\\Scripts\\{entity_type}s.json"
    with open(output_file, "w") as out_file:
        json.dump({f"{entity_type}s": data}, out_file, indent=4)

# Function to generate a report for os_groups
def generate_group_report(groups):
    table = PrettyTable(["Compute Name", "Group Name", "Description", "Users", "Action"])

    for group in groups:
        table.add_row([
            group["compute_name"],
            group["group_name"],
            group["description"],
            ", ".join(group["user_list"]),
            group["user_list_action"]
        ])

    print("\nReport of OS Groups:")
    print(table)

# Main Execution
if __name__ == "__main__":
    process_machines()
    process_os_groups()