from fastapi import APIRouter
from store import connections  # Importamos la lista global
from fastapi import WebSocket

router = APIRouter()

@router.post("/{video_id}")
async def like_video(video_id: int):
    likes = 100  # Aquí actualizas tu DB real
    print(f"Video {video_id} liked, total likes: {likes}")
    # Publicamos a todos los WS conectados
    message = f'{{"event":"like_updated","video_id":{video_id},"likes":{likes}}}'
    for ws in connections:
        try:
            await ws.send_text(message)
        except:
            connections.remove(ws)

    return {"status": "success", "video_id": video_id, "likes": likes}
