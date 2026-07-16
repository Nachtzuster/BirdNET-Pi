#!/usr/bin/env bash
# Restarts ALL services and removes ALL unprocessed audio

source /etc/birdnet/birdnet.conf

services=(birdnet_recording.service
custom_recording.service
birdnet_analysis.service
chart_viewer.service
spectrogram_viewer.service)

for i in  "${services[@]}";do
  sudo systemctl stop  ${i}
done

if [ -z "${RECS_DIR}" ] || [ ! -d "${RECS_DIR}" ]; then
  echo "RECS_DIR is unset or not a directory ('${RECS_DIR}') - refusing to purge" >&2
  exit 1
fi
sudo rm -rf "${RECS_DIR}/$(date +%B-%Y/%d-%A)"/*
