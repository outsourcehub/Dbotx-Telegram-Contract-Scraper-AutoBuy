"""
DBOTX API Client - Ultra-Fast Trading Execution
Speed-optimized HTTP client with connection pooling and async operations
"""
import asyncio
import aiohttp
import ujson
import time
from typing import Dict, Any, Optional, List
from asyncio_throttle.throttler import Throttler
from config import (
    DBOTX_BASE_URL, DBOTX_API_KEY, HTTP_TIMEOUT,
    MAX_CONNECTIONS, CONCURRENT_LIMIT, MAX_RETRIES
)
import logging

logger = logging.getLogger(__name__)


class DBOTXClient:
    """Ultra-fast DBOTX API client with connection pooling"""

    def __init__(self):
        self.base_url = DBOTX_BASE_URL
        self.api_key = DBOTX_API_KEY
        self.session: Optional[aiohttp.ClientSession] = None
        self.connector: Optional[aiohttp.TCPConnector] = None
        self.throttler = Throttler(rate_limit=CONCURRENT_LIMIT, period=1.0)

        # Request timeout configuration
        self.timeout = aiohttp.ClientTimeout(
            total=HTTP_TIMEOUT,
            connect=2.0,
            sock_read=HTTP_TIMEOUT
        )

    def set_api_key(self, api_key: str):
        """Set the DBOTX API key"""
        self.api_key = api_key

    async def __aenter__(self):
        """Async context manager entry"""
        await self.start_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close_session()

    async def start_session(self):
        """Initialize HTTP session with optimized settings"""
        if self.session is None or self.session.closed:
            # Create connector when session starts (inside event loop)
            if self.connector is None or self.connector.closed:
                self.connector = aiohttp.TCPConnector(
                    limit=MAX_CONNECTIONS,
                    limit_per_host=MAX_CONNECTIONS,
                    keepalive_timeout=30,
                    enable_cleanup_closed=True
                )

            self.session = aiohttp.ClientSession(
                connector=self.connector,
                timeout=self.timeout,
                json_serialize=ujson.dumps,
                headers={
                    'User-Agent': 'UltraFast-Trading-Bot/1.0',
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            )

    async def close_session(self):
        """Close HTTP session and connections"""
        if self.session and not self.session.closed:
            await self.session.close()
            await asyncio.sleep(0.1)  # Allow cleanup

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with API key"""
        headers = {
            'Content-Type': 'application/json'
        }
        if self.api_key:
            headers['x-api-key'] = self.api_key
        return headers

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make optimized HTTP request with retries"""
        if not self.session or self.session.closed:
            await self.start_session()

        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        # Mask API key for logging
        masked_headers = headers.copy()
        if 'x-api-key' in masked_headers:
            key = masked_headers['x-api-key']
            masked_headers['x-api-key'] = f"{key[:8]}...{key[-4:]}" if len(key) > 12 else "***"

        logger.info(f"🌐 API_REQUEST: {method} {endpoint}")
        logger.info(f"   ├─ URL: {url}")
        logger.info(f"   ├─ Headers: {masked_headers}")
        if params:
            logger.info(f"   ├─ Params: {params}")
        if data:
            # Log a subset of data to avoid spam
            data_preview = {k: v for k, v in list(data.items())[:10]}
            logger.info(f"   └─ Data (preview): {data_preview}")

        for attempt in range(MAX_RETRIES):
            try:
                if self.session is None:
                    logger.error("❌ API_REQUEST: Session not initialized")
                    return {'err': True, 'message': 'Session not initialized'}

                async with self.throttler:
                    start_time = time.time()

                    logger.info(f"📤 API_REQUEST: Sending request (attempt {attempt + 1}/{MAX_RETRIES})...")

                    async with self.session.request(
                        method=method,
                        url=url,
                        headers=headers,
                        json=data,
                        params=params
                    ) as response:
                        response_text = await response.text()

                        # Log response time for monitoring
                        response_time = (time.time() - start_time) * 1000

                        logger.info(f"📥 API_RESPONSE: Received in {response_time:.2f}ms")
                        logger.info(f"   ├─ Status: {response.status}")
                        logger.info(f"   ├─ Content-Length: {len(response_text)} bytes")

                        if response.status == 200:
                            try:
                                result = ujson.loads(response_text)
                                logger.info(f"   ├─ Has error: {result.get('err', True)}")
                                logger.info(f"   └─ Response keys: {list(result.keys())}")
                                return result
                            except ujson.JSONDecodeError as json_err:
                                logger.error(f"❌ API_RESPONSE: Invalid JSON")
                                logger.error(f"   ├─ Error: {json_err}")
                                logger.error(f"   └─ Raw response (first 200 chars): {response_text[:200]}")
                                return {'err': True, 'message': 'Invalid JSON response'}
                        else:
                            error_msg = f"HTTP {response.status}: {response_text[:200]}"
                            logger.error(f"❌ API_RESPONSE: HTTP Error")
                            logger.error(f"   ├─ Status: {response.status}")
                            logger.error(f"   └─ Message: {response_text[:200]}")

                            if attempt == MAX_RETRIES - 1:  # Last attempt
                                return {'err': True, 'message': error_msg}

                            # Wait before retry (exponential backoff)
                            retry_delay = 2 ** attempt
                            logger.warning(f"⏳ Retrying in {retry_delay}s...")
                            await asyncio.sleep(retry_delay)

            except asyncio.TimeoutError:
                logger.warning(f"⏱️ API_REQUEST: Timeout on attempt {attempt + 1}")
                if attempt == MAX_RETRIES - 1:
                    return {'err': True, 'message': 'Request timeout'}
                await asyncio.sleep(2 ** attempt)

            except aiohttp.ClientError as e:
                logger.error(f"❌ API_REQUEST: Client error on attempt {attempt + 1}: {e}")
                if attempt == MAX_RETRIES - 1:
                    return {'err': True, 'message': f'Client error: {str(e)}'}
                await asyncio.sleep(2 ** attempt)

            except Exception as e:
                logger.error(f"❌ API_REQUEST: Unexpected error on attempt {attempt + 1}: {e}", exc_info=True)
                if attempt == MAX_RETRIES - 1:
                    return {'err': True, 'message': f'Unexpected error: {str(e)}'}
                await asyncio.sleep(2 ** attempt)

        logger.error(f"❌ API_REQUEST: Max retries exceeded for {method} {endpoint}")
        return {'err': True, 'message': 'Max retries exceeded'}

    # Wallet Management
    async def get_wallets(self, wallet_type: str = 'solana', page: int = 0, size: int = 20) -> Dict[str, Any]:
        """Get user wallets"""
        params = {
            'type': wallet_type,
            'page': page,
            'size': size
        }
        return await self._make_request('GET', '/account/wallets', params=params)

    async def import_wallet(self, wallet_type: str, name: str, private_key: str) -> Dict[str, Any]:
        """Import a new wallet"""
        data = {
            'type': wallet_type,
            'name': name,
            'privateKey': private_key
        }
        return await self._make_request('POST', '/account/wallet', data=data)

    # Token Data Operations
    async def get_pair_info(self, chain: str, pair: str) -> Dict[str, Any]:
        """Get comprehensive token/pair information for validation

        Args:
            chain: Blockchain (solana, bsc, ethereum, base, tron)
            pair: Trading pair contract address

        Returns:
            Dict containing token data including:
            - marketCap, holders, snipersCount
            - buyVolume/sellVolume for various timeframes
            - safetyInfo (freeze authority, mint authority, etc.)
            - isLaunchMigration, tokenCreatedAt, etc.
        """
        params = {
            'chain': chain,
            'pair': pair
        }

        logger.info(f"🌐 API_CLIENT: get_pair_info called")
        logger.info(f"   ├─ Endpoint: GET /kline/pair_info")
        logger.info(f"   ├─ Chain: {chain}")
        logger.info(f"   └─ Pair: {pair}")

        result = await self._make_request('GET', '/kline/pair_info', params=params)

        logger.info(f"📥 API_CLIENT: get_pair_info response")
        logger.info(f"   ├─ Has error: {result.get('err', True)}")
        logger.info(f"   ├─ Full response: {ujson.dumps(result)}")
        if not result.get('err', True) and 'res' in result:
            res = result.get('res', [])
            if res and len(res) > 0:
                pair_data = res[0]
                logger.info(f"   ├─ Token: {pair_data.get('name')} ({pair_data.get('symbol')})")
                logger.info(f"   ├─ Market Cap: ${pair_data.get('marketCap', 0):,.2f}")
                logger.info(f"   ├─ Holders: {pair_data.get('holders', 0)}")
                logger.info(f"   ├─ Snipers: {pair_data.get('snipersCount', 0)}")
                logger.info(f"   └─ Available fields: {list(pair_data.keys())}")

        return result

    # Trading Operations
    async def create_swap_order(self, order_type: str, chain: str, pair: str,
                                wallet_id: str, amount_or_percent: float,
                                user_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Create fast buy/sell order - PRIMARY TRADING FUNCTION"""

        # Import centralized fallback utility
        from utils import get_sell_setting_with_fallback
        
        # Use sell-specific settings if this is a sell order, otherwise use buy settings
        if order_type == 'sell':
            priority_fee = get_sell_setting_with_fallback(user_settings, 'priorityFee', '')
            gas_fee_delta = get_sell_setting_with_fallback(user_settings, 'gasFeeDelta', 10)
            max_fee_per_gas = get_sell_setting_with_fallback(user_settings, 'maxFeePerGas', 150)
            jito_tip = get_sell_setting_with_fallback(user_settings, 'jitoTip', 0.002)
            custom_fee_and_tip = get_sell_setting_with_fallback(user_settings, 'customFeeAndTip', False)
            max_slippage = get_sell_setting_with_fallback(user_settings, 'maxSlippage', 0.25)
        else:
            priority_fee = user_settings.get('priorityFee', '')
            gas_fee_delta = user_settings.get('gasFeeDelta', 5)
            max_fee_per_gas = user_settings.get('maxFeePerGas', 100)
            jito_tip = user_settings.get('jitoTip', 0.001)
            custom_fee_and_tip = user_settings.get('customFeeAndTip', False)
            max_slippage = user_settings.get('maxSlippage', 0.15)

        order_data = {
            'chain': chain,
            'pair': pair,
            'walletId': wallet_id,
            'type': order_type,
            'amountOrPercent': amount_or_percent,

            # Gas & Fee Settings (sell-specific for sells, buy settings for buys)
            'customFeeAndTip': custom_fee_and_tip,
            'priorityFee': priority_fee,
            'gasFeeDelta': gas_fee_delta,
            'maxFeePerGas': max_fee_per_gas,
            'jitoEnabled': user_settings.get('jitoEnabled', True),
            'jitoTip': jito_tip,

            # Trading Settings
            'maxSlippage': max_slippage,
            'concurrentNodes': user_settings.get('concurrentNodes', 3),
            'retries': user_settings.get('retries', 2),

            # Auto-sell Settings
            'migrateSellPercent': user_settings.get('migrateSellPercent', 0.0),
            'minDevSellPercent': user_settings.get('minDevSellPercent', 0.5),
            'devSellPercent': user_settings.get('devSellPercent', 1.0),

            # PnL Settings (if enabled)
            'stopEarnPercent': user_settings.get('stopEarnPercent'),
            'stopLossPercent': user_settings.get('stopLossPercent'),
            'stopEarnGroup': user_settings.get('stopEarnGroup'),
            'stopLossGroup': user_settings.get('stopLossGroup'),
            'trailingStopGroup': user_settings.get('trailingStopGroup'),
            'pnlOrderExpireDelta': user_settings.get('pnlOrderExpireDelta', 43200000),
            'pnlOrderExpireExecute': user_settings.get('pnlOrderExpireExecute', False),
            'pnlOrderUseMidPrice': user_settings.get('pnlOrderUseMidPrice', True),
            'pnlCustomConfigEnabled': user_settings.get('pnlCustomConfigEnabled', False),
            'pnlCustomConfig': user_settings.get('pnlCustomConfig')
        }

        logger.info(f"📤 API_CLIENT: Order payload built")
        logger.info(f"   ├─ Type: {order_data['type']}")
        logger.info(f"   ├─ Max Slippage: {order_data['maxSlippage']}")
        logger.info(f"   ├─ Jito Enabled: {order_data['jitoEnabled']}")
        logger.info(f"   ├─ Jito Tip: {order_data['jitoTip']}")
        logger.info(f"   └─ Retries: {order_data['retries']}")

        # Make actual POST request to the API
        result = await self._make_request('POST', '/automation/swap_order', data=order_data)

        logger.info(f"📥 API_CLIENT: create_swap_order response")
        logger.info(f"   ├─ Has error: {result.get('err', True)}")
        logger.info(f"   └─ Response keys: {list(result.keys())}")

        if not result.get('err', True):
            res_data = result.get('res', {})
            if isinstance(res_data, dict):
                logger.info(f"   ├─ Order ID: {res_data.get('id', 'Unknown')}")
                logger.info(f"   └─ Response data keys: {list(res_data.keys())}")
        else:
            logger.error(f"   └─ Error message: {result.get('message', 'Unknown error')}")

        return result

    # Fast Buy Function - Optimized for Speed
    async def fast_buy(
        self,
        chain: str,
        pair: str,
        wallet_id: str,
        amount: float,
        user_settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Ultra-fast buy execution with user settings"""

        logger.info(f"🚀 API_CLIENT: fast_buy called")
        logger.info(f"   ├─ Chain: {chain}")
        logger.info(f"   ├─ Pair: {pair}")
        logger.info(f"   ├─ Wallet ID: {wallet_id}")
        logger.info(f"   └─ Amount: {amount}")

        # Build optimized order payload
        order_data = {
            'chain': chain,
            'pair': pair,
            'walletId': wallet_id,
            'type': 'buy',
            'amountOrPercent': amount,

            # Gas & Fee Settings
            'customFeeAndTip': user_settings.get('customFeeAndTip', False),
            'priorityFee': user_settings.get('priorityFee', ''),
            'gasFeeDelta': user_settings.get('gasFeeDelta', 5),
            'maxFeePerGas': user_settings.get('maxFeePerGas', 100),
            'jitoEnabled': user_settings.get('jitoEnabled', True),
            'jitoTip': user_settings.get('jitoTip', 0.001),

            # Trading Settings
            'maxSlippage': user_settings.get('maxSlippage', 0.15),
            'concurrentNodes': user_settings.get('concurrentNodes', 3),
            'retries': user_settings.get('retries', 2),

            # Auto-sell Settings
            'migrateSellPercent': user_settings.get('migrateSellPercent', 0.0),
            'minDevSellPercent': user_settings.get('minDevSellPercent', 0.5),
            'devSellPercent': user_settings.get('devSellPercent', 1.0),

            # PnL Settings (if enabled)
            'stopEarnPercent': user_settings.get('stopEarnPercent'),
            'stopLossPercent': user_settings.get('stopLossPercent'),
            'stopEarnGroup': user_settings.get('stopEarnGroup'),
            'stopLossGroup': user_settings.get('stopLossGroup'),
            'trailingStopGroup': user_settings.get('trailingStopGroup'),
            'pnlOrderExpireDelta': user_settings.get('pnlOrderExpireDelta', 43200000),
            'pnlOrderExpireExecute': user_settings.get('pnlOrderExpireExecute', False),
            'pnlOrderUseMidPrice': user_settings.get('pnlOrderUseMidPrice', True),
            'pnlCustomConfigEnabled': user_settings.get('pnlCustomConfigEnabled', False),
            'pnlCustomConfig': user_settings.get('pnlCustomConfig')
        }

        logger.info(f"📤 API_CLIENT: Order payload built")
        logger.info(f"   ├─ Type: {order_data['type']}")
        logger.info(f"   ├─ Max Slippage: {order_data['maxSlippage']}")
        logger.info(f"   ├─ Jito Enabled: {order_data['jitoEnabled']}")
        logger.info(f"   ├─ Jito Tip: {order_data['jitoTip']}")
        logger.info(f"   └─ Retries: {order_data['retries']}")

        result = await self.create_swap_order('buy', chain, pair, wallet_id, amount, user_settings)

        logger.info(f"📥 API_CLIENT: fast_buy response")
        logger.info(f"   ├─ Has error: {result.get('err', True)}")
        logger.info(f"   └─ Response keys: {list(result.keys())}")

        if not result.get('err', True):
            res_data = result.get('res', {})
            if isinstance(res_data, dict):
                logger.info(f"   ├─ Order ID: {res_data.get('id', 'Unknown')}")
                logger.info(f"   └─ Response data keys: {list(res_data.keys())}")
        else:
            logger.error(f"   └─ Error message: {result.get('message', 'Unknown error')}")

        return result

    # Fast Sell Function - Optimized for Speed
    async def fast_sell(
        self,
        chain: str,
        pair: str,
        wallet_id: str,
        amount_or_percent: float,
        user_settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Ultra-fast sell execution with user settings"""

        logger.info(f"🚀 API_CLIENT: fast_sell called")
        logger.info(f"   ├─ Chain: {chain}")
        logger.info(f"   ├─ Pair: {pair}")
        logger.info(f"   ├─ Wallet ID: {wallet_id}")
        logger.info(f"   └─ Amount/Percent: {amount_or_percent}")

        result = await self.create_swap_order('sell', chain, pair, wallet_id, amount_or_percent, user_settings)

        logger.info(f"📥 API_CLIENT: fast_sell response")
        logger.info(f"   ├─ Has error: {result.get('err', True)}")
        logger.info(f"   └─ Response keys: {list(result.keys())}")

        if not result.get('err', True):
            res_data = result.get('res', {})
            if isinstance(res_data, dict):
                logger.info(f"   ├─ Order ID: {res_data.get('id', 'Unknown')}")
                logger.info(f"   └─ Response data keys: {list(res_data.keys())}")
        else:
            logger.error(f"   └─ Error message: {result.get('message', 'Unknown error')}")

        return result

    # Create Dev Sell Order
    async def create_dev_sell_order(self, chain: str, pair_type: str, pair: str,
                                   wallet_id: str, min_dev_sell_percent: float,
                                   amount_or_percent: float, user_settings: dict) -> dict:
        """Create dev sell order"""
        if not self.api_key:
            return {'err': True, 'message': 'API key not configured'}

        # Import centralized fallback utility
        from utils import get_sell_setting_with_fallback

        # Use sell-specific settings for dev sell
        priority_fee = get_sell_setting_with_fallback(user_settings, 'priorityFee', '')
        jito_tip = get_sell_setting_with_fallback(user_settings, 'jitoTip', 0.002)
        custom_fee_and_tip = get_sell_setting_with_fallback(user_settings, 'customFeeAndTip', False)
        max_slippage = get_sell_setting_with_fallback(user_settings, 'maxSlippage', 0.25)

        order_data = {
            'chain': chain,
            'pairType': pair_type,
            'pair': pair,
            'walletId': wallet_id,
            'tradeType': 'sell',
            'minDevSellPercent': min_dev_sell_percent,
            'amountOrPercent': amount_or_percent,

            # Gas & Fee Settings (sell-specific)
            'customFeeAndTip': custom_fee_and_tip,
            'priorityFee': priority_fee,
            'jitoEnabled': user_settings.get('jitoEnabled', True),
            'jitoTip': jito_tip,

            # Trading Settings
            'expireDelta': user_settings.get('pnlOrderExpireDelta', 43200000),
            'maxSlippage': max_slippage,
            'concurrentNodes': user_settings.get('concurrentNodes', 3),
            'retries': user_settings.get('retries', 2)
        }

        result = await self._make_request('POST', '/automation/dev_order', data=order_data)
        logger.info(f"📥 API_CLIENT: create_dev_sell_order response")
        logger.info(f"   ├─ Has error: {result.get('err', True)}")
        logger.info(f"   └─ Response keys: {list(result.keys())}")

        if not result.get('err', True):
            res_data = result.get('res', {})
            if isinstance(res_data, dict):
                logger.info(f"   ├─ Order ID: {res_data.get('id', 'Unknown')}")
                logger.info(f"   └─ Response data keys: {list(res_data.keys())}")
        else:
            logger.error(f"   └─ Error message: {result.get('message', 'Unknown error')}")

        return result

    # Create Migrate Order
    async def create_migrate_order(self, chain: str, pair_type: str, pair: str,
                                  wallet_id: str, amount_or_percent: float,
                                  user_settings: dict) -> dict:
        """Create migrate (opening) sell order"""
        if not self.api_key:
            return {'err': True, 'message': 'API key not configured'}

        # Import centralized fallback utility
        from utils import get_sell_setting_with_fallback

        # Use sell-specific settings for migrate sell
        priority_fee = get_sell_setting_with_fallback(user_settings, 'priorityFee', '')
        jito_tip = get_sell_setting_with_fallback(user_settings, 'jitoTip', 0.002)
        custom_fee_and_tip = get_sell_setting_with_fallback(user_settings, 'customFeeAndTip', False)
        max_slippage = get_sell_setting_with_fallback(user_settings, 'maxSlippage', 0.25)

        order_data = {
            'chain': chain,
            'pairType': pair_type,
            'pair': pair,
            'walletId': wallet_id,
            'tradeType': 'sell',
            'amountOrPercent': amount_or_percent,

            # Gas & Fee Settings (sell-specific)
            'customFeeAndTip': custom_fee_and_tip,
            'priorityFee': priority_fee,
            'jitoEnabled': user_settings.get('jitoEnabled', True),
            'jitoTip': jito_tip,

            # Trading Settings
            'expireDelta': user_settings.get('pnlOrderExpireDelta', 43200000),
            'maxSlippage': max_slippage,
            'concurrentNodes': user_settings.get('concurrentNodes', 3),
            'retries': user_settings.get('retries', 2)
        }

        try:
            result = await self._make_request('POST', '/automation/migrate_order', data=order_data)
            logger.info(f"📥 API_CLIENT: create_migrate_order response")
            logger.info(f"   ├─ Has error: {result.get('err', True)}")
            logger.info(f"   └─ Response keys: {list(result.keys())}")

            if not result.get('err', True):
                res_data = result.get('res', {})
                if isinstance(res_data, dict):
                    logger.info(f"   ├─ Order ID: {res_data.get('id', 'Unknown')}")
                    logger.info(f"   └─ Response data keys: {list(res_data.keys())}")
            else:
                logger.error(f"   └─ Error message: {result.get('message', 'Unknown error')}")

            return result
        except Exception as e:
            logger.error(f"❌ Error creating migrate order: {e}", exc_info=True)
            return {'err': True, 'message': f'Failed to create migrate order: {str(e)}'}

    # Health Check
    async def health_check(self) -> bool:
        """Check if API is responsive"""
        try:
            response = await self.get_wallets(page=0, size=1)
            return not response.get('err', True)
        except Exception:
            return False

    async def test_connection(self) -> bool:
        """Test DBOTX API connectivity - alias for health_check"""
        return await self.health_check()


# Global client instance
client = DBOTXClient()