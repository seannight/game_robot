"""
竞赛智能客服系统 - 模型模块初始化
定义模型组件导入
"""

# 导入核心组件
from app.models.SimpleRAG import SimpleRAG
from app.models.MCPWithContext import MCPWithContext
from app.models.RAGAdapter import RAGAdapter
from app.models.SimpleMCPWithRAG import SimpleMCPWithRAG
from app.models.enhanced_rag import EnhancedRAG
from app.models.enhanced_mcp import EnhancedMCP

# 设置可导出组件
__all__ = [
    'SimpleRAG',
    'MCPWithContext',
    'RAGAdapter',
    'SimpleMCPWithRAG',
    'EnhancedRAG',
    'EnhancedMCP'
]
