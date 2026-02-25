# Project X — BCH Solo Mining Dashboard

**STABLE build** | BCHN v28.0.1 (EB32.0) | ckpool-solo:590fb2a | Stratum v1 | mainnet

---

## GitHub Repository

This project is connected to **https://github.com/MikeyRock/projectx-bch-solo**.

All code changes made in v0 are automatically pushed to the branch shown in the v0 sidebar (left panel, click the GitHub icon). To deploy to `main`:

1. Click the **GitHub icon** in the v0 sidebar
2. Click **Create a Pull Request**
3. On GitHub, review the changes and click **Merge pull request**

Once merged, all files are live on `main` and ready for Umbrel to read.

---

### Part 6 — Connect to Your Umbrel and Run the App

> Your Umbrel device must be on the same local network.

**Option A — Clone directly onto Umbrel (recommended)**

1. SSH into your Umbrel:
   ```bash
   ssh umbrel@umbrel.local
   # Default password: moneyprintergobrrr
   ```
2. Clone your repo:
   ```bash
   git clone https://github.com/MikeyRock/projectx-bch-solo.git
   cd projectx-bch-solo
   ```
3. **Set your payout address before starting.** Edit the settings file:
   ```bash
   mkdir -p /home/umbrel/umbrel/app-data/projectx/data
   # Then start the app — init.sh will create the default settings file on first boot.
   ```
4. Start the stack:
   ```bash
   docker compose up -d
   ```
5. Open a browser and go to `http://umbrel.local:8080`

**Option B — Run locally on any Linux/Mac machine with Docker**

1. Install Docker Desktop from **https://www.docker.com/products/docker-desktop**
2. Clone or copy the `projectx-bch-solo` folder onto that machine.
3. `cd projectx-bch-solo && docker compose up -d`
4. Open `http://localhost:8080`

---

## How to Connect the BCH Node

Everything below is handled automatically by `init.sh` and the `docker-compose.yml`.  
You only need to do **one thing manually** before the first start:

### Set your payout address

Open the dashboard at `http://<your-umbrel-ip>:8080`, click **Settings**, and enter your BCH address in **Payout Address**.

> Format: `bitcoincash:qxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`  
> (CashAddr format — starts with `bitcoincash:q`)

After saving, **restart the Docker stack** so ckpool picks up the new address:

```bash
docker compose restart ckpool
```

---

## Node Details

| Component | Image / Version |
|-----------|----------------|
| Bitcoin Cash Node | `zquestz/bitcoin-cash-node:28.0.1` |
| Excessive Block Size | 32 MB (EB32.0) |
| Network | mainnet |
| RPC Port | 8332 (internal, not exposed) |
| ckpool-solo | `ghcr.io/getumbrel/docker-ckpool-solo:590fb2a` |
| Stratum protocol | v1 |
| Default stratum port | 3333 |
| Dashboard port | 8080 |

---

## Settings Reference

| Setting | Where | Description |
|---------|-------|-------------|
| Payout Address | Settings → Mining | Your BCH CashAddr. **Requires restart.** |
| Stratum Port | Settings → Mining | Port miners connect to. Default 3333. **Requires restart.** |
| RPC Username | Settings → Node/RPC | Must match bitcoind. Default `bchrpc`. **Requires restart.** |
| RPC Password | Settings → Node/RPC | Strong random string. **Requires restart.** |
| Prune Target (MiB) | Settings → Node/RPC | `0` = full archival, `550+` = pruned mode. Saves disk. **Requires restart.** |
| Pool Name | Settings → UI | Display name shown in the header. |
| Worker Hint | Settings → UI | Example worker string shown on dashboard. |
| Webhooks | Settings → Notifications | HMAC-signed POST on block found. |

---

## Miner Configuration Example

```
Pool URL:  stratum+tcp://192.168.1.100:3333
Worker:    youraddress.rig1
Password:  x
```

Replace `192.168.1.100` with your Umbrel's LAN IP (set it using the **Set LAN IP** button).

---

## Troubleshooting

**Node chip shows Offline:**  
- The BCH node is still syncing — this is normal on first start. Full sync takes 12–24 hours.
- Check: `docker compose logs bchnd --tail 50`

**Stratum chip shows Starting:**  
- ckpool is waiting for bitcoind RPC. Check RPC credentials match in Settings.
- Check: `docker compose logs ckpool --tail 50`

**Miners not connecting:**  
- Make sure port 3333 is not blocked by your router's firewall.
- Confirm the LAN IP is set correctly in the dashboard header.

**Settings not saving:**  
- If the API is offline, settings are saved in your browser's local storage and will sync to the server when the container is running.
