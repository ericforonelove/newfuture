#!/bin/bash
# ============================================================
# 离线打包脚本 — 在有网机器上执行
# 生成 offline_bundle/ 目录，拷贝到内网服务器即可部署
# ============================================================
set -e

BUNDLE_DIR="offline_bundle"
echo "==> 创建离线包目录: $BUNDLE_DIR"
rm -rf "$BUNDLE_DIR"
mkdir -p "$BUNDLE_DIR"

# 1. 下载 Ollama 二进制
echo "==> 下载 Ollama Linux 二进制..."
curl -L -o "$BUNDLE_DIR/ollama" https://ollama.com/download/ollama-linux-amd64
chmod +x "$BUNDLE_DIR/ollama"

# 2. 导出模型文件
echo "==> 打包 Ollama 模型文件..."
if [ -d "$HOME/.ollama/models" ]; then
    tar czf "$BUNDLE_DIR/ollama-models.tar.gz" -C "$HOME/.ollama" models/
else
    echo "    [!] 未找到 ~/.ollama/models，请先运行: ollama pull qwen2.5:7b"
    echo "    跳过模型打包，你需要手动打包模型目录。"
fi

# 3. 下载 Python 依赖 wheel
echo "==> 下载 Python 依赖 wheel 包..."
mkdir -p "$BUNDLE_DIR/wheels"
pip download -r requirements.txt -d "$BUNDLE_DIR/wheels/"

# 4. 拷贝项目源码
echo "==> 拷贝项目源码..."
mkdir -p "$BUNDLE_DIR/src"
cp -r app.py config.py init_demo_db.py requirements.txt "$BUNDLE_DIR/src/"
cp -r deploy/ "$BUNDLE_DIR/src/deploy/"

# 5. 生成安装脚本
echo "==> 生成服务器端安装脚本..."
cat > "$BUNDLE_DIR/install.sh" << 'INSTALL_EOF'
#!/bin/bash
# 内网服务器上执行此脚本完成部署
set -e

echo "==> 安装 Ollama..."
sudo cp ollama /usr/local/bin/ollama
sudo chmod +x /usr/local/bin/ollama
sudo mkdir -p /opt/ollama

if [ -f ollama-models.tar.gz ]; then
    echo "==> 解压模型..."
    sudo tar xzf ollama-models.tar.gz -C /opt/ollama/
fi

echo "==> 部署项目..."
sudo mkdir -p /opt/vanna-qwen
sudo cp -r src/* /opt/vanna-qwen/
cd /opt/vanna-qwen

echo "==> 创建 Python 虚拟环境..."
python3 -m venv .venv
source .venv/bin/activate

echo "==> 离线安装 Python 依赖..."
pip install --no-index --find-links=/opt/vanna-qwen/../wheels/ -r requirements.txt 2>/dev/null || \
pip install --no-index --find-links="$(dirname "$0")/wheels/" -r requirements.txt

echo "==> 创建 systemd 服务..."
sudo tee /etc/systemd/system/ollama.service > /dev/null << 'SVC1'
[Unit]
Description=Ollama LLM Server
After=network.target

[Service]
Type=simple
Environment="OLLAMA_MODELS=/opt/ollama/models"
Environment="OLLAMA_HOST=0.0.0.0:11434"
ExecStart=/usr/local/bin/ollama serve
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
SVC1

sudo tee /etc/systemd/system/vanna-qwen.service > /dev/null << 'SVC2'
[Unit]
Description=Vanna Qwen Text-to-SQL Service
After=network.target ollama.service
Requires=ollama.service

[Service]
Type=simple
WorkingDirectory=/opt/vanna-qwen
Environment="PATH=/opt/vanna-qwen/.venv/bin:/usr/local/bin:/usr/bin"
ExecStart=/opt/vanna-qwen/.venv/bin/python app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVC2

sudo systemctl daemon-reload
sudo systemctl enable ollama vanna-qwen
sudo systemctl start ollama

echo ""
echo "==> 部署完成！"
echo "    1. 编辑 /opt/vanna-qwen/config.py 填入实际的数据库连接信息"
echo "    2. 启动服务: sudo systemctl start vanna-qwen"
echo "    3. 访问: http://$(hostname -I | awk '{print $1}'):8084"
INSTALL_EOF

chmod +x "$BUNDLE_DIR/install.sh"

echo ""
echo "============================================================"
echo "离线包已生成: $BUNDLE_DIR/"
echo ""
echo "内容："
ls -lh "$BUNDLE_DIR/"
echo ""
echo "下一步：将 $BUNDLE_DIR/ 整个目录拷贝到内网服务器，执行 install.sh"
echo "============================================================"
