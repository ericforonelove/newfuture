# 内网 Linux 服务器部署指南

## 整体架构

```
Linux 服务器
├── /opt/vanna-qwen/       # 本项目代码 + Python 依赖
└── systemd service        # vanna-qwen 自启动

外部依赖（已有）：
├── LLM 服务   → http://10.18.0.104:30111/v1/  (qwen3-30b-moe-normal)
└── 数据库     → PostgreSQL / GaussDB
```

## 一、在有网机器上准备离线包

### 1.1 打包 Python 依赖（离线 wheel）

```bash
pip download -r requirements.txt -d ./wheels/
tar czf python-wheels.tar.gz wheels/
```

### 1.2 汇总离线包

需要拷贝到内网的文件：

```
python-wheels.tar.gz      # Python 依赖包
newfuture/                # 本项目源码
```

不需要 Ollama，直接用内部模型服务 `10.18.0.104:30111`。

## 二、在内网 Linux 服务器上部署

### 2.1 部署项目

```bash
sudo mkdir -p /opt/vanna-qwen
sudo cp -r newfuture/* /opt/vanna-qwen/
cd /opt/vanna-qwen

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 离线安装依赖
pip install --no-index --find-links=./wheels/ -r requirements.txt
```

### 2.2 修改 config.py

```bash
vi /opt/vanna-qwen/config.py
```

填入实际的数据库连接信息：

```python
# LLM（已配好，无需修改）
QWEN_BASE_URL = "http://10.18.0.104:30111/v1/"
QWEN_API_KEY  = "aiap-2025"
QWEN_MODEL    = "openai/qwen3-30b-moe-normal"

# 数据库（改成你的实际地址）
PG_HOST     = "10.x.x.x"
PG_PORT     = 5432
PG_DATABASE = "production_db"
PG_USER     = "vanna_readonly"
PG_PASSWORD = "xxx"
```

### 2.3 配置 systemd 自启动

```bash
sudo tee /etc/systemd/system/vanna-qwen.service << 'EOF'
[Unit]
Description=Vanna Qwen Text-to-SQL Service
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/vanna-qwen
Environment="PATH=/opt/vanna-qwen/.venv/bin:/usr/local/bin:/usr/bin"
ExecStart=/opt/vanna-qwen/.venv/bin/python app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable vanna-qwen
sudo systemctl start vanna-qwen
```

### 2.4 验证

```bash
sudo systemctl status vanna-qwen
curl http://localhost:8084/health
```

浏览器访问 `http://<服务器IP>:8084`

## 三、安全建议

1. **数据库账号**：给 Vanna 创建只读账号
   ```sql
   CREATE USER vanna_readonly WITH PASSWORD 'xxx';
   GRANT CONNECT ON DATABASE production_db TO vanna_readonly;
   GRANT USAGE ON SCHEMA public TO vanna_readonly;
   GRANT SELECT ON ALL TABLES IN SCHEMA public TO vanna_readonly;
   ```

2. **防火墙**：只开放 8084 端口给内网用户
   ```bash
   firewall-cmd --add-port=8084/tcp --permanent
   firewall-cmd --reload
   ```
