#!/usr/bin/env bash
# Helper to enable/disable Tor hidden service for BirdNET-Pi
# Usage: update_tor_service.sh enable|disable
# Exit codes: 0=success, 1=error, 2=bad usage

ACTION="${1:-}"
TORRC_DIR="/etc/tor/torrc.d"
TORRC_FILE="$TORRC_DIR/birdnet.conf"
HS_DIR="/var/lib/tor/birdnet_hidden_service"
CONFIG_FILE="/etc/birdnet/birdnet.conf"
LOG_FILE="/tmp/tor_service_${ACTION}_$$.log"

# Redirect output to log file for debugging
exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

log_error() {
  echo "[ERROR] $*" >&2
}

log_info() {
  echo "[INFO] $*"
}

check_systemd() {
  if ! command -v systemctl >/dev/null 2>&1; then
    log_error "systemd not found. This system may not support 'systemctl restart tor'"
    return 1
  fi
  return 0
}

check_tor_user() {
  # On Raspberry Pi OS (Debian), the Tor user is debian-tor
  local tor_user="debian-tor"
  if id "$tor_user" &>/dev/null; then
    echo "$tor_user"
    return 0
  else
    log_error "Tor user 'debian-tor' not found. Tor may not be installed correctly."
    return 1
  fi
}

install_tor() {
  log_info "Checking/installing Tor..."
  
  if command -v tor >/dev/null 2>&1; then
    log_info "Tor is already installed"
    return 0
  fi
  
  log_info "Installing Tor via apt-get..."
  apt-get update -qq 2>&1 | grep -i "get\|update" || true
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq tor 2>&1 | tail -5 || {
    log_error "Failed to install Tor via apt-get"
    return 1
  }
  
  log_info "Tor installed successfully"
  return 0
}

enable_tor_service() {
  log_info "Enabling Tor hidden service..."
  cleanup_old_logs "enable"
  
  install_tor || return 1
  check_systemd || return 1
  
  # Wait for web services before enabling Tor
  check_web_services || {
    log_error "Cannot enable Tor - web services not available"
    return 1
  }

  # Ensure Tor service is running
  log_info "Starting Tor service..."
  if ! systemctl start tor@default 2>/dev/null; then
    log_error "Failed to start Tor service"
    return 1
  fi

  local tor_user
  tor_user=$(check_tor_user) || return 1
  
  # Ensure /var/lib/tor exists and has correct permissions
  log_info "Ensuring /var/lib/tor exists with correct permissions..."
  mkdir -p /var/lib/tor
  chown -R "$tor_user:$tor_user" /var/lib/tor 2>/dev/null || {
    log_error "Failed to set ownership of /var/lib/tor"
    return 1
  }
  chmod 0755 /var/lib/tor 2>/dev/null || {
    log_error "Failed to set permissions on /var/lib/tor"
    return 1
  }
  
  mkdir -p "$TORRC_DIR"
  mkdir -p "$HS_DIR"

  # Ensure tor reads /etc/tor/torrc.d/*.conf by including it in /etc/tor/torrc if missing
  # Detect Tor version to use correct include syntax
  local tor_version
  tor_version=$(/usr/bin/tor --version 2>&1 | sed -n 's/Tor version \([0-9.]*\).*/\1/p')
  local include_directive="%include"
  
  # Tor 0.4.8+ supports Include; older versions need %include
  if [ -n "$tor_version" ]; then
    if [[ "$tor_version" > "0.4.8" ]] || [[ "$tor_version" == "0.4.8" ]]; then
      include_directive="Include"
      log_info "Tor version $tor_version detected, using Include directive"
    else
      log_info "Tor version $tor_version detected, using %include directive"
    fi
  fi

  if ! grep -qF "$include_directive /etc/tor/torrc.d/*.conf" /etc/tor/torrc 2>/dev/null; then
    log_info "Adding $include_directive directive to /etc/tor/torrc"
    printf "\n# Include drop-in configs\n$include_directive /etc/tor/torrc.d/*.conf" >> /etc/tor/torrc
  fi
  
  log_info "Writing Tor configuration to $TORRC_FILE"
  cat <<EOF > "$TORRC_FILE"
HiddenServiceDir $HS_DIR
HiddenServiceVersion 3
HiddenServicePort 80 127.0.0.1:80
EOF
  
  log_info "Setting permissions on $HS_DIR (owner: $tor_user)"
  chown -R "$tor_user:$tor_user" "$HS_DIR" 2>/dev/null || {
    log_error "Failed to set ownership of $HS_DIR"
    return 1
  }
  chmod 0700 "$HS_DIR" 2>/dev/null || {
    log_error "Failed to set permissions on $HS_DIR"
    return 1
  }
  
  log_info "Restarting Tor daemon..."
  # Stop any running Tor instances
  pkill -SIGTERM tor 2>/dev/null || true
  sleep 1
  
  # # Enable and start the tor@default instance (actual Tor daemon)
  # log_info "Starting Tor daemon with tor@default service..."
  # systemctl daemon-reload 2>/dev/null || true
  # systemctl enable tor@default >/dev/null 2>&1 || true
  # systemctl restart tor@default 2>&1 | tail -3 || {
  #   log_info "Note: tor@default may not exist; trying standard tor service"
  #   systemctl restart tor 2>&1 | tail -3 || true
  # }
  
  # Give Tor time to initialize and create the hidden service
  log_info "Waiting for Tor daemon to initialize..."
  sleep 3

  # Single restart after configuration is complete
  log_info "Restarting Tor service to apply hidden service configuration..."
  if ! systemctl restart tor@default 2>/dev/null; then
    log_info "Note: tor@default may not exist; trying standard tor service"
    if ! systemctl restart tor 2>/dev/null; then
      log_error "Failed to restart Tor service"
      return 1
    fi
  fi
  
  # Wait for hostname generation
  log_info "Waiting for Tor hidden service hostname to be generated..."
  local HOSTNAME=""
  for i in {1..60}; do
    if [ -f "$HS_DIR/hostname" ]; then
      HOSTNAME=$(cat "$HS_DIR/hostname" | tr -d '\n')
      log_info "Success! Hostname file found on attempt $i"
      break
    fi
    if [ $((i % 5)) -eq 0 ]; then
      log_info "Attempt $i/60: waiting for hostname..."
    fi
    sleep 1
  done
  
  if [ -z "$HOSTNAME" ]; then
    log_error "Tor hidden service hostname not found after 60 seconds"
    log_error "Tor may not have started correctly. Checking status..."
    log_error "$(systemctl status tor@default 2>&1 || systemctl status tor 2>&1)"
    log_error "Directory contents: $(ls -la $HS_DIR 2>&1 || echo 'Directory not readable')"
    return 1
  fi
  
  log_info "Persisting Tor settings to $CONFIG_FILE"
  if grep -q "^TOR_ENABLED=" "$CONFIG_FILE" 2>/dev/null; then
    sed -i "s|^TOR_ENABLED=.*|TOR_ENABLED=1|" "$CONFIG_FILE"
  else
    echo "TOR_ENABLED=1" >> "$CONFIG_FILE"
  fi
  
  if grep -q "^TOR_ONION=" "$CONFIG_FILE" 2>/dev/null; then
    sed -i "s|^TOR_ONION=.*|TOR_ONION=\"http://$HOSTNAME\"|" "$CONFIG_FILE"
  else
    echo "TOR_ONION=\"http://$HOSTNAME\"" >> "$CONFIG_FILE"
  fi
  
  log_info "Tor hidden service enabled successfully"
  log_info "Onion address: http://$HOSTNAME"
  return 0
}

