# Telegram Subtitle Merger Bot

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Telethon](https://img.shields.io/badge/telethon-v1.36%2B-orange.svg)](https://github.com/LonamiWebs/Telethon)
[![FFmpeg](https://img.shields.io/badge/ffmpeg-stream%20muxing-green.svg)](https://ffmpeg.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A high-performance Telegram bot built on MTProto (Telethon) and FFmpeg for multiplexing subtitles into video files up to 2 GB with zero re-encoding latency and automated cloud cache indexing.

---

## ⚡ Features

* **Large File Support (up to 2 GB):** Powered by native MTProto via Telethon, bypassing standard Bot API 50 MB payload constraints.
* **Lossless Stream Multiplexing:** Subtitles are remuxed (`-c copy`) without re-encoding the video stream. Processing a 1.5 GB file finishes in seconds with minimal CPU load.
* **Storage Channel & Instant Cache:** Processed media is indexed in SQLite and persisted to a dedicated storage channel. Duplicate user requests are resolved instantly via direct message forwarding.
* **Automated Cleanup:** Ephemeral storage buffers are wiped immediately upon task completion to prevent disk exhaustion.
* **Production Daemon Ready:** Fully compatible with Linux `systemd` service management for 24/7 background operation.

---

## 📂 Project Structure

```text
subtitle-bot/
├── bot.py             # Event handlers and Telegram lifecycle management
├── merger.py          # FFmpeg multiplexing routines
├── database.py        # SQLite persistence layer and query interface
├── config.py          # Environment configuration loader
├── fast_telethon.py   # High-speed chunked upload/download utilities
├── requirements.txt   # Runtime dependencies
├── .env.example       # Template for environment secrets
└── README.md          # Technical documentation
```

---

## ⚙️ Configuration

Copy the sample environment file:

```bash
cp .env.example .env
```

Configure the following variables in `.env`:

| Key | Description |
| :--- | :--- |
| `BOT_TOKEN` | Telegram Bot token issued by [@BotFather](https://t.me/BotFather) |
| `API_ID` | Telegram application API ID from [my.telegram.org](https://my.telegram.org) |
| `API_HASH` | Telegram application API Hash from [my.telegram.org](https://my.telegram.org) |
| `STORAGE_CHANNEL_ID` | Telegram Channel ID (e.g. `-1001234567890`) where processed media is archived |
| `ADMIN_ID` | Telegram user ID of the administrator |

---

## 🚀 Quickstart

### Prerequisites

* Python 3.10 or higher
* FFmpeg installed on system path

### Local Setup

```bash
# Clone the repository
git clone https://github.com/xamidullayev38/subtitle-bot.git
cd subtitle-bot

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the bot
python bot.py
```

---

## 🛡️ Production Deployment (systemd)

For running continuously on Linux (e.g., Ubuntu VPS):

1. Create a service unit:
   ```bash
   sudo nano /etc/systemd/system/subtitle-bot.service
   ```

2. Add configuration:
   ```ini
   [Unit]
   Description=Telegram Subtitle Merger Bot
   After=network.target

   [Service]
   Type=simple
   User=azureuser
   WorkingDirectory=/home/azureuser/subtitle-bot
   ExecStart=/home/azureuser/subtitle-bot/.venv/bin/python bot.py
   Restart=always
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   ```

3. Enable and start:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now subtitle-bot
   ```

---

## 📄 License

This project is licensed under the MIT License.
