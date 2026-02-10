"""
Wren AI 语义层查询前端
用户提问 → Wren AI (千问模型) → MDL语义层 → SQL → PostgreSQL → 数据 → 图表
"""

import os
import time

import pandas as pd
import plotly.express as px
import psycopg2
import requests
import streamlit as st

# ---- 配置 ----
# wren-ai-service 内部 API（需要 mdl_hash）
WREN_AI_ENDPOINT = os.getenv("WREN_AI_ENDPOINT", "http://localhost:5555")
# wren-ui API（自动处理 mdl_hash）
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


# ---- 工具函数 ----
def get_deploy_hash() -> str:
    """从 wren-ui 获取当前部署的 mdl_hash"""
    query = """
    query {
      listModels {
        id
      }
    }
    """
    # 尝试通过 GraphQL 获取最新 deploy hash
    try:
        resp = requests.post(
            f"{WREN_UI_ENDPOINT}/api/graphql",
            json={"query": "{ deploy { hash } }"},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            deploy = data.get("data", {}).get("deploy", {})
            if deploy and deploy.get("hash"):
                return deploy["hash"]
    except Exception:
        pass

    # 回退：直接调用 wren-ui 内部接口获取 mdl hash
    try:
        resp = requests.get(f"{WREN_UI_ENDPOINT}/api/config", timeout=10)
        if resp.status_code == 200:
            return resp.json().get("mdlHash", "")
    except Exception:
        pass

    return ""


def ask_wren_ai(question: str) -> dict:
    """向 Wren AI 发送自然语言问题，获取 SQL"""
    # 先获取 deploy hash
    mdl_hash = get_deploy_hash()

    # 构建请求体（与 wrenAIAdaptor.ts 中 ask() 方法一致）
    payload = {
        "query": question,
        "histories": [],
    }
    if mdl_hash:
        payload["id"] = mdl_hash

    resp = requests.post(
        f"{WREN_AI_ENDPOINT}/v1/asks",
        json=payload,
        timeout=120,
    )
    if resp.status_code != 200:
        return {"error": f"API 返回 {resp.status_code}: {resp.text}"}
    query_id = resp.json().get("query_id")

    # 轮询等待结果
    for _ in range(120):
        result = requests.get(
            f"{WREN_AI_ENDPOINT}/v1/asks/{query_id}/result",
            timeout=10,
        )
        if result.status_code != 200:
            return {"error": f"结果查询失败: {result.status_code}"}
        data = result.json()

        status = data.get("status")
        if status == "finished":
            return data
        elif status == "failed":
            error = data.get("error", {})
            if isinstance(error, dict):
                msg = error.get("message", str(error))
            else:
                msg = str(error)
            return {"error": msg or "查询失败"}

        time.sleep(2)

    return {"error": "查询超时"}


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
        "**架构**: 用户问题 → Wren AI → MDL → SQL → PostgreSQL → 图表"
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
            # 显示生成的 SQL
            steps = result.get("response", [])
            if steps:
                sql = steps[0].get("sql", "")
                with st.expander("📝 生成的 SQL", expanded=False):
                    st.code(sql, language="sql")

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

    else:  # 直接 SQL 模式
        sql = st.text_area("输入 SQL 查询：", height=120)
        if sql and st.button("执行查询"):
            try:
                df = run_sql(sql)
                st.dataframe(df, use_container_width=True)
                auto_chart(df)
            except Exception as e:
                st.error(f"SQL 执行错误: {e}")
