#!/usr/bin/env bash

if [ "$EUID" == 0 ]
  then echo "Please run as a non-root user."
  exit
fi

if [ "$(uname -m)" != "aarch64" ] && [ "$(uname -m)" != "x86_64" ];then
  echo "BirdNET-Pi requires a 64-bit OS.
It looks like your operating system is using $(uname -m),
but would need to be aarch64."
  exit 1
fi

PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info[0]}{sys.version_info[1]}')")
if [ "${PY_VERSION}" == "39" ] ;then
  echo "### BirdNET-Pi requires a newer OS. Bullseye is deprecated, please use Bookworm. ###"
  [ -z "${FORCE_BULLSEYE}" ] && exit
fi

# we require passwordless sudo
sudo -K
if ! sudo -n true; then
    echo "Passwordless sudo is not working. Aborting"
    exit
fi

# Simple new installer
HOME=$HOME
USER=$USER

export HOME=$HOME
export USER=$USER

PACKAGES_MISSING=
for cmd in git jq ; do
  if ! which $cmd &> /dev/null;then
      PACKAGES_MISSING="${PACKAGES_MISSING} $cmd"
  fi
done
if [[ ! -z $PACKAGES_MISSING ]] ; then
  sudo apt update
  sudo apt -y install $PACKAGES_MISSING
fi

branch=main
git clone -b $branch --depth=1 https://github.com/YvedD/BirdNET-Pi-MigCount.git ${HOME}/BirdNET-Pi &&

# Check if WiFi setup is needed
if ! ping -c 1 -W 2 google.com &> /dev/null; then
    echo "No internet connection detected. Starting WiFi setup..."
    $HOME/BirdNET-Pi/scripts/setup_wifi_web.sh
    python3 /tmp/birdnet-wifi-setup/wifi_server.py &
    WIFI_PID=$!
    
    echo ""
    echo "=========================================="
    echo "  Open uw browser en ga naar:"
    echo "  http://birdnetpi.local:8080"
    echo "  of gebruik het IP adres van deze Pi"
    echo "=========================================="
    echo ""
    
    # Wait for WiFi configuration to complete
    while [ ! -f /tmp/birdnet-wifi-setup/complete ]; do
        sleep 1
    done
    
    kill $WIFI_PID 2>/dev/null || true
    rm -rf /tmp/birdnet-wifi-setup
fi

$HOME/BirdNET-Pi/scripts/install_birdnet.sh
if [ ${PIPESTATUS[0]} -eq 0 ];then
  echo "Installation completed successfully"
  sudo reboot
else
  echo "The installation exited unsuccessfully."
  exit 1
fi
