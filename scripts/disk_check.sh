#!/usr/bin/env bash

source /etc/birdnet/birdnet.conf

disk_used_pct() {
  local u
  u="$(df -h "${EXTRACTED}" | tail -n1 | awk '{print $5}')"
  echo "${u//%}"
}

used="$(disk_used_pct)"
purge_threshold="${PURGE_THRESHOLD:-95}"

if [ "${used}" -ge "$purge_threshold" ]; then

  case $FULL_DISK in
    purge) echo "Removing oldest data"
        cd ${EXTRACTED}/By_Date/
        curl localhost/views.php?view=Species%20Stats &>/dev/null
        if ! grep -qxFe \#\#start $HOME/BirdNET-Pi/scripts/disk_check_exclude.txt; then
            exit
        fi
        datedirs=$(find ${EXTRACTED}/By_Date/* -maxdepth 0 -type d 2>/dev/null | wc -l)
        if [ "${datedirs}" -gt 0 ]; then
          filestodelete=$(( $(find ${EXTRACTED}/By_Date/* -type f | wc -l) / datedirs ))
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
          find "${RECS_DIR:-$HOME/BirdSongs}/" -type d -empty -mtime +90 -delete
          find ${EXTRACTED}/By_Date/ -empty -type d -delete
        else
          echo "No date directories to purge"
        fi;;

       #rm -drfv "$(find ${EXTRACTED}/By_Date/* -maxdepth 1 -type d -prune \
        # | sort -r | tail -n1)";;
    keep) echo "Stopping Core Services"
       /usr/local/bin/stop_core_services.sh;;
  esac
fi
sleep 1
used="$(disk_used_pct)"
if [ "${used}" -ge "$purge_threshold" ]; then
  case $FULL_DISK in
    purge) echo "Removing more data"
       rm -rfv ${PROCESSED}/*;;
    keep) echo "Stopping Core Services"
       /usr/local/bin/stop_core_services.sh;;
  esac
fi
