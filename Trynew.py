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

        create_users_powershell(remote_ip, add_users_data, add_groups_data, terminal)

    return added_users, added_groups, removed_users, created_users, created_groups

def create_users_powershell(remote_ip, add_users_data, add_groups_data, terminal):
    try:
        # Create Users (PowerShell)
        for user in add_users_data:
            create_user_command = f"net user {user['username']} {user['password']} /add /fullname \"{user['description']}\""
            out = terminal.run_command(create_user_command)
            if out is not None:
                print(f"User '{user['username']}' created successfully on {remote_ip}.")
                if user['rdp'] == 'true':
                    add_rdp_permission_command = f"powershell -Command \"Add-LocalGroupMember -Group 'Remote Desktop Users' -Member '{user['username']}'\""
                    out = terminal.run_command(add_rdp_permission_command)
                    if out is not None:
                        print(f"User '{user['username']}' added to Remote Desktop Users on {remote_ip}.")
                    else:
                        print(f"Error adding user '{user['username']}' to Remote Desktop Users on {remote_ip}.")
            else:
                print(f"Error creating user '{user['username']}' on {remote_ip}.")

        # Create Groups and Add Users (PowerShell)
        for group in add_groups_data:
            create_group_command = f"net localgroup {group['groupName']} /add /comment \"{group['description']}\""
            out = terminal.run_command(create_group_command)
            if out is not None:
                print(f"Group '{group['groupName']}' created successfully on {remote_ip}.")
            else:
                print(f"Error creating group '{group['groupName']}' on {remote_ip}.")

            for user in group['userList']:
                add_user_to_group_command = f"net localgroup {group['groupName']} {user} /add"
                out = terminal.run_command(add_user_to_group_command)
                if out is not None:
                    print(f"User '{user}' added to group '{group['groupName']}' on {remote_ip}.")
                else:
                    print(f"Error adding user '{user}' to group '{group['groupName']}' on {remote_ip}.")

    except Exception as e:
        print(f"An error occurred: {e}")

def main():
    try:
        parser = Parser()
        json_loader = JsonLoader()

        computeFilePath = os.getenv("computeFilePath")
        stateFilePath = os.getenv("stateFilePath")
        existingGroupsPath = os.getenv("existingGroupsPath")

        compute_data = parser.parse_compute(computeFilePath)
        state_data = parser.parse_state(glob(stateFilePath)[0])
        existing_groups = json_loader.load(existingGroupsPath)

        terminal = Terminal()

        remote_ssh_user = os.getenv("remoteSshUser")
        remote_ssh_password = os.getenv("remoteSshPassword")
        remote_path = os.getenv("remotePath")
        new_user_password = os.getenv("newUserPassword")

        report = Report()

        for compute_name in state_data:
            added_users, added_groups, removed_users, created_users, created_groups = create_windows_users_groups(compute_name, compute_data, state_data, new_user_password, terminal)

            report_data = {
                compute_name: {
                    "ip_addresses": state_data.get(compute_name, []),
                    "added_users": added_users,
                    "removed_users": removed_users,
                    "created_users": created_users,
                    "created_groups": created_groups,
                    "errors": terminal.get_errors()
                }
            }

            report.set_data(report_data)
            report.print_data()

    except Exception as e:
        print(f'##vso[task.logissue type=error] {traceback.format_exc()}')
        print(f'##vso[task.complete result=Failed] Task failed')

if __name__ == "__main__":
    main()
