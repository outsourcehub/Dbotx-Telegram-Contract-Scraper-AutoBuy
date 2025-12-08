"""
Telegram Keyboard Layouts for Ultra-Fast Trading Bot
Optimized menu structure for instant trading parameter configuration
"""
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import Optional
from config import MENU_EMOJI


class TradingKeyboards:
    """All keyboard layouts for the trading bot"""

    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        """Main menu with primary options"""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    f"{MENU_EMOJI['buy']} BUY SETTINGS",
                    callback_data="menu:buy_settings"
                ),
                InlineKeyboardButton(
                    f"{MENU_EMOJI['sell']} SELL SETTINGS",
                    callback_data="menu:sell_settings"
                )
            ],
            [
                InlineKeyboardButton(
                    "📊 My Orders",
                    callback_data="menu:orders"
                ),
                InlineKeyboardButton(
                    "👥 Community",
                    url="https://t.me/CopyTradersHub"
                )
            ],
            [
                InlineKeyboardButton(
                    f"{MENU_EMOJI['channels']} Channel Monitor",
                    callback_data="menu:channels"
                ),
                InlineKeyboardButton(
                    "📖 Help",
                    callback_data="menu:help"
                )
            ],
            [
                InlineKeyboardButton(
                    "🔄 Reset Settings",
                    callback_data="action:reset_settings"
                )
            ]
        ])

    @staticmethod
    def buy_settings_menu() -> InlineKeyboardMarkup:
        """Buy settings main categories"""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    f"{MENU_EMOJI['basic']} Basic Trading",
                    callback_data="menu:buy_basic"
                )
            ],
            [
                InlineKeyboardButton(
                    f"{MENU_EMOJI['gas']} Gas & Fees",
                    callback_data="menu:buy_gas"
                )
            ],
            [
                InlineKeyboardButton(
                    f"{MENU_EMOJI['pnl']} Take Profit & Stop Loss",
                    callback_data="menu:buy_pnl"
                )
            ],
            [
                InlineKeyboardButton(
                    f"{MENU_EMOJI['back']} Back to Main",
                    callback_data="menu:main"
                )
            ]
        ])

    @staticmethod
    def buy_basic_menu() -> InlineKeyboardMarkup:
        """Basic trading settings"""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    f"{MENU_EMOJI['amount']} Buy Amount",
                    callback_data="setting:amountOrPercent"
                ),
                InlineKeyboardButton(
                    f"{MENU_EMOJI['slippage']} Max Slippage",
                    callback_data="setting:maxSlippage"
                )
            ],
            [
                InlineKeyboardButton(
                    f"{MENU_EMOJI['retry']} Retry Count",
                    callback_data="setting:retries"
                ),
                InlineKeyboardButton(
                    f"{MENU_EMOJI['nodes']} Concurrent Nodes",
                    callback_data="setting:concurrentNodes"
                )
            ],
            [
                InlineKeyboardButton(
                    f"{MENU_EMOJI['back']} Back",
                    callback_data="menu:buy_settings"
                )
            ]
        ])

    @staticmethod
    def buy_gas_menu() -> InlineKeyboardMarkup:
        """Gas and fees settings"""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    f"{MENU_EMOJI['mev']} Anti-MEV Mode",
                    callback_data="setting:jitoEnabled"
                ),
                InlineKeyboardButton(
                    f"{MENU_EMOJI['tip']} MEV Tip",
                    callback_data="setting:jitoTip"
                )
            ],
            [
                InlineKeyboardButton(
                    f"{MENU_EMOJI['fee']} Custom Fee Control",
                    callback_data="setting:customFeeAndTip"
                ),
                InlineKeyboardButton(
                    f"{MENU_EMOJI['priority']} Priority Fee SOL",
                    callback_data="setting:priorityFee"
                )
            ],
            [
                InlineKeyboardButton(
                    f"{MENU_EMOJI['gas_delta']} Extra Gas EVM",
                    callback_data="setting:gasFeeDelta"
                ),
                InlineKeyboardButton(
                    f"{MENU_EMOJI['max_gas']} Max Gas Price",
                    callback_data="setting:maxFeePerGas"
                )
            ],
            [
                InlineKeyboardButton(
                    f"{MENU_EMOJI['back']} Back",
                    callback_data="menu:buy_settings"
                )
            ]
        ])

    @staticmethod
    def buy_pnl_menu() -> InlineKeyboardMarkup:
        """Take Profit & Stop Loss settings"""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    f"{MENU_EMOJI['tp']} Take Profit %",
                    callback_data="setting:stopEarnPercent"
                ),
                InlineKeyboardButton(
                    f"{MENU_EMOJI['sl']} Stop Loss %",
                    callback_data="setting:stopLossPercent"
                )
            ],
            [
                InlineKeyboardButton(
                    f"{MENU_EMOJI['tp_group']} Take Profit Groups",
                    callback_data="setting:stopEarnGroup"
                ),
                InlineKeyboardButton(
                    f"{MENU_EMOJI['sl_group']} Stop Loss Groups",
                    callback_data="setting:stopLossGroup"
                )
            ],
            [
                InlineKeyboardButton(
                    f"{MENU_EMOJI['trailing']} Trailing Stop",
                    callback_data="setting:trailingStopGroup"
                ),
                InlineKeyboardButton(
                    f"{MENU_EMOJI['expiry']} Order Expiry",
                    callback_data="setting:pnlOrderExpireDelta"
                )
            ],
            [
                InlineKeyboardButton(
                    f"{MENU_EMOJI['auto_exec']} Auto Execute",
                    callback_data="setting:pnlOrderExpireExecute"
                ),
                InlineKeyboardButton(
                    f"{MENU_EMOJI['anti_spike']} Anti-Spike",
                    callback_data="setting:pnlOrderUseMidPrice"
                )
            ],
            [
                InlineKeyboardButton(
                    f"{MENU_EMOJI['custom_pnl']} Custom PnL Config",
                    callback_data="setting:pnlCustomConfigEnabled"
                ),
                InlineKeyboardButton(
                    f"{MENU_EMOJI['pnl_config']} PnL Settings",
                    callback_data="setting:pnlCustomConfig"
                )
            ],
            [
                InlineKeyboardButton(
                    f"{MENU_EMOJI['back']} Back",
                    callback_data="menu:buy_settings"
                )
            ]
        ])

    @staticmethod
    def sell_settings_menu() -> InlineKeyboardMarkup:
        """Sell settings menu"""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    f"{MENU_EMOJI['amount']} Sell Amount %",
                    callback_data="setting:sell_amountOrPercent"
                )
            ],
            [
                InlineKeyboardButton(
                    f"{MENU_EMOJI['migrate']} Pump Migration %",
                    callback_data="setting:migrateSellPercent"
                )
            ],
            [
                InlineKeyboardButton(
                    f"{MENU_EMOJI['dev_trigger']} Dev Sell Trigger %",
                    callback_data="setting:minDevSellPercent"
                ),
                InlineKeyboardButton(
                    f"{MENU_EMOJI['dev_sell']} Dev Sell Amount %",
                    callback_data="setting:devSellPercent"
                )
            ],
            [
                InlineKeyboardButton(
                    f"{MENU_EMOJI['back']} Back to Main",
                    callback_data="menu:main"
                )
            ]
        ])

    @staticmethod
    def boolean_setting(setting_name: str, current_value: bool, back_menu: str) -> InlineKeyboardMarkup:
        """Boolean toggle keyboard"""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    f"✅ Enabled" if current_value else "❌ Disabled",
                    callback_data=f"toggle:{setting_name}:{not current_value}"
                )
            ],
            [
                InlineKeyboardButton(
                    f"{MENU_EMOJI['back']} Back",
                    callback_data=f"menu:{back_menu}"
                )
            ]
        ])

    @staticmethod
    def numeric_setting(setting_name: str, back_menu: str, suggestions: Optional[list] = None) -> InlineKeyboardMarkup:
        """Numeric input keyboard with common values"""
        buttons = []

        if suggestions:
            # Add suggestion buttons in rows of 2
            for i in range(0, len(suggestions), 2):
                row = []
                for j in range(2):
                    if i + j < len(suggestions):
                        value = suggestions[i + j]
                        row.append(InlineKeyboardButton(
                            str(value),
                            callback_data=f"set:{setting_name}:{value}"
                        ))
                buttons.append(row)

        # Add custom input and back buttons
        buttons.extend([
            [
                InlineKeyboardButton(
                    "✏️ Custom Input",
                    callback_data=f"input:{setting_name}"
                )
            ],
            [
                InlineKeyboardButton(
                    f"{MENU_EMOJI['back']} Back",
                    callback_data=f"menu:{back_menu}"
                )
            ]
        ])

        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def wallet_selection(wallets: list) -> InlineKeyboardMarkup:
        """Wallet selection keyboard"""
        buttons = []

        for wallet in wallets[:10]:  # Limit to 10 wallets
            name = wallet.get('name', 'Unknown')
            address = wallet.get('address', '')
            short_address = f"{address[:6]}...{address[-4:]}" if address else "No Address"

            buttons.append([
                InlineKeyboardButton(
                    f"💳 {name} ({short_address})",
                    callback_data=f"wallet:{wallet['id']}"
                )
            ])

        buttons.append([
            InlineKeyboardButton(
                "➕ Import New Wallet",
                callback_data="action:import_wallet"
            )
        ])

        buttons.append([
            InlineKeyboardButton(
                f"{MENU_EMOJI['back']} Back",
                callback_data="menu:main"
            )
        ])

        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def orders_list(orders: list) -> InlineKeyboardMarkup:
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
                InlineKeyboardButton(
                    order_text,
                    callback_data=f"order:{order.order_id}"
                )
            ])

        if not orders:
            buttons.append([
                InlineKeyboardButton(
                    "📝 No orders yet",
                    callback_data="noop"
                )
            ])

        buttons.append([
            InlineKeyboardButton(
                f"{MENU_EMOJI['back']} Back",
                callback_data="menu:main"
            )
        ])

        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def confirmation_keyboard(action: str, data: str = "") -> InlineKeyboardMarkup:
        """Confirmation dialog"""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✅ Yes, Confirm",
                    callback_data=f"confirm:{action}:{data}"
                ),
                InlineKeyboardButton(
                    "❌ Cancel",
                    callback_data="menu:main"
                )
            ]
        ])

    # Channel Management Keyboards
    @staticmethod
    def channels_menu(channels: list) -> InlineKeyboardMarkup:
        """Channel management main menu"""
        buttons = []

        # Add channel button
        buttons.append([
            InlineKeyboardButton(
                f"{MENU_EMOJI['add_channel']} Add Channel",
                callback_data="action:add_channel"
            )
        ])

        # List channels (max 8)
        for channel in channels[:8]:
            status_emoji = MENU_EMOJI['active'] if channel.is_active else MENU_EMOJI['inactive']
            channel_name = channel.channel_username or channel.channel_title
            if len(channel_name) > 20:
                channel_name = channel_name[:17] + "..."

            buttons.append([
                InlineKeyboardButton(
                    f"{status_emoji} {channel_name}",
                    callback_data=f"channel:{channel.channel_id}"
                )
            ])

        if len(channels) > 8:
            buttons.append([
                InlineKeyboardButton(
                    "📄 View All Channels",
                    callback_data="action:all_channels"
                )
            ])

        if not channels:
            buttons.append([
                InlineKeyboardButton(
                    "📄 No channels configured",
                    callback_data="noop"
                )
            ])

        buttons.append([
            InlineKeyboardButton(
                f"{MENU_EMOJI['back']} Back to Main",
                callback_data="menu:main"
            )
        ])

        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def channel_settings(channel) -> InlineKeyboardMarkup:
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
                InlineKeyboardButton(
                    f"{status_emoji} {status_text} Channel",
                    callback_data=f"toggle_channel:{channel.channel_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    f"{MENU_EMOJI['filter_mode']} Filter: {filter_text}",
                    callback_data=f"channel_filter:{channel.channel_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    f"{MENU_EMOJI['amount']} Buy Amount",
                    callback_data=f"channel_amount:{channel.channel_id}"
                )
            ]
        ]

        if channel.filter_mode.value == 'users':
            user_count = len(channel.allowed_user_ids)
            buttons.append([
                InlineKeyboardButton(
                    f"{MENU_EMOJI['specific_users']} Manage Users ({user_count})",
                    callback_data=f"channel_users:{channel.channel_id}"
                )
            ])

        buttons.extend([
            [
                InlineKeyboardButton(
                    f"{MENU_EMOJI['remove_channel']} Remove Channel",
                    callback_data=f"remove_channel:{channel.channel_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    f"{MENU_EMOJI['back']} Back to Channels",
                    callback_data="menu:channels"
                )
            ]
        ])

        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def filter_mode_selection(channel_id: int) -> InlineKeyboardMarkup:
        """Filter mode selection for channel"""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    f"{MENU_EMOJI['all_msgs']} All Messages",
                    callback_data=f"set_filter:{channel_id}:all"
                )
            ],
            [
                InlineKeyboardButton(
                    f"{MENU_EMOJI['admin_only']} Admin Only",
                    callback_data=f"set_filter:{channel_id}:admins"
                )
            ],
            [
                InlineKeyboardButton(
                    f"{MENU_EMOJI['specific_users']} Specific Users",
                    callback_data=f"set_filter:{channel_id}:users"
                )
            ],
            [
                InlineKeyboardButton(
                    f"{MENU_EMOJI['back']} Back",
                    callback_data=f"channel:{channel_id}"
                )
            ]
        ])

    @staticmethod
    def channel_amount_setting(channel_id: int) -> InlineKeyboardMarkup:
        """Channel-specific buy amount setting"""
        suggestions = [0.01, 0.05, 0.1, 0.2, 0.5, 1.0]
        buttons = []

        # Add suggestion buttons in rows of 3
        for i in range(0, len(suggestions), 3):
            row = []
            for j in range(3):
                if i + j < len(suggestions):
                    value = suggestions[i + j]
                    row.append(InlineKeyboardButton(
                        f"{value} SOL",
                        callback_data=f"set_channel_amount:{channel_id}:{value}"
                    ))
            buttons.append(row)

        buttons.extend([
            [
                InlineKeyboardButton(
                    "✏️ Custom Amount",
                    callback_data=f"custom_channel_amount:{channel_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "🔄 Use Default",
                    callback_data=f"default_channel_amount:{channel_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    f"{MENU_EMOJI['back']} Back",
                    callback_data=f"channel:{channel_id}"
                )
            ]
        ])

        return InlineKeyboardMarkup(buttons)


