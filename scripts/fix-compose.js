const TOKEN = "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";
const OWNER = "MikeyRock";
const REPO = "projectx-bch-solo";
const BRANCH = "main";
const FILE_PATH = "projectx-bch-solo/docker-compose.yml";
const KNOWN_SHA = "373b127badd254ee85c35741247ffff14adaf4a6";

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

async function main() {
  // Step 1: get current SHA fresh from API
  console.log("[v0] Fetching current SHA...");
  const getRes = await fetch(
    `https://api.github.com/repos/${OWNER}/${REPO}/contents/${FILE_PATH}?ref=${BRANCH}`,
    {
      headers: {
        Authorization: `token ${TOKEN}`,
        Accept: "application/vnd.github.v3+json",
      },
    }
  );
  const fileData = await getRes.json();
  if (!getRes.ok) {
    console.error("[v0] Failed to get SHA:", fileData.message);
    process.exit(1);
  }
  const sha = fileData.sha;
  console.log("[v0] Got SHA:", sha);
  console.log("[v0] File size:", fileData.size, "bytes");

  // Step 2: update the file
  console.log("[v0] Pushing new content...");
  const encoded = Buffer.from(NEW_CONTENT, "utf8").toString("base64");
  const putRes = await fetch(
    `https://api.github.com/repos/${OWNER}/${REPO}/contents/${FILE_PATH}`,
    {
      method: "PUT",
      headers: {
        Authorization: `token ${TOKEN}`,
        Accept: "application/vnd.github.v3+json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message: "fix: full docker-compose rewrite for Umbrel",
        content: encoded,
        sha: sha,
        branch: BRANCH,
      }),
    }
  );
  const putData = await putRes.json();
  if (putRes.ok) {
    console.log("[v0] SUCCESS status:", putRes.status);
    console.log("[v0] New file SHA:", putData.content.sha);
    console.log("[v0] Commit URL:", putData.commit.html_url);
  } else {
    console.error("[v0] FAILED status:", putRes.status);
    console.error("[v0] Error:", putData.message);
  }
}

main().catch(console.error);
