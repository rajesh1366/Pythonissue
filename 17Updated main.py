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
            raise ValueError(f'Error loading YAML file: {file_path}')

class JsonLoader:
    @staticmethod
    def load(file_path):
        try:
            with open(file_path, 'r') as file:
                return json.load(file)
        except Exception:
            raise ValueError(f'Error loading JSON file: {file_path}')

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
        print(f'Parsing file: {computeFilePath}')
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
        print(f'Parsing file: {stateFilePath[0]}')
        data = {}
        json_loader = JsonLoader()
        state_file = json_loader.load(stateFilePath[0])

        if state_file:
            compute_configs = state_file.get('compute_configs', [])
            for compute in compute_configs:
                compute_name = compute['name'].lower()
                hostnames = compute.get('hostnames', [])  # Use hostnames instead of IPs
                data[compute_name] = hostnames

        return data

class Report:
    def __init__(self):
        self.data = {}

    def print_data(self):
        t1 = PrettyTable(['Hosts'])
        for host in self.data.get('hostnames', []):
            t1.add_row([host])
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

def generate_json(compute_data, state_data):
    user_json = {
        "deploy_artifact": "https://artifactory.global.standardchartered.com/artifactory/generic-sc-release_lo",
        "script": "win_user_action.ps1",
        "build_id": 856825,
        "build_local_path": "create-group-win-ps1",
        "listOfNodes": []
    }

    group_json = {
        "deploy_artifact": "https://artifactory.global.standardchartered.com/artifactory/generic-sc-release_lo",
        "script": "win_group_action.ps1",
        "build_id": 856825,
        "build_local_path": "create-group-win-ps1",
        "listOfNodes": []
    }

    for compute_name, hostnames in state_data.items():
        if compute_name not in compute_data:
            continue

        os_type = compute_data[compute_name].get("os", "")
        if os_type != "windows":
            print(f'##vso[task.logissue type=warning]{compute_name} is not a Windows machine. Skipping...')
            continue

        print(f'Processing Host: {compute_name} | Hostnames: {hostnames}')

        added_users = []
        added_groups = {}

        user_args = []
        group_args = []

        if compute_data[compute_name]["os_users"]:
            for user in compute_data[compute_name]["os_users"]:
                username = user['account-name']
                description = user['account-desc']
                rdp = 'true' if user['logon-type'] == 'rdp' else 'false'

                if username not in added_users:
                    added_users.append(username)

                user_args.append(f"create {username}|{description}")

        if compute_data[compute_name]["os_groups"]:
            for group in compute_data[compute_name]["os_groups"]:
                group_name = group['group-name']
                description = group['group-desc']
                user_list = group['user-list']
                user_list_action = group['user-list-action']

                for user in user_list:
                    if user_list_action == 'add':
                        if group_name not in added_groups.setdefault(user, []):
                            added_groups[user].append(group_name)
                    elif user_list_action == 'remove':
                        added_groups.setdefault(user, []).remove(group_name)

                group_args.append(f"create {group_name}|{description}")

        user_json["listOfNodes"].append({
            "targetNodes": ",".join(hostnames),
            "task arguments": " ".join(user_args)
        })

        group_json["listOfNodes"].append({
            "targetNodes": ",".join(hostnames),
            "task arguments": " ".join(group_args)
        })

    with open("windows_users.json", "w") as user_file:
        json.dump(user_json, user_file, indent=4)

    with open("windows_groups.json", "w") as group_file:
        json.dump(group_json, group_file, indent=4)

    print("JSON files created successfully!")

try:
    parser = Parser()
    json_loader = JsonLoader()

    computeFilePath = os.getenv("computeFilePath")
    stateFilePath = os.getenv("stateFilePath")

    compute_data = parser.parse_compute(computeFilePath)
    state_data = parser.parse_state(glob(stateFilePath))

    generate_json(compute_data, state_data)

    report = Report()
    report.set_data({
        'hostnames': state_data,
        'added_users': [],
        'added_groups': {},
        'removed_users': {}
    })
    report.print_data()

except Exception as e:
    print(f'##vso[task.logissue type=error] {traceback.format_exc()}')
    print(f'##vso[task.complete result=SucceededWithIssues;] Task completed with warnings')
