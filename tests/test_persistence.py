"""
@Time: 2025-11-26
@Author: AI Assistant
@Desc: 持久化验证脚本

模拟 WebSocket 客户端连接，发送更新，并验证数据库中是否保存了更新。
"""

import asyncio
import json
import sqlite3
import time
from websockets.client import connect
from pycrdt import Doc, Map

DB_PATH = "sync_canvas.db"
WS_URL = "ws://localhost:8021/ws/default-room"


async def test_persistence():
    print("开始持久化测试...")

    # 1. 连接 WebSocket 并发送更新
    async with connect(WS_URL) as websocket:
        print("已连接 WebSocket")

        # 接收 SyncStep1
        await websocket.recv()

        # 创建一个本地 Doc 并生成更新
        doc = Doc()
        shapes = doc.get("shapes", type=Map)

        with doc.transaction():
            shapes["test-shape"] = {
                "type": "rect",
                "x": 10,
                "y": 10,
                "w": 100,
                "h": 100,
            }

        update = doc.get_update()

        # 发送 Update 消息 (Sync protocol: type 0, step 2)
        msg = b"\x00\x02" + update
        await websocket.send(msg)
        print("已发送更新")

        # 等待服务器处理
        await asyncio.sleep(1)

    # 2. 验证数据库
    print("验证数据库...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT count(*) FROM 'update' WHERE room_id='default-room'")
    count = cursor.fetchone()[0]
    print(f"Updates 表记录数: {count}")

    if count > 0:
        print("✅ 持久化测试通过: 数据库中找到了更新记录")
    else:
        print("❌ 持久化测试失败: 数据库中未找到更新记录")

    conn.close()


if __name__ == "__main__":
    asyncio.run(test_persistence())
