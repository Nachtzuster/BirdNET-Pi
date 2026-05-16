#!/usr/bin/env bash
# BirdNET-Pi Installer
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
echo_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $1"; }
echo_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

# Determine paths
if [ -z "$HOME" ]; then
    HOME=$(getent passwd "$USER" | cut -d: -f6)
fi
BIRDNET_DIR="${BIRDNET_DIR:-$HOME/BirdNET-Pi}"
CONFIG_FILE="/etc/birdnet/birdnet.conf"
FRONTEND_BUILD_STAMP="$BIRDNET_DIR/frontend/build/.birdnet-build-hash"
FRONTEND_SOURCE_HASH=""
BUILD_PAUSED_SERVICES=()
BUILD_SERVICE_CANDIDATES=(
    birdnet-web
    birdnet_analysis
    birdnet_recording
    custom_recording
    chart_viewer
    spectrogram_viewer
    livestream
    icecast2
    caddy
)

# Detection functions
is_fresh_install() {
    # Fresh install if no config file exists
    [ ! -f "$CONFIG_FILE" ]
}

is_base_installed() {
    # Base is installed if Python venv exists and has required packages
    [ -d "$BIRDNET_DIR/birdnet" ] && [ -f "$BIRDNET_DIR/birdnet/bin/python3" ]
}

has_new_web_interface() {
    # New web interface is installed if FastAPI backend exists and service is enabled
    [ -f "$BIRDNET_DIR/backend/app/main.py" ] && systemctl is-enabled birdnet-web &>/dev/null
}

# Installation functions
install_nodejs() {
    echo_step "Installing Node.js..."
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
        if [ "$NODE_VERSION" -ge 18 ]; then
            echo_info "Node.js $(node -v) already installed"
            return 0
        fi
    fi
    
    curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
    sudo apt-get install -y nodejs
    echo_info "Node.js $(node -v) installed"
}

install_backend_deps() {
    echo_step "Installing Python backend dependencies..."
    if [ ! -f "$BIRDNET_DIR/backend/requirements.txt" ]; then
        echo_error "Backend requirements.txt not found"
        return 1
    fi
    
    "$BIRDNET_DIR/birdnet/bin/pip" install -q -r "$BIRDNET_DIR/backend/requirements.txt"
    echo_info "Backend dependencies installed"
}

hash_stdin() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum | awk '{print $1}'
    else
        shasum -a 256 | awk '{print $1}'
    fi
}

hash_file() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    else
        shasum -a 256 "$1" | awk '{print $1}'
    fi
}

frontend_source_hash() {
    if command -v git >/dev/null 2>&1 && git -C "$BIRDNET_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        git -C "$BIRDNET_DIR" ls-files -z \
            frontend/package.json \
            frontend/package-lock.json \
            frontend/svelte.config.js \
            frontend/vite.config.js \
            frontend/tsconfig.json \
            frontend/tailwind.config.js \
            frontend/postcss.config.js \
            frontend/src \
            frontend/static |
            while IFS= read -r -d '' file; do
                if [ -f "$BIRDNET_DIR/$file" ]; then
                    printf '%s  %s\n' "$(hash_file "$BIRDNET_DIR/$file")" "$file"
                fi
            done | hash_stdin
    else
        find "$BIRDNET_DIR/frontend" -type f \
            ! -path "$BIRDNET_DIR/frontend/node_modules/*" \
            ! -path "$BIRDNET_DIR/frontend/build/*" \
            ! -path "$BIRDNET_DIR/frontend/.svelte-kit/*" \
            -print0 |
            sort -z |
            while IFS= read -r -d '' file; do
                relative_path="${file#"$BIRDNET_DIR/"}"
                printf '%s  %s\n' "$(hash_file "$file")" "$relative_path"
            done | hash_stdin
    fi
}

