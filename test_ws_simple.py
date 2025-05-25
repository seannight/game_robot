#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单WebSocket测试脚本
测试WebSocket连接和消息处理
"""

import asyncio
import websockets
import json
import logging
import sys
import time

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

async def test_websocket():
    """测试WebSocket连接和消息处理"""
    uri = "ws://localhost:53085/ws_test"
    
    try:
        logger.info(f"尝试连接到WebSocket测试端点: {uri}")
        # 设置更宽松的超时时间
        async with websockets.connect(uri, ping_timeout=60, close_timeout=60) as websocket:
            logger.info("WebSocket连接成功!")
            
            # 接收欢迎消息
            response = await websocket.recv()
            logger.info(f"收到欢迎消息: {response}")
            
            # 发送测试消息
            test_message = "Hello, WebSocket!"
            logger.info(f"发送测试消息: {test_message}")
            await websocket.send(test_message)
            
            # 接收回应
            response = await websocket.recv()
            response_data = json.loads(response)
            logger.info(f"收到回应: {response_data}")
            
            return True, "WebSocket测试成功!"
    
    except Exception as e:
        logger.error(f"WebSocket测试失败: {str(e)}", exc_info=True)
        return False, f"WebSocket测试失败: {str(e)}"

async def test_main_websocket():
    """测试主WebSocket连接和问答功能"""
    uri = "ws://localhost:53085/ws"
    
    try:
        logger.info(f"尝试连接到主WebSocket端点: {uri}")
        # 设置更宽松的超时时间
        async with websockets.connect(uri, ping_timeout=60, close_timeout=60) as websocket:
            logger.info("WebSocket连接成功!")
            
            # 初始化会话
            session_id = f"test_session_{int(time.time())}"
            init_message = {
                "action": "init",
                "session_id": session_id
            }
            logger.info(f"发送初始化消息: {init_message}")
            await websocket.send(json.dumps(init_message))
            
            # 接收初始化确认
            response = await websocket.recv()
            logger.info(f"收到初始化响应: {response}")
            
            # 测试简单问题
            test_question = "泰迪杯是什么比赛?"
            question_message = {
                "text": test_question,
                "session_id": session_id
            }
            
            logger.info(f"发送测试问题: {test_question}")
            await websocket.send(json.dumps(question_message))
            
            # 接收回答
            response = await websocket.recv()
            response_data = json.loads(response)
            logger.info(f"收到回答: {response_data.get('answer', '')[:100]}...")
            logger.info(f"置信度: {response_data.get('confidence', 'N/A')}")
            
            return True, "主WebSocket测试成功!"
    
    except Exception as e:
        logger.error(f"主WebSocket测试失败: {str(e)}", exc_info=True)
        return False, f"主WebSocket测试失败: {str(e)}"

async def main():
    """主函数"""
    logger.info("开始简单WebSocket测试...")
    
    # 测试WebSocket测试端点
    success1, message1 = await test_websocket()
    
    # 测试主WebSocket端点
    success2, message2 = await test_main_websocket()
    
    if success1 and success2:
        logger.info(f"测试结果: 所有测试成功!")
        return 0
    else:
        if not success1:
            logger.error(f"测试端点测试结果: {message1}")
        if not success2:
            logger.error(f"主端点测试结果: {message2}")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
        sys.exit(130) 