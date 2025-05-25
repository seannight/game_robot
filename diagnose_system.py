"""
系统诊断工具 - 检查竞赛智能客服系统状态
"""

import os
import sys
import json
import logging
import asyncio

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("system_diagnosis")

async def main():
    try:
        # 导入依赖
        logger.info("加载系统组件...")
        from app.config import settings, get_project_root
        from app.models.MCPWithRAG import MCPWithRAG
        
        # 检查关键路径
        project_root = get_project_root()
        logger.info(f"项目根目录: {project_root}")
        
        knowledge_base_path = settings.KNOWLEDGE_BASE_PATH
        logger.info(f"知识库路径: {knowledge_base_path}")
        
        if not os.path.exists(knowledge_base_path):
            logger.error(f"知识库路径不存在!")
            # 尝试查找正确路径
            alternative_path = os.path.join(project_root, "data", "knowledge", "docs", "附件1")
            if os.path.exists(alternative_path):
                logger.info(f"找到可能的替代路径: {alternative_path}")
                # 统计PDF文件
                pdf_count = sum(1 for f in os.listdir(alternative_path) if f.lower().endswith('.pdf'))
                logger.info(f"替代路径中有 {pdf_count} 个PDF文件")
        
        # 初始化引擎
        logger.info("初始化MCPWithRAG引擎...")
        engine = MCPWithRAG(rebuild_index=False)
        
        # 进行诊断
        logger.info("执行系统诊断...")
        diagnosis = engine.diagnose()
        
        # 输出诊断结果
        logger.info("\n=== 系统诊断结果 ===")
        logger.info(f"知识库路径: {diagnosis['knowledge_base_path']}")
        logger.info(f"知识库存在: {'是' if diagnosis['knowledge_base_exists'] else '否'}")
        logger.info(f"索引路径: {diagnosis['index_path']}")
        logger.info(f"索引存在: {'是' if diagnosis['index_exists'] else '否'}")
        logger.info(f"PDF文件总数: {diagnosis.get('total_pdf_files', 0)}")
        logger.info(f"文档片段总数: {diagnosis['total_docs']}")
        logger.info(f"关键词总数: {diagnosis['total_keywords']}")
        logger.info(f"竞赛类型总数: {diagnosis['total_competition_types']}")
        
        # 输出每个竞赛类型的文档数
        logger.info("\n=== 竞赛类型文档统计 ===")
        for comp_type, count in diagnosis.get('competition_doc_counts', {}).items():
            logger.info(f"{comp_type}: {count} 个文档")
        
        # 测试一个查询
        logger.info("\n=== 执行测试查询 ===")
        test_queries = [
            "泰迪杯数据挖掘挑战赛的参赛要求是什么？",
            "3D编程模型创新设计专项赛的评分标准是什么？",
            "机器人工程挑战赛的报名时间是什么时候？"
        ]
        
        for query in test_queries:
            logger.info(f"\n测试问题: {query}")
            result = await engine.query(question=query)
            logger.info(f"找到 {len(result.get('sources', []))} 个相关文档")
            logger.info(f"检测到的竞赛类型: {result.get('competition_type', '未检测到')}")
            logger.info(f"回答: {result.get('answer', '')[:100]}...")
        
        # 检查是否需要重建索引
        if diagnosis['total_docs'] == 0:
            logger.warning("文档索引为空，建议重建索引")
            choice = input("是否重建索引？(y/n): ")
            if choice.lower() == 'y':
                logger.info("开始重建索引...")
                success = engine.rebuild_index()
                logger.info(f"索引重建{'成功' if success else '失败'}")
                
                # 重建后再次诊断
                if success:
                    new_diagnosis = engine.diagnose()
                    logger.info(f"重建后文档数: {new_diagnosis['total_docs']}")
                    
                    # 再次测试查询
                    logger.info("重建后再次测试查询...")
                    for query in test_queries:
                        logger.info(f"\n测试问题: {query}")
                        result = await engine.query(question=query)
                        logger.info(f"找到 {len(result.get('sources', []))} 个相关文档")
        
        logger.info("\n诊断完成")
        
    except Exception as e:
        logger.error(f"诊断过程中出错: {str(e)}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main()) 