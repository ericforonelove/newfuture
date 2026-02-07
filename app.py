"""
主入口：
1. 初始化 VannaQwen（Qwen LLM + ChromaDB 向量库）
2. 连接 SQLite 演示库
3. 喂入 DDL / 文档 / 示例 SQL 做 training
4. 启动 Vanna 自带的 Flask Web UI（问句 → SQL → 执行 → 图表）
"""

import os
import sqlite3

import config
from vanna_qwen import VannaQwen
from init_demo_db import create_demo_db


def build_vanna() -> VannaQwen:
    """构建并训练 Vanna 实例。"""

    vn = VannaQwen(config={
        # ----- LLM (Qwen via OpenAI-compat) -----
        "api_key":  config.QWEN_API_KEY,
        "base_url": config.QWEN_BASE_URL,
        "model":    config.QWEN_MODEL,
        # ----- ChromaDB -----
        "path":     config.CHROMA_PATH,
    })

    # ---------- 连接数据库 ----------
    vn.connect_to_sqlite(config.DB_PATH)

    # ---------- Training: DDL ----------
    vn.train(ddl="""
        CREATE TABLE departments (
            id   INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );
    """)

    vn.train(ddl="""
        CREATE TABLE employees (
            id            INTEGER PRIMARY KEY,
            name          TEXT NOT NULL,
            department_id INTEGER REFERENCES departments(id),
            salary        REAL,
            hire_date     TEXT
        );
    """)

    vn.train(ddl="""
        CREATE TABLE sales (
            id          INTEGER PRIMARY KEY,
            employee_id INTEGER REFERENCES employees(id),
            amount      REAL,
            sale_date   TEXT
        );
    """)

    # ---------- Training: 业务文档 ----------
    vn.train(documentation="departments 表保存部门信息，包含工程部、市场部、销售部、人事部。")
    vn.train(documentation="employees 表保存员工信息，salary 单位为人民币元。")
    vn.train(documentation="sales 表保存销售记录，amount 单位为人民币元，只有销售部员工有销售记录。")

    # ---------- Training: 示例 SQL ----------
    vn.train(
        question="每个部门有多少员工？",
        sql="SELECT d.name AS 部门, COUNT(*) AS 员工数 FROM employees e JOIN departments d ON e.department_id = d.id GROUP BY d.name;",
    )
    vn.train(
        question="销售额最高的员工是谁？",
        sql="SELECT e.name AS 员工, SUM(s.amount) AS 总销售额 FROM sales s JOIN employees e ON s.employee_id = e.id GROUP BY e.name ORDER BY 总销售额 DESC LIMIT 1;",
    )
    vn.train(
        question="每个月的销售总额是多少？",
        sql="SELECT strftime('%Y-%m', sale_date) AS 月份, SUM(amount) AS 销售总额 FROM sales GROUP BY 月份 ORDER BY 月份;",
    )

    return vn


def main():
    # 如果演示数据库还不存在就先创建
    if not os.path.exists(config.DB_PATH):
        create_demo_db()

    vn = build_vanna()

    # 启动 Vanna 内置 Flask Web UI
    # 默认 http://localhost:8084
    from vanna.flask import VannaFlaskApp
    app = VannaFlaskApp(vn, allow_llm_to_see_data=True)
    app.run(host="0.0.0.0", port=8084)


if __name__ == "__main__":
    main()
