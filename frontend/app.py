"""
Wren AI 语义层查询前端
用户提问 → Wren UI GraphQL → Wren AI (千问模型) → MDL语义层 → SQL → PostgreSQL → 数据 → 图表
"""

import os
import time

import pandas as pd
import plotly.express as px
import psycopg2
import requests
import streamlit as st

# ---- 配置 ----
# 通过 wren-ui GraphQL API 提问（自动处理 mdl_hash）
WREN_UI_ENDPOINT = os.getenv("WREN_UI_ENDPOINT", "http://wren-ui:3000")

PG_CONFIG = {
    "host": os.getenv("PG_HOST", "localhost"),
    "port": int(os.getenv("PG_PORT", "5432")),
    "user": os.getenv("PG_USER", "wrenai"),
    "password": os.getenv("PG_PASSWORD", "wrenai123"),
    "dbname": os.getenv("PG_DATABASE", "sales"),
}

st.set_page_config(page_title="Wren AI 智能数据分析", page_icon="📊", layout="wide")
st.title("📊 Wren AI 智能数据分析")
st.caption("用自然语言提问，AI 自动生成 SQL 查询并可视化结果")


# ---- GraphQL 工具 ----
def graphql(query: str, variables: dict = None) -> dict:
    """调用 wren-ui GraphQL API"""
    resp = requests.post(
        f"{WREN_UI_ENDPOINT}/api/graphql",
        json={"query": query, "variables": variables or {}},
        timeout=120,
    )
    data = resp.json()
    if "errors" in data:
        raise Exception(data["errors"][0].get("message", str(data["errors"])))
    return data.get("data", {})


def ask_wren_ai(question: str) -> dict:
    """通过 wren-ui GraphQL 提问，获取 AI 生成的 SQL"""
    # Step 1: 创建 asking task
    try:
        result = graphql(
            """
            mutation CreateAskingTask($data: AskingTaskInput!) {
                createAskingTask(data: $data) {
                    id
                }
            }
            """,
            {"data": {"question": question}},
        )
    except Exception as e:
        return {"error": f"创建任务失败: {e}"}

    task_id = result.get("createAskingTask", {}).get("id")
    if not task_id:
        return {"error": f"未获取到 taskId: {result}"}

    # Step 2: 轮询 asking task 结果
    for _ in range(120):
        try:
            result = graphql(
                """
                query GetAskingTask($taskId: String!) {
                    askingTask(taskId: $taskId) {
                        status
                        error {
                            code
                            message
                        }
                        candidates {
                            type
                            sql
                        }
                    }
                }
                """,
                {"taskId": task_id},
            )
        except Exception as e:
            return {"error": f"查询任务状态失败: {e}"}

        task = result.get("askingTask", {})
        status = task.get("status", "")

        if status == "FINISHED":
            candidates = task.get("candidates", [])
            if candidates:
                return {"sql": candidates[0].get("sql", ""), "candidates": candidates}
            return {"error": "AI 未生成 SQL"}

        elif status == "FAILED":
            error = task.get("error", {})
            msg = error.get("message", "未知错误") if error else "未知错误"
            return {"error": msg}

        elif status in ("STOPPED",):
            return {"error": "任务已取消"}

        time.sleep(2)

    return {"error": "查询超时（超过 4 分钟）"}


def run_sql(sql: str) -> pd.DataFrame:
    """直接在 PostgreSQL 上执行 SQL 并返回 DataFrame"""
    conn = psycopg2.connect(**PG_CONFIG)
    try:
        df = pd.read_sql(sql, conn)
        return df
    finally:
        conn.close()


def auto_chart(df: pd.DataFrame):
    """根据数据特征自动选择合适的图表类型"""
    if df.empty:
        st.warning("查询结果为空")
        return

    cols = df.columns.tolist()
    num_cols = df.select_dtypes(include="number").columns.tolist()
    date_cols = [c for c in cols if "date" in c.lower() or "time" in c.lower()]
    cat_cols = [c for c in cols if c not in num_cols and c not in date_cols]

    # 时间序列 → 折线图
    if date_cols and num_cols:
        fig = px.line(df, x=date_cols[0], y=num_cols[0],
                      title=f"{num_cols[0]} 随时间变化趋势")
        st.plotly_chart(fig, use_container_width=True)
        return

    # 分类 + 数值 → 柱状图
    if cat_cols and num_cols:
        if len(df) <= 20:
            fig = px.bar(df, x=cat_cols[0], y=num_cols[0],
                         title=f"按 {cat_cols[0]} 统计的 {num_cols[0]}")
        else:
            fig = px.bar(df.head(20), x=cat_cols[0], y=num_cols[0],
                         title=f"按 {cat_cols[0]} 统计的 {num_cols[0]} (前20)")
        st.plotly_chart(fig, use_container_width=True)
        return

    # 单数值列 → 直方图
    if num_cols:
        fig = px.histogram(df, x=num_cols[0], title=f"{num_cols[0]} 分布")
        st.plotly_chart(fig, use_container_width=True)
        return

    st.info("数据不适合自动绘图，请查看下方表格")


# ---- 侧边栏 ----
with st.sidebar:
    st.header("🔧 设置")
    mode = st.radio("查询模式", ["AI 自然语言", "直接 SQL"])

    st.divider()
    st.markdown("### 💡 示例问题")
    examples = [
        "每月总营收是多少？",
        "哪个产品卖得最好？",
        "各省份的客户数量分布",
        "2024年各类产品的销售额对比",
        "订单金额前10的客户",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True):
            st.session_state["question"] = ex

    st.divider()
    st.markdown(
        "**架构**: 用户问题 → Wren UI → Wren AI → SQL → PostgreSQL → 图表"
    )

# ---- 主界面 ----
question = st.text_input(
    "请输入您的问题：",
    value=st.session_state.get("question", ""),
    placeholder="例如：每月总营收是多少？",
)

if question:
    if mode == "AI 自然语言":
        with st.spinner("🤖 AI 正在理解您的问题并生成 SQL..."):
            result = ask_wren_ai(question)

        if "error" in result:
            st.error(f"查询失败: {result['error']}")
            # 回退：提供手动 SQL 输入
            fallback_sql = st.text_area("您也可以直接输入 SQL：")
            if fallback_sql:
                try:
                    df = run_sql(fallback_sql)
                    st.dataframe(df, use_container_width=True)
                    auto_chart(df)
                except Exception as e:
                    st.error(f"SQL 执行错误: {e}")
        else:
            sql = result.get("sql", "")
            if sql:
                with st.expander("📝 生成的 SQL", expanded=False):
                    st.code(sql, language="sql")

                # 显示其他候选 SQL
                candidates = result.get("candidates", [])
                if len(candidates) > 1:
                    with st.expander(f"📋 其他候选 SQL ({len(candidates)-1}个)"):
                        for i, c in enumerate(candidates[1:], 2):
                            st.code(c.get("sql", ""), language="sql")

                # 执行 SQL
                try:
                    df = run_sql(sql)
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        st.subheader("📋 数据结果")
                        st.dataframe(df, use_container_width=True)
                    with col2:
                        st.subheader("📈 可视化")
                        auto_chart(df)
                except Exception as e:
                    st.error(f"SQL 执行错误: {e}")
            else:
                st.warning("AI 未返回 SQL")

    else:  # 直接 SQL 模式
        sql = st.text_area("输入 SQL 查询：", height=120)
        if sql and st.button("执行查询"):
            try:
                df = run_sql(sql)
                st.dataframe(df, use_container_width=True)
                auto_chart(df)
            except Exception as e:
                st.error(f"SQL 执行错误: {e}")
