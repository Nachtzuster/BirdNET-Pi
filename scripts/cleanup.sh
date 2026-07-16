#!/usr/bin/env bash
source /etc/birdnet/birdnet.conf

cd "${PROCESSED}" || exit 1
empties=($(find ${PROCESSED} -size 57c))
for i in "${empties[@]}";do
  rm -f "${i}"
  rm -f "${i/.csv/}"
done

if [[ "$(find ${PROCESSED} | wc -l)" -ge 100 ]];then
  ls -1t . | tail -n +100 | xargs -r rm -vv
fi

#accumulated_files=$(find $RECS_DIR -path $PROCESSED -prune -o -path $EXTRACTED -prune -o -type f -print | wc -l)
#[ $accumulated_files -ge 10 ] && stop_core_services.sh
#echo "$(date "+%b  %e %I:%M:%S") Stopped Core Services -- It looks like analysis stopped. Check raw recordings in $RECS_DIR and check the birdnet_analysis.service and birdnet_server.service \"journalctl -eu birdnet_analysis -u birdnet_server\"" | sudo tee -a /var/log/syslog
