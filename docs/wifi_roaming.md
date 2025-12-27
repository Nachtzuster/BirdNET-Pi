# WiFi Roaming Configuration for BirdNET-Pi

## Overview

This feature enables your BirdNET-Pi Raspberry Pi to automatically connect to the strongest WiFi signal available. This is particularly useful when you have multiple WiFi access points (APs) with the same SSID covering your monitoring area.

## What is WiFi Roaming?

WiFi roaming allows your Raspberry Pi to automatically switch between different access points broadcasting the same network name (SSID) based on signal strength. This ensures your BirdNET-Pi maintains the best possible connection, which is critical for:

- **Stable SSH connections** - Remote access remains reliable
- **Web interface accessibility** - Consistent access to the BirdNET-Pi web UI
- **Data synchronization** - Reliable uploads to BirdWeather and other services
- **Live audio streaming** - Uninterrupted audio feed

## Prerequisites

Before enabling WiFi roaming, ensure:

1. **Multiple Access Points**: You have at least two WiFi access points
2. **Same SSID**: All access points broadcast the same network name (SSID)
3. **Same Security**: All access points use identical authentication (WPA2-PSK, password, etc.)
4. **WiFi Configured**: Your Raspberry Pi is already connected to WiFi

## How It Works

The roaming configuration uses `wpa_supplicant` with the following settings:

- **`ap_scan=1`**: Enables active scanning for the best available access point
- **`fast_reauth=1`**: Speeds up re-authentication when switching between APs
- **`bgscan="simple:30:-45:300"`**: Background scanning configuration
  - Scans every **30 seconds**
  - Switches to a better AP if current signal drops below **-45 dBm**
  - Maximum scan interval of **300 seconds** when signal is good

## Installation

### Option 1: Automated Configuration (Recommended)

Run the WiFi roaming configuration script:

```bash
sudo /usr/local/bin/configure_wifi_roaming.sh
```

This will:
1. Backup your current WiFi configuration
2. Add roaming parameters to `wpa_supplicant.conf`
3. Restart the WiFi service
4. Enable automatic roaming

### Option 2: Manual Configuration

1. Backup your current configuration:
```bash
sudo cp /etc/wpa_supplicant/wpa_supplicant.conf /etc/wpa_supplicant/wpa_supplicant.conf.backup
```

2. Edit the configuration file:
```bash
sudo nano /etc/wpa_supplicant/wpa_supplicant.conf
```

3. Add these lines after the `country=` line:
```
ap_scan=1
fast_reauth=1
```

4. For each `network` block, add the `bgscan` parameter:
```
network={
    ssid="YourNetworkName"
    psk="YourPassword"
    key_mgmt=WPA-PSK
    bgscan="simple:30:-45:300"
}
```

5. Restart the WiFi service:
```bash
sudo systemctl restart wpa_supplicant.service
```

## Checking Status

To verify your roaming configuration:

```bash
sudo /usr/local/bin/configure_wifi_roaming.sh status
```

This displays:
- Current roaming settings
- WiFi connection status
- Signal strength

## Customization

You can adjust the roaming behavior by modifying the `bgscan` parameter in `/etc/wpa_supplicant/wpa_supplicant.conf`:

```
bgscan="simple:SHORT_INTERVAL:SIGNAL_THRESHOLD:LONG_INTERVAL"
```

**Parameters:**
- **SHORT_INTERVAL**: Scan interval in seconds when signal is poor (default: 30)
- **SIGNAL_THRESHOLD**: Signal strength in dBm to trigger scanning (default: -45)
- **LONG_INTERVAL**: Maximum scan interval when signal is good (default: 300)

### Example Configurations

**Aggressive roaming** (faster switching, more power consumption):
```
bgscan="simple:15:-50:120"
```

**Conservative roaming** (less frequent switching, better battery life):
```
bgscan="simple:60:-40:600"
```

**Balanced** (default - good for most scenarios):
```
bgscan="simple:30:-45:300"
```

## Troubleshooting

### Roaming Not Working

1. **Verify multiple APs are available**:
```bash
sudo iwlist wlan0 scan | grep ESSID
```

