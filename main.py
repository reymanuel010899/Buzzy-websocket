import re
from typing import Optional
from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect
from routers import videos, likes
from jose import jwt, JWTError
from fastapi.middleware.cors import CORSMiddleware
from manager.websocket_manager import WebSocketManager
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

app = FastAPI()
manager = WebSocketManager()
# Registro de rutas
app.include_router(videos.router, prefix="/videos")
app.include_router(likes.router, prefix="/likes")
DJANGO_API_URL = os.getenv("DJANGO_API_URL")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_user_id_from_token(token: str) -> Optional[int]:
    token = token.replace("Bearer ", "").strip()
    try:
        print(token, "****")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print(payload, "****")
        return payload.get("user_id")
    except JWTError:
        print("Error decoding JWT:", JWTError)
        return None
    
@app.get("/")
async def root():
    return {
        "message": "Buzzy WS Server ON 🔥",
        "global_connections": len(manager.user_connections),
        "active_chats": len(manager.chat_rooms)
    }


async def update_user_online_status(user_id: int, is_online: bool, token: str=None, device_token: str=None):
    """
    Actualiza el estado online/offline del usuario en Django
    Se llama desde el WebSocket cuando conecta/desconecta
    """
    payload = {
        "user_id": user_id,
        "is_online": is_online,
        "device_token": device_token
    }
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        import httpx  # Mejor que requests en async
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{DJANGO_API_URL}/api/update-online-status/",
                json=payload,
                headers=headers,
                timeout=5.0
            )
    except Exception as e:
        print(f"Error actualizando online status para user {user_id}: {e}")
        # No rompemos el WebSocket por esto

@app.websocket("/ws")
async def websocket_endpoint(
    ws: WebSocket,
    user_id: Optional[int] = None,
    token: str = None
):
    await ws.accept()
    if not user_id:
        await ws.close(code=1008, reason="user_id requerido")
        return
    print("🔥 WS GLOBAL:", token)
    try:
        while True:
            data = await ws.receive_json()
            message_type = data.get("type")
            print("🔥 WS GLOBAL:", message_type)
            if message_type == "REGISTER":
                await update_user_online_status(user_id, is_online=True, token=token, device_token=data.get("device_token"))
                manager.add_user_socket(user_id, ws)
                await manager.connect_global(ws)
                await ws.send_json({
                    "type": "registered",
                    "user_id": user_id
                })

            elif message_type == "typing":
                await update_user_online_status(user_id, is_online=True, token=token)
                receiver_id = data.get("receiver_id")

                if not receiver_id:
                    continue

                await manager.send_to_user(
                    receiver_id,
                    {
                        "type": "typing",
                        "sender_id": user_id,
                        "is_typing": data.get("is_typing", False),
                    }, is_global=True
                )

    except WebSocketDisconnect:
        manager.remove_user_socket(user_id, ws)
        await update_user_online_status(user_id, is_online=False, token=token)

@app.websocket("/ws/chat/{chat_uuid}")
async def ws_chat(websocket: WebSocket, chat_uuid: str):
    await websocket.accept()
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008, reason="Token JWT requerido")
        return
    


    user_id = get_user_id_from_token(token)
    if not user_id:
        await websocket.close(code=1008, reason="Token JWT inválido")
        return

    manager.add_user_socket(user_id, websocket)
    await manager.connect_to_chat(websocket, chat_uuid)
    await update_user_online_status(user_id, is_online=True, token=token)
    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")
            receiver_id = data.get("receiver_id")

            if message_type == "message":
                # Agregar info del sender
                enriched_data = {
                    **data,
                    "sender_id": user_id,
                    "chat_uuid": chat_uuid
                }
          
                await manager.send_to_user(receiver_id, enriched_data)

            elif message_type == "typing" and chat_uuid:
                enriched_data = {
                    **data,
                    "sender_id": user_id,
                    "chat_uuid": chat_uuid
                }
            
                await manager.send_to_user(receiver_id, enriched_data, is_global=True)
            elif  message_type == "REGISTER":
                await update_user_online_status(user_id, is_online=True, token=token)
                manager.add_user_socket(user_id, websocket)

            elif message_type == "reaction":
                message_uuid = data.get("message_uuid")
                emoji = data.get("emoji")
                if message_uuid and emoji:
                    try:
                        import httpx
                        async with httpx.AsyncClient() as client:
                            resp = await client.post(
                                f"{DJANGO_API_URL}/api/messages/reaction/",
                                json={"message_uuid": message_uuid, "user_id": user_id, "emoji": emoji},
                                timeout=5.0
                            )
                            result = resp.json()  # {"action": "added" | "removed"}

                        # Broadcast to chat so both participants update in real time
                        await manager.broadcast_to_chat(chat_uuid, {
                            "event": "reaction",
                            "message_uuid": message_uuid,
                            "emoji": emoji,
                            "user_id": user_id,
                            "username": result.get("username", "Anónimo"),
                            "action": result.get("action", "added")
                        })
                    except Exception as e:
                        print(f"Error saving reaction: {e}")


    except WebSocketDisconnect:
        # await update_user_online_status(user_id, is_online=False)

        # ❌ Quitar socket del chat
        manager.disconnect_from_chat(websocket, chat_uuid)

        # ❌ Quitar SOLO ESTE socket del usuario
        if user_id:
            manager.remove_user_socket(user_id, websocket)

        if not manager.is_user_online(user_id):
            await update_user_online_status(user_id, is_online=False)

        # 🔔 Notificar al chat (opcional)
        await manager.broadcast_to_chat(chat_uuid, {
            "type": "user_offline",
            "user_id": user_id
        })

