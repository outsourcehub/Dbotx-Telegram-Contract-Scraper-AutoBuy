# 1. analysis: The user wants to fix an IndentationError in the callback_handler function by correctly completing the `elif action == "noop":` block and ensuring the subsequent `handle_recheck_membership_callback` function is placed correctly.

# ⚠️ LICENSE NOTICE:
# This file contains referral links required by the Prosperity Public License.
# Removing or modifying these for public/redistributed use constitutes
# commercial use and requires permission from the author.

import asyncio
from datetime import datetime, timezone
import time

"""
Message and Callback Handlers for Ultra-Fast Trading Bot (Telethon)
Speed-optimized handlers for instant trade execution
"""
import asyncio
import logging
from telethon import events, Button
from telethon.tl.types import Message, User, ChannelParticipantsAdmins
from telethon.errors import FloodWaitError
from models import storage
from api_client import client as dbotx_client
from keyboards_telethon import TradingKeyboards, SETTING_SUGGESTIONS
from models import ChannelSubscription, ChannelType, FilterMode
from utils import (
    detect_contract_address, validate_settings_input, format_setting_display,
    format_order_summary, generate_order_id, format_settings_summary,
    is_owner, log_trade_attempt, log_trade_result, PerformanceTimer,
    format_wallet_display
)
from config import DEFAULT_SETTINGS, OWNER_CHAT_ID, MENU_EMOJI

logger = logging.getLogger(__name__)

# User state for handling multi-step inputs
user_states = {}

# Store references to both clients
_bot_client = None
_user_client = None


# Required channels for membership verification
REQUIRED_CHANNELS = [
    {'id': -1002177319835, 'name': 'WeCopyTradess', 'url': 'https://t.me/WeCopyTradess'},
]

# Membership cache to avoid repeated API calls
_membership_cache = {}


async def check_required_membership(user_id: int) -> tuple[bool, str]:
    """
    Check if user has joined all required channels
    Returns: (is_member, message)
    """
    global _membership_cache
    
    # Check cache first (valid for 5 minutes)
    cache_key = f"{user_id}_membership"
    if cache_key in _membership_cache:
        cached_time, cached_result = _membership_cache[cache_key]
        if time.time() - cached_time < 300:  # 5 minutes
            return cached_result
    
    try:
        missing_channels = []
        
        for channel_info in REQUIRED_CHANNELS:
            channel_id = channel_info['id']
            channel_name = channel_info['name']
            
            try:
                # Get channel entity
                channel = await _user_client.get_entity(channel_id)
                
                # Check if user is a participant
                try:
                    participant = await _user_client.get_permissions(channel, user_id)
                    if participant is None or not hasattr(participant, 'user'):
                        missing_channels.append(channel_name)
                except Exception as perm_error:
                    logger.warning(f"Could not check permissions for user {user_id} in {channel_name}: {perm_error}")
                    missing_channels.append(channel_name)
                    
            except Exception as e:
                logger.error(f"Error checking channel {channel_name}: {e}")
                missing_channels.append(channel_name)
        
        if missing_channels:
            # Build message for single channel
            message = (
                "🚫 **Access Denied - Membership Required**\n\n"
                "You must join this channel to use this bot:\n\n"
                "• [WeCopyTradess](https://t.me/WeCopyTradess)\n\n"
                "After joining, click the button below to verify:"
            )
            
            result = (False, message)
        else:
            result = (True, "✅ Membership verified!")
        
        # Cache the result
        _membership_cache[cache_key] = (time.time(), result)
        return result
        
    except Exception as e:
        logger.error(f"Error in membership check: {e}", exc_info=True)
        return (False, "❌ Error checking membership. Please try again later.")



def register_bot_handlers(bot_client, user_client):
    """Register all BOT client handlers for commands and UI"""
    global _bot_client, _user_client
    _bot_client = bot_client
    _user_client = user_client

    logger.info("📝 Registering BOT client handlers...")

    # Register command handlers
    bot_client.add_event_handler(start_handler, events.NewMessage(pattern='/start'))
    bot_client.add_event_handler(help_handler, events.NewMessage(pattern='/help'))
    bot_client.add_event_handler(verify_handler, events.NewMessage(pattern='/verify'))
    bot_client.add_event_handler(settings_handler, events.NewMessage(pattern='/settings'))
    bot_client.add_event_handler(safety_handler, events.NewMessage(pattern='/safety'))
    bot_client.add_event_handler(channels_handler, events.NewMessage(pattern='/channels'))
    bot_client.add_event_handler(addchannel_handler, events.NewMessage(pattern='/addchannel'))
    bot_client.add_event_handler(addsource_handler, events.NewMessage(pattern='/addsource'))
    bot_client.add_event_handler(cancel_handler, events.NewMessage(pattern='/cancel'))
    bot_client.add_event_handler(setapikey_handler, events.NewMessage(pattern='/setapikey'))
    # Removed wallet and selectwallet handlers
    bot_client.add_event_handler(testchannel_handler, events.NewMessage(pattern='/testchannel'))

    # Register callback query handler
    bot_client.add_event_handler(callback_handler, events.CallbackQuery())

    # Register contract handler (for non-command messages)
    bot_client.add_event_handler(contract_handler, events.NewMessage(func=lambda e: not e.message.text.startswith('/')))

    logger.info("✅ BOT client handlers registered")


async def help_handler(event):
    """Handle /help command"""
    user_id = event.sender_id

    # Owner-only restriction
    if OWNER_CHAT_ID and user_id != OWNER_CHAT_ID:
        await event.respond("🚫 This bot is private and not available for public use.")
        return

    help_text = (
        "📚 **Help & Commands**\n\n"
        "**🚀 Getting Started:**\n"
        "1. **Configure your DBOT bots:**\n"
        "   i. Bind a telegram account: Go to https://dbotx.com/dashboard/telegram_personal click in bind and you will generate a key, copy it\n"
        "   ii. Go to the chain's telegram dbot bot, click on 'I already have an account' button and paste the key\n"
        "   Here are the dbot bots for all chains:\n"
        "   • SOL: [@sol_dbot](https://t.me/sol_dbot?start=ref_85402573)\n"
        "   • ETH: [@dex_dbot](https://t.me/dex_dbot?start=ref_85402573)\n"
        "   • ARB: [@arb_dbot](https://t.me/arb_dbot?start=ref_85402573)\n"
        "   • BSC: [@bsc_dbot](https://t.me/bsc_dbot?start=ref_85402573)\n"
        "   • BASE: [@base2_dbot](https://t.me/base2_dbot?start=ref_85402573)\n"
        "   **IMPORTANT:** Make sure \"auto buy\" setting is toggled ON in each DBOT bot!\n"
        "2. **Add a Source:** Add a private/public channel or group to monitor\n\n"
        "**How it works:**\n"
        "• This bot monitors your channels/groups for token contracts\n"
        "• Validates contracts to be sure if it's real and toggled on in the settings menu\n"
        "• If toggled on, sends valid contracts to your DBOT bot\n"
        "• Your DBOT bot executes the trade based on your settings\n\n"
        "**Need more help?**\n"
        "Contact support! theweb3scout@gmail.com"
    )

    await event.respond(help_text)


async def verify_handler(event):
    """Handle /verify command to submit wallet pattern verification"""
    user_id = event.sender_id

    # Owner-only restriction
    if OWNER_CHAT_ID and user_id != OWNER_CHAT_ID:
        await event.respond("🚫 This bot is private and not available for public use.")
        return

    user = storage.get_user(user_id)

    if not user:
        await start_handler(event)
        return

    # Check if already verified
    if user.is_verified:
        await event.respond(
            "✅ **Already Verified**\n\n"
            "Your account is already verified and has full access to the bot."
        )
        return

    # Extract wallet pattern from command
    command_parts = event.message.text.split(maxsplit=1)
    if len(command_parts) < 2:
        await event.respond(
            "**🔐 Wallet Verification**\n\n"
            "Usage: `/verify (first6)...(last4)`\n\n"
            "Example: `/verify 0x0ed9...eho3`\n\n"
            "This pattern must match a wallet in your dbot account."
        )
        return

    wallet_pattern = command_parts[1].strip()

    # Validate pattern format (basic check)
    if '...' not in wallet_pattern or len(wallet_pattern) < 10:
        await event.respond(
            "❌ **Invalid Pattern**\n\n"
            "Pattern must be in format: `(first6)...(last4)`\n"
            "Example: `0x0ed9...eho3`"
        )
        return

    # Import Supabase client
    try:
        from supabase import create_client
        from config import SUPABASE_URL, SUPABASE_SERVICE_KEY, VERIFY_REQUESTS_TABLE

        # Initialize Supabase client with SERVICE_ROLE key
        # Security is enforced by PostgreSQL triggers (rate limiting, validation)
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

        # Insert verification request into Supabase
        # Database trigger will validate and enforce rate limits
        request_data = {
            'user_id': str(user_id),
            'pattern': wallet_pattern,
            'chain': 'ethereum',  # Default, VerifyAddy will check all chains
            'status': 'pending'
        }

        response = supabase.table(VERIFY_REQUESTS_TABLE).insert(request_data).execute()

        # Store pattern in user record (SAFE: only updating wallet_pattern, not settings)
        user.wallet_pattern = wallet_pattern
        storage.create_user(user_id=user_id, wallet_pattern=wallet_pattern)

        # Get request ID for polling fallback
        request_id = response.data[0].get('id') if response.data else None

        await event.respond(
            "⏳ **Verification Request Submitted**\n\n"
            f"Address: `{wallet_pattern}`\n\n"
            "Your request is being processed. You should receive approval within 1 minute if the address matches the registered wallet in your dbot account.\n\n"
            "Please wait..."
        )

        logger.info(f"✅ Verification request submitted for user {user_id}: {wallet_pattern}, request_id={request_id}")

        # Start 5-second polling fallback (in case real-time fails)
        if request_id:
            asyncio.create_task(_verification_polling_fallback(user_id, request_id, wallet_pattern, supabase))

    except Exception as e:
        error_message = str(e)
        logger.error(f"❌ Error submitting verification request for user {user_id}: {e}")
        await event.respond(
            "❌ **Verification Error**\n\n"
            f"Failed to submit request: {error_message}\n\n"
            "Please try again later."
        )


async def _verification_polling_fallback(user_id: int, request_id: int, wallet_pattern: str, supabase):
    """
    Polling fallback: Check verification status after 5 seconds
    This ensures notifications are sent even if real-time listener fails
    """
    try:
        logger.info(f"⏱️ Starting 5-second polling fallback for user {user_id}, request {request_id}")

        # Wait 5 seconds
        await asyncio.sleep(5)

        # Query Supabase for the request status
        from config import VERIFY_REQUESTS_TABLE
        result = supabase.table(VERIFY_REQUESTS_TABLE).select('*').eq('id', request_id).execute()

        if not result.data or len(result.data) == 0:
            logger.warning(f"⚠️ [POLLING] Request {request_id} not found in database")
            return

        request_data = result.data[0]
        status = request_data.get('status')
        response_message = request_data.get('response_message', '')

        logger.info(f"📊 [POLLING] Request {request_id} status: {status}")

        # Only send notification if status is final (approved/denied)
        if status in ['approved', 'denied']:
            # Import bot instance to send notification
            from bot import bot

            # Process the verification update via polling
            await bot._process_verification_update(
                user_id,
                status,
                response_message,
                'polling_fallback'
            )
        else:
            logger.info(f"⏭️ [POLLING] Request {request_id} still {status}, no notification needed")

    except Exception as e:
        logger.error(f"❌ [POLLING] Error in fallback for request {request_id}: {e}", exc_info=True)

        # Parse database trigger errors for user-friendly messages
        if 'Rate limit exceeded' in str(e):
            await event.respond(
                "⏱️ **Rate Limit Exceeded**\n\n"
                "You've submitted too many verification requests.\n\n"
                "**Limits:**\n"
                "• Maximum 3 requests per hour\n"
                "• No duplicate requests within 5 minutes\n\n"
                "Please wait and try again later."
            )
        elif 'Invalid pattern format' in str(e):
            await event.respond(
                "❌ **Invalid pattern format**\n\n"
                "Pattern must be in format: `(first6)...(last4)`\n\n"
                "Example: `0x0ed9...eho3`"
            )
        elif 'Invalid chain' in str(e):
            await event.respond(
                "❌ **Invalid Chain**\n\n"
                "Supported chains: solana, ethereum, base, bsc, tron"
            )
        elif 'Duplicate request' in str(e):
            await event.respond(
                "⚠️ **Duplicate Request**\n\n"
                "You already submitted this recently.\n\n"
                "Please wait 5 minutes before submitting again."
            )
        elif 'Global rate limit' in str(e):
            await event.respond(
                "🚦 **System Busy**\n\n"
                "Too many verification requests right now.\n\n"
                "Please try again in 1 minute."
            )
        else:
            await event.respond(
                "❌ **Verification Failed**\n\n"
                f"Error: {str(e)[:100]}\n\n"
                "Please try again or contact support."
            )


async def register_user_handlers(user_client, bot_client):
    """Register all USER client handlers for channel monitoring"""
    global _user_client, _bot_client
    _user_client = user_client
    if not _bot_client:
        _bot_client = bot_client

    logger.info("📝 Registering USER client handlers...")

    # Verify client is connected
    if not user_client.is_connected():
        logger.error("❌ USER client not connected - cannot register handlers!")
        return

    # Get all monitored channels to create channel-specific handler
    all_channels = storage.get_all_active_channels()

    if not all_channels:
        logger.warning("⚠️ No active channels to monitor")
        return

    # Build list of channel entities for filtering
    monitored_entities = []
    for channel_sub in all_channels:
        try:
            # Get the channel entity (client is now connected)
            entity = await user_client.get_entity(channel_sub.channel_id)
            monitored_entities.append(entity)
            logger.info(f"✅ Will monitor: {entity.title} (ID: {channel_sub.channel_id})")
        except Exception as e:
            logger.warning(f"⚠️ Cannot get entity for {channel_sub.channel_id}: {e}")

    if not monitored_entities:
        logger.error("❌ No accessible channel entities found")
        return

    # Register handler ONLY for monitored channels
    @user_client.on(events.NewMessage(chats=monitored_entities))
    async def channel_message_handler(event):
        await monitor_channel_messages(event)

    logger.info(f"✅ USER client handlers registered for {len(monitored_entities)} channels")
    logger.info(f"🎯 MONITORING ACTIVE - Listening for messages from {len(monitored_entities)} channels")


