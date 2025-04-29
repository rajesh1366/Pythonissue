import os
import yaml
import json
import subprocess
import traceback
import argparse
from glob import glob
from prettytable import PrettyTable

class YamlLoader:
    @staticmethod
    def load(file_path):
        try:
            with open(file_path, 'r') as file:
                return yaml.safe_load(file)
        except Exception as e:
            raise ValueError(f'Error loading YAML file: {file_path}\n{str(e)}')

class JsonLoader:
    @staticmethod
    def load(file_path):
        try:
            with open(file_path, 'r') as file:
                return json.load(file)
        except Exception as e:
            raise ValueError(f'Error loading JSON file: {file_path}\n{str(e)}')

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
        yaml_loader = YamlLoader()
        compute_mf = yaml_loader.load(computeFilePath)

        if compute_mf and 'compute-config' in compute_mf:
            for compute in compute_mf['compute-config']:
                compute_name = compute['name'].lower()
                os_type = self.parse_os_name(compute['os']).lower()
                
                data[compute_name] = {
                    'os': os_type,
                    'os_groups': compute.get('win-os-groups', []),
                    'os_users': compute.get('win-os-accounts', [])
                }
        return data

    def parse_state(self, stateFilePath):
        print(f'Parsing state file: {stateFilePath}')
        data = {}
        json_loader = JsonLoader()
        state_file = json_loader.load(stateFilePath)

        if state_file and 'compute_configs' in state_file:
            for compute in state_file['compute_configs']:
                compute_name = compute['name'].lower()
                states = compute.get('vm_states', [])
                arr_ips = []

                if states:
                    for state in states:
                        ip_addresses = state.get('ip_addresses', [])
                        for item in ip_addresses:
                            arr_ips.append(item['ip_address'])

                data[compute_name] = arr_ips
        return data

class Terminal:
    errors = []

    def get_errors(self):
        return self.errors

    def run_command(self, command):
        try:
            result = subprocess.run(command, capture_output=True, text=True)
            if result.stderr:
                self.errors.append(result.stderr)
            return result.stdout.strip() if result.stdout else ""
        except Exception as e:
            self.errors.append(str(e))
            return ""

class Report:
    data = {}

    def print_data(self):
        print("\n==================== SUMMARY ====================\n")
        
        # Hosts table
        t1 = PrettyTable(['Hosts'])
        for ip in self.data.get('ip_addresses', []):
            t1.add_row([ip])
        print(t1)

        # Added Users
        print("\nAdded Users:")
        t2 = PrettyTable(['User', 'Group'])
        for user in self.data.get('added_users', []):
            groups = ', '.join(self.data.get('added_groups', {}).get(user, []))
            t2.add_row([user, groups])
        print(t2)

        # Removed Users
        print("\nRemoved Users:")
        t3 = PrettyTable(['User', 'Group'])
        for user in self.data.get('removed_users', []):
            groups = ', '.join(self.data.get('removed_users', {}).get(user, []))
            t3.add_row([user, groups])
        print(t3)

    def set_data(self, value):
        self.data = value

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip-addresses", required=True, help="List of IP addresses")
    parser.add_argument("--username", required=True, help="Username for authentication")
    parser.add_argument("--password", required=True, help="Password for authentication")
    parser.add_argument("--bootstrap-config", required=True, help="Bootstrap config")
    parser.add_argument("--controlm-premise", required=True, help="Control-M premise")
    parser.add_argument("--os_type", required=True, help="OS type")

    args = parser.parse_args()

    try:
        computeFilePath = os.getenv("computeFilePath")
        stateFilePath = os.getenv("stateFilePath")
        existingGroupsPath = os.getenv("existingGroupsPath")

        parser = Parser()
        json_loader = JsonLoader()

        compute_data = parser.parse_compute(computeFilePath)
        state_data = parser.parse_state(stateFilePath)
        existing_groups = json_loader.load(existingGroupsPath)

        terminal = Terminal()
        report = Report()

        added_users = []
        added_groups = {}
        removed_users = {}

        for compute_name in state_data:
            if compute_name not in compute_data or "os" not in compute_data[compute_name]:
                continue

            if compute_data[compute_name]["os"] != "windows":
                print(f'##vso[task.logissue type=warning]{compute_name} is not a Windows machine. Skipping...')
                continue

            print(f'\nProcessing Hostname: {compute_name} | IPs: {state_data[compute_name]}')

            add_users_data = []
            add_groups_data = []
            modified_groups = []

            # Process users
            for user in compute_data[compute_name].get("os_users", []):
                username = user['account-name']
                description = user['account-desc']
                rdp = 'true' if user['logon-type'] == 'rdp' else 'false'

                if username not in added_users:
                    added_users.append(username)

                add_users_data.append({
                    'username': username,
                    'description': description,
                    'rdp': rdp,
                    'password': args.password
                })

            # Process groups
            for group in compute_data[compute_name].get("os_groups", []):
                group_name = group['group-name']
                description = group['group-desc']
                user_list = group['user-list']
                user_list_action = group['user-list-action']

                for user in user_list:
                    if user_list_action == 'add':
                        added_groups.setdefault(user, []).append(group_name)
                    elif user_list_action == 'remove':
                        removed_users.setdefault(user, []).append(group_name)

                add_groups_data.append({
                    'groupName': group_name,
                    'description': description,
                    'userList': user_list,
                    'userListAction': user_list_action
                })
                modified_groups.append(group_name)

            report.set_data({
                'ip_addresses': state_data[compute_name],
                'added_users': added_users,
                'added_groups': added_groups,
                'removed_users': removed_users
            })

        report.print_data()
        
        errors = terminal.get_errors()
        if errors:
            print('##vso[task.logissue type=warning]========= WARNINGS ========')
            for err in errors:
                print(err)

    except Exception:
        print(f'##vso[task.logissue type=error] {traceback.format_exc()}')
        print(f'##vso[task.complete result=SucceededWithIssues;]Task completed with warnings')

if __name__ == "__main__":
    main()
