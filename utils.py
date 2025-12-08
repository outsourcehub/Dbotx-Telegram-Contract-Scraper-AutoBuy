"""
Utility Functions for Ultra-Fast Trading Bot
Speed-optimized contract detection and validation
"""
import re
import time
from typing import Optional, Tuple, Dict, Any, List
from config import CHAIN_PATTERNS, EVM_RPC_ENDPOINTS
import logging
import uuid
import requests
import aiohttp
import asyncio

logger = logging.getLogger(__name__)

# Pre-compile regex patterns for maximum speed
COMPILED_PATTERNS = {
    chain: re.compile(pattern) 
    for chain, pattern in CHAIN_PATTERNS.items()
}

# Link pattern matchers for extracting addresses from URLs (ULTRA-AGGRESSIVE)
# Enhanced patterns that capture both chain and address
LINK_PATTERNS = {
    # Photon patterns - capture chain from subdomain and pair address
    'photon_sol': re.compile(r'photon-sol\.tinyastro\.io/[^/\s]*/lp/([A-Za-z0-9]{32,})(?:\?|$|\s)', re.IGNORECASE),
    'photon_bnb': re.compile(r'photon-bnb\.tinyastro\.io/[^/\s]*/lp/([A-Za-z0-9]{32,})(?:\?|$|\s)', re.IGNORECASE),
    'photon_base': re.compile(r'photon-base\.tinyastro\.io/[^/\s]*/lp/([A-Za-z0-9]{32,})(?:\?|$|\s)', re.IGNORECASE),
    'photon_eth': re.compile(r'photon\.tinyastro\.io/[^/\s]*/lp/([A-Za-z0-9]{32,})(?:\?|$|\s)', re.IGNORECASE),

    # DexScreener patterns - capture chain from path and address
    'dexscreener': re.compile(r'dexscreener\.com/(solana|base|arbitrum|bsc|tron|ethereum)/([A-Za-z0-9]{32,})(?:\?|$|\s)', re.IGNORECASE),

    # DBotx patterns - capture chain from path and address
    'dbotx': re.compile(r'dbotx\.com/token/(solana|bsc)/([A-Za-z0-9]{32,})(?:\?|$|\s)', re.IGNORECASE),

    # GMGN patterns - capture chain from path and token contract
    'gmgn': re.compile(r'gmgn\.ai/(sol|bsc|base|eth|tron)/token/([A-Za-z0-9]{32,})(?:\?|$|\s)', re.IGNORECASE),

    # Legacy patterns for backwards compatibility
    'dextools': re.compile(r'dextools\.io/[^/\s]*/pair-explorer/([A-Za-z0-9]{32,})', re.IGNORECASE),
    'birdeye': re.compile(r'birdeye\.so/token/([A-Za-z0-9]{32,})', re.IGNORECASE),
    'pump': re.compile(r'pump\.fun/([A-Za-z0-9]{32,})', re.IGNORECASE),
    'raydium': re.compile(r'raydium\.io/[^/\s]*/([A-Za-z0-9]{32,})', re.IGNORECASE),
    'jupiter': re.compile(r'jup\.ag/swap/[^-\s]+-([A-Za-z0-9]{32,})', re.IGNORECASE),
    # Generic URL pattern - extract any 32+ char sequence from URLs
    'generic_url': re.compile(r'https?://[^\s]+/([A-Za-z0-9]{32,})', re.IGNORECASE),
}

# Chain mapping for aggregator subdomains/paths
CHAIN_MAPPING = {
    'sol': 'solana',
    'solana': 'solana',
    'bnb': 'bsc',
    'bsc': 'bsc',
    'base': 'base',
    'eth': 'ethereum',
    'ethereum': 'ethereum',
    'tron': 'tron',
    'arbitrum': 'arbitrum'
}


def detect_contract_address(text: str) -> Optional[Tuple[str, str]]:
    """
    Multi-strategy contract address detection with comprehensive logging
    Returns (chain, address) tuple or None

    Strategy:
    1. Extract addresses from common DEX tool links (DexScreener, DexTools, etc.)
    2. Find standalone addresses using aggressive multi-line regex
    3. Clean and validate each candidate
    4. Return first valid match
    """
    logger.info(f"🔍🔍🔍 DETECT_CONTRACT_ADDRESS CALLED")
    logger.info(f"🔍 Input text length: {len(text) if text else 0}")
    logger.info(f"🔍 Input preview: {repr(text[:200]) if text else 'None'}")

    if not text:
        logger.warning("❌ Contract detection: Empty text")
        return None

    # STRATEGY 1: Extract from links first (highest confidence)
    link_result = _extract_from_links(text)
    if link_result:
        logger.info(f"✅ Contract found via LINK extraction")
        return link_result

    # STRATEGY 2: Extract from raw text using aggressive patterns
    text_result = _extract_from_text(text)
    if text_result:
        logger.info(f"✅ Contract found via TEXT extraction")
        return text_result

    logger.debug(f"⚪ No contract found in text")
    return None