# ============================================================================
# COMMAND HANDLERS (BOT CLIENT)
# ============================================================================

async def start_handler(event):
    """Handle /start command"""
    user_id = event.sender_id

    # Owner-only restriction
    if OWNER_CHAT_ID and user_id != OWNER_CHAT_ID:
        await event.respond("🚫 This bot is private and not available for public use.")
        return

    # Get sender info
    sender = await event.get_sender()
    username = sender.username if hasattr(sender, 'username') else None
    first_name = sender.first_name if hasattr(sender, 'first_name') else None
    last_name = sender.last_name if hasattr(sender, 'last_name') else None

    # Create or update user (settings only applied for NEW users via default_factory in User model)
    # For existing users, we MUST NOT pass settings parameter
    existing_user = storage.get_user(user_id)
    if existing_user:
        # User exists - update metadata only, NEVER touch settings
        user = storage.create_user(
            user_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )

        # Ensure enabled_chains exists (migration for existing users)
        if 'enabled_chains' not in user.settings:
            user.settings['enabled_chains'] = ['solana', 'bsc', 'ethereum', 'base', 'arbitrum', 'tron']
            storage.update_user_settings(user_id, user.settings)
            logger.info(f"✅ Migrated user {user_id} to include enabled_chains")
    else:
        # New user - storage.create_user will initialize with DEFAULT_SETTINGS
        user = storage.create_user(
            user_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )

    # Check if user is verified
    if not user.is_verified:
        # Show membership required message
        await event.respond(
            "🚫 **Access Denied - Membership Required**\n\n"
            "You must join this channel to use this bot:\n\n"
            "• [WeCopyTradess](https://t.me/WeCopyTradess)\n\n"
            "After joining, click the button below to verify:",
            buttons=[
                [Button.inline("✅ I've Joined - Verify Now", b"recheck_membership")]
            ]
        )
        return
        
        # Continue to show welcome message below

    # User is verified - show normal welcome
    welcome_text = (
        "🚀 **Dbotx Scraper Bot**\n\n"
        "**Use the help button or /help to get a guide on how to use this bot**\n\n"
        "**Supported Chains:**\n"
        "• BSC (BNB) • Solana (SOL) • Ethereum (ETH) • Base (BASE) • Arbitrum (ARB) • TRX (Tron)\n\n"
        "✨ Powered by Vtechwriter — support the project via the free tool! (Includes referral links)"
    )

    await event.respond(
        welcome_text,
        buttons=TradingKeyboards.main_menu()
    )


async def settings_handler(event):
    """Handle /settings command - Show chain selector"""
    user_id = event.sender_id
    user = storage.get_user(user_id)

    if not user:
        await start_handler(event)
        return

    # Check verification
    if not user.is_verified:
        await event.respond(
            "❌ **Access Denied**\n\n"
            "You need to verify your account first.\n"
            "Use `/verify (first6)...(last4)` to verify your wallet."
        )
        return

    enabled_chains = user.settings.get('enabled_chains', ['solana', 'bsc', 'ethereum', 'base', 'tron'])
    enabled_names = ', '.join([c.upper() for c in enabled_chains])

    settings_text = (
        "⚙️ **CHAIN SETTINGS**\n\n"
        "Toggle chains to enable/disable forwarding:\n\n"
        f"**Currently Enabled:** {enabled_names}\n\n"
        "✅ = Enabled (contracts forwarded)\n"
        "❌ = Disabled (contracts ignored)\n\n"
        "Only contracts from enabled chains will be processed and sent to DBOT."
    )

    await event.respond(
        settings_text,
        buttons=TradingKeyboards.chain_selector_menu(user)
    )


async def safety_handler(event):
    """Handle /safety command - Redirect to settings (safety is now per-chain)"""
    user_id = event.sender_id
    user = storage.get_user(user_id)

    if not user:
        await start_handler(event)
        return

    # Check verification
    if not user.is_verified:
        await event.respond(
            "❌ **Access Denied**\n\n"
            "You need to verify your account first.\n"
            "Use `/verify (first6)...(last4)` to verify your wallet."
        )
        return

    # Redirect to settings (safety is per-chain now)
    await event.respond(
        "🔒 **Safety Filters**\n\n"
        "Safety filters are configured **per-chain** for better control.\n\n"
        "**Access path:**\n"
        "Settings → Select Chain → Safety Filters\n\n"
        "Each chain has independent safety settings:\n"
        "• Market cap limits\n"
        "• Holder requirements\n"
        "• Security checks (freeze/mint authority)\n"
        "• Volume ratio filters\n\n"
        "💡 Configure different safety levels for each chain!",
        buttons=TradingKeyboards.chain_selector_menu()
    )


async def channels_handler(event):
    """Handle /channels command"""
    user_id = event.sender_id
    user = storage.get_user(user_id)

    if not user:
        await start_handler(event)
        return

    # Check verification
    if not user.is_verified:
        await event.respond(
            "❌ **Access Denied**\n\n"
            "You need to verify your account first.\n"
            "Use `/verify (first6)...(last4)` to verify your wallet."
        )
        return

    channels = storage.get_user_channels(user_id)
    channels_text = "**📡 Source Monitor**\n\n"

    if channels:
        channels_text += f"**Monitored Sources ({len(channels)}):**\n\n"
        for channel in channels:
            status = "🟢 Active" if channel.is_active else "🔴 Inactive"
            filter_mode = {
                'all': "All messages",
                'admins': "Admin only",
                'users': f"{len(channel.allowed_user_ids)} users"
            }.get(channel.filter_mode.value, "All messages")

            channel_name = channel.channel_username or channel.channel_title
            channels_text += f"• **{channel_name}**\n"
            channels_text += f"  {status} | {filter_mode}\n"
            if channel.custom_buy_amount:
                channels_text += f"  💰 Custom: {channel.custom_buy_amount} SOL\n"
            channels_text += f"  📊 Trades: {channel.total_trades}\n\n"
    else:
        channels_text += "No channels configured yet.\n\n"
        channels_text += "Use /addchannel to start monitoring channels for automatic trading."

    await event.respond(
        channels_text,
        buttons=TradingKeyboards.channels_menu(channels)
    )


async def handle_user_id_input(event):
    """Handle user ID or username input for adding users to channel filters"""
    user_id = event.sender_id
    user = storage.get_user(user_id)

    if not user:
        logger.warning(f"User {user_id} not found when processing user ID input")
        return

    # Check if user is awaiting user ID input
    if user_id not in user_states or user_states[user_id].get('waiting_for') != 'user_id_input':
        logger.debug(f"User {user_id} not awaiting user ID input, ignoring")
        return

    try:
        # Get the input text
        input_text = event.message.text.strip()

        # Get channel ID from state
        channel_id = user_states[user_id].get('channel_id')
        if not channel_id:
            logger.error(f"No channel_id in state for user {user_id}")
            await event.respond("❌ Session error. Please try again.")
            if user_id in user_states:
                del user_states[user_id]
            return

        # Get channel subscription
        subscription = storage.get_channel_subscription(user_id, channel_id)
        if not subscription:
            await event.respond("❌ Channel not found")
            if user_id in user_states:
                del user_states[user_id]
            return

        target_user_id = None
        user_name = None

        # Try to parse as numeric ID first
        if input_text.isdigit():
            target_user_id = int(input_text)
            logger.info(f"Parsed as user ID: {target_user_id}")

            # Try to get user info
            try:
                user_entity = await _user_client.get_entity(target_user_id)
                user_name = user_entity.first_name
                if hasattr(user_entity, 'username') and user_entity.username:
                    user_name += f" (@{user_entity.username})"
                logger.info(f"✅ Validated user ID {target_user_id}: {user_name}")
            except Exception as e:
                logger.warning(f"Could not fetch user entity for ID {target_user_id}: {e}")
                user_name = f"User {target_user_id}"

        # Try to parse as username
        else:
            # Remove @ if present
            username = input_text.lstrip('@')
            logger.info(f"Attempting to resolve username: @{username}")

            try:
                user_entity = await _user_client.get_entity(username)
                target_user_id = user_entity.id
                user_name = user_entity.first_name
                if hasattr(user_entity, 'username') and user_entity.username:
                    user_name += f" (@{user_entity.username})"
                logger.info(f"✅ Resolved username @{username} to ID {target_user_id}: {user_name}")
            except Exception as e:
                logger.error(f"Failed to resolve username @{username}: {e}")
                await event.respond(
                    f"❌ **Username Not Found**\n\n"
                    f"Could not find user `@{username}`.\n\n"
                    f"**Possible reasons:**\n"
                    f"• Username doesn't exist\n"
                    f"• User's privacy settings prevent lookup\n"
                    f"• Username is misspelled\n\n"
                    f"💡 Try using their numeric ID instead (use @userinfobot to find it)"
                )
                if user_id in user_states:
                    del user_states[user_id]
                return

        # Add user to allowed list
        allowed_users = subscription.allowed_user_ids or []
        if target_user_id in allowed_users:
            await event.respond(f"⚠️ User `{target_user_id}` is already in the allowed list")
            if user_id in user_states:
                del user_states[user_id]
            return

        allowed_users.append(target_user_id)
        storage.update_channel_settings(
            user_id,
            channel_id,
            allowed_user_ids=allowed_users,
            filter_mode=FilterMode.SPECIFIC_USERS
        )

        # Clear state
        if user_id in user_states:
            del user_states[user_id]

        # Confirm
        await event.respond(
            f"✅ **User Added**\n\n"
            f"**Channel:** {subscription.channel_title}\n"
            f"**User:** {user_name or f'User {target_user_id}'}\n"
            f"**User ID:** `{target_user_id}`\n"
            f"**Total allowed users:** {len(allowed_users)}\n\n"
            f"Only messages from allowed users will be processed."
        )
        logger.info(f"✅ User {user_id} added user {target_user_id} to channel {channel_id} via ID/username input")

    except Exception as e:
        logger.error(f"Error processing user ID input for user {user_id}: {e}", exc_info=True)
        if user_id in user_states:
            del user_states[user_id]
        await event.respond(
            "❌ **Error Processing User**\n\n"
            "Failed to add user. Please try again or contact support."
        )


    # Check verification
    if not user.is_verified:
        await event.respond(
            "❌ **Access Denied**\n\n"
            "You need to verify your account first.\n"
            "Use `/verify (first6)...(last4)` to verify your wallet."
        )
        return

    channels = storage.get_user_channels(user_id)
    channels_text = "**📡 Source Monitor**\n\n"

    if channels:
        channels_text += f"**Monitored Sources ({len(channels)}):**\n\n"
        for channel in channels:
            status = "🟢 Active" if channel.is_active else "🔴 Inactive"
            filter_mode = {
                'all': "All messages",
                'admins': "Admin only",
                'users': f"{len(channel.allowed_user_ids)} users"
            }.get(channel.filter_mode.value, "All messages")

            channel_name = channel.channel_username or channel.channel_title
            channels_text += f"• **{channel_name}**\n"
            channels_text += f"  {status} | {filter_mode}\n"
            if channel.custom_buy_amount:
                channels_text += f"  💰 Custom: {channel.custom_buy_amount} SOL\n"
            channels_text += f"  📊 Trades: {channel.total_trades}\n\n"
    else:
        channels_text += "No channels configured yet.\n\n"
        channels_text += "Use /addchannel to start monitoring channels for automatic trading."

    await event.respond(
        channels_text,
        buttons=TradingKeyboards.channels_menu(channels)
    )


async def addchannel_handler(event):
    """Handle /addchannel command"""
    user_id = event.sender_id
    user = storage.get_user(user_id)

    if not user:
        await start_handler(event)
        return

    # Check verification
    if not user.is_verified:
        await event.respond(
            "❌ **Access Denied**\n\n"
            "You need to verify your account first.\n"
            "Use `/verify (first6)...(last4)` to verify your wallet."
        )
        return

    # Set user state to awaiting channel forward
    user_states[user_id] = {'waiting_for': 'channel_forward'}

    await event.respond(
        "**📡 Add Channel or Group to Monitor**\n\n"
        "**Smart Detection:**\n"
        "Please forward any message from the channel or group you want to monitor.\n\n"
        "**Benefits:**\n"
        "• Works with channels, supergroups, and regular groups\n"
        "• Works with private and public channels/groups\n"
        "• Automatically gets real info\n"
        "• No need to know ID or username\n\n"
        "**Instructions:**\n"
        "1. Go to the channel or group you want to monitor\n"
        "2. Forward any message from there to me\n"
        "3. I'll extract the info and start monitoring\n\n"
        "💡 **For Groups:** You can filter by specific users after adding\n"
        "⚡ Once added, monitoring will start immediately!\n\n"
        "Use /cancel to stop this process."
    )


async def addsource_handler(event):
    """Handle /addsource command - Pin-based detection method"""
    user_id = event.sender_id
    user = storage.get_user(user_id)

    if not user:
        await start_handler(event)
        return

    # Check verification
    if not user.is_verified:
        await event.respond(
            "❌ **Access Denied**\n\n"
            "You need to verify your account first.\n"
            "Use `/verify (first6)...(last4)` to verify your wallet."
        )
        return

    # Set user state to awaiting pinned confirmation
    user_states[user_id] = {'waiting_for': 'pinned_source', 'timestamp': time.time()}

    from telethon import Button
    await event.respond(
        "**📌 Add Source via Pinning**\n\n"
        "**Universal Method - Works with:**\n"
        "✅ Private Groups\n"
        "✅ Public Groups\n"
        "✅ Channels\n"
        "✅ Supergroups\n\n"
        "**Instructions:**\n"
        "1. Open Telegram and go to your chat list\n"
        "2. **Pin** the target group/channel to the TOP of your list\n"
        "   (Long press → Pin to top)\n"
        "3. Click the Continue button below\n\n"
        "💡 **Tip:** The bot will detect the chat pinned within 7 minutes of using the /addsource button\n"
        "💡 **Tip:** If the bot cannot find the chat, remove all pinned chats and start the process all over pinning just that one source.\n\n"
        "⚡ This method works instantly and doesn't require forwarding!\n\n"
        "Use /cancel to stop this process.",
        buttons=[
            [Button.inline("✅ Continue (I've pinned it)", b"detect_pinned")],
            [Button.inline("❌ Cancel", b"cancel_addsource")]
        ]
    )


