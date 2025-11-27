1. 系统总览与设计哲学1.1 核心定义SyncCanvas 是一个以后端为事实中心 (Backend-Authoritative) 的实时协作系统。与传统 WebSocket 广播不同，本系统的后端通过 pycrdt 维护着文档的完整内存状态。这意味着后端不仅仅是消息通道，更是一个拥有上帝视角的协作成员，它具备“审查”、“修改”甚至“创作”白板内容的能力（即 AI Agent）。1.2 关键性能指标 (KPIs)并发对象数: 单房间支持 5,000+ 图元流畅渲染与同步。同步延迟: 端到端 (End-to-End) 延迟 < 100ms。AI 响应成功率: 引入 jsonrepair 后，AI 指令解析成功率需达到 99% 以上。部署依赖: 单机 Python 环境 + 单文件 SQLite，零重型依赖。2. 深度技术栈选型2.1 后端 (The Brain)运行时: Python 3.10+ (使用 uv 管理)。Web 框架: FastAPI (基于 Starlette，原生 ASGI 异步)。核心引擎: pycrdt (基于 Rust 的 yrs 库，性能是纯 Python 的 10-100 倍)。数据清洗: jsonrepair (专门处理 LLM 输出的非标准 JSON)。持久化: aiosqlite (异步 SQLite 操作) + SQLAlchemy (ORM)。消息总线: Redis (可选，若单机运行可用 asyncio.Memory 替代，但建议保留 Redis 接口以备扩展)。2.2 前端 (The Face)框架: React 18 + TypeScript (严格类型)。Canvas 库: Konva.js / react-konva (支持层级、事件捕获、高性能渲染)。协作库: Yjs (前端 CRDT 实现)。网络层: y-websocket (标准 WebSocket 适配器)。状态管理: Zustand (用于 UI 状态，如工具栏选中项)。3. 详细数据结构定义 (Data Schema)这是项目最核心的部分。CRDT 的数据结构设计决定了协作的粒度。3.1 CRDT 文档结构 (Shared Types)我们不使用 Array 存储图形，而是使用 Map，以 UUID 为 Key。Root Doc:JSON{
  "shapes": Y.Map<UUID, Y.Map>,  // 存储所有图形
  "meta": Y.Map<String, Any>     // 存储画布元数据(背景色等)
}
3.2 图形对象模型 (Shape Model)每一个图形是一个嵌套的 Y.Map，包含以下字段。所有坐标均为世界坐标。字段名类型说明idStringUUID v4，唯一标识符typeString枚举: rect, circle, text, arrow, linexFloat世界坐标 XyFloat世界坐标 YwFloat宽度 (Width)hFloat高度 (Height)fillString填充颜色 Hex/RGBAstrokeString描边颜色strokeWidthInt描边粗细textString文本内容 (仅 Text 类型有效)lockedBoolean是否锁定 (禁止他人移动)4. 核心功能实现细节 (Implementation Details)4.1 无限画布坐标系统 (Infinite Canvas)前端必须实现视图变换 (Viewport Transform)。状态变量:scale: 缩放比例 (例如 1.0, 0.5, 2.0)。offset: 画布偏移量 {x, y}。屏幕转世界 (Screen -> World):用于将鼠标点击位置转换为图形存放位置。$$WorldX = (ClientX - OffsetX) / Scale$$世界转屏幕 (World -> Screen):用于 Canvas 渲染。$$ScreenX = WorldX * Scale + OffsetX$$4.2 实时同步协议 (Sync Protocol)通信完全基于 Binary (Uint8Array)，不传输明文 JSON。WebSocket 消息类型定义的伪代码:SYNC_STEP_1 (0): 客户端连接后发送。Payload: StateVector (我有哪些数据)。SYNC_STEP_2 (1): 服务端回复。Payload: Update (这是你缺少的数据二进制流)。UPDATE (2): 实时增量。Payload: Update (某人刚画的一笔)。后端处理逻辑 (FastAPI):Python@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await websocket.accept()
    # 1. 从 SQLite 加载房间历史快照
    doc = await load_room_doc(room_id)
    
    # 2. 创建同步协议处理器
    sync_handler = YSyncHandler(doc, websocket)
    
    try:
        while True:
            data = await websocket.receive_bytes()
            # pycrdt 处理数据合并
            message_type = data[0]
            if message_type == 0: # SyncStep1
                reply = create_sync_step_2(doc, data[1:])
                await websocket.send_bytes(reply)
            elif message_type == 2: # Update
                # 应用更新到后端内存 Doc
                doc.apply_update(data[1:])
                # 存入 SQLite (异步)
                await save_update(room_id, data[1:])
                # 广播给房间其他人
                await broadcast(room_id, data, exclude=websocket)
    except Exception:
        pass
