#!/usr/bin/env python
"""
竞赛智能客服系统 - 索引强制重建工具
绕过启动选择器，直接重建RAG索引
"""

import os
import sys
import logging
import time
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 确保工作目录是项目根目录
project_root = Path(__file__).parent
os.chdir(project_root)

# 添加当前目录到Python路径
sys.path.insert(0, str(project_root))

def main():
    """主函数：重建索引"""
    try:
        logger.info("开始强制重建RAG索引...")
        
        # 直接导入SimpleRAG模块，避免通过__init__.py间接导入
        start_time = time.time()
        logger.info("正在加载SimpleRAG模块...")
        
        # 修改导入方式，避免通过__init__.py导入
        sys.path.insert(0, str(project_root))
        from app.models.SimpleRAG import SimpleRAG
        
        # 实例化并强制重建索引
        logger.info("正在实例化SimpleRAG并重建索引...")
        rag_engine = SimpleRAG(rebuild_index=True)
        
        # 诊断索引状态
        logger.info("检查索引状态...")
        diagnostics = rag_engine.diagnose_knowledge_base()
        logger.info(f"索引包含 {diagnostics['total_documents']} 个文档和 {diagnostics['total_keywords']} 个关键词")
        
        # 记录竞赛类型统计
        logger.info(f"检测到 {len(diagnostics['competition_document_counts'])} 种竞赛类型")
        for comp_type, count in diagnostics['competition_document_counts'].items():
            logger.info(f"  - {comp_type}: {count} 个文档")
        
        elapsed_time = time.time() - start_time
        logger.info(f"索引重建完成! 耗时: {elapsed_time:.2f}秒")
        logger.info(f"配置: chunk_size={rag_engine.chunk_size}, score_threshold={rag_engine.score_threshold}")
        
        return True
    
    except Exception as e:
        logger.error(f"索引重建失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 