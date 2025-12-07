from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def list_videos():
    # Ejemplo de respuesta, reemplaza con DB real
    return [
        {"id": 1, "likes": 20, "title": "Video 1"},
        {"id": 2, "likes": 55, "title": "Video 2"}
    ]
