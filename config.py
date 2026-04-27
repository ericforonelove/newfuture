# ---------- Qwen / OpenAI-compatible endpoint ----------
# Ollama 本地部署，通过 OpenAI-compatible 接口调用
QWEN_BASE_URL = "http://localhost:11434/v1"
QWEN_API_KEY  = "ollama"
QWEN_MODEL    = "qwen2.5:7b"

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

# ---------- Vanna ChromaDB ----------
CHROMA_PATH = "./chroma_data"

# ---------- Ollama 离线部署 ----------
# 模型文件存放目录（离线拷贝过来的）
OLLAMA_MODELS_DIR = "/opt/ollama/models"
