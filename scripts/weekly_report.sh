#!/usr/bin/env bash
set -euo pipefail

source /etc/birdnet/birdnet.conf

if [ "${APPRISE_WEEKLY_REPORT:-0}" = "1" ]; then
	NOTIFICATION="$(curl -fsS http://127.0.0.1:8080/api/detections/weekly-report/notification || true)"
	[ -n "${NOTIFICATION}" ] || exit 0
	NOTIFICATION=${NOTIFICATION#*#}
	firstLine="$(printf '%s\n' "${NOTIFICATION}" | head -1)"
	NOTIFICATION="$(printf '%s\n' "${NOTIFICATION}" | tail -n +2)"
	[ -n "${firstLine}" ] || exit 0
	[ -n "${NOTIFICATION}" ] || exit 0
	"$HOME/BirdNET-Pi/birdnet/bin/apprise" -vv -t "${firstLine}" -b "${NOTIFICATION}" --input-format=html --config="$HOME/BirdNET-Pi/apprise.txt"
fi
