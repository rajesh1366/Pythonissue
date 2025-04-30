
import os
import yaml
import json
import subprocess
from prettytable import PrettyTable
import traceback
from glob import glob


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
                states = compute.get('vm_states', [])
                arr_ips = []

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
        result = subprocess.run(command, capture_output=True, text=True)
        if result.stderr:
            self.errors.append(result.stderr)
        return result.stdout if result.stdout else ""


class Report:
    data = {}

    def print_data(self):
        t1 = PrettyTable(['Hosts'])
        for ip in self.data.get('ip_addresses', []):
            t1.add_row([ip])
        print(t1)

        print('Added Users:')
        t2 = PrettyTable(['User', 'Group'])
        for user in self.data.get('added_users', []):
            groups = ", ".join(self.data.get('added_groups', {}).get(user, []))
            t2.add_row([user, groups])
        print(t2)

        print('Removed Users:')
        t3 = PrettyTable(['User', 'Group'])
        for user in self.data.get('removed_users', []):
            groups = ", ".join(self.data.get('removed_users', {}).get(user, []))
            t3.add_row([user, groups])
        print(t3)

    def set_data(self, value):
        self.data = value


try:
    parser = Parser()
    json_loader = JsonLoader()

    computeFilePath = os.getenv("computeFilePath")
    stateFilePath = os.getenv("stateFilePath")
    existingGroupsPath = os.getenv("existingGroupsPath")

    compute_data = parser.parse_compute(computeFilePath)
    state_data = parser.parse_state(glob(stateFilePath))
existing_groups = json_loader.load(existingGroupsPath)
    terminal = Terminal()

    remote_ssh_user = os.getenv("remoteSshUser")
    remote_ssh_password = os.getenv("remoteSshPassword")
    remote_path = os.getenv("remotePath")
    new_user_password = os.getenv("newUserPassword")

    report = Report()

    # Run script for each compute
    for compute_name in state_data:
        if compute_name not in compute_data:
            continue

        if "os" not in compute_data[compute_name]:
            continue

        if compute_data[compute_name]["os"] != 'windows':
            print(f'##vso[task.logissue type=warning]{compute_name} is not a Windows machine. Skipping....')
            continue

        print('===== INPUTS =====')
        print(f'Hostname: {compute_name} | IPs: {state_data[compute_name]}')

        added_users = []
        added_groups = {}
        removed_users = {}

        for remote_ip in state_data[compute_name]:
            # Copy PowerShell scripts to the remote machine
            command = [
                "sshpass", "-p", remote_ssh_password,
                "scp", "-o", "LogLevel=error",
                "create-user.ps1", "create-group.ps1", "checker.ps1",
                f"{remote_ssh_user}@{remote_ip}:{remote_path}"
            ]
            terminal.run_command(command)

            add_users_data = []
            add_groups_data = []
            modified_groups = []

            # Prepare user data
            if compute_data[compute_name]["os_users"]:
                for user in compute_data[compute_name]["os_users"]:
                    username = user['account-name']
                    description = user['account-desc']
                    rdp = 'true' if user['logon-type'] == 'rdp' else 'false'

                    if username not in added_users:
                        added_users.append(username)

                    add_users_data.append({
                        'username': username,
                        'description': description,
                        'rdp': rdp,
                        'password': new_user_password
                    })

            # Prepare group data
            if compute_data[compute_name]["os_groups"]:
                for group in compute_data[compute_name]["os_groups"]:
                    group_name = group['group-name']
                    description = group['group-desc']
                    user_list = group['user-list']
                    user_list_action = group['user-list-action']

                    # Prepare data for the report
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

            # Convert data to JSON and escape it
            escaped_add_users_data = json.dumps(add_users_data).replace('"', '\\"')
            escaped_add_groups_data = json.dumps(add_groups_data).replace('"', '\\"')
            escaped_existing_groups_data = json.dumps(existing_groups).replace('"', '\\"')
            escaped_modified_groups = json.dumps(modified_groups).replace('"', '\\"')

            print(f'Creating users and groups for {remote_ip}')
            print(f'Users: {escaped_add_users_data}')
            print(f'Groups: {escaped_add_groups_data}')

            # Run PowerShell scripts on the remote machine
            command = [
                "sshpass", "-p", remote_ssh_password,
                "ssh", "-o", "LogLevel=error", f"{remote_ssh_user}@{remote_ip}",
                f"powershell -ExecutionPolicy Bypass -File {remote_path}\\create-user.ps1 '{escaped_add_users_data}'; "
                f"powershell -ExecutionPolicy Bypass -File {remote_path}\\create-group.ps1 '{escaped_add_groups_data}' "
                f"'{escaped_existing_groups_data}'; "
                f"powershell -ExecutionPolicy Bypass -File {remote_path}\\checker.ps1 '{escaped_modified_groups}';"
            ]
            out = terminal.run_command(command)

            print('\n==== USERS/GROUPS OUTPUT ====')
            print(out)

            # Remove scripts from the remote machine
            command = [
                "sshpass", "-p", remote_ssh_password,
                "ssh", "-o", "LogLevel=error", f"{remote_ssh_user}@{remote_ip}",
                f'powershell -Command "Remove-Item {remote_path}\\create-user.ps1, {remote_path}\\create-group.ps1, {remote_path}\\checker.ps1 -Force"'
            ]
            terminal.run_command(command)

            # Prepare report data
            report.set_data({
                'ip_addresses': state_data[compute_name],
                'added_users': added_users,
                'added_groups': added_groups,
                'removed_users': removed_users
            })

    print('\n===== SUMMARY =====')
    report.print_data()

    print('')

    # Print warnings if any
    errors = terminal.get_errors()
    if errors:
        print('##vso[task.logissue type=warning] WARNINGS:')
        for err in errors:
            print(err)

except Exception:
    print(f'##vso[task.logissue type=error] {traceback.format_exc()}')
    print(f'##vso[task.complete result=SucceededWithIssues;] Task completed with warnings')

