#!/bin/bash
# 拉取千问模型和嵌入模型到 Ollama
set -e

echo "等待 Ollama 服务启动..."
until curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; do
    sleep 2
done

echo "拉取千问 Qwen2.5 7B 模型..."
docker compose exec ollama ollama pull qwen2.5:7b

echo "拉取嵌入模型 nomic-embed-text..."
docker compose exec ollama ollama pull nomic-embed-text

echo "模型准备完成！"
