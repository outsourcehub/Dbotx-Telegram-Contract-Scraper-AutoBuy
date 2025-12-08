"""
Data Models for Ultra-Fast Trading Bot
Memory-optimized storage for instant access
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import time
import ujson
import sqlite3
import asyncio
import threading
from enum import Enum
import logging

logger = logging.getLogger(__name__)


@dataclass
class User:
    """User model with trading settings"""
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    settings: Dict[str, Any] = field(default_factory=dict)
    api_key: Optional[str] = None
    wallet_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    is_verified: bool = False
    verified_at: Optional[float] = None
    wallet_pattern: Optional[str] = None

    def update_activity(self):
        """Update last activity timestamp"""
        self.last_active = time.time()

    def get_setting(self, key: str, default: Any = None, chain: str = 'solana') -> Any:
        """Get a specific setting value for a chain"""
        if chain in self.settings:
            return self.settings[chain].get(key, default)
        return default

    def set_setting(self, key: str, value: Any, chain: str = 'solana'):
        """Set a specific setting value for a chain"""
        if chain not in self.settings:
            from config import DEFAULT_SETTINGS
            self.settings[chain] = DEFAULT_SETTINGS.get(chain, {}).copy()
        self.settings[chain][key] = value
    
    def update_setting(self, key: str, value: Any, chain: str = 'solana'):
        """Update a specific setting value (alias for set_setting)"""
        self.set_setting(key, value, chain)
    
    def get_chain_settings(self, chain: str) -> Dict[str, Any]:
        """Get all settings for a specific chain"""
        if chain not in self.settings:
            from config import DEFAULT_SETTINGS
            return DEFAULT_SETTINGS.get(chain, {}).copy()
        return self.settings.get(chain, {})

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'settings': self.settings,
            'api_key': self.api_key,
            'wallet_id': self.wallet_id,
            'created_at': self.created_at,
            'last_active': self.last_active,
            'is_verified': self.is_verified,
            'verified_at': self.verified_at,
            'wallet_pattern': self.wallet_pattern
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Create User from dictionary"""
        return cls(**data)


class ChannelType(Enum):
    """Telegram channel types"""
    CHANNEL = "channel"
    GROUP = "group"
    SUPERGROUP = "supergroup"


class FilterMode(Enum):
    """Message filtering modes"""
    ALL_MESSAGES = "all"
    ADMIN_ONLY = "admins"  # Updated to match guide
    SPECIFIC_USERS = "users"  # Updated to match guide


@dataclass
class ChannelSubscription:
    """Channel subscription model for MTProto monitoring"""
    channel_id: int
    user_id: int  # Owner of this subscription
    channel_title: str
    channel_username: Optional[str] = None
    channel_type: ChannelType = ChannelType.CHANNEL
    is_active: bool = True
    filter_mode: FilterMode = FilterMode.ALL_MESSAGES
    allowed_user_ids: List[int] = field(default_factory=list)
    custom_buy_amount: Optional[float] = None
    created_at: float = field(default_factory=time.time)
    last_message_at: Optional[float] = None
    total_trades: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'channel_id': self.channel_id,
            'user_id': self.user_id,
            'channel_title': self.channel_title,
            'channel_username': self.channel_username,
            'channel_type': self.channel_type.value,
            'is_active': self.is_active,
            'filter_mode': self.filter_mode.value,
            'allowed_user_ids': self.allowed_user_ids,
            'custom_buy_amount': self.custom_buy_amount,
            'created_at': self.created_at,
            'last_message_at': self.last_message_at,
            'total_trades': self.total_trades
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChannelSubscription':
        """Create ChannelSubscription from dictionary"""
        return cls(
            channel_id=data['channel_id'],
            user_id=data['user_id'],
            channel_title=data['channel_title'],
            channel_username=data.get('channel_username'),
            channel_type=ChannelType(data.get('channel_type', 'channel')),
            is_active=data.get('is_active', True),
            filter_mode=FilterMode(data.get('filter_mode', 'all')),
            allowed_user_ids=data.get('allowed_user_ids', []),
            custom_buy_amount=data.get('custom_buy_amount'),
            created_at=data.get('created_at', time.time()),
            last_message_at=data.get('last_message_at'),
            total_trades=data.get('total_trades', 0)
        )


