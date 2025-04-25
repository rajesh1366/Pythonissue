import os
import yaml
import json
import subprocess
from prettytable import PrettyTable
import traceback
from glob import glob
import argparse
import logging
import pwd  # For user existence checks
import grp  # For group existence checks

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ... (YamlLoader, JsonLoader, Parser, Report classes - same as before, potentially improved)

def create_windows_users_groups(compute_name, compute_data, pipeline_action):  # No state_data, no terminal
    added_users = {}
    added_groups = {}
    removed_users = {}
    created_users = []
    created_groups = []

    # ... (same as before, filtering by compute_name)

    add_users_data = []
    add_groups_data = []
    remove_users_data = []

    # ... (same as before, processing compute_data['os_users'] and compute_data['os_groups'])

                for user in user_list:
                    if user_list_action == 'add':
                        # ... (same as before)
                    elif user_list_action == 'remove':
                        if group_name not in removed_users.setdefault(user, []):
                            removed_users[user].append(group_name)
                    elif user_list_action == 'delete': # Handle user deletion
                        remove_users_data.append({'username': user}) # Add to remove_users_data

    create_users_local(add_users_data, add_groups_data, remove_users_data, pipeline_action)  # Call local function

    return added_users, added_groups, removed_users, created_users, created_groups

def create_users_local(add_users_data, add_groups_data, remove_users_data, pipeline_action):  # Local function
    try:
        if pipeline_action == "create":
            # Create Users (with existence checks)
            for user in add_users_data:
                try:
                    pwd.getpwnam(user['username'])  # Check if user exists
                    print(f"User '{user['username']}' already exists. Skipping creation.")
                    continue
                except KeyError:  # User doesn't exist
                    subprocess.run(["net", "user", user['username'], user['password'], "/add", "/fullname", f"\"{user['description']}\""], check=True)
                    print(f"User '{user['username']}' created successfully.")
                    if user['rdp'] == 'true':
                        subprocess.run(["powershell", "-Command", f"Add-LocalGroupMember -Group 'Remote Desktop Users' -Member '{user['username']}'"], check=True)
                        print(f"User '{user['username']}' added to Remote Desktop Users.")
            # Create Groups and Add Users (with existence checks)
            for group in add_groups_data:
                try:
                    grp.getgrnam(group['groupName'])  # Check if group exists
                    print(f"Group '{group['groupName']}' already exists. Skipping creation.")
                    continue
                except KeyError:  # Group doesn't exist
                    subprocess.run(["net", "localgroup", group['groupName'], "/add", "/comment", f"\"{group['description']}\""], check=True)
                    print(f"Group '{group['groupName']}' created successfully.")
                for user in group['userList']:
                    subprocess.run(["net", "localgroup", group['groupName'], user, "/add"], check=True)
                    print(f"User '{user}' added to group '{group['groupName']}'.")

        elif pipeline_action == "delete":
            # Remove Users
            for user in remove_users_data:
                try:
                    pwd.getpwnam(user['username'])  # Check if user exists before deleting
                    subprocess.run(["net", "user", user['username'], "/delete"], check=True)
                    print(f"User '{user['username']}' deleted successfully.")
                except KeyError:
                    print(f"User '{user['username']}' does not exist. Skipping deletion.")
        elif pipeline_action == "modify":
            # Implement your modify logic here
            pass # Placeholder for modify actions
        else:
            logging.warning(f"Unknown pipeline action: {pipeline_action}")

    except subprocess.CalledProcessError as e:
        logging.error(f"Command execution failed: {e}")
    except Exception as e:
        logging.error(f"An error occurred: {e}")

def main():
    try:
        parser = Parser()
        json_loader = JsonLoader()

        # ... (Get file paths from environment variables or command-line arguments)

        compute_data = parser.parse_compute(computeFilePath)
        # state_data = parser.parse_state(glob(stateFilePath)[0]) # No longer needed

        # ... (Get SSH credentials and other parameters - not needed)
        pipeline_action = os.getenv("pipeline_action")

        report = Report()

        for compute_name in compute_data: # Iterate through compute_data directly
            added_users, added_groups, removed_users, created_users, created_groups = create_windows_users_groups(
                compute_name, compute_data, pipeline_action
            )  # No state_data

            # ... (Report generation)

    except Exception as e:
        logging.exception("An error occurred:")
        print(f'##vso[task.complete result=Failed] Task failed')

if __name__ == "__main__":
    main()

