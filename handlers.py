"""
Message and Callback Handlers for Ultra-Fast Trading Bot
Speed-optimized handlers for instant trade execution
"""
import asyncio
import logging
import pyrogram
import time
import uuid
from pyrogram import filters
from pyrogram.client import Client
from pyrogram.enums import ParseMode
from pyrogram.types import Message, CallbackQuery
from pyrogram import errors
from models import storage
from api_client import client as dbotx_client
from keyboards import TradingKeyboards, SETTING_SUGGESTIONS
from models import ChannelSubscription, ChannelType, FilterMode
from utils import (
    detect_contract_address, validate_settings_input, format_setting_display,
    format_order_summary, generate_order_id, format_settings_summary,
    is_owner, log_trade_attempt, log_trade_result, PerformanceTimer,
    format_wallet_display
)
from config import DEFAULT_SETTINGS, OWNER_CHAT_ID

logger = logging.getLogger(__name__)

# Setup detailed trace logging to file
trace_logger = logging.getLogger('trace')
trace_file_handler = logging.FileHandler('trace_logs.log', encoding='utf-8')
trace_file_handler.setLevel(logging.DEBUG)
trace_formatter = logging.Formatter('%(asctime)s - [%(name)s] - %(levelname)s - %(message)s')
trace_file_handler.setFormatter(trace_formatter)
trace_logger.addHandler(trace_file_handler)
trace_logger.setLevel(logging.DEBUG)

# User state for handling multi-step inputs
user_states = {}


async def start_handler(client: Client, message: Message):
    """Handle /start command"""
    user_id = message.from_user.id

    # Create or update user
    user = storage.create_user(
        user_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        settings=DEFAULT_SETTINGS.copy()
    )

    welcome_text = (
        "🚀 **Ultra-Fast Trading Bot**\n\n"
        "⚡ **MTProto USER MODE - Maximum Speed**\n"
        "🔗 Paste contract addresses to buy instantly\n"
        "📡 Channel monitoring fully integrated\n"
        "⚙️ Configure settings with /settings\n"
        "🔑 Set your DBOTX API key with /setapikey\n\n"
        "**Supported Chains:**\n"
        "• Solana (SOL)\n"
        "• Ethereum (ETH)\n"
        "• Base (BASE)\n"
        "• BSC (BNB)\n"
        "• Tron (TRX)\n\n"
        "**Key Features:**\n"
        "• Single MTProto client = faster\n"
        "• Direct channel monitoring\n"
        "• Sub-200ms detection\n\n"
        "Ready for ultra-fast trading!\n\n"
        "✨ Powered by Vtechwriter — support us via our free tools! (Includes referral links)"
    )

    await message.reply_text(
        welcome_text,
        reply_markup=TradingKeyboards.main_menu()
    )


async def settings_handler(client: Client, message: Message):
    """Handle /settings command"""
    user_id = message.from_user.id
    user = storage.get_user(user_id)

    if not user:
        await start_handler(client, message)
        return

    settings_text = format_settings_summary(user.settings)

    await message.reply_text(
        settings_text,
        reply_markup=TradingKeyboards.main_menu()
    )


async def channels_handler(client: Client, message: Message):
    """Handle /channels command"""
    user_id = message.from_user.id
    user = storage.get_user(user_id)

    if not user:
        await start_handler(client, message)
        return

    channels = storage.get_user_channels(user_id)
    channels_text = "**📡 Channel Monitor**\n\n"

    if channels:
        channels_text += f"**Monitored Channels ({len(channels)}):**\n\n"
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

    await message.reply_text(
        channels_text,
        reply_markup=TradingKeyboards.channels_menu(channels)
    )


async def addchannel_handler(client: Client, message: Message):
    """Handle /addchannel command - Smart Channel Detection via Forwarded Message"""
    # Generate unique trace ID for this operation
    trace_id = str(uuid.uuid4())[:8]
    user_id = message.from_user.id
    
    trace_logger.info(f"[TRACE-{trace_id}] ===== ADD_CHANNEL_BUTTON_CLICKED =====")
    trace_logger.info(f"[TRACE-{trace_id}] User ID: {user_id}, Username: {message.from_user.username}, Message ID: {message.id}")
    
    try:
        user = storage.get_user(user_id)
        trace_logger.debug(f"[TRACE-{trace_id}] User lookup complete: {user is not None}")

        if not user:
            trace_logger.warning(f"[TRACE-{trace_id}] User {user_id} not found in storage, initializing...")
            await start_handler(client, message)
            return

        # Set user state to awaiting channel forward
        user_states[user_id] = {'waiting_for': 'channel_forward', 'trace_id': trace_id}
        trace_logger.info(f"[TRACE-{trace_id}] User state set to awaiting_channel_forward")

        response_text = (
            "**📡 Add Channel to Monitor**\n\n"
            "**Smart Channel Detection:**\n"
            "Please forward any message from the channel you want to monitor.\n\n"
            "**Benefits:**\n"
            "• Works with private channels and groups\n"
            "• Automatically gets real channel info\n"
            "• No need to know channel ID or username\n\n"
            "**Instructions:**\n"
            "1. Go to the channel you want to monitor\n"
            "2. Forward any message from that channel to me\n"
            "3. I'll extract the channel info and start monitoring\n\n"
            "⚡ Once added, the MTProto scraper will automatically detect new tokens and execute trades!\n\n"
            "Use /cancel to stop this process."
        )
        
        sent_msg = await message.reply_text(response_text)
        trace_logger.info(f"[TRACE-{trace_id}] ADD_CHANNEL_PROMPT_SENT - Message ID: {sent_msg.id}")
        trace_logger.info(f"[TRACE-{trace_id}] ===== ADD_CHANNEL_HANDLER_COMPLETE =====\n")
        
    except Exception as e:
        trace_logger.error(f"[TRACE-{trace_id}] ERROR in addchannel_handler: {str(e)}", exc_info=True)
        try:
            await message.reply_text("❌ An error occurred. Please try again.")
        except:
            pass