@app.post("/broadcast-call/")
async def broadcast_call(request: Request):
    data = await request.json()
    receiver_id = int(data.get('recipient_id'))
    if not receiver_id:
        return {"error": "recipient_id is requerido"}

    # Forward the call event to the specific user
    # type can be: incoming_call, call_accepted, call_rejected, etc.
    print(f"Broadcast call to {receiver_id}: {data}")
    await manager.send_to_user(receiver_id, data, is_global=False)
    return {"status": "broadcasted"}

@app.post("/broadcast-chat/")
async def broadcast_chat(request: Request):
    data = await request.json()
    data['event'] = 'send_message'

    chat_uuid = data.get("chat_uuid")
    receiver_id = int(data['recipient_id'])
    if not chat_uuid:
        return {
            "error": "chat_uuid es requerido"
        }

    enriched_data = {
            **data,
            }
    print("Broadcast chat:", enriched_data)
    await manager.send_to_user(receiver_id, enriched_data, is_global=False)
    return {"status": "broadcasted"}



@app.post("/broadcast-like/")
async def broadcast_like(request: Request):
    data = await request.json()
    print("Broadcast like:", data)
    await manager.send_event_to_users(
    user_ids={data.get("user_id"), data.get("video_user_id")},
    data=data
)
    return {"status": "broadcasted"}

@app.post("/create-comment/")
async def create_comment(request: Request):
    data = await request.json()
    await manager.send_event_to_users(
    user_ids={data.get("user_id").get("id"), data.get("video_user_id")},
    data=data
)

    return {"status": "broadcasted"}


@app.post("/create-view/")
async def create_view(request: Request):
    data = await request.json()
    await manager.send_event_to_users(
        user_ids={data.get("user_id"), data.get("video_user_id")},
        data=data
    )
    return {"status": "broadcasted"}


@app.post("/broadcast-follower/")
async def broadcast_follower(request: Request):
    data = await request.json()
    await manager.broadcast_global({"event": "new_follower", **data})
    return {"status": "broadcasted"}


@app.post("/broadcast-story/")
async def broadcast_story(request: Request):
    data = await request.json()
    await manager.broadcast_global({"event": "new_story", **data})
    return {"status": "broadcasted"}

@app.post("/broadcast-gift-story/")
async def broadcast_gift(request: Request):
    data = await request.json()
    await manager.broadcast_global({"event": "gift_received", **data})
    return {"status": "broadcasted"}


@app.post("/broadcast-video-ready/")
async def broadcast_video_ready(request: Request):
    data = await request.json()
    user_id = data.get("user_id")
    if not user_id:
        return {"error": "user_id requerido"}

    event_name = "video_ready" if data.get("status") == "ready" else "video_blocked"
    sockets = manager.user_connections.get(int(user_id), set())
    payload = {
        "event": event_name,
        "video_id": data.get("video_id"),
        "status": data.get("status"),
        "category": data.get("category"),
        "safety_label": data.get("safety_label"),
    }
    for ws in list(sockets):
        try:
            await ws.send_json(payload)
        except Exception:
            manager.remove_user_socket(int(user_id), ws)

    return {"status": "broadcasted", "event": event_name, "sockets": len(sockets)}

