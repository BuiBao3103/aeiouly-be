from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi import status
from typing import List, Set, Dict
from src.auth.dependencies import get_current_active_user, resolve_user_from_token
from sqlalchemy.orm import Session
from src.database import get_db
from src.auth.models import User


router = APIRouter(prefix="/notifications", tags=["notifications"])


class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.user_connections: Dict[int, Set[WebSocket]] = {}
        self.websocket_to_user: Dict[WebSocket, int] = {}

    async def connect(self, websocket: WebSocket, user_id: int, db: Session) -> None:
        await websocket.accept()
        self.active_connections.add(websocket)

        user_set = self.user_connections.get(user_id)
        if user_set is None:
            user_set = set()
            self.user_connections[user_id] = user_set

        was_empty = len(user_set) == 0
        user_set.add(websocket)
        self.websocket_to_user[websocket] = user_id

        if was_empty:
            # First connection for this user → set online
            db_user = db.query(User).filter(User.id == user_id).first()
            if db_user and not db_user.is_online:
                db_user.is_online = True
                db.commit()

    def disconnect(self, websocket: WebSocket, db: Session) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

        user_id = self.websocket_to_user.pop(websocket, None)
        if user_id is None:
            return

        user_set = self.user_connections.get(user_id)
        if user_set is None:
            return
        if websocket in user_set:
            user_set.remove(websocket)

        if len(user_set) == 0:
            # Last tab closed → set offline
            self.user_connections.pop(user_id, None)
            db_user = db.query(User).filter(User.id == user_id).first()
            if db_user and db_user.is_online:
                db_user.is_online = False
                db.commit()

    async def broadcast_text(self, message: str):
        to_remove: List[WebSocket] = []
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception:
                to_remove.append(connection)
        for ws in to_remove:
            try:
                self.disconnect(ws, db=None)  # best-effort cleanup without DB status update
            except TypeError:
                # disconnect requires db; remove from sets only
                if ws in self.active_connections:
                    self.active_connections.remove(ws)


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

    await manager.connect(websocket, user_id=user.id, db=db)
    try:
        while True:
            # Echo incoming messages back; keeps connection alive
            data = await websocket.receive_text()
            await websocket.send_text(f"echo: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket, db)


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


