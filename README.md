# Open Source Telegram Scraper Trading Bot

A high-performance Telegram scraper bot for automated cryptocurrency trading across multiple blockchains (Solana, Ethereum, Base, BSC,Arbitrum and Tron). This bot monitors Telegram channels for contract addresses and automatically executes trades through the DBOTX.

## 🚀 Features

- **Multi-Chain Support**: Trade on Solana, Ethereum, Base, BSC, Arbitrum and Tron
- **Real-Time Monitoring and buying**: Automatically detects contract addresses from Telegram channels and groups
- **Safety Filters**: Configurable filters to protect against scam tokens
- **Monitor multiple channels and groups**: You can monitor both private and public channels/groups with thier own seperate setting for each one
- **Monitor Admins Only In groups**: You can choose to only monitor admins in the group
- **Monitor Specific Users In groups**: You can choose to only monitor admins in the group
- **High Performance**: Sub-200ms contract detection and trade execution

## 📋 Prerequisites

Before you begin, you'll need:

1. A Telegram account
2. A DBOT account (for verification)

---

## 🛠️ Complete Setup Guide

### Step 1: Get the Code (OPTIONAL: This step only applies if you are hosting this 24/7 online)

**If on GitHub**: Go to [https://github.com/outsourcehub/Dbotx-Telegram-Contract-Scraper-AutoBuy](https://github.com/outsourcehub/Dbotx-Telegram-Contract-Scraper-AutoBuy) and fork/clone it

### Step 2: Get Telegram Credentials

#### 2A. Get Your API ID and API Hash

1. Go to [https://my.telegram.org/auth](https://my.telegram.org/auth)
2. Enter your phone number with country code (e.g., `+1234567890`)
3. Enter the code Telegram sends you
4. Click **"API development tools"**
5. Fill in the form:

   * **App title**: `Trading Bot` (or any name)
   * **Short name**: `tradingbot`
   * **Platform**: Select `Other`

6. Click **"Create application"**
7. **SAVE THESE TWO VALUES** (you'll need them in Step 4):

   * `api\_id` (a number like `12345678`)
   * `api\_hash` (looks like `abcd1234efgh5678ijkl9012mnop3456`)

#### 2B. Create Your Bot Token

1. Open Telegram and search for `@BotFather`
2. Send the command: `/newbot`
3. Choose a display name: `My Trading Bot` (or any name you like)
4. Choose a username (must end with `bot`): `my\_trading\_bot` (must be unique)
5. **SAVE THE BOT TOKEN** BotFather gives you (looks like `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)
6. Make sure to check your new bot out, use the /start button.

#### 2C. Get Your User ID

1. In Telegram, search for `@userinfobot`
2. Send `/start`
3. **SAVE YOUR USER ID** (a number like `123456789`)

---

### Step 3: Download PC Version, Start Auto-Buy Now.
1.  Go to [Assests - Blazing-Bot-Telegram-Autobuy-Scraper/releases/tag/AutoBuyBlazingBotV1](https://github.com/outsourcehub/Blazing-Bot-Telegram-Autobuy-Scraper/releases/tag/AutoBuyBlazingBotV1) In the assets download the exe for your pc
2.  Unzip the folder, open the app, it should lead you to a console where you will setup your telegram bot token, your user Id (also known as owner chat ID), api id, api hash and number associated with the api hash/Id
3. You should be prompted to verify your number, you'll get a telegram code input it quickly dont waste more than 3 minutes. You will sucessfully be logged in a ready. Go to your telegram bot to setup the scraper

---
---

## 📜 License: Prosperity Public License 3.0.0

You are **free to**:
- Run this bot for personal use
- Set up your own Telegram bot token in `.env`
- Use it to scrape contracts — completely free

You **must not**:
- Modify core files not stated in Allowed config files (line 17) (e.g., `bot.py`, `handlers.py`) to **remove or replace** the referral/affiliate links
- Redistribute a version with **your own monetization links**
- Use this project to generate revenue (directly or indirectly) **without permission**

> 💡 Why?  
> This tool is free because it includes referral links that support its development.  
> If you remove them and add yours, you’re engaging in **commercial use** under the PPL — which requires my permission.

✅ **Allowed config file**: 
No file is completely allowed to be modified, you can only modify this part below of the config.py file (for setting up primary keys rquired to run the bot, etc.)  
BOT_TOKEN = config('Paste your bot token from Step', default='')
API_ID = config('Paste your api_id from Step', default=0, cast=int)
API_HASH = config('Paste your api_hash from Step', default='')
OWNER_CHAT_ID = config('Paste your user ID from Step', default=0, cast=int)

❌ **Do not modify**: any file that contains user-facing messages or links

Have a legit commercial need? Open an issue — I’m open to collaboration!