async def handle_forwarded_message(client: Client, message: Message):
    """Handle forwarded messages for channel addition"""
    # Generate unique trace ID - use existing one if available
    trace_id = str(uuid.uuid4())[:8]
    user_id = message.from_user.id
    
    trace_logger.info(f"[TRACE-{trace_id}] ===== FORWARD_MESSAGE_HANDLER_START =====")
    trace_logger.info(f"[TRACE-{trace_id}] FORWARDED_MESSAGE_RECEIVED - Message ID: {message.id}, User ID: {user_id}, Username: {message.from_user.username}")
    trace_logger.debug(f"[TRACE-{trace_id}] Message Details - Chat ID: {message.chat.id}, Timestamp: {message.date}")
    
    try:
        user = storage.get_user(user_id)
        trace_logger.debug(f"[TRACE-{trace_id}] USER_LOOKUP - Found: {user is not None}")

        if not user:
            trace_logger.warning(f"[TRACE-{trace_id}] VALIDATION_FAILED - User {user_id} not found in storage")
            trace_logger.info(f"[TRACE-{trace_id}] ===== FORWARD_MESSAGE_HANDLER_END (NO_USER) =====\n")
            return

        # Check if user is awaiting channel forward
        awaiting = user_id in user_states and user_states[user_id].get('waiting_for') == 'channel_forward'
        trace_logger.debug(f"[TRACE-{trace_id}] AWAITING_STATE_CHECK - User awaiting forward: {awaiting}")
        
        if not awaiting:
            trace_logger.info(f"[TRACE-{trace_id}] STATE_MISMATCH - User not in awaiting_channel_forward state, ignoring message")
            trace_logger.info(f"[TRACE-{trace_id}] ===== FORWARD_MESSAGE_HANDLER_END (NOT_AWAITING) =====\n")
            return

        # Validate forwarded message has source chat
        if not message.forward_from_chat:
            trace_logger.error(f"[TRACE-{trace_id}] VALIDATION_FAILED - No forward_from_chat found in message")
            error_response = (
                "❌ **Invalid Forward**\n\n"
                "Please forward a message from the channel you want to monitor.\n\n"
                "The message must be forwarded from a channel or group, not from a user."
            )
            trace_logger.debug(f"[TRACE-{trace_id}] ERROR_RESPONSE - Sending validation error")
            error_msg = await message.reply_text(error_response)
            trace_logger.info(f"[TRACE-{trace_id}] ERROR_RESPONSE_SENT - Message ID: {error_msg.id}")
            trace_logger.info(f"[TRACE-{trace_id}] ===== FORWARD_MESSAGE_HANDLER_END (VALIDATION_ERROR) =====\n")
            return

        chat = message.forward_from_chat
        channel_id = chat.id
        chat_type_str = chat.type.name if hasattr(chat.type, 'name') else str(chat.type)
        
        trace_logger.info(f"[TRACE-{trace_id}] SOURCE_CHAT_EXTRACTED - Channel ID: {channel_id}, Type: {chat_type_str}, Title: {chat.title}, Username: {chat.username}")

        # Check if channel already exists
        trace_logger.debug(f"[TRACE-{trace_id}] DUPLICATE_CHECK_START - Checking if channel {channel_id} already monitored")
        existing = storage.get_channel_subscription(user_id, channel_id)
        
        if existing:
            trace_logger.warning(f"[TRACE-{trace_id}] DUPLICATE_DETECTED - Channel {channel_id} already exists (DB ID: {existing.id})")
            storage.clear_user_state(user_id)
            dup_response = (
                f"❌ **Channel Already Monitored**\n\n"
                f"**{existing.channel_title}** is already in your monitor list.\n\n"
                f"Status: {'🟢 Active' if existing.is_active else '🔴 Inactive'}\n"
                f"Trades: {existing.total_trades}"
            )
            trace_logger.debug(f"[TRACE-{trace_id}] DUPLICATE_RESPONSE - Sending duplicate error")
            dup_msg = await message.reply_text(dup_response)
            trace_logger.info(f"[TRACE-{trace_id}] DUPLICATE_RESPONSE_SENT - Message ID: {dup_msg.id}")
            trace_logger.info(f"[TRACE-{trace_id}] ===== FORWARD_MESSAGE_HANDLER_END (DUPLICATE) =====\n")
            return

        trace_logger.debug(f"[TRACE-{trace_id}] DUPLICATE_CHECK_PASSED - Channel is new, proceeding")

        # Determine channel type
        channel_type = ChannelType.CHANNEL
        if chat.type.name == 'GROUP':
            channel_type = ChannelType.GROUP
        elif chat.type.name == 'SUPERGROUP':
            channel_type = ChannelType.SUPERGROUP
        
        trace_logger.debug(f"[TRACE-{trace_id}] CHANNEL_TYPE_DETERMINED - Type: {channel_type.value}")

        # Create new channel subscription with authentic data
        trace_logger.debug(f"[TRACE-{trace_id}] DB_INSERT_START - Creating ChannelSubscription record")
        subscription = storage.create_channel_subscription(
            user_id=user_id,
            channel_id=channel_id,
            channel_title=chat.title,
            channel_username=chat.username,
            channel_type=channel_type,
            is_active=True,
            filter_mode=FilterMode.ALL_MESSAGES
        )
        trace_logger.info(f"[TRACE-{trace_id}] DB_INSERT_SUCCESS - Channel subscription created with ID: {subscription.id}")

        # Clear user state
        if user_id in user_states:
            del user_states[user_id]
        trace_logger.debug(f"[TRACE-{trace_id}] USER_STATE_CLEARED - Awaiting state removed")

        # Format success message
        channel_info = f"**{chat.title}**"
        if chat.username:
            channel_info += f" (@{chat.username})"

        success_response = (
            f"✅ **Channel Added Successfully**\n\n"
            f"📡 {channel_info} is now being monitored!\n\n"
            f"**Channel Details:**\n"
            f"• Type: {channel_type.value.title()}\n"
            f"• ID: {channel_id}\n"
            f"• Filter: All messages\n\n"
            f"⚡ The MTProto scraper will automatically detect new tokens and execute trades.\n\n"
            f"🔧 Use /channels to configure advanced settings."
        )
        trace_logger.debug(f"[TRACE-{trace_id}] SUCCESS_RESPONSE_PREPARED - Length: {len(success_response)} chars")
        
        success_msg = await message.reply_text(success_response)
        trace_logger.info(f"[TRACE-{trace_id}] SUCCESS_RESPONSE_SENT - Message ID: {success_msg.id}")
        trace_logger.info(f"[TRACE-{trace_id}] OPERATION_COMPLETE - {channel_type.value.upper()} '{chat.title}' (ID: {channel_id}) now monitored")
        trace_logger.info(f"[TRACE-{trace_id}] ===== FORWARD_MESSAGE_HANDLER_END (SUCCESS) =====\n")
        
        logger.info(f"User {user_id} added channel '{chat.title}' (ID: {channel_id}) via forwarded message")

    except Exception as e:
        trace_logger.error(f"[TRACE-{trace_id}] UNHANDLED_ERROR - {str(e)}", exc_info=True)
        logger.error(f"Error processing forwarded message for user {user_id}: {e}")
        if user_id in user_states:
            del user_states[user_id]
        
        error_response = (
            "❌ **Error Processing Channel**\n\n"
            "Failed to add channel from forwarded message. Please try again or contact support."
        )
        trace_logger.debug(f"[TRACE-{trace_id}] ERROR_RESPONSE_SEND - Attempting to send error response")
        try:
            error_msg = await message.reply_text(error_response)
            trace_logger.info(f"[TRACE-{trace_id}] ERROR_RESPONSE_SENT - Message ID: {error_msg.id}")
        except Exception as send_error:
            trace_logger.error(f"[TRACE-{trace_id}] ERROR_RESPONSE_FAILED - Could not send: {str(send_error)}")
        finally:
            trace_logger.info(f"[TRACE-{trace_id}] ===== FORWARD_MESSAGE_HANDLER_END (ERROR) =====\n")


async def cancel_handler(client: Client, message: Message):
    """Handle /cancel command"""
    user_id = message.from_user.id
    user = storage.get_user(user_id)

    if not user:
        await start_handler(client, message)
        return

    # Clear any pending states
    if user_id in user_states:
        del user_states[user_id]

    await message.reply_text(
        "✅ **Operation Cancelled**\n\n"
        "All pending operations have been cancelled."
    )


