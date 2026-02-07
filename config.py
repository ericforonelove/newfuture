# ---------- Qwen / OpenAI-compatible endpoint ----------
# 如果你用 Ollama 本地跑 qwen2.5:7b，默认地址如下；
# 如果用其他推理服务（vLLM / LMStudio / llama.cpp server），改成对应地址即可。
QWEN_BASE_URL = "http://localhost:11434/v1"   # Ollama 默认 OpenAI-compat 端口
QWEN_API_KEY  = "ollama"                       # Ollama 不校验 key，随便填
QWEN_MODEL    = "qwen2.5:7b"

# ---------- Database ----------
# 演示用 SQLite；换成 PostgreSQL / MySQL 只需改这里
DB_PATH = "demo.db"

# ---------- Vanna ChromaDB ----------
CHROMA_PATH = "./chroma_data"
