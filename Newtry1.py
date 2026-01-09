import os
import yaml
import json
import subprocess
from prettytable import PrettyTable
import traceback
from glob import glob
import argparse
import logging
import pwd
import grp

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class YamlLoader:
    def load(self, file_path):
        with open(file_path, 'r') as f:
            return yaml.safe_load(f)

class JsonLoader:
    def load(self, file_path):
        with open(file_path, 'r') as f:
            return json.load(f)

class Parser:
    def parse_compute(self, file_path):
        yaml_loader = YamlLoader()
        return yaml_loader.load(file_path)

    def parse_state(self, file_path):  # Not used in this version
        return {}  # Return empty dict

class Report:
    def __init__(self):
        self.data = {}

    def set_data(self, data):
        self.data = data

    def print_data(self):
        # Improved report printing (example)
        for compute_name, report_data in self.data.items():
            print(f"Report for Compute: {compute_name}")
            print("-" * 30)
            # ... (Print other report data as needed)

class PrettyTable: # Dummy implementation if not using prettytable
    pass

def create_windows_users_groups(compute_name, compute_data, pipeline_action):
    added_users = {}
    added_groups = {}
    removed_users = {}
    created_users = []
    created_groups = []

    if compute_name not in compute_data:
        print(f"Warning: Compute '{compute_name}' not found in configuration data.")
        return added_users, added_groups, removed_users, created_users, created_groups

    if compute_data[compute_name].get('os', '').lower() != 'windows': # Handle missing 'os' key
        print(f"Warning: Compute '{compute_name}' is not a Windows machine. Skipping...")
        return added_users, added_groups, removed_users, created_users, created_groups

    add_users_data = []
    add_groups_data = []
    remove_users_data = []

    if compute_data[compute_name].get('win-os-accounts'): # Handle missing 'win-os-accounts'
        for user in compute_data[compute_name]['win-os-accounts']:
            username = user['account-name']
            description = user['account-desc']
            rdp = 'true' if user.get('logon-type', '') == 'rdp' else 'false' # Handle missing 'logon-type'
            password = user.get('password', 'DefaultPassword') # Get password, default if not found

            if username not in added_users:
                added_users[username] = []
                created_users.append({'username': username, 'description': description, 'rdp': rdp})
                add_users_data.append({
                    'username': username,
                    'description': description,
                    'rdp': rdp,
                    'password': password
                })

    if compute_data[compute_name].get('win-os-groups'): # Handle missing 'win-os-groups'
        for group in compute_data[compute_name]['win-os-groups']:
            group_name = group['group-name']
            description = group['group-desc']
            user_list = group['user-list']
            user_list_action = group.get('user-list-action', 'add') # Default to 'add' if missing

            for user in user_list:
                if user_list_action == 'add':
                    if group_name not in added_groups.setdefault(user, []):
                        added_groups[user].append(group_name)
                elif user_list_action == 'remove':
                    if group_name not in removed_users.setdefault(user, []):
                        removed_users[user].append(group_name)
                elif user_list_action == 'delete':
                    remove_users_data.append({'username': user})

            created_groups.append({'groupName': group_name, 'description': description})
            add_groups_data.append({
                'groupName': group_name,
                'description': description,
                'userList': user_list,
                'userListAction': user_list_action
            })

    create_users_local(add_users_data, add_groups_data, remove_users_data, pipeline_action)

    return added_users, added_groups, removed_users, created_users, created_groups


def create_users_local(add_users_data, add_groups_data, remove_users_data, pipeline_action):
    try:
        if pipeline_action == "create":
            # Create Users (with existence checks)
            for user in add_users_data:
                try:
                    pwd.getpwnam(user['username'])
                    print(f"User '{user['username']}' already exists. Skipping creation.")
                    continue
                except KeyError:
                    try:
                        subprocess.run(["net", "user", user['username'], user['password'], "/add", "/fullname", f"\"{user['description']}\""], check=True)
                        print(f"User '{user['username']}' created successfully.")
                        if user['rdp'] == 'true':
                            subprocess.run(["powershell", "-Command", f"Add-LocalGroupMember -Group 'Remote Desktop Users' -Member '{user['username']}'"], check=True)
                            print(f"User '{user['username']}' added to Remote Desktop Users.")
                    except subprocess.CalledProcessError as e:
                        logging.error(f"Error creating user '{user['username']}'. Command: {e.cmd}, Return Code: {e.returncode}, Output: {e.output.decode()}") # Improved error logging
            # Create Groups and Add Users (with existence checks)
            for group in add_groups_data:
                try:
                    grp.getgrnam(group['groupName'])
                    print(f"Group '{group['groupName']}' already exists. Skipping creation.")
                    continue
                except KeyError:
                    try:
                        subprocess.run(["net", "localgroup", group['groupName'], "/add", "/comment", f"\"{group['description']}\""], check=True)
                        print(f"Group '{group['groupName']}' created successfully.")
                    except subprocess.CalledProcessError as e:
                        logging.error(f"Error creating group '{group['groupName']}'. Command: {e.cmd}, Return Code: {e.returncode}, Output: {e.output.decode()}") # Improved error logging
                for user in group['userList']:
                    try:
                        subprocess.run(["net", "localgroup", group['groupName'], user, "/add"], check=True)
                        print(f"User '{user}' added to group '{group['groupName']}'.")
                    except subprocess.CalledProcessError as e:
                        logging.error(f"Error adding user '{user}' to group '{group['groupName']}'. Command: {e.cmd}, Return Code: {e.returncode}, Output: {e.output.decode()}") # Improved error logging

        elif pipeline_action == "delete":
            # Remove Users
            for user in remove_users_data:
                try:
                    pwd.getpwnam(user['username'])
                    try:
                        subprocess.run(["net", "user", user['username'], "/delete"], check=True)
                        print(f"User '{user['username']}' deleted successfully.")
                    except subprocess.CalledProcessError as e:
                        logging.error(f"Error deleting user '{user['username']}'. Command: {e.cmd}, Return Code: {e.returncode}, Output: {e.output.decode()}") # Improved error logging
                except KeyError:
                    print(f"User '{user['username']}' does not exist. Skipping deletion.")
        elif pipeline_action == "modify":
            # Implement your modify logic here
            pass  # Placeholder for modify actions
        else:
            logging.warning(f"Unknown pipeline action: {pipeline_action}")

    except Exception as e:
        logging.error(f"An error occurred: {e}")


def main():
    try:
        parser = Parser()
        json_loader = JsonLoader()

        computeFilePath = os.getenv("computeFilePath") # Get from env var
        # stateFilePath = os.getenv("stateFilePath") # Not used
        # existingGroupsPath = os.getenv("existingGroupsPath") # Not used
  
