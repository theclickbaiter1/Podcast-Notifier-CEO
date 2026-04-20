# 🔔 Online Notifier

A modular, automated notification system that runs daily via **GitHub Actions**. Currently tracks "Whale CEO" podcast appearances using the **Apple iTunes Search API** (free, no API key needed) and sends alerts via **Telegram**.

Designed to be **extensible** — drop in new Trackers (YouTube, RSS, etc.) or Notifiers (Discord, Slack, Email) without touching the core loop.

---

## 📂 Project Structure

```
├── .github/workflows/
│   └── daily_tracker.yml       # GitHub Actions cron job (22:30 EST daily)
├── src/
│   ├── main.py                 # Entry point — orchestrates trackers & notifiers
│   ├── config.py               # Loads & validates environment variables
│   ├── trackers/
│   │   ├── base_tracker.py     # Abstract base class for trackers
│   │   └── itunes.py           # Apple iTunes Search API tracker
│   └── notifiers/
│       ├── base_notifier.py    # Abstract base class for notifiers
│       └── telegram.py         # Telegram Bot notifier
├── seen.json                   # Auto-managed deduplication state
├── .env.example                # Template for local environment variables
├── requirements.txt            # Python dependencies
└── README.md
```

---

## 🚀 Deployment Guide

### Step 1 — Clone & Local Setup

```bash
git clone https://github.com/theclickbaiter1/Podcast-Notifier-CEO.git
cd Podcast-Notifier-CEO
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
# source venv/bin/activate
pip install -r requirements.txt
```

### Step 2 — Create a Telegram Bot & Get Your Chat ID

1. Open Telegram and search for **@BotFather**.
2. Send `/newbot` and follow the prompts to name your bot.
3. BotFather will give you a **Bot Token** (e.g., `123456:ABC-DEF1234…`).
4. **Start a conversation** with your new bot (send it any message like "hello").
5. Visit `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates` in your browser.
6. In the JSON response, find `"chat": {"id": 123456789}` — that number is your **Chat ID**.

### Step 3 — Configure Environment Variables

#### For local development:

```bash
cp .env.example .env
# Edit .env and fill in your real values
```

#### For GitHub Actions:

Go to your repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret** and add:

| Secret Name           | Value                   |
| --------------------- | ----------------------- |
| `TELEGRAM_BOT_TOKEN`  | Your Telegram bot token |
| `TELEGRAM_CHAT_ID`    | Your Telegram chat ID   |
| `PAT`                 | A GitHub Personal Access Token (see below) |

> **Note:** No podcast API keys are needed — the iTunes Search API is free and requires no authentication.

### Step 4 — Create a GitHub Personal Access Token (PAT)

The workflow needs to push `seen.json` back to the repo.

1. Go to [GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens](https://github.com/settings/tokens?type=beta).
2. Click **Generate new token**.
3. Give it a name (e.g., `podcast-notifier-push`).
4. Under **Repository access**, select **Only select repositories** → pick `Podcast-Notifier-CEO`.
5. Under **Permissions** → **Repository permissions** → set **Contents** to **Read and write**.
6. Click **Generate token** and copy it.
7. Add it as the `PAT` secret in your repo (see Step 3).

### Step 5 — Test It

#### Locally:

```bash
python -m src.main
```

#### On GitHub Actions:

1. Push your code to the `main` branch.
2. Go to **Actions** tab → **Daily Tracker** → **Run workflow** → click the green button.
3. Check your Telegram for notifications!

---

## 🧩 Extending the System

### Adding a New Tracker

1. Create `src/trackers/my_tracker.py`.
2. Subclass `BaseTracker` and implement `fetch_new_items(seen_ids)`.
3. In `src/main.py`, import it and add to the `trackers` list:

```python
from src.trackers.my_tracker import MyTracker

trackers = [
    ITunesTracker(settings),
    MyTracker(settings),          # ← new
]
```

### Adding a New Notifier

1. Create `src/notifiers/my_notifier.py`.
2. Subclass `BaseNotifier` and implement `send(items)`.
3. In `src/main.py`, import it and add to the `notifiers` list:

```python
from src.notifiers.my_notifier import MyNotifier

notifiers = [
    TelegramNotifier(settings),
    MyNotifier(settings),          # ← new
]
```

---

## 📝 License

MIT
