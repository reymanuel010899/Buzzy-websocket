from fastapi import FastAPI, WebSocket, Request
from routers import videos, likes
from store import connections
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Registro de rutas
app.include_router(videos.router, prefix="/videos")
app.include_router(likes.router, prefix="/likes")
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cambia esto en producción
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connections.append(ws)
    try:
        while True:
            data = await ws.receive_text()
            # Envía a todos los demás clientes conectados
            for conn in connections:
                if conn != ws:
                    await conn.send_text(f"Otro usuario dice: {data}")
    except:
        connections.remove(ws)

# Este endpoint recibe los eventos desde Django
@app.post("/broadcast-like/")
async def broadcast_like(request: Request):
    print("Evento recibido para broadcast")
    ws_data = await request.json()  # {"event":"like_updated","video_id":..., "likes":...}
    print("Datos del WS:", ws_data)
    # Enviar a todos los WS conectados
    for ws in connections:
        try:
            await ws.send_json(ws_data)
        except:
            connections.remove(ws)
    
    return {"status": "ok"}

@app.post("/create-comment/")
async def create_comment(request: Request):
    print("Evento recibido para broadcast")
    ws_data = await request.json()  # {"event":"create_comment","video_id":..., "likes":...}
    print("Datos del WS:", ws_data)
    # Enviar a todos los WS conectados
    for ws in connections:
        try:
            await ws.send_json(ws_data)
        except:
            connections.remove(ws)
    
    return {"status": "ok"}


@app.post("/create-view/")
async def create_view(request: Request):
    ws_data = await request.json()  # {"event":"create_view","video_id":..., "likes":...}
    print("Datos del WS:", ws_data)
    # Enviar a todos los WS conectados
    for ws in connections:
        try:
            await ws.send_json(ws_data)
        except:
            connections.remove(ws)
    
    return {"status": "ok"}

@app.post("/broadcast-follower/")
async def broadcast_follower(request: Request):
    ws_data = await request.json()
    print("Datos del WS:", ws_data)
    # Enviar a todos los WS conectados
    for ws in connections:
        try:
            await ws.send_json(ws_data)
        except:
            connections.remove(ws)
    
    return {"status": "ok"}

@app.post("/broadcast-story/")
async def broadcast_story(request: Request):
    ws_data = await request.json()
    for ws in connections:
        try:
            await ws.send_json(ws_data)
        except:
            connections.remove(ws)
    
    return {"status": "ok"}

@app.post("/broadcast-gift-story/")
async def broadcast_gift(request: Request):
    ws_data = await request.json()
    for ws in connections:
        try:
            await ws.send_json(ws_data)
        except:
            connections.remove(ws)
    
    return {"status": "ok"}
