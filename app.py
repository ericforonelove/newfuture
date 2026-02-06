import os
import sqlite3
from typing import Any

import pandas as pd
from flask import Flask, jsonify, request
from vanna.chromadb import ChromaDB_VectorStore
from vanna.openai import OpenAI_Chat


class QwenVanna(ChromaDB_VectorStore, OpenAI_Chat):
    """Use Vanna flow while routing LLM calls to Qwen via OpenAI-compatible endpoint."""

    def __init__(self, config: dict[str, Any]):
        ChromaDB_VectorStore.__init__(self, config=config)
        OpenAI_Chat.__init__(self, config=config)


def build_vn() -> QwenVanna:
    config = {
        "model": os.getenv("QWEN_MODEL", "qwen-plus"),
        "api_key": os.getenv("QWEN_API_KEY", ""),
        "base_url": os.getenv(
            "QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
        ),
    }
    if not config["api_key"]:
        raise RuntimeError("Missing QWEN_API_KEY.")

    vn = QwenVanna(config=config)

    # SQLite demo; replace with your production connector.
    db_path = os.getenv("SQLITE_PATH", "demo.db")
    conn = sqlite3.connect(db_path)
    vn.run_sql = lambda sql: pd.read_sql_query(sql, conn)

    return vn


vn = build_vn()
app = Flask(__name__)


@app.get("/health")
def health() -> tuple[dict[str, str], int]:
    return {"status": "ok"}, 200


@app.post("/ask")
def ask() -> tuple[dict[str, Any], int]:
    payload = request.get_json(silent=True) or {}
    question = (payload.get("question") or "").strip()
    if not question:
        return {"error": "question is required"}, 400

    try:
        sql = vn.generate_sql(question=question)
        df = vn.run_sql(sql)
        fig = vn.generate_plotly_code(question=question, sql=sql, df_metadata=str(df.dtypes))

        return (
            {
                "question": question,
                "sql": sql,
                "rows": df.to_dict(orient="records"),
                "plotly_code": fig,
            },
            200,
        )
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}, 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
