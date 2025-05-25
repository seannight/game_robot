#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
重建结构化知识库脚本
解决data/kb/structured_kb.json为空的问题
"""

import os
import sys
import logging

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from app.config import settings
from app.models.structured_kb import StructuredCompetitionKB

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """主函数：重建结构化知识库"""
    try:
        logger.info("开始重建结构化知识库...")
        
        # 获取文档路径
        txt_path = settings.TXT_PATH
        logger.info(f"使用文档路径: {txt_path}")
        
        # 检查文档路径是否存在
        if not os.path.exists(txt_path):
            logger.error(f"文档路径不存在: {txt_path}")
            return False
            
        # 检查文档数量
        txt_files = [f for f in os.listdir(txt_path) if f.endswith('.txt')]
        logger.info(f"发现 {len(txt_files)} 个txt文档")
        
        if len(txt_files) == 0:
            logger.error("未发现任何txt文档，请检查路径配置")
            return False
            
        # 强制重建结构化知识库
        logger.info("创建结构化知识库实例，强制重建...")
        kb = StructuredCompetitionKB(txt_path, rebuild=True)
        
        # 诊断结果
        diag = kb.diagnose()
        logger.info("结构化知识库诊断结果:")
        logger.info(f"  - 竞赛类型数量: {diag['competition_count']}")
        logger.info(f"  - 总信息条目: {diag['total_info_entries']}")
        logger.info(f"  - 竞赛类型列表: {', '.join(diag['competition_types'])}")
        
        # 检查知识库文件
        kb_file = "data/kb/structured_kb.json"
        if os.path.exists(kb_file):
            file_size = os.path.getsize(kb_file)
            logger.info(f"知识库文件大小: {file_size} 字节")
            
            if file_size > 100:  # 如果文件大于100字节，说明有内容
                logger.info("✅ 结构化知识库重建成功！")
                return True
            else:
                logger.warning("⚠️ 知识库文件过小，可能存在问题")
                return False
        else:
            logger.error("❌ 知识库文件未创建")
            return False
            
    except Exception as e:
        logger.error(f"重建结构化知识库失败: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 结构化知识库重建成功！")
        print("现在可以启动系统了。")
    else:
        print("\n❌ 结构化知识库重建失败！")
        print("请检查日志了解详细错误信息。")
    
    input("\n按Enter键退出...") 