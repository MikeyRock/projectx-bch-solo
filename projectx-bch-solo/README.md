# Project X — BCH Solo Mining Dashboard

**STABLE build** | BCHN v28.0.1 (EB32.0) | ckpool-solo:590fb2a | Stratum v1 | mainnet

---

## How to Put This on GitHub (step by step)

You do not need any coding experience. Follow every step in order.

---

### Part 1 — Create a GitHub Account (skip if you already have one)

1. Open your browser and go to **https://github.com**
2. Click **Sign up** in the top-right corner.
3. Enter an email address, create a password, and choose a username.
4. Follow the on-screen verification steps and confirm your email.

---

### Part 2 — Create a New Repository

1. After logging in, click the **+** icon in the top-right corner → **New repository**.
2. Fill in the form:
   - **Repository name:** `projectx-bch-solo` (or any name you like)
   - **Description:** `BCH solo mining dashboard for Umbrel`
   - **Visibility:** Choose **Private** (recommended — keeps your config out of public view)
   - Leave everything else at its default.
3. Click **Create repository**.
4. Leave this browser tab open — you will need the URL on the next page.

---

### Part 3 — Install Git on Your Computer

> If you already have Git installed, skip to Part 4.

**Windows:**
1. Go to **https://git-scm.com/download/win** and download the installer.
2. Run the installer — click **Next** through every screen. All defaults are fine.
3. Open **Git Bash** from the Start menu.

**Mac:**
1. Open **Terminal** (press Cmd+Space, type `terminal`, press Enter).
2. Type `git --version` and press Enter.
3. If Git is not installed, a prompt will appear asking you to install **Xcode Command Line Tools**. Click **Install**.

**Linux (Ubuntu / Debian):**
```bash
sudo apt update && sudo apt install git -y
```

---

### Part 4 — Download This Project to Your Computer

> These steps use the terminal (Git Bash on Windows, Terminal on Mac/Linux).

1. Download this project as a ZIP from v0 (click the three dots → **Download ZIP**).
2. Unzip the file. You will get a folder called `v0-project` (or similar).
3. Inside that folder, find the `projectx-bch-solo` folder. That is your project.
4. Open your terminal and navigate into that folder:

```bash
cd /path/to/projectx-bch-solo
```

Replace `/path/to/projectx-bch-solo` with the actual path on your computer.  
**Example on Windows (Git Bash):** `cd ~/Downloads/v0-project/projectx-bch-solo`  
**Example on Mac:** `cd ~/Downloads/v0-project/projectx-bch-solo`

---

### Part 5 — Push the Project to GitHub

Copy the commands below one by one and paste them into your terminal.  
Replace `YOUR_GITHUB_USERNAME` and `YOUR_REPO_NAME` with your actual values.

```bash
# 1. Tell Git who you are (only needed once per computer)
git config --global user.email "you@example.com"
git config --global user.name "Your Name"

# 2. Initialize a Git repository in this folder
git init

# 3. Add all files
git add .

# 4. Make your first commit
git commit -m "Initial commit — Project X BCH Solo"

# 5. Point Git to your GitHub repository
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/YOUR_REPO_NAME.git

# 6. Push to GitHub
git branch -M main
git push -u origin main
```

When you run step 6, GitHub will ask for your **username** and **password**.  
If you have two-factor authentication enabled (recommended), use a **Personal Access Token** instead of your password:

1. Go to **https://github.com/settings/tokens**
2. Click **Generate new token (classic)**
3. Give it a name, set expiry, check the **repo** scope, click **Generate token**
4. Copy the token and paste it as your password in the terminal prompt.

Refresh your GitHub repository page — you should see all the files.

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
   git clone https://github.com/YOUR_GITHUB_USERNAME/projectx-bch-solo.git
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
| Bitcoin Cash Node | `bitcoin-cash-node:v28.0.1` |
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
