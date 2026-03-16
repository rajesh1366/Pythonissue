import subprocess

# Azure DevOps details
org = "org"
project = "project"
pat = "yourPAT"

# Source repo
source_repo = f"https://{pat}@dev.azure.com/{org}/{project}/_git/source-repo"

# Destination repos
destination_repos = [
    f"https://{pat}@dev.azure.com/{org}/{project}/_git/repo1",
    f"https://{pat}@dev.azure.com/{org}/{project}/_git/repo2",
    f"https://{pat}@dev.azure.com/{org}/{project}/_git/repo3"
]

repo_folder = "repo-sync"

# Clone source repo
subprocess.run(["git", "clone", source_repo, repo_folder])

for i, repo in enumerate(destination_repos):
    remote_name = f"dest{i}"

    subprocess.run([
        "git", "-C", repo_folder,
        "remote", "add", remote_name, repo
    ])

    subprocess.run([
        "git", "-C", repo_folder,
        "push", remote_name, "HEAD:main"
    ])

print("Code successfully pushed to all repositories")
