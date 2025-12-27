# this should only contain functions and assignments, ie source install.sh should not have side effects.

get_tf_whl () {
  # Use Nachtzuster's BirdNET-Pi repository as the source for tflite wheels
  BASE_URL=https://github.com/Nachtzuster/BirdNET-Pi/releases/download/v0.1/

  ARCH=$(uname -m)
  PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info[0]}{sys.version_info[1]}')")
  
  # Determine which wheel to use based on architecture and Python version
  case "${ARCH}-${PY_VERSION}" in
    aarch64-39)
      WHL=tflite_runtime-2.17.1-cp39-cp39-linux_aarch64.whl
      ;;
    aarch64-310)
      WHL=tflite_runtime-2.17.1-cp310-cp310-linux_aarch64.whl
      ;;
    aarch64-311)
      WHL=tflite_runtime-2.17.1-cp311-cp311-linux_aarch64.whl
      ;;
    aarch64-312)
      WHL=tflite_runtime-2.17.1-cp312-cp312-linux_aarch64.whl
      ;;
    aarch64-313)
      WHL=tflite_runtime-2.17.1-cp313-cp313-linux_aarch64.whl
      ;;
    x86_64-*)
      # For x86_64, don't download a wheel - let pip install tensorflow from PyPI
      echo "Note: x86_64 architecture detected - will use pip to install tensorflow"
      WHL=''
      ;;
    *)
      echo "No tflite version found for ${ARCH}-${PY_VERSION}"
      WHL=''
      ;;
  esac
  
  if [ -n "$WHL" ]; then
    {
      curl -L -o $HOME/BirdNET-Pi/$WHL ${BASE_URL}${WHL}
      sed "s/tensorflow.*/$WHL/" $HOME/BirdNET-Pi/requirements.txt > requirements_custom.txt
    }
  else
    # For x86_64 or unknown architectures, keep tensorflow in requirements
    cp $HOME/BirdNET-Pi/requirements.txt requirements_custom.txt
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
  STATE=$(systemctl is-enabled tmp.mount 2>&1 | grep -E '(enabled|disabled|static)')
  ! [ -f /usr/share/systemd/tmp.mount ] && echo "Warning: no /usr/share/systemd/tmp.mount found"
  if [ -z $STATE ]; then
    cp -f /usr/share/systemd/tmp.mount /etc/systemd/system/tmp.mount
    systemctl daemon-reload
    systemctl enable tmp.mount
  else
    echo "tmp.mount is $STATE, skipping"
  fi
}
