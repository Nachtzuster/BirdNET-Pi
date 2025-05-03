#!/usr/bin/env bash
set -x
# Update BirdNET-Pi
trap 'exit 1' SIGINT SIGHUP
source /etc/birdnet/birdnet.conf
if [ -n "${BIRDNET_USER}" ]; then
  echo "BIRDNET_USER: ${BIRDNET_USER}"
  USER=${BIRDNET_USER}
  HOME=/home/${BIRDNET_USER}
else
  echo "WARNING: no BIRDNET_USER found"
  USER=$(awk -F: '/1000/ {print $1}' /etc/passwd)
  HOME=$(awk -F: '/1000/ {print $6}' /etc/passwd)
fi
my_dir=$HOME/BirdNET-Pi/scripts
source "$my_dir/install_helpers.sh"

# Sets proper permissions and ownership
find $HOME/Bird* -type f ! -perm -g+wr -exec chmod g+wr {} + 2>/dev/null
find $HOME/Bird* -not -user $USER -execdir sudo -E chown $USER:$USER {} \+
chmod 666 ~/BirdNET-Pi/scripts/*.txt
chmod 666 ~/BirdNET-Pi/*.txt
find $HOME/BirdNET-Pi -path "$HOME/BirdNET-Pi/birdnet" -prune -o -type f ! -perm /o=w -exec chmod a+w {} \;
chmod g+r $HOME

# remove world-writable perms
chmod -R o-w ~/BirdNET-Pi/templates/*

APT_UPDATED=0
PIP_UPDATED=0

# helpers
sudo_with_user () {
  sudo -u $USER "$@"
}

ensure_apt_updated () {
  [[ $APT_UPDATED != "UPDATED" ]] && apt-get update && APT_UPDATED="UPDATED"
}

ensure_pip_updated () {
  [[ $PIP_UPDATED != "UPDATED" ]] && sudo_with_user $HOME/BirdNET-Pi/birdnet/bin/pip3 install -U pip && PIP_UPDATED="UPDATED"
}

remove_unit_file() {
  # remove_unit_file pushed_notifications.service $HOME/BirdNET-Pi/templates/pushed_notifications.service
  if systemctl list-unit-files "${1}" &>/dev/null;then
    systemctl disable --now "${1}"
    rm -f "/usr/lib/systemd/system/${1}"
    rm "$HOME/BirdNET-Pi/templates/${1}"
    if [ $# == 2 ]; then
      rm -f "${2}"
    fi
  fi
}

ensure_python_package() {
  # ensure_python_package pytest pytest==7.1.2
  pytest_installation_status=$(~/BirdNET-Pi/birdnet/bin/python3 -c 'import pkgutil; import sys; print("installed" if pkgutil.find_loader(sys.argv[1]) else "not installed")' "$1")
  if [[ "$pytest_installation_status" = "not installed" ]];then
    ensure_pip_updated
    sudo_with_user $HOME/BirdNET-Pi/birdnet/bin/pip3 install "$2"
  fi
}

# sed -i on /etc/birdnet/birdnet.conf overwites the symbolic link - restore the link
if ! [ -L /etc/birdnet/birdnet.conf ] ; then
  sudo_with_user cp -f /etc/birdnet/birdnet.conf $HOME/BirdNET-Pi/
  ln -fs  $HOME/BirdNET-Pi/birdnet.conf /etc/birdnet/birdnet.conf
fi

# update snippets below
SRC="APPRISE_NOTIFICATION_BODY='(.*)'$"
DST='APPRISE_NOTIFICATION_BODY="\1"'
sed -i --follow-symlinks -E "s/$SRC/$DST/" /etc/birdnet/birdnet.conf

if ! grep -E '^DATA_MODEL_VERSION=' /etc/birdnet/birdnet.conf &>/dev/null;then
    echo "DATA_MODEL_VERSION=1" >> /etc/birdnet/birdnet.conf
fi

if ! grep -E '^BIRDNET_USER=' /etc/birdnet/birdnet.conf &>/dev/null;then
  echo "## BIRDNET_USER is for scripts to easily find where BirdNET-Pi is installed" >> /etc/birdnet/birdnet.conf
  echo "## DO NOT EDIT!" >> /etc/birdnet/birdnet.conf
  echo "BIRDNET_USER=$(awk -F: '/1000/ {print $1}' /etc/passwd)" >> /etc/birdnet/birdnet.conf
fi

if ! grep -E '^RTSP_STREAM_TO_LIVESTREAM=' /etc/birdnet/birdnet.conf &>/dev/null;then
  echo "RTSP_STREAM_TO_LIVESTREAM=\"0\"" >> /etc/birdnet/birdnet.conf
fi

SRC='^APPRISE_NOTIFICATION_BODY="A \$comname \(\$sciname\)  was just detected with a confidence of \$confidence"$'
DST='APPRISE_NOTIFICATION_BODY="A \$comname (\$sciname)  was just detected with a confidence of \$confidence (\$reason)"'
sed -i --follow-symlinks -E "s/$SRC/$DST/" /etc/birdnet/birdnet.conf

if ! grep -E '^INFO_SITE=' /etc/birdnet/birdnet.conf &>/dev/null;then
  echo "INFO_SITE=\"ALLABOUTBIRDS\"" >> /etc/birdnet/birdnet.conf
fi

if ! grep -E '^COLOR_SCHEME=' /etc/birdnet/birdnet.conf &>/dev/null;then
  echo "COLOR_SCHEME=\"light\"" >> /etc/birdnet/birdnet.conf
fi

if ! grep -E '^PURGE_THRESHOLD=' /etc/birdnet/birdnet.conf &>/dev/null;then
  echo "PURGE_THRESHOLD=95" >> /etc/birdnet/birdnet.conf
fi

if ! grep -E '^MAX_FILES_SPECIES=' /etc/birdnet/birdnet.conf &>/dev/null;then
  echo "MAX_FILES_SPECIES=\"0\"" >> /etc/birdnet/birdnet.conf
fi

if ! grep -E '^RARE_SPECIES_THRESHOLD=' /etc/birdnet/birdnet.conf &>/dev/null;then
  echo '## RARE_SPECIES_THRESHOLD defines after how many days a species is considered as rare and highlighted on overview page' >> /etc/birdnet/birdnet.conf
  echo "RARE_SPECIES_THRESHOLD=\"30\"" >> /etc/birdnet/birdnet.conf
fi

if ! grep -E '^BATS_ANALYSIS=' /etc/birdnet/birdnet.conf &>/dev/null;then
  echo '# BATS_ANALYSIS defines if the model analyses birds or bats. Set to 1 to use BattyBirdNET-Analyzer model' >> /etc/birdnet/birdnet.conf
  echo "BATS_ANALYSIS=0" >> /etc/birdnet/birdnet.conf
fi

if ! grep -E '^BATS_SAMPLING_RATE=' /etc/birdnet/birdnet.conf &>/dev/null; then
  echo '# BATS_SAMPLING_RATE : if using the bats model, please define your SAMPLING RATE' >> /etc/birdnet/birdnet.conf
  echo "BATS_SAMPLING_RATE=256000" >> /etc/birdnet/birdnet.conf
fi

if ! grep -E '^BATS_CLASSIFIER=' /etc/birdnet/birdnet.conf &>/dev/null; then
  echo '# BATS_CLASSIFIER : type of model to use' >> /etc/birdnet/birdnet.conf
  echo "BATS_CLASSIFIER=Bavaria" >> /etc/birdnet/birdnet.conf
fi

if ! grep -E '^TIMER=' /etc/birdnet/birdnet.conf &>/dev/null;then
  echo '# Set this value to 0 to have a continuous monitoring, and 1 to enable automated services control according to time' >> /etc/birdnet/birdnet.conf
  echo "TIMER=0" >> /etc/birdnet/birdnet.conf
fi

if ! grep -E '^TIMER_SWITCH=' /etc/birdnet/birdnet.conf &>/dev/null;then
  echo '# If you set TIMER_SWITCH to 1, your system will use your main analyzer during the start-stop defined (birds, except if BATS_ANALYSIS is set to 1), and the alternate analyzer during the night' >> /etc/birdnet/birdnet.conf
  echo "TIMER_SWITCH=0" >> /etc/birdnet/birdnet.conf
fi

if ! grep -E '^TIMER_START=' /etc/birdnet/birdnet.conf &>/dev/null; then
  echo '# TIMER_START : can be "Sunrise", "Sunset", or a specific time such as "06:00"' >> /etc/birdnet/birdnet.conf
  echo "TIMER_START=Sunrise" >> /etc/birdnet/birdnet.conf
fi

if ! grep -E '^TIMER_STOP=' /etc/birdnet/birdnet.conf &>/dev/null; then
  echo '# TIMER_STOP : can be "Sunset", "Sunrise", or a specific time such as "18:00"' >> /etc/birdnet/birdnet.conf
  echo "TIMER_STOP=Sunset" >> /etc/birdnet/birdnet.conf
fi

if ! grep -E '^DENOISING=' /etc/birdnet/birdnet.conf &>/dev/null; then
  echo '# DENOISING : if set to 1, will perform denoising on the files. Mostly useful for bats' >> /etc/birdnet/birdnet.conf
  echo "DENOISING=0" >> /etc/birdnet/birdnet.conf
fi

if ! grep -E '^DENOISING_PROFILE=' /etc/birdnet/birdnet.conf &>/dev/null; then
  echo '# DENOISING_PROFILE : define the model, relative to the path of your BirdNET-Pi installation. Mostly useful for bats.' >> /etc/birdnet/birdnet.conf
  echo "DENOISING_PROFILE=BattyBirdNET-Analyzer/checkpoints/bats/mic-noise/audiomoth_v12.prof" >> /etc/birdnet/birdnet.conf
fi

if ! grep -E '^DENOISING_FACTOR=' /etc/birdnet/birdnet.conf &>/dev/null; then
  echo '# DENOISING_FACTOR : factor for denoising' >> /etc/birdnet/birdnet.conf
  echo "DENOISING_FACTOR=0.22" >> /etc/birdnet/birdnet.conf
fi

if [ ! -L "$HOME/BirdNET-Pi/templates/birdnet_timer.service" ]; then
  ln -sf "$HOME/BirdNET-Pi"/scripts/birdnet_timer.py /usr/local/bin/
  chown "$USER:$USER" "$HOME/BirdNET-Pi"/scripts/birdnet_timer.py
  echo "Installing birdnet_timer.service"
  cat << EOF > $HOME/BirdNET-Pi/templates/birdnet_timer.service
[Unit]
Description=BirdNET Timer Service (Specific recording periods, and switch bat/bird mode automatically)
[Service]
Restart=always
Type=simple
RestartSec=2
User=${USER}
ExecStart=$PYTHON_VIRTUAL_ENV /usr/local/bin/birdnet_timer.py
[Install]
WantedBy=multi-user.target
EOF
  ln -sf $HOME/BirdNET-Pi/templates/birdnet_timer.service /usr/lib/systemd/system
  systemctl enable birdnet_timer.service
  systemctl daemon-reload && restart_services.sh
fi

if [ ! -d "$HOME"/BirdNET-Pi/BattyBirdNET-Analyzer/server.py ]; then
  if [ -d "$HOME"/BirdNET-Pi/BattyBirdNET-Analyzer ]; then
    rm -r "$HOME"/BirdNET-Pi/BattyBirdNET-Analyzer
  fi
  branch_classifier=main
  git clone -b $branch_classifier --depth=1 https://github.com/rdz-oss/BattyBirdNET-Analyzer.git ${HOME}/BirdNET-Pi/BattyBirdNET-Analyzer
  chown -R pi:pi ${HOME}/BirdNET-Pi/BattyBirdNET-Analyzer
fi

[ -d $RECS_DIR/StreamData ] || sudo_with_user mkdir -p $RECS_DIR/StreamData
[ -L ${EXTRACTED}/spectrogram.png ] || sudo_with_user ln -sf ${RECS_DIR}/StreamData/spectrogram.png ${EXTRACTED}/spectrogram.png

if ! which inotifywait &>/dev/null;then
  ensure_apt_updated
  apt-get -y install inotify-tools
fi

apprise_version=$($HOME/BirdNET-Pi/birdnet/bin/python3 -c "import apprise; print(apprise.__version__)" 2>/dev/null || echo "0")
[[ $apprise_version != "1.9.0" ]] && sudo_with_user $HOME/BirdNET-Pi/birdnet/bin/pip3 install apprise==1.9.0
version=$($HOME/BirdNET-Pi/birdnet/bin/python3 -c "import streamlit; print(streamlit.__version__)" 2>/dev/null || echo "0")
[[ $version != "1.44.0" ]] && sudo_with_user $HOME/BirdNET-Pi/birdnet/bin/pip3 install streamlit==1.44.0
version=$($HOME/BirdNET-Pi/birdnet/bin/python3 -c "import seaborn; print(seaborn.__version__)" 2>/dev/null || echo "0")
[[ $version != "0.13.2" ]] && sudo_with_user $HOME/BirdNET-Pi/birdnet/bin/pip3 install seaborn==0.13.2
version=$($HOME/BirdNET-Pi/birdnet/bin/python3 -c "import suntime; print(suntime.__version__)" 2>/dev/null || echo "0")
[[ $version != "1.3.2" ]] && sudo_with_user $HOME/BirdNET-Pi/birdnet/bin/pip3 install suntime==1.3.2
version=$($HOME/BirdNET-Pi/birdnet/bin/python3 -c "import bottle; print(bottle.__version__)" 2>/dev/null || echo "0")
[[ $version != "0.12.25" ]] && sudo_with_user $HOME/BirdNET-Pi/birdnet/bin/pip3 install bottle==0.12.25

PY_VERSION=$($HOME/BirdNET-Pi/birdnet/bin/python3 -c "import sys; print(f'{sys.version_info[0]}{sys.version_info[1]}')")
tf_version=$($HOME/BirdNET-Pi/birdnet/bin/python3 -c "import tflite_runtime; print(tflite_runtime.__version__)")
if [ "$tf_version" != "2.11.0" ]; then
  get_tf_whl
  # include our numpy dependants so pip can figure out which numpy version to install
  sudo_with_user $HOME/BirdNET-Pi/birdnet/bin/pip3 install $HOME/BirdNET-Pi/$WHL pandas librosa matplotlib
fi

ensure_python_package inotify inotify

if ! which inotifywait &>/dev/null;then
  ensure_apt_updated
  apt-get -y install inotify-tools
fi

install_tmp_mount
remove_unit_file birdnet_server.service /usr/local/bin/server.py
remove_unit_file extraction.service /usr/local/bin/extract_new_birdsounds.sh

if ! grep 'daemon' $HOME/BirdNET-Pi/templates/chart_viewer.service &>/dev/null;then
  sed -i "s|daily_plot.py.*|daily_plot.py --daemon --sleep 2|" ~/BirdNET-Pi/templates/chart_viewer.service
  systemctl daemon-reload && restart_services.sh
fi

if grep -q 'birdnet_server.service' "$HOME/BirdNET-Pi/templates/birdnet_analysis.service"&>/dev/null; then
    sed -i '/After=.*/d' "$HOME/BirdNET-Pi/templates/birdnet_analysis.service"
    sed -i '/Requires=.*/d' "$HOME/BirdNET-Pi/templates/birdnet_analysis.service"
    sed -i '/RuntimeMaxSec=.*/d' "$HOME/BirdNET-Pi/templates/birdnet_analysis.service"
    sed -i "s|ExecStart=.*|ExecStart=$HOME/BirdNET-Pi/birdnet/bin/python3 /usr/local/bin/birdnet_analysis.py|" "$HOME/BirdNET-Pi/templates/birdnet_analysis.service"
    systemctl daemon-reload && restart_services.sh
