#!/usr/bin/env python3
"""
birdnet_timer.py – keep BirdNET-Pi analysis on a configurable timer window.

If TIMER_SWITCH is true the script merely flips BATS_ANALYSIS in birdnet.conf.
If false it physically stops/starts the core services.
"""

import os
import re
import sys
import time
import signal
import logging
import subprocess
from datetime import datetime, date

from suntime import Sun
from dateutil import tz
from utils.helpers import get_settings

# ─────────────────────────  constants  ──────────────────────────
CONFIG_FILE    = '/etc/birdnet/birdnet.conf'
RESTART_SCRIPT = os.path.expanduser('~/BirdNET-Pi/scripts/restart_services.sh')
STOP_SCRIPT    = os.path.expanduser('~/BirdNET-Pi/scripts/stop_core_services.sh')

POLL_INTERVAL  = 60           # seconds between main-loop iterations
BACKOFF_ERROR  = 300          # seconds to wait after a failed restart

# ──────────────────────  global / logging  ──────────────────────
shutdown = False
log = logging.getLogger('birdnet_timer')


def setup_logging() -> None:
    """Attach a stdout handler to the root logger."""
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    h = logging.StreamHandler(stream=sys.stdout)
    h.setFormatter(logging.Formatter('[%(name)s][%(levelname)s] %(message)s'))
    root.addHandler(h)


# ──────────────────────  signal handling  ───────────────────────
def sig_handler(sig_num, _frame):
    global shutdown
    log.info("Received signal %d – shutting down", sig_num)
    shutdown = True


# ─────────────────────────  helpers  ────────────────────────────
def update_bats_analysis(enabled: bool) -> None:
    """Toggle BATS_ANALYSIS in birdnet.conf."""
    pattern = re.compile(r'^BATS_ANALYSIS=')
    replaced = False
    out: list[str] = []
    with open(CONFIG_FILE, 'r', encoding='utf-8') as fh:
        for line in fh:
            if pattern.match(line):
                out.append(f'BATS_ANALYSIS={int(enabled)}\n')
                replaced = True
            else:
                out.append(line)
    if not replaced:
        out.append(f'BATS_ANALYSIS={int(enabled)}\n')   # add if missing
    with open(CONFIG_FILE, 'w', encoding='utf-8') as fh:
        fh.writelines(out)
    log.info("Set BATS_ANALYSIS=%d", int(enabled))


def restart_services() -> bool:
    """Return True on success, False on subprocess failure."""
    try:
        log.info("Starting BirdNET services: %s", RESTART_SCRIPT)
        subprocess.run(['sudo', 'bash', RESTART_SCRIPT], check=True)
        return True
    except subprocess.CalledProcessError as exc:
        log.error("Restart script failed (%s)", exc)
        return False


def stop_services() -> None:
    log.info("Stopping BirdNET core services: %s", STOP_SCRIPT)
    subprocess.run(['sudo', 'bash', STOP_SCRIPT], check=True)


def is_service_active() -> bool:
    """True ↔ birdnet_analysis systemd service is active."""
    return (
        subprocess.run(
            ['systemctl', 'is-active', '--quiet', 'birdnet_analysis']
        ).returncode
        == 0
    )


def get_sun_times(lat: float, lon: float) -> tuple[str, str]:
    """Return today's local sunrise/sunset as HH:MM strings."""
    today = date.today()
    sun = Sun(lat, lon)
    sr = sun.get_local_sunrise_time(today).strftime('%H:%M')
    ss = sun.get_local_sunset_time(today).strftime('%H:%M')
    return sr, ss


def parse_time_field(name: str, value: str, sunrise: str, sunset: str) -> str:
    """Convert TIMER_* value to 'HH:MM' (accepts Sunrise/Sunset, case-insensitive)."""
    val = value.strip()
    if val.lower() == 'sunrise':
        return sunrise
    if val.lower() == 'sunset':
        return sunset
    if re.fullmatch(r'\d{2}:\d{2}', val):
        return val
    raise ValueError(f"Invalid {name}: '{value}' (use HH:MM | Sunrise | Sunset)")


def hhmm_to_minutes(hhmm: str) -> int:
    h, m = map(int, hhmm.split(':'))
    return h * 60 + m


# ───────────────────────────  main  ─────────────────────────────
def main() -> None:
    setup_logging()
    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    # ---------- one-time configuration check ----------
    try:
        conf = get_settings()
        if conf.getint('TIMER', fallback=0) == 0:
            log.info("Timer disabled – idle until exit signal.")
            while not shutdown:
                time.sleep(POLL_INTERVAL)
            return

        timer_switch = conf.getboolean('TIMER_SWITCH', fallback=False)

        lat = conf.getfloat('LATITUDE')
        lon = conf.getfloat('LONGITUDE')
    except Exception:
        log.exception("Fatal error while reading configuration.")
        sys.exit(1)

    # ---------- day-specific values ----------
    today = date.min          # force first update
    start_min = stop_min = None

    while not shutdown:
        now = datetime.now(tz.tzlocal())
        # ── refresh sunrise/sunset + timer fields at day change ──
        if now.date() != today:
            conf = get_settings()                              # <- re-read file
            sunrise, sunset = get_sun_times(lat, lon)

            start_str = parse_time_field(
                'TIMER_START', conf.get('TIMER_START'), sunrise, sunset
            )
            stop_str = parse_time_field(
                'TIMER_STOP', conf.get('TIMER_STOP'), sunrise, sunset
            )
            start_min = hhmm_to_minutes(start_str)
            stop_min  = hhmm_to_minutes(stop_str)
            today = now.date()

            log.info("New day – active window %s → %s (switch=%s)",
                     start_str, stop_str,
                     'toggle BATS_ANALYSIS' if timer_switch else 'stop services')

        # ---------- are we inside the active window? ----------
        minute_now = now.hour * 60 + now.minute
        in_window = (
            start_min <= minute_now < stop_min
            if start_min < stop_min           # same-day window
            else minute_now >= start_min or minute_now < stop_min  # across-midnight
        )

        service_active = is_service_active()

        if in_window:
            if timer_switch:
                update_bats_analysis(True)
            elif not service_active:
                if not restart_services():        # back-off on failure
                    time.sleep(BACKOFF_ERROR)
        else:
            if timer_switch:
                update_bats_analysis(False)
            elif service_active:
                stop_services()

        time.sleep(POLL_INTERVAL)

    log.info("Timer exited cleanly.")


if __name__ == '__main__':
    main()
