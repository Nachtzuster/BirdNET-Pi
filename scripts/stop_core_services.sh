#!/usr/bin/env bash
# Restarts ALL services and removes ALL unprocessed audio

# This script never sourced the config, and install_config.sh sets RECS_DIR
# WITHOUT export - so ${RECS_DIR} was empty here even when a parent had sourced
# birdnet.conf. The rm below therefore expanded to an absolute path like
# `sudo rm -rf /July-2026/16-Thursday/*`: the documented cleanup silently never
# happened, and it sat one path-layout change away from doing real damage as root.
source /etc/birdnet/birdnet.conf

services=(birdnet_recording.service
custom_recording.service
birdnet_analysis.service
chart_viewer.service
spectrogram_viewer.service)

for i in  "${services[@]}";do
  sudo systemctl stop  ${i}
done

# Refuse to run the rm unless RECS_DIR is actually a real directory.
if [ -z "${RECS_DIR}" ] || [ ! -d "${RECS_DIR}" ]; then
  echo "RECS_DIR is unset or not a directory ('${RECS_DIR}') - refusing to purge" >&2
  exit 1
fi
sudo rm -rf "${RECS_DIR}/$(date +%B-%Y/%d-%A)"/*
