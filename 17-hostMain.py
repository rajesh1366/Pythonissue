import os
import yaml
import json
import traceback
from glob import glob
from prettytable import PrettyTable

class YamlLoader:
    @staticmethod
    def load(file_path):
        try:
            with open(file_path, 'r') as file:
                return yaml.safe_load(file)
        except Exception:
            raise ValueError(f"Error loading YAML file: {file_path}")

class JsonLoader:
    @staticmethod
    def load(file_path):
        try:
            with open(file_path, 'r') as file:
                return json.load(file)
        except Exception:
            raise ValueError(f"Error loading JSON file: {file_path}")

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
        print(f"Parsing file: {computeFilePath}")
        data = {}

        yaml_loader = YamlLoader()
        compute_mf = yaml_loader.load(computeFilePath)

        if compute_mf:
            computes = compute_mf.get('compute-config', [])
            for compute in computes:
                compute_name = compute['name'].lower()
                os_type = self.parse_os_name(compute['os']).lower()
                
                data[compute_name] = {
                    'os': os_type,
                    'os_groups': compute.get('win-os-groups', []),
                    'os_users': compute.get('win-os-accounts', [])
                }
        return data

    def parse_state(self, stateFilePath):
        print(f"Parsing file: {stateFilePath}")
        data = {}

        json_loader = JsonLoader()
        state_file = json_loader.load(stateFilePath)

        if state_file:
            compute_configs = state_file.get('compute_configs', [])
            for compute in compute_configs:
                compute_name = compute['name'].lower()
                data[compute_name] = compute_name  # Store hostname instead of IP
        return data

class Report:
    def __init__(self):
        self.data = {}

    def print_data(self):
        print("\n======= REPORT =======")
        
        t1 = PrettyTable(['Hosts'])
        for hostname in self.data.get('hostnames', []):
            t1.add_row([hostname])
        print(t1)

        print('Added Users:')
        t2 = PrettyTable(['User', 'Group'])
        for user in self.data.get('added_users', []):
            groups = ', '.join(self.data.get('added_groups', {}).get(user, []))
            t2.add_row([user, groups])
        print(t2)

        print('Removed Users:')
        t3 = PrettyTable(['User', 'Group'])
        for user in self.data.get('removed_users', []):
            groups = ', '.join(self.data.get('removed_users', {}).get(user, []))
            t3.add_row([user, groups])
        print(t3)

    def set_data(self, value):
        self.data = value

try:
    parser = Parser()
    json_loader = JsonLoader()

    # Load environment variables for file paths
    computeFilePath = os.getenv("computeFilePath")
    stateFilePath = os.getenv("stateFilePath")
    existingGroupsPath = os.getenv("existingGroupsPath")

    # Load configuration data
    compute_data = parser.parse_compute(computeFilePath)
    state_data = parser.parse_state(stateFilePath)
    existing_groups = json_loader.load(existingGroupsPath)

    report = Report()

    # Process users and groups
    for compute_name in state_data:
        if compute_name not in compute_data:
            continue
        if "os" not in compute_data[compute_name]:
            continue
        if compute_data[compute_name]["os"] != 'windows':
            print(f"##vso[task.logissue type=warning]{compute_name} is not a Windows machine. Skipping...")
            continue

        print(f"Processing Host: {compute_name}")

        added_users = []
        added_groups = {}
        removed_users = {}

        if compute_data[compute_name]["os_users"]:
            for user in compute_data[compute_name]["os_users"]:
                username = user['account-name']
                if username not in added_users:
                    added_users.append(username)

        if compute_data[compute_name]["os_groups"]:
            for group in compute_data[compute_name]["os_groups"]:
                group_name = group['group-name']
                user_list = group['user-list']
                user_list_action = group['user-list-action']

                for user in user_list:
                    if user_list_action == 'add':
                        added_groups.setdefault(user, []).append(group_name)
                    elif user_list_action == 'remove':
                        removed_users.setdefault(user, []).append(group_name)

    report.set_data({
        'hostnames': list(state_data.values()),  # Store hostnames instead of IPs
        'added_users': added_users,
        'added_groups': added_groups,
        'removed_users': removed_users
    })

    print("\n==================== SUMMARY ====================")
    report.print_data()

except Exception:
    print(f"##vso[task.logissue type=error] {traceback.format_exc()}")
    print(f"##vso[task.complete result=SucceededWithIssues;]Task completed with warnings")
