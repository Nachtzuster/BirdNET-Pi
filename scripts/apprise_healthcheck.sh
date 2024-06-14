#!/usr/bin/env bash
source /etc/birdnet/birdnet.conf

# Check if the analysis and recording services are running, or alert the user if apprise is configured

if [ -s "$HOME/BirdNET-Pi/apprise.txt" ]; then
    if [[ "$(sudo systemctl is-active birdnet_analysis.service)" == "active" ]] && [[ "$(sudo systemctl is-active birdnet_recording.service)" == "active" ]]; then
        # Remove failed check
        if [ -f "$HOME"/BirdNET-Pi/failed_servicescheck ]; then rm "$HOME"/BirdNET-Pi/failed_servicescheck; fi
        export LASTCHECK="$(date +%c)"
    elif [ ! -f "$HOME"/BirdNET-Pi/failed_servicescheck ]; then
        # Set failed check so it only runs once
        touch "$HOME"/BirdNET-Pi/failed_servicescheck
        NOTIFICATION=""
        STOPPEDSERVICE="<br><b>Stopped services:</b> "
        services=(birdnet_analysis
            chart_viewer
            spectrogram_viewer
            icecast2
            birdnet_recording
            birdnet_log
            birdnet_stats)
        for i in "${services[@]}"; do
            if [[ "$(sudo systemctl is-active "${i}".service)" == "inactive" ]]; then
                STOPPEDSERVICE+="${i}; "
            fi
        done
        NOTIFICATION+="$STOPPEDSERVICE"
        NOTIFICATION+="<br><b>Additional informations</b>: "
        NOTIFICATION+="<br><b>Since:</b> ${LASTCHECK:-unknown}"
        NOTIFICATION+="<br><b>System:</b> ${SITE_NAME:-$(hostname)}"
        NOTIFICATION+="<br>Available disk space: $(df -h "$(readlink -f "$HOME/BirdSongs")" | awk 'NR==2 {print $4}')"
        if [ -n "$BIRDNETPI_URL" ]; then
            NOTIFICATION+="<br> <a href=\"$BIRDNETPI_URL\">Access your BirdNET-Pi</a>"
        fi
        TITLE="BirdNET-Analyzer stopped"
        $HOME/BirdNET-Pi/birdnet/bin/apprise -vv -t "$TITLE" -b "${NOTIFICATION}" --input-format=html --config="$HOME/BirdNET-Pi/apprise.txt"
    fi
fi
