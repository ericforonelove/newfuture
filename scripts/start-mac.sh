#!/bin/bash
# Mac Apple Silicon (M1/M2/M3/M4/M5) 一键启动脚本
set -e

echo "========================================="
echo "  Wren AI 智能数据分析 - Mac 启动脚本"
echo "========================================="

# ---- 1. 检查 Docker ----
if ! command -v docker &> /dev/null; then
    echo "❌ 请先安装 Docker Desktop: brew install --cask docker"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "❌ Docker Desktop 未运行，请先启动 Docker Desktop"
    exit 1
fi

echo "✅ Docker 已就绪"

# ---- 2. 检查/安装 Ollama (宿主机原生运行，利用 Metal GPU) ----
if ! command -v ollama &> /dev/null; then
    echo "📦 安装 Ollama..."
    if command -v brew &> /dev/null; then
        brew install ollama
    else
        echo "请手动安装 Ollama: https://ollama.ai/download"
        exit 1
    fi
fi

echo "✅ Ollama 已安装"

# ---- 3. 启动 Ollama 服务（如果没运行） ----
if ! curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "🚀 启动 Ollama 服务..."
    ollama serve &
    sleep 3
fi

echo "✅ Ollama 服务运行中"

# ---- 4. 拉取千问模型 ----
echo "📥 拉取千问 Qwen2.5 7B 模型（首次约 4.7GB，请耐心等待）..."
ollama pull qwen2.5:7b

echo "📥 拉取嵌入模型 nomic-embed-text..."
ollama pull nomic-embed-text

echo "✅ 模型准备完成"

# ---- 5. 使用 Mac 专用 compose 启动（排除容器内 Ollama） ----
echo "🐳 启动 Docker 服务..."
docker compose -f docker-compose.yml -f docker-compose.mac.yml up -d

echo ""
echo "========================================="
echo "  🎉 启动完成！"
echo "========================================="
echo ""
echo "  📊 自定义前端:  http://localhost:8501"
echo "  🖥  Wren UI:    http://localhost:3000"
echo "  🗄  PostgreSQL: localhost:5432"
echo ""
echo "  💡 示例问题: 每月总营收是多少？"
echo "========================================="