async def setapikey_handler(client: Client, message: Message):
    """Handle /setapikey command"""
    user_id = message.from_user.id

    # Check if user is owner
    if not is_owner(user_id):
        await message.reply_text("❌ Only the bot owner can set the API key.")
        return

    # Extract API key from command
    command_parts = message.text.split(maxsplit=1)
    if len(command_parts) < 2:
        await message.reply_text(
            "**🔑 Set DBOTX API Key**\n\n"
            "Usage: `/setapikey YOUR_API_KEY_HERE`\n\n"
            "Example: `/setapikey dbotx_1234567890abcdef`\n\n"
            "⚠️ Make sure to delete this message after setting the key for security."
        )
        return

    api_key = command_parts[1].strip()

    # Set the API key
    dbotx_client.set_api_key(api_key)

    # Test the API key
    api_healthy = await dbotx_client.health_check()

    if api_healthy:
        await message.reply_text(
            "✅ **API Key Set Successfully**\n\n"
            "DBOTX API connection verified and ready for trading!\n\n"
            "⚠️ Please delete your message containing the API key for security."
        )
        logger.info("✅ DBOTX API key configured successfully")
    else:
        await message.reply_text(
            "❌ **API Key Test Failed**\n\n"
            "The provided API key could not connect to DBOTX.\n"
            "Please check your key and try again.\n\n"
            "⚠️ Please delete your message containing the API key for security."
        )
        logger.error("❌ DBOTX API key test failed")


async def contract_handler(client: Client, message: Message):
    """Handle contract address messages - CORE TRADING FUNCTION"""
    user_id = message.from_user.id

    # Verify user exists
    user = storage.get_user(user_id)
    if not user:
        await message.reply_text(
            "❌ Please start the bot first with /start",
            reply_markup=TradingKeyboards.main_menu()
        )
        return

    # Check if user has wallet configured
    if not user.wallet_id:
        await message.reply_text(
            "❌ Please configure your wallet first in settings",
            reply_markup=TradingKeyboards.main_menu()
        )
        return

    with PerformanceTimer("contract_detection"):
        contract_info = detect_contract_address(message.text)

    if not contract_info:
        return  # Not a contract address, ignore

    chain, address = contract_info

    # Get user buy amount
    amount = user.get_setting('amountOrPercent', 0.1)

    # Generate order ID
    order_id = generate_order_id()

    # Log trade attempt
    log_trade_attempt(user_id, chain, address, amount)

    # Create order record
    order = storage.create_order(
        order_id=order_id,
        user_id=user_id,
        chain=chain,
        pair=address,
        order_type='buy',
        amount=amount,
        settings=user.settings.copy()
    )

    # Send immediate confirmation
    confirmation_text = (
        f"⚡ **FAST BUY EXECUTING**\n\n"
        f"🔗 Contract: `{address}`\n"
        f"🌐 Chain: {chain.upper()}\n"
        f"💰 Amount: {amount}\n"
        f"🆔 Order: `{order_id}`\n\n"
        f"⏳ Executing trade..."
    )

    status_message = await message.reply_text(
        confirmation_text
    )

    # Execute trade asynchronously
    asyncio.create_task(execute_fast_buy(
        order_id, user_id, chain, address, amount, user.settings, status_message
    ))


async def execute_fast_buy(order_id: str, user_id: int, chain: str, address: str,
                          amount: float, user_settings: dict, status_message):
    """Execute fast buy order with API call"""
    start_time = time.time()

    try:
        # Get user wallet
        user = storage.get_user(user_id)
        if not user or not user.wallet_id:
            raise Exception("No wallet configured")

        # Execute trade via DBOTX API
        with PerformanceTimer("api_fast_buy"):
            response = await dbotx_client.fast_buy(
                chain=chain,
                pair=address,
                wallet_id=user.wallet_id,
                amount=amount,
                user_settings=user_settings
            )

        response_time = (time.time() - start_time) * 1000

        if response.get('err', True):
            error_msg = response.get('message', 'Unknown error')
            storage.update_order_status(order_id, 'failed', error_msg)
            log_trade_result(order_id, False, response_time, error_msg)

            result_text = (
                f"❌ **TRADE FAILED**\n\n"
                f"🆔 Order: `{order_id}`\n"
                f"⚠️ Error: {error_msg}\n"
                f"⏱️ Response: {response_time:.0f}ms"
            )
        else:
            trade_id = response.get('res', {}).get('id', 'unknown')
            storage.update_order_status(order_id, 'completed')
            log_trade_result(order_id, True, response_time)

            result_text = (
                f"✅ **TRADE COMPLETED**\n\n"
                f"🆔 Order: `{order_id}`\n"
                f"🔗 Trade ID: `{trade_id}`\n"
                f"⚡ Speed: {response_time:.0f}ms\n\n"
                f"🎉 Successfully bought on {chain.upper()}!"
            )

    except Exception as e:
        error_msg = str(e)
        response_time = (time.time() - start_time) * 1000
        storage.update_order_status(order_id, 'failed', error_msg)
        log_trade_result(order_id, False, response_time, error_msg)

        result_text = (
            f"❌ **TRADE FAILED**\n\n"
            f"🆔 Order: `{order_id}`\n"
            f"⚠️ Error: {error_msg}\n"
            f"⏱️ Time: {response_time:.0f}ms"
        )

    # Update status message
    try:
        await status_message.edit_text(
            result_text
        )
    except Exception as e:
        logger.error(f"Failed to update status message: {e}")