# Predefined setting suggestions for quick selection
SETTING_SUGGESTIONS = {
    'amountOrPercent': [0.01, 0.05, 0.1, 0.2, 0.5, 1.0],
    'maxSlippage': [0.05, 0.1, 0.15, 0.2, 0.3, 0.5],
    'retries': [1, 2, 3, 5],
    'concurrentNodes': [1, 2, 3],
    'jitoTip': [0.001, 0.005, 0.01, 0.02],
    'gasFeeDelta': [2, 5, 10, 15, 20],
    'maxFeePerGas': [50, 100, 150, 200, 300],
    'stopEarnPercent': [0.1, 0.2, 0.5, 1.0, 2.0, 5.0],
    'stopLossPercent': [0.1, 0.2, 0.3, 0.5],
    'migrateSellPercent': [0.0, 0.1, 0.2, 0.5, 1.0],
    'minDevSellPercent': [0.1, 0.2, 0.3, 0.5],
    'devSellPercent': [0.0, 0.5, 1.0],
    'sell_priorityFee': [],  # String input only
    'sell_jitoTip': [0.001, 0.002, 0.005, 0.01, 0.02],
    'sell_gasFeeDelta': [5, 10, 15, 20, 30],
    'sell_maxFeePerGas': [100, 150, 200, 250, 300],
    'sell_maxSlippage': [0.15, 0.25, 0.35, 0.5],
}