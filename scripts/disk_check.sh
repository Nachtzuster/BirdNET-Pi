#!/usr/bin/env bash
set -x

source /etc/birdnet/birdnet.conf
used="$(df -h ${EXTRACTED} | tail -n1 | awk '{print $5}')"
purge_threshold="${PURGE_THRESHOLD:-95}"

if [ "${used//%}" -ge "$purge_threshold" ]; then

  case $FULL_DISK in
    purge) echo "Removing data to stay below threshold"
        max_files_species="1000"
        safe_files_species="30"
        safe_purge_threshold="$((95 * 9 / 10))"
        while [ "$(df -h "${EXTRACTED}" | tail -n1 | awk '{print $5}' | tr -d '%')" -ge "$safe_purge_threshold" ]; do
            max_files_species=$((max_files_species * 9 / 10))
            if [ "$max_files_species" -lt "$safe_files_species" ]; then
              echo "ERROR : safeguard initiated at $safe_files_species files remaining to make sure that we do not delete too many files. Is there an issue with the path of $EXTRACTED? Stopping core services."
              /usr/local/bin/stop_core_services.sh
              break
            fi
            ./disk_species_clean.sh "$max_files_species"
            sleep 5
        done;;

    keep) echo "Stopping Core Services"
        /usr/local/bin/stop_core_services.sh;;

    *) echo "Unknown FULL_DISK value: $FULL_DISK"
        exit 1;;
  esac
fi
