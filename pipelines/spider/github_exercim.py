import os
import subprocess
import requests
import time

def get_all_repos(org_name, token=None):
    base_url = f"https://api.github.com/orgs/{org_name}/repos"
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"
    
    all_repos = []
    page = 1
    per_page = 100

    while True:
        params = {
            "page": page,
            "per_page": per_page
        }
        
        response = requests.get(base_url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            print(response.json())
            break

        repos = response.json()
        if not repos:
            break

        all_repos.extend(repos)
        print(f"Fetched page {page}, total repos so far: {len(all_repos)}")

        if len(repos) < per_page:
            break

        page += 1
        time.sleep(1)

    return all_repos

def clone_or_update_repo(repo_url, repo_name, base_path):
    if repo_name not in ["cpp", "rust", "python", "go", "javascript", "java"]:
        return
    repo_path = os.path.join(base_path, repo_name)
    if os.path.exists(repo_path):
        print(f"Updating {repo_name}...")
        try:
            subprocess.run(["git", "-C", repo_path, "pull"], check=True)
        except subprocess.CalledProcessError:
            print(f"Error updating {repo_name}")
    else:
        print(f"Cloning {repo_name}...")
        try:
            subprocess.run(["git", "clone", repo_url, repo_path], check=True)
        except subprocess.CalledProcessError:
            print(f"Error cloning {repo_name}")

# set parameters
org_name = "exercism"
github_token = "xxx"
base_path = "./pipelines/spider/repos/data"  # set base path to save repos

# get all repos
repos = get_all_repos(org_name, github_token)

# ensure base path exists
os.makedirs(base_path, exist_ok=True)

# clone or update each repo
for repo in repos:
    clone_or_update_repo(repo['clone_url'], repo['name'], base_path)

print(f"\nTotal repositories processed: {len(repos)}")

# with open("./repos/data.jsonl", "w") as f:
#     for repo in repos:
#         f.write(
#             {
#                 "name": repo["name"],
#                 "repo_url": repo["clone_url"],
#                 "base_path": base_path + "/" + repo["name"]
#             }
#         )