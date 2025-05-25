#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
竞赛智能客服系统 - 查询路由器
根据问题类型选择合适的处理引擎
"""

import time
import logging
from typing import Dict, Any, List, Optional

from app.models.structured_kb import StructuredCompetitionKB
from app.models.SimpleMCPWithRAG import SimpleMCPWithRAG
from app.models.enhanced_mcp import EnhancedMCP

logger = logging.getLogger(__name__)

class QueryRouter:
    """查询路由器，决定使用哪个引擎处理问题"""
    
    def __init__(self):
        """初始化查询路由器及其引擎组件"""
        # 标准引擎 - 处理一般问题
        self.standard_engine = SimpleMCPWithRAG()
        
        # 增强引擎 - 处理特定竞赛问题
        self.enhanced_engine = EnhancedMCP(rebuild_index=False)
        
        # 结构化知识库 - 处理明确的竞赛信息查询
        self.structured_kb = None
        try:
            from app.config import settings
            self.structured_kb = StructuredCompetitionKB(settings.KNOWLEDGE_BASE_PATH)
            logger.info("结构化知识库加载成功")
        except Exception as e:
            logger.warning(f"结构化知识库加载失败: {str(e)}，将使用RAG引擎")
        
        logger.info("查询路由器初始化完成")
    
    async def route_query(self, question: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        路由并处理用户查询
        
        Args:
            question: 用户问题
            session_id: 会话ID
            
        Returns:
            包含回答和元数据的字典
        """
        start_time = time.time()
        logger.info(f"开始路由问题: '{question}'")
        
        try:
            # 1. 尝试结构化查询
            if self.structured_kb:
                # 分析问题，识别竞赛类型和信息类型
                competition_type = self.structured_kb.get_competition_type(question)
                info_type = self.structured_kb.get_info_type(question)
                
                if competition_type and info_type:
                    # 尝试从结构化知识库获取精确答案
                    result = self.structured_kb.query(competition_type, info_type)
                    if result:
                        logger.info(f"结构化知识库返回答案，竞赛: {competition_type}, 类型: {info_type}")
                        # 添加处理时间
                        result["processing_time"] = time.time() - start_time
                        return result
            
            # 2. 判断是否为特定竞赛的问题
            # 检测问题中是否包含特定竞赛关键词
            competition_keyword_candidates = [
                "泰迪杯", "3D编程", "编程创作", "机器人", "极地资源", "竞技",
                "鸿蒙", "人工智能", "三维程序", "生成式", "太空", "虚拟仿真",
                "数据采集", "智能芯片", "计算思维", "专项赛"
            ]
            
            contains_competition_keyword = False
            for keyword in competition_keyword_candidates:
                if keyword in question:
                    contains_competition_keyword = True
                    break
            
            # 3. 路由到合适引擎
            if contains_competition_keyword:
                # 使用增强引擎处理特定竞赛问题
                logger.info(f"路由至增强引擎: 问题包含竞赛关键词")
                result = await self.enhanced_engine.query(question, session_id)
            else:
                # 使用标准引擎处理一般问题
                logger.info(f"路由至标准引擎: 一般问题")
                result = await self.standard_engine.query(question=question, session_id=session_id)
            
            # 4. 标准化返回结果
            if not isinstance(result, dict):
                logger.warning(f"引擎返回了非字典类型: {type(result)}")
                # 转换为标准格式
                if isinstance(result, tuple) and len(result) >= 2:
                    result = {
                        "answer": result[0],
                        "confidence": result[1]
                    }
                else:
                    result = {
                        "answer": str(result) if result else "无法回答您的问题",
                        "confidence": 0.3
                    }
            
            # 确保包含处理时间
            if "processing_time" not in result:
                result["processing_time"] = time.time() - start_time
            
            logger.info(f"路由完成，返回答案，置信度: {result.get('confidence', 0.0):.2f}, 耗时: {result['processing_time']:.2f}秒")
            return result
            
        except Exception as e:
            logger.error(f"路由问题时出错: {str(e)}", exc_info=True)
            processing_time = time.time() - start_time
            
            return {
                "answer": "抱歉，系统处理您的问题时出现错误，请稍后再试。",
                "confidence": 0.1,
                "error": str(e),
                "processing_time": processing_time
            }
    
    def diagnose(self) -> Dict[str, Any]:
        """返回查询路由器诊断信息"""
        result = {
            "structured_kb_status": "可用" if self.structured_kb else "未配置",
            "standard_engine_status": "可用" if self.standard_engine else "未配置",
            "enhanced_engine_status": "可用" if self.enhanced_engine else "未配置"
        }
        
        # 获取结构化知识库诊断信息
        if hasattr(self.structured_kb, "diagnose"):
            result["structured_kb_info"] = self.structured_kb.diagnose()
        
        # 获取标准引擎诊断信息
        if hasattr(self.standard_engine, "diagnose"):
            result["standard_engine_info"] = self.standard_engine.diagnose()
        
        # 获取增强引擎诊断信息
        if hasattr(self.enhanced_engine, "diagnose"):
            result["enhanced_engine_info"] = self.enhanced_engine.diagnose()
        
        return result 