async def cancel_handler(event):
    """Handle /cancel command"""
    user_id = event.sender_id
    user = storage.get_user(user_id)

    if not user:
        await start_handler(event)
        return

    # Clear any pending states
    if user_id in user_states:
        del user_states[user_id]

    await event.respond(
        "❌ **Operation Cancelled**\n\n"
        "No source was added.\n\n"
        "Use /addsource to try again."
    )


async def setapikey_handler(event):
    """Handle /setapikey command"""
    user_id = event.sender_id

    # Check if user is owner
    if not is_owner(user_id):
        await event.respond("❌ Only the bot owner can set the API key.")
        return

    # Extract API key from command
    command_parts = event.message.text.split(maxsplit=1)
    if len(command_parts) < 2:
        await event.respond(
            "**🔑 Set DBOTX API Key**\n\n"
            "Usage: `/setapikey YOUR_API_KEY_HERE`\n\n"
            "Example: `/setapikey dbotx_1234567890abcdef`\n\n"
            "⚠️ Make sure to delete this message after setting the key for security."
        )
        return

    api_key = command_parts[1].strip()

    # Set the API key in client
    dbotx_client.set_api_key(api_key)

    # Test the API key
    api_healthy = await dbotx_client.health_check()

    if api_healthy:
        # Save API key to database permanently
        user = storage.get_user(user_id)
        if user:
            user.api_key = api_key
            storage.create_user(user_id=user_id, api_key=api_key)
            logger.info(f"💾 API key saved to database for user {user_id}")

        await event.respond(
            "✅ **API Key Set Successfully**\n\n"
            "DBOTX API connection verified and ready for trading!\n\n"
            "💾 **API key saved permanently** - no need to re-enter after restart\n\n"
            "⚠️ Please delete your message containing the API key for security."
        )
        logger.info("✅ DBOTX API key configured successfully and saved to database")
    else:
        await event.respond(
            "❌ **API Key Test Failed**\n\n"
            "The provided API key could not connect to DBOTX.\n"
            "Please check your key and try again.\n\n"
            "⚠️ Please delete your message containing the API key for security."
        )
        logger.error("❌ DBOTX API key test failed")


async def testchannel_handler(event):
    """Handle /testchannel command - Verify channel monitoring"""
    user_id = event.sender_id
    user = storage.get_user(user_id)

    if not user:
        await start_handler(event)
        return

    # Get monitored channels
    channels = storage.get_user_channels(user_id)

    if not channels:
        await event.respond(
            "❌ **No Channels Configured**\n\n"
            "Please add a channel first with /addchannel"
        )
        return

    await event.respond("🔍 **Testing Channel Access...**\n\nFetching recent messages from monitored channels...")

    results = []
    for channel in channels[:5]:  # Test first 5 channels
        try:
            channel_id = int(channel.channel_id)

            # Try to fetch last 10 messages from this channel using USER client
            messages = []
            async for msg in _user_client.iter_messages(channel_id, limit=10):
                messages.append(msg)

            if messages:
                results.append(
                    f"✅ **{channel.channel_title or channel.channel_username}**\n"
                    f"   📊 Retrieved {len(messages)} recent messages\n"
                    f"   📅 Latest: {messages[0].date.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"   📝 Last message preview: {messages[0].text[:50] if messages[0].text else '[Media]'}...\n"
                )
                logger.info(f"✅ Successfully tested channel {channel_id}: {len(messages)} messages")
            else:
                results.append(
                    f"⚠️ **{channel.channel_title or channel.channel_username}**\n"
                    f"   No messages found (channel may be empty)\n"
                )
                logger.warning(f"⚠️ No messages found in channel {channel_id}")

        except Exception as e:
            results.append(
                f"❌ **{channel.channel_title or channel.channel_username}**\n"
                f"   Error: {str(e)[:50]}\n"
            )
            logger.error(f"❌ Failed to test channel {channel_id}: {e}")

    test_result = "🧪 **Channel Monitoring Test Results**\n\n" + "\n".join(results)
    test_result += "\n\n💡 **Tip:** If a channel shows errors, try removing and re-adding it."

    await event.respond(test_result)


# Removed wallet_handler and selectwallet_handler as per instructions

# ============================================================================
# MESSAGE HANDLERS (BOT CLIENT)
# ============================================================================

async def handle_verification_forward(event, user_id: int, user):
    """Handle forwarded messages for channel verification"""
    try:
        # Get forward info
        forward_info = event.message.fwd_from
        if not forward_info:
            await event.respond(
                "❌ **Invalid Forward**\n\n"
                "Please forward a message from the required channel (WeCopyTradess)."
            )
            return
        
        # Extract channel ID
        chat_id = None
        if hasattr(forward_info, 'chat') and forward_info.chat:
            original_chat = forward_info.chat
            if hasattr(original_chat, 'channel_id'):
                chat_id = original_chat.channel_id
            elif hasattr(original_chat, 'chat_id'):
                chat_id = original_chat.chat_id
        elif hasattr(forward_info, 'from_id') and forward_info.from_id:
            from_id = forward_info.from_id
            if hasattr(from_id, 'channel_id'):
                chat_id = from_id.channel_id
            elif hasattr(from_id, 'chat_id'):
                chat_id = from_id.chat_id
        
        if not chat_id:
            await event.respond(
                "❌ **Could Not Detect Channel**\n\n"
                "Please forward a message from WeCopyTradess channel."
            )
            return
        
        # Check if this is the required verification channel (WeCopyTradess)
        state = user_states[user_id]
        required_channel_id = -1002177319835  # WeCopyTradess channel ID
        
        if chat_id != required_channel_id:
            await event.respond(
                "❌ **Wrong Channel**\n\n"
                "Please forward a message from [WeCopyTradess](https://t.me/WeCopyTradess) channel."
            )
            return
        
        # Forward detected successfully - show confirmation button
        await event.respond(
            "✅ **Forward Detected!**\n\n"
            "I've received your forward from WeCopyTradess.\n\n"
            "Click the button below to complete verification:",
            buttons=[
                [Button.inline("✅ Complete Verification", b"confirm_forward_verification")],
                [Button.inline("❌ Cancel", b"cancel_verification")]
            ]
        )
        
        # Store that forward was detected
        user_states[user_id]['forward_detected'] = True
        logger.info(f"📨 User {user_id} forwarded message from WeCopyTradess, awaiting confirmation")
    
    except Exception as e:
        logger.error(f"Error in verification forward handler: {e}", exc_info=True)
        await event.respond(
            "❌ **Verification Error**\n\n"
            "An error occurred during verification. Please try again."
        )


async def handle_forwarded_message(event):
    """Handle forwarded messages for channel addition"""
    user_id = event.sender_id
    user = storage.get_user(user_id)

    if not user:
        logger.warning(f"User {user_id} not found when processing forwarded message")
        return

    # Check user state - could be channel_forward or channel_verification
    if user_id not in user_states:
        logger.debug(f"User {user_id} has no state, ignoring")
        return
    
    waiting_for = user_states[user_id].get('waiting_for')
    if waiting_for not in ['channel_forward', 'channel_verification']:
        logger.debug(f"User {user_id} not awaiting forward or verification, ignoring")
        return
    
    # Handle channel verification mode
    if waiting_for == 'channel_verification':
        await handle_verification_forward(event, user_id, user)
        return

    # Check if message is forwarded
    if not event.message.fwd_from:
        logger.warning(f"Message from user {user_id} is not forwarded")
        await event.respond(
            "❌ **Invalid Forward**\n\n"
            "Please forward a message from the channel you want to monitor.\n\n"
            "The message must be forwarded from a channel or group, not from a user."
        )
        return

    try:
        # Get the forwarded chat entity using Telethon's structure
        forward_info = event.message.fwd_from
        chat_id = None

        # PRIORITY 1: Check fwd_from.chat (original chat) - CORRECT for forwarded messages
        if hasattr(forward_info, 'chat') and forward_info.chat:
            original_chat = forward_info.chat
            if hasattr(original_chat, 'channel_id'):
                # This is a channel/supergroup
                chat_id = original_chat.channel_id
                logger.info(f"✅ Got channel ID from fwd_from.chat.channel_id: {chat_id}")
            elif hasattr(original_chat, 'chat_id'):
                # This is a regular group
                chat_id = original_chat.chat_id
                logger.info(f"✅ Got group ID from fwd_from.chat.chat_id: {chat_id}")
            else:
                # Not a channel or group (probably private chat)
                await event.respond(
                    "❌ **Invalid Forward**\n\n"
                    "Please forward a message from a channel or group, not a private chat."
                )
                return

        # PRIORITY 2: Fallback to from_id (sender) - for edge cases
        elif hasattr(forward_info, 'from_id') and forward_info.from_id:
            from_id = forward_info.from_id

            # Check if it's a Channel object (includes supergroups)
            if hasattr(from_id, 'channel_id'):
                # This is a channel/supergroup - use the channel_id directly
                chat_id = from_id.channel_id
                logger.info(f"✅ Got channel ID from fwd_from.from_id.channel_id: {chat_id}")
            elif hasattr(from_id, 'chat_id'):
                # This is a regular group
                chat_id = from_id.chat_id
                logger.info(f"✅ Got chat ID from fwd_from.from_id.chat_id: {chat_id}")
            elif hasattr(from_id, 'user_id'):
                # This is a user - not what we want
                await event.respond(
                    "❌ **Invalid Forward**\n\n"
                    "You forwarded a message from a user, not a channel or group.\n\n"
                    "Please forward a message from the channel or group you want to monitor."
                )
                return

        # PRIORITY 3: Fallback to peer_id (very rare edge case)
        elif hasattr(event.message, 'peer_id') and event.message.peer_id:
            peer_id = event.message.peer_id
            if hasattr(peer_id, 'chat_id'):
                # Regular group
                chat_id = peer_id.chat_id
                logger.info(f"✅ Got chat ID from peer_id.chat_id: {chat_id}")
            elif hasattr(peer_id, 'channel_id'):
                # Channel/supergroup
                chat_id = peer_id.channel_id
                logger.info(f"✅ Got channel ID from peer_id.channel_id: {chat_id}")

        if not chat_id:
            logger.error("❌ Could not extract chat/channel ID from any source")
            await event.respond("❌ Could not determine channel/group ID from forwarded message")
            return

        # Get chat entity using USER client (Telethon automatically converts IDs)
        chat = await _user_client.get_entity(chat_id)

        # VALIDATION: Ensure this is a channel/group, not a private user chat
        from telethon.tl.types import User
        if isinstance(chat, User):
            logger.warning(f"⚠️ User {user_id} tried to add a private user chat (ID: {chat_id})")
            if user_id in user_states:
                del user_states[user_id]
            await event.respond(
                "❌ **Invalid Forward**\n\n"
                "You forwarded a message from a **private chat**, not a channel or group.\n\n"
                "**To add a channel/group:**\n"
                "1. Go to the channel or group you want to monitor\n"
                "2. Forward **any message from that channel/group** to me\n"
                "3. I'll automatically detect and add it\n\n"
                "💡 The message must come from a channel or group, not from a user."
            )
            return

        # Check if channel already exists
        existing = storage.get_channel_subscription(user_id, chat_id)
        if existing:
            if user_id in user_states:
                del user_states[user_id]
            await event.respond(
                f"❌ **Channel Already Monitored**\n\n"
                f"**{existing.channel_title}** is already in your monitor list.\n\n"
                f"Status: {'🟢 Active' if existing.is_active else '🔴 Inactive'}\n"
                f"Trades: {existing.total_trades}"
            )
            return

        # Determine channel type
        channel_type = ChannelType.CHANNEL
        if hasattr(chat, 'megagroup') and chat.megagroup:
            channel_type = ChannelType.SUPERGROUP
        elif hasattr(chat, 'broadcast') and not chat.broadcast:
            channel_type = ChannelType.GROUP

        # CRITICAL: Normalize channel_id for storage
        # Telethon uses different formats, we need consistency
        # Convert to -100XXXXXXXXXX format for all channels/supergroups
        # Regular groups stay as negative numbers
        normalized_id = chat_id
        if hasattr(chat, 'megagroup') or (hasattr(chat, 'broadcast') and chat.broadcast):
            # This is a channel or supergroup - ensure -100 prefix
            if abs(chat_id) < 1000000000000:  # Missing -100 prefix
                normalized_id = -1000000000000 - abs(chat_id)
            elif chat_id > 0:  # Positive ID needs conversion
                normalized_id = -1000000000000 - chat_id

        logger.info(f"📝 Channel ID normalization: {chat_id} -> {normalized_id}")

        # Create new channel subscription
        subscription = storage.create_channel_subscription(
            user_id=user_id,
            channel_id=normalized_id,
            channel_title=chat.title,
            channel_username=chat.username if hasattr(chat, 'username') else None,
            channel_type=channel_type,
            is_active=True,
            filter_mode=FilterMode.ALL_MESSAGES
        )

        # Clear user state
        if user_id in user_states:
            del user_states[user_id]

        # Format success message
        channel_info = f"**{chat.title}**"
        if hasattr(chat, 'username') and chat.username:
            channel_info += f" (@{chat.username})"

        # Determine if it's a channel or group for messaging
        entity_type = "channel" if channel_type == ChannelType.CHANNEL else "group"

        await event.respond(
            f"✅ **{entity_type.title()} Added Successfully**\n\n"
            f"📡 {channel_info} is now being monitored!\n\n"
            f"**Details:**\n"
            f"• Type: {channel_type.value.title()}\n"
            f"• ID: {chat_id}\n"
            f"• Filter: All messages\n\n"
            f"⚡ Monitoring will start immediately!\n\n"
            f"💡 **For Groups:** Use filter settings to monitor specific users only\n"
            f"🔧 Use /channels to configure advanced settings\n"
            f"🧪 Use /testchannel to verify monitoring"
        )

        logger.info(f"User {user_id} added {entity_type} '{chat.title}' (ID: {chat_id}) via forwarded message")

        # Re-register USER handlers with the new channel
        if _user_client:
            try:
                await register_user_handlers(_user_client, _bot_client)
                logger.info("✅ USER handlers re-registered with new channel")
            except Exception as reg_error:
                logger.warning(f"⚠️ Could not re-register USER handlers: {reg_error}")

    except Exception as e:
        logger.error(f"Error processing forwarded message for user {user_id}: {e}", exc_info=True)
        if user_id in user_states:
            del user_states[user_id]
        await event.respond(
            "❌ **Error Processing Channel**\n\n"
            "Failed to add channel from forwarded message. Please try again or contact support."
        )


