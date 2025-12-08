"""
Token Safety Validator
Validates tokens against user-configured safety filters before executing trades
"""
import logging
from typing import Dict, Any, Tuple, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of token validation"""
    is_safe: bool
    rejection_reason: Optional[str] = None
    pair_data: Optional[Dict[str, Any]] = None


class TokenValidator:
    """Validates tokens against comprehensive safety filters"""

    def __init__(self):
        pass

    def validate_token(
        self,
        pair_info_response: Dict[str, Any],
        detected_chain: str,
        safety_settings: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate token against all configured safety filters

        Args:
            pair_info_response: Response from /kline/pair_info API
            detected_chain: Chain detected from address (solana, bsc, ethereum, base, tron)
            safety_settings: User's full settings dict (contains per-chain settings)

        Returns:
            ValidationResult with is_safe flag and rejection_reason if applicable
        """

        # Check if API call failed
        if pair_info_response.get('err', True):
            error_msg = pair_info_response.get('message', 'Unknown error')
            return ValidationResult(
                is_safe=False,
                rejection_reason=f"Failed to fetch pair info: {error_msg}"
            )

        # Extract pair data
        res = pair_info_response.get('res', [])
        if not res or len(res) == 0:
            return ValidationResult(
                is_safe=False,
                rejection_reason="No pair data returned from API"
            )

        pair_data = res[0]

        # Log pair data for debugging
        logger.info(f"🔍🔍🔍 TOKEN VALIDATOR: Starting validation")
        logger.info(f"   ├─ Token Name: {pair_data.get('name', 'Unknown')}")
        logger.info(f"   ├─ Token Symbol: {pair_data.get('symbol', 'Unknown')}")
        logger.info(f"   ├─ Chain: {detected_chain}")
        logger.info(f"   ├─ Market Cap: ${pair_data.get('marketCap', 0):,.2f}")
        logger.info(f"   ├─ Holders: {pair_data.get('holders', 0)}")
        logger.info(f"   └─ Snipers: {pair_data.get('snipersCount', 0)}")
        logger.debug(f"📋 Full pair data: {pair_data}")

        # 1. CHAIN VALIDATION (check global enabled_chains)
        logger.info(f"✅ VALIDATION STEP 1: Chain Enablement Check")
        enabled_chains = safety_settings.get('enabled_chains', ['solana'])
        logger.info(f"   ├─ Detected chain: {detected_chain}")
        logger.info(f"   ├─ Enabled chains: {enabled_chains}")
        
        if detected_chain not in enabled_chains:
            logger.warning(f"   └─ ❌ REJECTED: Chain not enabled")
            return ValidationResult(
                is_safe=False,
                rejection_reason=f"Chain '{detected_chain}' not enabled. Enabled chains: {', '.join(enabled_chains)}",
                pair_data=pair_data
            )
        logger.info(f"   └─ ✅ PASSED: Chain is enabled")

        # Get chain-specific safety settings
        chain_settings = safety_settings.get(detected_chain, {})
        logger.info(f"🔒 Retrieved {detected_chain.upper()} chain-specific settings")
        logger.debug(f"   Chain settings: {chain_settings}")

        # 2. MARKET CAP VALIDATION (per-chain)
        logger.info(f"✅ VALIDATION STEP 2: Market Cap Check")
        market_cap = pair_data.get('marketCap', 0)
        market_cap_min = chain_settings.get('market_cap_min')
        market_cap_max = chain_settings.get('market_cap_max')
        
        logger.info(f"   ├─ Current market cap: ${market_cap:,.2f}")
        logger.info(f"   ├─ Min required: ${market_cap_min:,.2f}" if market_cap_min else "   ├─ Min required: None")
        logger.info(f"   └─ Max allowed: ${market_cap_max:,.2f}" if market_cap_max else "   └─ Max allowed: None")

        if market_cap_min is not None and market_cap < market_cap_min:
            logger.warning(f"   ❌ REJECTED: Market cap below minimum")
            return ValidationResult(
                is_safe=False,
                rejection_reason=f"Market cap ${market_cap:,.2f} below minimum ${market_cap_min:,.2f}",
                pair_data=pair_data
            )

        if market_cap_max is not None and market_cap > market_cap_max:
            logger.warning(f"   ❌ REJECTED: Market cap above maximum")
            return ValidationResult(
                is_safe=False,
                rejection_reason=f"Market cap ${market_cap:,.2f} above maximum ${market_cap_max:,.2f}",
                pair_data=pair_data
            )
        
        logger.info(f"   ✅ PASSED: Market cap within range")

        # 3. HOLDERS VALIDATION (per-chain)
        logger.info(f"✅ VALIDATION STEP 3: Holders Check")
        holders = pair_data.get('holders', 0)
        holders_min = chain_settings.get('holders_min')
        
        logger.info(f"   ├─ Current holders: {holders}")
        logger.info(f"   └─ Min required: {holders_min}" if holders_min else "   └─ Min required: None")

        if holders_min is not None and holders < holders_min:
            logger.warning(f"   ❌ REJECTED: Holders below minimum")
            return ValidationResult(
                is_safe=False,
                rejection_reason=f"Holders ({holders}) below {detected_chain.upper()} minimum ({holders_min})",
                pair_data=pair_data
            )
        
        logger.info(f"   ✅ PASSED: Holders meet requirement")

        # 4. SNIPERS COUNT VALIDATION (per-chain)
        snipers_count = pair_data.get('snipersCount', 0)
        snipers_max = chain_settings.get('snipers_max')

        if snipers_max is not None and snipers_count > snipers_max:
            return ValidationResult(
                is_safe=False,
                rejection_reason=f"Snipers count ({snipers_count}) above {detected_chain.upper()} maximum ({snipers_max})",
                pair_data=pair_data
            )

        # 5. LAUNCH MIGRATION VALIDATION (per-chain)
        require_launch_migration = chain_settings.get('require_launch_migration', False)
        is_launch_migration = pair_data.get('isLaunchMigration', False)

        if require_launch_migration and not is_launch_migration:
            return ValidationResult(
                is_safe=False,
                rejection_reason="Token not officially launched by platform (Pump, etc.)",
                pair_data=pair_data
            )

        # 6. VOLUME RATIO VALIDATION (per-chain)
        # If sell volume is X% or more higher than buy volume, reject
        volume_ratios = {
            '1m': ('buyVolume1m', 'sellVolume1m', 'volume_ratio_1m'),
            '5m': ('buyVolume5m', 'sellVolume5m', 'volume_ratio_5m'),
            '1h': ('buyVolume1h', 'sellVolume1h', 'volume_ratio_1h'),
            '6h': ('buyVolume6h', 'sellVolume6h', 'volume_ratio_6h'),
            '24h': ('buyVolume24h', 'sellVolume24h', 'volume_ratio_24h')
        }

        for timeframe, (buy_key, sell_key, setting_key) in volume_ratios.items():
            threshold = chain_settings.get(setting_key)
            if threshold is None:
                continue

            buy_volume = pair_data.get(buy_key, 0)
            sell_volume = pair_data.get(sell_key, 0)

            # Skip if no volume data at all
            if buy_volume == 0 and sell_volume == 0:
                continue

            # CRITICAL: If there's sell volume but zero buy volume, this is a dead/unsafe token
            # Reject immediately as this indicates only sellers, no buyers
            if buy_volume <= 0 and sell_volume > 0:
                return ValidationResult(
                    is_safe=False,
                    rejection_reason=f"Dead token detected: Sell volume {timeframe} exists ({sell_volume:.2f}) but zero buy volume - 100% selling pressure",
                    pair_data=pair_data
                )

            # Calculate sell percentage relative to buy volume
            # If sell is 60% or more higher than buy, that means sell_volume / buy_volume >= 1.6
            if buy_volume > 0:
                sell_to_buy_ratio = sell_volume / buy_volume
                # If ratio >= threshold (e.g., 1.6 for 60% threshold), reject
                if sell_to_buy_ratio >= (1 + threshold / 100):
                    return ValidationResult(
                        is_safe=False,
                        rejection_reason=f"Sell volume {timeframe} is {((sell_to_buy_ratio - 1) * 100):.1f}% higher than buy volume (threshold: {threshold}%)",
                        pair_data=pair_data
                    )

        # 7. SECURITY CHECKS (per-chain)
        safety_info = pair_data.get('safetyInfo', {})

        # Freeze Authority Check (per-chain)
        check_freeze_authority = chain_settings.get('check_freeze_authority', False)
        freeze_authority = safety_info.get('freezeAuthority', False)
        can_frozen = safety_info.get('canFrozen', False)

        if check_freeze_authority:
            if freeze_authority or can_frozen:
                return ValidationResult(
                    is_safe=False,
                    rejection_reason=f"{detected_chain.upper()} safety: Token has freeze authority enabled",
                    pair_data=pair_data
                )

        # Mint Authority Check (per-chain)
        check_mint_authority = chain_settings.get('check_mint_authority', False)
        mint_authority = safety_info.get('mintAuthority', False)
        can_mint = safety_info.get('canMint', False)

        if check_mint_authority:
            if mint_authority or can_mint:
                return ValidationResult(
                    is_safe=False,
                    rejection_reason=f"{detected_chain.upper()} safety: Token has mint authority enabled",
                    pair_data=pair_data
                )

        # Top 10 Holder Rate Check (per-chain)
        top10_holder_max = chain_settings.get('top10_holder_max')
        top10_holder_rate = safety_info.get('top10HolderRate', 0)

        if top10_holder_max is not None and top10_holder_rate > top10_holder_max:
            return ValidationResult(
                is_safe=False,
                rejection_reason=f"Top 10 holders own {top10_holder_rate * 100:.1f}% ({detected_chain.upper()} max: {top10_holder_max * 100:.1f}%)",
                pair_data=pair_data
            )

        # LP Burn/Lock Percentage Check (per-chain)
        lp_burn_min = chain_settings.get('lp_burn_min')
        burned_or_locked_lp = safety_info.get('burnedOrLockedLpPercent')

        if lp_burn_min is not None:
            if burned_or_locked_lp is None:
                return ValidationResult(
                    is_safe=False,
                    rejection_reason="LP burn/lock percentage not available",
                    pair_data=pair_data
                )

            if burned_or_locked_lp < lp_burn_min:
                return ValidationResult(
                    is_safe=False,
                    rejection_reason=f"LP burn/lock {burned_or_locked_lp * 100:.1f}% below {detected_chain.upper()} minimum {lp_burn_min * 100:.1f}%",
                    pair_data=pair_data
                )

        # All checks passed!
        logger.info(f"✅✅✅ ALL VALIDATION CHECKS PASSED")
        logger.info(f"   ├─ Token: {pair_data.get('name', 'Unknown')} ({pair_data.get('symbol', 'Unknown')})")
        logger.info(f"   ├─ Chain: {detected_chain.upper()}")
        logger.info(f"   └─ Token is SAFE to trade")
        
        return ValidationResult(
            is_safe=True,
            rejection_reason=None,
            pair_data=pair_data
        )


# Global validator instance
validator = TokenValidator()