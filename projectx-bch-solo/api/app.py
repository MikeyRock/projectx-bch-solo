"""
Project X — BCH Solo  |  API service
Flask app listening on :3000 (internal).
nginx proxies /api/* → http://api:3000/api/*
"""

import hashlib
import hmac
import json
import logging
import os
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────

SETTINGS_FILE = os.getenv("SETTINGS_FILE", "/data/projectx-settings.json")
LOG_FILE = os.getenv("LOG_FILE", "/data/ckpool.log")
BCH_RPC_HOST = os.getenv("BCH_RPC_HOST", "bchnd")
BCH_RPC_PORT = int(os.getenv("BCH_RPC_PORT", "8332"))

START_TIME = time.time()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [api] %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Default settings
# ──────────────────────────────────────────────────────────────────────────────

DEFAULT_SETTINGS = {
    "ui": {"pool_name": "Project X", "worker_hint": "user.worker"},
    "mining": {
        "payout_address": "bitcoincash:PUT_YOUR_PAYOUT_ADDRESS_HERE",
        "stratum_port": 3333,
    },
    "rpc": {"user": "bchrpc", "pass": "CHANGE_ME_RPC_PASSWORD"},
    "notifications": {
        "enabled": False,
        "secret": "CHANGE_ME_LONG_RANDOM_SECRET",
        "targets": [{"name": "Webhook", "url": "https://example.com/webhook"}],
    },
}

# Keys that require a service restart when changed
RESTART_REQUIRED_KEYS = {
    ("mining", "payout_address"),
    ("mining", "stratum_port"),
    ("rpc", "user"),
    ("rpc", "pass"),
}

# ──────────────────────────────────────────────────────────────────────────────
# Settings helpers
# ──────────────────────────────────────────────────────────────────────────────


def load_settings() -> dict:
    if not os.path.exists(SETTINGS_FILE):
        return json.loads(json.dumps(DEFAULT_SETTINGS))
    try:
        with open(SETTINGS_FILE, "r") as f:
            data = json.load(f)
        # Merge with defaults so new keys appear automatically
        merged = json.loads(json.dumps(DEFAULT_SETTINGS))
        for group, vals in data.items():
            if isinstance(vals, dict):
                merged.setdefault(group, {}).update(vals)
            else:
                merged[group] = vals
        return merged
    except Exception as e:
        log.error("Failed to load settings: %s", e)
        return json.loads(json.dumps(DEFAULT_SETTINGS))


def save_settings(data: dict) -> None:
    os.makedirs(os.path.dirname(SETTINGS_FILE) or ".", exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def mask_settings(settings: dict) -> dict:
    """Return a copy with secrets redacted."""
    s = json.loads(json.dumps(settings))
    if "rpc" in s and "pass" in s["rpc"]:
        s["rpc"]["pass"] = "••••••••"
    if "notifications" in s and "secret" in s["notifications"]:
        s["notifications"]["secret"] = "••••••••"
    return s


def detect_restart_required(old: dict, new: dict) -> bool:
    for group, key in RESTART_REQUIRED_KEYS:
        old_val = old.get(group, {}).get(key)
        new_val = new.get(group, {}).get(key)
        if old_val != new_val:
            return True
    return False


# ──────────────────────────────────────────────────────────────────────────────
# BCH Node RPC
# ──────────────────────────────────────────────────────────────────────────────


def rpc_call(method: str, params: list = None):
    settings = load_settings()
    user = settings["rpc"]["user"]
    password = settings["rpc"]["pass"]
    payload = json.dumps({"method": method, "params": params or [], "id": 1}).encode()
    req = Request(
        f"http://{BCH_RPC_HOST}:{BCH_RPC_PORT}/",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Basic "
            + __import__("base64")
            .b64encode(f"{user}:{password}".encode())
            .decode(),
        },
    )
    with urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def get_node_info() -> dict:
    try:
        result = rpc_call("getblockchaininfo")
        info = result.get("result", {})
        net_result = rpc_call("getnetworkinfo")
        net_info = net_result.get("result", {})
        return {
            "online": True,
            "chain": info.get("chain", "unknown"),
            "blocks": info.get("blocks", 0),
            "headers": info.get("headers", 0),
            "verification_progress": round(
                info.get("verificationprogress", 0) * 100, 4
            ),
            "initial_block_download": info.get("initialblockdownload", False),
            "subversion": net_info.get("subversion", ""),
            "version": net_info.get("version", 0),
        }
    except Exception as e:
        log.warning("RPC error: %s", e)
        return {"online": False, "error": str(e)}