def _extract_from_links(text: str) -> Optional[Tuple[str, str]]:
    """
    Extract contract addresses from common DEX tool links with chain detection
    Supports: DexScreener, DexTools, Photon, Birdeye, GMGN, DBotx
    """
    logger.debug("🔗 Checking for DEX tool links...")

    for tool_name, pattern in LINK_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            logger.info(f"🔗 Found {len(matches)} {tool_name} link(s)")

            for match in matches:
                # Handle different match formats
                if isinstance(match, tuple):
                    # Pattern captured multiple groups (chain, address)
                    if len(match) == 2:
                        chain_identifier, address_candidate = match
                        # Map chain identifier to standard chain name
                        chain = CHAIN_MAPPING.get(chain_identifier.lower())
                        cleaned = address_candidate.strip()

                        if chain:
                            # Direct chain detection from URL
                            _, validated_address = _detect_and_validate_address(cleaned, f"{tool_name}_link", text)
                            if validated_address:
                                logger.info(f"🎯 VALID ADDRESS from {tool_name}: {chain.upper()} | {validated_address}")
                                return (chain, validated_address)
                else:
                    # Single group capture (address only)
                    cleaned = match.strip()

                    # Determine chain from tool name
                    if 'photon_sol' in tool_name:
                        chain = 'solana'
                    elif 'photon_bnb' in tool_name:
                        chain = 'bsc'
                    elif 'photon_base' in tool_name:
                        chain = 'base'
                    elif 'photon_eth' in tool_name:
                        chain = 'ethereum'
                    else:
                        # Fallback to auto-detection with context
                        chain, validated_address = _detect_and_validate_address(cleaned, f"{tool_name}_link", text)
                        if chain and validated_address:
                            logger.info(f"🎯 VALID ADDRESS from {tool_name}: {chain.upper()} | {validated_address}")
                            return (chain, validated_address)
                        continue

                    # Validate with known chain
                    _, validated_address = _detect_and_validate_address(cleaned, f"{tool_name}_link", text)
                    if validated_address:
                        logger.info(f"🎯 VALID ADDRESS from {tool_name}: {chain.upper()} | {validated_address}")
                        return (chain, validated_address)

    return None


def _extract_from_text(text: str) -> Optional[Tuple[str, str]]:
    """
    ULTRA-AGGRESSIVE text extraction with multiple fallback strategies

    Pass 1: Normalize text
    Pass 2: Extract from permissive patterns
    Pass 3: Word boundary extraction
    Pass 4: Extract from URLs/paths
    Pass 5: Brute force - find ANY 32+ char sequence
    """
    logger.debug("📝 Extracting from raw text...")

    # Pass 1: Normalize text
    normalized = _normalize_text(text)
    logger.debug(f"📝 Normalized text length: {len(normalized)}")

    # Pass 2: Permissive pattern extraction
    candidates = _find_address_candidates(normalized)
    logger.debug(f"📝 Found {len(candidates)} address candidates from patterns")

    # Pass 3: Word boundary extraction - split by common separators and check each word
    separators = [' ', '\n', '\r', '\t', '/', '\\', '|', ':', ',', ';', '"', "'", '(', ')', '[', ']', '{', '}']
    words = [normalized]
    for sep in separators:
        new_words = []
        for word in words:
            new_words.extend(word.split(sep))
        words = new_words

    for word in words:
        if len(word) >= 32:
            # Could be an address
            candidates.append(('unknown', word))

    # Pass 4: Extract from URLs and file paths
    url_addresses = re.findall(r'/([A-Za-z0-9]{32,})', text)
    for addr in url_addresses:
        candidates.append(('unknown', addr))

    logger.debug(f"📝 Total candidates after all passes: {len(candidates)}")

    # Clean and validate ALL candidates
    seen_addresses = set()
    for candidate_type, raw_address in candidates:
        cleaned = _clean_address_aggressive(raw_address)

        if not cleaned or len(cleaned) < 32:
            continue

        # Skip duplicates
        if cleaned in seen_addresses:
            continue
        seen_addresses.add(cleaned)

        # Detect chain and validate (pass full text as context)
        chain, validated_address = _detect_and_validate_address(cleaned, candidate_type, text)
        if chain and validated_address:
            logger.info(f"🎯 VALID ADDRESS from text: {chain.upper()} | {validated_address}")
            return (chain, validated_address)

    return None


