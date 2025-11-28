#!/usr/bin/env python3
"""
Fetch all Azure DevOps repositories and project environments, find environments matching
'production_v2', extract a 5-digit ciid from each repo name, and write results to an Excel file.

Usage:
    python ado_repos_production_v2_to_excel.py \
        --org myOrg --project myProject --pat MY_PERSONAL_ACCESS_TOKEN \
        --out output.xlsx

You may also set AZDO_ORG, AZDO_PROJECT, AZDO_PAT env vars and omit those args.
"""

import os
import re
import argparse
import requests
import math
import pandas as pd
from typing import List, Dict

API_VERSION = "7.1-preview.1"  # works for repos & environments endpoints

def azdo_get(url: str, pat: str, params: dict = None):
    """Simple GET with PAT (basic)."""
    headers = {
        "Accept": "application/json"
    }
    # Basic auth: username can be empty, password is PAT
    resp = requests.get(url, headers=headers, auth=("", pat), params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()

def get_all_repos(org: str, project: str, pat: str) -> List[Dict]:
    """Return list of repo dicts for the project."""
    url = f"https://dev.azure.com/{org}/{project}/_apis/git/repositories"
    params = {"api-version": API_VERSION}
    data = azdo_get(url, pat, params=params)
    return data.get("value", [])

def get_all_environments(org: str, project: str, pat: str) -> List[Dict]:
    """
    Return list of environment dicts for the project.
    Environments endpoint: distributedtask/environments
    """
    url = f"https://dev.azure.com/{org}/{project}/_apis/distributedtask/environments"
    params = {"api-version": API_VERSION, "$top": 1000}  # try to get many; will still return 'value'
    data = azdo_get(url, pat, params=params)
    return data.get("value", [])

def extract_ciid(repo_name: str) -> str:
    """
    Try to extract first occurrence of 5 consecutive digits from repo name.
    If none, fallback to first 5 characters (trimmed). Returns empty string if repo_name empty.
    """
    if not repo_name:
        return ""
    m = re.search(r"(\d{5})", repo_name)
    if m:
        return m.group(1)
    # fallback: first 5 chars (strip non-alphanumeric)
    fallback = repo_name[:5]
    return fallback

def main(args):
    org = args.org
    project = args.project
    pat = args.pat
    out_file = args.out

    print(f"Connecting to Azure DevOps org='{org}' project='{project}' ...")

    # Fetch repos
    repos = get_all_repos(org, project, pat)
    print(f"Found {len(repos)} repositories.")

    # Fetch environments
    envs = get_all_environments(org, project, pat)
    print(f"Found {len(envs)} environments in project.")

    # filter production_v2 envs (case-insensitive partial match)
    production_envs = [
        e for e in envs
        if "production_v2" in (e.get("name") or "").lower()
    ]
    print(f"Filtered {len(production_envs)} environment(s) matching 'production_v2'.")

    # Map environment id -> name (useful if multiple)
    env_by_id = {e.get("id"): e.get("name") for e in envs}

    rows = []
    for r in repos:
        repo_name = r.get("name", "")
        repo_id = r.get("id", "")
        ciid = extract_ciid(repo_name)

        # If you want to know which production_v2 env(s) are associated with a repo,
        # there is no direct repo->environment link in Azure DevOps standard model.
        # We will report all production_v2 environments in project (same for each repo)
        # and also attempt to find env names that mention the repo name.
        matching_envs_for_repo = []

        # First, envs that contain 'production_v2' anywhere
        for e in production_envs:
            ename = e.get("name") or ""
            # optional: include only those where repo name appears in env name
            if repo_name.lower() in ename.lower() or True:
                matching_envs_for_repo.append(ename)

        rows.append({
            "repoName": repo_name,
            "repoId": repo_id,
            "ciid": ciid,
            "production_v2_envs_count": len(matching_envs_for_repo),
            "production_v2_envs": ", ".join(matching_envs_for_repo) if matching_envs_for_repo else ""
        })

    df = pd.DataFrame(rows, columns=[
        "repoName", "repoId", "ciid", "production_v2_envs_count", "production_v2_envs"
    ])

    # Save to Excel
    df.to_excel(out_file, index=False, engine="openpyxl")
    print(f"Wrote {len(df)} rows to '{out_file}'")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export Azure DevOps repos + production_v2 envs to Excel")
    parser.add_argument("--org", required=False, help="Azure DevOps organization (or collection) name")
    parser.add_argument("--project", required=False, help="Azure DevOps project name")
    parser.add_argument("--pat", required=False, help="Azure DevOps Personal Access Token (PAT)")
    parser.add_argument("--out", default="ado_repos_production_v2.xlsx", help="Output Excel filename")
    args = parser.parse_args()

    # allow env var fallback
    if not args.org:
        args.org = os.environ.get("AZDO_ORG")
    if not args.project:
        args.project = os.environ.get("AZDO_PROJECT")
    if not args.pat:
        args.pat = os.environ.get("AZDO_PAT")

    if not args.org or not args.project or not args.pat:
        parser.error("Missing required details. Provide --org, --project, and --pat, or set AZDO_ORG, AZDO_PROJECT, AZDO_PAT env vars.")

    try:
        main(args)
    except requests.HTTPError as ex:
        print("HTTP error from Azure DevOps API:", ex)
        print("Response body:", getattr(ex.response, "text", ""))
        raise
    except Exception as ex:
        print("Error:", ex)
        raise
