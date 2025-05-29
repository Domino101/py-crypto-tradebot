# web/app.py - 主要的 FastAPI 應用程序

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import HTMLResponse
import uvicorn
import asyncio
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
from pathlib import Path

# 導入我們的模組
from .api import router as api_router
from .websocket_manager import WebSocketManager
from .auth import verify_token, create_access_token
from .models import *

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 創建 FastAPI 應用
app = FastAPI(
    title="加密貨幣交易系統 Web API",
    description="基於 freqtrade 風格的交易機器人 Web 界面",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 設置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # 前端開發服務器
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 靜態文件和模板
app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")

# WebSocket 管理器
websocket_manager = WebSocketManager()

# 安全設置
security = HTTPBearer()

# 包含 API 路由
app.include_router(api_router, prefix="/api/v1")

@app.get("/", response_class=HTMLResponse)
async def read_root(request):
    """主頁面"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    """健康檢查端點"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 端點用於實時數據推送"""
    await websocket_manager.connect(websocket)
    try:
        while True:
            # 接收客戶端消息
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # 處理訂閱請求
            if message.get("type") == "subscribe":
                channels = message.get("channels", [])
                await websocket_manager.subscribe(websocket, channels)
                await websocket.send_text(json.dumps({
                    "type": "subscription_confirmed",
                    "channels": channels
                }))
            
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        websocket_manager.disconnect(websocket)

@app.on_event("startup")
async def startup_event():
    """應用啟動時的初始化"""
    logger.info("交易系統 Web 服務器啟動中...")
    
    # 確保必要的目錄存在
    os.makedirs("web/static", exist_ok=True)
    os.makedirs("web/templates", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    
    logger.info("Web 服務器啟動完成")

@app.on_event("shutdown")
async def shutdown_event():
    """應用關閉時的清理"""
    logger.info("Web 服務器正在關閉...")
    await websocket_manager.disconnect_all()

if __name__ == "__main__":
    uvicorn.run(
        "web.app:app",
        host="127.0.0.1",
        port=8080,
        reload=True,
        log_level="info"
    )
