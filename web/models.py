# web/models.py - Pydantic 模型定義

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum

class TradingMode(str, Enum):
    """交易模式"""
    BACKTEST = "backtest"
    LIVE = "live"
    PAPER = "paper"

class OrderSide(str, Enum):
    """訂單方向"""
    BUY = "buy"
    SELL = "sell"
    LONG = "long"
    SHORT = "short"

class OrderType(str, Enum):
    """訂單類型"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"

class TradeStatus(str, Enum):
    """交易狀態"""
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"

# 基礎響應模型
class BaseResponse(BaseModel):
    """基礎響應模型"""
    success: bool = True
    message: str = ""
    timestamp: datetime = Field(default_factory=datetime.now)

# 用戶認證相關
class UserLogin(BaseModel):
    """用戶登錄請求"""
    username: str
    password: str

class Token(BaseModel):
    """JWT Token 響應"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600

# 策略相關模型
class StrategyInfo(BaseModel):
    """策略信息"""
    name: str
    description: Optional[str] = ""
    parameters: Dict[str, Any] = {}
    file_path: str

class StrategyParameter(BaseModel):
    """策略參數"""
    name: str
    type: str
    default_value: Any
    description: Optional[str] = ""
    options: Optional[List[Any]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None

# 回測相關模型
class BacktestRequest(BaseModel):
    """回測請求"""
    strategy_name: str
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    initial_capital: float = 10000.0
    leverage: float = 1.0
    strategy_params: Dict[str, Any] = {}

class BacktestResult(BaseModel):
    """回測結果"""
    strategy_name: str
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: Optional[float] = None
    win_rate: float
    total_trades: int
    plot_path: Optional[str] = None

# 實盤交易相關模型
class LiveTradeRequest(BaseModel):
    """實盤交易請求"""
    strategy_name: str
    symbol: str
    timeframe: str
    trade_amount: float
    paper_trading: bool = True
    strategy_params: Dict[str, Any] = {}

class TradeInfo(BaseModel):
    """交易信息"""
    trade_id: str
    symbol: str
    side: OrderSide
    amount: float
    price: float
    timestamp: datetime
    status: TradeStatus
    profit_loss: Optional[float] = None

# 市場數據相關模型
class CandleData(BaseModel):
    """K線數據"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

class MarketDataRequest(BaseModel):
    """市場數據請求"""
    symbol: str
    timeframe: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: Optional[int] = 1000

# 系統狀態相關模型
class SystemStatus(BaseModel):
    """系統狀態"""
    trading_mode: TradingMode
    is_running: bool
    active_trades: int
    total_profit: float
    uptime: str
    last_update: datetime

class BotConfig(BaseModel):
    """機器人配置"""
    trading_mode: TradingMode
    max_open_trades: int = 3
    stake_amount: float = 100.0
    dry_run: bool = True
    exchange: str = "binance"

# WebSocket 消息模型
class WSMessage(BaseModel):
    """WebSocket 消息"""
    type: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)

class WSSubscription(BaseModel):
    """WebSocket 訂閱請求"""
    type: str = "subscribe"
    channels: List[str]
