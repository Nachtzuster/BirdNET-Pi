#!/usr/bin/env python3

import re
import time
import subprocess
import os
import logging
import sys
import signal
from datetime import datetime, date
from suntime import Sun
from dateutil import tz
from utils.helpers import get_settings

# Graceful shutdown flag
shutdown = False

# Configure logging
log = logging.getLogger(__name__)

def setup_logging():
    """Set up root logger to output to stdout with a simple format."""
    logger = logging.getLogger()
    formatter = logging.Formatter("[%(name)s][%(levelname)s] %(message)s")
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    global log
    log = logging.getLogger('birdnet_timer')

# Configuration paths
CONFIG_FILE    = '/etc/birdnet/birdnet.conf'
RESTART_SCRIPT = os.path.expanduser('~/BirdNET-Pi/scripts/restart_services.sh')
STOP_SCRIPT    = os.path.expanduser('~/BirdNET-Pi/scripts/stop_core_services.sh')

# Signal handler
def sig_handler(sig_num, frame):
    global shutdown
    log.info('Caught shutdown signal %d', sig_num)
    shutdown = True

# Helpers
def update_bats_analysis(new_value):
    """Write BATS_ANALYSIS=<new_value> into the config file."""
    with open(CONFIG_FILE, 'r') as f:
        lines = f.readlines()
    with open(CONFIG_FILE, 'w') as f:
        for line in lines:
            if line.startswith('BATS_ANALYSIS='):
                f.write(f'BATS_ANALYSIS={new_value}\n')
            else:
                f.write(line)

def restart_services():
    """Restart BirdNET services via the configured script with sudo."""
    log.info('Running restart script with sudo: %s', RESTART_SCRIPT)
    subprocess.run(["sudo", "bash", RESTART_SCRIPT], check=True)

def stop_services():
    """Stop BirdNET core services via the configured script with sudo."""
    log.info('Running stop script with sudo: %s', STOP_SCRIPT)
    subprocess.run(["sudo", "bash", STOP_SCRIPT], check=True)

def is_service_active():
    """Return True if the birdnet_analysis systemd service is active."""
    res = subprocess.run([
        'systemctl', 'is-active', 'birdnet_analysis'
    ], capture_output=True, text=True)
    active = res.stdout.strip() == 'active'
    log.debug('Service birdnet_analysis active: %s', active)
    return active

def get_sun_times():
    """Return today's sunrise and sunset times as 'HH:MM'."""
    conf = get_settings()
    raw_lat = conf.get('LATITUDE', fallback=None)
    raw_lon = conf.get('LONGITUDE', fallback=None)
    if raw_lat is None or raw_lon is None:
        error_and_sleep("Missing LATITUDE or LONGITUDE in configuration.")
    lat = conf.getfloat('LATITUDE')
    lon = conf.getfloat('LONGITUDE')
    sun = Sun(lat, lon)
    local_tz = tz.tzlocal()
    today_dt = datetime.combine(date.today(), datetime.min.time())
    sr = sun.get_sunrise_time(today_dt, local_tz).strftime("%H:%M")
    ss = sun.get_sunset_time(today_dt, local_tz).strftime("%H:%M")
    log.debug('Today sunrise=%s sunset=%s', sr, ss)
    return sr, ss

def error_and_sleep(msg):
    """Log an error message, then sleep forever or exit on shutdown."""
    log.error(msg)
    while not shutdown:
        time.sleep(3600)
    sys.exit(1)

def parse_time_field(field_name, value, sunrise, sunset):
    """Parse a TIMER_* value into an 'HH:MM' string or error."""
    if value == 'Sunrise':
        return sunrise
    if value == 'Sunset':
        return sunset
    if isinstance(value, str) and re.match(r'^\d{2}:\d{2}$', value):
        return value
    error_and_sleep(f"Invalid {field_name}: '{value}' (must be 'Sunrise', 'Sunset' or HH:MM)")

def time_to_minutes(timestr):
    """Convert 'HH:MM' to minutes since midnight."""
    h, m = map(int, timestr.split(':'))
    return h * 60 + m

if __name__ == '__main__':
    setup_logging()
    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    # Initialization with strict config checks
    try:
        conf = get_settings()
        raw_timer = conf.get('TIMER', fallback=None)
        if raw_timer is None:
            error_and_sleep("Missing TIMER in configuration.")
        timer_enabled = int(raw_timer)
        if timer_enabled == 0:
            log.info("Timer disabled: sleeping until restart...")
            while not shutdown:
                time.sleep(3600)
            sys.exit(0)
        raw_start = conf.get('TIMER_START', fallback=None)
        raw_stop  = conf.get('TIMER_STOP',  fallback=None)
        if raw_start is None or raw_stop is None:
            error_and_sleep("Missing TIMER_START or TIMER_STOP in configuration.")
        sunrise, sunset = get_sun_times()
        start_str = parse_time_field('TIMER_START', raw_start, sunrise, sunset)
        stop_str  = parse_time_field('TIMER_STOP',  raw_stop,  sunrise, sunset)
        if start_str == stop_str:
            error_and_sleep("TIMER_START and TIMER_STOP cannot be the same.")
        raw_switch = conf.get('TIMER_SWITCH', fallback=None)
        if raw_switch is None:
            error_and_sleep("Missing TIMER_SWITCH in configuration.")
        timer_switch = raw_switch.lower() in ('1','true','yes','on')
        start_min = time_to_minutes(start_str)
        stop_min  = time_to_minutes(stop_str)
        log.info("Timer configured: start=%s, stop=%s, switch=%s", start_str, stop_str,
                 'ON' if timer_switch else 'OFF')
    except Exception:
        log.exception("Initialization error")
        sys.exit(1)

    # Main loop
    today = date.today()
    while not shutdown:
        try:
            now = datetime.now()
            now_min = now.hour * 60 + now.minute
            if now.date() != today:
                sunrise, sunset = get_sun_times()
                today = now.date()
                raw_start = conf.get('TIMER_START')
                raw_stop  = conf.get('TIMER_STOP')
                start_str = parse_time_field('TIMER_START', raw_start, sunrise, sunset)
                stop_str  = parse_time_field('TIMER_STOP',  raw_stop,  sunrise, sunset)
                start_min = time_to_minutes(start_str)
                stop_min  = time_to_minutes(stop_str)
                log.info("[New day] start=%s, stop=%s", start_str, stop_str)
            if start_min < stop_min:
                in_window = start_min <= now_min < stop_min
            else:
                in_window = now_min >= start_min or now_min < stop_min
            service_active = is_service_active()
            if in_window:
                if not service_active:
                    log.info("Window start: service inactive -> restarting")
                    restart_services()
            else:
                if service_active:
                    if not timer_switch:
                        log.info("Window end: service active & switch OFF -> stopping core services")
                        stop_services()
                    else:
                        log.info("Window end: switch ON, leaving services running")
        except BaseException:
            log.exception("Unexpected error in main loop")
        time.sleep(60)
