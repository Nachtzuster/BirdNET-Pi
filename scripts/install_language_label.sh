#!/usr/bin/env bash

source /etc/birdnet/birdnet.conf
cd /home/$BIRDNET_USER/BirdNET-Pi/scripts

python3 -c 'from utils.helpers import set_label_file; set_label_file()'

cd -
