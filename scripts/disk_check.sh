#!/usr/bin/env bash
set -x

source /etc/birdnet/birdnet.conf
used="$(df -h ${EXTRACTED} | tail -n1 | awk '{print $5}')"
purge_threshold="${PURGE_THRESHOLD:-95}"
python_bin="${HOME}/BirdNET-Pi/birdnet/bin/python3"
[ -x "${python_bin}" ] || python_bin="$(command -v python3 || true)"

if [ "${used//%}" -ge "$purge_threshold" ]; then

  case $FULL_DISK in
    purge) echo "Removing oldest data"
        cd ${EXTRACTED}/By_Date/
        if [ -n "${python_bin}" ] && [ -f /usr/local/bin/refresh_disk_check_exclude.py ]; then
            "${python_bin}" /usr/local/bin/refresh_disk_check_exclude.py >/dev/null 2>&1 || true
        fi
        if ! grep -qxFe \#\#start $HOME/BirdNET-Pi/scripts/disk_check_exclude.txt; then
            exit
        fi
        filestodelete=$(($(find ${EXTRACTED}/By_Date/* -type f | wc -l) / $(find ${EXTRACTED}/By_Date/* -maxdepth 0 -type d | wc -l)))
        iter=0
        for i in */*/*; do
            if [ $iter -ge $filestodelete ]; then
                break
            fi
            if ! grep -qxFe "$i" $HOME/BirdNET-Pi/scripts/disk_check_exclude.txt; then
                rm "$i"
            fi
            ((iter++))
        done
        find ~/BirdSongs/ -type d -empty -mtime +90 -delete
        find ${EXTRACTED}/By_Date/ -empty -type d -delete;;

       #rm -drfv "$(find ${EXTRACTED}/By_Date/* -maxdepth 1 -type d -prune \
        # | sort -r | tail -n1)";;
    keep) echo "Stopping Core Services"
       /usr/local/bin/stop_core_services.sh;;
  esac
fi
sleep 1
if [ "${used//%}" -ge "$purge_threshold" ]; then
  case $FULL_DISK in
    purge) echo "Removing more data"
       rm -rfv ${PROCESSED}/*;;
    keep) echo "Stopping Core Services"
       /usr/local/bin/stop_core_services.sh;;
  esac
fi
