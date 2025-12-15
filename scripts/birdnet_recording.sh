#!/usr/bin/env bash
# Performs the recording from the specified RTSP stream or soundcard
source /etc/birdnet/birdnet.conf

loop_ffmpeg(){
  while true;do
    if ! ffmpeg -hide_banner -xerror -loglevel $LOGGING_LEVEL -nostdin ${1} -i ${2} -vn -map a:0 -acodec pcm_s16le -ac 1 -ar ${SAMPLERATE} -f segment -segment_format wav -segment_time ${RECORDING_LENGTH} -strftime 1 ${RECS_DIR}/StreamData/%F-birdnet-RTSP_${3}-%H:%M:%S.wav
    then
      sleep 1
    fi
  done
}

# Set logging level, default to 'error' if not set
LOGGING_LEVEL="${LogLevel_BirdnetRecordingService:-error}"

# Additionally if we're at debug or info level then allow printing of script commands and variables
if [ "$LOGGING_LEVEL" == "info" ] || [ "$LOGGING_LEVEL" == "debug" ];then
  # Enable printing of commands/variables etc to terminal for debugging
  set -x
fi

REC_CARD="${REC_CARD:-default}"
RECORDING_LENGTH="${RECORDING_LENGTH:-15}"

# Set sample rate based on the model
if [[ "$MODEL" == "Perch_v2" ]]; then
  SAMPLERATE=32000
else
  SAMPLERATE=48000
fi

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
    arecord -f S16_LE -c${CHANNELS} -r ${SAMPLERATE} -t wav --max-file-time ${RECORDING_LENGTH}\
          -D "${REC_CARD}" --use-strftime ${RECS_DIR}/StreamData/%F-birdnet-%H:%M:%S.wav
  fi
fi
