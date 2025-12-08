#!/usr/bin/env python3
"""
MTProto Telegram Scraper - Ultra-Fast Token Detection
Direct MTProto connection for 275ms trade execution
"""

import asyncio
import logging
import signal
import sys
import time
import os
from typing import Dict, List, Optional
from telethon import TelegramClient, events
from telethon.tl.types import Message
from telethon.errors import SessionPasswordNeededError, ApiIdInvalidError

# Import existing components
from config import API_ID, API_HASH
from models import storage, ChannelSubscription, FilterMode
from api_client import client as dbotx_client
from utils import detect_contract_address, generate_order_id, PerformanceTimer
from config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# MTProto Client Configuration
SCRAPER_SESSION = config('SCRAPER_SESSION', default='scraper_session')
SCRAPER_PHONE = config('SCRAPER_PHONE', default='')
SCRAPER_PASSWORD = config('SCRAPER_PASSWORD', default='')

class MTProtoScraper:
    """Ultra-fast MTProto scraper for real-time token detection"""

    def __init__(self):
        self.client: Optional[TelegramClient] = None
        self.running = False
        self.monitored_channels: Dict[int, List[ChannelSubscription]] = {}
        self.last_update = time.time()

    async def initialize(self):
        """Initialize MTProto client and authenticate"""
        logger.info("🔥 Initializing MTProto Scraper...")

        # Create Telethon client for direct MTProto access
        self.client = TelegramClient(
            SCRAPER_SESSION,
            API_ID,
            API_HASH,
            system_version="4.16.30-vxCUSTOM",
            device_model="Desktop",
            app_version="1.0",
            lang_code="en",
            system_lang_code="en-US"
        )

        # Start client
        await self.client.start()

        # Check if authenticated
        if not await self.client.is_user_authorized():
            logger.error("❌ MTProto client not authorized! Please authenticate first.")
            await self._authenticate()

        # Get client info
        me = await self.client.get_me()
        logger.info(f"✅ MTProto Scraper authenticated as {me.first_name} (ID: {me.id})")

        # Initialize DBOTX API client
        await dbotx_client.start_session()

        logger.info("✅ MTProto Scraper initialized successfully")

    async def _authenticate(self):
        """Authenticate MTProto client"""
        if not SCRAPER_PHONE:
            logger.error("❌ SCRAPER_PHONE not configured! Set it in .env")
            sys.exit(1)

        try:
            await self.client.send_code_request(SCRAPER_PHONE)
            code = input("Enter verification code: ")
            await self.client.sign_in(SCRAPER_PHONE, code)
        except SessionPasswordNeededError:
            if SCRAPER_PASSWORD:
                await self.client.sign_in(password=SCRAPER_PASSWORD)
            else:
                password = input("Enter 2FA password: ")
                await self.client.sign_in(password=password)

        logger.info("✅ MTProto authentication successful")

    async def start_monitoring(self):
        """Start monitoring configured channels"""
        if self.running:
            logger.warning("Scraper is already running")
            return

        try:
            logger.info("🚀 Starting channel monitoring...")
            self.running = True

            # Load channel configurations
            await self._update_channel_list()

            # Register message handler for all channels
            @self.client.on(events.NewMessage())
            async def message_handler(event):
                await self._handle_new_message(event)

            # Start periodic channel list updates
            asyncio.create_task(self._periodic_update())

            logger.info("🎯 MTProto Scraper is now monitoring channels!")
            logger.info(f"📊 Monitoring {len(self.monitored_channels)} channels")

            # Keep running
            await self.client.run_until_disconnected()

        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            self.running = False
            raise

    async def _update_channel_list(self):
        """Update list of channels to monitor with proper entity resolution"""
        try:
            # Get all active channels from storage
            active_channels = storage.get_all_active_channels()

            # Group by channel ID
            self.monitored_channels.clear()
            valid_channels = []
            
            for subscription in active_channels:
                channel_id = subscription.channel_id
                
                # Skip test/placeholder channels
                if channel_id == -1001234567890:
                    logger.warning(f"⚠️ Skipping test channel {channel_id} - removing from database")
                    storage.remove_channel_subscription(subscription.user_id, channel_id)
                    continue
                
                # Try to resolve channel entity properly
                if await self._validate_and_cache_channel(channel_id, subscription):
                    if channel_id not in self.monitored_channels:
                        self.monitored_channels[channel_id] = []
                    self.monitored_channels[channel_id].append(subscription)
                    valid_channels.append(subscription)
                else:
                    logger.warning(f"⚠️ Channel {channel_id} not accessible - removing subscription")
                    storage.remove_channel_subscription(subscription.user_id, channel_id)

            logger.info(f"🔄 Updated channel list: {len(self.monitored_channels)} valid channels")

        except Exception as e:
            logger.error(f"Error updating channel list: {e}")

    async def _validate_and_cache_channel(self, channel_id: int, subscription: ChannelSubscription) -> bool:
        """Validate and cache channel entity using proper Telegram entity resolution"""
        try:
            # First, try to get the entity from cache (session)
            try:
                entity = await self.client.get_input_entity(channel_id)
                logger.debug(f"✅ Channel {channel_id} found in cache")
                return True
            except ValueError:
                # Entity not in cache, need to encounter it first
                logger.debug(f"🔍 Channel {channel_id} not in cache, attempting to resolve...")
                
            # Try different methods to encounter the entity
            # Method 1: Try by username if available
            if subscription.channel_username:
                try:
                    entity = await self.client.get_entity(subscription.channel_username)
                    if entity.id == abs(channel_id):  # Handle negative channel IDs
                        logger.info(f"✅ Channel {channel_id} resolved via username @{subscription.channel_username}")
                        return True
                except Exception as e:
                    logger.debug(f"Username resolution failed for {subscription.channel_username}: {e}")
            
            # Method 2: Check if in dialogs
            try:
                async for dialog in self.client.iter_dialogs():
                    if dialog.entity.id == abs(channel_id):
                        logger.info(f"✅ Channel {channel_id} found in dialogs: {dialog.entity.title}")
                        return True
            except Exception as e:
                logger.debug(f"Dialog search failed: {e}")
            
            # Method 3: If all else fails, the channel is not accessible
            logger.warning(f"❌ Channel {channel_id} ({subscription.channel_title}) is not accessible")
            logger.info(f"💡 To fix this, user needs to:")
            logger.info(f"   1. Join the channel manually in Telegram")
            logger.info(f"   2. Send a message to the bot from that channel")
            logger.info(f"   3. Or provide the channel username/invite link")
            
            return False
            
        except Exception as e:
            logger.error(f"Error validating channel {channel_id}: {e}")
            return False

    async def _periodic_update(self):
        """Periodically update channel configurations"""
        while self.running:
            try:
                await asyncio.sleep(30)  # Update every 30 seconds
                await self._update_channel_list()
                self.last_update = time.time()

                # Heartbeat to confirm scraper is monitoring
                logger.info(f"💓 MTProto Scraper Heartbeat: Monitoring {len(self.monitored_channels)} channels")

                # Log active subscriptions for verification
                total_subs = sum(len(subs) for subs in self.monitored_channels.values())
                logger.info(f"📊 Active subscriptions: {total_subs}")

            except Exception as e:
                logger.error(f"Error in periodic update: {e}")

    async def _handle_new_message(self, event):
        """Handle new messages from monitored channels"""
        try:
            message = event.message

            # Import Telethon types for proper type checking
            from telethon.tl.types import PeerChannel, PeerChat

            # Filter out non-channel messages (only process channels and supergroups)
            if not isinstance(message.peer_id, (PeerChannel, PeerChat)):
                logger.debug("Skipping non-channel message (direct message or other type).")
                return

            # Get channel ID based on peer type
            if hasattr(message.peer_id, 'channel_id'):
                channel_id = message.peer_id.channel_id
            elif hasattr(message.peer_id, 'chat_id'):
                channel_id = message.peer_id.chat_id
            else:
                logger.debug("Skipping message - no channel or chat ID found.")
                return

            # Debug: Log all incoming messages
            logger.debug(f"📨 New message from channel {channel_id}: {message.text[:100] if message.text else 'No text'}")

            # Check if message is from a monitored channel
            if channel_id not in self.monitored_channels:
                logger.debug(f"🔍 Channel {channel_id} not in monitored list")
                return

            subscriptions = self.monitored_channels[channel_id]

            logger.info(f"📡 Processing message from monitored channel {channel_id} ({len(subscriptions)} subscriptions)")

            # Process message for each subscription
            for subscription in subscriptions:
                logger.debug(f"🔍 Checking message for user {subscription.user_id}")
                if await self._should_process_message(message, subscription):
                    logger.info(f"✅ Message passed filters for {subscription.channel_title}")
                    await self._process_token_message(message, subscription)
                else:
                    logger.debug(f"❌ Message filtered out for {subscription.channel_title}")

        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def _should_process_message(self, message: Message, subscription: ChannelSubscription) -> bool:
        """Check if message should be processed based on filters"""
        try:
            # Check filter mode
            if subscription.filter_mode == FilterMode.ALL_MESSAGES:
                return True

            elif subscription.filter_mode == FilterMode.ADMIN_ONLY:
                # Check if sender is admin
                sender = await message.get_sender()
                if not sender:
                    return False

                # Get channel admins (cached for performance)
                try:
                    entity = await self.client.get_entity(subscription.channel_id)
                    async for participant in self.client.iter_participants(entity, filter=lambda p: p.admin_rights):
                        if participant.id == sender.id:
                            return True
                    return False
                except:
                    return False

            elif subscription.filter_mode == FilterMode.SPECIFIC_USERS:
                # Check if sender is in allowed list
                sender = await message.get_sender()
                if not sender:
                    return False
                return sender.id in subscription.allowed_user_ids

            return False

        except Exception as e:
            logger.error(f"Error checking message filter: {e}")
            return False

    async def _process_token_message(self, message: Message, subscription: ChannelSubscription):
        """Process message for token contract addresses"""
        try:
            # Extract text from message
            text = message.text or ""
            if not text:
                return

            with PerformanceTimer("contract_detection"):
                contract_info = detect_contract_address(text)

            if not contract_info:
                return  # No contract found

            chain, address = contract_info

            # Get user settings
            user = storage.get_user(subscription.user_id)
            if not user or not user.wallet_id:
                logger.warning(f"User {subscription.user_id} not configured for trading")
                return

            # Determine buy amount
            amount = subscription.custom_buy_amount or user.get_setting('amountOrPercent', 0.1)

            # Generate order ID
            order_id = generate_order_id()

            # Log trade attempt
            logger.info(f"🎯 TOKEN DETECTED: {address} on {chain.upper()} from channel {subscription.channel_title}")

            # Create order record
            order = storage.create_order(
                order_id=order_id,
                user_id=subscription.user_id,
                chain=chain,
                pair=address,
                order_type='buy',
                amount=amount,
                settings=user.settings.copy()
            )

            # Execute trade asynchronously for maximum speed
            asyncio.create_task(self._execute_ultra_fast_trade(
                order_id, subscription.user_id, chain, address, amount, 
                user.settings, user.wallet_id, subscription
            ))

        except Exception as e:
            logger.error(f"Error processing token message: {e}")

    async def _execute_ultra_fast_trade(self, order_id: str, user_id: int, chain: str, 
                                      address: str, amount: float, user_settings: dict, 
                                      wallet_id: str, subscription: ChannelSubscription):
        """Execute ultra-fast trade via DBOTX API"""
        start_time = time.time()

        try:
            logger.info(f"⚡ EXECUTING TRADE: {order_id} | {chain.upper()} | {address}")

            # Execute trade via DBOTX API
            with PerformanceTimer("api_ultra_fast_buy"):
                response = await dbotx_client.fast_buy(
                    chain=chain,
                    pair=address,
                    wallet_id=wallet_id,
                    amount=amount,
                    user_settings=user_settings
                )

            response_time = (time.time() - start_time) * 1000

            if response.get('err', True):
                error_msg = response.get('message', 'Unknown error')
                storage.update_order_status(order_id, 'failed', error_msg)

                logger.error(f"❌ TRADE FAILED: {order_id} | {error_msg} | {response_time:.0f}ms")

                # Send failure notification
                await self._send_notification(
                    user_id,
                    f"❌ **TRADE FAILED**\\n\\n"
                    f"🆔 Order: `{order_id}`\\n"
                    f"🔗 Contract: `{address[:8]}...{address[-4:]}`\\n"
                    f"⚠️ Error: {error_msg}\\n"
                    f"⏱️ Response: {response_time:.0f}ms"
                )
            else:
                trade_id = response.get('res', {}).get('id', 'unknown')
                storage.update_order_status(order_id, 'completed')

                # Update subscription stats
                subscription.total_trades += 1
                subscription.last_message_at = time.time()

                logger.info(f"✅ TRADE SUCCESS: {order_id} | {response_time:.0f}ms | TX: {trade_id}")

                # Send success notification
                await self._send_notification(
                    user_id,
                    f"✅ **BOUGHT {address[:8]}...{address[-4:]} in {response_time:.0f}ms**\\n\\n"
                    f"🌐 Chain: {chain.upper()}\\n"
                    f"💰 Amount: {amount}\\n"
                    f"📡 From: {subscription.channel_title}\\n"
                    f"🆔 Order: `{order_id}`\\n"
                    f"🔗 Trade: `{trade_id}`"
                )

        except Exception as e:
            error_msg = str(e)
            response_time = (time.time() - start_time) * 1000
            storage.update_order_status(order_id, 'failed', error_msg)

            logger.error(f"❌ TRADE ERROR: {order_id} | {error_msg} | {response_time:.0f}ms")

            # Send error notification
            await self._send_notification(
                user_id,
                f"❌ **TRADE ERROR**\\n\\n"
                f"🆔 Order: `{order_id}`\\n"
                f"⚠️ Error: {error_msg}\\n"
                f"⏱️ Time: {response_time:.0f}ms"
            )

    async def _send_notification(self, user_id: int, message: str):
        """Send notification to user via MTProto client"""
        try:
            await self.client.send_message(user_id, message, parse_mode='markdown')
        except Exception as e:
            logger.error(f"Failed to send notification to user {user_id}: {e}")

    async def stop(self):
        """Stop the scraper"""
        if not self.running:
            return

        logger.info("🔄 Stopping MTProto scraper...")
        self.running = False

        try:
            # Close DBOTX API connection
            await dbotx_client.close_session()

            # Disconnect Telethon client
            if self.client:
                await self.client.disconnect()

            logger.info("✅ MTProto scraper stopped successfully")

        except Exception as e:
            logger.error(f"Error stopping scraper: {e}")

# Global scraper instance
scraper = MTProtoScraper()

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}")
    asyncio.create_task(scraper.stop())

async def main():
    """Main entry point"""
    print("🔥 MTProto Ultra-Fast Scraper v1.0")
    print("=" * 50)

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Initialize and start scraper
        await scraper.initialize()
        await scraper.start_monitoring()

    except KeyboardInterrupt:
        logger.info("📝 Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        logger.info("🔚 Scraper shutdown complete")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Scraper stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)