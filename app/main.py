"""
竞赛智能客服系统 - 主应用文件 (仅WebSocket版本)
提供Web界面和WebSocket接口，支持竞赛智能问答
"""

import os
import logging
import json
import time
import asyncio
from typing import Dict, List, Any, Optional
import uuid
from datetime import datetime
import sys

# --- 日志配置（在所有其他应用代码之前） ---
from app.config import settings as config, normalize_path

# 确保日志目录存在
log_dir = os.path.dirname(config.LOG_FILE)
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format=config.LOG_FORMAT,
    handlers=[
        logging.FileHandler(config.LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout) 
    ],
    force=True
)

logger = logging.getLogger(__name__)
logger.debug(f"app/main.py 模块加载：日志系统已配置为 DEBUG 级别。LOG_FILE: {config.LOG_FILE}")
# --- 日志配置结束 ---

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

# 导入核心模型
from app.models.SimpleMCPWithRAG import SimpleMCPWithRAG
from app.models.structured_kb import StructuredCompetitionKB
from app.models.query_router import QueryRouter

# 导入工具函数
from app.utils.question_enhancer import enhance_question
from app.utils.response_formatter import standardize_response, format_error_response

# 创建FastAPI应用
app = FastAPI(
    title="竞赛智能客服系统",
    description="基于WebSocket的竞赛问答服务",
    version="5.0.0"
)

# 添加CORS中间件（为WebSocket支持）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
app.mount("/static", StaticFiles(directory=normalize_path("app/static")), name="static")

# 设置模板
templates = Jinja2Templates(directory=normalize_path("app/templates"))

# 全局变量
qa_engine = None
active_sessions = {}

@app.get("/", response_class=HTMLResponse)
async def get_home(request: Request):
    """获取首页"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    主要WebSocket端点，支持实时问答
    """
    session_id = f"ws_{uuid.uuid4().hex}"
    
    try:
        await websocket.accept()
        logger.info(f"🔗 新WebSocket连接已建立: {session_id}")
        
        # 发送连接成功消息
        await websocket.send_json({
            "type": "connection_established",
            "status": "connected",
            "session_id": session_id,
            "timestamp": time.time(),
            "message": "连接成功，可以开始提问了！"
        })
        
        active_sessions[session_id] = {
            "connected_at": time.time(),
            "last_activity": time.time(),
            "questions_count": 0
        }
        
        while True:
            try:
                # 接收消息
                data = await websocket.receive_json()
                start_time = time.time()
                
                logger.debug(f"[WebSocket问答] 收到数据: {data}")
                
                # 处理初始化消息
                if data.get("action") == "init" and "session_id" in data:
                    session_id = data["session_id"]
                    logger.info(f"[WebSocket问答] 会话ID已更新: {session_id}")
                    await websocket.send_json({
                        "type": "init_ack",
                        "session_id": session_id,
                        "status": "connected",
                        "timestamp": time.time()
                    })
                    continue
                
                # 处理心跳消息
                if data.get("action") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": time.time(),
                        "session_id": session_id
                    })
                    continue
                
                # 获取问题文本
                question = data.get("text", "").strip()
                if not question:
                    logger.warning(f"[WebSocket问答] 收到空问题: {data}")
                    await websocket.send_json({
                        "type": "error",
                        "message": "请输入有效的问题",
                        "session_id": session_id,
                        "timestamp": time.time()
                    })
                    continue
                
                # 更新会话统计
                if session_id in active_sessions:
                    active_sessions[session_id]["last_activity"] = time.time()
                    active_sessions[session_id]["questions_count"] += 1
                
                logger.info(f"[WebSocket问答] 📝 收到问题: '{question}' (会话: {session_id})")
                logger.debug(f"[WebSocket问答] 请求时间戳: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}")
                
                # 发送处理中状态
                await websocket.send_json({
                    "type": "processing",
                    "message": "正在处理您的问题...",
                    "session_id": session_id,
                    "timestamp": time.time()
                })
                
                # 问题增强处理
                logger.debug(f"[WebSocket问答] 🔧 开始问题增强处理...")
                try:
                    enhanced_question = enhance_question(question)
                    logger.debug(f"[WebSocket问答] 增强后问题: {enhanced_question}")
                    question = enhanced_question
                except Exception as e:
                    logger.error(f"[WebSocket问答] 问题增强失败: {str(e)}")
                    logger.debug(f"[WebSocket问答] 使用原始问题继续处理")
                
                # 使用QA引擎处理问题
                logger.debug(f"[WebSocket问答] 🤖 开始调用QA引擎处理问题...")
                try:
                    result = await asyncio.wait_for(
                        qa_engine.route_query(question=question, session_id=session_id),
                        timeout=15.0
                    )
                    logger.debug(f"[WebSocket问答] QA引擎返回结果: {result}")
                except asyncio.TimeoutError:
                    logger.error(f"[WebSocket问答] ⏰ 问题处理超时 (>15秒)，会话: {session_id}")
                    await websocket.send_json({
                        "type": "answer",
                        "answer": "处理您的问题时间过长，请尝试简化问题或稍后再试。",
                        "confidence": 0.3,
                        "session_id": session_id,
                        "processing_time": 15.0,
                        "timestamp": time.time(),
                        "source": "timeout",
                        "error": "处理超时"
                    })
                    continue
                
                # 格式化响应
                logger.debug(f"[WebSocket问答] 📝 开始响应格式化...")
                response = standardize_response(result, session_id, start_time)
                response["type"] = "answer"  # 标记为答案类型
                
                processing_time = response.get('processing_time', 'N/A')
                confidence = response.get('confidence', 'N/A')
                answer_length = len(str(response.get('answer', '')))
                
                logger.info(f"[WebSocket问答] ✅ 问题处理完成，置信度: {confidence}, 耗时: {processing_time}秒, 答案长度: {answer_length}字符")
                logger.debug(f"[WebSocket问答] 完整响应数据: {response}")
                
                # 发送答案
                await websocket.send_json(response)
                
            except WebSocketDisconnect:
                logger.info(f"[WebSocket问答] 🔌 客户端断开连接: {session_id}")
                break
            except json.JSONDecodeError as json_err:
                logger.error(f"[WebSocket问答] JSON解析错误: {str(json_err)}")
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": "接收到非法JSON格式数据，请发送有效的JSON数据",
                        "session_id": session_id,
                        "timestamp": time.time()
                    })
                except Exception:
                    break
            except Exception as e:
                logger.error(f"[WebSocket问答] 处理消息时出错: {str(e)}", exc_info=True)
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"处理过程中出现错误: {str(e)}",
                        "session_id": session_id,
                        "timestamp": time.time()
                    })
                except Exception:
                    break
    except Exception as e:
        logger.error(f"[WebSocket问答] WebSocket处理过程中出错: {str(e)}", exc_info=True)
    finally:
        # 清理会话
        if session_id in active_sessions:
            session_info = active_sessions[session_id]
            duration = time.time() - session_info["connected_at"]
            questions_count = session_info["questions_count"]
            logger.info(f"[WebSocket问答] 🏁 会话结束: {session_id}, 持续时间: {duration:.1f}秒, 处理问题数: {questions_count}")
            del active_sessions[session_id]
        else:
            logger.info(f"[WebSocket问答] 🔌 WebSocket连接已关闭: {session_id}")