# ──────────────────────────────────────────────────────────────────────────────
# ckpool log parsing
# ──────────────────────────────────────────────────────────────────────────────

# Matches: 2025-01-15T12:34:56Z <rest of line>
TS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\s+(.*)")
# Share accepted:  workername diff ...
SHARE_RE = re.compile(
    r"(Share|Accepted|Rejected|share|accepted|rejected)", re.IGNORECASE
)
WORKER_RE = re.compile(r"Worker\s+(\S+)", re.IGNORECASE)
DIFF_RE = re.compile(r"diff(?:iculty)?\s+([\d.]+)", re.IGNORECASE)
SHARES_RE = re.compile(r"(\d+)\s+shares?", re.IGNORECASE)

WINDOW_MINUTES = 10


def parse_log_window() -> dict:
    """Read the last WINDOW_MINUTES of ckpool log and compute metrics."""
    metrics = {
        "workers_online": 0,
        "shares_per_min": 0.0,
        "best_share_diff": 0.0,
        "accepted": 0,
        "rejected": 0,
        "window_minutes": WINDOW_MINUTES,
    }
    if not os.path.exists(LOG_FILE):
        return metrics

    cutoff_dt = datetime.now(timezone.utc).timestamp() - WINDOW_MINUTES * 60
    workers_seen: set = set()
    accepted_count = 0
    rejected_count = 0
    best_diff = 0.0

    try:
        with open(LOG_FILE, "r", errors="replace") as f:
            # Seek to approximately last 2 MB to avoid huge files
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 2_000_000))
            lines = f.readlines()

        for line in lines:
            m = TS_RE.match(line.strip())
            if not m:
                continue
            ts_str, rest = m.group(1), m.group(2)
            try:
                ts = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%SZ").replace(
                    tzinfo=timezone.utc
                )
                ts_epoch = ts.timestamp()
            except ValueError:
                continue

            if ts_epoch < cutoff_dt:
                continue

            lower = rest.lower()

            # Worker tracking
            wm = WORKER_RE.search(rest)
            if wm:
                workers_seen.add(wm.group(1))

            # Accepted/rejected
            if "accepted" in lower:
                accepted_count += 1
                dm = DIFF_RE.search(rest)
                if dm:
                    d = float(dm.group(1))
                    if d > best_diff:
                        best_diff = d
            elif "rejected" in lower:
                rejected_count += 1

        elapsed_minutes = WINDOW_MINUTES
        total_shares = accepted_count + rejected_count
        metrics["workers_online"] = len(workers_seen)
        metrics["shares_per_min"] = (
            round(total_shares / elapsed_minutes, 2) if elapsed_minutes > 0 else 0.0
        )
        metrics["best_share_diff"] = best_diff
        metrics["accepted"] = accepted_count
        metrics["rejected"] = rejected_count

    except Exception as e:
        log.error("Log parse error: %s", e)

    return metrics


# ──────────────────────────────────────────────────────────────────────────────
# Webhook helpers
# ──────────────────────────────────────────────────────────────────────────────

BLOCK_PATTERNS = re.compile(
    r"block found|found block|solved block|submitblock|submit block",
    re.IGNORECASE,
)
HASH_RE = re.compile(r"\b([0-9a-f]{64})\b", re.IGNORECASE)

_last_block_fingerprint: str = ""
_log_offset: int = 0
_log_offset_lock = threading.Lock()


