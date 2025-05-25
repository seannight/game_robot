#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
竞赛智能客服系统 - jieba分词帮助工具
解决jieba词典路径问题
"""

import os
import logging
import jieba
import importlib.resources
from pathlib import Path
import shutil

logger = logging.getLogger(__name__)

# 预初始化pseg，稍后会更新此变量
try:
    import jieba.posseg
    pseg = jieba.posseg
except Exception as e:
    logger.error(f"导入jieba.posseg失败: {str(e)}")
    # 创建一个模拟的pseg模块，防止导入错误
    class DummyPseg:
        @staticmethod
        def lcut(text, *args, **kwargs):
            # 返回简单的分词结果，每个字作为一个词
            return [(char, 'x') for char in text if char.strip()]
    pseg = DummyPseg()

# 导出jieba对象，使其他模块可以通过jieba_helper导入
__all__ = ['jieba', 'pseg']

def init_jieba():
    """
    初始化jieba分词器，确保词典文件存在
    """
    try:
        # 设置jieba日志级别
        jieba.setLogLevel(logging.INFO)
        
        # 获取项目根目录
        current_directory = os.path.dirname(os.path.abspath(__file__))
        project_root = Path(current_directory).parent.parent
        
        # 创建自定义词典目录
        dict_dir = os.path.join(project_root, "data", "dict")
        os.makedirs(dict_dir, exist_ok=True)
        
        # 自定义词典文件路径
        custom_dict_path = os.path.join(dict_dir, "jieba_dict.txt")
        
        # 查找jieba原始词典文件
        jieba_module_dir = os.path.dirname(jieba.__file__)
        original_dict_path = os.path.join(jieba_module_dir, "dict.txt")
        
        # 如果原始词典文件存在，复制到自定义目录
        if os.path.exists(original_dict_path):
            logger.info(f"发现原始jieba词典，复制到自定义位置: {custom_dict_path}")
            shutil.copy(original_dict_path, custom_dict_path)
        else:
            # 如果自定义词典不存在，创建一个简单的词典文件
            if not os.path.exists(custom_dict_path):
                logger.info(f"创建简单的jieba词典文件: {custom_dict_path}")
                with open(custom_dict_path, "w", encoding="utf-8") as f:
                    f.write("智能客服 1000 n\n")
                    f.write("竞赛 1000 n\n")
                    f.write("泰迪杯 1000 n\n")
                    f.write("数据挖掘 1000 n\n")
                    f.write("评分标准 1000 n\n")
                    f.write("报名时间 1000 n\n")
                    f.write("参赛要求 1000 n\n")
                    f.write("获奖条件 1000 n\n")
                    f.write("专项赛 1000 n\n")
                    f.write("人工智能 1000 n\n")
            else:
                logger.info(f"使用已存在的自定义词典: {custom_dict_path}")
        
        # 强制重置jieba词典
        if os.path.exists(custom_dict_path):
            logger.info(f"加载自定义词典: {custom_dict_path}")
            jieba.set_dictionary(custom_dict_path)
            jieba.initialize()
            logger.info("jieba初始化成功")
            return True
        else:
            logger.error("无法找到或创建jieba词典文件")
            return False
    except Exception as e:
        logger.error(f"jieba初始化失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

# 初始化jieba
init_jieba() 