frontend_build_looks_current() {
    [ -f "$BIRDNET_DIR/frontend/build/index.html" ] || return 1

    newer_source="$(find "$BIRDNET_DIR/frontend" -type f \
        ! -path "$BIRDNET_DIR/frontend/node_modules/*" \
        ! -path "$BIRDNET_DIR/frontend/build/*" \
        ! -path "$BIRDNET_DIR/frontend/.svelte-kit/*" \
        -newer "$BIRDNET_DIR/frontend/build/index.html" \
        -print \
        -quit)"
    [ -z "$newer_source" ]
}

frontend_build_needed() {
    if [ "${BIRDNET_FORCE_FRONTEND_BUILD:-0}" = "1" ]; then
        echo_info "BIRDNET_FORCE_FRONTEND_BUILD=1; frontend build will run"
        FRONTEND_SOURCE_HASH="$(frontend_source_hash)"
        return 0
    fi

    if [ ! -d "$BIRDNET_DIR/frontend/build" ]; then
        FRONTEND_SOURCE_HASH="$(frontend_source_hash)"
        return 0
    fi

    FRONTEND_SOURCE_HASH="$(frontend_source_hash)"
    if [ ! -f "$FRONTEND_BUILD_STAMP" ]; then
        if frontend_build_looks_current; then
            echo_info "Existing frontend build looks current; writing build stamp"
            printf '%s\n' "$FRONTEND_SOURCE_HASH" > "$FRONTEND_BUILD_STAMP"
            return 1
        fi
        return 0
    fi

    previous_hash="$(cat "$FRONTEND_BUILD_STAMP" 2>/dev/null || true)"
    [ "$FRONTEND_SOURCE_HASH" != "$previous_hash" ]
}

pause_services_for_build() {
    echo_step "Pausing services for frontend build..."
    BUILD_PAUSED_SERVICES=()

    for service in "${BUILD_SERVICE_CANDIDATES[@]}"; do
        if sudo systemctl list-unit-files "${service}.service" 2>/dev/null | grep -q "^${service}\.service" &&
           sudo systemctl is-active --quiet "$service"; then
            sudo systemctl stop "$service" || true
            BUILD_PAUSED_SERVICES+=("$service")
        fi
    done

    if [ ${#BUILD_PAUSED_SERVICES[@]} -gt 0 ]; then
        echo_info "Paused services: ${BUILD_PAUSED_SERVICES[*]}"
    else
        echo_info "No active services needed pausing"
    fi
}

resume_services_after_build() {
    if [ ${#BUILD_PAUSED_SERVICES[@]} -eq 0 ]; then
        return 0
    fi

    echo_step "Restoring services paused for frontend build..."
    for service in "${BUILD_PAUSED_SERVICES[@]}"; do
        sudo systemctl start "$service" || echo_warn "Could not restart ${service}; check with: sudo systemctl status ${service}"
    done
    BUILD_PAUSED_SERVICES=()
}

build_frontend() {
    echo_step "Checking frontend build..."
    if ! frontend_build_needed; then
        echo_info "Frontend sources unchanged; skipping npm install and build"
        return 0
    fi

    echo_step "Building frontend..."
    pause_services_for_build
    trap resume_services_after_build RETURN

    cd "$BIRDNET_DIR/frontend"
    
    # Install npm dependencies
    # Use 'npm install' instead of 'npm ci' in case package-lock.json is missing
    if [ -f "package-lock.json" ]; then
        npm ci --silent
    else
        echo_info "No package-lock.json found, running npm install..."
        npm install
    fi
    
    # Build for production
    npm run build

    mkdir -p "$BIRDNET_DIR/frontend/build"
    printf '%s\n' "$FRONTEND_SOURCE_HASH" > "$FRONTEND_BUILD_STAMP"
    
    trap - RETURN
    resume_services_after_build
    echo_info "Frontend built successfully"
}

install_systemd_service() {
    echo_step "Installing systemd service..."
    
    # Create service file with correct user
    cat << EOF | sudo tee /etc/systemd/system/birdnet-web.service > /dev/null
[Unit]
Description=BirdNET-Pi Web Interface
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=${USER}
Group=${USER}
WorkingDirectory=${BIRDNET_DIR}/backend
Environment="PATH=${BIRDNET_DIR}/birdnet/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=${BIRDNET_DIR}/birdnet/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 2
Restart=always
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=birdnet-web

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable birdnet-web
    echo_info "Systemd service installed"
}

update_caddy_config() {
    echo_step "Updating Caddy configuration..."
    
    # Backup existing config
    if [ -f /etc/caddy/Caddyfile ]; then
        sudo cp /etc/caddy/Caddyfile /etc/caddy/Caddyfile.backup.$(date +%Y%m%d%H%M%S)
    fi
    
    # Get password hash if set
    source "$CONFIG_FILE" 2>/dev/null || true
    
    if [ -n "${CADDY_PWD}" ]; then
        HASHWORD=$(caddy hash-password --plaintext "${CADDY_PWD}")
        AUTH_BLOCK="
  basicauth /api/config* {
    birdnet ${HASHWORD}
  }
  @protected_system {
    path /api/system*
    not path /api/system/public-status*
  }
  basicauth @protected_system {
    birdnet ${HASHWORD}
  }
  basicauth /settings* {
    birdnet ${HASHWORD}
  }"
    else
        AUTH_BLOCK=""
    fi
    
    # Create new Caddyfile
    cat << EOF | sudo tee /etc/caddy/Caddyfile > /dev/null
# BirdNET-Pi Caddy Configuration
# Generated by install_web.sh on $(date)

{
    admin off
}

http:// ${BIRDNETPI_URL:-} {
    @blocked_legacy_probe_paths {
        path_regexp legacyProbe (?i)(^|/)[^/]+\.(php[0-9]?|phtml|phar|phps|phtm?)(/|$)|^/(\.git|\.env)(/|\.|$)
    }
    respond @blocked_legacy_probe_paths 404

    reverse_proxy localhost:8080
    ${AUTH_BLOCK}

    encode gzip
    
    log {
        output file /var/log/caddy/birdnet.log {
            roll_size 10mb
            roll_keep 5
        }
    }
}
EOF

    # Create log directory
    sudo mkdir -p /var/log/caddy
    sudo chown caddy:caddy /var/log/caddy
    
    echo_info "Caddy configuration updated"
}

disable_legacy_sidecars() {
    echo_step "Disabling legacy sidecar services..."

    for service in birdnet_log birdnet_stats web_terminal; do
        if sudo systemctl list-unit-files | grep -q "^${service}\.service"; then
            sudo systemctl disable --now "${service}.service" || true
        fi
    done
}

resolve_port_conflicts() {
    echo_step "Checking for service port conflicts..."

    # Legacy installs may have birdnet_log bound to 8080, which conflicts with birdnet-web.
    if sudo systemctl is-enabled birdnet_log &>/dev/null || sudo systemctl is-active birdnet_log &>/dev/null; then
        if sudo systemctl cat birdnet_log 2>/dev/null | grep -q -- "-p 8080"; then
            echo_warn "Detected legacy birdnet_log on port 8080; migrating it to 8081."
            unit_path=$(sudo systemctl show -p FragmentPath --value birdnet_log 2>/dev/null || true)
            if [ -n "$unit_path" ] && [ -f "$unit_path" ]; then
                sudo sed -i 's/-p 8080/-p 8081/g' "$unit_path"
                sudo systemctl daemon-reload
                sudo systemctl enable birdnet_log || true
                sudo systemctl restart birdnet_log || true
            else
                echo_warn "Could not locate birdnet_log unit file; disabling service to prevent conflict."
                sudo systemctl stop birdnet_log || true
                sudo systemctl disable birdnet_log || true
            fi
        else
            # Ensure logs service is running if configured on a non-conflicting port.
            sudo systemctl restart birdnet_log || true
        fi
    else
        # If service exists but is disabled, leave as-is.
        if sudo systemctl list-unit-files | grep -q "^birdnet_log.service"; then
            :
        else
            # No legacy service found; nothing to resolve.
            :
        fi
    fi

    # Explicitly guard against any other listener on 8080 before starting birdnet-web.
    if command -v lsof >/dev/null 2>&1; then
        if sudo lsof -nP -iTCP:8080 -sTCP:LISTEN 2>/dev/null | grep -v "uvicorn" | grep -q .; then
            echo_warn "A process is already listening on port 8080; attempting to continue may fail."
            sudo lsof -nP -iTCP:8080 -sTCP:LISTEN 2>/dev/null || true
        fi
    fi
}

verify_directories() {
    echo_step "Verifying directory structure..."
    
    # Source config to get directory paths
    source "$CONFIG_FILE" 2>/dev/null || true
    
    # Set defaults if not defined
    RECS_DIR="${RECS_DIR:-$HOME/BirdSongs}"
    EXTRACTED="${EXTRACTED:-$HOME/BirdSongs/Extracted}"
    
    # Create required directories
    mkdir -p "${EXTRACTED}/By_Date" 2>/dev/null || true
    mkdir -p "${EXTRACTED}/Charts" 2>/dev/null || true
    
    # Verify database exists; fail safe if missing to avoid silent empty migrations
    if [ ! -f "$BIRDNET_DIR/scripts/birds.db" ]; then
        echo_error "Database not found at $BIRDNET_DIR/scripts/birds.db"
        echo_error "Aborting to avoid an accidental empty migration."
        echo_error "Restore birds.db from backup, or run createdb.sh intentionally if this is a fresh system."
        return 1
    fi
    
    echo_info "Directory structure verified"
}

check_password_config() {
    echo_step "Checking authentication configuration..."
    
    source "$CONFIG_FILE" 2>/dev/null || true
    
    if [ -z "${CADDY_PWD}" ]; then
        echo ""
        echo_warn "No password is configured for the web interface settings."
        echo_warn "The Settings page requires authentication to prevent unauthorized changes."
        echo ""
        read -p "Would you like to set a password now? [Y/n] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            read -s -p "Enter password for 'birdnet' user: " NEW_PWD
            echo
            if [ -n "$NEW_PWD" ]; then
                # Update config file
                if grep -q "^CADDY_PWD=" "$CONFIG_FILE"; then
                    sudo sed -i "s/^CADDY_PWD=.*/CADDY_PWD=\"$NEW_PWD\"/" "$CONFIG_FILE"
                else
                    echo "CADDY_PWD=\"$NEW_PWD\"" | sudo tee -a "$CONFIG_FILE" > /dev/null
                fi
                echo_info "Password configured successfully"
            else
                echo_warn "Empty password entered, skipping"
            fi
        else
            echo_warn "Skipping password setup. You can set CADDY_PWD in $CONFIG_FILE later."
        fi
    else
        echo_info "Password already configured"
    fi
}

