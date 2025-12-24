#!/usr/bin/env bash
# Configure WiFi roaming on Raspberry Pi for BirdNET-Pi
# This script configures wpa_supplicant to automatically connect to the strongest WiFi signal
set -e

echo "Configuring WiFi roaming for BirdNET-Pi..."

# Backup existing wpa_supplicant configuration
if [ -f /etc/wpa_supplicant/wpa_supplicant.conf ]; then
    sudo cp /etc/wpa_supplicant/wpa_supplicant.conf /etc/wpa_supplicant/wpa_supplicant.conf.backup.$(date +%Y%m%d_%H%M%S)
    echo "Backed up existing wpa_supplicant configuration"
fi

# Function to add roaming settings to wpa_supplicant.conf
configure_roaming() {
    local conf_file="/etc/wpa_supplicant/wpa_supplicant.conf"
    
    # Check if file exists
    if [ ! -f "$conf_file" ]; then
        echo "Error: $conf_file not found. WiFi may not be configured on this system."
        echo "Please configure WiFi first using raspi-config or manually."
        return 1
    fi
    
    # Check if roaming is already configured
    if grep -q "ap_scan=1" "$conf_file" && grep -q "fast_reauth=1" "$conf_file"; then
        echo "WiFi roaming appears to be already configured."
        return 0
    fi
    
    # Add global roaming settings if not present
    if ! grep -q "ap_scan=1" "$conf_file"; then
        sudo sed -i '/^country=/a ap_scan=1' "$conf_file"
        echo "Added ap_scan=1 setting"
    fi
    
    if ! grep -q "fast_reauth=1" "$conf_file"; then
        sudo sed -i '/^ap_scan=1/a fast_reauth=1' "$conf_file"
        echo "Added fast_reauth=1 setting"
    fi
    
    # Add bgscan to all network blocks that don't have it
    # This enables background scanning and automatic roaming
    sudo sed -i '/^network={/,/^}/{
        /key_mgmt=/a\    bgscan="simple:30:-45:300"
    }' "$conf_file" 2>/dev/null || true
    
    # Remove duplicate bgscan entries if any were created
    sudo awk '!seen[$0]++ || !/bgscan/' "$conf_file" > /tmp/wpa_supplicant_temp.conf
    sudo mv /tmp/wpa_supplicant_temp.conf "$conf_file"
    
    echo "WiFi roaming configuration added successfully"
    echo ""
    echo "Configuration details:"
    echo "  - ap_scan=1: Enables scanning for best access point"
    echo "  - fast_reauth=1: Speeds up re-authentication when roaming"
    echo "  - bgscan=\"simple:30:-45:300\": Background scan every 30s, switch if signal < -45dBm"
    echo ""
    return 0
}

# Display current configuration
show_current_config() {
    echo "Current wpa_supplicant configuration:"
    echo "======================================"
    sudo grep -E "^(country|ap_scan|fast_reauth)|bgscan=" /etc/wpa_supplicant/wpa_supplicant.conf || echo "No roaming settings found"
    echo ""
}

# Main execution
case "${1:-configure}" in
    configure)
        show_current_config
        configure_roaming
        echo ""
        echo "Restarting wpa_supplicant service..."
        sudo systemctl restart wpa_supplicant.service || sudo systemctl restart dhcpcd.service || true
        echo ""
        echo "WiFi roaming is now configured!"
        echo "The Raspberry Pi will automatically connect to the strongest available WiFi signal."
        echo ""
        echo "Notes:"
        echo "  - All access points should have the same SSID and password"
        echo "  - The Pi will scan every 30 seconds and roam if signal drops below -45dBm"
        echo "  - You can adjust these values by editing /etc/wpa_supplicant/wpa_supplicant.conf"
        echo "  - To restore original configuration, use the backup file in /etc/wpa_supplicant/"
        ;;
    status)
        show_current_config
        echo "WiFi Status:"
        echo "============"
        iwconfig 2>/dev/null | grep -A 10 "wlan0" || echo "No wireless interface found"
        ;;
    restore)
        if [ -z "$2" ]; then
            echo "Available backup files:"
            ls -lh /etc/wpa_supplicant/wpa_supplicant.conf.backup.* 2>/dev/null || echo "No backups found"
            echo ""
            echo "Usage: $0 restore <backup_file>"
        else
            sudo cp "$2" /etc/wpa_supplicant/wpa_supplicant.conf
            sudo systemctl restart wpa_supplicant.service || sudo systemctl restart dhcpcd.service || true
            echo "Configuration restored from $2"
        fi
        ;;
    help|--help|-h)
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  configure  - Configure WiFi roaming (default)"
        echo "  status     - Show current WiFi roaming configuration"
        echo "  restore    - Restore from backup"
        echo "  help       - Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0                    # Configure roaming"
        echo "  $0 status            # Check current config"
        echo "  $0 restore /path/to/backup  # Restore backup"
        ;;
    *)
        echo "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac
