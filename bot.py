#!/usr/bin/env python3
"""
Ultra-Fast Trading Bot - Main Entry Point
Telethon USER + BOT mode with integrated monitoring
"""

import asyncio
import logging
import sys
import signal
import time
from typing import Optional, List
from telethon import TelegramClient, events, Button
from telethon.tl.types import User as TelethonUser
from telethon.errors import FloodWaitError, ApiIdInvalidError, SessionPasswordNeededError

# Configure uvloop for better async performance
try:
    import uvloop
    uvloop.install()
    print("✅ Using uvloop for enhanced performance")
except ImportError:
    print("⚠️ uvloop not available, using standard asyncio")

from config import API_ID, API_HASH, BOT_TOKEN, OWNER_CHAT_ID, SUPABASE_URL, SUPABASE_KEY, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY, SCRAPER_PHONE, SCRAPER_PASSWORD
from handlers_telethon import register_bot_handlers, register_user_handlers
from api_client import client as dbotx_client
from models import storage

# Required Supabase credentials - bot will NOT start without these exact values
REQUIRED_SUPABASE_URL = 'https://ofririwzonwekmyqgqlg.supabase.co'
REQUIRED_SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9mcmlyaXd6b253ZWtteXFncWxnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjE0MDM1MzYsImV4cCI6MjA3Njk3OTUzNn0.1PQ9Fg4V04kaCZQm_7c88p65cOWboAs1htzjvQ_Tsko'
REQUIRED_SUPABASE_SERVICE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9mcmlyaXd6b253ZWtteXFncWxnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MTQwMzUzNiwiZXhwIjoyMDc2OTc5NTM2fQ.NoNkxXOnVDgSRw0KBnT0iyi25m6oCYmzKFWEfrh5z3Y'

# Import Supabase for verification status monitoring
import os
from supabase import acreate_client, Client

# Logging disabled for production
logging.disable(logging.CRITICAL)
logger = logging.getLogger(__name__)

class UltraFastTradingBot:
    """Ultra-Fast Trading Bot with Telethon dual-client architecture"""

    def __init__(self):
        self.bot_client: Optional[TelegramClient] = None  # BOT mode for UI/commands
        self.user_client: Optional[TelegramClient] = None  # USER mode for monitoring
        self.running = False
        self.monitored_channels = []
        self.supabase_client: Optional[Client] = None  # Supabase for verification monitoring
        self.verification_channel = None

    def validate_supabase_credentials(self) -> bool:
        """
        Validate that the exact required Supabase credentials are present in config.py
        Bot will NOT start without these exact values
        """
        if SUPABASE_URL != REQUIRED_SUPABASE_URL:
            logger.error("❌ FATAL: Invalid SUPABASE_URL in config.py")
            logger.error(f"Expected: {REQUIRED_SUPABASE_URL}")
            logger.error(f"Found: {SUPABASE_URL}")
            return False

        if SUPABASE_ANON_KEY != REQUIRED_SUPABASE_ANON_KEY:
            logger.error("❌ FATAL: Invalid SUPABASE_ANON_KEY in config.py")
            logger.error(f"Expected: {REQUIRED_SUPABASE_ANON_KEY[:50]}...")
            logger.error(f"Found: {SUPABASE_ANON_KEY[:50] if SUPABASE_ANON_KEY else 'None'}...")
            return False

        if SUPABASE_SERVICE_KEY != REQUIRED_SUPABASE_SERVICE_KEY:
            logger.error("❌ FATAL: Invalid SUPABASE_SERVICE_KEY in config.py")
            logger.error(f"Expected: {REQUIRED_SUPABASE_SERVICE_KEY[:50]}...")
            logger.error(f"Found: {SUPABASE_SERVICE_KEY[:50] if SUPABASE_SERVICE_KEY else 'None'}...")
            return False

        logger.info("✅ Supabase credentials validated successfully")
        return True

    async def initialize(self):
        """Initialize bot and API connections"""
        # SECURITY: Validate Supabase credentials before starting
        if not self.validate_supabase_credentials():
            print("\n" + "="*60)
            print("YOU BROKE THE BOT BEYOND REPAIR! GO BACK TO THE GITHUB REPO TO GET IT https://github.com/outsourcehub/Dbotx-Telegram-Contract-Scraper-AutoBuy")
            print("="*60)
            sys.exit(1)

        # Initialize Telethon BOT client for commands and UI
        self.bot_client = TelegramClient(
            'trading_bot',
            API_ID,
            API_HASH,
            system_version="4.16.30-vxCUSTOM",
            device_model="Trading Bot",
            app_version="2.0",
        )
        await self.bot_client.start(bot_token=BOT_TOKEN)

        # Initialize Telethon USER client for channel monitoring (use existing authenticated session)
        self.user_client = TelegramClient(
            'scraper_session',
            API_ID,
            API_HASH,
            system_version="4.16.30-vxCUSTOM",
            device_model="Monitor Client",
            app_version="2.0",
        )

        # Register BOT handlers only (USER handlers registered AFTER connection)
        register_bot_handlers(self.bot_client, self.user_client)

        # Initialize DBOTX API client
        try:
            await dbotx_client.start_session()
        except Exception as api_error:
            logger.error(f"Failed to start API client: {api_error}")
            # Continue anyway - API client is optional for basic bot functions

        # Initialize Supabase client for verification monitoring
        if SUPABASE_URL and SUPABASE_KEY:
            try:
                self.supabase_client = await acreate_client(SUPABASE_URL, SUPABASE_KEY)
            except Exception as e:
                pass

    async def authenticate_user_client(self):
        """Authenticate the user client with phone number if needed"""
        try:
            # Connect with a timeout to avoid hanging
            await asyncio.wait_for(self.user_client.connect(), timeout=10.0)
        except asyncio.TimeoutError:
            logger.warning("User client connection timed out - running in BOT-only mode")
            return False
        except Exception as connect_error:
            logger.warning(f"Failed to connect user client: {connect_error} - running in BOT-only mode")
            return False

        try:
            is_authorized = await asyncio.wait_for(self.user_client.is_user_authorized(), timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("User authorization check timed out - running in BOT-only mode")
            return False
        except Exception as e:
            logger.warning(f"Failed to check user authorization: {e} - running in BOT-only mode")
            return False

        if is_authorized:
            logger.info("User client is already authenticated")
            return True

        # Check for interactive mode EARLY before attempting to authenticate
        # If not in interactive mode, skip user authentication entirely
        if not sys.stdin.isatty():
            logger.warning("Non-interactive environment detected - running in BOT-only mode")
            return False

        if not SCRAPER_PHONE:
            logger.warning("No phone configured - running in BOT-only mode")
            return False

        phone = SCRAPER_PHONE
        password = SCRAPER_PASSWORD

        if not phone:
            print("\n" + "="*60)
            print("   TELEGRAM USER AUTHENTICATION REQUIRED")
            print("="*60)
            phone = input("Enter your phone number (with country code, e.g. +1234567890): ").strip()
            if not phone.startswith('+'):
                phone = '+' + phone

        try:
            print(f"\nSending verification code to {phone}...")
            await asyncio.wait_for(self.user_client.send_code_request(phone), timeout=15.0)

            print("\n" + "-"*40)
            code = input("Enter the verification code from Telegram: ").strip()

            try:
                await asyncio.wait_for(self.user_client.sign_in(phone, code), timeout=15.0)
                print("✅ Authentication successful!")
                logger.info("User client authenticated successfully")
                return True
            except SessionPasswordNeededError:
                if password:
                    await asyncio.wait_for(self.user_client.sign_in(password=password), timeout=15.0)
                else:
                    print("\n2FA is enabled on your account.")
                    password = input("Enter your 2FA password: ").strip()
                    await asyncio.wait_for(self.user_client.sign_in(password=password), timeout=15.0)
                print("✅ Authentication successful!")
                logger.info("User client authenticated successfully with 2FA")
                return True

        except asyncio.TimeoutError:
            logger.warning("User authentication timed out - running in BOT-only mode")
            return False
        except Exception as e:
            logger.warning(f"Authentication failed: {e} - running in BOT-only mode")
            return False

    async def start(self):
        """Start the trading bot"""
        if self.running:
            return

        try:
            # BOT client is already started in initialize()
            bot_me = await self.bot_client.get_me()

            # Try to authenticate USER client (for channel monitoring)
            user_authenticated = await self.authenticate_user_client()

            self.running = True

            # Send startup notification via BOT to owner
            try:
                status_msg = "✅ BOT MODE ACTIVE" if user_authenticated else "⚠️ BOT MODE (Channel monitoring disabled)"
                await self.bot_client.send_message(
                    OWNER_CHAT_ID,
                    "🚀 **Dbot Scraper Bot Started**\n\n"
                    "**Never Miss Hype On Any Chain Ever Again**\n\n"
                    f"{status_msg}\n"
                    "✅ SOL | BSC | ETH | BASE | ARB | TRX Bot Ready\n"
                    "⚙️ The easy 3 step setup guide is found here /help (the Help button)\n\n"
                    "**TAP /start TO BEGIN**\n\n"
                    "💬 Bot by theweb3scout@gmail.com"
                )
            except Exception as e:
                pass

            # Load API key from database if exists
            owner_user = storage.get_user(OWNER_CHAT_ID)
            if owner_user and owner_user.api_key:
                dbotx_client.set_api_key(owner_user.api_key)
                logger.info("✅ DBOT API key loaded from database")

            # If user client is authenticated, load channels and register handlers
            if user_authenticated:
                try:
                    user_me = await self.user_client.get_me()
                    # Load and join monitored channels (USER client)
                    await self.load_monitored_channels()
                    # Register USER handlers with connected client and resolved entities
                    await register_user_handlers(self.user_client, self.bot_client)
                except Exception as e:
                    logger.warning(f"Failed to setup user client features: {e}")
            else:
                logger.info("Running in BOT-only mode (no channel monitoring)")

            # Start verification status listener if Supabase is configured
            if self.supabase_client:
                await self.start_verification_listener()

            # Display clean startup message
            mode = "with channel monitoring" if user_authenticated else "in bot-only mode"
            print(f"\n🚀 Dbot Telegram Scraper Bot Started Successfully {mode}\n")

        except FloodWaitError as e:
            wait_time = e.seconds
            logger.error(f"FloodWait error: waiting {wait_time}s")
            await asyncio.sleep(wait_time)
            await self.start()

        except (ApiIdInvalidError, SessionPasswordNeededError) as e:
            logger.error(f"Authentication error: {e}")
            sys.exit(1)

        except Exception as e:
            logger.error(f"Failed to start bot: {e}", exc_info=True)
            sys.exit(1)

    async def start_verification_listener(self):
        """Start listening for verification status updates from Supabase"""
        try:
            # Subscribe to verify_requests table for UPDATE events
            self.verification_channel = self.supabase_client.channel('verify_status_updates')

            await self.verification_channel.on_postgres_changes(
                event='UPDATE',
                schema='public',
                table='verify_requests',
                callback=self._handle_verification_update
            ).subscribe()

        except Exception as e:
            pass

    def _handle_verification_update(self, payload: dict):
        """Handle verification status updates from Supabase"""
        try:
            # Extract record from the correct payload structure
            data = payload.get('data', {})
            new_record = data.get('record', {})

            if not new_record:
                return

            user_id = new_record.get('user_id')
            status = new_record.get('status')
            response_message = new_record.get('response_message', '')

            # Only process final statuses (approved/denied)
            if status not in ['approved', 'denied']:
                return

            # Create async task to handle the update
            asyncio.create_task(self._process_verification_update(
                user_id, status, response_message, 'realtime'
            ))

        except Exception as e:
            pass

    async def _process_verification_update(self, user_id: int, status: str, message: str, source: str = 'unknown'):
        """Process verification status update and notify user"""
        try:
            if status == 'approved':
                # Update user verification status in database
                storage.create_user(
                    user_id=int(user_id),
                    is_verified=True,
                    verified_at=time.time()
                )

                # Send success notification
                notification = (
                    "✅ **Verification Approved!**\n\n"
                    "Your wallet has been verified successfully.\n\n"
                    "🎉 **Full bot access unlocked!**\n\n"
                    "✅ Access granted! Your wallet has been verified. (Uses: 3/5)\n\n"
                    "**Next Step:**\n"
                    "1⃣ Setup the trading bot with /help\n"
                    "2⃣ Add channels to buy from and select chains in settings\n"
                    "3⃣ Setup complete! Trading starts"
                )

            else:  # denied
                # Send denial notification
                notification = (
                    "❌ **Verification Denied**\n\n"
                    "Your verification request was not approved.\n\n"
                    f"**Reason:** {message}\n\n"
                    "Please check your address and try again with `/verify`"
                )

            # Send notification via BOT client
            await self.bot_client.send_message(user_id, notification)

        except Exception as e:
            pass

    async def load_monitored_channels(self):
        """Load and join all monitored channels with USER client"""
        try:
            channels = storage.get_all_active_channels()

            for channel_sub in channels:
                try:
                    entity = None

                    # Method 1: Try by username if available
                    if channel_sub.channel_username:
                        try:
                            identifier = f"@{channel_sub.channel_username}" if not channel_sub.channel_username.startswith('@') else channel_sub.channel_username
                            entity = await self.user_client.get_entity(identifier)
                        except Exception as e:
                            pass

                    # Method 2: Try by ID
                    if entity is None and channel_sub.channel_id:
                        try:
                            channel_id = int(channel_sub.channel_id)
                            entity = await self.user_client.get_entity(channel_id)
                        except Exception as e:
                            pass

                    # Method 3: Check dialogs
                    if entity is None:
                        try:
                            async for dialog in self.user_client.iter_dialogs(limit=200):
                                if str(dialog.id) == str(channel_sub.channel_id):
                                    entity = dialog.entity
                                    break
                        except Exception as e:
                            pass

                    # Establish update stream by fetching recent messages
                    if entity:
                        try:
                            messages = []
                            async for msg in self.user_client.iter_messages(entity, limit=1):
                                messages.append(msg)

                            self.monitored_channels.append(channel_sub)
                        except Exception as e:
                            self.monitored_channels.append(channel_sub)
                    else:
                        self.monitored_channels.append(channel_sub)

                except Exception as e:
                    self.monitored_channels.append(channel_sub)

        except Exception as e:
            pass

    async def stop(self):
        """Stop the trading bot"""
        if not self.running:
            return

        try:
            # Send shutdown notification via BOT
            try:
                await self.bot_client.send_message(
                    OWNER_CHAT_ID,
                    "🛑 **Trading Bot Stopped**\n\n"
                    "Shutting down safely."
                )
            except Exception as e:
                pass

            # Close API connections
            await dbotx_client.close_session()

            # Unsubscribe from verification listener
            if self.verification_channel:
                try:
                    await self.verification_channel.unsubscribe()
                except Exception as e:
                    pass

            # Stop both Telethon clients
            if self.bot_client:
                await self.bot_client.disconnect()

            if self.user_client:
                await self.user_client.disconnect()

            self.running = False

            # Give time for cleanup
            await asyncio.sleep(0.5)

        except Exception as e:
            pass
        finally:
            # Force cleanup any remaining tasks
            try:
                pending = [task for task in asyncio.all_tasks() if not task.done()]
                if pending:
                    for task in pending:
                        task.cancel()
                    await asyncio.gather(*pending, return_exceptions=True)
            except Exception as e:
                pass

    async def run_forever(self):
        """Run bot indefinitely"""
        try:
            await self.bot_client.run_until_disconnected()
        except KeyboardInterrupt:
            logger.info("📝 Received keyboard interrupt")
        except Exception as e:
            logger.error(f"Runtime error: {e}")
        finally:
            await self.stop()


# Global bot instance
bot = UltraFastTradingBot()


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}")
    asyncio.create_task(bot.stop())


async def main():
    """Main entry point"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Initialize bot
        print("🚀 Initializing bot...")
        await asyncio.wait_for(bot.initialize(), timeout=30.0)
        print("✅ Bot initialized successfully")

        # Start bot with timeout
        print("🔄 Starting bot...")
        try:
            await asyncio.wait_for(bot.start(), timeout=60.0)
            print("✅ Bot started successfully")
        except asyncio.TimeoutError:
            print("⚠️ Bot start timed out - continuing in limited mode")
            bot.running = True

        # Run forever
        print("🎯 Bot is now running and listening for messages...")
        await bot.run_forever()

    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Fatal error in main: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        sys.exit(1)