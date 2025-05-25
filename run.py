#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
竞赛智能客服系统 - 启动脚本
正确设置Python路径并启动应用
"""

import os
import sys
from pathlib import Path
import logging # 仍然需要导入logging，但仅用于获取settings

# 获取项目根目录
project_root = Path(__file__).resolve().parent

# 将项目根目录添加到Python路径中，解决模块导入问题
sys.path.insert(0, str(project_root))

def main():
    """主函数：启动应用"""
    try:
        print("正在启动竞赛智能客服系统...")
        
        # 导入settings，uvicorn.run需要它
        from app.config import settings 
        
        # --- 日志配置已移至 app/main.py 模块顶部 --- 
        # (移除此处的 logging.basicConfig 和测试日志)
        # --- 日志配置结束 ---
        
        # 导入 app.main (包含 FastAPI app 实例) 
        # 日志应该在 app.main 模块加载时由其内部的 basicConfig 配置
        from app.main import app 
        
        import uvicorn
        uvicorn.run(
            "app.main:app", 
            host=settings.API_HOST,
            port=settings.API_PORT,
            reload=settings.DEBUG,  
            log_config=None,        # 确保uvicorn不使用自己的log_config
            log_level=None          # 确保uvicorn不覆盖我们在app/main.py中的配置
        )
        
    except Exception as e:
        # 这里的日志记录可能会也可能不会工作，取决于app.main.py中的配置是否已成功
        # 为了保险起见，同时打印到控制台
        print(f"CRITICAL: 启动失败: {e}") 
        try:
            # 尝试使用logger，如果它被配置了
            critical_logger = logging.getLogger("run_py_critical_error")
            critical_logger.critical(f"启动失败: {e}", exc_info=True)
        except Exception:
            pass # 如果logger也失败，至少我们有print输出
        sys.exit(1)

if __name__ == "__main__":
    main() 