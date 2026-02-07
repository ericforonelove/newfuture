"""
自定义 Vanna 类：ChromaDB 做向量存储 + Qwen（OpenAI-compatible）做 LLM。
"""

from vanna.openai import OpenAI_Chat
from vanna.chromadb import ChromaDB_VectorStore


class VannaQwen(ChromaDB_VectorStore, OpenAI_Chat):
    """
    继承顺序：先 ChromaDB_VectorStore（向量检索），再 OpenAI_Chat（LLM 调用）。
    MRO 保证两边的 __init__ 都会被正确调用。
    """

    def __init__(self, config=None):
        ChromaDB_VectorStore.__init__(self, config=config)
        OpenAI_Chat.__init__(self, config=config)
