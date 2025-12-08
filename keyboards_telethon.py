"""
Telegram Keyboard Layouts for Ultra-Fast Trading Bot (Telethon)
Optimized menu structure for instant trading parameter configuration
"""
from telethon import Button
from typing import Optional, List
from config import MENU_EMOJI


class TradingKeyboards:
    """All keyboard layouts for the trading bot using Telethon"""

    @staticmethod
    def main_menu():
        """Main menu with primary options"""
        return [
            [
                Button.inline(
                    "⚙️ Settings", 
                    b"menu:settings"
                ),
                Button.inline(
                    f"{MENU_EMOJI['channels']} Source Monitor", 
                    b"menu:channels"
                )
            ],
            [
                Button.url(
                    "👥 Community", 
                    "https://t.me/CopyTradersHub"
                ),
                Button.inline(
                    "📖 Help", 
                    b"menu:help"
                )
            ]
        ]

    @staticmethod
    def chain_selector_menu(user=None):
        """Chain toggle menu - Enable/disable chains"""
        # Get enabled chains from user settings
        enabled_chains = []
        if user and hasattr(user, 'settings'):
            enabled_chains = user.settings.get('enabled_chains', ['solana', 'bsc', 'ethereum', 'base', 'arbitrum', 'tron'])
        else:
            enabled_chains = ['solana', 'bsc', 'ethereum', 'base', 'arbitrum', 'tron']
        
        # Define chain order and display names
        chains = [
            ('solana', 'SOL'),
            ('bsc', 'BSC'),
            ('ethereum', 'ETH'),
            ('base', 'Base'),
            ('arbitrum', 'ARB'),
            ('tron', 'TRX')
        ]
        
        buttons = []
        for chain_id, chain_name in chains:
            is_enabled = chain_id in enabled_chains
            status_emoji = '✅' if is_enabled else '❌'
            
            buttons.append([
                Button.inline(
                    f"{status_emoji} {chain_name}",
                    f"toggle_chain:{chain_id}".encode()
                )
            ])
        
        buttons.append([
            Button.inline(
                f"{MENU_EMOJI['back']} Back to Main",
                b"menu:main"
            )
        ])
        
        return buttons

    @staticmethod
    def buy_settings_menu(chain='solana'):
        """Buy settings main categories for specific chain"""
        return [
            [
                Button.inline(
                    f"{MENU_EMOJI['basic']} Basic Trading", 
                    f"menu:buy_basic:{chain}".encode()
                )
            ],
            [
                Button.inline(
                    f"{MENU_EMOJI['gas']} Gas & Fees", 
                    f"menu:buy_gas:{chain}".encode()
                )
            ],
            [
                Button.inline(
                    f"{MENU_EMOJI['pnl']} Take Profit & Stop Loss", 
                    f"menu:buy_pnl:{chain}".encode()
                )
            ],
            [
                Button.inline(
                    f"💸 Sell Settings", 
                    f"menu:sell_settings:{chain}".encode()
                )
            ],
            [
                Button.inline(
                    f"🔒 Safety Filters ({chain.upper()})", 
                    f"menu:chain_safety:{chain}".encode()
                )
            ],
            [
                Button.inline(
                    f"{MENU_EMOJI['back']} Back to Settings", 
                    b"menu:settings"
                )
            ]
        ]

    @staticmethod
    def buy_basic_menu(chain='solana'):
        """Basic trading settings for specific chain"""
        from config import SETTING_METADATA
        return [
            [
                Button.inline(
                    f"{MENU_EMOJI['amount']} {SETTING_METADATA.get('amountOrPercent', {}).get('display_name', 'Buy Amount')}", 
                    f"setting:amountOrPercent:{chain}".encode()
                ),
                Button.inline(
                    f"{MENU_EMOJI['slippage']} {SETTING_METADATA.get('maxSlippage', {}).get('display_name', 'Max Slippage')}", 
                    f"setting:maxSlippage:{chain}".encode()
                )
            ],
            [
                Button.inline(
                    f"{MENU_EMOJI['retry']} Retry Count", 
                    f"setting:retries:{chain}".encode()
                ),
                Button.inline(
                    f"{MENU_EMOJI['nodes']} Concurrent Nodes", 
                    f"setting:concurrentNodes:{chain}".encode()
                )
            ],
            [
                Button.inline(
                    f"{MENU_EMOJI['back']} Back", 
                    f"menu:buy_settings:{chain}".encode()
                )
            ]
        ]

    @staticmethod
    def buy_gas_menu(chain='solana'):
        """Gas and fees settings for specific chain"""
        return [
            [
                Button.inline(
                    f"{MENU_EMOJI['mev']} Anti-MEV Mode", 
                    f"setting:jitoEnabled:{chain}".encode()
                ),
                Button.inline(
                    f"{MENU_EMOJI['tip']} MEV Tip", 
                    f"setting:jitoTip:{chain}".encode()
                )
            ],
            [
                Button.inline(
                    f"{MENU_EMOJI['fee']} Custom Fee Control", 
                    f"setting:customFeeAndTip:{chain}".encode()
                ),
                Button.inline(
                    f"{MENU_EMOJI['priority']} Priority Fee SOL", 
                    f"setting:priorityFee:{chain}".encode()
                )
            ],
            [
                Button.inline(
                    f"{MENU_EMOJI['gas_delta']} Extra Gas EVM", 
                    f"setting:gasFeeDelta:{chain}".encode()
                ),
                Button.inline(
                    f"{MENU_EMOJI['max_gas']} Max Gas Price", 
                    f"setting:maxFeePerGas:{chain}".encode()
                )
            ],
            [
                Button.inline(
                    f"{MENU_EMOJI['back']} Back", 
                    f"menu:buy_settings:{chain}".encode()
                )
            ]
        ]

    @staticmethod
    def buy_pnl_menu(chain='solana'):
        """Take Profit & Stop Loss settings for specific chain"""
        return [
            [
                Button.inline(
                    f"{MENU_EMOJI['tp']} Take Profit %", 
                    f"setting:stopEarnPercent:{chain}".encode()
                ),
                Button.inline(
                    f"{MENU_EMOJI['sl']} Stop Loss %", 
                    f"setting:stopLossPercent:{chain}".encode()
                )
            ],
            [
                Button.inline(
                    f"{MENU_EMOJI['tp_group']} Take Profit Groups", 
                    f"setting:stopEarnGroup:{chain}".encode()
                ),
                Button.inline(
                    f"{MENU_EMOJI['sl_group']} Stop Loss Groups", 
                    f"setting:stopLossGroup:{chain}".encode()
                )
            ],
            [
                Button.inline(
                    f"{MENU_EMOJI['trailing']} Trailing Stop", 
                    f"setting:trailingStopGroup:{chain}".encode()
                ),
                Button.inline(
                    f"{MENU_EMOJI['expiry']} Order Expiry", 
                    f"setting:pnlOrderExpireDelta:{chain}".encode()
                )
            ],
            [
                Button.inline(
                    f"{MENU_EMOJI['auto_exec']} Auto Execute", 
                    f"setting:pnlOrderExpireExecute:{chain}".encode()
                ),
                Button.inline(
                    f"{MENU_EMOJI['anti_spike']} Anti-Spike", 
                    f"setting:pnlOrderUseMidPrice:{chain}".encode()
                )
            ],
            [
                Button.inline(
                    f"{MENU_EMOJI['custom_pnl']} Custom PnL Config", 
                    f"setting:pnlCustomConfigEnabled:{chain}".encode()
                ),
                Button.inline(
                    f"{MENU_EMOJI['pnl_config']} PnL Settings", 
                    f"setting:pnlCustomConfig:{chain}".encode()
                )
            ],
            [
                Button.inline(
                    f"{MENU_EMOJI['back']} Back", 
                    f"menu:buy_settings:{chain}".encode()
                )
            ]
        ]

    @staticmethod
    def sell_gas_menu(chain='solana'):
        """Sell gas and fees settings for specific chain"""
        return [
            [
                Button.inline(
                    f"{MENU_EMOJI['priority']} Sell Priority Fee", 
                    f"setting:sell_priorityFee:{chain}".encode()
                ),
                Button.inline(
                    f"{MENU_EMOJI['tip']} Sell Jito Tip", 
                    f"setting:sell_jitoTip:{chain}".encode()
                )
            ],
            [
                Button.inline(
                    f"{MENU_EMOJI['gas_delta']} Sell Gas Delta", 
                    f"setting:sell_gasFeeDelta:{chain}".encode()
                ),
                Button.inline(
                    f"{MENU_EMOJI['max_gas']} Sell Max Gas", 
                    f"setting:sell_maxFeePerGas:{chain}".encode()
                )
            ],
            [
                Button.inline(
                    f"{MENU_EMOJI['slippage']} Sell Slippage", 
                    f"setting:sell_maxSlippage:{chain}".encode()
                ),
                Button.inline(
                    f"{MENU_EMOJI['fee']} Sell Custom Fee", 
                    f"setting:sell_customFeeAndTip:{chain}".encode()
                )
            ],
            [
                Button.inline(
                    f"{MENU_EMOJI['back']} Back", 
                    f"menu:sell_settings:{chain}".encode()
                )
            ]
        ]

    @staticmethod
    def chain_safety_menu(chain='solana', user=None):
        """Chain-specific safety filters menu with current values displayed"""
        from models import storage
        
        chain_name = chain.upper()
        
        # Get chain-specific settings
        if user:
            chain_settings = user.get_chain_settings(chain)
        else:
            from config import DEFAULT_SETTINGS
            chain_settings = DEFAULT_SETTINGS.get(chain, {})
        
        # Get current values
        mcap_min = chain_settings.get('market_cap_min')
        holders_min = chain_settings.get('holders_min')
        snipers_max = chain_settings.get('snipers_max')
        check_freeze = chain_settings.get('check_freeze_authority', False)
        check_mint = chain_settings.get('check_mint_authority', False)
        top10_max = chain_settings.get('top10_holder_max')
        vol_1m = chain_settings.get('volume_ratio_1m')
        vol_5m = chain_settings.get('volume_ratio_5m')
        vol_1h = chain_settings.get('volume_ratio_1h')
        vol_6h = chain_settings.get('volume_ratio_6h')
        vol_24h = chain_settings.get('volume_ratio_24h')
        
        # Format display values
        mcap_display = f"${mcap_min:,.0f}" if mcap_min else "None"
        holders_display = str(holders_min) if holders_min else "None"
        snipers_display = str(snipers_max) if snipers_max else "None"
        freeze_display = "✅ Reject" if check_freeze else "❌ Allow"
        mint_display = "✅ Reject" if check_mint else "❌ Allow"
        top10_display = f"{top10_max * 100:.0f}%" if top10_max else "None"
        vol_1m_display = f"{vol_1m:.0f}%" if vol_1m else "Disabled"
        vol_5m_display = f"{vol_5m:.0f}%" if vol_5m else "Disabled"
        vol_1h_display = f"{vol_1h:.0f}%" if vol_1h else "Disabled"
        vol_6h_display = f"{vol_6h:.0f}%" if vol_6h else "Disabled"
        vol_24h_display = f"{vol_24h:.0f}%" if vol_24h else "Disabled"
        
        return [
            [
                Button.inline(
                    f"💰 Market Cap ({chain_name}): {mcap_display}", 
                    f"setting:market_cap_min:{chain}".encode()
                )
            ],
            [
                Button.inline(
                    f"👥 Min Holders ({chain_name}): {holders_display}", 
                    f"setting:holders_min:{chain}".encode()
                )
            ],
            [
                Button.inline(
                    f"🎯 Max Snipers ({chain_name}): {snipers_display}", 
                    f"setting:snipers_max:{chain}".encode()
                )
            ],
            [
                Button.inline(
                    f"🔒 Freeze Authority ({chain_name}): {freeze_display}", 
                    f"setting:check_freeze_authority:{chain}".encode()
                )
            ],
            [
                Button.inline(
                    f"🏭 Mint Authority ({chain_name}): {mint_display}", 
                    f"setting:check_mint_authority:{chain}".encode()
                )
            ],
            [
                Button.inline(
                    f"📊 Top 10 Holders ({chain_name}): {top10_display}", 
                    f"setting:top10_holder_max:{chain}".encode()
                )
            ],
            [
                Button.inline(
                    f"📊 Volume Ratios ({chain_name})", 
                    f"menu:volume_ratios:{chain}".encode()
                )
            ],
            [
                Button.inline(
                    f"{MENU_EMOJI['back']} Back to Settings", 
                    b"menu:settings"
                )
            ]
        ]
    
    @staticmethod
    def volume_ratios_menu(chain='solana', user=None):
        """Volume ratio filters submenu"""
        chain_name = chain.upper()
        
        # Get chain-specific settings
        if user:
            chain_settings = user.get_chain_settings(chain)
        else:
            from config import DEFAULT_SETTINGS
            chain_settings = DEFAULT_SETTINGS.get(chain, {})
        
        # Get volume ratio values
        vol_1m = chain_settings.get('volume_ratio_1m')
        vol_5m = chain_settings.get('volume_ratio_5m')
        vol_1h = chain_settings.get('volume_ratio_1h')
        vol_6h = chain_settings.get('volume_ratio_6h')
        vol_24h = chain_settings.get('volume_ratio_24h')
        
        # Format display values
        vol_1m_display = f"{vol_1m:.0f}%" if vol_1m else "Disabled"
        vol_5m_display = f"{vol_5m:.0f}%" if vol_5m else "Disabled"
        vol_1h_display = f"{vol_1h:.0f}%" if vol_1h else "Disabled"
        vol_6h_display = f"{vol_6h:.0f}%" if vol_6h else "Disabled"
        vol_24h_display = f"{vol_24h:.0f}%" if vol_24h else "Disabled"
        
        return [
            [
                Button.inline(
                    f"1m: {vol_1m_display}", 
                    f"setting:volume_ratio_1m:{chain}".encode()
                ),
                Button.inline(
                    f"5m: {vol_5m_display}", 
                    f"setting:volume_ratio_5m:{chain}".encode()
                )
            ],
            [
                Button.inline(
                    f"1h: {vol_1h_display}", 
                    f"setting:volume_ratio_1h:{chain}".encode()
                ),
                Button.inline(
                    f"6h: {vol_6h_display}", 
                    f"setting:volume_ratio_6h:{chain}".encode()
                )
            ],
            [
                Button.inline(
                    f"24h: {vol_24h_display}", 
                    f"setting:volume_ratio_24h:{chain}".encode()
                )
            ],
            [
                Button.inline(
                    f"{MENU_EMOJI['back']} Back to Safety", 
                    f"menu:chain_safety:{chain}".encode()
                )
            ]
        ]

    @staticmethod
    def sell_settings_menu(chain='solana'):
        """Sell settings menu for specific chain"""
        return [
            [
                Button.inline(
                    f"{MENU_EMOJI['amount']} Sell Amount %", 
                    f"setting:sell_amountOrPercent:{chain}".encode()
                )
            ],
            [
                Button.inline(
                    f"{MENU_EMOJI['migrate']} Pump Migration %", 
                    f"setting:migrateSellPercent:{chain}".encode()
                )
            ],
            [
                Button.inline(
                    f"{MENU_EMOJI['dev_trigger']} Dev Sell Trigger %", 
                    f"setting:minDevSellPercent:{chain}".encode()
                ),
                Button.inline(
                    f"{MENU_EMOJI['dev_sell']} Dev Sell Amount %", 
                    f"setting:devSellPercent:{chain}".encode()
                )
            ],
            [
                Button.inline(
                    f"{MENU_EMOJI['gas']} Sell Gas & Fees", 
                    f"menu:sell_gas:{chain}".encode()
                )
            ],
            [
                Button.inline(
                    f"{MENU_EMOJI['back']} Back", 
                    f"menu:buy_settings:{chain}".encode()
                )
            ]
        ]

    @staticmethod
    def boolean_setting(setting_name: str, current_value: bool, back_menu: str, chain: str = 'solana'):
        """Boolean toggle keyboard"""
        return [
            [
                Button.inline(
                    f"✅ Enabled" if current_value else "❌ Disabled",
                    f"toggle:{setting_name}:{not current_value}:{chain}".encode()
                )
            ],
            [
                Button.inline(
                    f"{MENU_EMOJI['back']} Back", 
                    f"menu:{back_menu}".encode()
                )
            ]
        ]

    @staticmethod
    def numeric_setting(setting_name: str, back_menu: str, suggestions: Optional[list] = None, chain: str = 'solana'):
        """Numeric input keyboard with common values"""
        buttons = []
        
        if suggestions:
            # Add suggestion buttons in rows of 2
            for i in range(0, len(suggestions), 2):
                row = []
                for j in range(2):
                    if i + j < len(suggestions):
                        value = suggestions[i + j]
                        row.append(Button.inline(
                            str(value),
                            f"set:{setting_name}:{value}:{chain}".encode()
                        ))
                buttons.append(row)
        
        # Add custom input and back buttons
        buttons.extend([
            [
                Button.inline(
                    "✏️ Custom Input", 
                    f"input:{setting_name}:{chain}".encode()
                )
            ],
            [
                Button.inline(
                    f"{MENU_EMOJI['back']} Back", 
                    f"menu:{back_menu}".encode()
                )
            ]
        ])
        
        return buttons

    @staticmethod
    def wallet_selection(wallets: list):
        """Wallet selection keyboard"""
        buttons = []
        
        for wallet in wallets[:10]:  # Limit to 10 wallets
            name = wallet.get('name', 'Unknown')
            address = wallet.get('address', '')
            short_address = f"{address[:6]}...{address[-4:]}" if address else "No Address"
            
            buttons.append([
                Button.inline(
                    f"💳 {name} ({short_address})",
                    f"wallet:{wallet['id']}".encode()
                )
            ])
        
        buttons.append([
            Button.inline(
                "➕ Import New Wallet",
                b"action:import_wallet"
            )
        ])
        
        buttons.append([
            Button.inline(
                f"{MENU_EMOJI['back']} Back",
                b"menu:main"
            )
        ])
        
        return buttons

    @staticmethod
    def orders_list(orders: list):
        """Recent orders list"""
        buttons = []
        
        for order in orders[:10]:  # Limit to 10 recent orders
            status_emoji = {
                'pending': '⏳',
                'completed': '✅',
                'failed': '❌'
            }.get(order.status, '❓')
            
            order_text = f"{status_emoji} {order.order_type.upper()} {order.chain.upper()}"
            if len(order.pair) > 8:
                order_text += f" {order.pair[:8]}..."
            else:
                order_text += f" {order.pair}"
            
            buttons.append([
                Button.inline(
                    order_text,
                    f"order:{order.order_id}".encode()
                )
            ])
        
        if not orders:
            buttons.append([
                Button.inline(
                    "📝 No orders yet",
                    b"noop"
                )
            ])
        
        buttons.append([
            Button.inline(
                f"{MENU_EMOJI['back']} Back",
                b"menu:main"
            )
        ])
        
        return buttons

    @staticmethod
    def confirmation_keyboard(action: str, data: str = ""):
        """Confirmation dialog"""
        return [
            [
                Button.inline(
                    "✅ Yes, Confirm",
                    f"confirm:{action}:{data}".encode()
                ),
                Button.inline(
                    "❌ Cancel",
                    b"menu:main"
                )
            ]
        ]

    # Channel Management Keyboards
    @staticmethod
    def channels_menu(channels: list):
        """Channel management main menu"""
        buttons = []
        
        # Add source button - directly triggers /addsource
        buttons.append([
            Button.inline(
                f"{MENU_EMOJI['add_channel']} Add Channel/Group",
                b"action:trigger_addsource"
            )
        ])
        
        # List channels (max 8)
        for channel in channels[:8]:
            status_emoji = MENU_EMOJI['active'] if channel.is_active else MENU_EMOJI['inactive']
            channel_name = channel.channel_username or channel.channel_title
            if len(channel_name) > 20:
                channel_name = channel_name[:17] + "..."
            
            buttons.append([
                Button.inline(
                    f"{status_emoji} {channel_name}",
                    f"channel:{channel.channel_id}".encode()
                )
            ])
        
        if len(channels) > 8:
            buttons.append([
                Button.inline(
                    "📄 View All Channels",
                    b"action:all_channels"
                )
            ])
        
        if not channels:
            buttons.append([
                Button.inline(
                    "📄 No channels configured",
                    b"noop"
                )
            ])
        
        buttons.append([
            Button.inline(
                f"{MENU_EMOJI['back']} Back to Main",
                b"menu:main"
            )
        ])
        
        return buttons

    @staticmethod
    def channel_settings(channel):
        """Channel-specific settings menu"""
        status_text = "Disable" if channel.is_active else "Enable"
        status_emoji = MENU_EMOJI['inactive'] if channel.is_active else MENU_EMOJI['active']
        
        filter_text = {
            'all': "All Messages",
            'admins': "Admin Only", 
            'users': "Specific Users"
        }.get(channel.filter_mode.value, "All Messages")
        
        buttons = [
            [
                Button.inline(
                    f"{status_emoji} {status_text} Channel",
                    f"toggle_channel:{channel.channel_id}".encode()
                )
            ],
            [
                Button.inline(
                    f"{MENU_EMOJI['filter_mode']} Filter: {filter_text}",
                    f"channel_filter:{channel.channel_id}".encode()
                )
            ]
        ]
        
        if channel.filter_mode.value == 'users':
            user_count = len(channel.allowed_user_ids)
            buttons.append([
                Button.inline(
                    f"{MENU_EMOJI['specific_users']} Manage Users ({user_count})",
                    f"channel_users:{channel.channel_id}".encode()
                )
            ])
        
        buttons.extend([
            [
                Button.inline(
                    f"{MENU_EMOJI['remove_channel']} Remove Channel",
                    f"remove_channel:{channel.channel_id}".encode()
                )
            ],
            [
                Button.inline(
                    f"{MENU_EMOJI['back']} Back to Channels",
                    b"menu:channels"
                )
            ]
        ])
        
        return buttons

    @staticmethod
    def filter_mode_selection(channel_id: int):
        """Filter mode selection for channel"""
        return [
            [
                Button.inline(
                    f"{MENU_EMOJI['all_msgs']} All Messages",
                    f"set_filter:{channel_id}:all".encode()
                )
            ],
            [
                Button.inline(
                    f"{MENU_EMOJI['admin_only']} Admin Only",
                    f"set_filter:{channel_id}:admins".encode()
                )
            ],
            [
                Button.inline(
                    f"{MENU_EMOJI['specific_users']} Specific Users",
                    f"set_filter:{channel_id}:users".encode()
                )
            ],
            [
                Button.inline(
                    f"{MENU_EMOJI['back']} Back",
                    f"channel:{channel_id}".encode()
                )
            ]
        ]

    @staticmethod
    def channel_amount_setting(channel_id: int):
        """Channel-specific buy amount setting"""
        suggestions = [0.01, 0.05, 0.1, 0.2, 0.5, 1.0]
        buttons = []
        
        # Add suggestion buttons in rows of 3
        for i in range(0, len(suggestions), 3):
            row = []
            for j in range(3):
                if i + j < len(suggestions):
                    value = suggestions[i + j]
                    row.append(Button.inline(
                        f"{value} SOL",
                        f"set_channel_amount:{channel_id}:{value}".encode()
                    ))
            buttons.append(row)
        
        buttons.extend([
            [
                Button.inline(
                    "✏️ Custom Amount",
                    f"custom_channel_amount:{channel_id}".encode()
                )
            ],
            [
                Button.inline(
                    "🔄 Use Default",
                    f"default_channel_amount:{channel_id}".encode()
                )
            ],
            [
                Button.inline(
                    f"{MENU_EMOJI['back']} Back",
                    f"channel:{channel_id}".encode()
                )
            ]
        ])
        
        return buttons

    @staticmethod
    def channel_users_management(channel_id: int, allowed_users: list):
        """User management keyboard for channel"""
        buttons = []
        
        # Show remove buttons for existing users (up to 5)
        for user_id in allowed_users[:5]:
            buttons.append([
                Button.inline(
                    f"❌ Remove {user_id}",
                    f"remove_user:{channel_id}:{user_id}".encode()
                )
            ])
        
        if len(allowed_users) > 5:
            buttons.append([
                Button.inline(
                    f"📋 {len(allowed_users) - 5} more users...",
                    b"noop"
                )
            ])
        
        buttons.extend([
            [
                Button.inline(
                    "➕ Add User",
                    f"add_user_prompt:{channel_id}".encode()
                )
            ],
            [
                Button.inline(
                    f"{MENU_EMOJI['back']} Back to Channel",
                    f"channel:{channel_id}".encode()
                )
            ]
        ])
        
        return buttons

    


