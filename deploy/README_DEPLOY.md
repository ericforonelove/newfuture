# 内网 Linux 离线部署指南

## 整体架构

```
Linux 服务器
├── /opt/ollama/           # Ollama 二进制 + qwen2.5:7b 模型
├── /opt/vanna-qwen/       # 本项目代码 + Python 依赖
└── systemd services       # ollama + vanna-qwen 自启动
```

## 一、在有网机器上准备离线包

### 1.1 下载 Ollama 二进制

```bash
# 在有网机器上
curl -L https://ollama.com/download/ollama-linux-amd64 -o ollama
chmod +x ollama
```

### 1.2 导出 Qwen 模型文件

```bash
# 先在有网机器上拉取模型
ollama pull qwen2.5:7b

# 模型文件在 ~/.ollama/models/ 下，整个拷贝
tar czf ollama-models.tar.gz -C ~/.ollama models/
```

### 1.3 打包 Python 依赖（离线 wheel）

```bash
# 在有网机器上，把所有依赖下载为 wheel 包
pip download -r requirements.txt -d ./wheels/

# 打包
tar czf python-wheels.tar.gz wheels/
```

### 1.4 汇总离线包

最终需要拷贝到内网的文件：

```
ollama                    # Ollama 可执行文件（~150MB）
ollama-models.tar.gz      # 模型文件（~4.7GB）
python-wheels.tar.gz      # Python 依赖包（~500MB）
newfuture/                # 本项目源码
```

## 二、在内网 Linux 服务器上部署

### 2.1 部署 Ollama

```bash
# 放置 Ollama 二进制
sudo cp ollama /usr/local/bin/ollama
sudo chmod +x /usr/local/bin/ollama

# 解压模型到指定目录
sudo mkdir -p /opt/ollama
sudo tar xzf ollama-models.tar.gz -C /opt/ollama/

# 创建 Ollama 用户
sudo useradd -r -s /bin/false ollama
sudo chown -R ollama:ollama /opt/ollama
```

### 2.2 配置 Ollama systemd 服务

```bash
sudo tee /etc/systemd/system/ollama.service << 'EOF'
[Unit]
Description=Ollama LLM Server
After=network.target

[Service]
Type=simple
User=ollama
Group=ollama
Environment="OLLAMA_MODELS=/opt/ollama/models"
Environment="OLLAMA_HOST=0.0.0.0:11434"
ExecStart=/usr/local/bin/ollama serve
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ollama
sudo systemctl start ollama
```

验证：

```bash
curl http://localhost:11434/v1/models
# 应该能看到 qwen2.5:7b
```

### 2.3 部署项目

```bash
# 创建项目目录
sudo mkdir -p /opt/vanna-qwen
sudo cp -r newfuture/* /opt/vanna-qwen/
cd /opt/vanna-qwen

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 离线安装依赖
pip install --no-index --find-links=./wheels/ -r requirements.txt
```

### 2.4 修改 config.py

```bash
vi /opt/vanna-qwen/config.py
```

把 PostgreSQL 连接信息改成实际的 GaussDB 地址：

```python
PG_HOST     = "10.x.x.x"        # GaussDB 地址
PG_PORT     = 5432
PG_DATABASE = "production_db"
PG_USER     = "vanna_readonly"   # 建议用只读账号
PG_PASSWORD = "xxx"
```

### 2.5 配置 Vanna 服务自启动

```bash
sudo tee /etc/systemd/system/vanna-qwen.service << 'EOF'
[Unit]
Description=Vanna Qwen Text-to-SQL Service
After=network.target ollama.service
Requires=ollama.service

[Service]
Type=simple
User=root
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

### 2.6 验证

```bash
# 检查服务状态
sudo systemctl status ollama
sudo systemctl status vanna-qwen

# 检查端口
ss -tlnp | grep -E '11434|8084'

# 访问 Web UI
curl http://localhost:8084/health
```

浏览器访问 `http://<服务器IP>:8084`

## 三、安全建议

1. **数据库账号**：给 Vanna 创建只读账号，避免误操作
   ```sql
   CREATE USER vanna_readonly WITH PASSWORD 'xxx';
   GRANT CONNECT ON DATABASE production_db TO vanna_readonly;
   GRANT USAGE ON SCHEMA public TO vanna_readonly;
   GRANT SELECT ON ALL TABLES IN SCHEMA public TO vanna_readonly;
   ```

2. **网络隔离**：Ollama 只监听 localhost，不暴露到外网

3. **防火墙**：只开放 8084 端口给内网用户
   ```bash
   firewall-cmd --add-port=8084/tcp --permanent
   firewall-cmd --reload
   ```

## 四、常见问题

| 问题 | 解决 |
|------|------|
| Ollama 启动失败 | 检查 `OLLAMA_MODELS` 路径和文件权限 |
| 模型加载慢 | 首次加载需 30s+ 到内存，之后会快 |
| 连不上 GaussDB | 检查网络/防火墙/pg_hba.conf 白名单 |
| psycopg2 安装失败 | 离线包用 `psycopg2-binary`，不依赖 libpq-dev |