def _sign_payload(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def send_webhook(target: dict, payload: dict, secret: str) -> dict:
    body = json.dumps(payload).encode()
    sig = _sign_payload(secret, body)
    headers = {
        "Content-Type": "application/json",
        "X-ProjectX-Signature": sig,
        "X-ProjectX-Event": payload["event"],
        "X-ProjectX-Event-Id": payload["event_id"],
    }
    try:
        resp = requests.post(target["url"], data=body, headers=headers, timeout=10)
        return {"name": target["name"], "url": target["url"], "status": resp.status_code, "ok": resp.ok}
    except Exception as e:
        return {"name": target["name"], "url": target["url"], "status": 0, "ok": False, "error": str(e)}


def _block_watcher():
    global _last_block_fingerprint, _log_offset
    log.info("Block watcher thread started.")
    while True:
        try:
            settings = load_settings()
            notif = settings.get("notifications", {})
            if not notif.get("enabled", False):
                time.sleep(5)
                continue

            if not os.path.exists(LOG_FILE):
                time.sleep(5)
                continue

            with _log_offset_lock:
                offset = _log_offset

            with open(LOG_FILE, "r", errors="replace") as f:
                f.seek(0, 2)
                new_size = f.tell()

            if new_size < offset:
                with _log_offset_lock:
                    _log_offset = 0
                offset = 0

            if new_size == offset:
                time.sleep(2)
                continue

            with open(LOG_FILE, "r", errors="replace") as f:
                f.seek(offset)
                new_lines = f.readlines()
                with _log_offset_lock:
                    _log_offset = f.tell()

            for line in new_lines:
                if not BLOCK_PATTERNS.search(line):
                    continue
                fingerprint = hashlib.sha256(line.encode()).hexdigest()[:16]
                if fingerprint == _last_block_fingerprint:
                    continue
                _last_block_fingerprint = fingerprint

                hm = HASH_RE.search(line)
                block_hash = hm.group(1) if hm else None

                payload = {
                    "event": "block.found",
                    "event_id": str(uuid.uuid4()),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "message": line.strip(),
                    "block_hash": block_hash,
                    "pool": settings.get("ui", {}).get("pool_name", "Project X"),
                    "chain": "bch-mainnet",
                }

                secret = notif.get("secret", "")
                for target in notif.get("targets", []):
                    result = send_webhook(target, payload, secret)
                    log.info("Webhook sent to %s: %s", target["name"], result)

        except Exception as e:
            log.error("Block watcher error: %s", e)

        time.sleep(2)


# Start background thread
_watcher_thread = threading.Thread(target=_block_watcher, daemon=True)
_watcher_thread.start()

# ──────────────────────────────────────────────────────────────────────────────
# Flask app
# ──────────────────────────────────────────────────────────────────────────────

app = Flask(__name__)
CORS(app)


@app.route("/api/health")
def health():
    return jsonify({"ok": True})


@app.route("/api/status")
def status():
    settings = load_settings()
    uptime_seconds = int(time.time() - START_TIME)
    h, rem = divmod(uptime_seconds, 3600)
    m, s = divmod(rem, 60)
    uptime_str = f"{h:02d}:{m:02d}:{s:02d}"

    return jsonify(
        {
            "ui": settings.get("ui", {}),
            "mining": {
                "payout_address": settings.get("mining", {}).get("payout_address", ""),
                "stratum_port": settings.get("mining", {}).get("stratum_port", 3333),
            },
            "ckpool": parse_log_window(),
            "node": get_node_info(),
            "uptime": uptime_str,
            "uptime_seconds": uptime_seconds,
        }
    )


@app.route("/api/settings", methods=["GET"])
def get_settings():
    settings = load_settings()
    return jsonify(mask_settings(settings))


@app.route("/api/settings", methods=["PUT"])
def put_settings():
    body = request.get_json(force=True, silent=True)
    if not isinstance(body, dict):
        return jsonify({"ok": False, "error": "Invalid JSON body"}), 400

    old_settings = load_settings()

    # Merge only known groups
    new_settings = json.loads(json.dumps(old_settings))
    for group in ("ui", "mining", "rpc", "notifications"):
        if group in body and isinstance(body[group], dict):
            new_settings[group].update(body[group])

    # Preserve real secrets if placeholder sent back
    if body.get("rpc", {}).get("pass") == "••••••••":
        new_settings["rpc"]["pass"] = old_settings["rpc"]["pass"]
    if body.get("notifications", {}).get("secret") == "••••••••":
        new_settings["notifications"]["secret"] = old_settings["notifications"]["secret"]

    # Basic validation
    addr = new_settings["mining"].get("payout_address", "")
    if not addr or "PUT_YOUR_PAYOUT" in addr:
        pass  # allow saving placeholder; UI will warn

    port = new_settings["mining"].get("stratum_port", 3333)
    try:
        port = int(port)
        if not (1 <= port <= 65535):
            raise ValueError
        new_settings["mining"]["stratum_port"] = port
    except (ValueError, TypeError):
        return jsonify({"ok": False, "error": "stratum_port must be 1–65535"}), 400

    restart_required = detect_restart_required(old_settings, new_settings)
    save_settings(new_settings)

    return jsonify({"ok": True, "restart_required": restart_required})


@app.route("/api/webhooks/test", methods=["POST"])
def test_webhook():
    settings = load_settings()
    notif = settings.get("notifications", {})
    secret = notif.get("secret", "")
    targets = notif.get("targets", [])

    payload = {
        "event": "block.found",
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "[TEST] This is a test webhook from Project X BCH Solo.",
        "block_hash": None,
        "pool": settings.get("ui", {}).get("pool_name", "Project X"),
        "chain": "bch-mainnet",
    }

    results = []
    for target in targets:
        result = send_webhook(target, payload, secret)
        results.append(result)

    return jsonify({"ok": True, "results": results})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=False)