async def callback_handler(client: Client, callback_query: CallbackQuery):
    """Handle all callback queries with Fortune 500-grade error resilience"""
    user_id = None

    try:
        user_id = callback_query.from_user.id

        # Validate callback data exists
        if not callback_query.data:
            logger.warning(f"Empty callback data from user {user_id}")
            await callback_query.answer("Invalid request. Please try again.")
            return

        # Ensure user exists with recovery
        user = storage.get_user(user_id)
        if not user:
            logger.warning(f"User {user_id} not found, attempting auto-recovery")
            # Auto-create user for recovery
            user = storage.create_user(
                user_id=user_id,
                username=callback_query.from_user.username,
                first_name=callback_query.from_user.first_name,
                last_name=callback_query.from_user.last_name,
                settings=DEFAULT_SETTINGS.copy()
            )
            await callback_query.answer("Session recovered. Please try again.")
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

        # Route with comprehensive error handling
        try:
            if action == 'menu':
                if not params:
                    await callback_query.answer("Missing menu parameter.")
                    return
                await handle_menu_navigation(callback_query, params[0], user)

            elif action == 'setting':
                if not params:
                    await callback_query.answer("Missing setting parameter.")
                    return
                await handle_setting_selection(callback_query, params[0], user)

            elif action == 'toggle':
                if len(params) < 2:
                    await callback_query.answer("Invalid toggle parameters.")
                    return
                await handle_boolean_toggle(callback_query, params, user)

            elif action == 'set':
                if len(params) < 2:
                    await callback_query.answer("Invalid setting parameters.")
                    return
                await handle_setting_value(callback_query, params, user)

            elif action == 'input':
                if not params:
                    await callback_query.answer("Missing input parameter.")
                    return
                await handle_custom_input(callback_query, params[0], user)

            elif action == 'wallet':
                if not params:
                    await callback_query.answer("Missing wallet parameter.")
                    return
                await handle_wallet_selection(callback_query, params[0], user)

            elif action == 'channel':
                if not params:
                    await callback_query.answer("Missing channel parameter.")
                    return
                await handle_channel_settings(callback_query, int(params[0]), user)

            elif action == 'toggle_channel':
                if not params:
                    await callback_query.answer("Missing channel parameter.")
                    return
                await handle_toggle_channel(callback_query, int(params[0]), user)

            elif action == 'channel_filter':
                if not params:
                    await callback_query.answer("Missing channel parameter.")
                    return
                await handle_channel_filter(callback_query, int(params[0]), user)

            elif action == 'set_filter':
                if len(params) < 2:
                    await callback_query.answer("Invalid filter parameters.")
                    return
                await handle_set_filter(callback_query, int(params[0]), params[1], user)

            elif action == 'channel_amount':
                if not params:
                    await callback_query.answer("Missing channel parameter.")
                    return
                await handle_channel_amount(callback_query, int(params[0]), user)

            elif action == 'set_channel_amount':
                if len(params) < 2:
                    await callback_query.answer("Invalid amount parameters.")
                    return
                await handle_set_channel_amount(callback_query, int(params[0]), float(params[1]), user)

            elif action == 'default_channel_amount':
                if not params:
                    await callback_query.answer("Missing channel parameter.")
                    return
                await handle_default_channel_amount(callback_query, int(params[0]), user)

            elif action == 'remove_channel':
                if not params:
                    await callback_query.answer("Missing channel parameter.")
                    return
                await handle_remove_channel(callback_query, int(params[0]), user)

            elif action == 'add_channel':
                await handle_add_channel_prompt(callback_query, user)

            elif action == 'action':
                if not params:
                    await callback_query.answer("Missing action parameter.")
                    return
                await handle_action(callback_query, params[0], user)

            elif action == 'order':
                if not params:
                    await callback_query.answer("Missing order parameter.")
                    return
                await handle_order_view(callback_query, params[0], user)

            elif action == 'confirm':
                if not params:
                    await callback_query.answer("Missing confirmation parameter.")
                    return
                await handle_confirmation(callback_query, params, user)

            elif action == 'noop':
                await callback_query.answer()

            else:
                logger.warning(f"Unknown callback action: {action} from user {user_id}")
                await callback_query.answer("Unknown action. Please refresh and try again.")

        except asyncio.TimeoutError:
            logger.error(f"Timeout in callback action '{action}' for user {user_id}")
            await safe_callback_answer(callback_query, "Request timed out. Please try again.")

        except Exception as action_error:
            logger.error(f"Error in callback action '{action}' for user {user_id}: {action_error}")
            await safe_callback_answer(callback_query, f"Action failed: {str(action_error)[:50]}...")

    except errors.BadRequest as bad_req:
        logger.error(f"Telegram BadRequest in callback for user {user_id}: {bad_req}")
        # Don't answer callback to avoid further errors

    except errors.Forbidden as forbidden:
        logger.error(f"Telegram Forbidden in callback for user {user_id}: {forbidden}")
        # User blocked bot, can't respond

    except errors.FloodWait as flood:
        wait_time = int(flood.value) if hasattr(flood, 'value') else 60
        logger.warning(f"Telegram FloodWait in callback for user {user_id}: {wait_time}s")
        await asyncio.sleep(wait_time)
        try:
            await callback_query.answer("Server busy. Please try again in a moment.")
        except:
            pass

    except Exception as critical_error:
        logger.critical(f"Critical callback error for user {user_id}: {critical_error}", exc_info=True)
        await safe_callback_answer(callback_query, "System error. Please restart the bot.")


async def safe_callback_answer(callback_query: CallbackQuery, text: str, show_alert: bool = False):
    """Safely answer callback queries with error handling"""
    try:
        await callback_query.answer(text, show_alert=show_alert)
    except errors.BadRequest:
        # Callback already answered or expired
        pass
    except Exception as e:
        logger.error(f"Failed to answer callback: {e}")


async def handle_menu_navigation(callback_query: CallbackQuery, menu_name: str, user):
    """Handle menu navigation with comprehensive error handling"""
    try:
        keyboard = None
        text = None

        if menu_name == 'main':
            keyboard = TradingKeyboards.main_menu()
            text = format_settings_summary(user.settings)

        elif menu_name == 'buy_settings':
            keyboard = TradingKeyboards.buy_settings_menu()
            text = "**💰 BUY SETTINGS**\n\nChoose a category to configure:"

        elif menu_name == 'buy_basic':
            keyboard = TradingKeyboards.buy_basic_menu()
            text = "**🚀 Basic Trading Settings**\n\nConfigure core trading parameters:"

        elif menu_name == 'buy_gas':
            keyboard = TradingKeyboards.buy_gas_menu()
            text = "**⛽ Gas & Fees Settings**\n\nOptimize gas and MEV protection:"

        elif menu_name == 'buy_pnl':
            keyboard = TradingKeyboards.buy_pnl_menu()
            text = "**🎯 Take Profit & Stop Loss**\n\nSet up automated PnL management:"

        elif menu_name == 'sell_settings':
            keyboard = TradingKeyboards.sell_settings_menu()
            text = "**📤 SELL SETTINGS**\n\nConfigure sell automation:"

        elif menu_name == 'orders':
            try:
                orders = storage.get_user_orders(user.user_id, 10)
                keyboard = TradingKeyboards.orders_list(orders)
                text = "**📊 Recent Orders**\n\nYour trading history:"
            except Exception as e:
                logger.error(f"Failed to load orders for user {user.user_id}: {e}")
                keyboard = TradingKeyboards.main_menu()
                text = "**❌ Failed to load orders**\n\nDatabase error occurred. Please try again."

        elif menu_name == 'wallet':
            try:
                # Fetch wallets from all supported chains
                all_wallets = []
                chains = ['solana', 'ethereum', 'bsc', 'base', 'tron']
                
                for chain in chains:
                    response = await asyncio.wait_for(
                        dbotx_client.get_wallets(wallet_type=chain, page=0, size=10),
                        timeout=10.0
                    )
                    if response and not response.get('err', True):
                        wallets = response.get('res', [])
                        for wallet in wallets:
                            wallet['chain'] = chain
                            all_wallets.append(wallet)
                
                if not all_wallets:
                    text = "⚠️ **No Wallets Found**\n\nYou don't have any wallets configured in DBOTX yet.\n\nPlease create wallets in the DBOTX dashboard first."
                    keyboard = TradingKeyboards.main_menu()
                else:
                    keyboard = TradingKeyboards.wallet_selection(all_wallets)
                    text = f"**💳 Wallet Selection ({len(all_wallets)} wallets)**\n\nChoose your trading wallet:"
            except asyncio.TimeoutError:
                text = "❌ **Request Timeout**\n\nWallet service is slow. Please try again."
                keyboard = TradingKeyboards.main_menu()
            except Exception as e:
                logger.error(f"Wallet API error for user {user.user_id}: {e}")
                text = "❌ **API Connection Failed**\n\nCannot reach wallet service. Check connection."
                keyboard = TradingKeyboards.main_menu()

        elif menu_name == 'channels':
            try:
                channels = storage.get_user_channels(user.user_id)
                keyboard = TradingKeyboards.channels_menu(channels)
                active_count = len([ch for ch in channels if ch.is_active])
                text = f"**📡 Channel Monitor**\n\nActive: {active_count} | Total: {len(channels)}\n\nSelect a channel to configure or add a new one."
            except Exception as e:
                logger.error(f"Failed to load channels for user {user.user_id}: {e}")
                keyboard = TradingKeyboards.main_menu()
                text = "❌ **Failed to load channels**\n\nDatabase error occurred. Please try again."

        elif menu_name == 'help':
            keyboard = TradingKeyboards.main_menu()
            text = (
                "**📖 Help & Usage**\n\n"
                "**Automatic Trading:**\n"
                "• Add channels with /addchannel @ChannelName\n"
                "• MTProto scraper monitors for new tokens\n"
                "• Trades execute automatically in 275ms\n\n"
                "**Manual Trading:**\n"
                "• Paste any contract address to buy instantly\n"
                "• Bot auto-detects blockchain and executes\n\n"
                "**Settings:**\n"
                "• Configure all trading parameters\n"
                "• Set buy amounts, slippage, gas fees\n"
                "• Enable auto-sell features\n\n"
                "**Supported Chains:**\n"
                "• Solana, Ethereum, Base, BSC, Tron\n\n"
                "**Speed Optimized:**\n"
                "• Sub-200ms contract detection\n"
                "• Connection pooling for fast API calls\n"
                "• Memory-based settings cache"
            )
        else:
            logger.warning(f"Unknown menu requested: {menu_name} by user {user.user_id}")
            keyboard = TradingKeyboards.main_menu()
            text = f"❌ **Unknown Menu: {menu_name}**\n\nReturning to main menu."

        # Validate we have both text and keyboard
        if not text or not keyboard:
            logger.error(f"Menu generation failed for {menu_name}")
            raise Exception(f"Failed to generate menu: {menu_name}")

        # Attempt to edit message with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await callback_query.edit_message_text(
                    text,
                    reply_markup=keyboard
                )
                await safe_callback_answer(callback_query, f"📍 {menu_name.replace('_', ' ').title()}")
                return

            except errors.BadRequest as e:
                if "message is not modified" in str(e).lower():
                    # Content is the same, just answer callback
                    await safe_callback_answer(callback_query)
                    return
                elif attempt == max_retries - 1:
                    raise

            except errors.FloodWait as flood:
                wait_time = int(flood.value) if hasattr(flood, 'value') else 60
                logger.warning(f"FloodWait in menu navigation: {wait_time}s")
                await asyncio.sleep(wait_time)

            await asyncio.sleep(0.5 * (attempt + 1))  # Progressive backoff

    except Exception as e:
        logger.error(f"Menu navigation error for {menu_name}: {e}", exc_info=True)
        # Fallback to main menu
        try:
            await callback_query.edit_message_text(
                "❌ **Navigation Error**\n\nReturning to main menu.",
                reply_markup=TradingKeyboards.main_menu()
            )
            await safe_callback_answer(callback_query, "Error occurred. Returned to main menu.")
        except:
            await safe_callback_answer(callback_query, "Navigation failed. Please restart bot.")


