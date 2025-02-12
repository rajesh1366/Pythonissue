import os
import yaml
import json
import subprocess
from prettytable import PrettyTable
import traceback
from glob import glob
import argparse

# ... (YamlLoader, JsonLoader, Parser, Terminal, Report classes - same as before)

def create_windows_users_groups(compute_name, compute_data, state_data, new_user_password, terminal):
    added_users = {}
    added_groups = {}
    removed_users = {}
    created_users = []
    created_groups = []

    if compute_name not in compute_data or compute_name not in state_data:
        print(f"Warning: Compute '{compute_name}' not found in configuration or state data.")
        return added_users, added_groups, removed_users, created_users, created_groups

    if compute_data[compute_name]['os'] != 'windows':
        print(f"Warning: Compute '{compute_name}' is not a Windows machine. Skipping...")
        return added_users, added_groups, removed_users, created_users, created_groups

    for remote_ip in state_data.get(compute_name, []):
        add_users_data = []
        add_groups_data = []

        if compute_data[compute_name]['os_users']:
            for user in compute_data[compute_name]['os_users']:
                username = user['account-name']
                description = user['account-desc']
                rdp = 'true' if user['logon-type'] == 'rdp' else 'false'
                password = user.get('password', new_user_password)

                if username not in added_users:
                    added_users[username] = []
                    created_users.append({'username': username, 'description': description, 'rdp': rdp})
                    add_users_data.append({
                        'username': username,
                        'description': description,
                        'rdp': rdp,
                        'password': password
                    })

        if compute_data[compute_name]['os_groups']:
            for group in compute_data[compute_name]['os_groups']:
                group_name = group['group-name']
                description = group['group-desc']
                user_list = group['user-list']
                user_list_action = group['user-list-action']

                for user in user_list:
                    if user_list_action == 'add':
                        if group_name not in added_groups.setdefault(user, []):
                            added_groups[user].append(group_name)
                    elif user_list_action == 'remove':
                        if group_name not in removed_users.setdefault(user, []):
                            removed_users[user].append(group_name)

                created_groups.append({'groupName': group_name, 'description': description})
                add_groups_data.append({
                    'groupName': group_name,
                    'description': description,
                    'userList': user_list,
                    'userListAction': user_list_action
                })

        create_users_powershell(remote_ip, add_users_data, add_groups_data, terminal)  # Pass remote_ip

    return added_users, added_groups, removed_users, created_users, created_groups


def create_users_powershell(remote_ip, add_users_data, add_groups_data, terminal):  # Add remote_ip parameter
    try:
        # ... (rest of the create_users_powershell function - same as before)
        # Use remote_ip when printing messages
        print(f"User '{user['username']}' created successfully on {remote_ip}.")
        print(f"Error creating user '{user['username']}' on {remote_ip}.")
        # ...

    except Exception as e:
        print(f"An error occurred: {e}")

def main():
    try:
        parser = Parser()
        # ... (rest of the main function - same as before)

if __name__ == "__main__":
    main()

