#!/bin/sh
# init.sh — ckpool container entrypoint
# Writes /data/ckpool.conf then launches ckpool in solo mode
set -e

CONF="/data/ckpool.conf"

# Defaults — these match the bchnd service in docker-compose
RPC_USER="bchrpc"
RPC_PASS="changeme"
PAYOUT="bitcoincash:qz2m9h840hxlr950dfeygltgxx7gfkaz9574w84d5m"

echo "[init] Writing ckpool config..."

cat > "$CONF" <<EOF
{
  "btcd": [
    {
      "url": "bchnd:8332",
      "auth": "$RPC_USER",
      "pass": "$RPC_PASS",
      "notify": true
    }
  ],
  "btcaddress": "$PAYOUT",
  "btcsig": "/Project X BCH Solo/",
  "serverurl": ["0.0.0.0:3333"],
  "mindiff": 1,
  "startdiff": 512,
  "logdir": "/data"
}
EOF

echo "[init] Config written. Waiting for bitcoind RPC..."

# Wait up to 5 minutes for bitcoind to become reachable
RETRIES=60
while [ $RETRIES -gt 0 ]; do
  if wget -qO- --timeout=3 "http://$RPC_USER:$RPC_PASS@bchnd:8332/" >/dev/null 2>&1; then
    echo "[init] bitcoind RPC is reachable."
    break
  fi
  RETRIES=$((RETRIES - 1))
  sleep 5
done

if [ $RETRIES -eq 0 ]; then
  echo "[init] WARNING: bitcoind RPC not reachable after 5 min — starting ckpool anyway."
fi

echo "[init] Starting ckpool in solo mode..."
exec ckpool --btcsolo --config "$CONF"
