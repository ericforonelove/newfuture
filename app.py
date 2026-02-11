"""
主入口：
1. 用 OpenAILlmService 对接 Qwen（Ollama OpenAI-compat 接口）
2. ChromaDB 做 Agent Memory
3. SQLite 跑 SQL + Plotly 可视化
4. Flask Web UI 提供交互界面
"""

import os
import sqlite3
import json

import config
from init_demo_db import create_demo_db

from vanna.integrations.openai.llm import OpenAILlmService
from vanna.integrations.chromadb.agent_memory import ChromaAgentMemory
from vanna.integrations.sqlite.sql_runner import SqliteRunner
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

数据库中有以下表：

departments（部门表）：
  - id: 部门ID
  - name: 部门名称（工程部、市场部、销售部、人事部）

employees（员工表）：
  - id: 员工ID
  - name: 姓名
  - department_id: 所属部门ID
  - salary: 薪资（人民币元）
  - hire_date: 入职日期

sales（销售记录表）：
  - id: 记录ID
  - employee_id: 员工ID（仅销售部员工）
  - amount: 销售金额（人民币元）
  - sale_date: 销售日期

## 工具使用规则（非常重要，必须严格遵守）

你有两个工具可用：

1. **run_sql** — 执行 SQL 查询。SQL 必须是 SQLite 方言。
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
- 生成的 SQL 必须是 SQLite 方言
- 回复中请用中文解释查询结果
- 如果用户的问题不明确，请用中文追问
"""


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
        system_prompt_builder=DefaultSystemPromptBuilder(base_prompt=CHINESE_SYSTEM_PROMPT),
    )

    return agent


# ---------- 数据预览页面 ----------

DATA_PAGE_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>演示数据预览</title>
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
</style>
</head>
<body>
<h1>演示数据预览</h1>
<p>以下是 <code>demo.db</code> 中的全部数据，你可以基于这些数据在聊天界面提问。</p>
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
    # 演示数据库不存在就先创建
    if not os.path.exists(config.DB_PATH):
        create_demo_db()

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
        conn = sqlite3.connect(config.DB_PATH)
        cur = conn.cursor()
        tables_html = ""

        cur.execute("SELECT id, name FROM departments ORDER BY id")
        tables_html += render_table(
            "departments（部门表）",
            ["ID", "部门名称"],
            cur.fetchall(),
        )

        cur.execute("SELECT e.id, e.name, d.name, e.salary, e.hire_date FROM employees e JOIN departments d ON e.department_id = d.id ORDER BY e.id")
        tables_html += render_table(
            "employees（员工表）",
            ["ID", "姓名", "部门", "薪资（元）", "入职日期"],
            cur.fetchall(),
        )

        cur.execute("SELECT s.id, e.name, s.amount, s.sale_date FROM sales s JOIN employees e ON s.employee_id = e.id ORDER BY s.id")
        tables_html += render_table(
            "sales（销售记录表）",
            ["ID", "员工", "金额（元）", "销售日期"],
            cur.fetchall(),
        )

        conn.close()
        return DATA_PAGE_HTML % tables_html

    # 启动
    app.run(host="0.0.0.0", port=8084)


if __name__ == "__main__":
    main()
