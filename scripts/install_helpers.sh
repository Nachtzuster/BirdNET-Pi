# this should only contain functions and assignments, ie source install.sh should not have side effects.

get_tf_whl () {
  BASE_URL=https://github.com/Nachtzuster/BirdNET-Pi/releases/download/v0.1/

  ARCH=$(uname -m)
  PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info[0]}{sys.version_info[1]}')")
  case "${ARCH}-${PY_VERSION}" in
    aarch64-39)
      WHL=tflite_runtime-2.11.0-cp39-none-linux_aarch64.whl
      ;;
    aarch64-310)
      WHL=tflite_runtime-2.11.0-cp310-none-linux_aarch64.whl
      ;;
    aarch64-311)
      WHL=tflite_runtime-2.11.0-cp311-cp311-linux_aarch64.whl
      ;;
    aarch64-312)
      WHL=tflite_runtime-2.11.0-cp312-cp312-linux_aarch64.whl
      ;;
    x86_64-39)
      WHL=tflite_runtime-2.11.0-cp39-cp39-linux_x86_64.whl
      ;;
    x86_64-311)
      WHL=tflite_runtime-2.11.0-cp311-cp311-linux_x86_64.whl
      ;;
    x86_64-312)
      WHL=tflite_runtime-2.11.0-cp312-cp312-linux_x86_64.whl
      ;;
    *)
      echo "No tflite version found"
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
