#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
竞赛智能客服系统 - 增强型RAG实现
多级联合检索策略，解决特定竞赛信息检索不足问题
"""

import os
import re
import logging
import json
import math
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Set
from collections import defaultdict

# 导入jieba帮助模块
from app.utils.jieba_helper import jieba, pseg
from app.config import settings

logger = logging.getLogger(__name__)

class EnhancedRAG:
    """增强型RAG引擎，使用多级联合检索策略"""
    
    def __init__(self, rebuild_index: bool = False):
        """
        初始化增强型RAG引擎
        
        Args:
            rebuild_index: 是否重建索引
        """
        self.knowledge_path = settings.KNOWLEDGE_BASE_PATH
        self.txt_path = settings.TXT_PATH
        self.index_file = os.path.join(settings.INDEX_PATH, "enhanced_index.json")
        
        # 检索参数
        self.chunk_size = 1500  # 文档块大小
        self.chunk_overlap = 200  # 块重叠大小
        self.score_threshold = 0.02  # 相关性阈值，降低以增加召回率
        
        # 竞赛信息表 - 建立竞赛标准名称与别名的映射
        self.competition_mapping = self._build_competition_mapping()
        self.competition_keywords = {}  # 每个竞赛的关键词
        
        # 竞赛信息类型（用于问题分类）
        self.info_categories = {
            "竞赛介绍": ["什么是", "介绍", "简介", "概述", "背景", "内容", "是什么", "关于"],
            "报名要求": ["报名", "要求", "条件", "资格", "如何参加", "怎么参加", "参赛条件"],
            "评分标准": ["评分", "标准", "评判", "打分", "评价", "评估", "打分"],
            "奖项设置": ["奖项", "奖励", "奖金", "获奖", "一等奖", "二等奖", "三等奖"],
            "时间安排": ["时间", "日期", "截止", "期限", "日程", "何时", "什么时候"],
            "作品提交": ["提交", "作品", "要求", "格式", "材料", "上传", "提交方式"]
        }
        
        # 文档索引
        self.docs = []  # 所有文档块
        self.inverted_index = defaultdict(list)  # 倒排索引：关键词 -> 文档ID列表
        self.competition_docs = defaultdict(list)  # 竞赛类型 -> 文档ID列表
        self.competition_types = set()  # 所有竞赛类型
        
        # 停用词表
        self.stopwords = self._load_stopwords()
        
        # 初始化索引
        if not os.path.exists(self.index_file) or rebuild_index:
            self._build_index()
        else:
            self._load_index()
    
    def _build_competition_mapping(self) -> Dict[str, str]:
        """构建竞赛标准名称与别名的映射"""
        mapping = {
            # 标准竞赛名称及其可能的别名
            "泰迪杯数据挖掘挑战赛": ["泰迪杯", "数据挖掘挑战赛", "泰迪杯挑战赛", "泰迪"],
            "3D编程模型创新设计专项赛": ["3D编程", "3D创新", "3D模型", "3D编程设计", "3D"],
            "编程创作与信息学专项赛": ["编程创作", "信息学", "编程专项赛"],
            "机器人工程设计专项赛": ["机器人工程", "机器人设计", "工程机器人"],
            "极地资源勘探专项赛": ["极地勘探", "极地资源", "资源勘探"],
            "竞技机器人专项赛": ["竞技机器人", "机器人竞技"],
            "开源鸿蒙机器人专项赛": ["开源鸿蒙", "鸿蒙机器人", "鸿蒙专项赛", "开源机器人"],
            "人工智能综合创新专项赛": ["人工智能创新", "AI创新", "人工智能专项赛", "AI综合"],
            "三维程序创意设计专项赛": ["三维程序", "三维创意", "3D程序设计"],
            "生成式人工智能应用专项赛": ["生成式AI", "AIGC", "生成式人工智能", "AI生成"],
            "太空电梯工程设计专项赛": ["太空电梯", "空间电梯", "电梯设计"],
            "太空探索智能机器人专项赛": ["太空探索", "太空机器人", "探索机器人", "太空智能"],
            "虚拟仿真平台创新设计专项赛": ["虚拟仿真", "虚拟平台", "仿真设计"],
            "智能数据采集装置设计专项赛": ["智能数据采集", "数据采集", "智能采集"],
            "智能芯片与计算思维专项赛": ["智能芯片", "计算思维", "芯片设计", "人工智能芯片"]
        }
        
        # 构建反向映射（别名 -> 标准名称）
        reverse_mapping = {}
        for standard, aliases in mapping.items():
            reverse_mapping[standard.lower()] = standard  # 标准名称本身
            for alias in aliases:
                reverse_mapping[alias.lower()] = standard  # 别名映射到标准名称
        
        return reverse_mapping
    
    def _load_stopwords(self) -> Set[str]:
        """加载停用词"""
        stopwords_file = os.path.join(settings.BASE_DIR, "stopwords", "stopwords.txt")
        stopwords = set()
        
        try:
            if os.path.exists(stopwords_file):
                with open(stopwords_file, "r", encoding="utf-8") as f:
                    stopwords = set([line.strip() for line in f if line.strip()])
                logger.info(f"成功加载 {len(stopwords)} 个停用词")
            else:
                # 创建一个基本的停用词表
                stopwords = {"的", "了", "是", "在", "我", "有", "和", "就", "不", "人", "都", 
                           "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", 
                           "会", "着", "没有", "看", "好", "自己", "这"}
                logger.warning(f"停用词文件不存在，使用内置停用词表 ({len(stopwords)}个词)")
        except Exception as e:
            logger.error(f"加载停用词出错: {str(e)}")
            stopwords = {"的", "了", "是", "在", "我", "有", "和", "就", "不"}
        
        return stopwords
    
    def _build_index(self):
        """构建文档索引"""
        logger.info("开始构建增强型文本索引...")
        
        # 确保索引目录存在
        os.makedirs(os.path.dirname(self.index_file), exist_ok=True)
        
        # 1. 扫描所有PDF文件
        pdf_files = []
        for root, _, files in os.walk(self.knowledge_path):
            for file in files:
                if file.endswith(".pdf"):
                    pdf_files.append(os.path.join(root, file))
        
        logger.info(f"发现 {len(pdf_files)} 个PDF文件")
        
        # 2. 预处理所有PDF文件，提取文本并分块
        doc_id = 0
        for pdf_file in pdf_files:
            try:
                # 解析文件名，提取竞赛类型
                filename = os.path.basename(pdf_file)
                competition_type = self._extract_competition_type(filename)
                
                # 如果没有识别到竞赛类型，使用文件名作为备用
                if not competition_type:
                    # 移除数字和特殊字符
                    clean_name = re.sub(r'^\d+_', '', filename)
                    clean_name = re.sub(r'\.pdf$', '', clean_name)
                    competition_type = clean_name
                
                # 获取对应的TXT文件路径
                txt_filename = os.path.splitext(os.path.basename(pdf_file))[0] + ".txt"
                txt_file = os.path.join(self.txt_path, txt_filename)
                
                # 如果TXT文件存在，则读取内容；否则尝试直接从PDF提取（未实现）
                if os.path.exists(txt_file):
                    with open(txt_file, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    # 分块处理文本
                    chunks = self._split_text_into_chunks(content, self.chunk_size, self.chunk_overlap)
                    
                    # 处理每个文本块
                    for chunk in chunks:
                        # 提取关键词
                        keywords = self._extract_keywords(chunk)
                        
                        # 添加到文档集合
                        self.docs.append({
                            "id": doc_id,
                            "content": chunk,
                            "source": filename,
                            "competition_type": competition_type,
                            "keywords": keywords
                        })
                        
                        # 更新倒排索引
                        for keyword in keywords:
                            self.inverted_index[keyword].append(doc_id)
                        
                        # 更新竞赛类型索引
                        self.competition_docs[competition_type].append(doc_id)
                        self.competition_types.add(competition_type)
                        
                        # 更新文档ID
                        doc_id += 1
                else:
                    logger.warning(f"未找到对应的TXT文件: {txt_file}")
            except Exception as e:
                logger.error(f"处理文件 {pdf_file} 时出错: {str(e)}")
        
        # 3. 为每个竞赛类型构建关键词集合
        for comp_type in self.competition_types:
            # 获取该竞赛类型的所有文档
            doc_ids = self.competition_docs[comp_type]
            
            # 提取所有关键词
            all_keywords = []
            for doc_id in doc_ids:
                all_keywords.extend(self.docs[doc_id]["keywords"])
            
            # 统计词频
            keyword_freq = defaultdict(int)
            for keyword in all_keywords:
                keyword_freq[keyword] += 1
            
            # 选择频率最高的关键词作为该竞赛的代表关键词
            sorted_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)
            top_keywords = [k for k, v in sorted_keywords[:10]]
            self.competition_keywords[comp_type] = top_keywords
        
        # 4. 保存索引
        self._save_index()
        
        logger.info(f"索引构建完成，包含 {len(self.docs)} 个文档片段，{len(self.inverted_index)} 个关键词，{len(self.competition_types)} 种竞赛类型")
    
    def _extract_competition_type(self, filename: str) -> Optional[str]:
        """从文件名中提取竞赛类型"""
        # 移除数字前缀和文件扩展名
        clean_name = re.sub(r'^\d+_', '', filename)
        clean_name = re.sub(r'\.pdf$', '', clean_name)
        
        # 在竞赛映射中查找匹配项
        for name_fragment in [clean_name.lower(), *clean_name.lower().split('_')]:
            if name_fragment in self.competition_mapping:
                return self.competition_mapping[name_fragment]
        
        # 如果没有直接匹配，尝试部分匹配
        for alias, standard in self.competition_mapping.items():
            if alias in clean_name.lower():
                return standard
        
        return None
    
    def _split_text_into_chunks(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """将文本分割成重叠的块"""
        if not text:
            return []
        
        # 按段落分割
        paragraphs = [p for p in text.split("\n\n") if p.strip()]
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para_len = len(para)
            
            # 如果段落本身超过块大小，则单独作为一个块
            if para_len > chunk_size:
                # 如果当前块不为空，则先保存当前块
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                    # 保留部分重叠内容
                    overlap_size = 0
                    while current_chunk and overlap_size < chunk_overlap:
                        overlap_size += len(current_chunk[-1])
                        if overlap_size <= chunk_overlap:
                            # 只保留不超过重叠大小的内容
                            current_chunk = [current_chunk[-1]]
                            current_size = len(current_chunk[-1])
                        else:
                            current_chunk = []
                            current_size = 0
                
                # 将大段落分成小块
                para_chunks = []
                for i in range(0, para_len, chunk_size - chunk_overlap):
                    end_idx = min(i + chunk_size, para_len)
                    para_chunks.append(para[i:end_idx])
                
                # 添加除最后一块外的所有块
                for pc in para_chunks[:-1]:
                    chunks.append(pc)
                
                # 将最后一块添加到当前块中
                if para_chunks:
                    current_chunk = [para_chunks[-1]]
                    current_size = len(para_chunks[-1])
            
            # 如果添加当前段落后超过块大小，则保存当前块并开始新块
            elif current_size + para_len > chunk_size:
                chunks.append("\n\n".join(current_chunk))
                
                # 保留部分重叠内容
                overlap_size = 0
                overlap_chunks = []
                for i in range(len(current_chunk) - 1, -1, -1):
                    overlap_size += len(current_chunk[i])
                    if overlap_size <= chunk_overlap:
                        overlap_chunks.insert(0, current_chunk[i])
                    else:
                        break
                
                current_chunk = overlap_chunks
                current_size = sum(len(c) for c in current_chunk)
                
                # 添加当前段落
                current_chunk.append(para)
                current_size += para_len
            
            # 否则，将段落添加到当前块
            else:
                current_chunk.append(para)
                current_size += para_len
        
        # 添加最后一个块
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))
        
        return chunks
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取文本中的关键词"""
        # 使用jieba进行分词
        words = pseg.lcut(text)
        
        # 筛选关键词（保留名词、动词、形容词等，排除停用词）
        keywords = []
        for word, flag in words:
            # 词性筛选：保留名词、动词、形容词、成语等
            if (flag.startswith(('n', 'v', 'a', 'i')) and 
                len(word) > 1 and  # 过滤单字词
                word not in self.stopwords):  # 过滤停用词
                keywords.append(word)
        
        return keywords
    
    def _save_index(self):
        """保存索引到文件"""
        try:
            index_data = {
                "docs": self.docs,
                "inverted_index": {k: v for k, v in self.inverted_index.items()},
                "competition_docs": {k: v for k, v in self.competition_docs.items()},
                "competition_types": list(self.competition_types),
                "competition_keywords": self.competition_keywords
            }
            
            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump(index_data, f, ensure_ascii=False)
            
            logger.info(f"索引文件保存成功: {self.index_file}")
            
        except Exception as e:
            logger.error(f"保存索引文件失败: {str(e)}")
    
    def _load_index(self):
        """从文件加载索引"""
        try:
            with open(self.index_file, "r", encoding="utf-8") as f:
                index_data = json.load(f)
            
            self.docs = index_data["docs"]
            self.inverted_index = defaultdict(list, index_data["inverted_index"])
            self.competition_docs = defaultdict(list, index_data["competition_docs"])
            self.competition_types = set(index_data["competition_types"])
            self.competition_keywords = index_data.get("competition_keywords", {})
            
            logger.info(f"成功加载索引，包含 {len(self.docs)} 个文档，{len(self.inverted_index)} 个关键词")
            
        except Exception as e:
            logger.error(f"加载索引文件失败: {str(e)}")
            # 重建索引
            self._build_index()
    
    def identify_competition_type(self, question: str) -> Tuple[Optional[str], float]:
        """
        识别问题中的竞赛类型
        
        Args:
            question: 用户问题
            
        Returns:
            (竞赛类型, 匹配置信度)
        """
        logger.debug(f"EnhancedRAG.identify_competition_type: 原始问题: '{question}'")
        # 步骤1: 直接匹配完整竞赛名称
        for competition_type in self.competition_types:
            if competition_type in question:
                logger.debug(f"EnhancedRAG.identify_competition_type: 步骤1命中 - 直接匹配完整竞赛名称: '{competition_type}'")
                return competition_type, 1.0
        
        # 步骤2: 寻找标准名称或别名
        question_lower = question.lower()
        for alias, standard in self.competition_mapping.items():
            if alias in question_lower:
                logger.debug(f"EnhancedRAG.identify_competition_type: 步骤2尝试匹配 - 别名 '{alias}' (标准: '{standard}') in question_lower")
                # 确认这个标准名称在我们的索引中
                if standard in self.competition_types:
                    logger.debug(f"EnhancedRAG.identify_competition_type: 步骤2命中 - 别名 '{alias}' 映射到标准名称 '{standard}' (存在于索引中)")
                    return standard, 0.9
                # 标准名称不在索引中，但可能是不同表述
                for comp_type in self.competition_types:
                    if standard in comp_type or comp_type in standard:
                        logger.debug(f"EnhancedRAG.identify_competition_type: 步骤2命中 - 别名 '{alias}' 映射到标准名称 '{standard}', 进一步匹配到索引中的 '{comp_type}'")
                        return comp_type, 0.8
        
        # 步骤3: 尝试关键词匹配
        # 提取问题中的关键词
        question_keywords = self._extract_keywords(question)
        logger.debug(f"EnhancedRAG.identify_competition_type: 步骤3提取的问题关键词: {question_keywords}")
        
        # 计算每个竞赛类型的匹配分数
        scores = {}
        for comp_type, comp_keywords in self.competition_keywords.items():
            # 计算关键词重叠度
            overlap = set(question_keywords) & set(comp_keywords)
            if overlap:
                # 计算匹配分数 (0-1范围)
                score = len(overlap) / len(comp_keywords) if comp_keywords else 0 # Avoid division by zero
                scores[comp_type] = score
                logger.debug(f"EnhancedRAG.identify_competition_type: 步骤3计算分数 - 竞赛: '{comp_type}', 重叠关键词: {overlap}, 分数: {score:.2f}")
        
        # 如果有匹配，返回得分最高的竞赛类型
        if scores:
            best_match = max(scores.items(), key=lambda x: x[1])
            logger.debug(f"EnhancedRAG.identify_competition_type: 步骤3最高匹配 - 竞赛: '{best_match[0]}', 分数: {best_match[1]:.2f}")
            return best_match[0], best_match[1]
        
        logger.debug(f"EnhancedRAG.identify_competition_type: 未匹配到任何竞赛类型")
        # 没有匹配到任何竞赛类型
        return None, 0.0
    
    def identify_question_type(self, question: str) -> Tuple[Optional[str], float]:
        """
        识别问题类型(如介绍、要求、评分标准等)
        
        Args:
            question: 用户问题
            
        Returns:
            (问题类型, 匹配置信度)
        """
        # 计算每个信息类型的匹配分数
        scores = {}
        question_lower = question.lower()
        
        for info_type, keywords in self.info_categories.items():
            matches = []
            for keyword in keywords:
                if keyword in question_lower:
                    matches.append(keyword)
            
            if matches:
                # 计算匹配分数 (0-1范围)，考虑关键词长度
                total_length = sum(len(m) for m in matches)
                max_possible = sum(len(k) for k in keywords[:len(matches)])
                score = min(1.0, total_length / max_possible)
                scores[info_type] = score
        
        # 如果有匹配，返回得分最高的信息类型
        if scores:
            best_match = max(scores.items(), key=lambda x: x[1])
            return best_match[0], best_match[1]
        
        # 默认为"竞赛介绍"，但置信度低
        return "竞赛介绍", 0.3
    
    async def search(self, question: str, **kwargs) -> List[Dict[str, Any]]:
        """
        多级联合检索，根据问题查找相关文档
        
        Args:
            question: 用户问题
            **kwargs: 额外参数
                - top_n: 返回的文档数量
                - score_threshold: 相似度阈值
                - competition_type: 指定竞赛类型
        
        Returns:
            相关文档列表
        """
        start_time = time.time()
        
        # 提取参数
        top_n = kwargs.get("top_n", 10)
        score_threshold = kwargs.get("score_threshold", self.score_threshold)
        specified_competition = kwargs.get("competition_type", None)
        
        logger.info(f"EnhancedRAG.search: 原始问题: '{question}', 参数: top_n={top_n}, threshold={score_threshold}, specified_competition='{specified_competition}'")
        
        try:
            # 1. 识别竞赛类型和问题类型
            competition_type, comp_confidence = self.identify_competition_type(question)
            question_type, q_type_confidence = self.identify_question_type(question)
            
            if specified_competition and specified_competition in self.competition_types:
                logger.info(f"EnhancedRAG.search: 使用了指定的竞赛类型 '{specified_competition}' 覆盖了识别结果 '{competition_type}'")
                competition_type = specified_competition
                comp_confidence = 1.0 # Assume 100% confidence if specified
            
            logger.info(f"EnhancedRAG.search: 识别到竞赛类型: '{competition_type}', 置信度: {comp_confidence:.2f}")
            logger.info(f"EnhancedRAG.search: 识别到问题类型: '{question_type}', 置信度: {q_type_confidence:.2f}")
            
            question_keywords = self._extract_keywords(question)
            logger.info(f"EnhancedRAG.search: 提取的问题关键词: {question_keywords}")
            
            candidate_docs = []
            retrieval_strategy_log = f"Question: '{question}'. Keywords: {question_keywords}. Identified Comp: '{competition_type}' (Conf: {comp_confidence:.2f}). Q_Type: '{question_type}' (Conf: {q_type_confidence:.2f}). "

            # 步骤 3: 多级联合检索策略
            # 3.1 高置信度特定竞赛聚焦检索
            if competition_type and comp_confidence > 0.85:
                logger.info(f"EnhancedRAG.search: 高置信度识别到竞赛 '{competition_type}'. 进行聚焦检索.")
                retrieval_strategy_log += f"Strategy: Focused on '{competition_type}'. "
                doc_ids_for_competition = self.competition_docs.get(competition_type, [])
                
                if doc_ids_for_competition:
                    logger.debug(f"EnhancedRAG.search: '{competition_type}' 有 {len(doc_ids_for_competition)} 个关联文档ID. 将在这些文档中进行关键词匹配。")
                    for doc_id in doc_ids_for_competition:
                        # 此处可以进一步优化，例如只对这些文档进行关键词匹配打分，而不是直接全部加入
                        # 但为了先实现聚焦，我们将它们作为首要候选
                        candidate_docs.append(self.docs[doc_id])
                    retrieval_strategy_log += f"Initial candidates from focused search: {len(candidate_docs)}. "
                else:
                    logger.warning(f"EnhancedRAG.search: 高置信度识别到 '{competition_type}', 但该竞赛无索引文档.")
                    retrieval_strategy_log += f"No documents indexed for '{competition_type}'. "

            # 3.2 通用关键词检索 (如果聚焦检索未执行或结果不足，或补充聚焦结果)
            # 如果candidate_docs 为空 (聚焦检索无结果或未执行聚焦) 或者 数量远少于top_n，则执行或补充通用检索
            # 为简化逻辑，如果执行了聚焦搜索，我们会先基于聚焦结果打分，如果不够再考虑扩大。
            # 这里暂时修改为：如果聚焦搜索已经有候选，则跳过大范围的关键词索引。后续细化。
            
            if not candidate_docs: # 仅当聚焦搜索完全没结果或未触发时，才进行大范围关键词搜索
                logger.info(f"EnhancedRAG.search: 未进行聚焦检索或聚焦检索无结果. 执行通用关键词检索.")
                retrieval_strategy_log += "Strategy: General keyword search. "
                
                potential_docs_by_keyword = defaultdict(list)
                for keyword in question_keywords:
                    doc_ids_for_keyword = self.inverted_index.get(keyword, [])
                    for doc_id in doc_ids_for_keyword:
                        potential_docs_by_keyword[doc_id].append(keyword)
                
                logger.info(f"EnhancedRAG.search: 通用关键词检索发现 {len(potential_docs_by_keyword)} 个潜在文档ID.")
                for doc_id in potential_docs_by_keyword:
                    # 避免重复添加 (虽然在此逻辑分支candidate_docs应为空)
                    if not any(cdoc["id"] == doc_id for cdoc in candidate_docs):
                         candidate_docs.append(self.docs[doc_id])
                retrieval_strategy_log += f"General search candidates: {len(candidate_docs)}. "
            
            # 确保候选文档列表中的文档是唯一的
            unique_candidate_docs = []
            seen_doc_ids = set()
            for doc_content in candidate_docs:
                if doc_content["id"] not in seen_doc_ids:
                    unique_candidate_docs.append(doc_content)
                    seen_doc_ids.add(doc_content["id"])
            candidate_docs = unique_candidate_docs
            
            logger.info(f"EnhancedRAG.search: 总计 {len(candidate_docs)} 个唯一候选文档进入评分阶段. {retrieval_strategy_log}")

            # 4. 计算文档相关性得分 (后续步骤与原先类似，但候选集可能更精确)
            scored_docs = []
            logger.info(f"EnhancedRAG.search: 步骤4 - 开始为 {len(candidate_docs)} 个候选文档计算得分")
            for i, doc in enumerate(candidate_docs):
                keyword_match_score = self._calculate_keyword_match(question_keywords, doc["keywords"])
                type_match_bonus = 1.0
                # 关键：如果原始识别的competition_type与文档的类型严格匹配，且信心高，那么这个加成应该更显著
                if competition_type and doc["competition_type"] == competition_type:
                    type_match_bonus = 1.8 if comp_confidence > 0.85 else (1.5 if comp_confidence > 0.7 else 1.2)
                
                question_type_relevance = 1.0
                if question_type:
                    content_lower = doc["content"].lower()
                    for keyword in self.info_categories.get(question_type, []):
                        if keyword in content_lower:
                            question_type_relevance = 1.3
                            break
                
                text_match_score_bonus = 0.0
                # 避免对非常短的通用问题词语（如"是什么"）给予过高的直接匹配奖励
                if len(question) > 5 and question.lower() in doc["content"].lower():
                    text_match_score_bonus = 0.3
                
                position_bonus = 1.0 # 暂时简化，可以根据文档在竞赛内的排序等调整
                # if doc["id"] < 5 and doc.get("competition_type") == competition_type :
                #     position_bonus = 1.2
                
                final_score = (keyword_match_score * type_match_bonus * 
                               question_type_relevance * position_bonus + text_match_score_bonus)
                
                scored_docs.append({
                    "content": doc["content"],
                    "source": doc["source"],
                    "competition_type": doc["competition_type"],
                    "score": final_score,
                    "original_doc_id": doc["id"]
                })
                if i < 20: # Log score calculation for first 20 docs
                    logger.debug(f"EnhancedRAG.search:  DocID {doc['id']} ({doc['source']}) scoring details:")
                    logger.debug(f"    Scores: keyword_match={keyword_match_score:.2f}, type_bonus={type_match_bonus:.2f} (orig_comp_conf={comp_confidence:.2f}), q_type_relevance={question_type_relevance:.2f}, position_bonus={position_bonus:.2f}, text_match_bonus={text_match_score_bonus:.2f}")
                    logger.debug(f"    Final Score: {final_score:.4f} | Doc Comp: '{doc['competition_type']}' (Query Identified Comp: '{competition_type}')")

            # 5. 排序并过滤结果
            scored_docs.sort(key=lambda x: x["score"], reverse=True)
            
            if scored_docs:
                 logger.info(f"EnhancedRAG.search: 步骤5 - {len(scored_docs)} 个文档已评分和排序. 最高分: {scored_docs[0]['score']:.4f} (ID: {scored_docs[0]['original_doc_id']}, Source: {scored_docs[0]['source']}, Comp: {scored_docs[0]['competition_type']})")
            else:
                logger.info("EnhancedRAG.search: 步骤5 - 没有文档被评分。")


            filtered_docs = [doc for doc in scored_docs if doc["score"] > score_threshold]
            logger.info(f"EnhancedRAG.search: 应用阈值 {score_threshold} 后，剩余 {len(filtered_docs)} 个文档")
            
            if not filtered_docs and scored_docs:
                # 如果是因为阈值过滤掉了所有，但实际上有评分的文档，取top_n或少量作为回退
                # 尤其是当聚焦搜索后，可能好文档分数中等但仍比通用文档好
                num_fallback_docs = min(max(1, top_n // 2), len(scored_docs)) # 取top_n的一半，至少1个
                logger.info(f"EnhancedRAG.search: 过滤后无文档，但有评分文档。将返回得分最高的 {num_fallback_docs} 个文档作为回退。")
                filtered_docs = scored_docs[:num_fallback_docs]
            
            # 6. 返回结果
            result_docs = filtered_docs[:top_n]
            
            logger.info(f"EnhancedRAG.search: 步骤6 - 最终检索到 {len(result_docs)} 个相关文档返回给MCP (top_n={top_n})，耗时: {time.time() - start_time:.2f}秒")
            if result_docs:
                for i, r_doc in enumerate(result_docs):
                    logger.debug(f"EnhancedRAG.search:   ResultDoc[{i}]: ID={r_doc['original_doc_id']}, Score={r_doc['score']:.4f}, Source='{r_doc['source']}', CompType='{r_doc['competition_type']}'")
            else:
                logger.warning(f"EnhancedRAG.search: 未检索到任何满足条件的文档。")
            
            return result_docs
            
        except Exception as e:
            logger.error(f"EnhancedRAG搜索出错: {str(e)}", exc_info=True)
            return []
    
    def _calculate_keyword_match(self, query_keywords: List[str], doc_keywords: List[str]) -> float:
        """计算查询关键词与文档关键词的匹配度"""
        if not query_keywords or not doc_keywords:
            return 0.0
        
        # 计算共同关键词
        common_keywords = set(query_keywords) & set(doc_keywords)
        
        # 如果没有共同关键词，分数为0
        if not common_keywords:
            return 0.0
        
        # 计算基础匹配分数
        match_score = len(common_keywords) / len(query_keywords)
        
        # 考虑匹配关键词的长度（长词更重要）
        length_bonus = sum(len(k) for k in common_keywords) / sum(len(k) for k in query_keywords)
        
        # 最终分数结合基础匹配度和长度加权
        final_score = 0.7 * match_score + 0.3 * length_bonus
        
        return final_score
    
    async def diagnose(self) -> Dict[str, Any]:
        """系统诊断，返回检索引擎状态"""
        result = {
            "docs_count": len(self.docs),
            "keywords_count": len(self.inverted_index),
            "competition_types": list(self.competition_types),
            "competition_docs_count": {k: len(v) for k, v in self.competition_docs.items()},
            "parameters": {
                "chunk_size": self.chunk_size,
                "chunk_overlap": self.chunk_overlap,
                "score_threshold": self.score_threshold
            }
        }
        
        return result 