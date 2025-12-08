"""
Ultra-Fast Trading Bot Configuration
Contract Detection & Monitoring Only
"""
import os

def config(key, default=None, cast=None):
    """Simple config function to replace decouple"""
    value = os.environ.get(key, default)
    if cast and value is not None:
        try:
            return cast(value)
        except (ValueError, TypeError):
            return default
    return value

# Telegram Bot Configuration
BOT_TOKEN = config('BOT_TOKEN', default='YOUR_BOT_TOKEN_HERE')
API_ID = config('API_ID', default=0)
API_HASH = config('API_HASH', default='YOUR_API_HASH_HERE')
OWNER_CHAT_ID = config('OWNER_CHAT_ID', default=0, cast=int)

# Scraper User Authentication (for channel monitoring)
SCRAPER_PHONE = config('SCRAPER_PHONE', default='')
SCRAPER_PASSWORD = config('SCRAPER_PASSWORD', default='')

# DBOTX API Configuration
DBOTX_API_KEY = config('DBOTX_API_KEY', default='')
DBOTX_BASE_URL = 'https://api-data-v1.dbotx.com'

# Supabase Configuration (for verification monitoring)
SUPABASE_URL = config('SUPABASE_URL', default='https://ofririwzonwekmyqgqlg.supabase.co')
SUPABASE_ANON_KEY = config('SUPABASE_ANON_KEY', default='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9mcmlyaXd6b253ZWtteXFncWxnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjE0MDM1MzYsImV4cCI6MjA3Njk3OTUzNn0.1PQ9Fg4V04kaCZQm_7c88p65cOWboAs1htzjvQ_Tsko')
SUPABASE_SERVICE_KEY = config('SUPABASE_SERVICE_KEY', default='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9mcmlyaXd6b253ZWtteXFncWxnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MTQwMzUzNiwiZXhwIjoyMDc2OTc5NTM2fQ.NoNkxXOnVDgSRw0KBnT0iyi25m6oCYmzKFWEfrh5z3Y')

# For backwards compatibility
SUPABASE_KEY = SUPABASE_ANON_KEY

# Supabase Table Names
VERIFY_REQUESTS_TABLE = 'verify_requests'
WALLET_PATTERNS_TABLE = 'wallet_patterns'
REALTIME_CHANNEL = 'verify_updates'

# Speed Optimization Settings
HTTP_TIMEOUT = 5.0
MAX_CONNECTIONS = 20
MAX_RETRIES = 3
CONCURRENT_LIMIT = 10

# Speed Mode - Skip delays for maximum speed
_speed_mode_val = config('SPEED_MODE', default='true')
SPEED_MODE = str(_speed_mode_val).lower() == 'true' if _speed_mode_val else True

# Delay settings (only used when SPEED_MODE=false)
_delay_min = config('HUMAN_DELAY_MIN', default='0.05')
_delay_max = config('HUMAN_DELAY_MAX', default='0.1')
HUMAN_DELAY_MIN = float(_delay_min) if _delay_min else 0.05
HUMAN_DELAY_MAX = float(_delay_max) if _delay_max else 0.1

# Session Configuration
SESSION_NAME = 'trading_bot_session'
WORKDIR = os.path.dirname(os.path.abspath(__file__))

