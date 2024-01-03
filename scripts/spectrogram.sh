#!/usr/bin/env bash
# Make sox spectrogram
source /etc/birdnet/birdnet.conf

# Read the logging level from the configuration option
LOGGING_LEVEL="${LogLevel_SpectrogramViewerService}"
# If empty for some reason default to log level of error
[ -z $LOGGING_LEVEL ] && LOGGING_LEVEL='error'
# Additionally if we're at debug or info level then allow printing of script commands and variables
if [ "$LOGGING_LEVEL" == "info" ] || [ "$LOGGING_LEVEL" == "debug" ];then
  # Enable printing of commands/variables etc to terminal for debugging
  set -x
fi

# Continuously loop generating a spectrogram
inotifywait -m --format '%w%f' \
  -e close_write "${RECS_DIR}/StreamData/" |
while read -r analyzing_now; do

  if [ -n "${analyzing_now}" ] && [ -f "${analyzing_now}" ]; then
    spectrogram_png=${EXTRACTED}/spectrogram.png
    sox -V1 "${analyzing_now}" -n remix 1 rate 24k spectrogram -c "${analyzing_now//$HOME\//}" -o "${spectrogram_png}"
  fi
done
