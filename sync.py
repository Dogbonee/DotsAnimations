#!/usr/bin/env python3
import os
import json
import shutil
import subprocess
from datetime import datetime

# Allow any user to run git operations on the repo without dubious ownership errors
os.environ["GIT_CONFIG_COUNT"] = "1"
os.environ["GIT_CONFIG_KEY_0"] = "safe.directory"
os.environ["GIT_CONFIG_VALUE_0"] = "*"

REPO_PATH = "/home/hermes/repos/DotsAnimations"
ANIM_REPO_PATH = os.path.join(REPO_PATH, "animations")
SHARED_PATH = "/home/caleb/shared/animations"
MANIFEST_PATH = os.path.join(REPO_PATH, "manifest.json")

def run(cmd, cwd=None):
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return None
    return result.stdout.strip()

def sync():
    # 1. Update repo first
    run("git pull origin main", cwd=REPO_PATH)

    # 2. Find new files or check if activeAnimation needs advancing
    shared_files = {f for f in os.listdir(SHARED_PATH) if f.endswith(".dots")}
    repo_files = {f for f in os.listdir(ANIM_REPO_PATH) if f.endswith(".dots")}
    new_files = list(shared_files - repo_files)

    # Helper key to sort by date:
    # - New format with year (e.g. "10_22_26.dots" -> (2026, 10, 22))
    # - Legacy format without year (e.g. "10_13.dots" -> (2026, 10, 13))
    # Ignore non-dated animations like animation.dots, non_animation.dots
    def sort_key(filename):
        base = filename[:-5] if filename.endswith(".dots") else filename
        parts = base.split("_")
        if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit() and parts[2].isdigit():
            month, day, year = int(parts[0]), int(parts[1]), int(parts[2])
            if year < 100:
                year += 2000
            return (year, month, day)
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            # Legacy files created prior to the year naming specification are from 2026
            return (2026, int(parts[0]), int(parts[1]))
        return None

    # Filter to valid dated animation files
    dated_shared = [f for f in shared_files if sort_key(f) is not None]
    dated_shared.sort(key=sort_key)
    if not dated_shared:
        print("No dated animations found in shared.")
        return

    # 3. Copy any new files over
    for f in new_files:
        shutil.copy2(os.path.join(SHARED_PATH, f), os.path.join(ANIM_REPO_PATH, f))

    # 4. Check active animation against available animations
    with open(MANIFEST_PATH, 'r') as f:
        data = json.load(f)

    current_active = os.path.basename(data.get('activeAnimation', ''))

    # Determine target animation
    dated_new = [f for f in new_files if sort_key(f) is not None]
    if dated_new:
        dated_new.sort(key=sort_key)
        target = dated_new[0]
    else:
        # Check if there is an animation newer than current_active
        curr_key = sort_key(current_active)
        if curr_key is None:
            target = dated_shared[-1]
        else:
            newer = [f for f in dated_shared if sort_key(f) > curr_key]
            if newer:
                target = newer[0]
            else:
                # Check for uncommitted or unpushed changes before exiting
                git_status = run("git status --porcelain", cwd=REPO_PATH)
                unpushed = run("git cherry -v", cwd=REPO_PATH)
                if git_status or unpushed:
                    if git_status:
                        run("git add .", cwd=REPO_PATH)
                        run("git commit -m 'Add new animations from shared'", cwd=REPO_PATH)
                    run("git push origin main", cwd=REPO_PATH)
                    print(f"Pushed pending changes. Active animation is {current_active}.")
                    return
                print(f"Already on latest active animation ({current_active}). Nothing to do.")
                return

    data['activeAnimation'] = f"https://github.com/Dogbonee/DotsAnimations/raw/refs/heads/main/animations/{target}"

    with open(MANIFEST_PATH, 'w') as f:
        json.dump(data, f, indent=4)
        
    # 6. Commit and Push
    run("git add .", cwd=REPO_PATH)
    run("git commit -m 'Add new animations from shared'", cwd=REPO_PATH)
    run("git push origin main", cwd=REPO_PATH)
    print(f"Synced {len(new_files)} files. Set activeAnimation to {target}.")

if __name__ == "__main__":
    sync()
