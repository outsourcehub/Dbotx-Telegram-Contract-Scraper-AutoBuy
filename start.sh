#!/bin/bash

# Ultra-Fast Trading Bot Startup Script
echo "🚀 Starting Ultra-Fast Trading Bot..."

# Check Python version
python3 --version

# Set optimal environment variables for performance
export PYTHONUNBUFFERED=1
export PYTHONOPTIMIZE=2

# Start the bot
echo "⚡ Launching bot in ultra-fast mode..."
python3 bot.py
