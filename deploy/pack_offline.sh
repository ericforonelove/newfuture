#!/bin/bash
# ============================================================
# 离线打包脚本 — 在有网机器上执行
#
# 用法：
#   bash deploy/pack_offline.sh docker   → 打包 Docker 镜像（推荐）
#   bash deploy/pack_offline.sh wheels   → 打包 Linux wheel 包
# ============================================================
set -e

MODE="${1:-docker}"
BUNDLE_DIR="offline_bundle"

echo "==> 打包模式: $MODE"
rm -rf "$BUNDLE_DIR"
mkdir -p "$BUNDLE_DIR"

# 拷贝项目源码
cp app.py config.py init_demo_db.py requirements.txt Dockerfile docker-compose.yml "$BUNDLE_DIR/"
cp -r deploy/ "$BUNDLE_DIR/deploy/"

if [ "$MODE" = "docker" ]; then
    # ========== Docker 镜像方式（推荐） ==========
    echo "==> 构建 Docker 镜像..."
    docker build -t vanna-qwen:latest .

    echo "==> 导出镜像为 tar 文件..."
    docker save vanna-qwen:latest -o "$BUNDLE_DIR/vanna-qwen-image.tar"

    cat > "$BUNDLE_DIR/install.sh" << 'EOF'
#!/bin/bash
set -e
echo "==> 导入 Docker 镜像..."
docker load -i vanna-qwen-image.tar

echo "==> 请先修改 config.py 中的数据库连接信息，然后启动："
echo "    docker compose up -d"
echo "    访问: http://$(hostname -I | awk '{print $1}'):8084"
EOF
    chmod +x "$BUNDLE_DIR/install.sh"

    echo ""
    echo "============================================================"
    echo "Docker 离线包已生成:"
    ls -lh "$BUNDLE_DIR/"
    echo ""
    echo "拷贝 $BUNDLE_DIR/ 到内网服务器后执行："
    echo "  1. 修改 config.py 中的数据库连接"
    echo "  2. bash install.sh"
    echo "  3. docker compose up -d"
    echo "============================================================"

elif [ "$MODE" = "wheels" ]; then
    # ========== Linux wheel 方式 ==========
    # 用 Docker 在 Linux 环境中下载正确平台的 wheel
    echo "==> 通过 Docker 下载 Linux 平台 wheel 包..."
    mkdir -p "$BUNDLE_DIR/wheels"

    docker run --rm \
        -v "$(pwd)/requirements.txt:/tmp/requirements.txt" \
        -v "$(pwd)/$BUNDLE_DIR/wheels:/tmp/wheels" \
        python:3.11-slim \
        pip download -r /tmp/requirements.txt -d /tmp/wheels/

    cat > "$BUNDLE_DIR/install.sh" << 'EOF'
#!/bin/bash
set -e
echo "==> 部署项目到 /opt/vanna-qwen ..."
sudo mkdir -p /opt/vanna-qwen
sudo cp app.py config.py init_demo_db.py requirements.txt /opt/vanna-qwen/

cd /opt/vanna-qwen
echo "==> 创建虚拟环境..."
python3 -m venv .venv
source .venv/bin/activate

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "==> 离线安装依赖..."
pip install --no-index --find-links="$SCRIPT_DIR/wheels/" -r requirements.txt

echo ""
echo "==> 安装完成！"
echo "    1. 修改 /opt/vanna-qwen/config.py 中的数据库连接"
echo "    2. source /opt/vanna-qwen/.venv/bin/activate && python app.py"
echo "    3. 访问: http://$(hostname -I | awk '{print $1}'):8084"
EOF
    chmod +x "$BUNDLE_DIR/install.sh"

    echo ""
    echo "============================================================"
    echo "Wheel 离线包已生成:"
    ls -lh "$BUNDLE_DIR/wheels/" | head -20
    echo "..."
    echo ""
    echo "拷贝 $BUNDLE_DIR/ 到内网服务器后执行 bash install.sh"
    echo "============================================================"

else
    echo "未知模式: $MODE"
    echo "用法: bash deploy/pack_offline.sh [docker|wheels]"
    exit 1
fi
