#!/usr/bin/env python3
"""
Setup script to configure test user with provided API key and channel
"""

import asyncio
import logging
from models import storage, ChannelSubscription, FilterMode, ChannelType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def setup_test_user():
    """Setup test user using provided test credentials"""
    logger.info("🧪 Setting up test user with provided credentials...")
    
    # Test user ID - using a real ID that would use the bot
    test_user_id = 6601959348  # The authenticated user ID from logs
    
    # Create/update user with provided API key
    user = storage.create_user(
        user_id=test_user_id,
        username="vi_tech_writer",
        first_name="Vi",
        last_name="Tech Writer",
        api_key="vu4ql0a13fuivobm8ehpa0r1eofykx6f",  # Provided API key
        wallet_id="test_wallet_123"
    )
    
    # Real channel ID from our test (ID: 2607730894)
    real_channel_id = -1002607730894  # Convert to negative for Telegram format
    
    # Create channel subscription for @GateioPumpAlerts
    subscription = storage.create_channel_subscription(
        user_id=test_user_id,
        channel_id=real_channel_id,
        channel_title="Gateio Pump Alerts",
        channel_username="GateioPumpAlerts",
        channel_type=ChannelType.CHANNEL,
        filter_mode=FilterMode.ALL_MESSAGES,  # Start with all messages
        is_active=True
    )
    
    logger.info(f"✅ Created/updated test user: {user.user_id}")
    logger.info(f"✅ API Key: {user.api_key[:10]}...")
    logger.info(f"✅ Created channel subscription: {subscription.channel_title}")
    logger.info(f"✅ Channel ID: {subscription.channel_id}")
    logger.info(f"✅ Filter Mode: {subscription.filter_mode.value}")
    
    # Test different monitoring modes
    logger.info("\n🧪 Testing different monitoring modes...")
    
    # Mode 1: ALL MESSAGES (already set)
    logger.info("✅ Mode 1: ALL_MESSAGES configured")
    
    # Mode 2: ADMIN_ONLY
    storage.update_channel_settings(
        test_user_id, real_channel_id, 
        filter_mode=FilterMode.ADMIN_ONLY
    )
    logger.info("✅ Mode 2: ADMIN_ONLY configured")
    
    # Mode 3: SPECIFIC_USERS  
    test_user_ids = [6601959348, 1234567890]  # Include our test user
    storage.update_channel_user_list(test_user_id, real_channel_id, test_user_ids)
    logger.info(f"✅ Mode 3: SPECIFIC_USERS configured with IDs: {test_user_ids}")
    
    # Reset to ALL_MESSAGES for testing
    storage.update_channel_settings(
        test_user_id, real_channel_id,
        filter_mode=FilterMode.ALL_MESSAGES
    )
    logger.info("✅ Reset to ALL_MESSAGES mode for testing")
    
    # Verify setup
    final_subscription = storage.get_channel_subscription(test_user_id, real_channel_id)
    logger.info(f"\n📊 Final Configuration:")
    logger.info(f"   User ID: {final_subscription.user_id}")
    logger.info(f"   Channel: {final_subscription.channel_title}")
    logger.info(f"   Channel ID: {final_subscription.channel_id}")
    logger.info(f"   Mode: {final_subscription.filter_mode.value}")
    logger.info(f"   Active: {final_subscription.is_active}")
    
    return user, final_subscription

if __name__ == "__main__":
    asyncio.run(setup_test_user())