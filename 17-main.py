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
            raise ValueError(f'Error loading yaml file: {file_path}')

class JsonLoader:
    @staticmethod
    def load(file_path):
        try:
            with open(file_path, 'r') as file:
                return json.load(file)
        except Exception:
            raise ValueError(f'Error loading json file: {file_path}')

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
            computes = compute_mf.get('compute-config', [])  # Handle missing key
            if computes:
                for compute in computes:
                    compute_name = compute['name'].lower()
                    os = self.parse_os_name(compute['os']).lower()
                    data[compute_name] = {
                        'os': os,
                        'os_groups': compute.get('win-os-groups', []),
                        'os_users': compute.get('win-os-accounts', [])
                    }
        return data

    def parse_state(self, stateFilePath):
        print(f'Parsing file: {stateFilePath[0]}') # Access the first element of the list
        data = {}
        json_loader = JsonLoader()
        state_file = json_loader.load(stateFilePath[0])
        if state_file:
            compute_configs = state_file.get('compute_configs', []) # Handle missing key
            if compute_configs:
                for compute in compute_configs:
                    compute_name = compute['name'].lower()
                    states = compute.get('vm_states', []) # Handle missing key
                    arr_ips = []
                    if states:
                        for state in states:
                            ip_addresses = state.get('ip_addresses', []) # Handle missing key
                            if ip_addresses:
                                for item in ip_addresses:
                                    arr_ips.append(item['ip_address'])
                    data[compute_name] = arr_ips
        return data

class Terminal:
    errors = []

    def get_errors(self):
        return self.errors

    def run_command(self, command):
        result = subprocess.run(command, capture_output=True, text=True, shell=True) # Added shell=True
        if result.stderr:
            self.errors.append(result.stderr)
        if result.stdout:
            return result.stdout
        return None  # Return None if no stdout

class Report:
    data = {}

    def print_data(self):
        # ... (same as before)

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

    remote_ssh_user = os.getenv("remoteSshUser")  # Not used anymore
    remote_ssh_password = os.getenv("remoteSshPassword") # Not used anymore
    remote_path = os.getenv("remotePath") # Not used anymore
    new_user_password = os.getenv("newUserPassword")

    report = Report()

    for compute_name in state_data:
        if compute_name not in compute_data:
            continue

        if "os" not in compute_data[compute_name] or compute_data[compute_name]["os"] != 'windows':
            print(f'##vso[task.logissue type=warning]{compute_name} is not a Windows machine. Skipping...')
            continue

        print('======= INPUTS ========')
        print(f'Hostname: {compute_name} | IPs: {state_data[compute_name]}')

        added_users = []
        added_groups = {}
        removed_users = {}

        for remote_ip in state_data[compute_name]:
            # Construct PowerShell command directly
            ps_command = f"""
            # Your PowerShell script content here, using $add_users_data and $add_groups_data
            # Example:
            $add_users_data = @{add_users_data} | ConvertFrom-Json
            $add_groups_data = @{add_groups_data} | ConvertFrom-Json
            # ... rest of your PowerShell logic
            """

            add_users_data = []
            add_groups_data = []
            modified_groups = []

            # ... (rest of the data preparation logic, same as before)

            add_users_data_json = json.dumps(add_users_data)
            add_groups_data_json = json.dumps(add_groups_data)
            existing_groups_data_json = json.dumps(existing_groups)
            modified_groups_json = json.dumps(modified_groups)


            # Inject the JSON data into the PowerShell command
            ps_command = ps_command.replace("@{add_users_data}", add_users_data_json).replace("@{add_groups_data}", add_groups_data_json)
            # You can also inject $existing_groups_data_json and $modified_groups_json if needed.

            print(f'Creating users and groups for {remote_ip}')
            print(f'Users: {add_users_data_json}')
            print(f'Groups: {add_groups_data_json}')

            out = terminal.run_command(["powershell", "-Command", ps_command]) # Run PowerShell directly

            print('======= USERS/GROUPS ========')
            print(out)

            report.set_data({
                'ip_addresses': state_data[compute_name],
                'added_users': added_users,
                'added_groups': added_groups,
                'removed_users': removed_users
            })

            print('')

        print('===========================SUMMARY=====')
        report.print_data()
        print('')

        errors = terminal.get_errors()
        if errors:
            print('##vso[task.logissue type=warning]=========WARNINGS=======')
            for err in errors:
                print(err)

except Exception:
    print(f'##vso[task.logissue type=error] {traceback.format_exc()}')
    print(f'##vso[task.complete result=SucceededWithIssues;]Task completed with warnings')

