import os
import yaml
import json
import subprocess
from prettytable import PrettyTable
import traceback
from glob import glob
import argparse

class YamlLoader:
    @staticmethod
    def load(file_path):
        try:
            with open(file_path, 'r') as file:
                return yaml.safe_load(file)
        except Exception as e:
            raise ValueError(f'Error loading YAML file: {file_path} - {e}')

class JsonLoader:
    @staticmethod
    def load(file_path):
        try:
            with open(file_path, 'r') as file:
                return json.load(file)
        except Exception as e:
            raise ValueError(f'Error loading JSON file: {file_path} - {e}')

class Parser:
    def parse_os_name(self, value):
        value = value.upper()
        if 'W2K' in value:
            return 'windows'
        elif 'RHEL' in value:
            return 'linux'
        else:
            return 'unknown'

    def parse_compute(self, computeFilePath):
        print(f'Parsing compute file: {computeFilePath}')
        data = {}
        try:
            compute_mf = YamlLoader.load(computeFilePath)
            if compute_mf and 'compute-config' in compute_mf:
                computes = compute_mf['compute-config']
                for compute in computes:
                    compute_name = compute['name'].lower()
                    os_name = self.parse_os_name(compute['os']).lower()
                    data[compute_name] = {
                        'os': os_name,
                        'os_groups': compute.get('win-os-groups', []),
                        'os_users': compute.get('win-os-accounts', [])
                    }
            return data
        except ValueError as e:
            print(f"Error parsing compute file: {e}")
            return {}

    def parse_state(self, stateFilePath):
        print(f'Parsing state file: {stateFilePath}')
        data = {}
        try:
            state_file = JsonLoader.load(stateFilePath)
            if state_file and 'compute_configs' in state_file:
                compute_configs = state_file['compute_configs']
                for compute in compute_configs:
                    compute_name = compute['name'].lower()
                    states = compute['vm_states']
                    arr_ips = []
                    if states:
                        for state in states:
                            ip_addresses = state.get('ip_addresses', [])
                            if ip_addresses:
                                for item in ip_addresses:
                                    arr_ips.append(item['ip_address'])
                    data[compute_name] = arr_ips
            return data
        except ValueError as e:
            print(f"Error parsing state file: {e}")
            return {}


class Terminal:
    errors = []

    def get_errors(self):
        return self.errors

    def run_command(self, command):
        result = subprocess.run(command, capture_output=True, text=True, shell=True)
        if result.stderr:
            self.errors.append(result.stderr)
        if result.stdout:
            return result.stdout
        return None

class Report:
    def __init__(self):
        self.data = {}

    def set_data(self, data):
        self.data = data

    def print_data(self):
        if not self.data:
            print("No data to report.")
            return

        for compute_name, report_data in self.data.items():
            print(f"===========================SUMMARY for {compute_name}=====================")

            if not report_data.get('ip_addresses'):
                print("No IP addresses found for this compute.")
                continue

            t1 = PrettyTable(['IP Address'])
            for ip in report_data['ip_addresses']:
                t1.add_row([ip])
            print("IP Addresses:")
            print(t1)

            t2 = PrettyTable(['User', 'Groups Added'])
            added_users = report_data.get('added_users', {})
            for user, groups in added_users.items():
                t2.add_row([user, ', '.join(groups) if groups else ""])
            print("Users Added:")
            if added_users: print(t2)
            else: print("No users added.")

            t3 = PrettyTable(['User', 'Groups Removed'])
            removed_users = report_data.get('removed_users', {})
            for user, groups in removed_users.items():
                t3.add_row([user, ', '.join(groups) if groups else ""])
            print("Users Removed:")
            if removed_users: print(t3)
            else: print("No users removed.")

            created_users = report_data.get('created_users', [])
            if created_users:
                t4 = PrettyTable(['User', 'Description', 'RDP'])
                for user in created_users:
                    t4.add_row([user['username'], user['description'], user['rdp']])
                print("Users Created:")
                print(t4)
            else: print("No users created.")

            created_groups = report_data.get('created_groups', [])
            if created_groups:
                t5 = PrettyTable(['Group', 'Description'])
                for group in created_groups:
                    t5.add_row([group['groupName'], group['description']])
                print("Groups Created:")
                print(t5)
            else: print("No groups created.")

            errors = report_data.get('errors', [])
            if errors:
                print('##vso[task.logissue type=warning]=========WARNINGS=======')
                for err in errors:
                    print(err)
            print('')


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

        create_users_powershell(remote
