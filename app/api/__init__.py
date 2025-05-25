"""
API包初始化文件
定义API路由和相关功能
"""

# 导入并导出路由器
from app.api.routes import router as api_router 

# 添加知识图谱模块导出
try:
    from app.api.knowledge_graph import router as knowledge_graph
except ImportError:
    # 如果存在特殊文件名，尝试另一种导入方式
    try:
        from app.api.knowledge_graph_api import router as knowledge_graph
    except ImportError:
        # 如果文件名包含括号，使用特殊方式导入
        try:
            import importlib.util
            import os
            # 查找可能的知识图谱文件
            for filename in os.listdir(os.path.dirname(__file__)):
                if filename.startswith("knowledge_graph") and filename.endswith(".py"):
                    spec = importlib.util.spec_from_file_location(
                        "knowledge_graph_module", 
                        os.path.join(os.path.dirname(__file__), filename)
                    )
                    knowledge_graph_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(knowledge_graph_module)
                    knowledge_graph = knowledge_graph_module.router
                    break
            else:
                knowledge_graph = None
        except:
            knowledge_graph = None
            
# 如果所有导入方式都失败，可能需要在其他地方处理这个问题
# 例如在routes.py中使用try-except块 