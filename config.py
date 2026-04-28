# ---------- LLM (内部模型服务，OpenAI-compatible 接口) ----------
QWEN_BASE_URL = "http://10.18.0.104:30111/v1/"
QWEN_API_KEY  = "aiap-2025"
QWEN_MODEL    = "openai/qwen3-30b-moe-normal"

# ---------- Database (PostgreSQL / GaussDB) ----------
PG_HOST     = "192.168.1.100"       # 改成你的数据库 IP
PG_PORT     = 5432                   # GaussDB 默认也是 5432
PG_DATABASE = "your_database"
PG_USER     = "your_username"
PG_PASSWORD = "your_password"
# 可选额外参数（GaussDB 可能需要 sslmode）
PG_EXTRA    = {
    # "sslmode": "require",
    # "connect_timeout": 10,
}

# ---------- Embedding (内部嵌入模型) ----------
EMBED_BASE_URL = "http://10.18.0.104:30111/v1/"
EMBED_API_KEY  = "aiap-2025"
EMBED_MODEL    = "openai/em01"

# ---------- Vanna ChromaDB ----------
CHROMA_PATH = "./chroma_data"