4.3 AI 智能体流水线 (The AI Pipeline)这是本项目最复杂、技术含量最高的部分。流程图:用户 Prompt -> LLM 生成 -> jsonrepair 修复 -> Pydantic 校验 -> pycrdt 注入 -> WebSocket 广播Step 1: 提示词工程 (System Prompt)"你是一个绘图引擎。不要解释，只返回 JSON 数组。坐标系：x轴向右，y轴向下。可用类型：rect, circle, text, arrow。格式示例：[{'type':'rect', 'x':0, 'y':0, 'w':100, 'h':100, 'text':'Login'}]"Step 2: 鲁棒性解析 (Robust Parsing)Pythonimport json_repair
from pydantic import BaseModel, ValidationError

class AIShape(BaseModel):
    type: str
    x: float
    y: float
    w: float = 100
    h: float = 100
    text: str = ""

async def generate_shapes(prompt: str, doc: pycrdt.Doc):
    # 1. 调用 LLM (DeepSeek/OpenAI)
    raw_text = await llm_client.chat(prompt)
    
    # 2. 脏数据修复 (关键步骤)
    # 哪怕 AI 返回的是 ```json [ {x:1... } ``` 也能修好
    try:
        clean_json = json_repair.loads(raw_text)
    except Exception:
        return "AI生成失败，无法解析"

    # 3. 结构校验
    valid_shapes = []
    if isinstance(clean_json, list):
        for item in clean_json:
            try:
                shape = AIShape(**item)
                valid_shapes.append(shape)
            except ValidationError:
                continue # 丢弃坏掉的单个图形，保留其他的

    # 4. CRDT 事务注入
    shapes_map = doc.get_map("shapes")
    with doc.transaction():
        for shape in valid_shapes:
            new_id = str(uuid.uuid4())
            shapes_map[new_id] = shape.model_dump()
            
    # 5. 无需手动广播
    # 因为 pycrdt 的 observe 回调会自动捕获这次 transaction
    # 并通过 websocket 广播出去
5. 数据库详细设计 (SQLite)文件名: sync_canvas.db5.1 rooms 表字段类型约束说明idTEXTPRIMARY KEYUUIDnameTEXTNOT NULL房间名created_atINTEGERUnix 时间戳5.2 snapshots 表 (快照)存储文档在某个时刻的完整二进制状态。| 字段 | 类型 | 约束 | 说明 || :--- | :--- | :--- | :--- || id | INTEGER | PRIMARY KEY AUTOINCREMENT | || room_id | TEXT | INDEX | 关联 rooms.id || data | BLOB | NOT NULL | doc.get_state() 的结果 || timestamp | INTEGER | | 生成时间 |5.3 updates 表 (增量日志)存储自上次快照以来所有的细碎更新。| 字段 | 类型 | 约束 | 说明 || :--- | :--- | :--- | :--- || id | INTEGER | PRIMARY KEY AUTOINCREMENT | || room_id | TEXT | INDEX | 关联 rooms.id || data | BLOB | NOT NULL | 单个 Update 二进制流 || created_at | INTEGER | | |优化策略: 当一个房间的 updates 记录超过 50 条时，后端触发一次 Compact 操作：加载快照 + 应用所有 updates -> 生成新快照 -> 删除旧 updates。6. 开发与测试规划Phase 1: 基础架构搭建 (Environment)uv init: 配置 Python 环境。FastAPI Hello World: 跑通 HTTP 服务。WebSocket Echo: 跑通最简单的 WS 通信。Frontend Init: Vite + React + TypeScript + Konva。Phase 2: 单机白板实现 (Frontend Logic)Canvas 封装: 实现 Stage 和 Layer。视口逻辑: 绑定 Wheel 事件，实现 scale 和 offset 的计算。基础绘图: 实现拖拽生成矩形。Yjs 集成: 将本地图形状态存入 Y.Map，并监听 observe 事件触发重绘。Phase 3: 后端同步与持久化 (Backend Logic)pycrdt 引入: 后端接收 WS 二进制流，通过 pycrdt 解析。SQLite 写入: 将接收到的流存入 updates 表。初始加载: 用户连接时，读取 SQLite 数据并合并发送。多端测试: 打开两个浏览器窗口，验证同步是否正常。Phase 4: AI Agent 开发 (Intelligence)API 对接: 申请 DeepSeek/SiliconFlow Key。jsonrepair 集成: 编写单元测试，喂给它各种烂 JSON，确保能修好。Command 接口: 实现 POST /api/ai，触发后端修改 pycrdt 文档。效果调优: 优化 Prompt，让 AI 画出的流程图布局更合理（例如自动计算 x, y 坐标避免重叠）。7. 成果交付清单 (Deliverables)源代码: 包含 Backend (/server) 和 Frontend (/client) 的完整仓库。设计文档: 即本规划书的最终修订版。演示视频:展示 3 个客户端同时绘画的无延迟效果。展示输入一句话，屏幕自动生成复杂图表的过程。展示断网重连后，数据自动恢复的过程。性能报告: 说明在 SQLite + Python 架构下能支撑多少并发量。这份文档现在极其详尽，涵盖了变量名、数据库表结构、算法公式和关键代码逻辑。你可以根据这个蓝图直接开始写代码。建议先从 Phase 1 开始。