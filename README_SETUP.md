# DbotxScraperVtech - Setup Instructions

## ⚠️ Security Warnings (Important!)

Since these executables are **unsigned**, your operating system will show security warnings. This is normal and expected:

### Windows
When you run the `.exe` file, Windows SmartScreen will show a warning:
1. Click **"More info"**
2. Click **"Run anyway"**

Alternative method:
1. Right-click the `.exe` file
2. Select **Properties**
3. Check **"Unblock"** at the bottom
4. Click **Apply** → **OK**

### macOS
When you run the executable, macOS Gatekeeper will block it:
1. **Don't double-click** the file
2. **Right-click** (or Control+click) the file
3. Select **"Open"**
4. Click **"Open"** in the dialog

Alternative method:
1. Go to **System Preferences** → **Security & Privacy**
2. Click **"Open Anyway"** for DbotxScraperVtech

### Linux
The executable needs execute permissions:
```bash
chmod +x DbotxScraperVtech-*-Linux
./DbotxScraperVtech-*-Linux
```

## System Requirements

- **Windows**: Windows 10 or later (64-bit)
- **macOS**: macOS 10.15 (Catalina) or later
- **Linux**: Ubuntu 20.04 or later (or equivalent)

## First Time Setup

1. **Run the executable** (DbotxScraperVtech-*.exe on Windows, DbotxScraperVtech-* on macOS/Linux)

2. **Enter your credentials when prompted:**
   - **BOT_TOKEN**: Your Telegram bot token from @BotFather
   - **API_ID**: Your API ID from https://my.telegram.org/apps
   - **API_HASH**: Your API hash from https://my.telegram.org/apps
   - **OWNER_CHAT_ID**: Your Telegram user ID (get it from @userinfobot)
   - **PHONE NUMBER**: Your Telegram account phone number (with country code like +1234567890)
   - **2FA PASSWORD**: Your Telegram 2FA password (if you have one enabled)

3. **Telegram Verification:**
   - After entering your phone number, Telegram will send you a verification code
   - Enter the code when prompted
   - If you have 2FA enabled, enter your password

4. **Done!** The bot will create a session file and start running.

## Files Created

After first run, these files will be created in the same folder:
- `config_local.py` - Your saved credentials (editable)
- `trading_bot_session.session` - Telegram session (do not share!)
- `trading_bot.db` - SQLite database (auto-created)
- `bot.log` - Application logs

## Editing Your Configuration

You can manually edit `config_local.py` to change your credentials:

```python
BOT_TOKEN = 'your_bot_token'
API_ID = 12345678
API_HASH = 'your_api_hash'
OWNER_CHAT_ID = 123456789
```

## Troubleshooting

- **Bot won't start**: Delete `config_local.py` and run again to re-enter credentials
- **Session expired**: Delete the `.session` file and restart
- **Permission errors**: Make sure the bot folder has write permissions

## Getting Your Credentials

1. **BOT_TOKEN**: Message @BotFather on Telegram, create a new bot
2. **API_ID & API_HASH**: Go to https://my.telegram.org/apps and create an app
3. **OWNER_CHAT_ID**: Message @userinfobot on Telegram to get your user ID
