# Vanna.ai + Qwen Text-to-SQL

用 [Vanna.ai](https://vanna.ai/) 做框架，底座 LLM 替换为 **Qwen2.5:7b**（通过 OpenAI-compatible 接口），实现：

> 自然语言提问 → 生成 SQL → 执行查询 → 返回表格 & 图表

## 架构

```
用户提问（中文/英文）
        │
        ▼
  ChromaDB 向量检索（匹配相似的 DDL / 文档 / 示例 SQL）
        │
        ▼
  Qwen2.5:7b（OpenAI-compat 接口）生成 SQL
        │
        ▼
  SQLite 执行 SQL
        │
        ▼
  Flask Web UI 展示表格 + Plotly 图表
```

## 项目结构

```
├── config.py          # Qwen 端点、数据库路径、ChromaDB 配置
├── vanna_qwen.py      # 自定义 Vanna 类（ChromaDB + OpenAI_Chat）
├── init_demo_db.py    # 创建演示 SQLite 数据库
├── app.py             # 主入口：训练 Vanna + 启动 Flask Web UI
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

# 数据库路径（换成 PostgreSQL / MySQL 需改 app.py 中的连接方式）
DB_PATH = "demo.db"
```

## 换用其他数据库

将 `app.py` 中的 `vn.connect_to_sqlite(...)` 替换为：

```python
# PostgreSQL
vn.connect_to_postgres(host="localhost", dbname="mydb", user="postgres", password="xxx", port=5432)

# MySQL
vn.connect_to_mysql(host="localhost", dbname="mydb", user="root", password="xxx", port=3306)
```

同时更新 training 中的 DDL 为实际表结构。
