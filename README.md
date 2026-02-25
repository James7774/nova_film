# Code to Video Delivery Bot

A professional Telegram bot built with aiogram v3 and SQLite.

## Features

- **User Side:**
  - Get videos by numeric code.
  - Search videos by name/title.
  - Daily limit (configurable, default 5).
  - Mandatory channel subscription check.
- **Admin Side:**
  - Add videos with codes, titles, and quality.
  - Set expiration time for codes (e.g. `/add 123 --expires 24h`).
  - Delete codes.
  - View bot statistics and list all codes.

## Installation

1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file and add your `BOT_TOKEN`, `ADMINS`, and `CHANNELS`.
4. Run the bot:
   ```bash
   python main.py
   ```

## Admin Commands

- `/add <code> [--expires 24h]` - Start the flow to add a video.
- `/delete <code>` - Remove a code and its videos.
- `/list` - List all stored codes and titles.
- `/stats` - View user and video statistics.
