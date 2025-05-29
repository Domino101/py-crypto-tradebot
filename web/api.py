# web/api.py - API 路由定義

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Dict, Any, Optional
import asyncio
import os
import json
from datetime import datetime, timedelta
import pandas as pd

from .models import *
from .auth import verify_token, create_access_token
from .services import (
    StrategyService, 
    BacktestService, 
    LiveTradeService, 
    MarketDataService,
    SystemService
)

router = APIRouter()
security = HTTPBearer()

# 服務實例
strategy_service = StrategyService()
backtest_service = BacktestService()
live_trade_service = LiveTradeService()
market_data_service = MarketDataService()
system_service = SystemService()

# 認證依賴
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """獲取當前用戶"""
    token = credentials.credentials
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload

# 認證端點
@router.post("/auth/login", response_model=Token)
async def login(user_data: UserLogin):
    """用戶登錄"""
    # 簡單的用戶驗證 (生產環境應該使用數據庫)
    if user_data.username == "admin" and user_data.password == "password":
        access_token = create_access_token({"sub": user_data.username})
        return Token(access_token=access_token)
    raise HTTPException(status_code=401, detail="Invalid credentials")

# 系統狀態端點
@router.get("/status", response_model=SystemStatus)
async def get_system_status(current_user: dict = Depends(get_current_user)):
    """獲取系統狀態"""
    return await system_service.get_status()

@router.get("/ping")
async def ping():
    """健康檢查"""
    return {"status": "pong", "timestamp": datetime.now()}

# 策略管理端點
@router.get("/strategies", response_model=List[StrategyInfo])
async def list_strategies(current_user: dict = Depends(get_current_user)):
    """獲取所有可用策略"""
    return await strategy_service.list_strategies()

@router.get("/strategies/{strategy_name}", response_model=StrategyInfo)
async def get_strategy(strategy_name: str, current_user: dict = Depends(get_current_user)):
    """獲取特定策略詳情"""
    strategy = await strategy_service.get_strategy(strategy_name)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy

@router.get("/strategies/{strategy_name}/parameters", response_model=List[StrategyParameter])
async def get_strategy_parameters(strategy_name: str, current_user: dict = Depends(get_current_user)):
    """獲取策略參數定義"""
    params = await strategy_service.get_strategy_parameters(strategy_name)
    if not params:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return params

# 回測端點
@router.post("/backtest", response_model=BaseResponse)
async def start_backtest(
    request: BacktestRequest, 
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """開始回測"""
    task_id = await backtest_service.start_backtest(request, background_tasks)
    return BaseResponse(
        success=True, 
        message=f"Backtest started with task ID: {task_id}"
    )

@router.get("/backtest/{task_id}/status")
async def get_backtest_status(task_id: str, current_user: dict = Depends(get_current_user)):
    """獲取回測狀態"""
    status = await backtest_service.get_backtest_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Backtest task not found")
    return status

@router.get("/backtest/{task_id}/result", response_model=BacktestResult)
async def get_backtest_result(task_id: str, current_user: dict = Depends(get_current_user)):
    """獲取回測結果"""
    result = await backtest_service.get_backtest_result(task_id)
    if not result:
        raise HTTPException(status_code=404, detail="Backtest result not found")
    return result

# 實盤交易端點
@router.post("/live/start", response_model=BaseResponse)
async def start_live_trading(
    request: LiveTradeRequest,
    current_user: dict = Depends(get_current_user)
):
    """開始實盤交易"""
    success = await live_trade_service.start_trading(request)
    if success:
        return BaseResponse(success=True, message="Live trading started")
    raise HTTPException(status_code=400, detail="Failed to start live trading")

@router.post("/live/stop", response_model=BaseResponse)
async def stop_live_trading(current_user: dict = Depends(get_current_user)):
    """停止實盤交易"""
    success = await live_trade_service.stop_trading()
    if success:
        return BaseResponse(success=True, message="Live trading stopped")
    raise HTTPException(status_code=400, detail="Failed to stop live trading")

@router.get("/live/trades", response_model=List[TradeInfo])
async def get_live_trades(current_user: dict = Depends(get_current_user)):
    """獲取實盤交易記錄"""
    return await live_trade_service.get_trades()

# 市場數據端點
@router.post("/market/data", response_model=List[CandleData])
async def get_market_data(
    request: MarketDataRequest,
    current_user: dict = Depends(get_current_user)
):
    """獲取市場數據"""
    data = await market_data_service.get_candle_data(request)
    return data

@router.get("/market/symbols")
async def get_available_symbols(current_user: dict = Depends(get_current_user)):
    """獲取可用交易對"""
    return await market_data_service.get_available_symbols()

@router.get("/market/timeframes")
async def get_available_timeframes(current_user: dict = Depends(get_current_user)):
    """獲取可用時間框架"""
    return ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"]

# 配置端點
@router.get("/config", response_model=BotConfig)
async def get_config(current_user: dict = Depends(get_current_user)):
    """獲取機器人配置"""
    return await system_service.get_config()

@router.post("/config", response_model=BaseResponse)
async def update_config(
    config: BotConfig,
    current_user: dict = Depends(get_current_user)
):
    """更新機器人配置"""
    success = await system_service.update_config(config)
    if success:
        return BaseResponse(success=True, message="Configuration updated")
    raise HTTPException(status_code=400, detail="Failed to update configuration")