# Safety Filters Per Chain (For Token Validation)
DEFAULT_SETTINGS = {
    'enabled_chains': ['solana', 'bsc', 'ethereum', 'base', 'arbitrum', 'tron'],  # Global chain enablement
    'solana': {
        'market_cap_min': 5000,
        'market_cap_max': None,
        'holders_min': 25,
        'snipers_max': None,
        'require_launch_migration': False,
        'volume_ratio_1m': None,
        'volume_ratio_5m': None,
        'volume_ratio_1h': None,
        'volume_ratio_6h': None,
        'volume_ratio_24h': None,
        'check_freeze_authority': True,
        'check_mint_authority': False,
        'top10_holder_max': None,
        'lp_burn_min': None,
    },
    'bsc': {
        'market_cap_min': 50000,
        'market_cap_max': None,
        'holders_min': 100,
        'snipers_max': None,
        'require_launch_migration': False,
        'volume_ratio_1m': None,
        'volume_ratio_5m': None,
        'volume_ratio_1h': None,
        'volume_ratio_6h': None,
        'volume_ratio_24h': None,
        'check_freeze_authority': False,
        'check_mint_authority': False,
        'top10_holder_max': None,
        'lp_burn_min': None,
    },
    'base': {
        'market_cap_min': 50000,
        'market_cap_max': None,
        'holders_min': 100,
        'snipers_max': None,
        'require_launch_migration': False,
        'volume_ratio_1m': None,
        'volume_ratio_5m': None,
        'volume_ratio_1h': None,
        'volume_ratio_6h': None,
        'volume_ratio_24h': None,
        'check_freeze_authority': False,
        'check_mint_authority': False,
        'top10_holder_max': None,
        'lp_burn_min': None,
    },
    'ethereum': {
        'market_cap_min': 100000,
        'market_cap_max': None,
        'holders_min': 200,
        'snipers_max': None,
        'require_launch_migration': False,
        'volume_ratio_1m': None,
        'volume_ratio_5m': None,
        'volume_ratio_1h': None,
        'volume_ratio_6h': None,
        'volume_ratio_24h': None,
        'check_freeze_authority': False,
        'check_mint_authority': False,
        'top10_holder_max': None,
        'lp_burn_min': None,
    },
    'arbitrum': {
        'market_cap_min': 50000,
        'market_cap_max': None,
        'holders_min': 100,
        'snipers_max': None,
        'require_launch_migration': False,
        'volume_ratio_1m': None,
        'volume_ratio_5m': None,
        'volume_ratio_1h': None,
        'volume_ratio_6h': None,
        'volume_ratio_24h': None,
        'check_freeze_authority': False,
        'check_mint_authority': False,
        'top10_holder_max': None,
        'lp_burn_min': None,
    },
    'tron': {
        'market_cap_min': 50000,
        'market_cap_max': None,
        'holders_min': 100,
        'snipers_max': None,
        'require_launch_migration': False,
        'volume_ratio_1m': None,
        'volume_ratio_5m': None,
        'volume_ratio_1h': None,
        'volume_ratio_6h': None,
        'volume_ratio_24h': None,
        'check_freeze_authority': False,
        'check_mint_authority': False,
        'top10_holder_max': None,
        'lp_burn_min': None,
    },
}

# RPC Endpoints for EVM Chain Detection
EVM_RPC_ENDPOINTS = {
    'base': 'https://base-rpc.publicnode.com',
    'bsc': 'https://bsc-rpc.publicnode.com',
    'ethereum': 'https://eth-rpc.publicnode.com'
}

# Blockchain Detection Patterns (Pre-compiled for speed)
CHAIN_PATTERNS = {
    'tron': r'^T[A-Za-z0-9]{33}$',
    'bsc': r'^0x[a-fA-F0-9]{40}$',
    'base': r'^0x[a-fA-F0-9]{40}$',
    'solana': r'^[1-9A-HJ-NP-Za-km-z]{32,44}$'
}

# Menu Configuration (Channel Management Only)
MENU_EMOJI = {
    'channels': '📡',
    'add_channel': '➕',
    'remove_channel': '🗑️',
    'toggle_channel': '🔄',
    'channel_settings': '⚙️',
    'filter_mode': '🔍',
    'active': '✅',
    'inactive': '❌',
    'all_msgs': '📢',
    'admin_only': '👑',
    'specific_users': '👥',
    'back': '⬅️',
    'save': '💾',
    'reset': '🔄',
}