@app.websocket("/ws_test")
async def websocket_test(websocket: WebSocket):
    """
    简单WebSocket测试端点
    """
    test_session_id = f"test_{uuid.uuid4().hex}"
    
    try:
        await websocket.accept()
        logger.info(f"🧪 WebSocket测试连接已建立: {test_session_id}")
        
        await websocket.send_json({
            "type": "test_welcome",
            "message": "欢迎使用WebSocket测试接口",
            "status": "connected",
            "session_id": test_session_id,
            "timestamp": time.time()
        })
        
        while True:
            try:
                data = await websocket.receive_text()
                logger.info(f"🧪 WebSocket测试收到消息: {data}")
                
                response = {
                    "type": "test_echo",
                    "echo": data,
                    "timestamp": time.time(),
                    "session_id": test_session_id,
                    "message": f"收到您的消息: {data}"
                }
                
                await websocket.send_json(response)
            except WebSocketDisconnect:
                logger.info(f"🧪 WebSocket测试客户端断开连接: {test_session_id}")
                break
            except Exception as e:
                logger.error(f"🧪 WebSocket测试接收消息时出错: {str(e)}")
                break
    except Exception as e:
        logger.error(f"🧪 WebSocket测试处理过程中出错: {str(e)}")
    finally:
        logger.info(f"🧪 WebSocket测试连接已关闭: {test_session_id}")

@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    global qa_engine
    
    try:
        logger.info("🚀 FastAPI startup_event: 尝试进行应用初始化...")
        
        # 初始化目录
        os.makedirs(normalize_path("logs"), exist_ok=True)
        os.makedirs(normalize_path("data/sessions"), exist_ok=True)
        
        # 根据配置选择QA引擎
        try:
            # 尝试使用双引擎系统
            logger.info("🔄 尝试初始化双引擎查询系统...")
            qa_engine = QueryRouter()
            logger.info("✅ 使用双引擎问答系统(结构化知识库 + 语义搜索)")
        except Exception as e:
            logger.warning(f"⚠️ 双引擎初始化失败: {e}")
            logger.info("🔄 降级到SimpleMCPWithRAG引擎...")
            qa_engine = SimpleMCPWithRAG()
            logger.info("✅ 使用SimpleMCPWithRAG引擎")
        
        logger.info(f"🎯 系统启动完成 - 版本: {config.VERSION}")
        logger.info(f"🌐 WebSocket服务运行在: ws://localhost:{config.API_PORT}/ws")
        logger.info(f"🏠 Web界面访问: http://localhost:{config.API_PORT}")
        logger.info(f"📚 知识库路径: {config.KNOWLEDGE_BASE_PATH}")
        
    except Exception as e:
        logger.error(f"❌ 应用初始化失败: {str(e)}", exc_info=True)
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("🛑 系统正在关闭...")
    
    # 通知所有活跃的WebSocket连接
    logger.info(f"📊 当前活跃会话数: {len(active_sessions)}")
    active_sessions.clear()
    
    logger.info("✅ 系统关闭完成")

if __name__ == "__main__":
    import uvicorn
    
    logger.info("🚀 启动竞赛智能客服系统...")
    logger.info("📋 系统特性:")
    logger.info("  - 仅使用WebSocket通信")
    logger.info("  - 双引擎问答系统")
    logger.info("  - 实时DEBUG日志")
    logger.info("  - 16个竞赛类型支持")
    
    uvicorn.run(
        "app.main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=True,
        log_level="info"
    )