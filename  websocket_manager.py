class WebSocketManager:
    def __init__(self):
        self.active_connections = []

    async def connect(self, ws):
        await ws.accept()
        self.active_connections.append(ws)

    async def disconnect(self, ws):
        self.active_connections.remove(ws)

    async def send_to_all(self, message: str):
        for ws in self.active_connections:
            await ws.send_text(message)

manager = WebSocketManager()
