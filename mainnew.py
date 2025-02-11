import os
import json
import yaml
import sys
import subprocess
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

# Function to parse task arguments and extract user/group details
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

# Function to process compute machines & their states
def process_machines():
    yaml_data, _ = load_configuration()  # We only need the YAML data here

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

# Function to process users and groups
def process_entities():
    yaml_data, json_data = load_configuration()

    list_of_nodes = yaml_data.get("listOfNodes", [])
    
    users = []
    groups = []

    for node in list_of_nodes:
        task_arguments = node.get("taskArguments", "")
        users.extend(parse_task_arguments(task_arguments, "user"))
        groups.extend(parse_task_arguments(task_arguments, "group"))

    # Save extracted users and groups data into JSON files
    save_json("users", users)
    save_json("groups", groups)

    print("Processed users and groups successfully.")
    
    generate_report("user", users)
    generate_report("group", groups)

    # Run Puppet for both users and groups
    run_puppet("user")
    run_puppet("group")

    sys.exit(0)

# Function to save extracted data into JSON files
def save_json(entity_type, data):
    output_file = f"C:\\Scripts\\{entity_type}s.json"
    with open(output_file, "w") as out_file:
        json.dump({f"{entity_type}s": data}, out_file, indent=4)

# Function to execute Puppet manifest for user/group creation
def run_puppet(entity_type):
    try:
        puppet_manifest = f"C:\\Scripts\\{entity_type}_config.pp"
        command = ["puppet", "apply", puppet_manifest]
        subprocess.run(command, check=True)

        print(f"Puppet applied successfully for {entity_type}s.")
    
    except subprocess.CalledProcessError as e:
        print(f"Error executing Puppet: {e}")
        sys.exit(1)

# Function to generate a report of added, modified, and removed users/groups
def generate_report(entity_type, entities):
    table = PrettyTable(["Username/Group", "Action"])
    
    for entity in entities:
        action = "Added"
        table.add_row([entity.get("username", entity.get("groupname")), action])

    print(f"\nReport of Processed {entity_type.capitalize()}s:")
    print(table)

# Main Execution
if __name__ == "__main__":
    # Load and process compute machine states
    process_machines()

    # Process users and groups in a single execution
    process_entities()