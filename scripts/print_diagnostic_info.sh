#!/bin/bash

# 1. Service status
services=("caddy" "birdnet_analysis" "birdnet_log" "birdnet_recording" "birdnet_stats" "chart_viewer" "extraction" "web_terminal" "spectrogram_viewer" "livestream")

for service in "${services[@]}"; do
    echo "========== $service status =========="
    sudo service $service status | cat
    echo ""
done

echo "========= Syslog snippet =========="
tail -n 100 /var/log/syslog

# 2. Mounted file systems
echo "========== Mounted File Systems =========="
df -h
echo ""

# 3. Memory usage
echo "========== Memory Usage =========="
free -h
echo ""

# 4. Load averages
echo "========== Load Averages =========="
uptime
echo ""

# 5. CPU usage
echo "========== CPU Info =========="
cat /proc/cpuinfo 

echo ""

# 6. System temperature
echo "========== System Temperature =========="
temp_c=$(cat /sys/class/thermal/thermal_zone0/temp | awk '{printf "%.2f", $1/1000}')
temp_f=$(echo "scale=2; 9/5*$temp_c+32" | bc)
echo "CPU Temperature: ${temp_c}°C / ${temp_f}°F"
echo ""

# 7. Output of /usr/local/bin/extra_info.sh
echo "========== Extra Info =========="
sudo /usr/local/bin/extra_info.sh
echo ""

# 8. Microphone devices
echo "========== Connected Microphone Devices =========="
arecord -l
echo ""
arecord -L
echo ""

echo "========= Date and Time =========="
date

echo "==========================================="