@dataclass
class TradeOrder:
    """Trade order model for tracking"""
    order_id: str
    user_id: int
    chain: str
    pair: str
    order_type: str  # 'buy', 'sell', 'dev_sell', 'migrate'
    amount: float
    status: str = 'pending'  # 'pending', 'completed', 'failed'
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    error_message: Optional[str] = None
    settings: Dict[str, Any] = field(default_factory=dict)

    def mark_completed(self):
        """Mark order as completed"""
        self.status = 'completed'
        self.completed_at = time.time()

    def mark_failed(self, error: str):
        """Mark order as failed with error"""
        self.status = 'failed'
        self.error_message = error
        self.completed_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'order_id': self.order_id,
            'user_id': self.user_id,
            'chain': self.chain,
            'pair': self.pair,
            'order_type': self.order_type,
            'amount': self.amount,
            'status': self.status,
            'created_at': self.created_at,
            'completed_at': self.completed_at,
            'error_message': self.error_message,
            'settings': self.settings
        }




class SQLiteStorage:
    """Ultra-fast SQLite storage for trading bot with persistence"""
    
    def __init__(self, db_path: str = "trading_bot.db"):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize SQLite database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('PRAGMA synchronous=NORMAL')
            conn.execute('PRAGMA cache_size=10000')
            conn.execute('PRAGMA temp_store=MEMORY')
            
            # Users table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    settings TEXT,
                    api_key TEXT,
                    wallet_id TEXT,
                    created_at REAL,
                    last_active REAL,
                    is_verified BOOLEAN DEFAULT 0,
                    verified_at REAL,
                    wallet_pattern TEXT
                )
            ''')
            
            # Orders table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    user_id INTEGER,
                    chain TEXT,
                    pair TEXT,
                    order_type TEXT,
                    amount REAL,
                    status TEXT,
                    created_at REAL,
                    completed_at REAL,
                    error_message TEXT,
                    settings TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Channel subscriptions table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS channel_subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id INTEGER,
                    user_id INTEGER,
                    channel_title TEXT,
                    channel_username TEXT,
                    channel_type TEXT,
                    is_active BOOLEAN,
                    filter_mode TEXT,
                    allowed_user_ids TEXT,
                    custom_buy_amount REAL,
                    created_at REAL,
                    last_message_at REAL,
                    total_trades INTEGER,
                    UNIQUE(channel_id, user_id),
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # User states table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_states (
                    user_id INTEGER PRIMARY KEY,
                    state TEXT,
                    timestamp REAL,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            conn.commit()
    
    def _serialize_json(self, data: Any) -> str:
        """Serialize data to JSON string"""
        if data is None:
            return '{}'
        return ujson.dumps(data)
    
    def _deserialize_json(self, data: str) -> Any:
        """Deserialize JSON string to data"""
        if not data:
            return {}
        try:
            return ujson.loads(data)
        except:
            return {}
    
    # User management methods
    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                'SELECT * FROM users WHERE user_id = ?', (user_id,)
            )
            row = cursor.fetchone()
            if row:
                return User(
                    user_id=row['user_id'],
                    username=row['username'],
                    first_name=row['first_name'],
                    last_name=row['last_name'],
                    settings=self._deserialize_json(row['settings']),
                    api_key=row['api_key'],
                    wallet_id=row['wallet_id'],
                    created_at=row['created_at'],
                    last_active=row['last_active'],
                    is_verified=bool(row['is_verified']) if 'is_verified' in row.keys() else False,
                    verified_at=row['verified_at'] if 'verified_at' in row.keys() else None,
                    wallet_pattern=row['wallet_pattern'] if 'wallet_pattern' in row.keys() else None
                )
            return None
    
    def create_user(self, user_id: int, **kwargs) -> User:
        """Create or update user"""
        # CRITICAL SAFEGUARD: Reject 'settings' parameter to prevent accidental overwrites
        if 'settings' in kwargs:
            raise ValueError(
                "SECURITY: Cannot pass 'settings' to create_user()! "
                "Use update_user_settings() or update_user_setting() instead. "
                "This prevents accidental deletion of user's custom settings."
            )
        
        user = self.get_user(user_id)
        
        if user:
            # Update existing user (settings are now guaranteed to be safe)
            for key, value in kwargs.items():
                if hasattr(user, key) and value is not None:
                    setattr(user, key, value)
            user.update_activity()
            
            # Ensure enabled_chains exists in settings
            if 'enabled_chains' not in user.settings:
                user.settings['enabled_chains'] = ['solana', 'bsc', 'ethereum', 'base', 'tron']
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    UPDATE users SET 
                    username=?, first_name=?, last_name=?, settings=?, 
                    api_key=?, wallet_id=?, last_active=?, is_verified=?,
                    verified_at=?, wallet_pattern=?
                    WHERE user_id=?
                ''', (
                    user.username, user.first_name, user.last_name,
                    self._serialize_json(user.settings), user.api_key,
                    user.wallet_id, user.last_active, user.is_verified,
                    user.verified_at, user.wallet_pattern, user_id
                ))
                conn.commit()
                logger.debug(f"💾 Updated user {user_id} in database")
        else:
            # Create new user with default settings
            from config import DEFAULT_SETTINGS
            new_user_settings = DEFAULT_SETTINGS.copy()
            
            user = User(user_id=user_id, settings=new_user_settings, **kwargs)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO users 
                    (user_id, username, first_name, last_name, settings, 
                     api_key, wallet_id, created_at, last_active, is_verified,
                     verified_at, wallet_pattern)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user.user_id, user.username, user.first_name, user.last_name,
                    self._serialize_json(user.settings), user.api_key,
                    user.wallet_id, user.created_at, user.last_active,
                    user.is_verified, user.verified_at, user.wallet_pattern
                ))
                conn.commit()
                logger.debug(f"💾 Created new user {user_id} in database with default settings")
        
        return user
    
    def update_user_setting(self, user_id: int, key: str, value: Any):
        """Update a specific user setting"""
        user = self.get_user(user_id)
        if user:
            user.set_setting(key, value)
            user.update_activity()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    'UPDATE users SET settings=?, last_active=? WHERE user_id=?',
                    (self._serialize_json(user.settings), user.last_active, user_id)
                )
                conn.commit()
    
    def update_user_settings(self, user_id: int, settings: Dict[str, Any]):
        """Update all user settings at once"""
        user = self.get_user(user_id)
        if user:
            user.settings = settings.copy()
            user.update_activity()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    'UPDATE users SET settings=?, last_active=? WHERE user_id=?',
                    (self._serialize_json(user.settings), user.last_active, user_id)
                )
                conn.commit()
    
    def get_user_setting(self, user_id: int, key: str, default: Any = None) -> Any:
        """Get a specific user setting"""
        user = self.get_user(user_id)
        if user:
            return user.get_setting(key, default)
        return default
    
    # Order management methods
    def create_order(self, order_id: str, user_id: int, **kwargs) -> TradeOrder:
        """Create a new trade order"""
        order = TradeOrder(order_id=order_id, user_id=user_id, **kwargs)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO orders 
                (order_id, user_id, chain, pair, order_type, amount, status, 
                 created_at, completed_at, error_message, settings)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                order.order_id, order.user_id, order.chain, order.pair,
                order.order_type, order.amount, order.status, order.created_at,
                order.completed_at, order.error_message, 
                self._serialize_json(order.settings)
            ))
            conn.commit()
        
        return order
    
    def get_order(self, order_id: str) -> Optional[TradeOrder]:
        """Get order by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                'SELECT * FROM orders WHERE order_id = ?', (order_id,)
            )
            row = cursor.fetchone()
            if row:
                return TradeOrder(
                    order_id=row['order_id'],
                    user_id=row['user_id'],
                    chain=row['chain'],
                    pair=row['pair'],
                    order_type=row['order_type'],
                    amount=row['amount'],
                    status=row['status'],
                    created_at=row['created_at'],
                    completed_at=row['completed_at'],
                    error_message=row['error_message'],
                    settings=self._deserialize_json(row['settings'])
                )
            return None
    
    def get_user_orders(self, user_id: int, limit: int = 10) -> List[TradeOrder]:
        """Get recent orders for user"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM orders WHERE user_id = ? 
                ORDER BY created_at DESC LIMIT ?
            ''', (user_id, limit))
            
            orders = []
            for row in cursor.fetchall():
                orders.append(TradeOrder(
                    order_id=row['order_id'],
                    user_id=row['user_id'],
                    chain=row['chain'],
                    pair=row['pair'],
                    order_type=row['order_type'],
                    amount=row['amount'],
                    status=row['status'],
                    created_at=row['created_at'],
                    completed_at=row['completed_at'],
                    error_message=row['error_message'],
                    settings=self._deserialize_json(row['settings'])
                ))
            return orders
    
    def update_order_status(self, order_id: str, status: str, error: Optional[str] = None):
        """Update order status"""
        completed_at = time.time() if status in ['completed', 'failed'] else None
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                UPDATE orders SET status=?, completed_at=?, error_message=?
                WHERE order_id=?
            ''', (status, completed_at, error, order_id))
            conn.commit()
    
    # Channel management methods
    def create_channel_subscription(self, user_id: int, channel_id: int, 
                                  channel_title: str, **kwargs) -> ChannelSubscription:
        """Create or update channel subscription"""
        existing = self.get_channel_subscription(user_id, channel_id)
        
        if existing:
            # Update existing subscription
            for key, value in kwargs.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            subscription = existing
        else:
            # Create new subscription
            subscription = ChannelSubscription(
                channel_id=channel_id,
                user_id=user_id,
                channel_title=channel_title,
                **kwargs
            )
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO channel_subscriptions 
                (channel_id, user_id, channel_title, channel_username, channel_type,
                 is_active, filter_mode, allowed_user_ids, custom_buy_amount,
                 created_at, last_message_at, total_trades)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                subscription.channel_id, subscription.user_id, subscription.channel_title,
                subscription.channel_username, subscription.channel_type.value,
                subscription.is_active, subscription.filter_mode.value,
                self._serialize_json(subscription.allowed_user_ids),
                subscription.custom_buy_amount, subscription.created_at,
                subscription.last_message_at, subscription.total_trades
            ))
            conn.commit()
        
        return subscription
    
    def get_channel_subscription(self, user_id: int, channel_id: int) -> Optional[ChannelSubscription]:
        """Get specific channel subscription"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                'SELECT * FROM channel_subscriptions WHERE user_id = ? AND channel_id = ?',
                (user_id, channel_id)
            )
            row = cursor.fetchone()
            if row:
                return ChannelSubscription(
                    channel_id=row['channel_id'],
                    user_id=row['user_id'],
                    channel_title=row['channel_title'],
                    channel_username=row['channel_username'],
                    channel_type=ChannelType(row['channel_type']),
                    is_active=bool(row['is_active']),
                    filter_mode=FilterMode(row['filter_mode']),
                    allowed_user_ids=self._deserialize_json(row['allowed_user_ids']),
                    custom_buy_amount=row['custom_buy_amount'],
                    created_at=row['created_at'],
                    last_message_at=row['last_message_at'],
                    total_trades=row['total_trades']
                )
            return None
    
    def get_user_channels(self, user_id: int) -> List[ChannelSubscription]:
        """Get all channel subscriptions for user"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                'SELECT * FROM channel_subscriptions WHERE user_id = ?', (user_id,)
            )
            
            channels = []
            for row in cursor.fetchall():
                channels.append(ChannelSubscription(
                    channel_id=row['channel_id'],
                    user_id=row['user_id'],
                    channel_title=row['channel_title'],
                    channel_username=row['channel_username'],
                    channel_type=ChannelType(row['channel_type']),
                    is_active=bool(row['is_active']),
                    filter_mode=FilterMode(row['filter_mode']),
                    allowed_user_ids=self._deserialize_json(row['allowed_user_ids']),
                    custom_buy_amount=row['custom_buy_amount'],
                    created_at=row['created_at'],
                    last_message_at=row['last_message_at'],
                    total_trades=row['total_trades']
                ))
            return channels
    
    def get_active_channels(self, user_id: int) -> List[ChannelSubscription]:
        """Get active channel subscriptions for user"""
        return [ch for ch in self.get_user_channels(user_id) if ch.is_active]
    
    def remove_channel_subscription(self, user_id: int, channel_id: int) -> bool:
        """Remove channel subscription"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'DELETE FROM channel_subscriptions WHERE user_id = ? AND channel_id = ?',
                (user_id, channel_id)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    # User state management
    def set_user_state(self, user_id: int, state: str):
        """Set user state for multi-step operations"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO user_states (user_id, state, timestamp)
                VALUES (?, ?, ?)
            ''', (user_id, state, time.time()))
            conn.commit()
    
    def get_user_state(self, user_id: int) -> Optional[str]:
        """Get user state"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                'SELECT * FROM user_states WHERE user_id = ?', (user_id,)
            )
            row = cursor.fetchone()
            if row:
                # Clear old states (older than 5 minutes)
                if time.time() - row['timestamp'] > 300:
                    conn.execute('DELETE FROM user_states WHERE user_id = ?', (user_id,))
                    conn.commit()
                    return None
                return row['state']
            return None
    
    def is_awaiting_channel_forward(self, user_id: int) -> bool:
        """Check if user is awaiting channel forward"""
        return self.get_user_state(user_id) == 'awaiting_channel_forward'
    
    def clear_user_state(self, user_id: int):
        """Clear user state"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('DELETE FROM user_states WHERE user_id = ?', (user_id,))
            conn.commit()
    
    def toggle_channel(self, user_id: int, channel_id: int) -> Optional[bool]:
        """Toggle channel active status, returns new status"""
        subscription = self.get_channel_subscription(user_id, channel_id)
        if subscription:
            new_status = not subscription.is_active
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    'UPDATE channel_subscriptions SET is_active = ? WHERE user_id = ? AND channel_id = ?',
                    (new_status, user_id, channel_id)
                )
                conn.commit()
            return new_status
        return None
    
    def update_channel_subscription(self, channel_sub: ChannelSubscription):
        """Update channel subscription using ChannelSubscription object"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                UPDATE channel_subscriptions SET 
                channel_title=?, channel_username=?, channel_type=?, is_active=?,
                filter_mode=?, allowed_user_ids=?, custom_buy_amount=?,
                last_message_at=?, total_trades=?
                WHERE user_id=? AND channel_id=?
            ''', (
                channel_sub.channel_title, channel_sub.channel_username,
                channel_sub.channel_type.value, channel_sub.is_active,
                channel_sub.filter_mode.value, 
                self._serialize_json(channel_sub.allowed_user_ids),
                channel_sub.custom_buy_amount, channel_sub.last_message_at,
                channel_sub.total_trades, channel_sub.user_id, channel_sub.channel_id
            ))
            conn.commit()
    
    def update_channel_settings(self, user_id: int, channel_id: int, **kwargs):
        """Update channel-specific settings"""
        subscription = self.get_channel_subscription(user_id, channel_id)
        if subscription:
            # Update the subscription object
            for key, value in kwargs.items():
                if hasattr(subscription, key):
                    setattr(subscription, key, value)
            
            # Save to database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    UPDATE channel_subscriptions SET 
                    channel_title=?, channel_username=?, channel_type=?, is_active=?,
                    filter_mode=?, allowed_user_ids=?, custom_buy_amount=?,
                    last_message_at=?, total_trades=?
                    WHERE user_id=? AND channel_id=?
                ''', (
                    subscription.channel_title, subscription.channel_username,
                    subscription.channel_type.value, subscription.is_active,
                    subscription.filter_mode.value, 
                    self._serialize_json(subscription.allowed_user_ids),
                    subscription.custom_buy_amount, subscription.last_message_at,
                    subscription.total_trades, user_id, channel_id
                ))
                conn.commit()
    
    def update_channel_user_list(self, user_id: int, channel_id: int, user_ids: List[int]):
        """Update tracked user list for specific users monitoring mode"""
        subscription = self.get_channel_subscription(user_id, channel_id)
        if subscription:
            subscription.allowed_user_ids = user_ids.copy()
            subscription.filter_mode = FilterMode.SPECIFIC_USERS
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    UPDATE channel_subscriptions SET 
                    filter_mode=?, allowed_user_ids=?
                    WHERE user_id=? AND channel_id=?
                ''', (
                    subscription.filter_mode.value,
                    self._serialize_json(subscription.allowed_user_ids),
                    user_id, channel_id
                ))
                conn.commit()
            return True
        return False
    
    def get_all_active_channels(self) -> List[ChannelSubscription]:
        """Get all active channels across all users (for real-time monitor)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                'SELECT * FROM channel_subscriptions WHERE is_active = 1'
            )
            
            channels = []
            for row in cursor.fetchall():
                channels.append(ChannelSubscription(
                    channel_id=row['channel_id'],
                    user_id=row['user_id'],
                    channel_title=row['channel_title'],
                    channel_username=row['channel_username'],
                    channel_type=ChannelType(row['channel_type']),
                    is_active=bool(row['is_active']),
                    filter_mode=FilterMode(row['filter_mode']),
                    allowed_user_ids=self._deserialize_json(row['allowed_user_ids']),
                    custom_buy_amount=row['custom_buy_amount'],
                    created_at=row['created_at'],
                    last_message_at=row['last_message_at'],
                    total_trades=row['total_trades']
                ))
            return channels
    
    def get_all_user_channels_by_channel_id(self, channel_id: int) -> List[ChannelSubscription]:
        """Get all user subscriptions for a specific channel ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                'SELECT * FROM channel_subscriptions WHERE channel_id = ? AND is_active = 1',
                (channel_id,)
            )
            
            channels = []
            for row in cursor.fetchall():
                channels.append(ChannelSubscription(
                    channel_id=row['channel_id'],
                    user_id=row['user_id'],
                    channel_title=row['channel_title'],
                    channel_username=row['channel_username'],
                    channel_type=ChannelType(row['channel_type']),
                    is_active=bool(row['is_active']),
                    filter_mode=FilterMode(row['filter_mode']),
                    allowed_user_ids=self._deserialize_json(row['allowed_user_ids']),
                    custom_buy_amount=row['custom_buy_amount'],
                    created_at=row['created_at'],
                    last_message_at=row['last_message_at'],
                    total_trades=row['total_trades']
                ))
            return channels
    
    def get_stats(self) -> Dict[str, int]:
        """Get storage statistics"""
        with sqlite3.connect(self.db_path) as conn:
            users_count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
            channels_count = conn.execute('SELECT COUNT(*) FROM channel_subscriptions').fetchone()[0]
            orders_count = conn.execute('SELECT COUNT(*) FROM orders').fetchone()[0]
            
            return {
                'users': users_count,
                'channels': channels_count,
                'orders': orders_count
            }
    
    def export_data(self) -> Dict[str, Any]:
        """Export all data for backup"""
        data = {
            'users': [],
            'orders': [],
            'channel_subscriptions': [],
            'user_states': []
        }
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Export users
            for row in conn.execute('SELECT * FROM users'):
                data['users'].append(dict(row))
            
            # Export orders
            for row in conn.execute('SELECT * FROM orders'):
                data['orders'].append(dict(row))
            
            # Export channel subscriptions
            for row in conn.execute('SELECT * FROM channel_subscriptions'):
                data['channel_subscriptions'].append(dict(row))
            
            # Export user states
            for row in conn.execute('SELECT * FROM user_states'):
                data['user_states'].append(dict(row))
        
        return data
    
    def import_data(self, data: Dict[str, Any]):
        """Import data from backup"""
        with sqlite3.connect(self.db_path) as conn:
            # Clear existing data
            conn.execute('DELETE FROM user_states')
            conn.execute('DELETE FROM channel_subscriptions')
            conn.execute('DELETE FROM orders')
            conn.execute('DELETE FROM users')
            
            # Import users
            if 'users' in data:
                for user_data in data['users']:
                    conn.execute('''
                        INSERT INTO users 
                        (user_id, username, first_name, last_name, settings, 
                         api_key, wallet_id, created_at, last_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        user_data['user_id'], user_data['username'], 
                        user_data['first_name'], user_data['last_name'],
                        user_data['settings'], user_data['api_key'],
                        user_data['wallet_id'], user_data['created_at'],
                        user_data['last_active']
                    ))
            
            # Import orders
            if 'orders' in data:
                for order_data in data['orders']:
                    conn.execute('''
                        INSERT INTO orders 
                        (order_id, user_id, chain, pair, order_type, amount, status, 
                         created_at, completed_at, error_message, settings)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        order_data['order_id'], order_data['user_id'],
                        order_data['chain'], order_data['pair'],
                        order_data['order_type'], order_data['amount'],
                        order_data['status'], order_data['created_at'],
                        order_data['completed_at'], order_data['error_message'],
                        order_data['settings']
                    ))
            
            # Import channel subscriptions
            if 'channel_subscriptions' in data:
                for ch_data in data['channel_subscriptions']:
                    conn.execute('''
                        INSERT INTO channel_subscriptions 
                        (channel_id, user_id, channel_title, channel_username, 
                         channel_type, is_active, filter_mode, allowed_user_ids,
                         custom_buy_amount, created_at, last_message_at, total_trades)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        ch_data['channel_id'], ch_data['user_id'],
                        ch_data['channel_title'], ch_data['channel_username'],
                        ch_data['channel_type'], ch_data['is_active'],
                        ch_data['filter_mode'], ch_data['allowed_user_ids'],
                        ch_data['custom_buy_amount'], ch_data['created_at'],
                        ch_data['last_message_at'], ch_data['total_trades']
                    ))
            
            # Import user states
            if 'user_states' in data:
                for state_data in data['user_states']:
                    conn.execute('''
                        INSERT INTO user_states (user_id, state, timestamp)
                        VALUES (?, ?, ?)
                    ''', (
                        state_data['user_id'], state_data['state'],
                        state_data['timestamp']
                    ))
            
            conn.commit()


# Global storage instance - initialize with SQLite storage immediately
storage = SQLiteStorage()