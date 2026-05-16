#!/usr/bin/env bash
source /etc/birdnet/birdnet.conf
my_dir=$HOME/BirdNET-Pi/scripts
set -x
[ -d /etc/caddy ] || mkdir /etc/caddy
if [ -f /etc/caddy/Caddyfile ];then
  cp /etc/caddy/Caddyfile{,.original}
fi
if ! [ -z ${CADDY_PWD} ];then
HASHWORD=$(caddy hash-password --plaintext ${CADDY_PWD})
cat << EOF > /etc/caddy/Caddyfile
http:// ${BIRDNETPI_URL} {
  @blocked_legacy_probe_paths {
    path_regexp legacyProbe (?i)(^|/)[^/]+\.(php[0-9]?|phtml|phar|phps|phtm?)(/|$)|^/(\.git|\.env)(/|\.|$)
  }
  respond @blocked_legacy_probe_paths 404

  reverse_proxy localhost:8080
  basicauth /api/config* {
    birdnet ${HASHWORD}
  }
  @protected_system {
    path /api/system*
    not path /api/system/public-status*
  }
  basicauth @protected_system {
    birdnet ${HASHWORD}
  }
  basicauth /settings* {
    birdnet ${HASHWORD}
  }
  encode gzip
}
EOF
else
  cat << EOF > /etc/caddy/Caddyfile
http:// ${BIRDNETPI_URL} {
  @blocked_legacy_probe_paths {
    path_regexp legacyProbe (?i)(^|/)[^/]+\.(php[0-9]?|phtml|phar|phps|phtm?)(/|$)|^/(\.git|\.env)(/|\.|$)
  }
  respond @blocked_legacy_probe_paths 404

  reverse_proxy localhost:8080
  encode gzip
}
EOF
fi

sudo caddy fmt --overwrite /etc/caddy/Caddyfile
sudo systemctl reload caddy
