#!/usr/bin/env bash
# Install BirdNET script
set -x # Debugging
exec > >(tee -i installation-$(date +%F).txt) 2>&1 # Make log
set -e # exit installation if anything fails

my_dir=$HOME/BirdNET-Pi
export my_dir=$my_dir

cd $my_dir/scripts || exit 1
git log -n 1 --pretty=oneline --no-color --decorate

source install_helpers.sh

if [ "$(uname -m)" != "aarch64" ] && [ "$(uname -m)" != "x86_64" ];then
  echo "BirdNET-Pi requires a 64-bit OS.
It looks like your operating system is using $(uname -m),
but would need to be aarch64."
  exit 1
fi

#Install/Configure /etc/birdnet/birdnet.conf
./install_config.sh || exit 1
sudo -E HOME=$HOME USER=$USER ./install_services.sh || exit 1
source /etc/birdnet/birdnet.conf

install_birdnet() {
  TMP_SIZE=$(df --output=avail /tmp | tail -n 1)
  if [[ $TMP_SIZE -lt 300000 ]]; then
    mkdir -p $HOME/bird_tmp
    export TMPDIR=$HOME/bird_tmp
  fi
  cd ~/BirdNET-Pi || exit 1
  echo "Establishing a python virtual environment"
  python3 -m venv birdnet
  source ./birdnet/bin/activate
  pip3 install wheel
  get_tf_whl
  LOOP_COUNT=2
  while ! pip3 install -U -r ./requirements_custom.txt
  do
    LOOP_COUNT=$(( LOOP_COUNT - 1 ))
    pip3 cache purge
    [ $LOOP_COUNT == 0 ] && exit 1
    sleep 5
  done
  rm -rf $HOME/bird_tmp
}

[ -d ${RECS_DIR} ] || mkdir -p ${RECS_DIR} &> /dev/null

install_birdnet

cd $my_dir/scripts || exit 1

# tzlocal.get_localzone() will fail if the Debian specific /etc/timezone is not in sync
CURRENT_TIMEZONE=$(timedatectl show --value --property=Timezone)
[ -f /etc/timezone ] && echo "$CURRENT_TIMEZONE" | sudo tee /etc/timezone > /dev/null

./install_language_label.sh || exit 1

# Optional TFT Display Installation
echo ""
echo "=== TFT Display Support (Optional) ==="
echo "BirdNET-Pi supports TFT displays with XPT2046 touch controller."
echo "This allows you to display bird detections on a small screen connected via SPI."
echo ""

# Check if we're in an interactive session
if [ -t 0 ]; then
    # Attempt to detect TFT hardware
    echo "Detecting TFT hardware..."
    if ./detect_tft.sh > /dev/null 2>&1; then
        echo "TFT display hardware detected!"
        echo ""
        read -p "Would you like to install TFT display support now? (y/n): " install_tft_choice
        
        if [ "$install_tft_choice" = "y" ] || [ "$install_tft_choice" = "Y" ]; then
            echo ""
            echo "Installing TFT display support..."
            ./install_tft.sh || echo "TFT installation had issues, but continuing..."
        else
            echo "Skipping TFT installation. You can install it later by running: ~/BirdNET-Pi/scripts/install_tft.sh"
        fi
    else
        echo "No TFT display hardware detected."
        read -p "Would you like to install TFT display support anyway for future use? (y/n): " install_tft_choice
        
        if [ "$install_tft_choice" = "y" ] || [ "$install_tft_choice" = "Y" ]; then
            echo ""
            echo "Installing TFT display support..."
            ./install_tft.sh || echo "TFT installation had issues, but continuing..."
        else
            echo "Skipping TFT installation. You can install it later by running: ~/BirdNET-Pi/scripts/install_tft.sh"
        fi
    fi
else
    echo "Non-interactive installation detected. Skipping TFT installation."
    echo "You can install TFT support later by running: ~/BirdNET-Pi/scripts/install_tft.sh"
fi

echo ""

exit 0
