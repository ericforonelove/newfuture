"""
主入口：
1. 用 OpenAILlmService 对接 Qwen（Ollama OpenAI-compat 接口）
2. ChromaDB 做 Agent Memory
3. PostgreSQL/GaussDB 跑 SQL + Plotly 可视化
4. Flask Web UI 提供交互界面
"""

import os

import psycopg2
import config

from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from vanna.integrations.openai.llm import OpenAILlmService
from vanna.integrations.chromadb.agent_memory import ChromaAgentMemory
from vanna.integrations.postgres.sql_runner import PostgresRunner
from vanna.integrations.local.file_system import LocalFileSystem
from vanna.core.agent.agent import Agent
from vanna.core.agent.config import AgentConfig
from vanna.core.registry import ToolRegistry
from vanna.core.system_prompt.default import DefaultSystemPromptBuilder
from vanna.tools.run_sql import RunSqlTool
from vanna.tools.visualize_data import VisualizeDataTool
from vanna.core.user.resolver import UserResolver
from vanna.core.user.models import User
from vanna.core.user.request_context import RequestContext
from vanna.servers.flask.app import VannaFlaskServer

# ---- 中文系统提示 ----
CHINESE_SYSTEM_PROMPT = """你是一个专业的数据库助手，请始终用中文回复用户。

你可以帮助用户：
1. 根据自然语言问题生成 SQL 查询
2. 执行 SQL 并展示结果
3. 用图表可视化数据

你连接的是 PostgreSQL（GaussDB 兼容）数据库。

## 工具使用规则（非常重要，必须严格遵守）

你有两个工具可用：

1. **run_sql** — 执行 SQL 查询。SQL 必须是 PostgreSQL 方言。
   执行成功后，工具会返回结果并告诉你保存到了哪个文件，例如 "Results saved to file: query_results_abcd1234.csv"。

2. **visualize_data** — 读取 CSV 文件并生成图表。
   - filename 参数**必须**使用 run_sql 返回的那个文件名（如 query_results_abcd1234.csv）。
   - **绝对禁止**自己编造文件名或使用 /tmp 等绝对路径！
   - 只使用 run_sql 结果中给出的 filename。

## 标准工作流程

每次回答数据问题时，按以下步骤执行：
1. 先调用 run_sql 执行查询
2. 从 run_sql 的返回结果中提取文件名（形如 query_results_xxxxxxxx.csv）
3. 用**这个确切的文件名**调用 visualize_data 生成图表
4. 用中文向用户解释结果

请注意：
- 生成的 SQL 必须是 PostgreSQL 方言（支持 GaussDB）
- 回复中请用中文解释查询结果
- 如果用户的问题不明确，请用中文追问
- 如果不确定表结构，先用 SELECT * FROM information_schema.tables WHERE table_schema='public' 查看可用表
- 查看字段用 SELECT column_name, data_type FROM information_schema.columns WHERE table_name='表名'
"""


class AnonymousUserResolver(UserResolver):
    """本地演示用，所有请求都返回同一个匿名用户。"""

    async def resolve_user(self, request_context: RequestContext) -> User:
        return User(id="local", username="local", groups=["admin"])


def build_agent() -> Agent:
    """组装 Vanna 2.0 Agent：Qwen LLM + ChromaDB + PostgreSQL。"""

    # ---- LLM: Qwen via OpenAI-compatible API ----
    llm = OpenAILlmService(
        model=config.QWEN_MODEL,
        base_url=config.QWEN_BASE_URL,
        api_key=config.QWEN_API_KEY,
    )

    # ---- Agent Memory: ChromaDB + 内部 Embedding 模型 ----
    embedding_fn = OpenAIEmbeddingFunction(
        api_key=config.EMBED_API_KEY,
        api_base=config.EMBED_BASE_URL,
        model_name=config.EMBED_MODEL,
    )
    memory = ChromaAgentMemory(
        persist_directory=config.CHROMA_PATH,
        collection_name="vanna_qwen_memory",
        embedding_function=embedding_fn,
    )

    # ---- SQL Runner: PostgreSQL / GaussDB ----
    sql_runner = PostgresRunner(
        host=config.PG_HOST,
        port=config.PG_PORT,
        database=config.PG_DATABASE,
        user=config.PG_USER,
        password=config.PG_PASSWORD,
        **config.PG_EXTRA,
    )

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
        system_prompt_builder=DefaultSystemPromptBuilder(base_prompt=CHINESE_SYSTEM_PROMPT),
    )

    return agent


# ---------- 数据预览页面 ----------

DATA_PAGE_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>数据库表预览</title>
<style>
  body { font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
         max-width: 960px; margin: 40px auto; padding: 0 20px; color: #333; }
  h1 { color: #1a1a2e; }
  h2 { color: #16213e; margin-top: 32px; }
  table { border-collapse: collapse; width: 100%%; margin-bottom: 24px; }
  th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; }
  th { background: #1a1a2e; color: #fff; }
  tr:nth-child(even) { background: #f9f9f9; }
  .back { display: inline-block; margin-top: 20px; color: #0066cc; text-decoration: none; }
  .back:hover { text-decoration: underline; }
  .info { background: #f0f7ff; border: 1px solid #c0d8f0; padding: 12px; border-radius: 6px; margin-bottom: 20px; }
</style>
</head>
<body>
<h1>数据库表预览</h1>
<div class="info">
  <strong>连接信息：</strong> %s:%s / %s<br>
  <strong>提示：</strong> 以下展示各表前 20 条记录，完整数据请在聊天界面用 SQL 查询。
</div>
%s
<a class="back" href="/">← 返回聊天</a>
</body>
</html>"""


def render_table(title, headers, rows):
    """把查询结果渲染成 HTML 表格。"""
    html = f"<h2>{title}</h2><table><tr>"
    html += "".join(f"<th>{h}</th>" for h in headers)
    html += "</tr>"
    for row in rows:
        html += "<tr>" + "".join(f"<td>{v}</td>" for v in row) + "</tr>"
    html += "</table>"
    return html


def main():
    agent = build_agent()

    # 创建 Flask 应用
    server = VannaFlaskServer(agent, config={
        "dev_mode": False,
        "cors": {"enabled": True},
    })
    app = server.create_app()

    # ---- 自定义路由：数据预览 ----
    @app.route("/data")
    def data_preview():
        conn = psycopg2.connect(
            host=config.PG_HOST,
            port=config.PG_PORT,
            database=config.PG_DATABASE,
            user=config.PG_USER,
            password=config.PG_PASSWORD,
            **config.PG_EXTRA,
        )
        cur = conn.cursor()
        tables_html = ""

        # 查出所有 public schema 下的表
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' ORDER BY table_name
        """)
        table_names = [row[0] for row in cur.fetchall()]

        for table_name in table_names:
            cur.execute(f"SELECT * FROM \"{table_name}\" LIMIT 20")
            headers = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            tables_html += render_table(
                f"{table_name}（前 20 条）",
                headers,
                rows,
            )

        cur.close()
        conn.close()

        return DATA_PAGE_HTML % (
            config.PG_HOST, config.PG_PORT, config.PG_DATABASE,
            tables_html,
        )

    # 启动
    app.run(host="0.0.0.0", port=8084)


if __name__ == "__main__":
    main()