start_services() {
    echo_step "Starting services..."
    
    # Reload and restart Caddy
    sudo systemctl reload caddy || sudo systemctl restart caddy
    
    # Start the new web service
    sudo systemctl start birdnet-web
    
    # Verify it's running
    sleep 2
    if sudo systemctl is-active --quiet birdnet-web; then
        echo_info "Web service started successfully"
    else
        echo_error "Web service failed to start"
        echo_error "Check logs with: sudo journalctl -u birdnet-web -n 50"
        return 1
    fi
}

run_base_install() {
    echo_step "Running base BirdNET-Pi installation..."
    
    # Run the existing installation scripts
    cd "$BIRDNET_DIR/scripts"
    
    # Install config if needed
    if [ ! -f "$CONFIG_FILE" ]; then
        ./install_config.sh
    fi
    
    # Source config
    source "$CONFIG_FILE"
    
    sudo -E HOME=$HOME USER=$USER ./install_services.sh
    
    # Install Python environment
    cd "$BIRDNET_DIR"
    if [ ! -d "birdnet" ]; then
        echo_info "Creating Python virtual environment..."
        python3 -m venv birdnet
        source ./birdnet/bin/activate
        pip3 install wheel
        pip3 install -r ./requirements.txt
    fi
    
    # Install language labels
    cd "$BIRDNET_DIR/scripts"
    ./install_language_label.sh || true
    
    echo_info "Base installation complete"
}

