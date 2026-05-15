# V1 Release Context - 2026-05-11

This note captures the current release state, decisions, and next steps so work can continue cleanly if chat context compacts.

## Current State

- The modern FastAPI + Svelte app now includes:
  - restored settings parity (`INFO_SITE`, `IMAGE_PROVIDER`, `FLICKR_API_KEY`, `FLICKR_FILTER_EMAIL`)
  - restored system controls (shutdown, clear-all-data, per-service enable/disable)
  - Weekly Report at `/reports/weekly`
  - Daily Report work, now considered in-scope and intended to ship
  - admin-only File Manager at `/files`, linked from Library
  - Live Logs in-app
- The local feature work has been pushed and is considered good to include for v1.
- Installer/runtime cleanup is now in place for the supported deployment path:
  - generated Caddy config points at the FastAPI app directly
  - legacy `/stats`, `/log`, `/terminal`, and older page exposure are removed from the supported runtime path
  - dropped services (`birdnet_stats`, `birdnet_log`, `web_terminal`) are no longer part of the supported modern service surface
- Script cleanup is also in place for remaining active legacy dependencies:
  - `scripts/weekly_report.sh` now uses the FastAPI weekly report notification endpoint
  - `scripts/disk_check.sh` no longer relies on the retired stats page side effect to rebuild `disk_check_exclude.txt`
  - `scripts/print_diagnostic_info.sh` now targets the supported service set, including `birdnet-web`
- Local verification status on 2026-05-11:
  - `python3 -m compileall backend/app` passes
  - `npm run check` passes
  - `npm run build` passes
  - `pytest` is not installed in the local workspace, so backend tests have not been run locally from this environment

## Key V1 Decisions

- Ship the modern reports features, including Daily Report and Weekly Report.
- Keep File Manager.
- Do not ship Adminer.
- Do not ship Web Terminal.
- Treat the modern app as the supported product surface.
- The installer/runtime should no longer wire older legacy routes or retired sidecar paths back into the deployed system.

## Current Focus

The next release blocker is CI/test hardening for the modern stack.

The active runtime and script paths that were still depending on the retired web stack have been replaced. There are still older compatibility code paths left in a few installer and migration scripts, but they are no longer the primary blocker for moving forward with CI.

## Installer Pass Summary

Completed in this pass:

1. Simplified generated Caddy configs to the modern shape:
   - reverse proxy to `localhost:8080`
   - modern auth-protected app/API surfaces only
   - no retired sidecar web handlers
   - no supported `/views`, `/system-info`, `/terminal`, `/log`, or `/stats` runtime exposure

2. Cleaned installer/runtime scripts:
   - stopped symlinking retired legacy web files into `EXTRACTED`
   - stopped reinstalling dropped sidecars
   - aligned the supported service set with the modern admin UI

3. Cleaned reset/rebuild flows:
   - clear-all-data now recreates only the directories and links needed by the modern app and recording pipeline

4. Replaced active script-level legacy dependencies:
   - weekly report notification rendering now comes from FastAPI
   - disk purge protection refresh now comes from a native helper script instead of page side effects
   - diagnostics now target `birdnet-web` and the modern service set

## Next Steps

1. Add or strengthen CI for the modern stack:
   - frontend `npm run check`
   - frontend `npm run build`
   - backend tests in an environment that installs `pytest`
2. Review remaining legacy repo-only code and decide what should be deleted now versus left as historical/migration material.
3. Deploy to the target host.
4. Run a live parity and exposure audit against the deployed host.
5. Finalize release metadata and tag `1.0.0` only after deployment matches the repo state.
