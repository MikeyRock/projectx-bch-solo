#!/bin/sh
# init.sh — ckpool container entrypoint
# Reads /data/projectx-settings.json, writes /data/ckpool.conf,
# then launches ckpool with timestamped logging to /data/ckpool.log
set -e

SETTINGS="/data/projectx-settings.json"
CONF="/data/ckpool.conf"
LOG="/data/ckpool.log"

# ── Defaults ────────────────────────────────────────────────────────────────
DEFAULT_PAYOUT="bitcoincash:PUT_YOUR_PAYOUT_ADDRESS_HERE"
DEFAULT_PORT=3333
DEFAULT_RPC_USER="bchrpc"
DEFAULT_RPC_PASS="CHANGE_ME_RPC_PASSWORD"

# ── Bootstrap default settings if not present ───────────────────────────────
if [ ! -f "$SETTINGS" ]; then
  mkdir -p /data
  cat > "$SETTINGS" <<'EOF'
{
  "ui": { "pool_name": "Project X", "worker_hint": "user.worker" },
  "mining": { "payout_address": "bitcoincash:PUT_YOUR_PAYOUT_ADDRESS_HERE", "stratum_port": 3333 },
  "rpc": { "user": "bchrpc", "pass": "CHANGE_ME_RPC_PASSWORD" },
  "notifications": {
    "enabled": false,
    "secret": "CHANGE_ME_LONG_RANDOM_SECRET",
    "targets": [
      { "name": "Webhook", "url": "https://example.com/webhook" }
    ]
  }
}
EOF
fi

# ── Parse settings with python3 (available in ckpool image) -----------------
PAYOUT=$(python3 -c "
import json, sys
try:
    d = json.load(open('$SETTINGS'))
    print(d['mining']['payout_address'])
except Exception:
    print('$DEFAULT_PAYOUT')
" 2>/dev/null || echo "$DEFAULT_PAYOUT")

STRATUM_PORT=$(python3 -c "
import json
try:
    d = json.load(open('$SETTINGS'))
    print(d['mining']['stratum_port'])
except Exception:
    print('$DEFAULT_PORT')
" 2>/dev/null || echo "$DEFAULT_PORT")

RPC_USER=$(python3 -c "
import json
try:
    d = json.load(open('$SETTINGS'))
    print(d['rpc']['user'])
except Exception:
    print('$DEFAULT_RPC_USER')
" 2>/dev/null || echo "$DEFAULT_RPC_USER")

RPC_PASS=$(python3 -c "
import json
try:
    d = json.load(open('$SETTINGS'))
    print(d['rpc']['pass'])
except Exception:
    print('$DEFAULT_RPC_PASS')
" 2>/dev/null || echo "$DEFAULT_RPC_PASS")

echo "[init] Payout address : $PAYOUT"
echo "[init] Stratum port   : $STRATUM_PORT"
echo "[init] RPC user       : $RPC_USER"

# ── Wait for BCH node RPC to become available ────────────────────────────────
echo "[init] Waiting for bitcoind RPC at bchnd:8332 ..."
RETRIES=60
while [ $RETRIES -gt 0 ]; do
  if python3 -c "
import urllib.request, base64, json, sys
creds = base64.b64encode(b'${RPC_USER}:${RPC_PASS}').decode()
req = urllib.request.Request(
  'http://bchnd:8332/',
  data=json.dumps({'method':'getblockchaininfo','params':[],'id':1}).encode(),
  headers={'Authorization': 'Basic ' + creds, 'Content-Type': 'application/json'}
)
try:
    urllib.request.urlopen(req, timeout=3)
    sys.exit(0)
except:
    sys.exit(1)
" 2>/dev/null; then
    echo "[init] bitcoind RPC is ready."
    break
  fi
  RETRIES=$((RETRIES - 1))
  sleep 5
done

if [ $RETRIES -eq 0 ]; then
  echo "[init] WARNING: bitcoind RPC not reachable after 5 minutes — starting ckpool anyway."
fi

# ── Write ckpool config ───────────────────────────────────────────────────────
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
  "btcsig": "Project X BCH Solo",
  "serverurl": ["0.0.0.0:$STRATUM_PORT"],
  "mindiff": 1,
  "startdiff": 1024,
  "logdir": "/data"
}
EOF

echo "[init] ckpool config written to $CONF"

# ── Launch ckpool with timestamped log output ─────────────────────────────────
# ckpool is launched with -L (log to stdout) and output is piped through
# a small awk that prepends a UTC ISO-8601 timestamp to every line,
# writing simultaneously to stdout and the persistent log file.

echo "[init] Starting ckpool ..."
exec ckpool -L -c "$CONF" 2>&1 | awk '
{
  cmd = "date -u +\"%Y-%m-%dT%H:%M:%SZ\""
  cmd | getline ts
  close(cmd)
  line = ts " " $0
  print line
  print line >> "'"$LOG"'"
  fflush()
}
'
