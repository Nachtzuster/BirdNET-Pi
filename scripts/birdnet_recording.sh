#!/usr/bin/env bash
# Performs the recording from the specified RTSP stream or soundcard
source /etc/birdnet/birdnet.conf

loop_ffmpeg(){
  while true;do
    if ! ffmpeg -hide_banner -loglevel $LOGGING_LEVEL -nostdin ${1} -i ${2} -vn -map a:0 -acodec pcm_s16le -ac 2 -ar 48000 -f segment -segment_format wav -segment_time ${RECORDING_LENGTH} -strftime 1 ${RECS_DIR}/StreamData/%F-birdnet-RTSP_${3}-%H:%M:%S.wav
    then
      sleep 1
    fi
  done
}

# Read the logging level from the configuration option
LOGGING_LEVEL="${LogLevel_BirdnetRecordingService}"
# If empty for some reason default to log level of error
[ -z $LOGGING_LEVEL ] && LOGGING_LEVEL='error'
# Additionally if we're at debug or info level then allow printing of script commands and variables
if [ "$LOGGING_LEVEL" == "info" ] || [ "$LOGGING_LEVEL" == "debug" ];then
  # Enable printing of commands/variables etc to terminal for debugging
  set -x
fi

[ -z $RECORDING_LENGTH ] && RECORDING_LENGTH=15
[ -d $RECS_DIR/StreamData ] || mkdir -p $RECS_DIR/StreamData

if [ -n "${RTSP_STREAM}" ];then
  # Explode the RTSP steam setting into an array so we can count the number we have
  RTSP_STREAMS_EXPLODED_ARRAY=(${RTSP_STREAM//,/ })
  FFMPEG_VERSION=$(ffmpeg -version | head -n 1 | cut -d ' ' -f 3 | cut -d '.' -f 1)

  STREAM_COUNT=1
  # Loop over the streams
  for i in "${RTSP_STREAMS_EXPLODED_ARRAY[@]}"
  do
    if [[ "$i" =~ ^rtsps?:// ]]; then
      [ $FFMPEG_VERSION -lt 5 ] && PARAM=-stimeout || PARAM=-timeout
      TIMEOUT_PARAM="$PARAM 10000000"
    elif [[ "$i" =~ ^[a-z]+:// ]]; then
      TIMEOUT_PARAM="-rw_timeout 10000000"
    else
      TIMEOUT_PARAM=""
    fi
    loop_ffmpeg "${TIMEOUT_PARAM}" "${i}" "${STREAM_COUNT}" &
    ((STREAM_COUNT += 1))
  done
  wait
else
  if ! pulseaudio --check;then pulseaudio --start;fi
  if pgrep arecord &> /dev/null ;then
    echo "Recording"
  else
    if [ -z ${REC_CARD} ];then
      arecord -f S16_LE -c${CHANNELS} -r48000 -t wav --max-file-time ${RECORDING_LENGTH}\
	      	      	       --use-strftime ${RECS_DIR}/StreamData/%F-birdnet-%H:%M:%S.wav
    else
      arecord -f S16_LE -c${CHANNELS} -r48000 -t wav --max-file-time ${RECORDING_LENGTH}\
        -D "${REC_CARD}" --use-strftime ${RECS_DIR}/StreamData/%F-birdnet-%H:%M:%S.wav
    fi
  fi
fi