def _normalize_text(text: str) -> str:
    """
    Normalize text to handle Telegram formatting quirks
    - Remove zero-width spaces
    - Preserve structure but normalize excessive whitespace
    """
    # Remove zero-width chars
    text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)

    # Don't collapse newlines (addresses might span lines)
    # Just normalize multiple spaces on same line
    lines = text.split('\n')
    normalized_lines = [re.sub(r' {2,}', ' ', line) for line in lines]

    return '\n'.join(normalized_lines)


def _find_address_candidates(text: str) -> List[Tuple[str, str]]:
    """
    ULTRA-AGGRESSIVE address detection with multiple extraction passes
    Returns list of (type, raw_address) tuples
    """
    candidates = []

    # PASS 1: Direct extraction with strict continuous patterns only
    # TRON: T + exactly 33 base58 chars (continuous)
    tron_pattern = r'T[A-HJ-NP-Za-km-z1-9]{33}'
    for match in re.finditer(tron_pattern, text):
        candidates.append(('tron', match.group(0)))

    # EVM: 0x + exactly 40 hex chars (continuous)
    evm_pattern = r'0x[a-fA-F0-9]{40}'
    for match in re.finditer(evm_pattern, text):
        candidates.append(('evm', match.group(0)))

    # Solana: 32-44 base58 chars (continuous)
    solana_pattern = r'(?<![A-Za-z0-9])[1-9A-HJ-NP-Za-km-z]{32,44}(?![A-Za-z0-9])'
    for match in re.finditer(solana_pattern, text):
        raw = match.group(0)
        if not raw.startswith('0x') and not raw.startswith('T'):
            candidates.append(('solana', raw))

    return candidates


def _clean_address_aggressive(raw: str) -> str:
    """
    ULTRA-AGGRESSIVE address cleaning
    - Remove ALL non-alphanumeric except 0x prefix
    - Handle ANY separator character
    - Extract pure address from any context
    """
    # Step 1: Remove ALL Unicode emojis, symbols, and special chars
    # Keep only alphanumeric and x (for 0x)
    cleaned = ''
    for char in raw:
        if char.isalnum() or char == 'x':
            cleaned += char

    # Step 2: Handle 0x prefix restoration
    if raw.strip().startswith('0') and 'x' in cleaned[:10]:
        # Ensure 0x prefix is intact
        x_pos = cleaned.find('x')
        if x_pos > 0 and cleaned[x_pos-1] == '0':
            # 0x is already correct
            pass
        elif x_pos == 0:
            # Missing 0 before x
            cleaned = '0' + cleaned
        else:
            # 0 and x are separated
            cleaned = '0x' + cleaned.replace('0', '', 1).replace('x', '', 1)

    # Step 3: Remove common text prefixes (after cleaning)
    text_markers = ['contract', 'ca', 'address', 'token', 'pair', 'mint', 'swap', 'buy']
    for marker in text_markers:
        if cleaned.lower().startswith(marker):
            cleaned = cleaned[len(marker):]
            break

    # Step 4: Remove any remaining non-address characters
    # Keep only: 0-9, a-f, A-F (for EVM), 1-9, A-Z, a-z (for Solana/TRON)
    final = ''
    for char in cleaned:
        if char in '0123456789abcdefABCDEFxXTtGgHhJjKkLlMmNnPpQqRrSsUuVvWwYyZz':
            final += char

    return final.strip()


def _detect_and_validate_address(address: str, source: str = 'unknown', context: str = '') -> Tuple[Optional[str], Optional[str]]:
    """
    Detect chain type and validate address format
    Returns (chain, validated_address) or (None, None)
    
    Strategy:
    1. Detect address format (TRON, EVM, Solana)
    2. Use context keywords to determine specific chain
    3. Fall back to format-based defaults if no context
    """
    # TRON: T + 33 chars
    if len(address) == 34 and address.startswith('T') and address[1:].isalnum():
        if COMPILED_PATTERNS['tron'].match(address):
            # Try context detection first
            chain_from_context = _detect_evm_chain(context, address) if context else None
            if chain_from_context == 'tron':
                logger.info(f"   ✅ Tron chain confirmed via context")
            
            if _validate_address('tron', address):
                return ('tron', address)

    # EVM: 0x + 40 hex chars (could be BSC, Ethereum, Base, or Arbitrum)
    if len(address) == 42 and address.startswith('0x'):
        if COMPILED_PATTERNS['bsc'].match(address):  # EVM pattern works for all
            # Try to detect specific EVM chain via context
            chain = None
            if context:
                chain = _detect_evm_chain(context, address)
            
            # If no context match, default to ethereum
            if not chain:
                chain = 'ethereum'
                logger.info(f"   ⚠️ No context keywords found, defaulting to Ethereum")
            
            if _validate_address(chain, address):
                return (chain, address)

    # Solana: 32-44 base58 chars
    if 32 <= len(address) <= 44 and not address.startswith('0x') and not address.startswith('T'):
        # Try context detection first
        chain_from_context = _detect_evm_chain(context, address) if context else None
        if chain_from_context == 'solana':
            logger.info(f"   ✅ Solana chain confirmed via context")
        
        # Skip base58 character validation - send address as-is to DBOT API
        if _validate_address('solana', address):
            return ('solana', address)

    logger.debug(f"❌ Failed validation: {address} (len={len(address)}, source={source})")
    return (None, None)


