#!/usr/bin/env bash
# A comprehensive log dumper
# set -x # Uncomment to debug
source /etc/birdnet/birdnet.conf &> /dev/null
LOG_DIR="${HOME}/BirdNET-Pi/logs"
my_dir=$HOME/BirdNET-Pi/scripts
# Must be an ARRAY: as a plain string, "${services[@]}" below expands to a single
# element holding every service name joined by newlines, so the -L test never
# matched and the bundle shipped with no journals at all. (uninstall.sh does this
# correctly.)
services=($(awk '/service/ && /systemctl/ && !/php/ {print $3}' ${my_dir}/install_services.sh | sort -u))

# Create logs directory
[ -d ${LOG_DIR} ] || mkdir ${LOG_DIR}

# Create services logs
for i in "${services[@]}";do
  if [ -L "/etc/systemd/system/multi-user.target.wants/${i}" ];then
    journalctl -u ${i} -n 100 --no-pager > ${LOG_DIR}/${i}.log
    cp -L /etc/systemd/system/multi-user.target.wants/${i} ${LOG_DIR}/${i}
  fi
done

# Create password-removed birdnet.conf
# Prefer the canonical location the rest of the tree sources; fall back to the
# in-tree copy so this keeps working on older layouts.
CONF=/etc/birdnet/birdnet.conf
[ -f "${CONF}" ] || CONF="${HOME}/BirdNET-Pi/birdnet.conf"
sed -e '/PWD=/d' "${CONF}" > ${LOG_DIR}/birdnet.conf

# Create password-removed Caddyfile
if [ -f /etc/caddy/Caddyfile ];then
  sed -e '/basicauth/,+2d' /etc/caddy/Caddyfile > ${LOG_DIR}/Caddyfile
fi  

# Get sound card specs
SOUND_CARD="$(aplay -L \
  | awk -F, '/^hw:/ {print $1}' \
  | grep -ve 'vc4' -e 'Head' -e 'PCH' \
  | uniq)"
echo "SOUND_CARD=${SOUND_CARD}" > ${LOG_DIR}/soundcard
# --dump-hw-params opens the capture device, which on a *running* station is
# always held by the recorder, so arecord blocks indefinitely and dump_logs
# never returns - i.e. you could not collect logs from a live station, which is
# exactly when you need them. Bound it, and say so in the output rather than
# silently omitting the section.
if [ -n "${SOUND_CARD}" ]; then
  if ! timeout 10 arecord -D "${SOUND_CARD}" --dump-hw-params >> ${LOG_DIR}/soundcard 2>&1; then
    echo "(hw params unavailable: device busy or timed out - expected while the recorder is running)" \
      >> ${LOG_DIR}/soundcard
  fi
else
  echo "(no capture card detected)" >> ${LOG_DIR}/soundcard
fi

# Get system info
CALLS=("df -h" "free -h" "ifconfig" "find ${RECS_DIR}")

for i in "${CALLS[@]}";do
  ${i} >> ${LOG_DIR}/sysinfo
  echo "
===============================================================================
===============================================================================

" >> ${LOG_DIR}/sysinfo
done

# TAR the logs into a ball
tar --remove-files -cvpzf ${HOME}/BirdNET-Pi/logs.tar.gz ${LOG_DIR} &> /dev/null
# Finished
echo "Your compressed logs are located at ${HOME}/BirdNET-Pi/logs.tar.gz"
