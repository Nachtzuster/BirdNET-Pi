#!/usr/bin/env bash
source /etc/birdnet/birdnet.conf

if [ -s "$HOME/BirdNET-Pi/apprise.txt" ] && [ ${APPRISE_HOURLY_HEALTHCHECK} == 1 ];then
  TITLE="$(hostname) : BirdNET-Analyzer service stopped"
  services=(chart_viewer.service
    spectrogram_viewer.service
    icecast2.service
    birdnet_recording.service
    birdnet_analysis.service
    birdnet_log.service
    birdnet_stats.service)
  for i in  "${services[@]}"; do
    NOTIFICATION+="${i} : $(sudo systemctl is-active "${i}")"
  done
  if [ -z "$BIRDNETPI_URL" ]; then
    NOTIFICATION+="<br> <a href=$BIRDNETPI_URL>Access your BirdNET-Pi instance</a>"
  fi
	$HOME/BirdNET-Pi/birdnet/bin/apprise -vv -t "$TITLE" -b "${NOTIFICATION}" --input-format=html --config="$HOME/BirdNET-Pi/apprise.txt"
fi