# Channel Management Handlers

async def handle_channel_settings(callback_query: CallbackQuery, channel_id: int, user):
    """Handle channel settings display"""
    try:
        subscription = storage.get_channel_subscription(user.user_id, channel_id)
        if not subscription:
            await safe_callback_answer(callback_query, "Channel not found.")
            return

        channel_name = subscription.channel_username or subscription.channel_title
        text = f"**⚙️ {channel_name} Settings**\n\n"
        text += f"📊 **Status:** {'🟢 Active' if subscription.is_active else '🔴 Inactive'}\n"
        text += f"🔍 **Filter:** {subscription.filter_mode.value.replace('_', ' ').title()}\n"

        if subscription.custom_buy_amount:
            text += f"💰 **Custom Amount:** {subscription.custom_buy_amount} SOL\n"
        else:
            text += f"💰 **Amount:** Using default settings\n"

        text += f"📈 **Total Trades:** {subscription.total_trades}\n"

        await callback_query.edit_message_text(
            text,
            reply_markup=TradingKeyboards.channel_settings(subscription)
        )
        await safe_callback_answer(callback_query)

    except Exception as e:
        logger.error(f"Error displaying channel settings: {e}")
        await safe_callback_answer(callback_query, "Failed to load channel settings.")


async def handle_toggle_channel(callback_query: CallbackQuery, channel_id: int, user):
    """Handle channel enable/disable toggle"""
    try:
        new_status = storage.toggle_channel(user.user_id, channel_id)
        if new_status is None:
            await safe_callback_answer(callback_query, "Channel not found.")
            return

        status_text = "enabled" if new_status else "disabled"
        await callback_query.answer(f"Channel {status_text}!")

        # Refresh the settings view
        await handle_channel_settings(callback_query, channel_id, user)

    except Exception as e:
        logger.error(f"Error toggling channel: {e}")
        await safe_callback_answer(callback_query, "Failed to toggle channel.")


async def handle_channel_filter(callback_query: CallbackQuery, channel_id: int, user):
    """Handle channel filter mode selection"""
    try:
        subscription = storage.get_channel_subscription(user.user_id, channel_id)
        if not subscription:
            await safe_callback_answer(callback_query, "Channel not found.")
            return

        text = f"**🔍 Filter Mode for {subscription.channel_title}**\n\n"
        text += "Choose who's messages to monitor:\n\n"
        text += "• **All Messages** - Monitor every message\n"
        text += "• **Admin Only** - Only monitor admin messages\n"
        text += "• **Specific Users** - Monitor selected users only"

        await callback_query.edit_message_text(
            text,
            reply_markup=TradingKeyboards.filter_mode_selection(channel_id)
        )
        await safe_callback_answer(callback_query)

    except Exception as e:
        logger.error(f"Error showing filter options: {e}")
        await safe_callback_answer(callback_query, "Failed to load filter options.")


async def handle_set_filter(callback_query: CallbackQuery, channel_id: int, filter_mode: str, user):
    """Handle setting channel filter mode"""
    try:
        filter_enum = FilterMode(filter_mode)
        storage.update_channel_settings(
            user.user_id,
            channel_id,
            filter_mode=filter_enum
        )

        filter_text = filter_mode.replace('_', ' ').title()
        await safe_callback_answer(callback_query, f"Filter set to {filter_text}!")

        # Go back to channel settings
        await handle_channel_settings(callback_query, channel_id, user)

    except Exception as e:
        logger.error(f"Error setting filter mode: {e}")
        await safe_callback_answer(callback_query, "Failed to set filter mode.")


async def handle_channel_amount(callback_query: CallbackQuery, channel_id: int, user):
    """Handle channel amount setting"""
    try:
        subscription = storage.get_channel_subscription(user.user_id, channel_id)
        if not subscription:
            await safe_callback_answer(callback_query, "Channel not found.")
            return

        current_amount = subscription.custom_buy_amount or "Default"
        text = f"**💰 Buy Amount for {subscription.channel_title}**\n\n"
        text += f"Current: {current_amount}\n\n"
        text += "Select a custom amount for this channel or use default settings:"

        await callback_query.edit_message_text(
            text,
            reply_markup=TradingKeyboards.channel_amount_setting(channel_id)
        )
        await safe_callback_answer(callback_query)

    except Exception as e:
        logger.error(f"Error showing amount options: {e}")
        await safe_callback_answer(callback_query, "Failed to load amount options.")