async def contract_handler(event):
    """Handle contract address messages - CORE TRADING FUNCTION"""
    user_id = event.sender_id

    # Owner-only restriction
    if OWNER_CHAT_ID and user_id != OWNER_CHAT_ID:
        return  # Silently ignore non-owner messages

    logger.info(f"🔵 CONTRACT_HANDLER: Called for user {user_id}")

    # Verify user exists
    user = storage.get_user(user_id)
    if not user:
        logger.warning(f"⚠️ CONTRACT_HANDLER: User {user_id} not found in database")
        await event.respond(
            "❌ Please start the bot first with /start",
            buttons=TradingKeyboards.main_menu()
        )
        return

    logger.info(f"✅ CONTRACT_HANDLER: User {user_id} verified, wallet_id={user.wallet_id}, is_verified={user.is_verified}")

    # Check verification
    if not user.is_verified:
        logger.warning(f"⚠️ CONTRACT_HANDLER: User {user_id} not verified")
        await event.respond(
            "❌ **Access Denied**\n\n"
            "You need to verify your account first.\n"
            "Use `/verify (first6)...(last4)` to verify your wallet."
        )
        return

    # PRIORITY 1: Check if user is awaiting channel forward or user ID input
    if user_id in user_states:
        state = user_states[user_id]
        logger.info(f"📋 CONTRACT_HANDLER: User {user_id} has state: {state}")

        if state.get('waiting_for') == 'channel_forward':
            logger.info(f"🔀 CONTRACT_HANDLER: Forwarding to handle_forwarded_message")
            await handle_forwarded_message(event)
            return

        if state.get('waiting_for') == 'user_id_input':
            logger.info(f"🔀 CONTRACT_HANDLER: Forwarding to handle_user_id_input")
            await handle_user_id_input(event)
            return

    # Handle user input for settings
    if user_id in user_states:
        state = user_states[user_id]

        if state.get('waiting_for') == 'setting_input':
            setting_name = state.get('setting_name')
            chain = state.get('chain', 'solana')
            text = event.message.text.strip()
            logger.info(f"⚙️ CONTRACT_HANDLER: Processing setting input for {setting_name} = {text} (chain: {chain})")

            try:
                # Use centralized validation to ensure percentage conversion works correctly
                is_valid, value, error = validate_settings_input(setting_name, text)

                if not is_valid:
                    await event.respond(f"❌ {error}")
                    return

                # Update setting for specific chain
                user.update_setting(setting_name, value, chain=chain)
                storage.update_user_settings(user_id, user.settings)

                # Clear state
                del user_states[user_id]

                chain_name = chain.upper()
                # Confirm update
                await event.respond(
                    f"✅ **Setting Updated**\n\n"
                    f"**Chain:** {chain_name}\n"
                    f"**{setting_name.replace('_', ' ').title()}:** {text}\n\n"
                    f"Setting saved successfully!"
                )
                logger.info(f"✅ CONTRACT_HANDLER: User {user_id} updated {setting_name} to {value} for {chain}")
                return

            except ValueError:
                await event.respond(
                    f"❌ **Invalid Value**\n\n"
                    f"Please enter a valid number.\n\n"
                    f"Or use /cancel to abort."
                )
                return

        elif state.get('waiting_for') == 'custom_channel_amount':
            channel_id = state.get('channel_id')
            text = event.message.text.strip()
            logger.info(f"💰 CONTRACT_HANDLER: Processing custom channel amount for channel {channel_id} = {text}")

            try:
                amount = float(text)
                if amount <= 0:
                    await event.respond("❌ Amount must be greater than 0")
                    return

                # Update channel amount
                storage.update_channel_settings(
                    user_id,
                    channel_id,
                    custom_buy_amount=amount
                )

                # Clear state
                del user_states[user_id]

                # Confirm
                subscription = storage.get_channel_subscription(user_id, channel_id)
                await event.respond(
                    f"✅ **Amount Updated**\n\n"
                    f"**Channel:** {subscription.channel_title}\n"
                    f"**Custom Amount:** {amount} SOL\n\n"
                    f"Use `/channels` to view all channel settings."
                )
                logger.info(f"✅ CONTRACT_HANDLER: User {user_id} set custom amount {amount} for channel {channel_id}")
                return

            except ValueError:
                await event.respond(
                    f"❌ **Invalid Amount**\n\n"
                    f"Please enter a valid number.\n\n"
                    f"Or use /cancel to abort."
                )
                return



        # Other states (like channel_forward) are handled elsewhere
        return

    # Detect contract address
    text = event.message.text
    logger.info(f"🔍 CONTRACT_HANDLER: Attempting to detect contract in message: '{text[:100]}'")

    detection_result = detect_contract_address(text)

    if not detection_result:
        logger.info(f"⚪ CONTRACT_HANDLER: No contract detected, ignoring message")
        return

    chain, address = detection_result
    logger.info(f"🎯 CONTRACT_HANDLER: DETECTED {chain.upper()} contract: {address}")

    # Validate wallet is configured
    if not user.wallet_id:
        logger.warning(f"⚠️ CONTRACT_HANDLER: User {user_id} has no wallet configured")
        await event.respond(
            f"⚠️ **Wallet Not Configured**\n\n"
            f"Detected: {chain.upper()} contract\n"
            f"🔗 `{address}`\n\n"
            f"❌ **You need to set a default wallet first!**\n\n"
            f"**Setup Steps:**\n"
            f"1. Use `/wallet` to see your wallets\n"
            f"2. Use `/selectwallet <wallet_id>` to set default\n\n"
            f"💡 Then send the contract address again to trade!"
        )
        return

    logger.info(f"✅ CONTRACT_HANDLER: Wallet configured: {user.wallet_id}")

    # Quick response
    status_msg = await event.respond(
        f"⚡ **{chain.upper()} Contract Detected**\n\n"
        f"🔗 `{address}`\n\n"
        f"💳 Wallet: `{user.wallet_id}`\n"
        f"🔒 Validating token safety..."
    )

    # SAFETY VALIDATION: Fetch pair info and validate token
    try:
        from token_validator import TokenValidator
        validator = TokenValidator()

        logger.info(f"🔒 CONTRACT_HANDLER: Calling get_pair_info API...")
        logger.info(f"   ├─ Chain: {chain}")
        logger.info(f"   └─ Pair: {address}")

        pair_info_response = await dbotx_client.get_pair_info(chain=chain, pair=address)

        logger.info(f"📦 CONTRACT_HANDLER: Pair info API response received")
        logger.info(f"   ├─ Has error: {pair_info_response.get('err', True)}")
        logger.info(f"   ├─ Response keys: {list(pair_info_response.keys())}")
        if not pair_info_response.get('err', True):
            res = pair_info_response.get('res', [])
            if res and len(res) > 0:
                pair_data = res[0]
                logger.info(f"   ├─ Token: {pair_data.get('name', 'Unknown')} ({pair_data.get('symbol', 'Unknown')})")
                logger.info(f"   ├─ Market Cap: ${pair_data.get('marketCap', 0):,.2f}")
                logger.info(f"   ├─ Holders: {pair_data.get('holders', 0)}")
                logger.info(f"   └─ Snipers: {pair_data.get('snipersCount', 0)}")

        logger.info(f"🔍 CONTRACT_HANDLER: Validating token against safety filters...")
        validation_result = validator.validate_token(
            pair_info_response=pair_info_response,
            detected_chain=chain,
            safety_settings=user.settings
        )

        if not validation_result.is_safe:
            logger.warning(f"🚫 CONTRACT_HANDLER: TOKEN REJECTED")
            logger.warning(f"   └─ Reason: {validation_result.rejection_reason}")
            await status_msg.edit(
                f"🚫 **Token Rejected by Safety Filters**\n\n"
                f"⛓️ Chain: {chain.upper()}\n"
                f"🔗 Contract: `{address}`\n\n"
                f"❌ **Reason:** {validation_result.rejection_reason}\n\n"
                f"💡 **Tip:** Adjust your safety filters with `/safety` if you want to trade this token.\n\n"
                f"🛡️ This filter protects you from scam/dead tokens!"
            )
            return

        logger.info(f"✅ CONTRACT_HANDLER: TOKEN VALIDATION PASSED")

    except Exception as val_error:
        logger.error(f"❌ CONTRACT_HANDLER: Validation error: {val_error}", exc_info=True)
        await status_msg.edit(
            f"⚠️ **Validation Error**\n\n"
            "Could not validate token safety: {str(val_error)}\n\n"
            "Trade cancelled for safety."
        )
        return

    # Update status
    await status_msg.edit(
        f"⚡ **{chain.upper()} Contract Validated**\n\n"
        f"🔗 `{address}`\n\n"
        f"💳 Wallet: `{user.wallet_id}`\n"
        f"⏳ Creating buy order..."
    )

    # Get chain-specific settings
    chain_settings = user.get_chain_settings(chain)
    amount = chain_settings.get('amountOrPercent', 0.1)
    logger.info(f"💰 CONTRACT_HANDLER: Buy amount: {amount} (chain: {chain})")
    logger.info(f"⚙️ CONTRACT_HANDLER: Chain settings for {chain.upper()}:")
    logger.info(f"   ├─ maxSlippage: {chain_settings.get('maxSlippage')}")
    logger.info(f"   ├─ jitoEnabled: {chain_settings.get('jitoEnabled')}")
    logger.info(f"   ├─ jitoTip: {chain_settings.get('jitoTip')}")
    logger.info(f"   └─ retries: {chain_settings.get('retries')}")

    try:
        logger.info(f"🚀 CONTRACT_HANDLER: Calling DBOTX fast_buy API...")
        logger.info(f"   ├─ Chain: {chain}")
        logger.info(f"   ├─ Pair: {address}")
        logger.info(f"   ├─ Wallet ID: {user.wallet_id}")
        logger.info(f"   └─ Amount: {amount}")

        # Execute trade via DBOTX API with chain-specific settings
        response = await dbotx_client.fast_buy(
            chain=chain,
            pair=address,
            wallet_id=user.wallet_id,
            amount=amount,
            user_settings=chain_settings
        )

        response_time = (time.time() - time.time()) * 1000 # This seems like a mistake, should be start_time
        logger.info(f"⏱️ CONTRACT_HANDLER: API response time: {response_time:.2f}ms")

        if response and not response.get('err', True):
            # Handle successful response
            res_data = response.get('res', {})
            order_id = res_data.get('id', 'Unknown') if isinstance(res_data, dict) else 'Unknown'

            logger.info(f"✅ CONTRACT_HANDLER: Trade SUCCESSFUL")
            logger.info(f"   ├─ Order ID: {order_id}")
            logger.info(f"   └─ Response data: {res_data}")

            # Store order in database with chain-specific settings
            storage.create_order(
                order_id=order_id,
                user_id=user_id,
                chain=chain,
                pair=address,
                order_type='buy',
                amount=amount,
                settings=chain_settings.copy()
            )

            logger.info(f"💾 CONTRACT_HANDLER: Order saved to database")

            await status_msg.edit(
                f"✅ **Buy Order Submitted**\n\n"
                f"⛓️ Chain: {chain.upper()}\n"
                f"🔗 Contract: `{address}`\n"
                f"💰 Amount: {amount}\n"
                f"🆔 Order ID: `{order_id}`\n\n"
                f"⚡ Your trade is being executed by DBOTX!\n\n"
                f"📊 Use /settings to adjust trading parameters"
            )
        else:
            # Handle API error with detailed message
            error_msg = response.get('message', 'Unknown API error') if response else 'No response from API'

            logger.error(f"❌ CONTRACT_HANDLER: Trade FAILED")
            logger.error(f"   ├─ Error message: {error_msg}")
            logger.error(f"   └─ Full response: {response}")

            # Provide specific guidance based on error
            help_text = ""
            if 'api key' in error_msg.lower() or 'unauthorized' in error_msg.lower():
                help_text = "💡 **Fix:** API key issue - contact admin"
            elif 'balance' in error_msg.lower() or 'insufficient' in error_msg.lower():
                help_text = "💡 **Fix:** Add funds to your wallet"
            elif 'wallet' in error_msg.lower():
                help_text = "💡 **Fix:** Check wallet configuration"
            else:
                help_text = "💡 **Troubleshooting:**\n• Check wallet balance\n• Verify API key is set\n• Ensure contract address is valid"

            await status_msg.edit(
                f"❌ **Trade Failed**\n\n"
                f"⛓️ Chain: {chain.upper()}\n"
                f"🔗 Contract: `{address}`\n\n"
                f"⚠️ **Error:** {error_msg}\n\n"
                f"{help_text}"
            )

    except Exception as e:
        logger.error(f"❌ CONTRACT_HANDLER: Exception during trade execution: {e}", exc_info=True)
        await status_msg.edit(
            f"❌ **Trade Execution Error**\n\n"
            f"Failed to execute buy order: {str(e)}\n\n"
            "Please check logs and try again."
        )


# ============================================================================
# CALLBACK QUERY HANDLER (BOT CLIENT)
# ============================================================================

