# BirdNET-Pibird

[![Listen Live](https://img.shields.io/badge/🎧_Listen_Live-durm.pibirds.org-4CAF50?style=for-the-badge)](https://durm.pibirds.org)
[![Powered by](https://img.shields.io/badge/Powered_by-Raspberry_Pi_3B+-C51A4A?style=for-the-badge&logo=raspberrypi)](https://www.raspberrypi.com/)
[![Location](https://img.shields.io/badge/📍-Durham,_NC-blue?style=for-the-badge)](https://durm.pibirds.org)

> *A tiny computer in my backyard is eavesdropping on birds. 24/7. They have no idea.*

Real-time acoustic bird classification running on a Raspberry Pi 3B+, listening to the birds of Durham, North Carolina.

<p align="center">
  <img src="frontend/static/bird.png" alt="Pibird Logo" width="300"/>
</p>

---

## What's This?

This is a modernized fork of [BirdNET-Pi](https://github.com/Nachtzuster/BirdNET-Pi), built around a **modern web stack** for performance, maintainability, and a much better day-to-day operating experience.

**Want to see what's singing right now?** → **[durm.pibirds.org](https://durm.pibirds.org)**

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        BirdNET-Pibird                           │
├─────────────────────────────────────────────────────────────────┤
│  Frontend (SvelteKit + Tailwind CSS)                            │
│  • Modern, responsive UI with dark mode                         │
│  • Real-time detection feed                                     │
│  • Mobile-first design                                          │
├─────────────────────────────────────────────────────────────────┤
│  Backend (FastAPI + Python)                                     │
│  • RESTful API for all operations                               │
│  • Reuses existing BirdNET Python utilities                     │
│  • SQLite database for detections                               │
├─────────────────────────────────────────────────────────────────┤
│  Analysis Pipeline (unchanged from upstream)                    │
│  • BirdNET TensorFlow Lite model                                │
│  • Audio recording & spectrogram generation                     │
│  • BirdWeather integration                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## What Makes This Fork Special

| Feature | Description |
|---------|-------------|
| **Modern Web Stack** | FastAPI backend + SvelteKit frontend |
| **Tailwind CSS** | Single consolidated stylesheet with dark mode support |
| **Mobile-First UI** | Responsive design that works great on phones |
| **Type Safety** | TypeScript frontend + Pydantic backend schemas |
| **Full Species Charts** | Daily charts show *all* species, not just the top 10 |
| **Faster Analysis** | Consolidated analysis pipeline + TFLite 2.17.1 |
| **Backup & Restore** | Never lose your bird data again |
| **Modern Admin UI** | Notifications, advanced settings, live logs, system controls, time/date, and updates in the new interface |
| **Reports & Exports** | Weekly Report plus eBird export from the modern UI |
| **Scoped File Manager** | Admin-only file management for BirdNET-owned media roots |
| **Live Audio + Spectrogram UX** | Dashboard live audio plus compact/expandable spectrogram views where they are most useful |
| **Temporal Zoom** | Pitch-preserved playback presets help reveal fast notes, trills, gaps, and subtle differences in recordings |
| **Local Bird Image Cache** | Wikipedia bird images are cached locally so browsers are not sent directly to Wikimedia asset URLs |
| **Modern Debian** | Bookworm + Trixie support |

<details>
<summary><b>Changes from upstream BirdNET-Pi</b></summary>

**New in this fork:**
- Complete web interface rebuild around FastAPI + SvelteKit
- Tailwind CSS with unified light/dark theme
- RESTful API for all operations
- Improved mobile experience with bottom navigation

**Inherited improvements:**
- Reworked analysis to consolidate analysis/server/extraction
- Daily plot daemon (`daily_plot.py`) avoids expensive startup overhead
- Experimental tmpfs support for transient files  
- Bumped Apprise version for 90+ notification platforms
- Swipe events on Daily Charts (thanks [@croisez](https://github.com/croisez))
- Support for Species range model V2.4 - V2

</details>

---

## Current Web UI Coverage

The modern web app covers the main day-to-day and admin workflows:

- Dashboard with current detections, live audio access, and public status
- Review feed for recent detections and moderation actions
- Library for historical recordings, spectrogram inspection, frequency-shifted clips, and Temporal Zoom playback
- Species and Insights views for trends, charts, date-filtered species lists, and exports
- Weekly Report at `/reports/weekly`
- Settings, Advanced Settings, and System administration
- Live Logs for service log inspection
- Admin-only File Manager at `/files`, linked from Library

Intentional exclusions from earlier admin tooling:

- No Web Terminal
- No Adminer

The File Manager is intentionally scoped to BirdNET-owned directories rather than acting as a general server browser.

Recording players include Temporal Zoom presets (`1.0x`, `0.85x`, `0.7x`, `0.6x`, `0.5x`) that slow playback while preserving pitch. The feature is framed as a listening aid for humans, not as a simulation of another animal's hearing. On mobile browsers, Pibird uses a lighter native playback path and can prepare cached tempo-rendered clips in the background to avoid render-on-tap delays over Cloudflare Tunnel or other remote access paths.

---

## Installation

### Fresh Install

On a fresh Raspberry Pi with 64-bit RaspiOS:

```bash
curl -s https://raw.githubusercontent.com/cpieper/BirdNET-Pibird/main/newinstaller.sh | bash
```

You can also record an update preference during install:

```bash
RELEASE_CHANNEL=stable bash newinstaller.sh
```

Supported channels are `stable`, `prerelease`, and `edge`.
- `stable` is the default and installs the latest stable release tag.
- `prerelease` installs the latest prerelease or release tag, but requires explicit opt-in.
- `edge` follows the selected `BRANCH`, and also requires explicit opt-in.

This installs everything: BirdNET analysis pipeline, the new web interface, and all services.

<details>
<summary><b>Installing from a specific branch (for testing)</b></summary>

To install from a feature or development branch:

```bash
# Replace BRANCH_NAME with the actual branch name
curl -s https://raw.githubusercontent.com/cpieper/BirdNET-Pibird/main/newinstaller.sh | RELEASE_CHANNEL=edge BRANCH=BRANCH_NAME bash
```

Example for the `fastapi-svelte-migration-mk1` branch:

```bash
curl -s https://raw.githubusercontent.com/cpieper/BirdNET-Pibird/main/newinstaller.sh | RELEASE_CHANNEL=edge BRANCH=fastapi-svelte-migration-mk1 bash
```

You can also override the repository URL and install directory:

```bash
REPO_URL=https://github.com/yourfork/BirdNET-Pibird.git RELEASE_CHANNEL=edge BRANCH=your-branch bash newinstaller.sh
```

</details>

### Updating An Existing Install

If you already have BirdNET-Pibird checked out on a system and want to refresh the installed services and web app:

```bash
cd ~/BirdNET-Pi
git pull
./scripts/install_web.sh
```

The installer script will:
- Install Node.js and build the new frontend
- Install FastAPI backend dependencies
- Reconfigure Caddy for the new architecture
- Start the new web service

Your detection data, configuration, and recordings are preserved.

### Requirements

- **Hardware:** Raspberry Pi 5/4B/400/3B+/Zero 2W
- **OS:** 64-bit Raspberry Pi OS (Bookworm recommended)
- **Microphone:** USB microphone or RTSP stream

For local development on macOS, use Python `3.11` for the backend environment. TensorFlow does not currently provide a compatible install path for the newer Homebrew `python3.14` toolchain, so backend setup and tests are expected to run from a `3.11` virtual environment.

---

## Development

### Backend (FastAPI)

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cd backend
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

### Running Tests

Backend tests currently need both the BirdNET runtime dependencies from the repository root and the FastAPI backend dependencies from `backend/`:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -r backend/requirements.txt
python -m pip uninstall -y pyarrow
pytest tests -q
```

On Apple Silicon macOS, uninstalling `pyarrow` in the local development venv avoids a TensorFlow import crash during test collection. This is only a local test-environment workaround and is not required on the target Pi install path.

### Frontend (SvelteKit)

```bash
cd frontend
npm install
npm run dev
```

The frontend dev server proxies API requests to `localhost:8080`.

### Version Metadata

- `versions.md` stores machine-readable release metadata used by the API:
  - `service_version` (SemVer)
  - `git_hash` (commit hash)
  - `git_branch`
  - `api_version`
  - `build_date_utc`
- `version.md` remains the human-readable changelog/history.

Update metadata before a release/build:

```bash
./scripts/update_version_metadata.sh --service-version 0.14.0
```

Use the guided release script to keep ordering correct (metadata -> commit -> tag -> push):

```bash
./scripts/release_flow.sh --tag v0.14.0-rc6
```

### Project Structure

```
BirdNET-Pibird/
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── main.py         # Application entry point
│   │   ├── config.py       # Configuration management
│   │   ├── dependencies.py # Auth, database connections
│   │   ├── routers/        # API endpoints
│   │   └── models/         # Pydantic schemas
│   └── requirements.txt
├── frontend/                # SvelteKit application
│   ├── src/
│   │   ├── routes/         # Page components
│   │   ├── lib/            # Shared code, components, stores
│   │   └── app.css         # Tailwind entry point
│   ├── tailwind.config.js
│   └── package.json
├── scripts/                 # Analysis & utility scripts (unchanged)
│   ├── birdnet_analysis.py # Main analysis pipeline
│   ├── utils/              # Python utilities (reused by backend)
│   └── *.sh                # Shell scripts
├── model/                   # BirdNET models & labels
├── versions.md              # Machine-readable release metadata
└── version.md               # Human-readable changelog
```

---

## Standing on the Shoulders of Giants

This project builds upon the incredible work of:

| Project | Credit |
|---------|--------|
| [BirdNET-Analyzer](https://github.com/kahst/BirdNET-Analyzer) | [@kahst](https://github.com/kahst) — the ML magic behind bird identification |
| [BirdNET-Pi](https://github.com/mcguirepr89/BirdNET-Pi) | [@mcguirepr89](https://github.com/mcguirepr89) — the original Pi implementation |
| [BirdNET-Pi (Nachtzuster)](https://github.com/Nachtzuster/BirdNET-Pi) | [@Nachtzuster](https://github.com/Nachtzuster) — the fork this builds upon |
| [TFLite Binaries](https://github.com/PINTO0309/TensorflowLite-bin) | [@PINTO0309](https://github.com/PINTO0309) — pre-built TensorFlow Lite |

<a href="https://creativecommons.org/licenses/by-nc-sa/4.0/"><img src="https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg" alt="License"></a>

---

## Learn More

- [Wiki](https://github.com/cpieper/BirdNET-Pibird/wiki) — Full documentation & troubleshooting
- [Web UI Guide](docs/web-ui.md) — Settings surfaces, reports, file management, live audio, and tunnel guidance
- [External Integrations Notes](docs/integrations.md) — Bird image provider behavior, local asset caching, and Wikimedia safeguards
- [Discussions](https://github.com/cpieper/BirdNET-Pibird/discussions) — Community Q&A
- [BirdWeather](https://app.birdweather.com) — Share your birds with the world

---

<p align="center">
  <i>Currently listening in Durham, NC...</i> 🎤🐦
</p>
