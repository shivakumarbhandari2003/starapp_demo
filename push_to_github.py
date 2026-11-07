#!/usr/bin/env python3
"""
StarApp GitHub Pusher
Reads GITHUB_TOKEN from .env and pushes all project files to GitHub via GitHub REST API.
Does not require external git binary or third-party packages.
"""

import os
import sys
import json
import base64
import urllib.request
import urllib.error

# Load environment variables from .env if present
def load_env(env_path=".env"):
    config = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    config[key.strip()] = val.strip().strip('"').strip("'")
    return config

def parse_repo_info(repo_str):
    # Handles "https://github.com/owner/repo.git" or "owner/repo"
    s = repo_str.strip()
    if s.endswith(".git"):
        s = s[:-4]
    if "github.com/" in s:
        s = s.split("github.com/")[1]
    s = s.strip("/")
    parts = s.split("/")
    if len(parts) >= 2:
        return parts[0], parts[1]
    raise ValueError(f"Could not parse repository owner and name from '{repo_str}'")

def api_request(url, token, data=None, method=None):
    headers = {
        "Authorization": f"token {token}",
        "User-Agent": "StarApp-GitHub-Pusher",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode("utf-8")
            return json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        raise RuntimeError(f"GitHub API error {e.code} for {url}: {err_msg}")

def get_ignore_patterns():
    patterns = [".env", ".git", "__pycache__", ".vscode", ".idea", "*.pyc"]
    if os.path.exists(".gitignore"):
        with open(".gitignore", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line.rstrip("/"))
    return patterns

def should_ignore(rel_path, ignore_patterns):
    parts = rel_path.replace("\\", "/").split("/")
    for part in parts:
        if part in [".git", "__pycache__", ".env", ".vscode", ".idea"]:
            return True
        if part.endswith(".pyc"):
            return True
    for pat in ignore_patterns:
        if pat.startswith("*.") and rel_path.endswith(pat[1:]):
            return True
        if pat in parts:
            return True
    return False

def push_project(commit_message="Update StarApp files"):
    config = load_env()
    token = config.get("GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN")
    repo_raw = config.get("GITHUB_REPO") or os.environ.get("GITHUB_REPO", "shivakumarbhandari2003/starapp_demo")

    if not token:
        print("Error: GITHUB_TOKEN not found in .env or environment.", file=sys.stderr)
        sys.exit(1)

    owner, repo_name = parse_repo_info(repo_raw)
    base_url = f"https://api.github.com/repos/{owner}/{repo_name}"
    print(f"[*] Preparing push to GitHub: {owner}/{repo_name}")

    # 1. Collect all local files
    ignore_patterns = get_ignore_patterns()
    files_to_upload = []
    root_dir = os.path.abspath(".")

    for r, dirs, files in os.walk(root_dir):
        # Filter directories in-place
        dirs[:] = [d for d in dirs if not should_ignore(d, ignore_patterns)]
        for f in files:
            full_path = os.path.join(r, f)
            rel_path = os.path.relpath(full_path, root_dir).replace("\\", "/")
            if not should_ignore(rel_path, ignore_patterns):
                files_to_upload.append((rel_path, full_path))

    print(f"[*] Found {len(files_to_upload)} files to synchronize.")

    # 2. Upload blobs to GitHub
    tree_items = []
    for rel_path, full_path in files_to_upload:
        try:
            with open(full_path, "rb") as f:
                content_bytes = f.read()
            b64_content = base64.b64encode(content_bytes).decode("ascii")

            blob_resp = api_request(
                f"{base_url}/git/blobs",
                token,
                data={"content": b64_content, "encoding": "base64"},
                method="POST"
            )
            blob_sha = blob_resp["sha"]
            tree_items.append({
                "path": rel_path,
                "mode": "100644",
                "type": "blob",
                "sha": blob_sha
            })
            print(f"  + Uploaded blob: {rel_path}")
        except Exception as e:
            print(f"  ! Failed to upload {rel_path}: {e}", file=sys.stderr)
            raise

    # 3. Create Tree
    print(f"[*] Creating Git tree with {len(tree_items)} elements...")
    tree_resp = api_request(
        f"{base_url}/git/trees",
        token,
        data={"tree": tree_items},
        method="POST"
    )
    new_tree_sha = tree_resp["sha"]
    print(f"[*] New tree SHA: {new_tree_sha}")

    # 4. Get current commit on default branch ('main')
    parent_commits = []
    ref_exists = False
    try:
        ref_data = api_request(f"{base_url}/git/refs/heads/main", token, method="GET")
        parent_commits = [ref_data["object"]["sha"]]
        ref_exists = True
        print(f"[*] Found existing head on 'main': {parent_commits[0]}")
    except Exception:
        print("[*] 'main' branch ref does not exist yet. Creating as initial commit.")

    # 5. Create Commit
    print(f"[*] Creating commit: '{commit_message}'...")
    commit_payload = {
        "message": commit_message,
        "tree": new_tree_sha,
        "parents": parent_commits
    }
    commit_resp = api_request(
        f"{base_url}/git/commits",
        token,
        data=commit_payload,
        method="POST"
    )
    new_commit_sha = commit_resp["sha"]
    print(f"[*] Created commit SHA: {new_commit_sha}")

    # 6. Update or Create Ref
    if ref_exists:
        print("[*] Updating 'refs/heads/main'...")
        api_request(
            f"{base_url}/git/refs/heads/main",
            token,
            data={"sha": new_commit_sha, "force": True},
            method="PATCH"
        )
    else:
        print("[*] Creating 'refs/heads/main'...")
        api_request(
            f"{base_url}/git/refs",
            token,
            data={"ref": "refs/heads/main", "sha": new_commit_sha},
            method="POST"
        )

    print(f"\n[SUCCESS] Successfully pushed all StarApp code to:")
    print(f"          https://github.com/{owner}/{repo_name}")
    print(f"          Commit: {new_commit_sha}")

if __name__ == "__main__":
    msg = sys.argv[1] if len(sys.argv) > 1 else "StarApp: Complete application development with liquid-glass design system"
    push_project(msg)

