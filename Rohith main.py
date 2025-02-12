import os
import yaml
import json
import subprocess
from prettytable import PrettyTable
import traceback
from glob import glob
import argparse

class YamlLoader:
    # ... (Same as before)

class JsonLoader:
    # ... (Same as before)

class Parser:
    # ... (Same as before)

class Terminal:
    # ... (Same as before)

class Report:
    # ... (Same as before)


def create_windows_users_groups(compute_name, compute_data, state_data, new_user_password, terminal):
    added_users = []
    added_groups = {}
    removed_users = {}

    if compute_name not in compute_data or compute_name not in state_data:
        print(f"Warning: Compute '{compute_name}' not found in configuration or state data.")
        return added_users, added_groups, removed_users  # Return empty if compute is not found

    if compute_data[compute_name]['os'] != 'windows':
        print(f"Warning: Compute '{compute_name}' is not a Windows machine. Skipping...")
        return added_users, added_groups, removed_users

    for remote_ip in state_data.get(compute_name, []): # Handle cases where compute_name has no IPs
        add_users_data = []
        add_groups_data = []
        modified_groups = []

        if compute_data[compute_name]['os_users']:
            for user in compute_data[compute_name]['os_users']:
                username = user['account-name']
                description = user['account-desc']
                rdp = 'true' if user['logon-type'] == 'rdp' else 'false'
                password = user.get('password', new_user_password) # Use provided password or fallback

                if username not in added_users:
                    added_users.append(username)
                    add_users_data.append({
                        'username': username,
                        'description': description,
                        'rdp': rdp,
                        'password': password  # Include the password here
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

                add_groups_data.append({
                    'groupName': group_name,
                    'description': description,
                    'userList': user_list,
                    'userListAction': user_list_action
                })
                modified_groups.append(group_name)

        # Execute PowerShell commands (using the new function)
        create_users_powershell(remote_ip, add_users_data, add_groups_data, terminal)

    return added_users, added_groups, removed_users


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
    parser = argparse.ArgumentParser(description="Create Windows users and groups.")
    parser.add_argument("-compute", dest="compute_file", required=True, help="Path to compute YAML file")
    parser.add_argument("-state", dest="state_file", required=True, help="Path to state JSON file")
    parser.add_argument("-password", dest="new_user_password", required=True, help="Default password for new users")
    args = parser.parse_args()

    try:
        parser_obj = Parser()
        compute_data = parser_obj.parse_compute(args.compute_file)
        state_data = parser_obj.parse_state(glob(args.state_file)[0]) # Handle glob and take first file
        terminal = Terminal()
        report = Report()

        for compute_name in state_data:
            added_users, added_groups, removed_users = create_windows_users_groups(compute_name, compute_data, state_data, args.new_user_password, terminal)

            report.set_data({
                'ip_addresses': state_data.get(compute_name, []), # Handle missing compute_name
                'added_users': added_users,
                'added_groups': added_groups,
                'removed_users': removed_users
            })

            print(f"===========================SUMMARY for {compute_name}=====================")
            report.print_data()
            print('')

            errors = terminal.get_errors()
            if errors:
                print('##vso[task.logissue type=warning]=========WARNINGS=======')
                for err in errors:
                    print(err)

    except Exception as e:
        print(f'##vso[task.logissue type=error] {traceback.format_exc()}')
        print(f'##vso[task.complete result=Failed] Task failed')  # Indicate failure


if __name__ == "__main__":
    main()