async def handle_set_channel_amount(callback_query: CallbackQuery, channel_id: int, amount: float, user):
    """Handle setting channel custom amount"""
    try:
        storage.update_channel_settings(
            user.user_id,
            channel_id,
            custom_buy_amount=amount
        )

        await safe_callback_answer(callback_query, f"Amount set to {amount} SOL!")

        # Go back to channel settings
        await handle_channel_settings(callback_query, channel_id, user)

    except Exception as e:
        logger.error(f"Error setting channel amount: {e}")
        await safe_callback_answer(callback_query, "Failed to set amount.")


async def handle_default_channel_amount(callback_query: CallbackQuery, channel_id: int, user):
    """Handle setting channel to use default amount"""
    try:
        storage.update_channel_settings(
            user.user_id,
            channel_id,
            custom_buy_amount=None
        )

        await safe_callback_answer(callback_query, "Using default amount!")

        # Go back to channel settings
        await handle_channel_settings(callback_query, channel_id, user)

    except Exception as e:
        logger.error(f"Error setting default amount: {e}")
        await safe_callback_answer(callback_query, "Failed to set default amount.")


async def handle_remove_channel(callback_query: CallbackQuery, channel_id: int, user):
    """Handle channel removal"""
    try:
        subscription = storage.get_channel_subscription(user.user_id, channel_id)
        if not subscription:
            await safe_callback_answer(callback_query, "Channel not found.")
            return

        # Remove the channel
        removed = storage.remove_channel_subscription(user.user_id, channel_id)
        if removed:
            await safe_callback_answer(callback_query, f"Channel {subscription.channel_title} removed!")

            # Go back to channels menu
            channels = storage.get_user_channels(user.user_id)
            text = f"**📡 Channel Monitor**\n\nActive: {len([ch for ch in channels if ch.is_active])} | Total: {len(channels)}\n\nSelect a channel to configure or add a new one."

            await callback_query.edit_message_text(
                text,
                reply_markup=TradingKeyboards.channels_menu(channels)
            )
        else:
            await safe_callback_answer(callback_query, "Failed to remove channel.")

    except Exception as e:
        logger.error(f"Error removing channel: {e}")
        await safe_callback_answer(callback_query, "Failed to remove channel.")


async def handle_add_channel_prompt(callback_query: CallbackQuery, user):
    """Handle add channel button"""
    try:
        text = (
            "**📡 Add New Channel**\n\n"
            "Send me a channel to monitor using:\n\n"
            "**Commands:**\n"
            "• `/addchannel @ChannelUsername`\n"
            "• `/addchannel ChannelName`\n"
            "• `/addchannel -1001234567890` (ID)\n\n"
            "**Examples:**\n"
            "• `/addchannel @CryptoSnipers`\n"
            "• `/addchannel CryptoLaunches`\n\n"
            "⚡ The MTProto scraper will monitor for new tokens automatically!"
        )

        await callback_query.edit_message_text(
            text,
            reply_markup=TradingKeyboards.main_menu()
        )
        await safe_callback_answer(callback_query, "Add channel options displayed")

    except Exception as e:
        logger.error(f"Error showing add channel prompt: {e}")
        await safe_callback_answer(callback_query, "Failed to show add channel options.")


async def handle_setting_selection(callback_query: CallbackQuery, setting_name: str, user):
    """Handle setting selection with validation and error recovery"""
    try:
        # Validate setting name
        if not setting_name or not isinstance(setting_name, str):
            raise ValueError(f"Invalid setting name: {setting_name}")

        # Get current value with fallback
        try:
            current_value = user.get_setting(setting_name, DEFAULT_SETTINGS.get(setting_name))
        except Exception as e:
            logger.error(f"Failed to get setting {setting_name} for user {user.user_id}: {e}")
            current_value = DEFAULT_SETTINGS.get(setting_name, 0)

        # Determine back menu with validation
        if setting_name in ['amountOrPercent', 'maxSlippage', 'retries', 'concurrentNodes']:
            back_menu = 'buy_basic'
        elif setting_name in ['jitoEnabled', 'jitoTip', 'customFeeAndTip', 'priorityFee', 'gasFeeDelta', 'maxFeePerGas']:
            back_menu = 'buy_gas'
        elif setting_name.startswith('pnl') or setting_name in ['stopEarnPercent', 'stopLossPercent', 'stopEarnGroup', 'stopLossGroup', 'trailingStopGroup']:
            back_menu = 'buy_pnl'
        else:
            back_menu = 'sell_settings'

        # Generate appropriate interface
        if setting_name in ['jitoEnabled', 'customFeeAndTip', 'pnlOrderExpireExecute', 'pnlOrderUseMidPrice', 'pnlCustomConfigEnabled']:
            # Boolean settings
            try:
                keyboard = TradingKeyboards.boolean_setting(setting_name, bool(current_value), back_menu)
                status = "✅ Enabled" if current_value else "❌ Disabled"
                text = f"**⚙️ {setting_name}**\n\nCurrent: {status}\n\nClick to toggle:"
            except Exception as e:
                logger.error(f"Failed to create boolean keyboard for {setting_name}: {e}")
                raise
        else:
            # Numeric settings
            try:
                suggestions = SETTING_SUGGESTIONS.get(setting_name, [])
                keyboard = TradingKeyboards.numeric_setting(setting_name, back_menu, suggestions)
                formatted_value = format_setting_display(setting_name, current_value)
                text = f"**⚙️ {setting_name}**\n\nCurrent: {formatted_value}\n\nSelect a value or use custom input:"
            except Exception as e:
                logger.error(f"Failed to create numeric keyboard for {setting_name}: {e}")
                raise

        # Update message with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await callback_query.edit_message_text(
                    text,
                    reply_markup=keyboard
                )
                await safe_callback_answer(callback_query, f"⚙️ {setting_name}")
                return

            except errors.BadRequest as e:
                if "message is not modified" in str(e).lower():
                    await safe_callback_answer(callback_query)
                    return
                elif attempt == max_retries - 1:
                    raise

            except errors.FloodWait as flood:
                wait_time = int(flood.value) if hasattr(flood, 'value') else 60
                await asyncio.sleep(wait_time)

            await asyncio.sleep(0.5 * (attempt + 1))

    except Exception as e:
        logger.error(f"Setting selection error for {setting_name}: {e}", exc_info=True)
        # Fallback to settings menu
        try:
            await callback_query.edit_message_text(
                f"❌ **Setting Error**\n\nFailed to load {setting_name}.\nReturning to settings menu.",
                reply_markup=TradingKeyboards.main_menu()
            )
            await safe_callback_answer(callback_query, f"Failed to load {setting_name}")
        except:
            await safe_callback_answer(callback_query, "Setting load failed. Please try again.")


