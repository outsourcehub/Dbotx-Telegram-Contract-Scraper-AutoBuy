"""
MTProto Scraper Configuration
Environment variables and settings for the scraper service
"""
from decouple import config

# MTProto Scraper Authentication
SCRAPER_PHONE = config('SCRAPER_PHONE', default='')
SCRAPER_PASSWORD = config('SCRAPER_PASSWORD', default='')  # 2FA password if enabled
SCRAPER_SESSION = config('SCRAPER_SESSION', default='scraper_session')

# Performance Settings
UPDATE_INTERVAL = config('UPDATE_INTERVAL', default=30, cast=int)  # Channel list update interval
MAX_CONCURRENT_TRADES = config('MAX_CONCURRENT_TRADES', default=50, cast=int)

# Monitoring Settings
ENABLE_ADMIN_FILTER = config('ENABLE_ADMIN_FILTER', default=True, cast=bool)
ENABLE_USER_FILTER = config('ENABLE_USER_FILTER', default=True, cast=bool)
MESSAGE_CACHE_SIZE = config('MESSAGE_CACHE_SIZE', default=1000, cast=int)

# Logging Configuration
SCRAPER_LOG_LEVEL = config('SCRAPER_LOG_LEVEL', default='INFO')
ENABLE_PERFORMANCE_LOGS = config('ENABLE_PERFORMANCE_LOGS', default=True, cast=bool)

# Speed Optimization
USE_FAST_MODE = config('USE_FAST_MODE', default=True, cast=bool)
SKIP_OLD_MESSAGES = config('SKIP_OLD_MESSAGES', default=True, cast=bool)