async def callback_handler(callback_query):
    """Handle all callback queries from inline keyboards"""
    try:
        user_id = callback_query.sender_id

        # Owner-only restriction
        if OWNER_CHAT_ID and user_id != OWNER_CHAT_ID:
            await callback_query.answer("🚫 This bot is private.", alert=True)
            return

        user = storage.get_user(user_id)
        if not user:
            await callback_query.answer("Please start the bot first with /start", alert=True)
            return

        # Parse callback data with validation
        # Ensure callback_data is a string
        if isinstance(callback_query.data, str):
            callback_data = callback_query.data
        elif isinstance(callback_query.data, bytes):
            callback_data = callback_query.data.decode('utf-8')
        elif isinstance(callback_query.data, memoryview):
            callback_data = bytes(callback_query.data).decode('utf-8')
        else:
            callback_data = str(callback_query.data)

        data_parts = callback_data.split(':')
        if not data_parts:
            logger.error(f"Invalid callback data format: {callback_query.data}")
            await callback_query.answer("Invalid request format.")
            return

        action = data_parts[0]
        params = data_parts[1:] if len(data_parts) > 1 else []

        # Extract chain parameter if present (last parameter convention)
        # Don't strip chain for actions that need it in params
        chain = 'solana'
        if params and params[-1] in ['solana', 'bsc', 'ethereum', 'base', 'arbitrum', 'tron']:
            chain = params[-1]
            # Only strip chain from params for actions that use separate chain parameter
            # toggle_chain needs the chain in params[0], so don't strip it
            if action not in ['chain_config', 'toggle_chain']:
                params = params[:-1]

        # VERIFICATION GATE: Block unverified users from accessing bot features
        # Only allow recheck_membership and cancel_verification for unverified users
        if not user.is_verified and action not in ['recheck_membership', 'cancel_verification']:
            await callback_query.answer(
                "❌ Access Denied\n\n"
                "You need to verify your account first.\n"
                "Use /verify (first6)...(last4) to verify your wallet.",
                alert=True
            )
            return

        # Route with comprehensive error handling
        try:
            if action == 'chain_config':
                if not params:
                    await callback_query.answer("Missing chain parameter.")
                    return
                await handle_chain_config(callback_query, params[0], user)

            elif action == 'menu':
                if not params:
                    await callback_query.answer("Missing menu parameter.")
                    return
                await handle_menu_navigation(callback_query, params[0], user, chain)

            elif action == 'setting':
                if not params:
                    await callback_query.answer("Missing setting parameter.")
                    return
                setting_name = params[0]
                await handle_setting_selection(callback_query, setting_name, user, chain)

            elif action == 'input':
                if not params:
                    await callback_query.answer("Missing setting name for input.")
                    return
                setting_name = params[0]
                await handle_input_callback(callback_query, [setting_name, chain])

            elif action == 'toggle':
                if len(params) < 2:
                    await callback_query.answer("Invalid toggle parameters.")
                    return
                await handle_boolean_toggle(callback_query, params, user, chain)

            elif action == 'set':
                if len(params) < 2:
                    await callback_query.answer("Invalid setting parameters.")
                    return
                await handle_setting_value(callback_query, params, user, chain)

            elif action == 'action':
                if not params:
                    await callback_query.answer("Missing action name.")
                    return
                await handle_action_callback(callback_query, params[0])

            elif action == 'channel':
                if not params:
                    await callback_query.answer("Missing channel ID.")
                    return
                await handle_channel_callback(callback_query, params[0])

            elif action == 'toggle_channel':
                if not params:
                    await callback_query.answer("Missing channel ID.")
                    return
                await handle_toggle_channel_callback(callback_query, params[0])

            elif action == 'channel_filter':
                if not params:
                    await callback_query.answer("Missing channel ID.")
                    return
                await handle_channel_filter_callback(callback_query, params[0])

            elif action == 'set_filter':
                if len(params) < 2:
                    await callback_query.answer("Invalid set filter parameters.")
                    return
                await handle_set_filter_callback(callback_query, params)

            elif action == 'channel_amount':
                if not params:
                    await callback_query.answer("Missing channel ID.")
                    return
                await handle_channel_amount_callback(callback_query, params[0])

            elif action == 'set_channel_amount':
                if len(params) < 2:
                    await callback_query.answer("Invalid set channel amount parameters.")
                    return
                await handle_set_channel_amount_callback(callback_query, params)

            elif action == 'custom_channel_amount':
                if not params:
                    await callback_query.answer("Missing channel ID.")
                    return
                await handle_custom_channel_amount_callback(callback_query, params[0])

            elif action == 'default_channel_amount':
                if not params:
                    await callback_query.answer("Missing channel ID.")
                    return
                await handle_default_channel_amount_callback(callback_query, params[0])

            elif action == 'remove_channel':
                if not params:
                    await callback_query.answer("Missing channel ID.")
                    return
                await handle_remove_channel_callback(callback_query, params[0])

            elif action == 'channel_users':
                if not params:
                    await callback_query.answer("Missing channel ID.")
                    return
                await handle_channel_users_callback(callback_query, params[0])

            elif action == 'add_user_prompt':
                if not params:
                    await callback_query.answer("Missing channel ID.")
                    return
                await handle_add_user_prompt_callback(callback_query, params[0])

            elif action == 'remove_user':
                if len(params) < 2:
                    await callback_query.answer("Invalid parameters.")
                    return
                await handle_remove_user_callback(callback_query, params)

            elif action == "my_orders":
                await handle_my_orders_callback(callback_query)

            # No-op (disabled buttons)
            elif action == "detect_pinned":
                await handle_detect_pinned_callback(callback_query)

            elif action == "cancel_addsource":
                await handle_cancel_addsource_callback(callback_query)

            elif action == "confirm_pinned":
                if not params:
                    await callback_query.answer("Missing source ID.")
                    return
                await handle_confirm_pinned_callback(callback_query, params[0])

            elif action == "toggle_chain":
                if not params:
                    await callback_query.answer("Missing chain parameter.")
                    return
                await handle_toggle_chain_callback(callback_query, params[0])

            elif action == "recheck_membership":
                await handle_recheck_membership_callback(callback_query)

            elif action == "cancel_verification":
                await handle_cancel_verification_callback(callback_query)

            elif action == "noop":
                await callback_query.answer("This feature is not yet implemented", alert=True)

            else:
                logger.warning(f"Unknown callback action: {action}")
                await callback_query.answer("Unknown action", alert=True)

        except Exception as e:
            logger.error(f"Error handling callback action '{action}': {e}", exc_info=True)
            await callback_query.answer("An error occurred", alert=True)

    except Exception as e:
        logger.error(f"Error processing callback: {e}", exc_info=True)
        try:
            await callback_query.answer("An error occurred", alert=True)
        except: # Avoid errors if answer() itself fails
            pass


async def handle_chain_config(callback_query, chain: str, user):
    """Handle chain configuration selection - Direct to Safety Filters"""
    try:
        chain_name = chain.upper()
        text = f"🔒 **{chain_name} - Safety Filters**\n\nProtect yourself from scam/dead tokens with these filters."

        await callback_query.edit(
            text,
            buttons=TradingKeyboards.chain_safety_menu(chain, user)
        )
        await callback_query.answer(f"Opening {chain_name} Safety Setup")
    except Exception as e:
        logger.error(f"Chain config error: {e}")
        await callback_query.answer("Failed to load configuration.")


async def handle_menu_navigation(callback_query, menu_name: str, user, chain: str = 'solana'):
    """Handle menu navigation"""
    # Parse chain from menu_name if it contains colon (e.g., "buy_settings:solana")
    if ':' in menu_name:
        parts = menu_name.split(':')
        menu_name = parts[0]
        if len(parts) > 1 and parts[1] in ['solana', 'bsc', 'ethereum', 'base', 'tron']:
            chain = parts[1]

    # Generate appropriate menu
    if menu_name == "main":
        text = "🏠 **Main Menu**\n\nSelect an option:"
        buttons = TradingKeyboards.main_menu()
    elif menu_name == "settings":
        enabled_chains = user.settings.get('enabled_chains', ['solana', 'bsc', 'ethereum', 'base', 'tron'])
        enabled_names = ', '.join([c.upper() for c in enabled_chains])

        text = (
            "⚙️ **CHAIN SETTINGS**\n\n"
            "Toggle chains to enable/disable forwarding:\n\n"
            f"**Currently Enabled:** {enabled_names}\n\n"
            "✅ = Enabled (contracts forwarded)\n"
            "❌ = Disabled (contracts ignored)\n\n"
            "Only contracts from enabled chains will be processed and sent to DBOT."
        )
        buttons = TradingKeyboards.chain_selector_menu(user)
    elif menu_name == "buy_settings":
        chain_name = chain.upper()
        text = f"💰 **{chain_name} - Buy Settings**\n\nConfigure your buy parameters:"
        buttons = TradingKeyboards.buy_settings_menu(chain)
    elif menu_name == "buy_basic":
        chain_name = chain.upper()
        text = f"⚙️ **{chain_name} - Basic Trading Settings**"
        buttons = TradingKeyboards.buy_basic_menu(chain)
    elif menu_name == "buy_gas":
        chain_name = chain.upper()
        text = f"⛽ **{chain_name} - Gas & Fees Settings**"
        buttons = TradingKeyboards.buy_gas_menu(chain)
    elif menu_name == "buy_pnl":
        chain_name = chain.upper()
        text = f"📊 **{chain_name} - Take Profit & Stop Loss**"
        buttons = TradingKeyboards.buy_pnl_menu(chain)
    elif menu_name == "chain_safety":
        chain_name = chain.upper()
        text = f"🔒 **{chain_name} - Safety Filters**\n\nProtect yourself from scam/dead tokens with these filters."
        buttons = TradingKeyboards.chain_safety_menu(chain, user)
    elif menu_name == "volume_ratios":
        chain_name = chain.upper()
        text = (
            f"📊 **{chain_name} - Volume Ratios**\n\n"
            f"Skip tokens if sell volume exceeds buy volume:\n\n"
            f"• **1m**: 1 minute timeframe\n"
            f"• **5m**: 5 minute timeframe\n"
            f"• **1h**: 1 hour timeframe\n"
            f"• **6h**: 6 hour timeframe\n"
            f"• **24h**: 24 hour timeframe\n\n"
            f"Set to 0 to disable, or % threshold (e.g., 50% = skip if sell > buy by 50%)"
        )
        buttons = TradingKeyboards.volume_ratios_menu(chain, user)
    elif menu_name == "sell_settings":
        chain_name = chain.upper()
        text = f"💸 **{chain_name} - Sell Settings**"
        buttons = TradingKeyboards.sell_settings_menu(chain)
    elif menu_name == "sell_gas":
        chain_name = chain.upper()
        text = f"⛽ **{chain_name} - Sell Gas & Fees Settings**"
        buttons = TradingKeyboards.sell_gas_menu(chain)
    elif menu_name == "channels":
        channels = storage.get_user_channels(user.user_id)
        text = f"📡 **Channel Monitor** ({len(channels)} channels)"
        buttons = TradingKeyboards.channels_menu(channels)
    elif menu_name == "wallet":
        await handle_wallet_info_callback(callback_query)
        return
    elif menu_name == "orders":
        await handle_my_orders_callback(callback_query)
        return
    elif menu_name == "help":
        await handle_help_callback(callback_query)
        return
    else:
        await callback_query.answer("Unknown menu", alert=True)
        return

    await callback_query.edit(text, buttons=buttons)
    await callback_query.answer()







async def handle_setting_selection(callback_query, setting_name: str, user, chain: str = 'solana'):
    """Handle settings selection - show menu with preset values"""
    # Get current value for this chain
    current_value = user.get_setting(setting_name, chain=chain)
    current_display = format_setting_display(setting_name, current_value) if current_value is not None else "Not set"

    # Get metadata for user-friendly display
    from config import SETTING_METADATA
    metadata = SETTING_METADATA.get(setting_name, {})
    display_name = metadata.get('display_name', setting_name.replace('_', ' ').title())
    description = metadata.get('description', '')
    format_hint = metadata.get('format_hint', '')

    chain_name = chain.upper()

    # Build text with enhanced description
    text = f"**⚙️ {chain_name} - {display_name}**\n\n"

    if description:
        text += f"📝 {description}\n\n"

    text += f"**Current:** `{current_display}`\n\n"

    if format_hint:
        text += f"💡 {format_hint}\n\n"

    # Determine correct back menu and input type using SETTINGS_DESCRIPTOR
    from config import SETTINGS_DESCRIPTOR
    descriptor = SETTINGS_DESCRIPTOR.get(setting_name, {})
    back_menu = descriptor.get('parent_menu', 'buy_settings')  # Default to buy_settings if not found
    input_type = descriptor.get('input_type', 'numeric')

    # Add chain to back_menu
    back_menu_with_chain = f"{back_menu}:{chain}"

    # PHASE 2 FIX: Route boolean settings to toggle keyboard
    if input_type == 'boolean':
        text += "Toggle to enable/disable:"
        # Boolean settings use toggle keyboard
        current_bool = current_value if isinstance(current_value, bool) else False
        buttons = TradingKeyboards.boolean_setting(setting_name, current_bool, back_menu_with_chain, chain)
    elif input_type == 'complex':
        # Complex settings show instructional text only
        text += "Configure using custom input:"
        buttons = [
            [Button.inline("✏️ Custom Input", f"input:{setting_name}:{chain}".encode())],
            [Button.inline(f"{MENU_EMOJI['back']} Back", f"menu:{back_menu_with_chain}".encode())]
        ]
    else:
        text += "Select a preset value or enter a custom value:"
        # Numeric, percentage, string settings use numeric keyboard with suggestions
        buttons = TradingKeyboards.numeric_setting(setting_name, back_menu_with_chain, SETTING_SUGGESTIONS.get(setting_name), chain)

    await callback_query.edit(text, buttons=buttons)
    await callback_query.answer()


async def handle_boolean_toggle(callback_query, params: list, user, chain: str = 'solana'):
    """Handle boolean toggle"""
    if len(params) < 2:
        await callback_query.answer("Invalid toggle data", alert=True)
        return

    setting_name = params[0]
    new_value = params[1].lower() == 'true'
    # Chain is passed directly

    # Update setting in database for specific chain
    user.update_setting(setting_name, new_value, chain=chain)
    storage.update_user_settings(user.user_id, user.settings)

    status_text = "✅ Enabled" if new_value else "❌ Disabled"
    await callback_query.answer(f"{status_text}", alert=False)

    # Refresh the setting detail view with chain context
    await handle_setting_selection(callback_query, setting_name, user, chain)


