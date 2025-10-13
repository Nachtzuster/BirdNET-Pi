#!/usr/bin/env bash
set -x

# =============================================================================
# BirdNET-Pi Disk Space Management Script
#
# PURPOSE:
#   This script monitors the disk space used by BirdNET-Pi recordings and
#   automatically purges old files if the used space exceeds a configurable
#   threshold. It is designed to prevent disk full errors and ensure smooth
#   operation of BirdNET-Pi services.
#
# USAGE:
#   - The script is intended to be run automatically (e.g., via cron).
#   - It sources configuration from `/etc/birdnet/birdnet.conf`.
#   - It respects the `FULL_DISK` environment variable to determine whether to
#     purge files or stop services when the disk is full.
#   - Always leaves at least 30 recordings per species.
#   - Deletes files in steps of 5% of MAX_FILES_SPECIES (minimum 5 files per step).
#   - Stops core services if disk remains full after purging.
#
# =============================================================================

source /etc/birdnet/birdnet.conf

# Get the variables
max_files_species="${MAX_FILES_SPECIES:-1000}"
purge_threshold="${PURGE_THRESHOLD:-95}"
# Remove 10% below the threshold to avoid running the script too often, ensure integer
purge_threshold_target=$(($purge_threshold * 9 / 10))
# Deletion step corresponding to 5% of max_files_species, with at least 5 files, ensure integer
safe_purge_step=$(($max_files_species * 5 / 100))
(( safe_purge_step >= 5 )) || safe_purge_step=5
# Always leave at least 30 recordings
safe_files_species="30"
# Ensure integers
purge_threshold="${purge_threshold%%[.,]*}"
purge_threshold_target="${purge_threshold_target%%[.,]*}"
safe_purge_step="${safe_purge_step%%[.,]*}"
# Get the disk space in %
base_dir="$(realpath -e "$HOME/BirdSongs/Extracted/By_Date")"
used_disk() {
  df -P "$base_dir" | awk 'END { gsub(/%/,"",$5); print $5 }'
}

# If the used space is above the threshold
if [ "$(used_disk)" -ge "$purge_threshold" ]; then
  case $FULL_DISK in
    purge) echo "Removing data to stay below threshold of $purge_threshold"
        # Loop until the value is below 10% of the threshold, to avoid running the script too often
        max_files_species_loop="$max_files_species"
        while [ "$(used_disk)" -ge "$purge_threshold_target" ]; do
            max_files_species_loop=$(( max_files_species_loop - safe_purge_step ))
            if [ "$max_files_species_loop" -gt "$safe_files_species" ]; then
              bash "$HOME/BirdNET-Pi/scripts/disk_species_clean.sh" "$max_files_species_loop"
              sleep 5
            else
              echo "ERROR : safeguard initiated at $safe_files_species files remaining to make sure that we do not delete too many files. Is there an issue with the path of $base_dir? Stopping core services."
              /usr/local/bin/stop_core_services.sh
              break
            fi
        done;;

    keep) echo "FULL_DISK=keep → Stopping Core Services."
        /usr/local/bin/stop_core_services.sh;;

    *) echo "Unknown FULL_DISK value: $FULL_DISK"
        exit 1;;
  esac
fi
