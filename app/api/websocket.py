from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from typing import List
import json
router = APIRouter()

connected_clients: List[WebSocket] = []


@router.websocket("/alerts")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    print("🟢 新客户端连接 WebSocket")
    try:
        while True:
            await websocket.receive_text()  # 保持连接活跃
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
        print("🔌 客户端断开 WebSocket")


# 推送函数，供外部调用
async def send_alert_message(level: str, message: str, alert_id: int = 1):
    data = {
        "id": alert_id,
        "level": level,
        "message": message
    }
    json_data = json.dumps(data)

    print(f"📡 推送消息给 {len(connected_clients)} 个客户端: {json_data}")

    # 使用 list 来遍历客户端连接
    disconnected_clients = []  # 用于保存断开连接的客户端
    for client in connected_clients:
        try:
            await client.send_text(json_data)
        except Exception as e:
            print(f"❌ WebSocket 推送失败: {e}")
            disconnected_clients.append(client)  # 记录无法推送的客户端

    # 移除断开连接的客户端
    for client in disconnected_clients:
        connected_clients.remove(client)
        print("🔌 从客户端列表中移除断开连接的客户端")
