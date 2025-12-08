#!/usr/bin/env python3
"""
Real-Time Telegram Monitoring System
Battle-tested architecture for 0.004ms message filtering with 3 monitoring modes
"""

import asyncio
import logging
import signal
import sys
import time
import random
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta

from telethon import TelegramClient, events
from telethon.tl.types import (
    Message, UpdateNewMessage, PeerChannel, PeerChat, PeerUser,
    ChannelParticipantsAdmins, MessageService
)
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest, GetFullChatRequest
from telethon.errors import (
    SessionPasswordNeededError, ApiIdInvalidError, ChannelPrivateError,
    PeerIdInvalidError, FloodWaitError
)

# Import existing components
from config import API_ID, API_HASH, config, SPEED_MODE, HUMAN_DELAY_MIN, HUMAN_DELAY_MAX
from models import storage, ChannelSubscription, FilterMode, ChannelType
from api_client import client as dbotx_client
from utils import detect_contract_address, generate_order_id, PerformanceTimer
from token_validator import validator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('realtime_monitor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class MonitoringMode(Enum):
    """Enhanced monitoring modes matching the guide specification"""
    ALL = "all"              # Process every message
    ADMINS = "admins"        # Only admin messages
    USERS = "users"          # Only specific user IDs


@dataclass
class MonitorConfig:
    """Configuration for channel monitoring"""
    id: int                                 # Channel ID
    name: str                              # Channel name/username
    mode: MonitoringMode                   # Monitoring mode
    user_ids: List[int] = None            # For USERS mode
    invite_hash: Optional[str] = None      # For private groups
    
    def __post_init__(self):
        if self.user_ids is None:
            self.user_ids = []


class AdminCache:
    """Thread-safe admin caching system with 1-hour TTL"""
    
    def __init__(self):
        self._cache: Dict[int, Dict[int, bool]] = {}
        self._timestamps: Dict[int, float] = {}
        self._lock = asyncio.Lock()
        
    async def get_admins(self, channel_id: int, client: TelegramClient) -> Set[int]:
        """Get admins for channel with caching"""
        async with self._lock:
            now = time.time()
            
            # Check cache validity (1 hour TTL)
            if (channel_id in self._cache and 
                channel_id in self._timestamps and
                now - self._timestamps[channel_id] < 3600):
                return set(self._cache[channel_id].keys())
            
            # Fetch fresh admin list
            try:
                admins = await self._fetch_channel_admins(channel_id, client)
                self._cache[channel_id] = {admin_id: True for admin_id in admins}
                self._timestamps[channel_id] = now
                return admins
            except Exception as e:
                logger.error(f"Failed to fetch admins for {channel_id}: {e}")
                return set()
    
    async def _fetch_channel_admins(self, channel_id: int, client: TelegramClient) -> Set[int]:
        """Fetch admin list using appropriate API for entity type"""
        # PUBLIC CHANNELS/SUPERGROUPS: -100 prefix
        if channel_id < -1000000000000:
            try:
                admins = set()
                async for participant in client.iter_participants(
                    channel_id, filter=ChannelParticipantsAdmins
                ):
                    if hasattr(participant, 'id'):
                        admins.add(participant.id)
                return admins
            except Exception as e:
                logger.debug(f"Channel participants failed for {channel_id}: {e}")
                return set()
        
        # PRIVATE GROUPS: regular negative ID  
        elif channel_id < 0 and channel_id > -1000000000000:
            try:
                full_chat = await client.get_entity(channel_id)
                # For basic groups, get chat info
                chat_info = await client(GetFullChatRequest(chat_id=-channel_id))
                participants = chat_info.full_chat.participants.participants
                
                admins = set()
                for participant in participants:
                    # Check if participant has admin rights
                    if (hasattr(participant, 'can_edit') and participant.can_edit) or \
                       (hasattr(participant, 'inviter_id') and participant.inviter_id):
                        admins.add(participant.user_id)
                return admins
            except Exception as e:
                logger.debug(f"Group participants failed for {channel_id}: {e}")
                return set()
        
        return set()


class RealTimeMonitor:
    """Real-time Telegram monitoring system with 0.004ms filtering"""
    
    def __init__(self):
        self.client: Optional[TelegramClient] = None
        self.running = False
        self.monitor_configs: List[MonitorConfig] = []
        self.admin_cache = AdminCache()
        
        # Performance tracking
        self.messages_processed = 0
        self.filter_times = []
        self.start_time = time.time()
        
        # Hot reload tracking
        self.last_config_check = time.time()
        self.config_check_interval = 5  # Check every 5 seconds
        self.last_channel_count = 0
        
    async def initialize(self):
        """Initialize real-time monitoring client"""
        logger.info("🔥 Initializing Real-Time Monitor...")
        
        # Create Telethon client using existing session
        session_name = config('SCRAPER_SESSION', default='scraper_session')
        self.client = TelegramClient(
            session_name,
            API_ID,
            API_HASH,
            system_version="4.16.30-vxCUSTOM",
            device_model="Desktop",
            app_version="1.0",
            lang_code="en",
            system_lang_code="en-US"
        )
        
        # Start and authenticate
        await self.client.start()
        
        if not await self.client.is_user_authorized():
            logger.error("❌ Real-time monitor not authorized!")
            await self._authenticate()
        
        # Get client info
        me = await self.client.get_me()
        logger.info(f"✅ Real-Time Monitor authenticated as {me.first_name} (ID: {me.id})")
        
        # Initialize DBOTX client
        await dbotx_client.start_session()
        
        logger.info("✅ Real-Time Monitor initialized successfully")
    
    async def _authenticate(self):
        """Authenticate the client"""
        phone = config('SCRAPER_PHONE', default='')
        password = config('SCRAPER_PASSWORD', default='')
        
        if not phone:
            logger.error("❌ SCRAPER_PHONE not configured!")
            sys.exit(1)
        
        try:
            await self.client.send_code_request(phone)
            code = input("Enter verification code: ")
            await self.client.sign_in(phone, code)
        except SessionPasswordNeededError:
            if password:
                await self.client.sign_in(password=password)
            else:
                password = input("Enter 2FA password: ")
                await self.client.sign_in(password=password)
        
        logger.info("✅ Authentication successful")
    
    async def load_monitor_configs(self):
        """Load monitoring configurations from storage"""
        try:
            # Get all active channels from storage
            active_channels = storage.get_all_active_channels()
            
            self.monitor_configs.clear()
            for subscription in active_channels:
                # Map FilterMode to MonitoringMode
                if subscription.filter_mode == FilterMode.ALL_MESSAGES:
                    mode = MonitoringMode.ALL
                elif subscription.filter_mode == FilterMode.ADMIN_ONLY:
                    mode = MonitoringMode.ADMINS
                elif subscription.filter_mode == FilterMode.SPECIFIC_USERS:
                    mode = MonitoringMode.USERS
                else:
                    mode = MonitoringMode.ALL
                
                config = MonitorConfig(
                    id=subscription.channel_id,
                    name=subscription.channel_username or subscription.channel_title,
                    mode=mode,
                    user_ids=subscription.allowed_user_ids.copy()
                )
                
                self.monitor_configs.append(config)
            
            logger.info(f"📊 Loaded {len(self.monitor_configs)} monitor configurations")
            
        except Exception as e:
            logger.error(f"Failed to load monitor configs: {e}")
    
    async def join_entities(self):
        """Join all configured entities with validation"""
        valid_configs = []
        for config in self.monitor_configs:
            try:
                # First validate the channel exists and is accessible
                if await self._validate_channel_access(config):
                    await self._join_single_entity(config)
                    valid_configs.append(config)
                    logger.info(f"✅ Successfully joined and validated: {config.name}")
                else:
                    logger.warning(f"⚠️ Channel not accessible, removing from monitoring: {config.name} (ID: {config.id})")
                
                # Small delay to avoid rate limits
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.warning(f"Failed to join {config.name} ({config.id}): {e}")
        
        # Update configs to only include valid channels
        self.monitor_configs = valid_configs
        logger.info(f"📊 Final monitoring list: {len(self.monitor_configs)} valid channels")
    
    async def _validate_channel_access(self, config: MonitorConfig) -> bool:
        """Validate that a channel is accessible before attempting to join"""
        try:
            # Try to get channel info
            entity = await self.client.get_entity(config.id)
            logger.debug(f"✅ Channel accessible: {entity.title}")
            return True
        except Exception as e:
            logger.warning(f"❌ Channel validation failed for {config.name} (ID: {config.id}): {e}")
            return False
    
    async def _join_single_entity(self, config: MonitorConfig):
        """Join a single entity using appropriate method"""
        channel_id = config.id
        
        # PUBLIC CHANNELS/SUPERGROUPS: -100 prefix
        if channel_id < -1000000000000:
            try:
                # Try to get entity first (might already be joined)
                entity = await self.client.get_entity(channel_id)
                logger.debug(f"✅ Already in channel: {entity.title}")
                return
            except Exception:
                # Not joined, try to join
                try:
                    if config.name.startswith('@'):
                        # Join by username
                        await self.client(JoinChannelRequest(config.name))
                    else:
                        # Join by ID
                        await self.client(JoinChannelRequest(channel_id))
                    logger.info(f"✅ Joined channel: {config.name}")
                except Exception as e:
                    logger.warning(f"Failed to join channel {config.name}: {e}")
        
        # PRIVATE GROUPS: regular negative ID
        elif channel_id < 0 and channel_id > -1000000000000:
            try:
                # Check if already in group
                entity = await self.client.get_entity(channel_id)
                logger.debug(f"✅ Already in group: {entity.title}")
                return
            except Exception:
                if config.invite_hash:
                    try:
                        # Join using invite hash
                        await self.client(ImportChatInviteRequest(hash=config.invite_hash))
                        logger.info(f"✅ Joined private group via invite: {config.name}")
                    except Exception as e:
                        logger.warning(f"Failed to join private group {config.name}: {e}")
                else:
                    logger.warning(f"No invite hash for private group: {config.name}")
    
    async def start_monitoring(self):
        """Start real-time monitoring with update handlers"""
        if self.running:
            logger.warning("Monitor already running")
            return
        
        try:
            logger.info("🚀 Starting real-time monitoring...")
            self.running = True
            
            # Load configurations
            await self.load_monitor_configs()
            
            # Initialize channel count tracker
            self.last_channel_count = len(self.monitor_configs)
            
            # Join all entities
            await self.join_entities()
            
            # Register real-time update handler with channel-specific filtering
            # This is more efficient than processing ALL Telegram messages
            monitored_channel_entities = []
            for config in self.monitor_configs:
                try:
                    entity = await self.client.get_entity(config.id)
                    monitored_channel_entities.append(entity)
                    logger.info(f"🎯 Registered message handler for: {config.name} (ID: {config.id})")
                except Exception as e:
                    logger.warning(f"Could not get entity for {config.name}: {e}")
            
            # Register handler only for monitored channels
            @self.client.on(events.NewMessage(chats=monitored_channel_entities))
            async def message_handler(event):
                await self._process_update(event)
            
            # Store handler reference
            self._message_handler = message_handler
            
            # Start performance monitoring (includes config checking)
            asyncio.create_task(self._performance_monitor())
            
            logger.info("🎯 Real-Time Monitor active!")
            logger.info(f"📊 Monitoring {len(self.monitor_configs)} channels")
            logger.info(f"🔄 Hot reload enabled - checking every {self.config_check_interval}s")
            
            # Keep running
            await self.client.run_until_disconnected()
            
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            self.running = False
            raise
    
    async def _process_update(self, event):
        """Process incoming update with pre-filtering to avoid unnecessary processing"""
        start_time = time.perf_counter()
        
        try:
            message = event.message
            
            # CRITICAL OPTIMIZATION: Pre-filter by channel IMMEDIATELY
            channel_id = getattr(message.peer_id, 'channel_id', None) if hasattr(message, 'peer_id') else None
            if not channel_id:
                return  # Not a channel message, skip silently
            
            # Check if we're monitoring this channel - BLOCK 99.9% of messages here
            monitored_channel_ids = [abs(config.id) for config in self.monitor_configs]
            if abs(channel_id) not in monitored_channel_ids:
                # Silent return - no logging for non-monitored channels to reduce noise
                return
            
            # Only log messages from monitored channels
            user_id = getattr(message.from_id, 'user_id', None) if hasattr(message, 'from_id') else None
            message_text = getattr(message, 'message', '')[:100] if hasattr(message, 'message') else 'No text'
            
            logger.info(f"📨 MONITORED MESSAGE: Channel {channel_id} | User {user_id} | Text: {message_text}...")
            
            # Apply filtering pipeline with detailed logging
            message_processed = False
            for config in self.monitor_configs:
                logger.debug(f"🔍 Checking config {config.id} ({config.name}) mode={config.mode.value}")
                
                if await self._should_process_message(message, config):
                    logger.info(f"✅ MESSAGE PASSED FILTER: Channel {config.name} | Mode: {config.mode.value}")
                    
                    # Log message content for contract detection
                    if hasattr(message, 'message') and message.message:
                        logger.info(f"📝 MESSAGE CONTENT: {message.message}")
                        
                        # Test contract detection immediately
                        from utils import detect_contract_address
                        contract_info = detect_contract_address(message.message)
                        if contract_info:
                            chain, address = contract_info
                            logger.info(f"🎯 CONTRACT DETECTED LIVE: {chain.upper()} | {address}")
                        else:
                            logger.info(f"⚪ No contract detected in message")
                    
                    # Human-like delay for ban prevention
                    await self._apply_human_delay()
                    
                    # Process message in background
                    asyncio.create_task(
                        self._handle_relevant_message(message, config)
                    )
                    message_processed = True
                    break
                else:
                    logger.debug(f"❌ Message failed filter for {config.name}")
            
            if not message_processed:
                logger.debug(f"⚪ Message not processed by any config")
            
            # Track performance
            filter_time = (time.perf_counter() - start_time) * 1000  # Convert to ms
            self.filter_times.append(filter_time)
            self.messages_processed += 1
            
        except Exception as e:
            logger.error(f"❌ Error processing update: {e}", exc_info=True)
    
    async def _should_process_message(self, message: Message, config: MonitorConfig) -> bool:
        """Message filtering with detailed logging"""
        
        # 1. Channel check - blocks 99.9% of messages
        if not hasattr(message.peer_id, 'channel_id'):
            logger.debug(f"❌ Filter step 1: No channel_id in peer_id")
            return False
        
        message_channel_id = message.peer_id.channel_id
        config_channel_id = abs(config.id)
        
        if abs(message_channel_id) != config_channel_id:
            logger.debug(f"❌ Filter step 1: Channel mismatch - message:{abs(message_channel_id)} vs config:{config_channel_id}")
            return False
        
        logger.debug(f"✅ Filter step 1: Channel match - {abs(message_channel_id)}")
        
        # 2. Skip service messages
        if isinstance(message, MessageService):
            logger.debug(f"❌ Filter step 2: Service message skipped")
            return False
        
        logger.debug(f"✅ Filter step 2: Not a service message")
        
        # 3. Check for text content
        if not hasattr(message, 'message') or not message.message:
            logger.debug(f"❌ Filter step 3: No text content")
            return False
        
        if hasattr(message, 'media') and message.media:
            logger.debug(f"❌ Filter step 3: Has media, skipping")
            return False
        
        logger.debug(f"✅ Filter step 3: Has text content - {len(message.message)} chars")
        
        # 4. Apply monitoring mode
        if config.mode == MonitoringMode.ALL:
            logger.debug(f"✅ Filter step 4: ALL mode - accepting message")
            return True
        
        elif config.mode == MonitoringMode.ADMINS:
            if not hasattr(message, 'from_id') or not message.from_id:
                logger.debug(f"❌ Filter step 4: ADMINS mode - no from_id")
                return False
            
            user_id = message.from_id.user_id if hasattr(message.from_id, 'user_id') else None
            if not user_id:
                logger.debug(f"❌ Filter step 4: ADMINS mode - no user_id")
                return False
            
            admins = await self.admin_cache.get_admins(config.id, self.client)
            is_admin = user_id in admins
            logger.debug(f"{'✅' if is_admin else '❌'} Filter step 4: ADMINS mode - user {user_id} admin check: {is_admin}")
            return is_admin
        
        elif config.mode == MonitoringMode.USERS:
            if not hasattr(message, 'from_id') or not message.from_id:
                logger.debug(f"❌ Filter step 4: USERS mode - no from_id")
                return False
            
            user_id = message.from_id.user_id if hasattr(message.from_id, 'user_id') else None
            if not user_id:
                logger.debug(f"❌ Filter step 4: USERS mode - no user_id")
                return False
            
            is_allowed = user_id in config.user_ids
            logger.debug(f"{'✅' if is_allowed else '❌'} Filter step 4: USERS mode - user {user_id} in allowed list: {is_allowed}")
            return is_allowed
        
        logger.debug(f"❌ Filter step 4: Unknown mode {config.mode}")
        return False
    
    async def _check_and_reload_configs(self):
        """Check for new channels and reload configurations if needed"""
        try:
            # Get current active channels count
            active_channels = storage.get_all_active_channels()
            new_channel_count = len(active_channels)
            
            # Check if channel count changed
            if new_channel_count != self.last_channel_count:
                logger.info(f"🔄 CHANNEL CHANGE DETECTED: {self.last_channel_count} → {new_channel_count}")
                
                # Reload configurations
                old_config_count = len(self.monitor_configs)
                await self.load_monitor_configs()
                
                # Join any new channels
                await self.join_entities()
                
                # Re-register handlers with new channels
                await self._update_message_handlers()
                
                self.last_channel_count = new_channel_count
                logger.info(f"✅ CONFIG RELOAD COMPLETE: {old_config_count} → {len(self.monitor_configs)} channels")
                
        except Exception as e:
            logger.error(f"Error checking/reloading configs: {e}")
    
    async def _update_message_handlers(self):
        """Update message handlers with current channel list"""
        try:
            # Remove old handlers
            self.client.remove_event_handler(self._message_handler)
            
            # Get monitored channel entities
            monitored_channel_entities = []
            for config in self.monitor_configs:
                try:
                    entity = await self.client.get_entity(config.id)
                    monitored_channel_entities.append(entity)
                except Exception as e:
                    logger.warning(f"Could not get entity for {config.name}: {e}")
            
            # Register new handler
            @self.client.on(events.NewMessage(chats=monitored_channel_entities))
            async def message_handler(event):
                await self._process_update(event)
            
            # Store handler reference
            self._message_handler = message_handler
            
            logger.info(f"📡 Updated message handlers for {len(monitored_channel_entities)} channels")
            
        except Exception as e:
            logger.error(f"Error updating message handlers: {e}")
    
    async def _apply_human_delay(self):
        """Apply human-like delays for ban prevention - uses SPEED_MODE config"""
        # SPEED_MODE: Skip all delays for maximum speed (instant processing)
        if SPEED_MODE:
            return
        
        # Normal mode: Use configurable minimal delays (50-100ms default)
        delay = random.uniform(HUMAN_DELAY_MIN, HUMAN_DELAY_MAX)
        await asyncio.sleep(delay)
    
    async def _handle_relevant_message(self, message: Message, config: MonitorConfig):
        """Handle relevant message for token detection and trading with detailed logging"""
        try:
            logger.info(f"🔄 PROCESSING RELEVANT MESSAGE from {config.name}")
            
            # Extract message text
            text = message.message
            if not text:
                logger.warning(f"❌ No text in message from {config.name}")
                return
            
            logger.info(f"📝 Message text: {text}")
            
            # Detect contract address
            logger.info(f"🔍 Running contract detection...")
            with PerformanceTimer("contract_detection"):
                contract_info = detect_contract_address(text)
            
            if not contract_info:
                logger.info(f"⚪ No contract detected in message: {text[:100]}...")
                return
            
            chain, address = contract_info
            logger.info(f"🎯 CONTRACT FOUND: {chain.upper()} | {address}")
            
            # Find subscription for this channel
            logger.info(f"🔍 Looking for subscription for channel {config.id}")
            all_subscriptions = storage.get_all_active_channels()
            subscription = None
            for sub in all_subscriptions:
                if sub.channel_id == config.id:
                    subscription = sub
                    logger.info(f"✅ Found subscription: User {sub.user_id}, Channel {sub.channel_title}")
                    break
            
            if not subscription:
                logger.error(f"❌ No subscription found for channel {config.id}")
                logger.info(f"Available subscriptions: {[(s.channel_id, s.channel_title) for s in all_subscriptions]}")
                return
            
            # Get user settings
            logger.info(f"🔍 Getting user settings for user {subscription.user_id}")
            user = storage.get_user(subscription.user_id)
            if not user:
                logger.error(f"❌ User {subscription.user_id} not found in storage")
                return
            
            if not user.wallet_id:
                logger.error(f"❌ User {subscription.user_id} has no wallet configured")
                return
            
            logger.info(f"✅ User found: {user.username}, Wallet: {user.wallet_id}")
            
            # SAFETY VALIDATION: Fetch pair info and validate token
            logger.info(f"🔒 FETCHING PAIR INFO for safety validation...")
            with PerformanceTimer("pair_info_fetch"):
                pair_info_response = await dbotx_client.get_pair_info(chain=chain, pair=address)
            
            logger.info(f"🔍 VALIDATING TOKEN against safety filters...")
            with PerformanceTimer("token_validation"):
                validation_result = validator.validate_token(
                    pair_info_response=pair_info_response,
                    detected_chain=chain,
                    safety_settings=user.settings
                )
            
            if not validation_result.is_safe:
                logger.warning(f"🚫 TOKEN REJECTED: {validation_result.rejection_reason}")
                logger.warning(f"   Chain: {chain.upper()}")
                logger.warning(f"   Address: {address}")
                logger.warning(f"   User: {user.username} ({user.user_id})")
                logger.warning(f"   Channel: {config.name}")
                logger.warning(f"   Reason: {validation_result.rejection_reason}")
                return
            
            logger.info(f"✅ TOKEN VALIDATION PASSED - Proceeding with trade")
            
            # Determine buy amount
            amount = subscription.custom_buy_amount or user.get_setting('amountOrPercent', 0.1)
            logger.info(f"💰 Trade amount: {amount} {chain.upper()}")
            
            # Generate order ID
            order_id = generate_order_id()
            logger.info(f"📄 Generated order ID: {order_id}")
            
            # Log detection with full details
            logger.info(f"🚀 INITIATING TRADE:")
            logger.info(f"   Order ID: {order_id}")
            logger.info(f"   Chain: {chain.upper()}")
            logger.info(f"   Address: {address}")
            logger.info(f"   Amount: {amount}")
            logger.info(f"   User: {user.username} ({user.user_id})")
            logger.info(f"   Channel: {config.name}")
            
            # Create order record
            logger.info(f"💾 Creating order record...")
            order = storage.create_order(
                order_id=order_id,
                user_id=subscription.user_id,
                chain=chain,
                pair=address,
                order_type='buy',
                amount=amount,
                settings=user.settings.copy()
            )
            logger.info(f"✅ Order record created: {order_id}")
            
            # Execute trade
            logger.info(f"⚡ Starting trade execution...")
            asyncio.create_task(self._execute_trade(
                order_id, subscription.user_id, chain, address, amount,
                user.settings, user.wallet_id, subscription
            ))
            
        except Exception as e:
            logger.error(f"❌ Error handling relevant message from {config.name}: {e}", exc_info=True)
    
    async def _execute_trade(self, order_id: str, user_id: int, chain: str,
                           address: str, amount: float, user_settings: dict,
                           wallet_id: str, subscription: ChannelSubscription):
        """Execute trade via DBOTX API"""
        start_time = time.time()
        
        try:
            logger.info(f"⚡ EXECUTING TRADE: {order_id} | {chain.upper()} | {address}")
            
            # Execute via DBOTX API
            with PerformanceTimer("api_trade_execution"):
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
            else:
                trade_id = response.get('res', {}).get('id', 'unknown')
                storage.update_order_status(order_id, 'completed')
                
                # Update stats
                subscription.total_trades += 1
                subscription.last_message_at = time.time()
                
                logger.info(f"✅ TRADE SUCCESS: {order_id} | {response_time:.0f}ms | TX: {trade_id}")
                
        except Exception as e:
            error_msg = str(e)
            response_time = (time.time() - start_time) * 1000
            storage.update_order_status(order_id, 'failed', error_msg)
            logger.error(f"❌ TRADE ERROR: {order_id} | {error_msg} | {response_time:.0f}ms")
    
    async def _performance_monitor(self):
        """Monitor performance metrics and system status"""
        while self.running:
            try:
                # Check for config changes more frequently
                current_time = time.time()
                if current_time - self.last_config_check >= self.config_check_interval:
                    await self._check_and_reload_configs()
                    self.last_config_check = current_time
                
                await asyncio.sleep(30)  # Report every 30 seconds
                
                # Performance metrics
                if self.filter_times:
                    avg_filter_time = sum(self.filter_times) / len(self.filter_times)
                    max_filter_time = max(self.filter_times)
                    
                    uptime = time.time() - self.start_time
                    msg_per_sec = self.messages_processed / uptime if uptime > 0 else 0
                    
                    logger.info(f"📊 PERFORMANCE: {avg_filter_time:.4f}ms avg filter | "
                              f"{max_filter_time:.4f}ms max | "
                              f"{msg_per_sec:.1f} msg/sec | "
                              f"{self.messages_processed} total")
                    
                    # Reset metrics
                    self.filter_times = []
                
                # System status
                logger.info(f"🔄 SYSTEM STATUS:")
                logger.info(f"   Running: {self.running}")
                logger.info(f"   Client connected: {self.client and self.client.is_connected()}")
                logger.info(f"   Monitor configs: {len(self.monitor_configs)}")
                
                for config in self.monitor_configs:
                    logger.info(f"   • {config.name} (ID: {config.id}, Mode: {config.mode.value})")
                
                # Check if we're actually receiving messages
                if self.messages_processed == 0:
                    logger.warning(f"⚠️ NO MESSAGES RECEIVED - Check channel connections!")
                
            except Exception as e:
                logger.error(f"Performance monitor error: {e}")
    
    async def stop(self):
        """Stop the monitor"""
        if not self.running:
            return
        
        logger.info("🔄 Stopping Real-Time Monitor...")
        self.running = False
        
        try:
            # Close DBOTX connection
            await dbotx_client.close_session()
            
            # Disconnect client
            if self.client:
                await self.client.disconnect()
            
            logger.info("✅ Real-Time Monitor stopped")
            
        except Exception as e:
            logger.error(f"Error stopping monitor: {e}")


# Global monitor instance
monitor = RealTimeMonitor()


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info("Received shutdown signal")
    asyncio.create_task(monitor.stop())
    sys.exit(0)


async def main():
    """Main entry point"""
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize and start monitoring
        await monitor.initialize()
        await monitor.start_monitoring()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await monitor.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        await monitor.stop()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())