async def handle_setting_value(callback_query, params: list, user, chain: str = 'solana'):
    """Handle value setting"""
    if len(params) < 2:
        await callback_query.answer("Invalid setting parameters.")
        return

    setting_name = params[0]
    value_str = params[1]
    # Chain is passed directly

    # Validate and convert value
    is_valid, converted_value, error = validate_settings_input(setting_name, value_str)

    if is_valid:
        # Update setting in database for specific chain
        user.update_setting(setting_name, converted_value, chain=chain)
        storage.update_user_settings(user.user_id, user.settings)

        await callback_query.answer(f"✅ Updated to {format_setting_display(setting_name, converted_value)}", alert=False)

        # Refresh the setting detail menu with chain context
        await handle_setting_selection(callback_query, setting_name, user, chain)
    else:
        await callback_query.answer(f"❌ {error}", alert=True)


async def handle_action_callback(callback_query, action_name):
    """Handle action buttons"""
    if action_name == "add_channel":
        # Legacy handler - kept for compatibility
        await callback_query.respond(
            "**📡 Add Channel to Monitor**\n\n"
            "Please forward any message from the channel you want to monitor."
        )
        user_states[callback_query.sender_id] = {'waiting_for': 'channel_forward'}
    elif action_name == "trigger_addchannel":
        # Directly invoke /addchannel command handler
        await addchannel_handler(callback_query)
        await callback_query.answer()
    elif action_name == "trigger_addsource":
        # Directly invoke /addsource command handler
        await addsource_handler(callback_query)
        await callback_query.answer()
    else:
        await callback_query.answer(f"Action {action_name} - coming soon!", alert=True)


async def handle_channel_callback(callback_query, channel_id):
    """Handle channel-specific actions"""
    if not channel_id:
        await callback_query.answer("Invalid channel ID", alert=True)
        return

    # Get channel details
    channel = storage.get_channel_subscription(callback_query.sender_id, int(channel_id))
    if not channel:
        await callback_query.answer("Channel not found", alert=True)
        return

    # Show channel settings
    text = (
        f"**📡 {channel.channel_title or channel.channel_username}**\n\n"
        f"Status: {'🟢 Active' if channel.is_active else '🔴 Inactive'}\n"
        f"Filter: {channel.filter_mode.value}\n"
        f"Trades: {channel.total_trades}"
    )
    buttons = TradingKeyboards.channel_settings(channel)

    await callback_query.edit(text, buttons=buttons)
    await callback_query.answer()


async def handle_my_orders_callback(callback_query):
    """Handle my orders button callback"""
    user_id = callback_query.sender_id
    user = storage.get_user(user_id)

    if not user:
        await callback_query.answer("Please start the bot first with /start", alert=True)
        return

    await callback_query.answer("📊 Loading your orders...", alert=False)

    try:
        orders = storage.get_user_orders(user_id, 10)

        if not orders:
            orders_text = (
                "📊 **Recent Orders**\n\n"
                "📝 No orders yet\n\n"
                "Start trading by pasting a contract address!"
            )
        else:
            orders_text = f"📊 **Recent Orders ({len(orders)} recent)**\n\n"

            for i, order in enumerate(orders, 1):
                status_emoji = {
                    'pending': '⏳',
                    'completed': '✅',
                    'failed': '❌'
                }.get(order.status, '❓')

                # Format order time
                time_diff = time.time() - order.created_at
                if time_diff < 60:
                    time_str = f"{int(time_diff)}s ago"
                elif time_diff < 3600:
                    time_str = f"{int(time_diff // 60)}m ago"
                else:
                    time_str = f"{int(time_diff // 3600)}h ago"

                # Format pair address
                pair_display = order.pair
                if len(pair_display) > 12:
                    pair_display = f"{pair_display[:8]}...{pair_display[-4:]}"

                orders_text += f"{i}. {status_emoji} **{order.order_type.upper()}** {order.chain.upper()}\n"
                orders_text += f"   🔗 `{pair_display}`\n"
                orders_text += f"   💰 {order.amount} | {time_str}\n\n"

        await callback_query.edit(orders_text, buttons=TradingKeyboards.main_menu())

    except Exception as e:
        logger.error(f"❌ Error loading orders: {e}")
        await callback_query.edit(
            "❌ **Error Loading Orders**\n\n"
            "Failed to retrieve your order history.\n\n"
            "Please try again later.",
            buttons=TradingKeyboards.main_menu()
        )


async def handle_help_callback(callback_query):
    """Handle help button callback"""
    help_text = (
        "📚 **Help & Commands**\n\n"
        "**🚀 Getting Started:**\n"
        "1. **Configure your DBOT bots:**\n"
        "   i. Bind a telegram account: Go to https://dbotx.com/dashboard/telegram_personal click in bind and you will generate a key, copy it\n"
        "   ii. Go to the chain's telegram dbot bot, click on 'I already have an account' button and paste the key\n"
        "   Here are the dbot bots for all chains:\n"
        "   • SOL: [@sol_dbot](https://t.me/sol_dbot?start=ref_85402573)\n"
        "   • ETH: [@dex_dbot](https://t.me/dex_dbot?start=ref_85402573)\n"
        "   • ARB: [@arb_dbot](https://t.me/arb_dbot?start=ref_85402573)\n"
        "   • BSC: [@bsc_dbot](https://t.me/bsc_dbot?start=ref_85402573)\n"
        "   • BASE: [@base2_dbot](https://t.me/base2_dbot?start=ref_85402573)\n"
        "   **IMPORTANT:** Make sure \"auto buy\" setting is toggled ON in each DBOT bot!\n"
        "2. **Add a Source:** Add a private/public channel or group to monitor\n\n"
        "**How it works:**\n"
        "• This bot monitors your channels/groups for token contracts\n"
        "• Validates contracts to be sure if it's real and toggled on in the settings menu\n"
        "• If toggled on, sends valid contracts to your DBOT bot\n"
        "• Your DBOT bot executes the trade based on your settings\n\n"
        "**Need more help?**\n"
        "Contact support! theweb3scout@gmail.com"
    )

    await callback_query.edit(help_text, buttons=TradingKeyboards.main_menu())
    await callback_query.answer()


async def handle_detect_pinned_callback(callback_query):
    """Detect most recently pinned dialog"""
    user_id = callback_query.sender_id
    user = storage.get_user(user_id)

    if not user:
        await callback_query.answer("User not found", alert=True)
        return

    # Check if user is in the correct state
    if user_id not in user_states or user_states[user_id].get('waiting_for') != 'pinned_source':
        await callback_query.answer("Please use /addsource to start", alert=True)
        return

    await callback_query.answer("🔍 Scanning for pinned chats...", alert=False)

    try:
        # Check 7-minute time window
        addsource_timestamp = user_states[user_id].get('timestamp', 0)
        current_time = time.time()
        time_elapsed = current_time - addsource_timestamp

        if time_elapsed > 420:  # 7 minutes = 420 seconds
            await callback_query.edit(
                "⏱️ **Time Window Expired**\n\n"
                "More than 7 minutes have passed since you used /addsource.\n\n"
                "**Solution:**\n"
                "1. Remove all pinned chats\n"
                "2. Use /addsource again\n"
                "3. Pin ONLY the target source\n"
                "4. Click Continue within 7 minutes\n\n"
                "This ensures the bot detects the correct chat.",
                buttons=[
                    [Button.inline("🔄 Start Over", b"cancel_addsource")]
                ]
            )
            return

        # Get all dialogs and find pinned ones
        pinned_dialogs = []
        async for dialog in _user_client.iter_dialogs(limit=100):
            if dialog.pinned:
                pinned_dialogs.append(dialog)

        if not pinned_dialogs:
            await callback_query.edit(
                "❌ **No Pinned Chats Found**\n\n"
                "Please pin the target group/channel to the top of your chat list, then try again.\n\n"
                "**How to Pin:**\n"
                "1. Long press on the chat\n"
                "2. Select 'Pin to top'\n"
                "3. Click Continue below\n\n"
                "**Troubleshooting:**\n"
                "If this keeps failing, remove ALL pinned chats and pin ONLY your target source.",
                buttons=[
                    [Button.inline("🔄 Try Again", b"detect_pinned")],
                    [Button.inline("❌ Cancel", b"cancel_addsource")]
                ]
            )
            return

        # Filter pinned dialogs to those with recent activity (within 7-minute window)
        time_threshold = current_time - 420  # 7 minutes ago
        recent_pinned = []

        for dialog in pinned_dialogs:
            if dialog.message and dialog.message.date:
                message_timestamp = dialog.message.date.timestamp()
                # Check if message was sent within the time window OR after /addsource was used
                if message_timestamp >= addsource_timestamp or message_timestamp >= time_threshold:
                    recent_pinned.append(dialog)

        # If no recent pinned chats, use all pinned chats but warn user
        if not recent_pinned:
            logger.warning(f"No pinned chats with recent activity for user {user_id}")
            recent_pinned = pinned_dialogs

        # Sort by last message date to find most recent activity
        recent_pinned.sort(key=lambda d: d.message.date if d.message else datetime(1970, 1, 1, tzinfo=timezone.utc), reverse=True)

        # Get the most recently active pinned chat
        target_dialog = recent_pinned[0]
        chat = target_dialog.entity

        # Extract chat details
        chat_id = chat.id
        chat_title = chat.title if hasattr(chat, 'title') else f"Chat {chat_id}"
        chat_username = chat.username if hasattr(chat, 'username') else None

        # Determine chat type
        from telethon.tl.types import Channel, Chat
        if isinstance(chat, Channel):
            if hasattr(chat, 'megagroup') and chat.megagroup:
                chat_type_str = "Supergroup"
            elif hasattr(chat, 'broadcast') and chat.broadcast:
                chat_type_str = "Channel"
            else:
                chat_type_str = "Channel"
        elif isinstance(chat, Chat):
            chat_type_str = "Group"
        else:
            chat_type_str = "Chat"

        # Check if already exists
        existing = storage.get_channel_subscription(user_id, chat_id)
        if existing:
            await callback_query.edit(
                f"❌ **Already Monitoring**\n\n"
                f"**{chat_title}** is already in your monitor list.\n\n"
                f"Status: {'🟢 Active' if existing.is_active else '🔴 Inactive'}\n"
                f"Use /channels to manage it.",
                buttons=TradingKeyboards.main_menu()
            )
            if user_id in user_states:
                del user_states[user_id]
            return

        # Store in user state for confirmation
        user_states[user_id].update({
            'chat_id': chat_id,
            'chat_title': chat_title,
            'chat_username': chat_username,
            'chat_type_str': chat_type_str
        })

        # Show confirmation
        username_str = f" (@{chat_username})" if chat_username else ""
        await callback_query.edit(
            f"✅ **Source Detected**\n\n"
            f"**Name:** {chat_title}{username_str}\n"
            f"**Type:** {chat_type_str}\n"
            f"**ID:** `{chat_id}`\n\n"
            f"📌 This was your most recently active pinned chat.\n\n"
            f"**Confirm:** Add this to your monitor list?",
            buttons=[
                [Button.inline("✅ Yes, Add It", f"confirm_pinned:{chat_id}".encode())],
                [Button.inline("❌ No, Cancel", b"cancel_addsource")]
            ]
        )

    except Exception as e:
        logger.error(f"Error detecting pinned source: {e}", exc_info=True)
        await callback_query.edit(
            "❌ **Detection Failed**\n\n"
            f"Error: {str(e)}\n\n"
            "Please try again or use /addchannel instead.",
            buttons=TradingKeyboards.main_menu()
        )
        if user_id in user_states:
            del user_states[user_id]


async def handle_confirm_pinned_callback(callback_query, chat_id_str):
    """Confirm and add pinned source to monitoring"""
    user_id = callback_query.sender_id
    user = storage.get_user(user_id)

    if not user:
        await callback_query.answer("User not found", alert=True)
        return

    # Check state
    if user_id not in user_states or user_states[user_id].get('waiting_for') != 'pinned_source':
        await callback_query.answer("Session expired. Please use /addsource again.", alert=True)
        return

    state = user_states[user_id]
    chat_id = int(chat_id_str)

    # Verify this matches what we detected
    if state.get('chat_id') != chat_id:
        await callback_query.answer("Mismatch detected. Please try again.", alert=True)
        return

    chat_title = state.get('chat_title', f"Chat {chat_id}")
    chat_username = state.get('chat_username')
    chat_type_str = state.get('chat_type_str', 'Channel')

    try:
        # Determine ChannelType enum
        channel_type = ChannelType.CHANNEL
        if 'supergroup' in chat_type_str.lower():
            channel_type = ChannelType.SUPERGROUP
        elif 'group' in chat_type_str.lower() and 'supergroup' not in chat_type_str.lower():
            channel_type = ChannelType.GROUP

        # Normalize ID (same as forward handler)
        normalized_id = chat_id
        if 'channel' in chat_type_str.lower() or 'supergroup' in chat_type_str.lower():
            if abs(chat_id) < 1000000000000:
                normalized_id = -1000000000000 - abs(chat_id)
            elif chat_id > 0:
                normalized_id = -1000000000000 - chat_id

        logger.info(f"📝 Source ID normalization: {chat_id} -> {normalized_id}")

        # Create subscription
        storage.create_channel_subscription(
            user_id=user_id,
            channel_id=normalized_id,
            channel_title=chat_title,
            channel_username=chat_username,
            channel_type=channel_type,
            is_active=True,
            filter_mode=FilterMode.ALL_MESSAGES
        )

        # Clear user state
        if user_id in user_states:
            del user_states[user_id]

        # Success message
        username_str = f" (@{chat_username})" if chat_username else ""
        await callback_query.edit(
            f"✅ **Source Added Successfully**\n\n"
            f"📡 **{chat_title}**{username_str} is now being monitored!\n\n"
            f"**Details:**\n"
            f"• Type: {chat_type_str}\n"
            f"• ID: {normalized_id}\n"
            f"• Filter: All messages\n\n"
            f"⚡ Monitoring will start immediately!\n\n"
            f"💡 Use /channels to configure advanced settings\n"
            f"🧪 Use /testchannel to verify monitoring",
            buttons=TradingKeyboards.main_menu()
        )

        logger.info(f"User {user_id} added source '{chat_title}' (ID: {normalized_id}) via pinned detection")

        # Re-register USER handlers with the new source
        if _user_client:
            try:
                await register_user_handlers(_user_client, _bot_client)
                logger.info("✅ USER handlers re-registered with new source")
            except Exception as reg_error:
                logger.warning(f"⚠️ Could not re-register USER handlers: {reg_error}")

    except Exception as e:
        logger.error(f"Error adding pinned source: {e}", exc_info=True)
        await callback_query.edit(
            "❌ **Failed to Add Source**\n\n"
            f"Error: {str(e)}\n\n"
            "Please try again or contact support.",
            buttons=TradingKeyboards.main_menu()
        )
        if user_id in user_states:
            del user_states[user_id]