async def handle_boolean_toggle(callback_query: CallbackQuery, params: list, user):
    """Handle boolean setting toggle"""
    setting_name, new_value = params[0], params[1] == 'True'

    storage.update_user_setting(user.user_id, setting_name, new_value)

    await callback_query.answer(f"✅ {setting_name} {'enabled' if new_value else 'disabled'}")

    # Refresh the setting page
    await handle_setting_selection(callback_query, setting_name, user)


async def handle_setting_value(callback_query: CallbackQuery, params: list, user):
    """Handle setting value selection"""
    setting_name, value_str = params[0], params[1]

    # Validate and convert value
    is_valid, converted_value, error = validate_settings_input(setting_name, value_str)

    if is_valid:
        storage.update_user_setting(user.user_id, setting_name, converted_value)
        await callback_query.answer(f"✅ {setting_name} set to {format_setting_display(setting_name, converted_value)}")

        # Refresh the setting page
        await handle_setting_selection(callback_query, setting_name, user)
    else:
        await callback_query.answer(f"❌ {error}", show_alert=True)


async def handle_custom_input(callback_query: CallbackQuery, setting_name: str, user):
    """Handle custom input request"""
    user_states[user.user_id] = {'waiting_for': setting_name}

    await callback_query.edit_message_text(
        f"**Custom Input: {setting_name}**\n\n"
        f"Current: {format_setting_display(setting_name, user.get_setting(setting_name))}\n\n"
        f"Please send the new value:",
        parse_mode=ParseMode.MARKDOWN
    )
    await callback_query.answer()


async def handle_wallet_selection(callback_query: CallbackQuery, wallet_id: str, user):
    """Handle wallet selection"""
    storage.update_user_setting(user.user_id, 'wallet_id', wallet_id)
    user.wallet_id = wallet_id

    await callback_query.answer("✅ Wallet selected successfully!")
    await handle_menu_navigation(callback_query, 'main', user)


async def handle_action(callback_query: CallbackQuery, action_name: str, user):
    """Handle various actions"""
    if action_name == 'reset_settings':
        # Reset to default settings
        for key, value in DEFAULT_SETTINGS.items():
            storage.update_user_setting(user.user_id, key, value)

        await callback_query.answer("✅ Settings reset to defaults")
        await handle_menu_navigation(callback_query, 'main', user)

    elif action_name == 'import_wallet':
        user_states[user.user_id] = {'waiting_for': 'wallet_import'}

        await callback_query.edit_message_text(
            "**Import Wallet**\n\n"
            "Send your private key in this format:\n"
            "`type:name:private_key`\n\n"
            "Example:\n"
            "`solana:MyWallet:your_private_key_here`\n\n"
            "⚠️ **Security Warning:**\n"
            "Only import wallets with small amounts for testing!",
            parse_mode=ParseMode.MARKDOWN
        )
        await callback_query.answer()

    elif action_name == 'add_channel':
        await handle_add_channel_prompt(callback_query, user)


async def handle_order_view(callback_query: CallbackQuery, order_id: str, user):
    """Handle order details view"""
    order = storage.get_order(order_id)
    if not order or order.user_id != user.user_id:
        await callback_query.answer("❌ Order not found")
        return

    order_details = format_order_summary(order)

    await callback_query.edit_message_text(
        f"**📊 Order Details**\n\n{order_details}",
        reply_markup=TradingKeyboards.main_menu(),
        parse_mode=ParseMode.MARKDOWN
    )
    await callback_query.answer()


async def handle_confirmation(callback_query: CallbackQuery, params: list, user):
    """Handle confirmation dialogs"""
    action = params[0]

    if action == 'reset_settings':
        await handle_action(callback_query, action, user)

    await callback_query.answer()


async def text_input_handler(client: Client, message: Message):
    """Handle text input for custom settings"""
    user_id = message.from_user.id

    if user_id not in user_states:
        return

    state = user_states[user_id]
    waiting_for = state.get('waiting_for')

    if waiting_for and waiting_for != 'wallet_import':
        # Handle setting input
        is_valid, converted_value, error = validate_settings_input(waiting_for, message.text)

        if is_valid:
            storage.update_user_setting(user_id, waiting_for, converted_value)
            await message.reply_text(
                f"✅ {waiting_for} set to {format_setting_display(waiting_for, converted_value)}",
                reply_markup=TradingKeyboards.main_menu()
            )
        else:
            await message.reply_text(f"❌ {error}")

        del user_states[user_id]

    elif waiting_for == 'wallet_import':
        # Handle wallet import
        try:
            parts = message.text.split(':')
            if len(parts) != 3:
                raise ValueError("Invalid format")

            wallet_type, name, private_key = parts

            response = await dbotx_client.import_wallet(wallet_type, name, private_key)

            if response.get('err', True):
                error_msg = response.get('message', 'Unknown error')
                await message.reply_text(f"❌ Failed to import wallet: {error_msg}")
            else:
                wallet_data = response.get('res', {})
                wallet_id = wallet_data.get('id')

                if wallet_id:
                    storage.update_user_setting(user_id, 'wallet_id', wallet_id)
                    user = storage.get_user(user_id)
                    if user:
                        user.wallet_id = wallet_id

                await message.reply_text(
                    f"✅ Wallet imported successfully!\n\n{format_wallet_display(wallet_data)}",
                    reply_markup=TradingKeyboards.main_menu(),
                    parse_mode=ParseMode.MARKDOWN
                )

            del user_states[user_id]

        except Exception as e:
            await message.reply_text(f"❌ Import failed: {str(e)}")


# Message filters
@filters.create
def contract_filter(_, __, message):
    """Filter to detect contract addresses"""
    if not message.text:
        return False
    return detect_contract_address(message.text) is not None


@filters.create
def owner_filter(_, __, message):
    """Filter for bot owner only"""
    return message.from_user.id == OWNER_CHAT_ID


@filters.create
def forwarded_message_filter(_, __, message):
    """Filter for forwarded messages from channels/groups"""
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return False

    # Only process forwarded messages when user is awaiting channel forward
    if user_id not in user_states or user_states[user_id].get('waiting_for') != 'channel_forward':
        return False

    return message.forward_from_chat is not None


