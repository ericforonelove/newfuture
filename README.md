# Vanna + 千问（OpenAI-Compatible）示例

这个仓库演示：

- 继续用 **Vanna.ai** 做问句到 SQL 的主流程；
- 把底座模型切到 **千问**，通过 OpenAI-compatible 接口访问；
- 提供一个最小 `Flask` API：`问句 -> SQL -> 执行 -> 图表代码`。

## 1) 安装

```bash
pip install -r requirements.txt
```

## 2) 配置环境变量

```bash
export QWEN_API_KEY="你的千问Key"
export QWEN_MODEL="qwen-plus"  # 可改成其他可用模型
export QWEN_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
export SQLITE_PATH="demo.db"
```

## 3) 启动

```bash
python app.py
```

## 4) 调用

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"统计每个月销售额"}'
```

返回包含：

- `sql`: Vanna 生成的 SQL
- `rows`: SQL 执行结果
- `plotly_code`: Vanna 生成的图表代码

## 关键点

在 `app.py` 里通过以下配置把 LLM 换成千问：

```python
config = {
    "model": "qwen-plus",
    "api_key": os.getenv("QWEN_API_KEY"),
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
}
```

`QwenVanna(ChromaDB_VectorStore, OpenAI_Chat)` 这个组合保留了 Vanna 的检索/SQL 生成链路，只是把 Chat 模型路由到了千问兼容接口。
