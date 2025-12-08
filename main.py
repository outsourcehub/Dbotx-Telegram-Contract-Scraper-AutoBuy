#!/usr/bin/env python3
"""
Main entry point for Ultra-Fast Trading Bot (Telethon)
"""
import asyncio
import sys
import logging

if __name__ == "__main__":
    from first_run_setup import check_and_run_setup
    check_and_run_setup()

    # DISABLE ALL LOGGING
    logging.disable(logging.CRITICAL)

    # ENABLE ALL MODULE LOGS AT DEBUG LEVEL
    # Production logging levels
    logging.getLogger('telethon').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('websockets').setLevel(logging.WARNING)
    logging.getLogger('realtime').setLevel(logging.INFO)
    logging.getLogger('handlers_telethon').setLevel(logging.INFO)
    logging.getLogger('utils').setLevel(logging.INFO)
    logging.getLogger('bot').setLevel(logging.INFO)
    logging.getLogger('api_client').setLevel(logging.INFO)
    logging.getLogger('models').setLevel(logging.INFO)
    logging.getLogger('token_validator').setLevel(logging.INFO)

    print("="*80)
    print("🔍 DEBUG MODE ENABLED - ALL LOGS VISIBLE")
    print("="*80)

    from bot import main as bot_main
    try:
        asyncio.run(bot_main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)