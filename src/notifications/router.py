from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi import status
from typing import List, Set
from src.auth.dependencies import get_current_active_user, resolve_user_from_token
from sqlalchemy.orm import Session
from src.database import get_db


router = APIRouter(prefix="/notifications", tags=["notifications"])


class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_text(self, message: str):
        to_remove: List[WebSocket] = []
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception:
                to_remove.append(connection)
        for ws in to_remove:
            self.disconnect(ws)


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    # Authenticate via cookie, query, or subprotocol before accepting
    from src.config import settings
    token = websocket.cookies.get(settings.ACCESS_TOKEN_COOKIE_NAME)
    if not token:
        token = websocket.query_params.get("token")
    if not token:
        subproto = websocket.headers.get("sec-websocket-protocol")
        if subproto:
            parts = [p.strip() for p in subproto.split(",") if p.strip()]
            if parts:
                cand = parts[-1]
                token = cand[7:].strip() if cand.lower().startswith("bearer ") else cand

    user = resolve_user_from_token(token, db) if token else None
    if not user or not getattr(user, "is_active", False):
        await websocket.close(code=1008)
        return

    await manager.connect(websocket)
    try:
        while True:
            # Echo incoming messages back; keeps connection alive
            data = await websocket.receive_text()
            await websocket.send_text(f"echo: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.post("/broadcast", status_code=status.HTTP_202_ACCEPTED)
async def broadcast_notification(
    message: str,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    # Only admins can broadcast
    try:
        from src.auth.models import UserRole
        if getattr(current_user, "role", None) != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Chỉ admin mới có thể broadcast")
    except Exception:
        raise HTTPException(status_code=403, detail="Chỉ admin mới có thể broadcast")

    await manager.broadcast_text(message)
    return {"sent": True, "message": message}