cleanup_old_logs() {
  # Keep only the last 3 log files for each action type
  local action="$1"
  local keep_count=3
  
  ls -t /tmp/tor_service_${action}_*.log 2>/dev/null | tail -n +$((keep_count + 1)) | xargs rm -f 2>/dev/null || true
}

disable_tor_service() {
  log_info "Disabling Tor hidden service..."
  
  check_systemd || return 1
  
  if [ -f "$TORRC_FILE" ]; then
    log_info "Removing Tor configuration $TORRC_FILE"
    rm -f "$TORRC_FILE"
  fi

  # Remove hidden service directory to ensure new keys on re-enable
  if [ -d "$HS_DIR" ]; then
    log_info "Removing hidden service directory for key regeneration"
    rm -rf "$HS_DIR"
  fi

  log_info "Stopping Tor service..."
  if systemctl stop tor@default 2>/dev/null; then
    log_info "Tor service stopped successfully"
  else
    log_error "Warning: Failed to stop Tor service"
  fi
  
  log_info "Removing Tor settings from $CONFIG_FILE"
  if [ -f "$CONFIG_FILE" ]; then
    sed -i "/^TOR_ENABLED=/d" "$CONFIG_FILE" 2>/dev/null || true
    sed -i "/^TOR_ONION=/d" "$CONFIG_FILE" 2>/dev/null || true
  fi
  
  log_info "Tor hidden service disabled successfully"
  return 0
}

if [ -z "$ACTION" ]; then
  cat <<EOF >&2
Usage: $0 enable|disable
  enable   - Install Tor and enable hidden service
  disable  - Disable hidden service
  
Log file: $LOG_FILE
EOF
  exit 2
fi

# To this:
case "$ACTION" in
  enable)
    enable_tor_service
    exit $?
    ;;
  disable)
    disable_tor_service
    exit $?
    ;;
  *)
    log_error "Unknown action: $ACTION"
    exit 2
    ;;
esac
