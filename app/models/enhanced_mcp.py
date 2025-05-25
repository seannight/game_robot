#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
竞赛智能客服系统 - 增强型MCP引擎
专门针对竞赛领域问题生成更精确答案
"""

import os
import time
import json
import logging
import asyncio
from typing import Dict, List, Any, Tuple, Optional

from app.models.enhanced_rag import EnhancedRAG
from app.models.MCPWithContext import MCPWithContext
from app.config import settings

logger = logging.getLogger(__name__)

class EnhancedMCP:
    """增强型MCP引擎，专注于竞赛领域问题回答"""
    
    def __init__(self, rebuild_index: bool = False):
        """
        初始化增强型MCP引擎
        
        Args:
            rebuild_index: 是否重建索引
        """
        # 初始化RAG引擎和MCP引擎
        self.rag_engine = EnhancedRAG(rebuild_index=rebuild_index)
        self.mcp_engine = MCPWithContext()
        
        # 竞赛类型映射
        self.competition_mapping = self.rag_engine.competition_mapping
        
        # 答案生成配置
        self.max_context_length = 4000  # MCP上下文最大长度
        self.min_search_results = 3     # 最少检索结果数量
        self.competition_confidence_threshold = 0.6  # 竞赛类型置信度阈值
        
        logger.info(f"增强型MCP引擎初始化完成")
    
    async def query(self, question: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        处理用户问题并生成回答
        
        Args:
            question: 用户问题
            session_id: 会话ID
            
        Returns:
            包含回答和元数据的字典
        """
        start_time = time.time()
        logger.info(f"EnhancedMCP.query: 开始处理问题: '{question}', session_id: '{session_id}'")
        
        try:
            logger.info(f"EnhancedMCP.query: 详细记录 - 原始问题: '{question}'")
            
            # 1. 使用RAG检索相关上下文
            docs = await self.rag_engine.search(question, top_n=5)
            
            # 获取竞赛类型和问题类型识别结果
            identified_comp_type, comp_confidence = self.rag_engine.identify_competition_type(question)
            question_type_identified, _ = self.rag_engine.identify_question_type(question)

            logger.info(f"EnhancedMCP.query: RAG识别到竞赛类型: '{identified_comp_type}', 置信度: {comp_confidence:.2f}")
            logger.info(f"EnhancedMCP.query: RAG识别到问题类型: '{question_type_identified}'")

            competition_type_for_prompt = "未知竞赛"
            if docs:
                logger.info(f"EnhancedMCP.query: RAG检索到 {len(docs)} 个文档片段. 最高分文档来源: {docs[0]['source']}, 竞赛类型: {docs[0]['competition_type']}")
                if identified_comp_type and comp_confidence > 0.85 and docs[0]["competition_type"] == identified_comp_type:
                    competition_type_for_prompt = identified_comp_type
                elif docs[0]["competition_type"]:
                    competition_type_for_prompt = docs[0]["competition_type"]
            else:
                logger.warning("EnhancedMCP.query: RAG未检索到任何文档.")

            # 2. 使用超聚焦提示策略
            if identified_comp_type and comp_confidence > 0.85 and competition_type_for_prompt == identified_comp_type:
                logger.info(f"EnhancedMCP.query: 使用针对'{identified_comp_type}'的超聚焦提示.")
            else:
                logger.info(f"EnhancedMCP.query: 使用通用提示 (上下文主要关于: '{competition_type_for_prompt}').")

            # 3. 调用MCP引擎生成回答
            mcp_response = await self.mcp_engine.query(question, docs)
            answer = mcp_response.get("answer", "未能生成回答。")
            model_confidence = mcp_response.get("confidence", 0.5)
            
            logger.info(f"EnhancedMCP.query: MCP生成回答: '{answer[:200]}...', 模型置信度: {model_confidence:.2f}")

            # 4. 答案质量验证和置信度调整
            final_confidence = model_confidence
            if not docs:
                final_confidence = max(0.1, model_confidence * 0.5)
                if "无法回答" not in answer and "不确定" not in answer and "信息不足" not in answer:
                    answer = f"抱歉，我目前没有关于'{question}'的足够信息来直接回答。您可以尝试更具体地说明您感兴趣的竞赛方面吗？"
            elif "无法回答" in answer or "不确定" in answer or "信息不足" in answer or "没有找到相关信息" in answer:
                final_confidence = max(0.2, model_confidence * 0.6)
            
            # 如果是高置信度聚焦，但答案仍然泛泛，需要进一步处理
            if identified_comp_type and comp_confidence > 0.85 and competition_type_for_prompt == identified_comp_type:
                if identified_comp_type.lower() not in answer.lower() and not ("无法回答" in answer or "不确定" in answer):
                    logger.warning(f"EnhancedMCP.query: 聚焦于 '{identified_comp_type}' 但答案 '{answer[:100]}...' 未明确提及。可能需要重新提示或调整策略.")
                    final_confidence *= 0.7 

            processing_time = time.time() - start_time
            logger.info(f"EnhancedMCP.query: 问题处理完成. 最终置信度: {final_confidence:.2f}, 耗时: {processing_time:.2f} 秒")
            
            return {
                "answer": answer,
                "confidence": final_confidence,
                "sources": [doc["source"] for doc in docs][:3],
                "competition_type": identified_comp_type if identified_comp_type else competition_type_for_prompt,
                "question_type": question_type_identified,
                "processing_time": round(processing_time, 2)
            }

        except Exception as e:
            logger.error(f"EnhancedMCP处理问题 '{question}' 时出错: {str(e)}", exc_info=True)
            processing_time = time.time() - start_time
            return {
                "answer": "抱歉，处理您的问题时发生了内部错误。",
                "confidence": 0.0,
                "sources": [],
                "competition_type": "未知",
                "question_type": "未知",
                "processing_time": round(processing_time, 2)
            }
    
    def _build_context_from_docs(self, docs: List[Dict[str, Any]], 
                                question: str, 
                                competition_type: Optional[str], 
                                question_type: Optional[str]) -> str:
        """
        从检索结果构建MCP上下文
        
        Args:
            docs: 检索到的文档列表
            question: 用户问题
            competition_type: 识别到的竞赛类型
            question_type: 识别到的问题类型
            
        Returns:
            构建好的上下文字符串
        """
        logger.debug(f"EnhancedMCP._build_context_from_docs: 开始构建上下文，源文档数: {len(docs)}")
        # 限制使用的文档数量，避免上下文过长
        relevant_docs = docs[:settings.ENHANCED_MCP_MAX_CONTEXT_DOCS]  # 使用配置值
        logger.debug(f"EnhancedMCP._build_context_from_docs: 将使用 {len(relevant_docs)} 个文档构建上下文 (上限: {settings.ENHANCED_MCP_MAX_CONTEXT_DOCS})")
        
        # 构建上下文头部
        context_parts = []
        
        # 添加竞赛类型和问题类型信息
        if competition_type:
            context_parts.append(f"竞赛类型: {competition_type}")
        if question_type:
            context_parts.append(f"问题类型: {question_type}")
        
        # 添加检索到的文档内容
        context_parts.append("以下是相关竞赛文档内容:")
        
        for i, doc in enumerate(relevant_docs):
            doc_header = f"\n--- 文档 {i+1} (来源: {doc['source']}, 相关度: {doc['score']:.2f}) ---"
            context_parts.append(doc_header)
            
            # 如果文档过长，截取前部分
            content = doc["content"]
            if len(content) > 800:  # 限制每个文档的长度
                content = content[:800] + "..."
            context_parts.append(content)
        
        # 添加回答指导
        prompt_instructions = f"""
请严格根据以下提供的关于'{competition_type if competition_type else "竞赛一般信息"}'的文档内容，回答用户的问题：'{question}'。
你的回答应满足以下要求:
1. **精确性**: 完全基于提供的文档信息回答，禁止使用任何外部知识或个人推断。
2. **相关性**: 直接针对用户问题的核心要点进行回答，避免无关信息。
3. **简洁性**: 回答应简洁明了，突出重点。
4. **完整性**: 如果文档中包含多个相关方面，请综合后回答。
5. **忠实性**: 如果文档内容不足以回答问题，或者问题超出文档范围，请明确说明"根据提供的文档，我无法找到关于您问题的具体信息"，不要猜测或编造。
6. **特定信息优先**: 如果问题明确指向特定竞赛的特定方面（例如"XX竞赛的报名要求"），请优先使用最匹配该竞赛和该方面信息的文档片段。
7. **不要重复问题**：在你的回答中不要复述用户的问题。
"""
        context_parts.append(prompt_instructions)
        logger.debug(f"EnhancedMCP._build_context_from_docs: 添加的指令提示: \n{prompt_instructions}")
        
        # 组合上下文，并确保不超过最大长度
        full_context = "\n\n".join(context_parts)
        if len(full_context) > self.max_context_length:
            # 如果超过最大长度，截断中间文档内容
            logger.warning(f"上下文长度({len(full_context)})超过最大限制({self.max_context_length})，进行截断")
            header = "\n\n".join(context_parts[:2])  # 保留竞赛类型和问题类型
            footer = "\n\n".join(context_parts[-1:])  # 保留回答指导
            
            # 计算中间文档可用的长度
            available_length = self.max_context_length - len(header) - len(footer) - 100  # 留出一些余量
            
            # 重新分配每个文档的长度配额
            doc_parts = []
            for i, doc in enumerate(relevant_docs):
                doc_header = f"\n--- 文档 {i+1} (来源: {doc['source']}, 相关度: {doc['score']:.2f}) ---"
                
                # 分配长度配额，重要性随序号递减
                doc_quota = available_length * (0.5 ** i)  # 第一个文档获得一半配额，依次减半
                
                content = doc["content"]
                if len(content) > doc_quota:
                    content = content[:int(doc_quota)] + "..."
                
                doc_parts.append(doc_header + "\n" + content)
            
            # 重新组装上下文
            docs_content = "\n\n".join(doc_parts)
            full_context = f"{header}\n\n{docs_content}\n\n{footer}"
            
            # 最终检查长度并在必要时截断
            if len(full_context) > self.max_context_length:
                full_context = full_context[:self.max_context_length - 3] + "..."
        
        return full_context
    
    def _verify_answer_quality(self, 
                              answer: str, 
                              confidence: float, 
                              question: str,
                              competition_type: Optional[str],
                              question_type: Optional[str]) -> Tuple[str, float]:
        """
        验证答案质量，处理低质量回答
        
        Args:
            answer: 原始回答
            confidence: 原始置信度
            question: 用户问题
            competition_type: 竞赛类型
            question_type: 问题类型
            
        Returns:
            (处理后的回答, 调整后的置信度)
        """
        logger.debug(f"EnhancedMCP._verify_answer_quality: 开始验证答案. 原始回答(前50字): '{answer[:50]}...', 原始置信度: {confidence:.2f}")
        # 如果答案为空，返回无法回答
        if not answer or answer.strip() == "":
            return "抱歉，无法回答这个问题。请尝试更明确地描述您想了解的竞赛信息。", 0.1
        
        # 检查是否含有拒绝回答的模式
        rejection_patterns = [
            "无法回答", "没有相关信息", "没有足够信息", "无法提供", 
            "文档中没有", "没有提到", "无法确定", "无法找到"
        ]
        
        is_rejection = False
        for pattern in rejection_patterns:
            if pattern in answer:
                is_rejection = True
                break
        
        # 如果是拒绝回答，但识别到了特定竞赛类型，可能是检索问题
        if is_rejection and competition_type and question_type:
            adjusted_confidence = 0.2
            
            # 为特定竞赛和问题类型构建引导性回答
            if question_type == "竞赛介绍":
                suggestion = f"您可以尝试询问'{competition_type}的基本信息是什么'或'什么是{competition_type}'。"
            elif question_type == "报名要求":
                suggestion = f"您可以尝试询问'{competition_type}的参赛条件是什么'或'{competition_type}如何报名'。"
            elif question_type == "评分标准":
                suggestion = f"您可以尝试询问'{competition_type}的评分标准是什么'或'{competition_type}如何评分'。"
            elif question_type == "奖项设置":
                suggestion = f"您可以尝试询问'{competition_type}的奖项设置'或'{competition_type}有哪些奖励'。"
            else:
                suggestion = f"您可以尝试以不同方式询问关于{competition_type}的信息。"
            
            # 构建更友好的拒绝回答
            logger.debug(f"EnhancedMCP._verify_answer_quality: competition_type={repr(competition_type)}, question={repr(question)}, suggestion={repr(suggestion)}")
            friendly_rejection = f"抱歉，根据我目前掌握的关于'{competition_type}'的知识，我无法直接回答您关于'{question}'的问题。{suggestion}"
            logger.debug(f"EnhancedMCP._verify_answer_quality: 构建了引导性拒绝回答: '{friendly_rejection}'")
            return friendly_rejection, adjusted_confidence
        
        # 如果是普通回答，检查其质量
        if len(answer) < 10:  # 回答过短
            confidence *= 0.7  # 降低置信度
        
        if "根据提供的文档" in answer or "根据上述文档" in answer:
            # 去除模板术语
            answer = answer.replace("根据提供的文档，", "")
            answer = answer.replace("根据上述文档，", "")
            answer = answer.replace("根据文档内容，", "")
        
        # 如果置信度过低但回答看起来合理，适当提高置信度
        if confidence < 0.3 and len(answer) > 50 and not is_rejection:
            confidence = 0.4  # 设置最低有效置信度
        
        return answer, confidence
    
    async def diagnose(self) -> Dict[str, Any]:
        """返回引擎诊断信息"""
        # 获取RAG引擎诊断信息
        rag_info = await self.rag_engine.diagnose()
        
        # 组合诊断信息
        result = {
            "rag_engine": rag_info,
            "mcp_engine": {
                "max_context_length": self.max_context_length,
                "min_search_results": self.min_search_results,
                "competition_confidence_threshold": self.competition_confidence_threshold
            },
            "status": "ready"
        }
        
        return result 