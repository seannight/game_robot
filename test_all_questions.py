#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
竞赛智能客服系统 - 批量测试工具
测试系统对一组预设问题的回答质量
"""

import os
import sys
import logging
import time
import json
import asyncio
from typing import List, Dict, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/test_results.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 测试问题列表
TEST_QUESTIONS = [
    # 基础信息类问题
    "泰迪杯数据挖掘挑战赛是什么比赛？",
    "3D编程模型创新设计专项赛的参赛要求是什么？",
    "机器人工程设计专项赛需要提交哪些材料？",
    "太空电梯工程设计专项赛的评分标准是什么？",
    "虚拟仿真平台创新设计专项赛的参赛对象有哪些？",
    "开源鸿蒙机器人专项赛的比赛流程是怎样的？",
    
    # 跨竞赛问题
    "所有竞赛的报名方式是什么？",
    "竞赛作品提交的截止日期是什么时候？",
    "参赛获奖证书如何颁发？",
    
    # 具体细节问题
    "如何确保我的竞赛作品不被剽窃？",
    "参加3D编程模型创新设计专项赛需要什么编程基础？",
    "太空电梯工程设计专项赛中对模型材料有什么要求？",
    
    # 可能超出知识库范围的问题
    "参赛团队可以跨学校组队吗？",
    "若竞赛过程中遇到技术问题如何寻求帮助？",
    "比赛前是否有相关培训？",
    
    # 边界测试问题
    "这是一个测试问题",
    "请你谈谈你对人工智能的看法",
    "世界上最高的山峰是什么？"
]

async def test_single_question(engine, question: str) -> Dict[str, Any]:
    """测试单个问题"""
    try:
        logger.info(f"测试问题: {question}")
        start_time = time.time()
        
        # 调用引擎处理问题
        result = await engine.query(question=question)
        
        elapsed_time = time.time() - start_time
        
        # 记录结果
        test_result = {
            "question": question,
            "answer": result.get("answer", ""),
            "confidence": result.get("confidence", 0),
            "sources_count": len(result.get("sources", [])),
            "competition_type": result.get("competition_type"),
            "processing_time": elapsed_time
        }
        
        # 记录简要信息
        logger.info(f"问题处理完成，置信度: {test_result['confidence']:.2f}, 耗时: {elapsed_time:.2f}秒")
        
        return test_result
    
    except Exception as e:
        logger.error(f"测试问题时出错: {str(e)}")
        return {
            "question": question,
            "error": str(e),
            "success": False
        }

async def run_tests() -> List[Dict[str, Any]]:
    """运行所有测试问题"""
    try:
        # 导入SimpleMCPWithRAG引擎
        from app.models.SimpleMCPWithRAG import SimpleMCPWithRAG
        
        logger.info("初始化SimpleMCPWithRAG引擎...")
        engine = SimpleMCPWithRAG()  # 使用简化版引擎
        
        logger.info(f"开始测试 {len(TEST_QUESTIONS)} 个问题...")
        results = []
        
        for i, question in enumerate(TEST_QUESTIONS, 1):
            logger.info(f"[{i}/{len(TEST_QUESTIONS)}] 测试: {question}")
            result = await test_single_question(engine, question)
            results.append(result)
        
        return results
    
    except Exception as e:
        logger.error(f"测试过程中发生错误: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def save_results(results: List[Dict[str, Any]]) -> str:
    """保存测试结果到文件"""
    try:
        # 创建输出目录
        os.makedirs("test_results", exist_ok=True)
        
        # 生成文件名
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"test_results/test_results_{timestamp}.json"
        
        # 保存结果
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"测试结果已保存至: {filename}")
        return filename
    
    except Exception as e:
        logger.error(f"保存测试结果时出错: {str(e)}")
        return ""

def analyze_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """分析测试结果"""
    if not results:
        return {"error": "没有测试结果", "total_questions": 0}
    
    # 计算统计信息
    total = len(results)
    success_count = sum(1 for r in results if "error" not in r)
    
    confidence_values = [r.get("confidence", 0) for r in results if "confidence" in r]
    avg_confidence = sum(confidence_values) / len(confidence_values) if confidence_values else 0
    
    processing_times = [r.get("processing_time", 0) for r in results if "processing_time" in r]
    avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
    
    # 置信度分布
    confidence_bins = {
        "高 (>0.7)": sum(1 for c in confidence_values if c > 0.7),
        "中 (0.4-0.7)": sum(1 for c in confidence_values if 0.4 <= c <= 0.7),
        "低 (0.2-0.4)": sum(1 for c in confidence_values if 0.2 <= c < 0.4),
        "极低 (<0.2)": sum(1 for c in confidence_values if c < 0.2)
    }
    
    return {
        "total_questions": total,
        "success_count": success_count,
        "success_rate": success_count / total if total > 0 else 0,
        "average_confidence": avg_confidence,
        "average_processing_time": avg_processing_time,
        "confidence_distribution": confidence_bins
    }

async def main():
    """主函数"""
    try:
        logger.info("开始批量测试...")
        
        # 运行测试
        results = await run_tests()
        
        # 保存结果
        save_results(results)
        
        # 分析结果
        analysis = analyze_results(results)
        
        # 输出分析报告
        logger.info("\n====== 测试分析报告 ======")
        logger.info(f"测试问题总数: {analysis['total_questions']}")
        logger.info(f"成功处理数: {analysis['success_count']}")
        logger.info(f"成功率: {analysis['success_rate']*100:.1f}%")
        logger.info(f"平均置信度: {analysis['average_confidence']:.2f}")
        logger.info(f"平均处理时间: {analysis['average_processing_time']:.2f}秒")
        
        logger.info("\n置信度分布:")
        for level, count in analysis['confidence_distribution'].items():
            percentage = count / analysis['total_questions'] * 100
            logger.info(f"  {level}: {count} 个问题 ({percentage:.1f}%)")
        
        logger.info("\n测试完成！")
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    # 创建日志目录
    os.makedirs("logs", exist_ok=True)
    
    # 运行测试
    asyncio.run(main()) 