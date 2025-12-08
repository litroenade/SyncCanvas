"""数据库迁移脚本

为 Room 表添加新字段：
- elements_count: 画布元素数量
- total_contributors: 历史贡献者数量  
- last_active_at: 最后活跃时间
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "sync_canvas.db"


def migrate():
    """执行数据库迁移"""
    if not DB_PATH.exists():
        print(f"数据库文件不存在: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 获取 room 表的现有列
    cursor.execute("PRAGMA table_info(room)")
    columns = {row[1] for row in cursor.fetchall()}
    print(f"Room 表现有列: {columns}")

    # 添加缺失的列
    migrations = [
        ("elements_count", "INTEGER DEFAULT 0"),
        ("total_contributors", "INTEGER DEFAULT 0"),
        ("last_active_at", "INTEGER DEFAULT NULL"),
    ]

    for col_name, col_type in migrations:
        if col_name not in columns:
            try:
                sql = f"ALTER TABLE room ADD COLUMN {col_name} {col_type}"
                cursor.execute(sql)
                print(f"已添加列: {col_name}")
            except sqlite3.OperationalError as e:
                print(f"添加列 {col_name} 失败: {e}")
        else:
            print(f"列已存在: {col_name}")

    conn.commit()
    conn.close()
    print("迁移完成!")


if __name__ == "__main__":
    migrate()