async def handle_cancel_addsource_callback(callback_query):
    """Cancel add source operation"""
    user_id = callback_query.sender_id

    if user_id in user_states:
        del user_states[user_id]

    await callback_query.edit(
        "❌ **Operation Cancelled**\n\n"
        "No source was added.\n\n"
        "Use /addsource or /addchannel to try again.",
        buttons=TradingKeyboards.main_menu()
    )
    await callback_query.answer()


async def handle_recheck_membership_callback(callback_query):
    """Show registration message with wallet verification instructions (does NOT grant access)"""
    user_id = callback_query.sender_id
    user = storage.get_user(user_id)
    
    if not user:
        await callback_query.answer("User not found", alert=True)
        return
    
    await callback_query.answer()
    
    await callback_query.edit(
        "🤖 **Welcome to DBotX Auto Trader**\n\n"
        "I can scrape telegram channels and trade with your dbotx API\n\n"
        "📋 **Registration Required:**\n"
        "1. Create a new dbot account with https://dbotx.com/dashboard/login?referrer=85402573 (The link must be used to get access)\n"
        "2. Use your wallet address to verify: /verify (first6)...(last4)\n"
        "   Example: /verify 0x0ed9...eho3\n"
        "3. You should get access within a minute.\n\n"
        "💡 Use /help for more information"
    )
    logger.info(f"📋 User {user_id} shown registration message (still waiting for wallet verification)")


async def handle_cancel_verification_callback(callback_query):
    """Cancel verification process"""
    user_id = callback_query.sender_id
    
    # Clear state
    if user_id in user_states:
        del user_states[user_id]
    
    await callback_query.edit(
        "❌ **Verification Cancelled**\n\n"
        "You can try again anytime using /start"
    )
    
    await callback_query.answer("Cancelled", alert=False)


async def handle_toggle_chain_callback(callback_query, chain: str):
    """Toggle chain enable/disable status"""
    user_id = callback_query.sender_id
    user = storage.get_user(user_id)

    if not user:
        await callback_query.answer("User not found", alert=True)
        return

    # Get current enabled chains
    enabled_chains = user.settings.get('enabled_chains', ['solana', 'bsc', 'ethereum', 'base', 'tron'])

    # Toggle the chain
    if chain in enabled_chains:
        enabled_chains.remove(chain)
        status = "disabled"
        emoji = "❌"
    else:
        enabled_chains.append(chain)
        status = "enabled"
        emoji = "✅"

    # Update settings
    user.settings['enabled_chains'] = enabled_chains
    storage.update_user_settings(user_id, user.settings)

    # Show feedback
    await callback_query.answer(f"{emoji} {chain.upper()} {status}", alert=False)

    # Refresh the menu
    enabled_names = ', '.join([c.upper() for c in enabled_chains])
    settings_text = (
        "⚙️ **CHAIN SETTINGS**\n\n"
        "Toggle chains to enable/disable forwarding:\n\n"
        f"**Currently Enabled:** {enabled_names}\n\n"
        "✅ = Enabled (contracts forwarded)\n"
        "❌ = Disabled (contracts ignored)\n\n"
        "Only contracts from enabled chains will be processed and sent to DBOT."
    )

    await callback_query.edit(
        settings_text,
        buttons=TradingKeyboards.chain_selector_menu(user)
    )


# ============================================================================
# CHANNEL MANAGEMENT CALLBACKS
# ============================================================================

async def handle_toggle_channel_callback(callback_query, channel_id):
    """Handle channel enable/disable toggle"""
    if not channel_id:
        await callback_query.answer("Invalid channel ID", alert=True)
        return

    user_id = callback_query.sender_id
    user = storage.get_user(user_id)

    if not user:
        await callback_query.answer("User not found", alert=True)
        return

    # Toggle channel status
    new_status = storage.toggle_channel(user_id, int(channel_id))

    if new_status is None:
        await callback_query.answer("Channel not found", alert=True)
        return

    status_text = "enabled" if new_status else "disabled"
    await callback_query.answer(f"Channel {status_text}!", alert=False)

    # Refresh channel settings view
    await handle_channel_callback(callback_query, channel_id)


async def handle_channel_filter_callback(callback_query, channel_id):
    """Show filter mode selection menu"""
    if not channel_id:
        await callback_query.answer("Invalid channel ID", alert=True)
        return

    user_id = callback_query.sender_id
    subscription = storage.get_channel_subscription(user_id, int(channel_id))

    if not subscription:
        await callback_query.answer("Channel not found", alert=True)
        return

    text = f"**🔍 Filter Mode for {subscription.channel_title}**\n\n"
    text += f"Current: {subscription.filter_mode.value.replace('_', ' ').title()}\n\n"
    text += "Choose which messages to monitor:"

    buttons = TradingKeyboards.filter_mode_selection(int(channel_id))

    await callback_query.edit(text, buttons=buttons)
    await callback_query.answer()


async def handle_set_filter_callback(callback_query, params):
    """Apply selected filter mode"""
    if len(params) < 2:
        await callback_query.answer("Invalid filter parameters", alert=True)
        return

    channel_id = int(params[0])
    filter_mode = params[1]
    user_id = callback_query.sender_id

    # Update filter mode
    from models import FilterMode
    storage.update_channel_settings(
        user_id,
        channel_id,
        filter_mode=FilterMode(filter_mode)
    )

    await callback_query.answer(f"Filter updated to {filter_mode.replace('_', ' ').title()}!", alert=False)

    # Refresh channel settings
    await handle_channel_callback(callback_query, str(channel_id))


async def handle_channel_amount_callback(callback_query, channel_id):
    """Show channel amount setting menu"""
    if not channel_id:
        await callback_query.answer("Invalid channel ID", alert=True)
        return

    user_id = callback_query.sender_id
    subscription = storage.get_channel_subscription(user_id, int(channel_id))

    if not subscription:
        await callback_query.answer("Channel not found", alert=True)
        return

    current_amount = subscription.custom_buy_amount or "Using default"
    text = f"**💰 Buy Amount for {subscription.channel_title}**\n\n"
    text += f"Current: {current_amount}\n\n"
    text += "Select a custom amount for this channel or use default settings:"

    buttons = TradingKeyboards.channel_amount_setting(int(channel_id))

    await callback_query.edit(text, buttons=buttons)
    await callback_query.answer()


async def handle_set_channel_amount_callback(callback_query, params):
    """Set channel custom amount"""
    if len(params) < 2:
        await callback_query.answer("Invalid amount parameters", alert=True)
        return

    channel_id = int(params[0])
    amount = float(params[1])
    user_id = callback_query.sender_id

    # Update channel amount
    storage.update_channel_settings(
        user_id,
        channel_id,
        custom_buy_amount=amount
    )

    await callback_query.answer(f"Amount set to {amount} SOL!", alert=False)

    # Refresh channel settings
    await handle_channel_callback(callback_query, str(channel_id))


async def handle_custom_channel_amount_callback(callback_query, channel_id):
    """Prompt for custom channel amount input"""
    if not channel_id:
        await callback_query.answer("Invalid channel ID", alert=True)
        return

    user_id = callback_query.sender_id
    subscription = storage.get_channel_subscription(user_id, int(channel_id))

    if not subscription:
        await callback_query.answer("Channel not found", alert=True)
        return

    # Set user state
    user_states[user_id] = {
        'waiting_for': 'custom_channel_amount',
        'channel_id': int(channel_id)
    }

    # FIXED: Use respond() instead of callback_query.message.reply_text() for Telethon
    await callback_query.respond(
        f"**💰 Custom Amount for {subscription.channel_title}**\n\n"
        f"Please send the custom buy amount (in SOL):\n\n"
        f"Use /cancel to abort."
    )
    await callback_query.answer("💬 Send custom amount", alert=False)


async def handle_default_channel_amount_callback(callback_query, channel_id):
    """Clear custom amount (use default)"""
    if not channel_id:
        await callback_query.answer("Invalid channel ID", alert=True)
        return

    user_id = callback_query.sender_id

    # Clear custom amount
    storage.update_channel_settings(
        user_id,
        int(channel_id),
        custom_buy_amount=None
    )

    await callback_query.answer("Using default amount!", alert=False)

    # Refresh channel settings
    await handle_channel_callback(callback_query, str(channel_id))


async def handle_remove_channel_callback(callback_query, channel_id):
    """Remove channel from monitoring"""
    if not channel_id:
        await callback_query.answer("Invalid channel ID", alert=True)
        return

    user_id = callback_query.sender_id
    subscription = storage.get_channel_subscription(user_id, int(channel_id))

    if not subscription:
        await callback_query.answer("Channel not found", alert=True)
        return

    # Remove channel
    storage.remove_channel_subscription(user_id, int(channel_id))

    await callback_query.answer(f"Channel {subscription.channel_title} removed!", alert=True)

    # Go back to channels menu
    await channels_handler(callback_query)


# ============================================================================
# CHANNEL USER MANAGEMENT CALLBACKS
# ============================================================================

async def handle_channel_users_callback(callback_query, channel_id):
    """Show user management for channel"""
    if not channel_id:
        await callback_query.answer("Invalid channel ID", alert=True)
        return

    user_id = callback_query.sender_id
    subscription = storage.get_channel_subscription(user_id, int(channel_id))

    if not subscription:
        await callback_query.answer("Channel not found", alert=True)
        return

    allowed_users = subscription.allowed_user_ids or []

    text = f"**👥 Manage Users for {subscription.channel_title}**\n\n"
    text += f"Filter mode: **Specific Users**\n"
    text += f"Allowed users: **{len(allowed_users)}**\n\n"

    if allowed_users:
        text += "**Current allowed users:**\n"
        for uid in allowed_users[:10]:  # Show first 10
            text += f"• `{uid}`\n"
        if len(allowed_users) > 10:
            text += f"_...and {len(allowed_users) - 10} more_\n"
    else:
        text += "_No users added yet. Add user IDs to filter messages._\n"

    text += "\n💡 **Tip:** To find a user's ID, forward their message to @userinfobot"

    buttons = TradingKeyboards.channel_users_management(int(channel_id), allowed_users)

    await callback_query.edit(text, buttons=buttons)
    await callback_query.answer()


async def handle_add_user_prompt_callback(callback_query, channel_id):
    """Prompt to add a user via ID or username input"""
    if not channel_id:
        await callback_query.answer("Invalid channel ID", alert=True)
        return

    user_id = callback_query.sender_id
    subscription = storage.get_channel_subscription(user_id, int(channel_id))

    if not subscription:
        await callback_query.answer("Channel not found", alert=True)
        return

    # Set user state to wait for user ID/username input
    user_states[user_id] = {
        'waiting_for': 'user_id_input',
        'channel_id': int(channel_id)
    }

    await callback_query.respond(
        f"**👤 Add User to {subscription.channel_title}**\n\n"
        f"Please send the user's **ID** or **username**:\n\n"
        f"**Examples:**\n"
        f"• User ID: `123456789`\n"
        f"• Username: `@john` or `john`\n\n"
        f"💡 **Tip:** Use @userinfobot to find a user's ID\n\n"
        f"Use /cancel to abort."
    )
    await callback_query.answer("💬 Send user ID or username", alert=False)


async def handle_remove_user_callback(callback_query, params):
    """Remove a user from allowed list"""
    if len(params) < 2:
        await callback_query.answer("Invalid parameters", alert=True)
        return

    channel_id = int(params[0])
    user_to_remove = int(params[1])
    user_id = callback_query.sender_id

    subscription = storage.get_channel_subscription(user_id, channel_id)

    if not subscription:
        await callback_query.answer("Channel not found", alert=True)
        return

    # Remove user from allowed list
    allowed_users = subscription.allowed_user_ids or []
    if user_to_remove in allowed_users:
        allowed_users.remove(user_to_remove)

        # If no users left, reset filter mode to ALL_MESSAGES
        if len(allowed_users) == 0:
            storage.update_channel_settings(
                user_id,
                channel_id,
                allowed_user_ids=allowed_users,
                filter_mode=FilterMode.ALL_MESSAGES
            )
            await callback_query.answer(f"User removed! Filter reset to all messages.", alert=False)
        else:
            storage.update_channel_settings(
                user_id,
                channel_id,
                allowed_user_ids=allowed_users
            )
            await callback_query.answer(f"User {user_to_remove} removed!", alert=False)
    else:
        await callback_query.answer("User not in list", alert=True)

    # Refresh user management screen
    await handle_channel_users_callback(callback_query, str(channel_id))


# ============================================================================
# SAFETY FILTER CALLBACKS
# ============================================================================

