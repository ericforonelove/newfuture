"""
主入口：
1. 用 OpenAILlmService 对接 Qwen（Ollama OpenAI-compat 接口）
2. ChromaDB 做 Agent Memory
3. SQLite 跑 SQL + Plotly 可视化
4. Flask Web UI 提供交互界面
"""

import os

import config
from init_demo_db import create_demo_db

from vanna.integrations.openai.llm import OpenAILlmService
from vanna.integrations.chromadb.agent_memory import ChromaAgentMemory
from vanna.integrations.sqlite.sql_runner import SqliteRunner
from vanna.integrations.local.file_system import LocalFileSystem
from vanna.core.agent.agent import Agent
from vanna.core.agent.config import AgentConfig
from vanna.core.registry import ToolRegistry
from vanna.tools.run_sql import RunSqlTool
from vanna.tools.visualize_data import VisualizeDataTool
from vanna.core.user.resolver import UserResolver
from vanna.core.user.models import User
from vanna.core.user.request_context import RequestContext
from vanna.servers.flask.app import VannaFlaskServer


class AnonymousUserResolver(UserResolver):
    """本地演示用，所有请求都返回同一个匿名用户。"""

    async def resolve_user(self, request_context: RequestContext) -> User:
        return User(id="local", username="local", groups=["admin"])


def build_agent() -> Agent:
    """组装 Vanna 2.0 Agent：Qwen LLM + ChromaDB + SQLite。"""

    # ---- LLM: Qwen via OpenAI-compatible API ----
    llm = OpenAILlmService(
        model=config.QWEN_MODEL,
        base_url=config.QWEN_BASE_URL,
        api_key=config.QWEN_API_KEY,
    )

    # ---- Agent Memory: ChromaDB ----
    memory = ChromaAgentMemory(
        persist_directory=config.CHROMA_PATH,
        collection_name="vanna_qwen_memory",
    )

    # ---- SQL Runner: SQLite ----
    sql_runner = SqliteRunner(database_path=config.DB_PATH)

    # ---- 本地文件系统（图表等产物存放） ----
    file_system = LocalFileSystem(working_directory="./output")

    # ---- 注册工具 ----
    tools = ToolRegistry()
    tools.register_local_tool(RunSqlTool(sql_runner=sql_runner, file_system=file_system), access_groups=[])
    tools.register_local_tool(VisualizeDataTool(file_system=file_system), access_groups=[])

    # ---- 组装 Agent ----
    agent = Agent(
        llm_service=llm,
        tool_registry=tools,
        user_resolver=AnonymousUserResolver(),
        agent_memory=memory,
        config=AgentConfig(
            stream_responses=True,
            temperature=0.7,
        ),
    )

    return agent


def main():
    # 演示数据库不存在就先创建
    if not os.path.exists(config.DB_PATH):
        create_demo_db()

    agent = build_agent()

    # 启动 Flask Web UI
    server = VannaFlaskServer(agent, config={
        "dev_mode": False,
        "cors": {"enabled": True},
    })
    server.run(host="0.0.0.0", port=8084)


if __name__ == "__main__":
    main()
