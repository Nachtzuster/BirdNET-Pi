# 0.13
- Removed secondary and tertiary custom URLs
- Added new custom-compiled GoTTY binary
- All new web interface
- SQLite database replaced MariaDB
- Better service controls
- Spectrogram views
- Privacy server.py for testing
- New mobile view
- Moved (nearly) all CSS to style.css
- Added "try/except" to server.py to fail BirdWeather
  POSTing gracefully and not kill the service

# main v.11.1
- `server.py` socket
- Removed DB password from scripts
- FTP included
- WebGUI tools:
  - Settings > Advanced Settings
  - Include/Exclude Species List Editor
  - Web Terminal
- Removed Extraction Logging
- Lowered minimum recording length
- No longer requires CADDY_PWD
- Auto-set random DB_PWD
- New (but still changing) charts
- Crontabs now in `/etc/crontab` instead of `pi` user

# main v.11
- New "Reconfigure System" GUI
- labels.txt language support for 20+ languages
  - Tool in `birdnet-pi-config` for now
  - Added German top.html and menu.html

# main v.10 & pre-installed image notes
- New "BirdWeather" Chromium App (Pre-install image)
- New Infographics _chart_viewer.service_ (courtesy of @CaiusX)
- New "Overview"
- BirdWeather Support
- Bug Fix for systemd-networkd-wait-online.service
- Bug Fix for `install_noip2.sh` for NoIP DUC Support
- New `disk_check.sh` utility/crontab entry to `stop_core_services.sh`
  when disk space is greater than 95%

# main v0.9 -- pre-installed image
- Bug fix for Auto Access Point
- Improved Welcome Wizard
- Support for GPIO shutdown, reboot, and power on
- Ships with Caddy 2.4.5 to avoid 2.4.6 bug
- IceCast2 bug fix (for pre-installed image)

# main v0.8
- Supports Bullseye
- Pre-installed image has AutoHotSpot enabled
- Updated php from 7.3 to 7.4
- Updated MariaDB
- Added Configuration GUI

# newinstaller v0.7
- Systemd networkd supported

# newinstaller v0.5
- New `birdnet-pi-config` tool meant for:
  - SSH-only installation
  - Reconfiguring birdnet.conf
  - Configuring system settings