2. **Check signal strength**:
```bash
watch -n 1 iwconfig wlan0
```

3. **View wpa_supplicant logs**:
```bash
sudo journalctl -u wpa_supplicant -f
```

### Connection Drops During Roaming

If you experience brief connection drops when roaming:

1. **Enable 802.11r (Fast Roaming)** on your access points if supported
2. **Increase the signal threshold** to trigger roaming earlier:
```
bgscan="simple:30:-50:300"
```

### SSH Disconnects

If SSH sessions disconnect during roaming:

1. Use `tmux` or `screen` for persistent sessions
2. Configure SSH keep-alive in your SSH client
3. Consider using Mosh instead of SSH for mobile connections

## Restoring Original Configuration

If you need to revert to the original WiFi configuration:

```bash
sudo /usr/local/bin/configure_wifi_roaming.sh restore
```

This will list available backups. Then restore a specific backup:

```bash
sudo /usr/local/bin/configure_wifi_roaming.sh restore /etc/wpa_supplicant/wpa_supplicant.conf.backup.YYYYMMDD_HHMMSS
```

## Performance Considerations

**Benefits:**
- ✅ Maintains optimal signal strength
- ✅ Reduces packet loss and latency
- ✅ Improves reliability of remote access
- ✅ Better streaming quality

**Trade-offs:**
- ⚠️ Slightly increased power consumption (minimal on Pi 4/5)
- ⚠️ Brief connection interruption during AP switch (typically < 1 second)
- ⚠️ May cause momentary audio stream dropout

## Network Requirements

For optimal roaming performance:

1. **Overlapping Coverage**: Access points should have overlapping coverage areas
2. **Channel Planning**: Configure APs on non-overlapping channels (1, 6, 11 for 2.4GHz)
3. **Same Band**: All APs should use the same frequency band (2.4GHz or 5GHz)
4. **Consistent Configuration**: Identical SSID, password, and security settings
5. **Adequate Signal**: At least -70 dBm where transition occurs

## Advanced: Using NetworkManager Instead

If you prefer NetworkManager over wpa_supplicant:

```bash
sudo apt install network-manager
sudo systemctl enable NetworkManager
sudo systemctl start NetworkManager
```

NetworkManager handles roaming automatically without additional configuration.

## Integration with BirdNET-Pi

WiFi roaming works seamlessly with all BirdNET-Pi features:

- **Web Interface**: Continuous access via http://birdnetpi.local
- **SSH Terminal**: Persistent remote terminal access
- **Live Audio Stream**: Uninterrupted audio monitoring
- **BirdWeather Uploads**: Reliable data synchronization
- **Notifications**: Consistent Apprise notification delivery

## FAQ

**Q: Will this work with different WiFi networks (different SSIDs)?**  
A: No, roaming is designed for multiple access points with the same SSID. For different networks, wpa_supplicant already prioritizes based on signal strength and priority settings.

**Q: Do I need enterprise WiFi (802.11r) for this to work?**  
A: No, basic roaming works with consumer-grade access points. 802.11r (Fast Roaming) provides even faster handoffs but is not required.

**Q: Will this affect my audio recordings?**  
A: No, recordings are stored locally. WiFi roaming only affects network connectivity, not audio capture.

**Q: Can I use this with a single access point?**  
A: Yes, the settings are harmless with a single AP, but provide no benefit. The background scanning adds minimal overhead.

**Q: Does this work with 5GHz WiFi?**  
A: Yes, roaming works with both 2.4GHz and 5GHz networks. Ensure your Raspberry Pi model supports 5GHz.

## Support

For issues or questions:
1. Check the [BirdNET-Pi discussions](https://github.com/mcguirepr89/BirdNET-Pi/discussions)
2. Review the [installation guide](https://github.com/mcguirepr89/BirdNET-Pi/wiki/Installation-Guide)
3. Open an issue on the GitHub repository

## References

- [wpa_supplicant Documentation](https://w1.fi/wpa_supplicant/)
- [Raspberry Pi WiFi Configuration](https://www.raspberrypi.org/documentation/configuration/wireless/)
- [Linux WiFi Roaming Best Practices](https://wireless.wiki.kernel.org/en/users/documentation/iw)
