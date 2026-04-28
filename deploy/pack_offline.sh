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

# 1. 下载 Python 依赖 wheel
echo "==> 下载 Python 依赖 wheel 包..."
mkdir -p "$BUNDLE_DIR/wheels"
pip download -r requirements.txt -d "$BUNDLE_DIR/wheels/"

# 2. 拷贝项目源码
echo "==> 拷贝项目源码..."
mkdir -p "$BUNDLE_DIR/src"
cp app.py config.py init_demo_db.py requirements.txt "$BUNDLE_DIR/src/"
cp -r deploy/ "$BUNDLE_DIR/src/deploy/"

# 3. 生成安装脚本
echo "==> 生成服务器端安装脚本..."
cat > "$BUNDLE_DIR/install.sh" << 'INSTALL_EOF'
#!/bin/bash
set -e

echo "==> 部署项目..."
sudo mkdir -p /opt/vanna-qwen
sudo cp -r src/* /opt/vanna-qwen/
cd /opt/vanna-qwen

echo "==> 创建 Python 虚拟环境..."
python3 -m venv .venv
source .venv/bin/activate

echo "==> 离线安装 Python 依赖..."
pip install --no-index --find-links="$(cd "$(dirname "$0")/wheels" && pwd)" -r requirements.txt

echo "==> 创建 systemd 服务..."
sudo tee /etc/systemd/system/vanna-qwen.service > /dev/null << 'SVC'
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
SVC

sudo systemctl daemon-reload
sudo systemctl enable vanna-qwen

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
ls -lh "$BUNDLE_DIR/"
echo ""
echo "拷贝 $BUNDLE_DIR/ 到内网服务器，执行 bash install.sh"
echo "============================================================"