def _detect_evm_chain(context: str, address: str) -> Optional[str]:
    """
    Detect specific chain based on STRICT context keyword matching only
    Supports: BSC, Ethereum, Base, Arbitrum, Solana, Tron
    
    Returns chain name or None if no keywords found
    """
    context_lower = context.lower()
    
    logger.info(f"🔗 Chain detection: Analyzing context for keywords")
    logger.debug(f"   Context preview: {context_lower[:200]}")
    
    # STRICT KEYWORD MATCHING - Each chain has specific keywords only
    
    # BSC - Only "bsc"
    if 'bsc' in context_lower:
        logger.info(f"🔗 Chain detection: Found BSC keyword")
        return 'bsc'
    
    # Ethereum - Only "ethereum" or "eth"
    if 'ethereum' in context_lower or 'eth' in context_lower:
        logger.info(f"🔗 Chain detection: Found Ethereum keyword")
        return 'ethereum'
    
    # Base - Only "base"
    if 'base' in context_lower:
        logger.info(f"🔗 Chain detection: Found Base keyword")
        return 'base'
    
    # Arbitrum - Only "arb" or "arbitrum"
    if 'arb' in context_lower or 'arbitrum' in context_lower:
        logger.info(f"🔗 Chain detection: Found Arbitrum keyword")
        return 'arbitrum'
    
    # Solana - Only "sol" or "solana"
    if 'sol' in context_lower or 'solana' in context_lower:
        logger.info(f"🔗 Chain detection: Found Solana keyword")
        return 'solana'
    
    # Tron - Only "trx" or "tron"
    if 'trx' in context_lower or 'tron' in context_lower:
        logger.info(f"🔗 Chain detection: Found Tron keyword")
        return 'tron'
    
    # No keywords found
    logger.warning(f"🔗 Chain detection: No chain keywords found in context")
    return None


def _validate_address(chain: str, address: str) -> bool:
    """Additional validation for detected addresses"""
    if chain == 'solana':
        # Solana: Basic length check only (32-44 chars)
        if len(address) < 32 or len(address) > 44:
            return False
        # Check for obvious scam patterns
        if '1111111111111111111111111111111111111111111111' in address:
            return False

    elif chain in ['bsc', 'base', 'ethereum']:
        # EVM addresses should be 42 characters with 0x prefix
        if len(address) != 42 or not address.startswith('0x'):
            return False
        # Check for obvious scam patterns
        if address.lower() in ['0x0000000000000000000000000000000000000000', 
                              '0xdead000000000000000000000000000000000000']:
            return False

    elif chain == 'tron':
        # TRON addresses should be 34 characters and start with 'T'
        if len(address) != 34 or not address.startswith('T'):
            return False

    return True


