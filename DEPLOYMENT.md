# CollectIQ — How to Run It and Put It Live

This guide is written to be followed even if you don't have a technical
background. Take it one numbered step at a time.

CollectIQ has three parts that run together: a **database** (MongoDB), a
**backend** (the brain, written in Python), and a **frontend** (the website you
look at). The setup below starts all three with a single command.

---

## What was fixed so this can run anywhere

This app was originally built on a platform called Emergent and depended on a
few things that only worked there. Those have been replaced with standard,
free, widely-used equivalents, so it now runs on any normal computer or server:

- The AI document-reading feature now uses **Google Gemini** with a free key
  (instead of the Emergent-only AI library).
- The website now builds cleanly on its own.
- Login works correctly both on your own computer and on a live HTTPS website.

You do **not** need to understand any of that to follow the steps below.

---

## Option 1 — See it running on your own computer (easiest, ~15 min)

This is the best way to confirm everything works before paying for anything.

### Step 1. Install Docker Desktop
Download and install it from https://www.docker.com/products/docker-desktop/
(available for Windows and Mac). Open Docker Desktop once installed and wait
until it says it is running.

> Docker is a free tool that runs the whole app for you in the background so you
> don't have to install Python, databases, etc. by hand.

### Step 2. Get the project onto your computer
If you have the project as a folder already, use that. Otherwise download it
from GitHub (the green **Code** button → **Download ZIP**) and unzip it.

### Step 3. Create your settings file
Inside the project there is a folder called `backend`. In it you'll find a file
named `.env.example`. Make a copy of it in the same folder and name the copy
exactly `.env` (just `.env`, nothing before the dot).

Open that new `.env` file in any text editor and change **one** important line —
the security secret:

```
JWT_SECRET=change-me-to-a-long-random-secret
```

Replace the right-hand side with any long random jumble of letters and numbers,
for example `JWT_SECRET=8f3Kd9_xQ2mLpZ7rVn4Wb6Ty1Hs0Gc5Aa`. (This just keeps
logins secure. It can be anything, as long as it's long and not shared.)

You can leave everything else as-is for now. The AI key is optional — see the
"AI document reading" section later.

### Step 4. Start everything
Open a terminal **in the project folder** (the folder that contains the file
`docker-compose.yml`):

- **Windows:** open the folder in File Explorer, click the address bar, type
  `cmd`, and press Enter.
- **Mac:** right-click the folder → Services → "New Terminal at Folder".

Then type this and press Enter:

```
docker compose up -d --build
```

The first time, this downloads and builds everything and may take 5–10 minutes.
When it finishes you'll get your prompt back.

### Step 5. Open the app
Go to your web browser and visit:

```
http://localhost:8080
```

Log in with:

- **Email:** `admin@company.com`
- **Password:** `Admin@123`

You should see the dashboard with four weeks of sample data already loaded.

### To stop it
In the same terminal:

```
docker compose down
```

Your data is saved and will still be there next time you start it. (To wipe all
data and start fresh, use `docker compose down -v`.)

---

## Option 2 — Put it live on the internet (a small server)

To give other people a web link they can visit, the app needs to run on a
computer that's always on and reachable from the internet — a "server". The
simplest kind is a small cloud server (often called a VPS) that costs roughly
**$4–6 per month**.

> Why not a one-click free host? This app is three pieces that must talk to each
> other privately (website + brain + database). A single small server running
> the exact same command from Option 1 is the most reliable, cheapest, and
> easiest-to-reason-about way to do that. The instructions below are copy-paste.

### Step 1. Create a server
Sign up with any provider (DigitalOcean, Hetzner, Vultr, Linode are all common)
and create the smallest **Ubuntu 24.04** server. 1 GB of RAM is enough; 2 GB is
comfortable. They'll give you an IP address (like `203.0.113.45`) and a way to
log in.

### Step 2. Log into the server and install Docker
Connect to the server (the provider shows you how — usually a "Console" button
in your browser, or `ssh root@YOUR_SERVER_IP` from your own terminal). Then run:

```
curl -fsSL https://get.docker.com | sh
```

### Step 3. Put the project on the server
The easiest way, if your project is on GitHub:

```
git clone https://github.com/AryanShah45/Collectiq.git
cd Collectiq
```

### Step 4. Create your settings file (same as before)
```
cp backend/.env.example backend/.env
nano backend/.env
```
Change `JWT_SECRET` to a long random value (as in Option 1, Step 3). Also change
`ADMIN_PASSWORD` to a strong password of your own — this is now a real, public
login. Save with `Ctrl+O`, Enter, then exit with `Ctrl+X`.

### Step 5. Start it
```
docker compose up -d --build
```

### Step 6. Visit it
In your browser go to:

```
http://YOUR_SERVER_IP:8080
```

That's your live app. Log in with `admin@company.com` and the password you set.

### Making it nicer (optional)
- **A real web address** (like `collectiq.yourcompany.com`) instead of an IP:
  buy a domain and point it at your server's IP, then put a small HTTPS proxy
  (Caddy is the easiest — it gets a free SSL certificate automatically) in front
  of port 8080. If you'd like, I can write that Caddy config for you.
- **Security:** once you're on HTTPS, it's good practice to set `COOKIE_SECURE=true`
  in `backend/.env` and restart.

---

## AI document reading (optional, free)

The "upload the meeting PDF/Excel and auto-fill the numbers" feature uses Google
Gemini. Everything else works without it. To turn it on:

1. Get a free key from Google AI Studio: https://aistudio.google.com/app/apikey
2. Open `backend/.env` and paste it in:
   ```
   GEMINI_API_KEY=your-key-here
   ```
3. Restart: `docker compose up -d --build`

If you leave the key blank, the app runs normally — only the file-upload
auto-extraction is disabled (you can still enter meetings manually).

---

## Login details

The first admin account is created automatically from your `.env` file
(`ADMIN_EMAIL` / `ADMIN_PASSWORD`). Defaults are:

- Admin (can edit everything): `admin@company.com` / `Admin@123`

Once logged in as admin, you can add more users (including read-only "viewer"
accounts for leadership) from inside the app.

**Change the default admin password before sharing the app with anyone.**

---

## If something goes wrong

- **See what's happening:** `docker compose logs -f` (press `Ctrl+C` to stop
  watching). This shows messages from all three parts.
- **Restart everything:** `docker compose restart`
- **Rebuild from clean:** `docker compose down` then `docker compose up -d --build`
- **"Port already in use":** something else is using port 8080. Either stop it,
  or open `docker-compose.yml` and change `"8080:80"` to `"9090:80"`, then use
  port 9090 in your browser.
- **Login seems to "not stick" on a live HTTPS site:** set `COOKIE_SECURE=true`
  in `backend/.env` and restart.

---

## Appendix — Running without Docker (for developers)

**Backend** (needs Python 3.12 and a MongoDB you can reach):
```
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # then edit MONGO_URL, JWT_SECRET, etc.
uvicorn server:app --host 0.0.0.0 --port 8001
```
(There is also a helper, `_run_local.py`, that runs the backend against an
in-memory database with no MongoDB needed — handy for a quick look:
`pip install mongomock-motor` then `python _run_local.py`.)

**Frontend** (needs Node.js 20):
```
cd frontend
cp .env.example .env        # REACT_APP_BACKEND_URL=http://localhost:8001
npm install --legacy-peer-deps
npm start                   # opens http://localhost:3000
```
