# Vanna.ai + Qwen Text-to-SQL

用 [Vanna.ai](https://vanna.ai/) 2.0 做框架，底座 LLM 替换为 **Qwen2.5:7b**（通过 OpenAI-compatible 接口），实现：

> 自然语言提问 → 生成 SQL → 执行查询 → 返回表格 & 图表

## 架构

```
用户提问（中文/英文）
        │
        ▼
  Vanna Agent（工具调度）
        │
   ┌────┴────┐
   ▼         ▼
RunSqlTool  VisualizeDataTool
   │              │
   ▼              ▼
Qwen2.5:7b    Plotly 图表
生成 & 执行 SQL
   │
   ▼
SQLite / 其他数据库
```

**组件说明：**

| 组件 | 实现 |
|------|------|
| LLM | `OpenAILlmService` → Qwen2.5:7b (Ollama) |
| Agent Memory | `ChromaAgentMemory` → ChromaDB 本地持久化 |
| SQL 执行 | `SqliteRunner` → SQLite |
| 可视化 | `VisualizeDataTool` → Plotly |
| Web UI | `VannaFlaskServer` → Flask |

## 项目结构

```
├── config.py          # Qwen 端点、数据库路径、ChromaDB 配置
├── init_demo_db.py    # 创建演示 SQLite 数据库
├── app.py             # 主入口：组装 Agent + 启动 Flask Web UI
└── requirements.txt   # Python 依赖
```

## 快速开始

### 1. 启动 Qwen 模型

使用 [Ollama](https://ollama.com/) 拉取并运行：

```bash
ollama pull qwen2.5:7b
ollama serve  # 如果尚未运行
```

默认会在 `http://localhost:11434/v1` 暴露 OpenAI-compatible API。

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 运行

```bash
python app.py
```

浏览器打开 http://localhost:8084 ，直接输入中文问题即可。

## 演示数据库

首次运行会自动创建 `demo.db`，包含三张表：

| 表名 | 说明 |
|------|------|
| `departments` | 部门（工程部、市场部、销售部、人事部） |
| `employees` | 员工（姓名、部门、薪资、入职日期） |
| `sales` | 销售记录（员工、金额、日期） |

示例问题：

- 每个部门有多少员工？
- 销售额最高的员工是谁？
- 每个月的销售总额是多少？
- 平均薪资最高的部门是哪个？

## 配置

编辑 `config.py` 即可修改：

```python
# Qwen 端点（Ollama / vLLM / LMStudio 等）
QWEN_BASE_URL = "http://localhost:11434/v1"
QWEN_API_KEY  = "ollama"
QWEN_MODEL    = "qwen2.5:7b"

# 数据库路径
DB_PATH = "demo.db"

# ChromaDB 持久化目录
CHROMA_PATH = "./chroma_data"
```

## 换用其他数据库

将 `app.py` 中的 `SqliteRunner` 替换为对应的 Runner：

```python
# PostgreSQL
from vanna.integrations.postgres.sql_runner import PostgresRunner
sql_runner = PostgresRunner(host="localhost", dbname="mydb", user="postgres", password="xxx", port=5432)

# MySQL
from vanna.integrations.mysql.sql_runner import MysqlRunner
sql_runner = MysqlRunner(host="localhost", dbname="mydb", user="root", password="xxx", port=3306)
```