async def validate_via_dexscreener(chain: str, address: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate contract exists on DexScreener and extract verified token address
    Uses FALLBACK STRATEGY: tries pairs endpoint first, then tokens endpoint

    Args:
        chain: Blockchain name (solana, ethereum, bsc, base, tron)
        address: Contract address to validate (can be pair or token)

    Returns:
        Tuple of (is_valid, error_message, token_address)
        - (True, None, token_address) if found on DexScreener
        - (False, "reason", None) if validation fails
    """
    logger.info(f"🔍 DEXSCREENER VALIDATION: {chain.upper()} | {address}")
    
    # STRATEGY 1: Try pairs endpoint first (most common for aggregator links)
    logger.info(f"   📍 STRATEGY 1: Trying /pairs endpoint...")
    pairs_result = await _try_dexscreener_pairs(chain, address)
    
    if pairs_result[0]:  # Success
        logger.info(f"   ✅ STRATEGY 1 SUCCESS: Found via /pairs endpoint")
        return pairs_result
    
    logger.info(f"   ⚠️ STRATEGY 1 FAILED: {pairs_result[1]}")
    
    # STRATEGY 2: Fallback to tokens endpoint (for raw token addresses)
    logger.info(f"   📍 STRATEGY 2: Trying /tokens endpoint (fallback)...")
    tokens_result = await _try_dexscreener_tokens(chain, address)
    
    if tokens_result[0]:  # Success
        logger.info(f"   ✅ STRATEGY 2 SUCCESS: Found via /tokens endpoint")
        return tokens_result
    
    logger.info(f"   ⚠️ STRATEGY 2 FAILED: {tokens_result[1]}")
    
    # Both strategies failed
    error_msg = f"Not found on DexScreener (tried pairs & tokens endpoints)"
    logger.error(f"   ❌ BOTH STRATEGIES FAILED: {error_msg}")
    return (False, error_msg, None)


async def _try_dexscreener_pairs(chain: str, address: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """Try DexScreener /pairs endpoint"""
    try:
        url = f"https://api.dexscreener.com/latest/dex/pairs/{chain}/{address}"
        logger.debug(f"      └─ Pairs URL: {url}")

        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return (False, f"HTTP {response.status}", None)

                data = await response.json()
                pairs = data.get('pairs', [])

                if not pairs or len(pairs) == 0:
                    return (False, "No pairs found", None)

                # Extract token from first pair
                pair_data = pairs[0]
                base_token = pair_data.get('baseToken', {})
                token_address = base_token.get('address', '')
                
                if not token_address:
                    return (False, "No token address in pair data", None)

                logger.debug(f"      ├─ Found token: {base_token.get('name', 'Unknown')} ({base_token.get('symbol', 'Unknown')})")
                logger.debug(f"      └─ Token address: {token_address}")
                
                return (True, None, token_address)

    except asyncio.TimeoutError:
        return (False, "Timeout", None)
    except Exception as e:
        return (False, f"Error: {str(e)}", None)


async def _try_dexscreener_tokens(chain: str, address: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """Try DexScreener /tokens endpoint"""
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{address}"
        logger.debug(f"      └─ Tokens URL: {url}")

        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return (False, f"HTTP {response.status}", None)

                data = await response.json()
                pairs = data.get('pairs', [])

                if not pairs or len(pairs) == 0:
                    return (False, "No pairs found for token", None)

                # Filter pairs by chain
                chain_pairs = [p for p in pairs if p.get('chainId', '').lower() == chain.lower()]
                
                if not chain_pairs:
                    return (False, f"No pairs on {chain}", None)

                # Use first pair on this chain
                pair_data = chain_pairs[0]
                base_token = pair_data.get('baseToken', {})
                token_address = base_token.get('address', '')
                
                if not token_address:
                    return (False, "No token address in response", None)

                logger.debug(f"      ├─ Found token: {base_token.get('name', 'Unknown')} ({base_token.get('symbol', 'Unknown')})")
                logger.debug(f"      └─ Token address: {token_address}")
                
                return (True, None, token_address)

    except asyncio.TimeoutError:
        return (False, "Timeout", None)
    except Exception as e:
        return (False, f"Error: {str(e)}", None)


def validate_settings_input(setting_key: str, value: str) -> Tuple[bool, Any, str]:
    """
    Validate and convert user input for settings
    Returns (is_valid, converted_value, error_message)

    PERCENTAGE CONVERSION:
    - User enters 10, 50, 100 (human-readable %)
    - System converts to 0.1, 0.5, 1.0 (API format)
    """
    try:
        # COMPLEX SETTINGS - Multi-line group configurations
        if setting_key in ['stopEarnGroup', 'stopLossGroup']:
            # Parse multi-line format: "profit_percent: X, sell_percent: Y"
            lines = [line.strip() for line in value.strip().split('\n') if line.strip()]

            if not lines:
                return False, None, "Please enter at least one level"

            if len(lines) > 6:
                return False, None, "Maximum 6 levels allowed"

            parsed_levels = []
            for i, line in enumerate(lines, 1):
                try:
                    # Parse "profit_percent: 50, sell_percent: 25"
                    parts = {}
                    for pair in line.split(','):
                        if ':' not in pair:
                            return False, None, f"Line {i}: Invalid format - use 'profit_percent: X, sell_percent: Y'"
                        key, val = pair.split(':', 1)
                        parts[key.strip()] = float(val.strip())

                    if 'profit_percent' not in parts or 'sell_percent' not in parts:
                        return False, None, f"Line {i}: Missing profit_percent or sell_percent"

                    # Convert percentages to 0-1.0 range
                    profit = parts['profit_percent'] / 100.0 if parts['profit_percent'] > 1 else parts['profit_percent']
                    sell = parts['sell_percent'] / 100.0 if parts['sell_percent'] > 1 else parts['sell_percent']

                    if sell <= 0 or sell > 1.0:
                        return False, None, f"Line {i}: sell_percent must be between 0-100"

                    parsed_levels.append({
                        'profit_percent': profit,
                        'sell_percent': sell
                    })
                except (ValueError, KeyError) as e:
                    return False, None, f"Line {i}: Invalid number format"

            return True, parsed_levels, ""

        elif setting_key == 'trailingStopGroup':
            # Parse single-line format: "trigger_percent: 50, callback_percent: 20"
            try:
                parts = {}
                for pair in value.strip().split(','):
                    if ':' not in pair:
                        return False, None, "Invalid format - use 'trigger_percent: X, callback_percent: Y'"
                    key, val = pair.split(':', 1)
                    parts[key.strip()] = float(val.strip())

                if 'trigger_percent' not in parts or 'callback_percent' not in parts:
                    return False, None, "Missing trigger_percent or callback_percent"

                # Convert percentages to 0-1.0 range
                trigger = parts['trigger_percent'] / 100.0 if parts['trigger_percent'] > 1 else parts['trigger_percent']
                callback = parts['callback_percent'] / 100.0 if parts['callback_percent'] > 1 else parts['callback_percent']

                if trigger <= 0 or callback <= 0:
                    return False, None, "Percentages must be positive"

                result = [{
                    'trigger_percent': trigger,
                    'callback_percent': callback
                }]

                return True, result, ""
            except (ValueError, KeyError) as e:
                return False, None, f"Invalid format: {str(e)}"

        # Boolean settings
        if setting_key in ['jitoEnabled', 'customFeeAndTip', 'pnlOrderExpireExecute', 
                          'pnlOrderUseMidPrice', 'pnlCustomConfigEnabled',
                          'check_freeze_authority', 'check_mint_authority', 'require_launch_migration']:
            if value.lower() in ['true', '1', 'yes', 'on', 'enabled']:
                return True, True, ""
            elif value.lower() in ['false', '0', 'no', 'off', 'disabled']:
                return True, False, ""
            else:
                return False, None, "Please enter true/false, yes/no, or 1/0"

        # PERCENTAGE SETTINGS - User enters 0-100, we convert to 0-1.0
        percentage_settings = [
            'maxSlippage', 'stopEarnPercent', 'stopLossPercent',
            'migrateSellPercent', 'minDevSellPercent', 'devSellPercent',
            'sell_maxSlippage', 'sell_amountOrPercent',
            'top10_holder_max', 'lp_burn_min'
        ]

        if setting_key in percentage_settings:
            val = float(value)

            # Accept 0-100 range (user input)
            if 0 <= val <= 100:
                converted = val / 100.0  # Convert to 0-1.0 for API
                return True, converted, ""
            # Also accept 0-1.0 range (legacy/direct input)
            elif 0 <= val <= 1.0:
                return True, val, ""
            else:
                return False, None, f"Enter 0-100 (e.g., 50 for 50%)"

        # VOLUME RATIO SETTINGS - Already in % format (no conversion)
        if 'volume_ratio' in setting_key:
            val = float(value)
            if val >= 0:
                return True, val, ""
            else:
                return False, None, "Value must be positive"

        # MARKET CAP AND HOLDER SETTINGS - Integer values
        if setting_key in ['market_cap_min', 'market_cap_max', 'holders_min', 'snipers_max']:
            val = int(float(value))
            if val >= 0:
                return True, val, ""
            else:
                return False, None, "Value must be positive"

        # Amount settings (SOL/ETH/BNB amounts - no conversion)
        if setting_key in ['amountOrPercent', 'jitoTip', 'sell_jitoTip']:
            val = float(value)
            if val > 0:
                return True, val, ""
            else:
                return False, None, "Value must be greater than 0"

        # Integer settings
        if setting_key in ['retries', 'concurrentNodes', 'gasFeeDelta', 'maxFeePerGas', 
                          'sell_gasFeeDelta', 'sell_maxFeePerGas', 'pnlOrderExpireDelta']:
            val = int(float(value))

            if setting_key == 'retries' and 0 <= val <= 10:
                return True, val, ""
            elif setting_key == 'concurrentNodes' and 1 <= val <= 3:
                return True, val, ""
            elif setting_key in ['gasFeeDelta', 'sell_gasFeeDelta'] and val >= 0:
                return True, val, ""
            elif setting_key in ['maxFeePerGas', 'sell_maxFeePerGas'] and val > 0:
                return True, val, ""
            elif setting_key == 'pnlOrderExpireDelta' and 0 < val <= 432000000:
                return True, val, ""
            else:
                return False, None, f"Invalid range for {setting_key}"

        # String settings (priority fees)
        if setting_key in ['priorityFee', 'sell_priorityFee']:
            # Can be empty string for auto, or a number
            if value == '' or value.lower() == 'auto':
                return True, '', ""
            try:
                val = float(value)
                if val >= 0:
                    return True, str(val), ""
                else:
                    return False, None, "Priority fee must be positive or empty for auto"
            except ValueError:
                return False, None, "Invalid priority fee format"

        # Custom fee toggles
        if setting_key in ['sell_customFeeAndTip']:
            if value.lower() in ['true', '1', 'yes', 'on', 'enabled']:
                return True, True, ""
            elif value.lower() in ['false', '0', 'no', 'off', 'disabled']:
                return True, False, ""
            else:
                return False, None, "Please enter true/false"

        # Default case - return as string
        return True, value, ""

    except ValueError:
        return False, None, f"Invalid number format for {setting_key}"
    except Exception as e:
        return False, None, f"Validation error: {str(e)}"


def format_setting_display(key: str, value: Any) -> str:
    """
    Format setting values for display in menus

    PERCENTAGE DISPLAY:
    - System stores 0.1, 0.5, 1.0 (API format)
    - User sees 10%, 50%, 100% (human-readable)
    """
    if value is None:
        return "Not set"

    if isinstance(value, bool):
        return "✅ Enabled" if value else "❌ Disabled"

    if isinstance(value, list):
        # For enabled_chains
        if key == 'enabled_chains':
            return ', '.join([c.upper() for c in value]) if value else "None"
        return str(value)

    if isinstance(value, float):
        # Format percentages (0.1 → 10%, 0.5 → 50%, 1.0 → 100%)
        if key in ['maxSlippage', 'stopEarnPercent', 'stopLossPercent', 
                  'migrateSellPercent', 'minDevSellPercent', 'devSellPercent',
                  'sell_maxSlippage', 'sell_amountOrPercent',
                  'top10_holder_max', 'lp_burn_min']:
            return f"{value * 100:.1f}%"
        # Format volume ratios (already in % format, no conversion)
        elif 'volume_ratio' in key:
            return f"{value:.0f}% threshold"
        # Format amounts (SOL/ETH/BNB amounts)
        elif key in ['amountOrPercent', 'jitoTip', 'sell_jitoTip']:
            return f"{value:.4f}"
        # Format market cap
        elif 'market_cap' in key:
            return f"${value:,.0f}"
        else:
            return str(value)

    if isinstance(value, int):
        # Format market cap, holders, snipers
        if 'market_cap' in key:
            return f"${value:,.0f}"
        return str(value)

    if isinstance(value, str) and value == '':
        return "Auto"

    return str(value)


def format_order_summary(order) -> str:
    """Format order details for display"""
    status_emoji = {
        'pending': '⏳',
        'completed': '✅',
        'failed': '❌'
    }.get(order.status, '❓')

    # Format creation time
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

    summary = f"{status_emoji} **{order.order_type.upper()}** on {order.chain.upper()}\n"
    summary += f"🔗 Contract: `{pair_display}`\n"
    summary += f"💰 Amount: {order.amount}\n"
    summary += f"⏰ {time_str}\n"

    if order.status == 'failed' and order.error_message:
        summary += f"❌ Error: {order.error_message}\n"

    return summary


def generate_order_id() -> str:
    """Generate unique order ID"""
    return f"ord_{int(time.time())}_{uuid.uuid4().hex[:8]}"


def format_settings_summary(user_settings: Dict[str, Any]) -> str:
    """Format user settings for display with user-friendly names"""
    summary = "**🔧 Current Settings**\n\n"

    # Buy Settings - Basic
    summary += "**💰 BUY SETTINGS - Basic Trading**\n"
    summary += f"💵 {get_setting_display_name('amountOrPercent')}: {format_setting_display('amountOrPercent', user_settings.get('amountOrPercent'))}\n"
    summary += f"📊 {get_setting_display_name('maxSlippage')}: {format_setting_display('maxSlippage', user_settings.get('maxSlippage'))}\n"
    summary += f"🔄 {get_setting_display_name('retries')}: {user_settings.get('retries', 'Not set')}\n"
    summary += f"⚡ {get_setting_display_name('concurrentNodes')}: {user_settings.get('concurrentNodes', 'Not set')}\n\n"

    # Buy Settings - Gas & Fees
    summary += "**⛽ Gas & Fees**\n"
    summary += f"🛡️ {get_setting_display_name('jitoEnabled')}: {format_setting_display('jitoEnabled', user_settings.get('jitoEnabled'))}\n"
    summary += f"💸 {get_setting_display_name('jitoTip')}: {format_setting_display('jitoTip', user_settings.get('jitoTip'))}\n"
    summary += f"🔧 {get_setting_display_name('customFeeAndTip')}: {format_setting_display('customFeeAndTip', user_settings.get('customFeeAndTip'))}\n"
    summary += f"⚡ {get_setting_display_name('priorityFee')}: {format_setting_display('priorityFee', user_settings.get('priorityFee'))}\n\n"

    # Sell Settings
    summary += "**📤 SELL SETTINGS**\n"
    summary += f"🚀 {get_setting_display_name('migrateSellPercent')}: {format_setting_display('migrateSellPercent', user_settings.get('migrateSellPercent'))}\n"
    summary += f"👨‍💻 {get_setting_display_name('minDevSellPercent')}: {format_setting_display('minDevSellPercent', user_settings.get('minDevSellPercent'))}\n"
    summary += f"📊 {get_setting_display_name('devSellPercent')}: {format_setting_display('devSellPercent', user_settings.get('devSellPercent'))}\n\n"

    # Safety Filters
    summary += "**🔒 SAFETY FILTERS**\n"
    enabled_chains = user_settings.get('enabled_chains', ['solana'])
    summary += f"🌐 Active Chain: {', '.join([c.upper() for c in enabled_chains])}\n"

    return summary


def is_owner(user_id: int) -> bool:
    """Check if user is the bot owner"""
    from config import OWNER_CHAT_ID
    return user_id == OWNER_CHAT_ID


def log_trade_attempt(user_id: int, chain: str, pair: str, amount: float):
    """Log trade attempt for monitoring"""
    logger.info(f"TRADE_ATTEMPT: User {user_id} | {chain.upper()} | {pair} | Amount: {amount}")


def log_trade_result(order_id: str, success: bool, response_time_ms: float, error: Optional[str] = None):
    """Log trade execution result"""
    status = "SUCCESS" if success else "FAILED"
    log_msg = f"TRADE_RESULT: {order_id} | {status} | {response_time_ms:.2f}ms"
    if error:
        log_msg += f" | Error: {error}"
    logger.info(log_msg)


def get_setting_display_name(setting_key: str) -> str:
    """Get user-friendly display name for a setting"""
    from config import SETTING_METADATA
    metadata = SETTING_METADATA.get(setting_key, {})
    return metadata.get('display_name', setting_key.replace('_', ' ').title())


def get_setting_description(setting_key: str) -> str:
    """Get user-friendly description for a setting"""
    from config import SETTING_METADATA
    metadata = SETTING_METADATA.get(setting_key, {})
    return metadata.get('description', '')


def get_setting_format_hint(setting_key: str) -> str:
    """Get format hint for a setting"""
    from config import SETTING_METADATA
    metadata = SETTING_METADATA.get(setting_key, {})
    return metadata.get('format_hint', '')


def format_wallet_display(wallet: Dict[str, Any]) -> str:
    """Format wallet information for display"""
    name = wallet.get('name', 'Unknown Wallet')
    address = wallet.get('address', '')
    wallet_type = wallet.get('type', 'unknown').upper()

    if address:
        short_address = f"{address[:8]}...{address[-6:]}"
        return f"💳 **{name}**\n🔗 `{short_address}`\n🌐 {wallet_type} Network"
    else:
        return f"💳 **{name}**\n❌ No address available\n🌐 {wallet_type} Network"


def get_sell_setting_with_fallback(user_settings: Dict[str, Any], setting_name: str, default: Any = None) -> Any:
    """
    Centralized fallback logic for sell settings

    Strategy:
    1. Try sell-specific setting (e.g., 'sell_priorityFee')
    2. Fall back to buy setting (e.g., 'priorityFee')
    3. Fall back to provided default

    Args:
        user_settings: User settings dictionary
        setting_name: Base setting name (e.g., 'priorityFee', 'jitoTip')
        default: Default value if neither sell nor buy setting exists

    Returns:
        Setting value with proper fallback chain
    """
    # Construct sell-specific key
    sell_key = f'sell_{setting_name}'

    # Try sell-specific setting first
    if sell_key in user_settings and user_settings[sell_key] is not None:
        return user_settings[sell_key]

    # Fall back to buy setting
    if setting_name in user_settings and user_settings[setting_name] is not None:
        return user_settings[setting_name]

    # Fall back to default
    return default


# Performance monitoring
class PerformanceTimer:
    """Context manager for measuring execution time"""

    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = 0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (time.time() - self.start_time) * 1000
        logger.debug(f"PERF: {self.operation_name} took {duration:.2f}ms")

        # Log slow operations
        if duration > 100:  # More than 100ms
            logger.warning(f"SLOW_OPERATION: {self.operation_name} took {duration:.2f}ms")