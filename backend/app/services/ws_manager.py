from fastapi import WebSocket
from starlette.websockets import WebSocketState
from app.utils.log_util import logger


class WebSocketManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    def is_connected(self, websocket: WebSocket) -> bool:
        """检查 WebSocket 连接是否仍然活跃"""
        try:
            return (
                websocket in self.active_connections
                and websocket.client_state == WebSocketState.CONNECTED
                and websocket.application_state == WebSocketState.CONNECTED
            )
        except Exception as e:
            logger.warning(f"检查 WebSocket 连接状态时出错: {e}")
            return False

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """发送文本消息，带连接状态检查"""
        if not self.is_connected(websocket):
            logger.warning("WebSocket 连接已关闭，跳过消息发送")
            return
        
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"发送 WebSocket 消息失败: {e}")
            self.disconnect(websocket)

    async def send_personal_message_json(self, message: dict, websocket: WebSocket):
        """发送 JSON 消息，带连接状态检查"""
        if not self.is_connected(websocket):
            logger.warning("WebSocket 连接已关闭，跳过消息发送")
            return
        
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"发送 WebSocket JSON 消息失败: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        """广播消息到所有活跃连接"""
        disconnected = []
        for connection in self.active_connections:
            if not self.is_connected(connection):
                disconnected.append(connection)
                continue
            
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"广播消息失败: {e}")
                disconnected.append(connection)
        
        # 清理断开的连接
        for conn in disconnected:
            self.disconnect(conn)


ws_manager = WebSocketManager()