async def handle_input_callback(callback_query, params):
    """Handle input prompts for settings"""
    if not params or len(params) == 0:
        await callback_query.answer("Invalid setting", alert=True)
        return

    setting_name = params[0]
    chain = params[1] if len(params) > 1 else 'solana'

    user_id = callback_query.sender_id
    user = storage.get_user(user_id)

    if not user:
        await callback_query.answer("User not found", alert=True)
        return

    # Set user state for input with chain context - FIXED: Now storing chain parameter
    user_states[user_id] = {'waiting_for': 'setting_input', 'setting_name': setting_name, 'chain': chain}

    # Get current value for this chain
    current_value = user.get_setting(setting_name, chain=chain)
    current_display = format_setting_display(setting_name, current_value) if current_value is not None else "Not set"

    # Define prompts with format hints
    prompts = {
        'amountOrPercent': "💵 Enter buy amount (e.g., 0.1 for 0.1 SOL):",
        'maxSlippage': "📊 Enter max slippage % (0-100, e.g., 10 for 10%):",
        'retries': "🔄 Enter number of retries (1-10):",
        'concurrentNodes': "⚡ Enter concurrent nodes (1-3):",
        'jitoTip': "💸 Enter MEV tip amount (e.g., 0.001):",
        'priorityFee': "⚡ Enter priority fee in SOL (or leave empty for auto):",
        'gasFeeDelta': "⛽ Enter extra gas amount (e.g., 5):",
        'maxFeePerGas': "⛽ Enter max gas price (e.g., 100):",
        'stopEarnPercent': "📈 Enter take profit % (0-100, e.g., 50 for 50%):",
        'stopLossPercent': "📉 Enter stop loss % (0-100, e.g., 30 for 30%):",
        'pnlOrderExpireDelta': "⏰ Enter order expiry time in ms (e.g., 3600000 for 1 hour):",
        'migrateSellPercent': "🚀 Enter migration sell % (0-100, e.g., 50 for 50%):",
        'devSellPercent': "👨‍💻 Enter dev sell amount % (0-100, e.g., 100 for 100%):",
        'market_cap_min': "💰 Enter minimum market cap in USD (e.g., 10000):",
        'market_cap_max': "💰 Enter maximum market cap in USD (e.g., 1000000):",
        'holders_min': "👥 Enter minimum number of holders (e.g., 50):",
        'snipers_max': "🎯 Enter maximum number of snipers (e.g., 10):",
        'volume_ratio_1m': "⏱️ Enter 1-minute volume ratio threshold % (e.g., 50):",
        'volume_ratio_5m': "⏱️ Enter 5-minute volume ratio threshold % (e.g., 60):",
        'volume_ratio_1h': "⏱️ Enter 1-hour volume ratio threshold % (e.g., 70):",
        'volume_ratio_6h': "⏱️ Enter 6-hour volume ratio threshold % (e.g., 80):",
        'volume_ratio_24h': "⏱️ Enter 24-hour volume ratio threshold % (e.g., 90):",
        'top10_holder_max': "📊 Enter maximum top 10 holder % (0-100, e.g., 80 for 80%):",
        'lp_burn_min': "🔥 Enter minimum LP burn % (0-100, e.g., 90 for 90%):",
    }

    prompt = prompts.get(setting_name, f"Enter value for {setting_name}:")

    # FIXED: Use respond() instead of callback_query.message.reply_text() for Telethon
    await callback_query.respond(
        f"**⚙️ Custom Input: {setting_name.replace('_', ' ').title()}**\n\n"
        f"Current: `{current_display}`\n\n"
        f"{prompt}\n\n"
        f"Use /cancel to abort."
    )
    await callback_query.answer("💬 Send your new value", alert=False)


# ============================================================================
# CHANNEL MONITORING HANDLER (USER CLIENT)
# ============================================================================

async def monitor_channel_messages(event):
    """Monitor messages from configured channels - USER client handler"""
    try:
        # Get channel ID from the message
        chat = await event.get_chat()
        channel_id = chat.id

        logger.info(f"WebContent message received from channel ID: {channel_id}")
        logger.info(f"WebContent Message preview: {event.message.text[:100] if event.message.text else '[Media]'}")

        # DEBUG: Log raw message object details
        logger.debug(f"WebContent Message object type: {type(event.message)}")
        logger.debug(f"WebContent Has .text: {hasattr(event.message, 'text')}")
        logger.debug(f"WebContent Has .message: {hasattr(event.message, 'message')}")

        if hasattr(event.message, 'text') and event.message.text:
            logger.debug(f"WebContent .text value: '{event.message.text}'")
            logger.debug(f"WebContent .text type: {type(event.message.text)}")
            logger.debug(f"WebContent .text length: {len(event.message.text)}")
            logger.debug(f"WebContent .text repr: {repr(event.message.text)}")
            logger.debug(f"WebContent .text bytes: {event.message.text.encode('utf-8')}")

        if hasattr(event.message, 'message') and event.message.message:
            logger.debug(f"WebContent .message value: '{event.message.message}'")
            logger.debug(f"WebContent .message type: {type(event.message.message)}")
            logger.debug(f"WebContent .message length: {len(event.message.message)}")
            logger.debug(f"WebContent .message repr: {repr(event.message.message)}")
            logger.debug(f"WebContent .message bytes: {event.message.message.encode('utf-8')}")

        # Get all subscriptions for this channel
        all_channels = storage.get_all_active_channels()

        # Normalize the incoming channel ID to match storage format
        incoming_id = int(channel_id)

        # Convert positive IDs to -100 format if needed
        if incoming_id > 0:
            normalized_event_id = -1000000000000 - incoming_id
        else:
            normalized_event_id = incoming_id

        logger.debug(f"WebContent Event channel ID: {channel_id} -> Normalized: {normalized_event_id}")

        for channel_sub in all_channels:
            stored_id = int(channel_sub.channel_id)

            logger.debug(f"WebContent Comparing: Event={normalized_event_id} vs Stored={stored_id} ({channel_sub.channel_title})")

            if stored_id == normalized_event_id:
                logger.info(f"WebContent MATCH FOUND! Processing for user {channel_sub.user_id}: {channel_sub.channel_title}")
                # Process the message
                await process_channel_message(event, channel_sub)
            else:
                logger.debug(f"WebContent No match for channel {channel_sub.channel_title}")

    except Exception as e:
        logger.error(f"Error in channel monitoring: {e}", exc_info=True)


async def send_contract_to_dbot(chain: str, address: str, user_id: int):
    """Send validated contract to appropriate DBOT bot"""
    logger.info(f"📤 SENDING CONTRACT TO DBOT BOT")
    logger.info(f"   ├─ Chain: {chain.upper()}")
    logger.info(f"   ├─ Address: {address}")
    logger.info(f"   └─ User ID: {user_id}")

    dbot_bots = {
        'solana': '@sol_dbot',
        'bsc': '@bsc_dbot',
        'ethereum': '@dex_dbot',
        'base': '@base2_dbot',
        'tron': '@tron_dbot',
        'arbitrum': '@arb_dbot'
    }

    target_bot = dbot_bots.get(chain)
    if not target_bot:
        logger.error(f"❌ No DBOT bot configured for chain: {chain}")
        return False

    try:
        logger.info(f"🤖 Target DBOT bot: {target_bot}")
        await _user_client.send_message(target_bot, address)
        logger.info(f"✅ Contract sent successfully to {target_bot}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send message to {target_bot}: {e}")
        return False


async def process_channel_message(event, channel_sub):
    """Process a message from a monitored channel"""
    logger.info(f"═══════════════════════════════════════════════════════════")
    logger.info(f"🔄 NEW MESSAGE DETECTED - STARTING PROCESSING PIPELINE")
    logger.info(f"═══════════════════════════════════════════════════════════")
    logger.info(f"📍 Channel: {channel_sub.channel_title}")
    logger.info(f"🆔 Channel ID: {channel_sub.channel_id}")
    logger.info(f"👤 User: {channel_sub.user_id}")
    logger.info(f"📊 Filter Mode: {channel_sub.filter_mode.value}")

    try:
        # STEP 1: EXTRACT MESSAGE TEXT
        logger.info(f"━━━ STEP 1: EXTRACTING MESSAGE TEXT ━━━")
        message_text = None

        if hasattr(event.message, 'message') and event.message.message:
            message_text = event.message.message
            logger.info(f"✅ Text extracted from .message attribute")
        elif hasattr(event.message, 'text') and event.message.text:
            message_text = event.message.text
            logger.info(f"✅ Text extracted from .text attribute")
        else:
            logger.warning(f"❌ No text found in message - ABORTING")
            return

        logger.info(f"📝 Message Length: {len(message_text)} characters")
        logger.info(f"📄 Message Preview: {message_text[:200]}")

        # STEP 2: CHECK FILTER MODE
        logger.info(f"━━━ STEP 2: CHECKING FILTER MODE ━━━")
        should_process = True
        filter_mode = channel_sub.filter_mode.value

        logger.info(f"🚦 Current Filter Mode: {filter_mode.upper()}")

        if filter_mode == "all":
            logger.info(f"✅ Filter Mode: ALL_MESSAGES - No filtering needed")
            should_process = True
        elif filter_mode == "admins":
            # Check if sender is actually a channel admin
            if not event.sender_id:
                logger.warning(f"   ❌ Filter mode: ADMINS - no sender_id in message")
                should_process = False
            else:
                try:
                    # Get channel entity
                    channel_entity = await _user_client.get_entity(channel_sub.channel_id)
                    # Get channel admins
                    admins = await _user_client.get_participants(channel_entity, filter=ChannelParticipantsAdmins)
                    admin_ids = [admin.id for admin in admins]

                    is_admin = event.sender_id in admin_ids
                    should_process = is_admin

                    if is_admin:
                        logger.info(f"   ✅ Filter mode: ADMINS - user {event.sender_id} is admin")
                    else:
                        logger.warning(f"   ❌ Filter mode: ADMINS - user {event.sender_id} not admin")
                except Exception as admin_check_error:
                    logger.error(f"   ❌ Failed to check admin status: {admin_check_error}")
                    should_process = False
        elif filter_mode == "users":
            sender_id = event.message.sender_id if hasattr(event.message, 'sender_id') else None
            if sender_id and sender_id in channel_sub.allowed_user_ids:
                should_process = True
                logger.info(f"   ✅ Filter mode: USERS - user {sender_id} in allowed list")
            else:
                should_process = False
                logger.warning(f"   ❌ Filter mode: USERS - user {sender_id if sender_id else 'None'} not in allowed list ({channel_sub.allowed_user_ids})")
        else:
            logger.warning(f"   ❓ Unknown filter mode: {filter_mode}")

        # CRITICAL: Stop processing if filter rejected message
        if not should_process:
            logger.info(f"━━━ FILTER REJECTED MESSAGE ━━━")
            logger.warning(f"🛑 Filter Mode '{filter_mode}' rejected this message")
            logger.info(f"═══════════════════════════════════════════════════════════")
            return

        # STEP 3: DETECT CONTRACT ADDRESS
        logger.info(f"━━━ STEP 3: DETECTING CONTRACT ADDRESS ━━━")
        logger.info(f"🔍 Calling detect_contract_address()...")
        logger.info(f"📝 Scanning text: {message_text[:150]}...")

        detection_start = time.time()
        detection_result = detect_contract_address(message_text)
        detection_time = (time.time() - detection_start) * 1000

        logger.info(f"⏱️ Contract detection took {detection_time:.2f}ms")
        logger.info(f"📊 Detection Result: {detection_result}")

        if not detection_result:
            logger.info(f"⚪ No contract address detected in message")
            logger.info(f"═══════════════════════════════════════════════════════════")
            return

        # Extract chain and address
        chain, address = detection_result
        logger.info(f"🎯 CHAIN: {chain.upper()}")
        logger.info(f"🔗 ADDRESS: {address}")

        # Get user for chain check
        user_id = channel_sub.user_id
        user = storage.get_user(user_id)

        if not user:
            logger.error(f"❌ User {user_id} NOT FOUND in database")
            logger.info(f"═══════════════════════════════════════════════════════════")
            return

        logger.info(f"✅ User found: {user_id}")

        # STEP 4: CHECK IF CHAIN IS ENABLED
        logger.info(f"━━━ STEP 4: CHECKING IF CHAIN IS ENABLED ━━━")
        enabled_chains = user.settings.get('enabled_chains', ['solana', 'bsc', 'ethereum', 'base', 'arbitrum', 'tron'])
        logger.info(f"📋 User's enabled chains: {enabled_chains}")
        logger.info(f"🔍 Checking if '{chain}' is enabled...")

        if chain not in enabled_chains:
            logger.warning(f"🚫 CHAIN '{chain.upper()}' IS DISABLED FOR USER {user_id}")
            logger.warning(f"❌ Contract rejected - chain not in enabled list")
            logger.info(f"═══════════════════════════════════════════════════════════")
            return

        logger.info(f"✅ CHAIN CHECK PASSED - '{chain.upper()}' is enabled")

        # STEP 4.5: VALIDATE VIA DEXSCREENER API (FAST PUBLIC CHECK)
        logger.info(f"━━━ STEP 4.5: VALIDATING VIA DEXSCREENER API ━━━")
        logger.info(f"🔍 Checking if pair exists on DexScreener...")

        from utils import validate_via_dexscreener

        dex_valid, dex_error, verified_token_address = await validate_via_dexscreener(chain, address)

        if not dex_valid:
            logger.warning(f"🚫 DEXSCREENER VALIDATION FAILED: {dex_error}")

            # Send rejection notification
            await _bot_client.send_message(
                user_id,
                f"🚫 **Pair Not Found on DexScreener**\n\n"
                f"📡 Channel: {channel_sub.channel_title}\n"
                f"⛓️ Chain: {chain.upper()}\n"
                f"🔗 Contract: `{address}`\n\n"
                f"❌ **Reason:** {dex_error}\n\n"
                f"💡 This pair doesn't exist on DexScreener or hasn't been indexed yet."
            )
            logger.info(f"═══════════════════════════════════════════════════════════")
            return

        logger.info(f"✅ DEXSCREENER VALIDATION PASSED - Pair exists")
        logger.info(f"🎯 VERIFIED TOKEN ADDRESS: {verified_token_address}")
        logger.info(f"📝 Original extracted address: {address}")
        logger.info(f"📝 Sending verified token address to DBOT bot")

        # STEP 5: SEND VERIFIED TOKEN ADDRESS TO DBOT BOT
        logger.info(f"━━━ STEP 5: SENDING VERIFIED TOKEN TO DBOT BOT ━━━")

        # Use the verified token address from DexScreener response
        send_success = await send_contract_to_dbot(chain, verified_token_address, user_id)

        if send_success:
            logger.info(f"✅ Token sent to DBOT successfully")

            # Update channel stats
            try:
                channel_sub.total_trades += 1
                channel_sub.last_message_at = time.time()
                storage.update_channel_subscription(channel_sub)
                logger.info(f"📊 Channel stats updated successfully")
            except Exception as stats_error:
                logger.error(f"⚠️ Failed to update channel stats (non-critical): {stats_error}")
        else:
            # Send failure notification
            await _bot_client.send_message(
                user_id,
                f"❌ **Failed to Send Token**\n\n"
                f"📡 Channel: {channel_sub.channel_title}\n"
                f"⛓️ Chain: {chain.upper()}\n"
                f"🔗 Token: `{verified_token_address}`\n\n"
                f"⚠️ Could not send to DBOT bot. Please try manually."
            )

        logger.info(f"═══════════════════════════════════════════════════════════")

    except Exception as e:
        logger.error(f"❌ Exception in process_channel_message: {e}", exc_info=True)