# Predefined setting suggestions for quick selection
# PERCENTAGES: Use 0-100 format (user-friendly), system converts to 0-1.0
SETTING_SUGGESTIONS = {
    'amountOrPercent': [0.01, 0.05, 0.1, 0.2, 0.5, 1.0],  # SOL amounts (no conversion)
    'maxSlippage': [5, 10, 15, 20, 30, 50],  # User sees 5%, 10%, 15%, etc.
    'retries': [1, 2, 3, 5],
    'concurrentNodes': [1, 2, 3],
    'jitoTip': [0.001, 0.005, 0.01, 0.02],  # SOL amounts (no conversion)
    'gasFeeDelta': [2, 5, 10, 15, 20],
    'maxFeePerGas': [50, 100, 150, 200, 300],
    'stopEarnPercent': [10, 20, 50, 100, 200, 500],  # User sees 10%, 20%, 50%, etc.
    'stopLossPercent': [10, 20, 30, 50],  # User sees 10%, 20%, 30%, 50%
    'sell_amountOrPercent': [25, 50, 75, 100],  # User sees 25%, 50%, 75%, 100%
    'migrateSellPercent': [0, 10, 20, 50, 100],  # User sees 0%, 10%, 20%, etc.
    'minDevSellPercent': [10, 20, 30, 50, 80],  # User sees 10%, 20%, 30%, etc.
    'devSellPercent': [50, 70, 100],  # User sees 50%, 70%, 100%
    # Sell-specific gas & fee suggestions
    'sell_priorityFee': [0.0001, 0.0005, 0.001, 0.002],  # SOL amounts (no conversion)
    'sell_jitoTip': [0.001, 0.002, 0.005, 0.01, 0.02],  # SOL amounts (no conversion)
    'sell_gasFeeDelta': [5, 10, 15, 20, 30],
    'sell_maxFeePerGas': [100, 150, 200, 250, 300],
    'sell_maxSlippage': [15, 20, 25, 30, 50],  # User sees 15%, 20%, 25%, etc.
    # Safety filters
    'top10_holder_max': [60, 70, 80, 90],  # User sees 60%, 70%, 80%, 90%
    'lp_burn_min': [80, 90, 95, 100],  # User sees 80%, 90%, 95%, 100%
}
