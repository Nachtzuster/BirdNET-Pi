#!/usr/bin/env bash
# Backup and restore BirdNET data

my_dir=$HOME/BirdNET-Pi/scripts
source /etc/birdnet/birdnet.conf

if [ "$EUID" == 0 ]
  then echo "Please run as a non-root user."
  exit
fi

usage() { echo "Usage: $0 -a backup|restore -f <backup_file>" 1>&2; exit 1; }

unset -v ACTION
unset -v ARCHIVE
unset -v QUIET
while getopts "a:f:" o; do
  case "${o}" in
    a)
      ACTION=${OPTARG}
      [ $ACTION == "backup" ] || [ $ACTION == "restore" ] || usage
      ;;
    f)
      ARCHIVE=${OPTARG}
      ;;
    *)
      usage
      ;;
  esac
done

[ -z "$ACTION" ] && usage && exit 1
[ -z "$ARCHIVE" ] && usage && exit 1
[ "$ARCHIVE" == '-' ] && QUIET=1

PHP_SERVICE=$(systemctl list-unit-files -t service --output json --no-pager php*-fpm.service | jq --raw-output '.[0].unit_file')
[ -z "$PHP_SERVICE" ] || [ "$PHP_SERVICE" == 'null' ] && echo "Could not determine the php service name, this is most likely a bug." && exit 1

log() {
  [ -z "$QUIET" ] && echo "$1"
}

backup_check() {
  [ "$ARCHIVE" != '-' ] && [ -f "$ARCHIVE" ] && echo "$ARCHIVE already exists" && exit 1
}

backup() {
  log "Starting backup"
  CMD='tar --create -f "$ARCHIVE"'
  for obj in  "${objects[@]}";do
    CMD="$CMD -C $(dirname "$obj") $(basename "$obj")"
  done
  eval "$CMD"
  log "Backup done"
}

restore_check() {
  [ ! -f "$ARCHIVE" ] && echo "$ARCHIVE" not found && exit 1
  arch_list=$(tar --list --exclude="*/*" -f "$ARCHIVE" | sed 's/\///')
  for obj in  "${objects[@]}";do
    part2=$(basename "$obj")
    ! (echo $arch_list | grep -F -q "$part2") && echo corrupted backup file && exit 1
  done
}

restore() {
  log "Starting restore"
  for obj in  "${objects[@]}";do
    tar --extract - p -f "$ARCHIVE" -C "$(dirname "$obj")" "$(basename "$obj")"
  done
  sed -i "s/BIRDNET_USER=.*/BIRDNET_USER=$BIRDNET_USER/" "/home/$BIRDNET_USER/BirdNET-Pi/birdnet.conf"
  log "Restore done"
}

objects=("/home/$BIRDNET_USER/BirdSongs/Extracted/By_Date"
"/home/$BIRDNET_USER/BirdSongs/Extracted/Charts"
"/home/$BIRDNET_USER/BirdNET-Pi/BirdDB.txt"
"/home/$BIRDNET_USER/BirdNET-Pi/scripts/birds.db"
"/home/$BIRDNET_USER/BirdNET-Pi/birdnet.conf")

[ $ACTION == "backup" ] && backup_check
[ $ACTION == "restore" ] && restore_check

log "Stopping services"
"$my_dir/stop_core_services.sh"
sudo systemctl stop "$PHP_SERVICE"

[ $ACTION == "backup" ] && backup
[ $ACTION == "restore" ] && restore

log "Restarting services"
sudo systemctl restart "$PHP_SERVICE"
sudo systemctl restart caddy.service
"$my_dir/restart_services.sh" &>/dev/null
