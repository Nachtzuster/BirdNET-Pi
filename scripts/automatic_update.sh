#!/usr/bin/env bash
source /etc/birdnet/birdnet.conf
if [ ${AUTOMATIC_UPDATE} == 1 ]; then
  $HOME/BirdNET-Pi/scripts/update_birdnet.sh
  $HOME/BirdNET-Pi/scripts/restart_services.sh
fi
