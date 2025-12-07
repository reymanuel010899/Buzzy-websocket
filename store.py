# store.py
from typing import List
from fastapi import WebSocket

connections: List[WebSocket] = []
