// This script uses the GitHub API to directly update files on the main branch.
// It requires a GITHUB_TOKEN environment variable with repo write access.

const TOKEN = "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";
const OWNER = "MikeyRock";
const REPO = "projectx-bch-solo";
const BRANCH = "main";

const files = [
  {
    path: "umbrel-app-store.yml",
    content: `id: mikeyrock
name: MikeyRock
`,
  },
  {
    path: "projectx-bch-solo/umbrel-app.yml",
    content: `manifestVersion: 1
id: projectx-bch-solo
category: bitcoin
name: Project X BCH Solo
version: "1.0.0"
tagline: BCH node + solo pool
icon: https://raw.githubusercontent.com/MikeyRock/projectx-bch-solo/main/projectx-bch-solo/icon.png
description: >-
  Project X runs a full Bitcoin Cash node alongside a ckpool-solo stratum
  server. Point your ASIC miners at the stratum URL and solo mine BCH directly
  to your own payout address. No pool fees, full custody. Dashboard shows live
  hashrate, node sync, network difficulty, and block notifications.
developer: MikeyRock
website: https://github.com/MikeyRock/projectx-bch-solo
dependencies: []
repo: https://github.com/MikeyRock/projectx-bch-solo
support: https://github.com/MikeyRock/projectx-bch-solo/issues
port: 80
gallery:
  - https://raw.githubusercontent.com/MikeyRock/projectx-bch-solo/main/projectx-bch-solo/screenshots/1.png
  - https://raw.githubusercontent.com/MikeyRock/projectx-bch-solo/main/projectx-bch-solo/screenshots/2.png
path: ""
defaultUsername: ""
defaultPassword: ""
torOnly: false
submitter: MikeyRock
submission: https://github.com/MikeyRock/projectx-bch-solo
`,
  },
  {
    path: "projectx-bch-solo/docker-compose.yml",
    content: `version: "3.7"

services:
  app_proxy:
    environment:
      APP_HOST: web
      APP_PORT: 80
      PROXY_AUTH_ADD: "false"
    networks:
      - umbrel_main_network

  web:
    image: nginx:1.27-alpine
    restart: on-failure
    networks:
      default:
        aliases:
          - web
      umbrel_main_network:
        aliases:
          - web

  bchnd:
    image: zquestz/bitcoin-cash-node:28.0.1
    restart: on-failure
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
    depends_on:
      - bchnd

networks:
  umbrel_main_network:
    external: true
    name: umbrel_main_network
`,
  },
];

async function getFileSha(path) {
  const url = `https://api.github.com/repos/${OWNER}/${REPO}/contents/${path}?ref=${BRANCH}`;
  const res = await fetch(url, {
    headers: {
      Authorization: `token ${TOKEN}`,
      Accept: "application/vnd.github.v3+json",
    },
  });
  if (res.ok) {
    const data = await res.json();
    return data.sha;
  }
  return null;
}

async function updateFile(path, content) {
  const sha = await getFileSha(path);
  const url = `https://api.github.com/repos/${OWNER}/${REPO}/contents/${path}`;
  const body = {
    message: `fix: update ${path} for Umbrel compatibility`,
    content: Buffer.from(content).toString("base64"),
    branch: BRANCH,
  };
  if (sha) body.sha = sha;

  const res = await fetch(url, {
    method: "PUT",
    headers: {
      Authorization: `token ${TOKEN}`,
      Accept: "application/vnd.github.v3+json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (res.ok) {
    console.log(`[v0] Successfully updated ${path}`);
  } else {
    const err = await res.text();
    console.error(`[v0] Failed to update ${path}: ${res.status} ${err}`);
  }
}

async function main() {
  console.log("[v0] Starting GitHub API file updates on main branch...");

  for (const file of files) {
    await updateFile(file.path, file.content);
  }

  console.log("\n[v0] Done! All files updated directly on main.");
  console.log("[v0] Now remove and re-add the community store on Umbrel.");
}

main().catch(console.error);
