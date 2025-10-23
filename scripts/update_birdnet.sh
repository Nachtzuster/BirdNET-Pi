#!/usr/bin/env bash
# Update BirdNET-Pi's Git Repo
source /etc/birdnet/birdnet.conf
trap 'exit 1' SIGINT SIGHUP

usage() { echo "Usage: $0 [-r <remote name>] [-b <branch name>] [-a]" 1>&2; exit 1; }

if [ -n "${BIRDNET_USER}" ]; then
  USER=${BIRDNET_USER}
  HOME=/home/${BIRDNET_USER}
else
  USER=$(awk -F: '/1000/ {print $1}' /etc/passwd)
  HOME=$(awk -F: '/1000/ {print $6}' /etc/passwd)
fi
my_dir=$HOME/BirdNET-Pi/scripts

# Defaults
remote="origin"
branch="main"
auto_update=""

while getopts ":r:b:a" o; do
  case "${o}" in
    r)
      remote=${OPTARG}
      git -C $HOME/BirdNET-Pi remote show $remote > /dev/null 2>&1
      ret_val=$?

      if [ $ret_val -ne 0 ]; then
        echo "Error: remote '$remote' not found. Add the upstream remote to your repository and try again."
        exit 1
      fi
      ;;
    b)
      branch=${OPTARG}
      ;;
    a)
      auto_update=1
      ;;
    *)
      usage
      ;;
  esac
done
shift $((OPTIND-1))

sudo_with_user () {
  set -x
  sudo -u $USER "$@"
  set +x
}

can_auto_update () {
  if [ -z ${AUTOMATIC_UPDATE} ] || [ "${AUTOMATIC_UPDATE}" == 0 ]; then
    echo "Auto update is not enabled"
    exit 0
  fi
  sudo_with_user git -C $HOME/BirdNET-Pi fetch $remote $branch
  behind_count=$(sudo_with_user git -C $HOME/BirdNET-Pi rev-list --count HEAD..@{u})
  if [ "${behind_count}" -eq 0 ]; then
    echo "No updates"
    exit 0
  fi
}

[ -n "${auto_update}" ] && can_auto_update

# Get current HEAD hash
commit_hash=$(sudo_with_user git -C $HOME/BirdNET-Pi rev-parse HEAD)

# Reset current HEAD to remove any local changes
sudo_with_user git -C $HOME/BirdNET-Pi reset --hard

# Fetches latest changes
sudo_with_user git -C $HOME/BirdNET-Pi fetch $remote $branch

# Switches git to specified branch
sudo_with_user git -C $HOME/BirdNET-Pi switch -C $branch --track $remote/$branch

# Prints out changes
sudo_with_user git --no-pager -C $HOME/BirdNET-Pi diff --stat $commit_hash HEAD

$my_dir/pre_update.sh

sudo systemctl daemon-reload
sudo ln -sf $my_dir/* /usr/local/bin/

# The script below handles changes to the host system
# Any additions to the updater should be placed in that file.
sudo $my_dir/update_birdnet_snippets.sh
