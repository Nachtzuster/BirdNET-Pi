#!/usr/bin/env bash

source /etc/birdnet/birdnet.conf
if [ "$MODEL" == "BirdNET_GLOBAL_6K_V2.4_Model_FP16" ]; then
  BASEDIR=labels_nm
else
  BASEDIR=labels_l18n
fi

label_file_name="labels_${DATABASE_LANG}.txt"

ln -sf ${BASEDIR}/${label_file_name} $HOME/BirdNET-Pi/model/labels.txt