# Channel message handler for integrated monitoring
async def handle_channel_message(client: Client, message: Message):
    """Handle messages from monitored channels - INTEGRATED MONITORING"""
    try:
        # Only process channel messages
        if not message.chat or message.chat.type not in ["channel", "supergroup"]:
            logger.debug(f"⏭️ Skipping non-channel message (type: {message.chat.type if message.chat else 'None'})")
            return

        channel_id = message.chat.id
        channel_title = message.chat.title or f"Channel {channel_id}"

        logger.info(f"📨 RECEIVED MESSAGE from channel {channel_id} ({channel_title})")
        logger.info(f"📝 Message text: {message.text[:200] if message.text else 'NO TEXT'}")

        # Get all subscriptions for this channel ID
        subscriptions = storage.get_all_user_channels_by_channel_id(channel_id)
        
        if not subscriptions:
            logger.warning(f"⏭️ Channel {channel_title} ({channel_id}) NOT IN MONITORED LIST")
            return

        logger.info(f"✅ MONITORED CHANNEL CONFIRMED: {channel_title} (ID: {channel_id}) | {len(subscriptions)} subscription(s)")

        # Process message for each subscription (allows multiple users to monitor same channel)
        for subscription in subscriptions:
            try:
                logger.info(f"🔍 Processing subscription for user {subscription.user_id}")
                logger.info(f"   Filter mode: {subscription.filter_mode.value}")
                logger.info(f"   Active: {subscription.is_active}")
                
                if not subscription.is_active:
                    logger.warning(f"   ⚠️ Subscription is INACTIVE - skipping")
                    continue
                
                # Apply filter mode
                should_process = False
                filter_mode = subscription.filter_mode.value

                if filter_mode == "all":
                    should_process = True
                    logger.info(f"   ✅ Filter mode: ALL - WILL PROCESS")
                elif filter_mode == "admins":
                    # Check if sender is admin (simplified)
                    if message.from_user:
                        should_process = True
                        logger.info(f"   ✅ Filter mode: ADMINS - processing message from user {message.from_user.id}")
                    else:
                        logger.warning(f"   ❌ Filter mode: ADMINS - no from_user in message")
                elif filter_mode == "users":
                    if message.from_user and message.from_user.id in subscription.allowed_user_ids:
                        should_process = True
                        logger.info(f"   ✅ Filter mode: USERS - user {message.from_user.id} in allowed list")
                    else:
                        logger.warning(f"   ❌ Filter mode: USERS - user {message.from_user.id if message.from_user else 'None'} not in allowed list")

                if not should_process:
                    logger.warning(f"   ⚠️ Message FILTERED OUT by mode: {filter_mode}")
                    continue

                logger.info(f"   ✅ Filter PASSED - checking for contract...")

                # Check for contract address
                if not message.text:
                    logger.warning(f"   ⚠️ No text in message")
                    continue

                logger.info(f"   🔍 Scanning text: {message.text[:100]}...")
                contract_info = detect_contract_address(message.text)
                
                if not contract_info:
                    logger.info(f"   ⚪ No contract detected")
                    continue

                chain, address = contract_info
                logger.info(f"🎯🎯🎯 CONTRACT DETECTED: {chain.upper()} | {address}")
                logger.info(f"   📍 Channel: {channel_title}")
                logger.info(f"   👤 User: {subscription.user_id}")

                # Get user for this subscription
                user = storage.get_user(subscription.user_id)
                if not user:
                    logger.error(f"   ❌ User {subscription.user_id} NOT FOUND in database")
                    continue
                    
                if not user.wallet_id:
                    logger.error(f"   ❌ User {subscription.user_id} has NO WALLET configured")
                    logger.error(f"   💡 User needs to select wallet via /wallet command")
                    continue

                # Determine buy amount
                amount = subscription.custom_buy_amount or user.get_setting('amountOrPercent', 0.1)
                logger.info(f"   💰 Buy amount: {amount} (custom: {subscription.custom_buy_amount})")

                # Generate order ID
                order_id = generate_order_id()
                logger.info(f"   🆔 Order ID: {order_id}")

                # Create order
                storage.create_order(
                    order_id=order_id,
                    user_id=subscription.user_id,
                    chain=chain,
                    pair=address,
                    order_type='buy',
                    amount=amount,
                    settings=user.settings.copy()
                )
                logger.info(f"   ✅ Order created in database")

                logger.info(f"🚀🚀🚀 EXECUTING TRADE NOW")
                logger.info(f"   Order: {order_id}")
                logger.info(f"   Chain: {chain}")
                logger.info(f"   Address: {address}")
                logger.info(f"   Amount: {amount}")

                # Execute trade
                asyncio.create_task(execute_fast_buy(
                    order_id, subscription.user_id, chain, address, amount,
                    user.settings, None  # No status message for channel trades
                ))
                
                logger.info(f"   ⚡ Trade task created and running")
                
            except Exception as sub_error:
                logger.error(f"Error processing subscription for user {subscription.user_id}: {sub_error}")
                continue

    except Exception as e:
        logger.error(f"Error handling channel message: {e}", exc_info=True)


# Register handlers - SPLIT FOR DUAL-CLIENT ARCHITECTURE
def register_bot_handlers(app: Client):
    """Register BOT client handlers (commands, UI, callbacks)"""
    from pyrogram.handlers.message_handler import MessageHandler
    from pyrogram.handlers.callback_query_handler import CallbackQueryHandler

    logger.info("📋 Registering BOT client handlers...")

    # Command handlers (BOT handles all commands)
    app.add_handler(MessageHandler(start_handler, filters.command("start") & filters.private))
    app.add_handler(MessageHandler(settings_handler, filters.command("settings") & filters.private))
    app.add_handler(MessageHandler(setapikey_handler, filters.command("setapikey") & filters.private))
    app.add_handler(MessageHandler(channels_handler, filters.command("channels") & filters.private))
    app.add_handler(MessageHandler(addchannel_handler, filters.command("addchannel") & filters.private))
    app.add_handler(MessageHandler(cancel_handler, filters.command("cancel") & filters.private))

    # Forwarded message handler (for adding channels via BOT)
    app.add_handler(MessageHandler(handle_forwarded_message, forwarded_message_filter & filters.private))

    # Contract handler for private messages (BOT handles user trades)
    app.add_handler(MessageHandler(contract_handler, contract_filter & filters.private))

    # Text input handler (BOT handles user settings input)
    app.add_handler(MessageHandler(text_input_handler, filters.text & filters.private))

    # Callback query handler (BOT handles all inline keyboard callbacks)
    app.add_handler(CallbackQueryHandler(callback_handler))

    logger.info("✅ BOT client handlers registered")


def register_user_handlers(app: Client):
    """Register USER client handlers (channel monitoring only)"""
    from pyrogram.handlers.message_handler import MessageHandler

    logger.info("📋 Registering USER client handlers...")

    # Channel monitoring handler - USER client only monitors channels
    # Filter for channel messages only (groups and channels)
    app.add_handler(MessageHandler(
        handle_channel_message,
        filters.channel & ~filters.private
    ))

    logger.info("✅ USER client handlers registered (channel monitoring only)")

    # Debug command for monitoring status (in BOT handlers)
    @app.on_message(filters.command("debug") & filters.private)
    async def debug_monitoring(client, message):
        """Show dual-client monitoring debug info"""
        try:
            if not is_owner(message.from_user.id):
                await message.reply_text("❌ Owner only command")
                return

            # Get all active channels from storage
            channels = storage.get_all_active_channels()

            debug_info = f"""
🔍 **DUAL-CLIENT MONITORING DEBUG**

**System:**
• BOT client: Commands & UI
• USER client: Channel monitoring
• MTProto direct protocol

**Monitored Channels: {len(channels)}**
"""

            if channels:
                for i, sub in enumerate(channels, 1):
                    name = sub.channel_username or sub.channel_title or f"Channel {sub.channel_id}"
                    debug_info += f"\n**{i}. {name}**\n"
                    debug_info += f"  ID: `{sub.channel_id}`\n"
                    debug_info += f"  User: {sub.user_id}\n"
                    debug_info += f"  Status: {'🟢 Active' if sub.is_active else '🔴 Inactive'}\n"
            else:
                debug_info += "\n• No channels configured\n"
                debug_info += "• Use /addchannel to start monitoring\n"

            await message.reply_text(debug_info)

        except Exception as e:
            logger.error(f"Debug command error: {e}")
            await message.reply_text(f"❌ Debug error: {str(e)}")