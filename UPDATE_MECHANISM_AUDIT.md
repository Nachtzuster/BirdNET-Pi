# BirdNET-Pi Update Mechanism Audit

## Summary
This document provides a comprehensive audit of how BirdNET-Pi determines where and how it downloads updates, and documents the changes made to point all update mechanisms to the YvedD/BirdNET-Pi-MigCount repository.

## Update Mechanism Overview

### Primary Update Script: `scripts/update_birdnet.sh`
The main update script that handles software updates. It:
1. Uses `git fetch` to retrieve updates from a remote repository
2. Defaults to using the `origin` remote and `main` branch
3. Can be called manually or automatically via cron job
4. Performs the following operations:
   - Fetches latest changes from remote
   - Switches to the specified branch tracking the remote
   - Executes pre-update and post-update scripts

**Key variables:**
- `remote="origin"` (line 18) - The git remote to fetch from
- `branch="main"` (line 19) - The git branch to track

**How it works:**
The script uses standard git commands to pull updates from the repository origin. Since the git remote `origin` is already configured to point to `https://github.com/YvedD/BirdNET-Pi-MigCount`, the update mechanism automatically pulls from the correct repository.

### Automatic Updates: `templates/automatic_update.cron`
A cron job that runs weekly (Sundays at 3:00 AM) to automatically update the system:
```
0 3 * * 0 $USER /usr/local/bin/update_birdnet.sh -a >/dev/null 2>&1
```

### Initial Installation: `newinstaller.sh`
The installer that clones the repository during initial setup (line 47):
```bash
git clone -b $branch --depth=1 https://github.com/YvedD/BirdNET-Pi-MigCount.git ${HOME}/BirdNET-Pi
```

## Files Modified to Use YvedD Repository

### 1. `scripts/install_helpers.sh`
**Changed:** Line 4
**From:** `BASE_URL=https://github.com/Nachtzuster/BirdNET-Pi/releases/download/v0.1/`
**To:** `BASE_URL=https://github.com/YvedD/BirdNET-Pi-MigCount/releases/download/v0.1/`

**Purpose:** This function downloads TensorFlow Lite runtime wheels from GitHub releases. Updated to use YvedD's repository for release downloads.

### 2. `scripts/system_controls.php`
**Changed:** Line 68
**From:** `<a href="https://github.com/Nachtzuster/BirdNET-Pi/commit/<?php echo $curr_hash; ?>" target="_blank">`
**To:** `<a href="https://github.com/YvedD/BirdNET-Pi-MigCount/commit/<?php echo $curr_hash; ?>" target="_blank">`

**Purpose:** Displays the current running version in the web UI with a link to the GitHub commit. Updated to link to YvedD's repository.

### 3. `homepage/index.php`
**Changed:** Lines 31 and 33
**From:** `https://github.com/Nachtzuster/BirdNET-Pi.git`
**To:** `https://github.com/YvedD/BirdNET-Pi-MigCount`

**Purpose:** Logo link on the homepage that points to the GitHub repository. Updated to point to YvedD's repository.

### 4. `README.md`
**Changed:** Line 144
**From:** `git remote add origin https://github.com/Nachtzuster/BirdNET-Pi.git`
**To:** `git remote add origin https://github.com/YvedD/BirdNET-Pi-MigCount.git`

**Purpose:** Migration instructions for users switching to this repository fork. Updated to show correct repository URL.

## Verification

### Current Git Configuration
The repository is already correctly configured:
```bash
$ git remote -v
origin  https://github.com/YvedD/BirdNET-Pi-MigCount (fetch)
origin  https://github.com/YvedD/BirdNET-Pi-MigCount (push)
```

### How Updates Work
1. **Manual Update:** Users run `/usr/local/bin/update_birdnet.sh` which fetches from the origin remote
2. **Automatic Update:** Cron job runs weekly calling `update_birdnet.sh -a`
3. **Git Operations:** The script performs:
   - `git fetch origin main` - Fetches latest changes from YvedD repository
   - `git switch -C main --track origin/main` - Switches to and tracks the main branch

## Files That Reference Other Repositories (Not Changed)

Several files contain references to the original `mcguirepr89/BirdNET-Pi` repository in documentation and comments. These are intentionally left unchanged as they:
1. Reference the original upstream project for attribution
2. Point to wiki/discussion pages that contain general BirdNET-Pi information
3. Are in documentation files explaining the project's origins

Examples:
- `README.md` - Contains links to original project wiki and discussions
- Documentation files in `docs/` directory

## Conclusion

The BirdNET-Pi update mechanism now fully points to `https://github.com/YvedD/BirdNET-Pi-MigCount`. All critical files have been updated:
- ✅ Update script uses git origin (already configured correctly)
- ✅ Release downloads point to YvedD repository
- ✅ Web UI links point to YvedD repository
- ✅ Homepage links point to YvedD repository
- ✅ Migration instructions updated

The system will now download all updates from the YvedD/BirdNET-Pi-MigCount repository on the main branch.
