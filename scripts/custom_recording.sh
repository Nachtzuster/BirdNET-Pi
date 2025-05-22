#!/usr/bin/env bash
set -x
source /etc/birdnet/birdnet.conf

STAMP="%H:%M:%S"

[ -z $RECORDING_LENGTH ] && RECORDING_LENGTH=15

if ! pulseaudio --check;then pulseaudio --start;fi

CUSTOM_WINDOW_START=(0 3 15 22)
CUSTOM_WINDOW_END=(0 7 19 23)
RECORDING_DURATION=60
PAUSE_DURATION=240

now=$(date +%H)

SAMPLING_RATE=48000
if [ "$BATS_ANALYSIS" = "1" ]; then
    SAMPLING_RATE="${BATS_SAMPLING_RATE:-256000}"
fi

while [ $now -ge ${CUSTOM_WINDOW_START[0]} ] && [ $now -le ${CUSTOM_WINDOW_END[0]} ];do
  echo $now
  # If you prefer no directory structure under "Raw", comment out the
  # lines below and uncommend the commands at the bottom.
  arecord -f S16_LE -c${CHANNELS} -r${SAMPLING_RATE} -t wav -d $RECORDING_DURATION \
    --use-strftime ${EXTRACTED}/Raw/%B-%Y/%d-%A/%F-birdnet-${STAMP}.wav
  
  # Uncomment the lines below if you'd prefer having no directory scructure
  # under the "Raw" directory. Be sure to comment out the command above.
  #arecord -f S16_LE -c${CHANNELS} -r${SAMPLING_RATE} -t wav -d $RECORDING_DURATION \
  #  --use-strftime ${EXTRACTED}/Raw/%F-birdnet-${STAMP}.wav
  sleep $PAUSE_DURATION
  now=$(date +%H)
done
while [ $now -ge ${CUSTOM_WINDOW_START[1]} ] && [ $now -le ${CUSTOM_WINDOW_END[1]} ];do
  echo $now
  # If you prefer no directory structure under "Raw", comment out the
  # lines below and uncommend the commands at the bottom.
  arecord -f S16_LE -c${CHANNELS} -r${SAMPLING_RATE} -t wav -d $RECORDING_DURATION \
    --use-strftime ${EXTRACTED}/Raw/%B-%Y/%d-%A/%F-birdnet-${STAMP}.wav
  
  # Uncomment the lines below if you'd prefer having no directory scructure
  # under the "Raw" directory. Be sure to comment out the command above.
  #arecord -f S16_LE -c${CHANNELS} -r${SAMPLING_RATE} -t wav -d $RECORDING_DURATION \
  #  --use-strftime ${EXTRACTED}/Raw/%F-birdnet-${STAMP}.wav
  sleep $PAUSE_DURATION
  now=$(date +%H)
done
while [ $now -ge ${CUSTOM_WINDOW_START[2]} ] && [ $now -le ${CUSTOM_WINDOW_END[2]} ];do
  echo $now
  # If you prefer no directory structure under "Raw", comment out the
  # lines below and uncommend the commands at the bottom.
  arecord -f S16_LE -c${CHANNELS} -r${SAMPLING_RATE} -t wav -d $RECORDING_DURATION \
    --use-strftime ${EXTRACTED}/Raw/%B-%Y/%d-%A/%F-birdnet-${STAMP}.wav
  
  # Uncomment the lines below if you'd prefer having no directory scructure
  # under the "Raw" directory. Be sure to comment out the command above.
  #arecord -f S16_LE -c${CHANNELS} -r${SAMPLING_RATE} -t wav -d $RECORDING_DURATION \
  #  --use-strftime ${EXTRACTED}/Raw/%F-birdnet-${STAMP}.wav 
  sleep $PAUSE_DURATION
  now=$(date +%H)
done
while [ $now -ge ${CUSTOM_WINDOW_START[3]} ] && [ $now -le ${CUSTOM_WINDOW_END[3]} ];do
  echo $now
  # If you prefer no directory structure under "Raw", comment out the
  # lines below and uncommend the commands at the bottom.
  arecord -f S16_LE -c${CHANNELS} -r${SAMPLING_RATE} -t wav -d $RECORDING_DURATION \
    --use-strftime ${EXTRACTED}/Raw/%B-%Y/%d-%A/%F-birdnet-${STAMP}.wav
  
  # Uncomment the lines below if you'd prefer having no directory scructure
  # under the "Raw" directory. Be sure to comment out the command above.
  #arecord -f S16_LE -c${CHANNELS} -r${SAMPLING_RATE} -t wav -d $RECORDING_DURATION \
  #  --use-strftime ${EXTRACTED}/Raw/%F-birdnet-${STAMP}.wav
  sleep $PAUSE_DURATION
  now=$(date +%H)
done
