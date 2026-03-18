# AIM Website — Local Development Setup Guide

This guide gets you from a brand-new computer to a fully running local copy of the AIM website.
No prior Docker or Django experience needed. Follow each step in order.

---

## What you'll need from Daniel before you start

- [ ] The database dump file (e.g. `aim_dev.sql`) — sent separately, not on GitHub
- [ ] The `FIELD_ENCRYPTION_KEY` value — a secret key that unlocks encrypted data in the database

---

## Step 1 — Install Docker Desktop

Docker runs the website and database inside isolated containers so you don't have to install Python or PostgreSQL directly on your machine.

1. Download Docker Desktop: https://www.docker.com/products/docker-desktop/
2. Install it and open it
3. Wait for the Docker whale icon to appear in your menu bar (Mac) or system tray (Windows) and show "Docker Desktop is running"

> You don't need to create a Docker account. You can skip any sign-in prompts.

---

## Step 2 — Clone the repository

This downloads the code to your computer.

Open Terminal (Mac) or Git Bash (Windows) and run:

```
git clone [PASTE GITHUB REPO URL HERE]
```

Then navigate into the folder:

```
cd WebsiteRedesign
```

> All commands from here on should be run from inside this `WebsiteRedesign` folder.

---

## Step 3 — Add the database dump

Daniel will send you a file called something like `aim_dev.sql`.

Copy that file into:

```
WebsiteRedesign/docker/initdb/
```

It should look like this when done:

```
WebsiteRedesign/
  docker/
    initdb/
      aim_dev.sql    ← your file goes here
```

**Mac — using Finder:**

1. Open Finder and navigate to your `WebsiteRedesign` folder
2. Open `docker` → `initdb`
3. Drag and drop the `.sql` file in

**Windows — using File Explorer:**

1. Open File Explorer and navigate to your `WebsiteRedesign` folder
2. Open `docker` → `initdb`
3. Paste the `.sql` file in

---

## Step 4 — Configure your environment file

This file tells Django how to connect to the database and which secret keys to use.

1. Open the `WebsiteRedesign` folder in your file explorer
2. Find the file named `.env.docker`
3. Open it in any text editor (Notepad, TextEdit, VS Code, etc.)
4. Find this line near the bottom:
   ```
   FIELD_ENCRYPTION_KEY=replace-me-with-the-key-daniel-gave-you
   ```
5. Replace `replace-me-with-the-key-daniel-gave-you` with the key Daniel sent you
6. Save and close the file

---

## Step 5 — Start the application

Back in your terminal, run:

```
docker compose up
```

The first time you run this it will:

1. Download the PostgreSQL database image (~100 MB)
2. Build the Django application image and install all Python packages (~3–5 minutes)
3. Import your database dump into PostgreSQL (may take a minute depending on dump size)
4. Start the website

You'll know it's ready when you see a line like:

```
web-1  | Django version 6.0.3, using settings 'mysite.settings.dev'
web-1  | Starting development server at http://0.0.0.0:8000/
```

Open your browser and go to: **http://localhost:8000**

> Leave the terminal window open while you're working — it shows you live request logs.
> To stop the server, press `Ctrl + C` in the terminal.

---

## Step 7 — Run database migrations (first time only)

Open a **second terminal window** (keep the first one running), navigate to the project folder, and run:

```
docker compose exec web python manage.py migrate
```

This sets up any database tables that aren't in the dump yet. You'll see a list of migration names scroll by — that's normal.

---

## You're done!

The site is running at **http://localhost:8000**

---

## Daily workflow

Every day when you want to work on the project:

**Start:**

```
docker compose up
```

**Stop (when you're done for the day):**
Press `Ctrl + C` in the terminal, then run:

```
docker compose down
```

**Pull the latest code from GitHub and restart:**

```
git pull
docker compose down
docker compose up
```

If the pull included database changes (migrations), also run:

```
docker compose exec web python manage.py migrate
```

---

## Troubleshooting

### "Docker Desktop is not running"

Open Docker Desktop from your Applications folder (Mac) or Start menu (Windows) and wait for it to fully start before running `docker compose up`.

### The page shows a database error or "relation does not exist"

Your migrations may not be up to date. Run:

```
docker compose exec web python manage.py migrate
```

### Port 5432 is already in use

You have a local PostgreSQL installation running on your machine. Run:

```
# Mac (if installed via Homebrew)
brew services stop postgresql

# Then try again
docker compose up
```

### Port 8000 is already in use

Something else is using port 8000. Find and stop it, or open `docker-compose.yml`, change `"8000:8000"` to `"8001:8000"`, and access the site at http://localhost:8001 instead.

### I see "FIELD_ENCRYPTION_KEY" errors

The encryption key in `.env.docker` doesn't match the database dump. Double-check that you copied it exactly (no extra spaces or line breaks) from what Daniel sent you.

### I want to start fresh with a new database dump

Replace the file in `docker/initdb/` with the new dump, then run:

```
docker compose down -v
docker compose up
```

The `-v` flag deletes the stored database so it gets re-imported from your new file.

### Nothing is working and I want to start completely over

```
docker compose down -v
docker system prune
docker compose up
```

This removes everything Docker has cached and rebuilds from scratch. Takes 5–10 minutes.

---

## Glossary

| Term                    | What it means                                                                  |
| ----------------------- | ------------------------------------------------------------------------------ |
| **Docker**              | Software that runs apps in isolated "containers" — like a mini virtual machine |
| **Container**           | A running instance of an image (your database, your Django app)                |
| **Image**               | A blueprint for a container (think: installer)                                 |
| **docker compose up**   | Starts all containers defined in `docker-compose.yml`                          |
| **docker compose down** | Stops and removes the containers (data is preserved unless you add `-v`)       |
| **Migration**           | A database schema change — run `migrate` after pulling new code                |
| **Terminal / Git Bash** | A text-based window where you type commands                                    |
