# Update System Plan

## Goals
- Distinguish "new stable release available" from "new commits available on the tracked code line".
- Let the installer and settings UI store a durable update preference.
- Provide a safe, admin-only update workflow that can eventually apply updates from the web UI.
- Keep stable users on the lowest-risk path by default.

## Update channels
- `stable`
  Install or update to the newest non-prerelease tag approved for general users.
- `prerelease`
  Allow release candidates such as `vX.Y.Z-rcN`.
- `edge`
  Follow the latest branch tip for the tracked development line.

## Current persisted settings
- `UPDATE_CHANNEL`
  Stored in `birdnet.conf` and exposed through the FastAPI config API and Svelte settings page.

## Current installer behavior
- `stable`
  Resolves and installs the latest stable release tag from the remote repository.
- `prerelease`
  Resolves and installs the latest prerelease-or-stable tag, with explicit opt-in.
- `edge`
  Installs the selected branch head, with explicit opt-in.

## Recommended future metadata model
- Installed state:
  - `service_version`
  - `git_hash`
  - `git_branch`
  - `update_channel`
- Available update state:
  - latest stable tag
  - latest prerelease tag
  - tracked branch head hash
  - changelog / breaking-change marker

## Recommended API shape
- `GET /api/system/update-preferences`
  Return persisted update channel and any future advanced targeting values.
- `PUT /api/system/update-preferences`
  Update channel selection.
- `GET /api/system/update-status`
  Return:
  - installed version/hash/branch
  - update channel
  - latest stable release
  - latest prerelease release
  - branch-head status
  - whether update is available
  - whether the recommendation is a release update or branch update
- `POST /api/system/update-check`
  Force refresh remote metadata.
- `POST /api/system/apply-update`
  Admin-only action to apply a selected target.

## Recommended script interface
- New script:
  `scripts/apply_update.sh --channel stable|prerelease|edge [--target <tag-or-branch>] [--yes]`
- Responsibilities:
  1. Preflight checks
  2. Optional backup
  3. Fetch tags and branch refs
  4. Resolve target for selected channel
  5. Checkout target safely
  6. Install backend dependencies
  7. Build frontend
  8. Run host update snippets
  9. Reload services
  10. Verify health and version metadata

## Safety rules
- Default to `stable` for new installs.
- Require an explicit confirmation when moving from `stable` to `prerelease` or `edge`.
- Show release notes / breaking-change indicators before applying non-stable updates.
- Create or verify a backup before in-place update.
- Preserve previous commit/tag reference for rollback guidance.

## Known gap in current repo
- `update_birdnet.sh` is still branch-oriented and does not yet implement tag-aware release updates or the full modern web rebuild path.