fi

TMP_MOUNT=$(systemd-escape -p --suffix=mount "$RECS_DIR/StreamData")
if ! [ -f "$HOME/BirdNET-Pi/templates/$TMP_MOUNT" ]; then
   install_birdnet_mount
   chown $USER:$USER "$HOME/BirdNET-Pi/templates/$TMP_MOUNT"
fi

if grep -q -e '-P log' $HOME/BirdNET-Pi/templates/birdnet_log.service ;then
  sed -i "s/-P log/--path log/" ~/BirdNET-Pi/templates/birdnet_log.service
  systemctl daemon-reload && restart_services.sh
fi

if grep -q -e '-P terminal' $HOME/BirdNET-Pi/templates/web_terminal.service ;then
  sed -i "s/-P terminal/--path terminal/" ~/BirdNET-Pi/templates/web_terminal.service
  systemctl daemon-reload && restart_services.sh
fi

if grep -q 'php7.4-' /etc/caddy/Caddyfile &>/dev/null; then
  sed -i 's/php7.4-/php-/' /etc/caddy/Caddyfile
fi

if ! [ -L /etc/avahi/services/http.service ];then
  # symbolic link does not work here, so just copy
  cp -f $HOME/BirdNET-Pi/templates/http.service /etc/avahi/services/
  systemctl restart avahi-daemon.service
fi

if [ -L /usr/local/bin/analyze.py ];then
  rm -f /usr/local/bin/analyze.py
fi

if [ -L /usr/local/bin/birdnet_analysis.sh ];then
  rm -f /usr/local/bin/birdnet_analysis.sh
fi

# Clean state and update cron if all scripts are not installed
if [ "$(grep -o "#birdnet" /etc/crontab | wc -l)" -lt 5 ]; then
  sudo sed -i '/birdnet/,+1d' /etc/crontab
  sed "s/\$USER/$USER/g" "$HOME"/BirdNET-Pi/templates/cleanup.cron >> /etc/crontab
  sed "s/\$USER/$USER/g" "$HOME"/BirdNET-Pi/templates/weekly_report.cron >> /etc/crontab
fi

set +x
AUTH=$(grep basicauth /etc/caddy/Caddyfile)
[ -n "${CADDY_PWD}" ] && [ -z "${AUTH}" ] && sudo /usr/local/bin/update_caddyfile.sh > /dev/null 2>&1
set -x

# update snippets above

systemctl daemon-reload
restart_services.sh
