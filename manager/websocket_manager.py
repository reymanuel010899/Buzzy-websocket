from typing import Dict, Set
from fastapi import WebSocket

class WebSocketManager:
    def __init__(self):
        self.global_connections: Set[WebSocket] = set()
        self.chat_rooms: Dict[str, Set[WebSocket]] = {}
        self.user_connections: Dict[int, Set[WebSocket]] = {}


    # ---------- USER SOCKETS ----------
    def add_user_socket(self, user_id: int, ws: WebSocket):
        current = self.user_connections.get(user_id)

        # 👇 Si no existe o está mal tipado, lo corregimos
        if not isinstance(current, set):
            self.user_connections[user_id] = set()

        self.user_connections[user_id].add(ws)

        print(
            f"User {user_id} sockets:",
            len(self.user_connections[user_id])
        )

    def is_user_online(self, user_id: int) -> bool:
        return user_id in self.user_connections

    def remove_user_socket(self, user_id: int, ws: WebSocket):
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(ws)

            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

    async def send_to_user(self, user_id: int, message: dict, is_global: bool):
        sockets = self.user_connections.get(user_id, set())
        print(f"Sending to user {user_id} on {len(sockets)} sockets: {message}")
        if is_global:
            message['event'] = 'typing'
        else:
            message['event'] = 'send_message'
            
        for ws in list(sockets):
            try:
                e = await ws.send_json(message)
                print(f"Sent to user {user_id} socket: {e}")
            except:
                print(f"Failed to send to user {user_id} socket, removing it.")
                self.remove_user_socket(user_id, ws)

    # ---------- GLOBAL ----------
    async def connect_global(self, ws: WebSocket):
        self.global_connections.add(ws)

    def disconnect_global(self, ws: WebSocket):
        self.global_connections.discard(ws)

    # ---------- CHAT ----------
    async def connect_to_chat(self, ws: WebSocket, chat_uuid: str):
        self.chat_rooms.setdefault(chat_uuid, set()).add(ws)

    def disconnect_from_chat(self, ws: WebSocket, chat_uuid: str):
        connections = self.chat_rooms.get(chat_uuid)
        if connections:
            connections.discard(ws)
            if not connections:
                del self.chat_rooms[chat_uuid]

    async def broadcast_global(self, data: dict):
        await self._safe_broadcast(self.global_connections, data)

    async def broadcast_to_chat(self, chat_uuid: str, data: dict):
        connections = self.chat_rooms.get(chat_uuid, set())
        await self._safe_broadcast(connections, data)

    async def _safe_broadcast(self, connections: Set[WebSocket], data: dict):
        disconnected = set()
        for ws in connections:
            try:
                await ws.send_json(data)
            except:
                disconnected.add(ws)

        for ws in disconnected:
            connections.discard(ws)
