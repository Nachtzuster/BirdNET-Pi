# this should only contain functions and assignments, ie source install.sh should not have side effects.

get_tf_whl () {
  BASE_URL=https://github.com/Nachtzuster/BirdNET-Pi/releases/download/v0.1/

  ARCH=$(uname -m)
  PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info[0]}{sys.version_info[1]}')")
  case "${ARCH}-${PY_VERSION}" in
    aarch64-39)
      WHL=tflite_runtime-2.11.0-cp39-none-linux_aarch64.whl
      ;;
    aarch64-311)
      WHL=tflite_runtime-2.17.1-cp311-cp311-linux_aarch64.whl
      ;;
    aarch64-312)
      WHL=tflite_runtime-2.17.1-cp312-cp312-linux_aarch64.whl
      ;;
    x86_64-39)
      WHL=tflite_runtime-2.11.0-cp39-cp39-linux_x86_64.whl
      ;;
    x86_64-311)
      WHL=tflite_runtime-2.17.1-cp311-cp311-linux_x86_64.whl
      ;;
    x86_64-312)
      WHL=tflite_runtime-2.17.1-cp312-cp312-linux_x86_64.whl
      ;;
    *)
      echo "No tflite version found for ${ARCH}-${PY_VERSION}"
      WHL=''
      ;;
  esac
  if [ -n "$WHL" ]; then
    {
      curl -L -o $HOME/BirdNET-Pi/$WHL $BASE_URL$WHL
      sed "s/tflite_runtime.*/$WHL/" $HOME/BirdNET-Pi/requirements.txt > requirements_custom.txt
    }
  fi
}

install_birdnet_mount() {
  TMP_MOUNT=$(systemd-escape -p --suffix=mount "$RECS_DIR/StreamData")
  cat << EOF > $HOME/BirdNET-Pi/templates/$TMP_MOUNT
[Unit]
Description=Birdnet tmpfs for transient files
ConditionPathExists=$RECS_DIR/StreamData

[Mount]
What=tmpfs
Where=$RECS_DIR/StreamData
Type=tmpfs
Options=mode=1777,nosuid,nodev

[Install]
WantedBy=multi-user.target
EOF
  ln -sf $HOME/BirdNET-Pi/templates/$TMP_MOUNT /usr/lib/systemd/system
}

install_tmp_mount() {
  STATE=$(systemctl is-enabled tmp.mount 2>&1 | grep -E '(enabled|disabled)')
  ! [ -f /usr/share/systemd/tmp.mount ] && echo "Warning: no /usr/share/systemd/tmp.mount found"
  if [ -z $STATE ]; then
    cp -f /usr/share/systemd/tmp.mount /etc/systemd/system/tmp.mount
    systemctl daemon-reload
    systemctl enable tmp.mount
  else
    echo "tmp.mount is $STATE, skipping"
  fi
}

install_birdweather_past_publication() {
  cat << EOF > $HOME/BirdNET-Pi/templates/birdweather_past_publication@.service
[Unit]
Description=BirdWeather Publication for %i interface
After=network-online.target
Wants=network-online.target
[Service]
Type=oneshot
User=${USER}
ExecStartPre= /bin/sh -c 'n=0; until curl --silent --head --fail https://app.birdweather.com >/dev/null || [ \$n -ge 30 ]; do n=\$((n+1)); sleep 5; done;'
ExecStart=$PYTHON_VIRTUAL_ENV /usr/local/bin/birdweather_past_publication.py
EOF
  cat << EOF > $HOME/BirdNET-Pi/templates/50-birdweather-past-publication
#!/bin/bash
UNIT_NAME="birdweather_past_publication@\$IFACE.service"
# Check if the service is active and then start it
if systemctl is-active --quiet "\$UNIT_NAME"; then
    echo "\$UNIT_NAME is already running."
else
    echo "Starting \$UNIT_NAME..."
    systemctl start "\$UNIT_NAME"
fi
EOF
  chmod +x $HOME/BirdNET-Pi/templates/50-birdweather-past-publication
  chown root:root $HOME/BirdNET-Pi/templates/50-birdweather-past-publication
  ln -sf $HOME/BirdNET-Pi/templates/50-birdweather-past-publication /etc/networkd-dispatcher/routable.d
  ln -sf $HOME/BirdNET-Pi/templates/birdweather_past_publication@.service /usr/lib/systemd/system
  systemctl enable systemd-networkd
}