# Setting Metadata - Safety Filter Validation Only
SETTING_METADATA = {
    # Safety Filters
    'market_cap_min': {
        'display_name': 'Minimum Market Cap',
        'description': 'Only process tokens with market cap above this value.',
        'category': 'safety',
        'input_type': 'number',
    },
    'market_cap_max': {
        'display_name': 'Maximum Market Cap',
        'description': 'Only process tokens with market cap below this value. Leave empty for no limit.',
        'category': 'safety',
        'input_type': 'number',
    },
    'holders_min': {
        'display_name': 'Minimum Holders',
        'description': 'Only process tokens with at least this many holders.',
        'category': 'safety',
        'input_type': 'number',
    },
    'snipers_max': {
        'display_name': 'Maximum Snipers',
        'description': 'Reject tokens with more than this many sniper wallets. Leave empty for no limit.',
        'category': 'safety',
        'input_type': 'number',
    },
    'check_freeze_authority': {
        'display_name': 'Check Freeze Authority',
        'description': 'Reject tokens that have freeze authority enabled (Solana only).',
        'category': 'safety',
        'input_type': 'toggle',
    },
    'check_mint_authority': {
        'display_name': 'Check Mint Authority',
        'description': 'Reject tokens that have mint authority enabled.',
        'category': 'safety',
        'input_type': 'toggle',
    },
    'top10_holder_max': {
        'display_name': 'Max Top 10 Holder %',
        'description': 'Reject tokens where top 10 holders own more than this % of supply.',
        'category': 'safety',
        'input_type': 'percentage',
    },
    'lp_burn_min': {
        'display_name': 'Minimum LP Burn %',
        'description': 'Only process tokens with at least this % of LP burned.',
        'category': 'safety',
        'input_type': 'percentage',
    },
    'volume_ratio_1m': {
        'display_name': 'Volume Ratio (1m)',
        'description': 'Minimum volume ratio for 1 minute candle.',
        'category': 'safety',
        'input_type': 'number',
    },
    'volume_ratio_5m': {
        'display_name': 'Volume Ratio (5m)',
        'description': 'Minimum volume ratio for 5 minute candle.',
        'category': 'safety',
        'input_type': 'number',
    },
    'volume_ratio_1h': {
        'display_name': 'Volume Ratio (1h)',
        'description': 'Minimum volume ratio for 1 hour candle.',
        'category': 'safety',
        'input_type': 'number',
    },
    'volume_ratio_6h': {
        'display_name': 'Volume Ratio (6h)',
        'description': 'Minimum volume ratio for 6 hour candle.',
        'category': 'safety',
        'input_type': 'number',
    },
    'volume_ratio_24h': {
        'display_name': 'Volume Ratio (24h)',
        'description': 'Minimum volume ratio for 24 hour candle.',
        'category': 'safety',
        'input_type': 'number',
    },
    'require_launch_migration': {
        'display_name': 'Require Launch Migration',
        'description': 'Only process tokens from verified launches (Pump.fun/Fourmeme migrations).',
        'category': 'safety',
        'input_type': 'toggle',
    },
}

# Setting Input Types for UI Validation
SETTING_INPUT_TYPES = {
    'market_cap_min': {'input_type': 'number', 'parent_menu': 'chain_safety'},
    'market_cap_max': {'input_type': 'number', 'parent_menu': 'chain_safety'},
    'holders_min': {'input_type': 'number', 'parent_menu': 'chain_safety'},
    'snipers_max': {'input_type': 'number', 'parent_menu': 'chain_safety'},
    'check_freeze_authority': {'input_type': 'toggle', 'parent_menu': 'chain_safety'},
    'check_mint_authority': {'input_type': 'toggle', 'parent_menu': 'chain_safety'},
    'top10_holder_max': {'input_type': 'percentage', 'parent_menu': 'chain_safety'},
    'lp_burn_min': {'input_type': 'percentage', 'parent_menu': 'chain_safety'},
    'volume_ratio_1m': {'input_type': 'number', 'parent_menu': 'chain_safety'},
    'volume_ratio_5m': {'input_type': 'number', 'parent_menu': 'chain_safety'},
    'volume_ratio_1h': {'input_type': 'number', 'parent_menu': 'chain_safety'},
    'volume_ratio_6h': {'input_type': 'number', 'parent_menu': 'chain_safety'},
    'volume_ratio_24h': {'input_type': 'number', 'parent_menu': 'chain_safety'},
    'require_launch_migration': {'input_type': 'toggle', 'parent_menu': 'chain_safety'},
}
