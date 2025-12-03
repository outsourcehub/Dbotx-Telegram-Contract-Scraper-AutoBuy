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