# Main installation logic
main() {
    echo ""
    echo "=============================================="
    echo "   BirdNET-Pi Installer"
    echo "=============================================="
    echo ""
    
    # Detect installation state
    if is_fresh_install; then
        echo_info "Detected: Fresh installation"
        INSTALL_MODE="fresh"
    elif has_new_web_interface; then
        echo_info "Detected: New web interface already installed"
        echo_warn "Re-running will update web services; frontend build is skipped when sources are unchanged"
        INSTALL_MODE="update"
    elif is_base_installed; then
        echo_info "Detected: Base installation present, finishing web setup"
        INSTALL_MODE="add"
    else
        echo_error "BirdNET-Pi base system not found"
        echo_error "Please verify BIRDNET_DIR or clone the repository again"
        exit 1
    fi
    
    echo ""
    echo "Installation mode: ${INSTALL_MODE}"
    echo ""
    
    # Confirm with user
    read -p "Continue with installation? [Y/n] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        echo "Installation cancelled"
        exit 0
    fi
    
    # Run appropriate installation steps
    case "$INSTALL_MODE" in
        fresh)
            run_base_install
            verify_directories
            check_password_config
            install_nodejs
            install_backend_deps
            build_frontend
            install_systemd_service
            disable_legacy_sidecars
            resolve_port_conflicts
            update_caddy_config
            start_services
            ;;
        add|update)
            verify_directories
            check_password_config
            install_nodejs
            install_backend_deps
            build_frontend
            install_systemd_service
            disable_legacy_sidecars
            resolve_port_conflicts
            update_caddy_config
            start_services
            ;;
    esac
    
    # Success message
    echo ""
    echo "=============================================="
    echo_info "Installation complete!"
    echo ""
    
    # Get IP address
    IP_ADDR=$(hostname -I | awk '{print $1}')
    echo "Access your BirdNET-Pi at:"
    echo "  http://${IP_ADDR}"
    echo "  http://$(hostname).local"
    echo ""
    
    # Check if password was configured
    source "$CONFIG_FILE" 2>/dev/null || true
    if [ -z "${CADDY_PWD}" ]; then
        echo ""
        echo_warn "Note: No password configured. Settings page will be inaccessible."
        echo_warn "To enable settings, set CADDY_PWD in $CONFIG_FILE and restart birdnet-web"
    else
        echo ""
        echo "Settings page login: username 'birdnet'"
    fi
    
    echo "=============================================="
}

# Run main
main "$@"
