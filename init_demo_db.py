"""
创建一个演示用的 SQLite 数据库，包含 employees / departments / sales 三张表。
运行一次即可：python init_demo_db.py
"""

import sqlite3
import config

def create_demo_db():
    conn = sqlite3.connect(config.DB_PATH)
    cur = conn.cursor()

    # ---------- departments ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS departments (
            id   INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        )
    """)
    cur.executemany(
        "INSERT OR IGNORE INTO departments (id, name) VALUES (?, ?)",
        [
            (1, "工程部"),
            (2, "市场部"),
            (3, "销售部"),
            (4, "人事部"),
        ],
    )

    # ---------- employees ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id            INTEGER PRIMARY KEY,
            name          TEXT NOT NULL,
            department_id INTEGER REFERENCES departments(id),
            salary        REAL,
            hire_date     TEXT
        )
    """)
    cur.executemany(
        "INSERT OR IGNORE INTO employees (id, name, department_id, salary, hire_date) VALUES (?, ?, ?, ?, ?)",
        [
            (1,  "张三", 1, 15000, "2021-03-15"),
            (2,  "李四", 1, 18000, "2020-07-01"),
            (3,  "王五", 2, 12000, "2022-01-10"),
            (4,  "赵六", 3, 20000, "2019-11-20"),
            (5,  "孙七", 3, 16000, "2021-06-05"),
            (6,  "周八", 4, 13000, "2023-02-28"),
            (7,  "吴九", 1, 22000, "2018-09-12"),
            (8,  "郑十", 2, 14000, "2022-08-18"),
            (9,  "钱一", 3, 17000, "2020-04-22"),
            (10, "冯二", 4, 11000, "2023-07-01"),
        ],
    )

    # ---------- sales ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id          INTEGER PRIMARY KEY,
            employee_id INTEGER REFERENCES employees(id),
            amount      REAL,
            sale_date   TEXT
        )
    """)
    cur.executemany(
        "INSERT OR IGNORE INTO sales (id, employee_id, amount, sale_date) VALUES (?, ?, ?, ?)",
        [
            (1,  4, 50000,  "2024-01-15"),
            (2,  5, 35000,  "2024-01-20"),
            (3,  9, 42000,  "2024-02-05"),
            (4,  4, 60000,  "2024-02-18"),
            (5,  5, 28000,  "2024-03-01"),
            (6,  9, 55000,  "2024-03-12"),
            (7,  4, 70000,  "2024-04-08"),
            (8,  5, 33000,  "2024-04-22"),
            (9,  9, 48000,  "2024-05-10"),
            (10, 4, 45000,  "2024-05-25"),
        ],
    )

    conn.commit()
    conn.close()
    print(f"演示数据库已创建: {config.DB_PATH}")


if __name__ == "__main__":
    create_demo_db()
