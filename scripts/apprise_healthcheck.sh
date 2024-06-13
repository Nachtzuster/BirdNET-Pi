#!/usr/bin/env bash
source /etc/birdnet/birdnet.conf

# Check if the analysis and recording services are running, or alert the user if apprise is configured

if [ -s "$HOME/BirdNET-Pi/apprise.txt" ] && [ ${APPRISE_HOURLY_HEALTHCHECK} == 1 ]; then
    if [[ "$(sudo systemctl is-active birdnet_analysis.service)" == "active" ]] && [[ "$(sudo systemctl is-active birdnet_recording.service)" == "active" ]]; then
        export LASTCHECK="$(date +%c)"
    else
        NOTIFICATION="<br><b>Since:</b> ${LASTCHECK:-unknown}"
        NOTIFICATION="<br><b>System:</b> ${SITE_NAME:-$(hostname)}"
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
        if [ -n "$BIRDNETPI_URL" ]; then
            NOTIFICATION+="<br> <a href=\"$BIRDNETPI_URL\">Access your BirdNET-Pi instance</a>"
        fi
        TITLE="BirdNET-Analyzer stopped"
        $HOME/BirdNET-Pi/birdnet/bin/apprise -vv -t "$TITLE" -b "${NOTIFICATION}" --input-format=html --config="$HOME/BirdNET-Pi/apprise.txt"
    fi
fi
