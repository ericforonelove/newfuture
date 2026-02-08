# Wren AI 智能数据分析平台

基于 Wren AI Engine + MDL 语义层 + 千问本地大模型的自然语言数据查询与可视化系统。

## 架构

```
用户问题 → Wren AI Engine → MDL语义层 → SQL → PostgreSQL
                ↓                              ↓
          千问模型(本地/Ollama)             数据 → 图表(Streamlit)
```

## 组件

| 服务 | 端口 | 说明 |
|------|------|------|
| PostgreSQL | 5432 | 数据存储 (销售示例数据) |
| Ollama | 11434 | 本地 LLM 服务 (千问 Qwen2.5) |
| Wren Engine | 8080 | SQL 引擎，连接 MDL 与数据源 |
| Wren AI Service | 5556 | AI 服务层，自然语言转 SQL |
| Wren UI | 3000 | 官方管理界面 |
| 自定义前端 | 8501 | Streamlit 问答 + 图表界面 |

## 快速开始

```bash
# 1. 启动所有服务
docker compose up -d

# 2. 拉取千问模型（首次需要）
bash scripts/setup-ollama.sh

# 3. 访问界面
#    自定义前端:  http://localhost:8501
#    Wren UI:    http://localhost:3000
```

## MDL 语义层

MDL (Modeling Definition Language) 定义在 `mdl/mdl.json`，包含：

- **模型**: customers, products, orders, order_items
- **关系**: 订单→客户, 订单明细→订单, 订单明细→产品
- **指标**: 总营收 (total_revenue), 订单数 (order_count)

语义层让 AI 理解业务含义，生成准确的 SQL。

## 示例问题

- 每月总营收是多少？
- 哪个产品卖得最好？
- 各省份的客户数量分布
- 2024年各类产品的销售额对比
- 订单金额前10的客户

## 目录结构

```
├── docker-compose.yml      # 服务编排
├── db/init.sql             # 数据库初始化和种子数据
├── mdl/mdl.json            # MDL 语义层定义
├── frontend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app.py              # Streamlit 前端应用
└── scripts/
    └── setup-ollama.sh     # 模型下载脚本
```
