import { Buffer } from "buffer";

const TOKEN = "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";
const OWNER = "MikeyRock";
const REPO = "projectx-bch-solo";
const BRANCH = "main";
const FILE_PATH = "projectx-bch-solo/docker-compose.yml";

const NEW_CONTENT = `version: "3.7"

services:

  app_proxy:
    environment:
      APP_HOST: web
      APP_PORT: 80
      PROXY_AUTH_ADD: "false"

  web:
    image: nginx:1.27-alpine
    restart: on-failure
    volumes:
      - \${APP_DATA_DIR}/exports/nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
      - \${APP_DATA_DIR}/exports/app:/usr/share/nginx/html:ro
    depends_on:
      - api

  bchnd:
    image: zquestz/bitcoin-cash-node:28.0.1
    restart: on-failure
    stop_grace_period: 10m
    command: >
      bitcoind
      -datadir=/data
      -rpcuser=bchrpc
      -rpcpassword=changeme
      -rpcallowip=0.0.0.0/0
      -rpcbind=0.0.0.0
      -rpcport=8332
      -server=1
      -txindex=1
      -addnode=seed.flowee.cash
    volumes:
      - \${APP_DATA_DIR}/data/bchnd:/data

  ckpool:
    image: ghcr.io/getumbrel/docker-ckpool-solo:590fb2a
    restart: on-failure
    ports:
      - "3333:3333"
    volumes:
      - \${APP_DATA_DIR}/data/ckpool:/data
      - \${APP_DATA_DIR}/scripts/init.sh:/scripts/init.sh:ro
    entrypoint: ["/bin/sh", "/scripts/init.sh"]
    depends_on:
      - bchnd

  api:
    image: python:3.12-slim
    restart: on-failure
    working_dir: /app
    command: >
      sh -c "pip install --no-cache-dir flask gunicorn requests flask-cors --quiet &&
             exec gunicorn -w 2 -b 0.0.0.0:3000 app:app"
    volumes:
      - \${APP_DATA_DIR}/data/ckpool:/data
      - \${APP_DATA_DIR}/api:/app:ro
    environment:
      - BCH_RPC_HOST=bchnd
      - BCH_RPC_PORT=8332
      - SETTINGS_FILE=/data/projectx-settings.json
      - LOG_FILE=/data/ckpool.log
    depends_on:
      - bchnd
      - ckpool
`;

async function getCurrentSha() {
  const url = `https://api.github.com/repos/${OWNER}/${REPO}/contents/${FILE_PATH}?ref=${BRANCH}`;
  console.log("[v0] Fetching current file SHA from:", url);
  const res = await fetch(url, {
    headers: {
      Authorization: `Bearer ${TOKEN}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
    },
  });
  const data = await res.json();
  console.log("[v0] Response status:", res.status);
  if (!res.ok) {
    console.error("[v0] Error fetching SHA:", JSON.stringify(data));
    process.exit(1);
  }
  console.log("[v0] Current SHA:", data.sha);
  console.log("[v0] Current size:", data.size, "bytes");
  return data.sha;
}

async function updateFile(sha) {
  const url = `https://api.github.com/repos/${OWNER}/${REPO}/contents/${FILE_PATH}`;
  const body = {
    message: "fix: correct docker-compose.yml for Umbrel compatibility",
    content: Buffer.from(NEW_CONTENT).toString("base64"),
    sha: sha,
    branch: BRANCH,
  };

  console.log("[v0] Updating file via GitHub API...");
  const res = await fetch(url, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${TOKEN}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  const data = await res.json();
  console.log("[v0] Update response status:", res.status);
  if (res.ok) {
    console.log("[v0] SUCCESS! File updated.");
    console.log("[v0] New SHA:", data.content?.sha);
    console.log("[v0] Commit:", data.commit?.html_url);
  } else {
    console.error("[v0] FAILED:", JSON.stringify(data));
  }
}

const sha = await getCurrentSha();
await updateFile(sha);
