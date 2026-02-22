# BirdNET-Pibird

[![Listen Live](https://img.shields.io/badge/🎧_Listen_Live-durm.pibirds.org-4CAF50?style=for-the-badge)](https://durm.pibirds.org)
[![Powered by](https://img.shields.io/badge/Powered_by-Raspberry_Pi_3B+-C51A4A?style=for-the-badge&logo=raspberrypi)](https://www.raspberrypi.com/)
[![Location](https://img.shields.io/badge/📍-Durham,_NC-blue?style=for-the-badge)](https://durm.pibirds.org)

> *A tiny computer in my backyard is eavesdropping on birds. 24/7. They have no idea.*

Real-time acoustic bird classification running on a Raspberry Pi 3B+, listening to the birds of Durham, North Carolina.

<p align="center">
  <img src="homepage/images/bird.png" alt="Pibird Logo" width="300"/>
</p>

---

## What's This?

This is a modernized fork of [BirdNET-Pi](https://github.com/Nachtzuster/BirdNET-Pi), completely rebuilt with a **modern web stack** for better performance, maintainability, and user experience. The original PHP interface has been replaced with **FastAPI + SvelteKit + Tailwind CSS**.

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
| **Modern Web Stack** | FastAPI backend + SvelteKit frontend replaces PHP |
| **Tailwind CSS** | Single consolidated stylesheet with dark mode support |
| **Mobile-First UI** | Responsive design that works great on phones |
| **Type Safety** | TypeScript frontend + Pydantic backend schemas |
| **Full Species Charts** | Daily charts show *all* species, not just the top 10 |
| **Faster Analysis** | Consolidated analysis pipeline + TFLite 2.17.1 |
| **Backup & Restore** | Never lose your bird data again |
| **Modern Debian** | Bookworm + Trixie support |

<details>
<summary><b>Changes from upstream BirdNET-Pi</b></summary>

**New in this fork:**
- Complete web interface rewrite (PHP → FastAPI + SvelteKit)
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

## Installation

### Fresh Install

On a fresh Raspberry Pi with 64-bit RaspiOS:

```bash
curl -s https://raw.githubusercontent.com/cpieper/BirdNET-Pibird/main/newinstaller.sh | bash
```

This installs everything: BirdNET analysis pipeline, the new web interface, and all services.

<details>
<summary><b>Installing from a specific branch (for testing)</b></summary>

To install from a feature or development branch:

```bash
# Replace BRANCH_NAME with the actual branch name
curl -s https://raw.githubusercontent.com/cpieper/BirdNET-Pibird/BRANCH_NAME/newinstaller.sh | BRANCH=BRANCH_NAME bash
```

Example for the `fastapi-svelte-migration-mk1` branch:

```bash
curl -s https://raw.githubusercontent.com/cpieper/BirdNET-Pibird/fastapi-svelte-migration-mk1/newinstaller.sh | BRANCH=fastapi-svelte-migration-mk1 bash
```

You can also override the repository URL and install directory:

```bash
REPO_URL=https://github.com/yourfork/BirdNET-Pibird.git BRANCH=your-branch bash newinstaller.sh
```

</details>

### Migration from PHP-based BirdNET-Pi

If you have an existing BirdNET-Pi installation with the PHP interface:

```bash
cd ~/BirdNET-Pi
git pull
./scripts/install_web.sh
```

The migration script will:
- Install Node.js and build the new frontend
- Install FastAPI backend dependencies
- Disable PHP-FPM services
- Reconfigure Caddy for the new architecture
- Start the new web service

Your detection data, configuration, and recordings are preserved.

### Requirements

- **Hardware:** Raspberry Pi 5/4B/400/3B+/Zero 2W
- **OS:** 64-bit Raspberry Pi OS (Bookworm recommended)
- **Microphone:** USB microphone or RTSP stream

---

## Development

### Backend (FastAPI)

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

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
- [Discussions](https://github.com/cpieper/BirdNET-Pibird/discussions) — Community Q&A
- [BirdWeather](https://app.birdweather.com) — Share your birds with the world

---

<p align="center">
  <i>Currently listening in Durham, NC...</i> 🎤🐦
</p>
