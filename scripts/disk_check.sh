#!/usr/bin/env bash
# set -x  # was unconditional: this runs on a timer/at every restart, and every
# traced line is a journal write (SD-card wear). Uncomment to debug.

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
        datedirs=$(find ${EXTRACTED}/By_Date/* -maxdepth 0 -type d | wc -l)
        # Guard the divisor: with no date dirs this was a division by zero, which
        # left filestodelete empty and made the [ -ge ] test below error instead
        # of ever breaking out of the loop.
        if [ "${datedirs}" -eq 0 ]; then
            echo "No date directories to purge"
            exit 0
        fi
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
        find ${EXTRACTED}/By_Date/ -empty -type d -delete;;

       #rm -drfv "$(find ${EXTRACTED}/By_Date/* -maxdepth 1 -type d -prune \
        # | sort -r | tail -n1)";;
    keep) echo "Stopping Core Services"
       /usr/local/bin/stop_core_services.sh;;
  esac
fi
sleep 1
# Re-measure: the purge above may already have freed enough. Re-using the stale
# reading made this second, more destructive purge (rm -rf $PROCESSED) fire
# unconditionally whenever the first one did.
used="$(disk_used_pct)"
if [ "${used}" -ge "$purge_threshold" ]; then
  case $FULL_DISK in
    purge) echo "Removing more data"
       rm -rfv ${PROCESSED}/*;;
    keep) echo "Stopping Core Services"
       /usr/local/bin/stop_core_services.sh;;
  esac
fi
