from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi import status
from src.auth.dependencies import get_current_active_user, resolve_user_from_token
from sqlalchemy.orm import Session
from src.database import get_db
from src.users.models import User
from src.notifications.connection_manager import ConnectionManager
from src.notifications.schemas import BroadcastRequest, ConnectionStatus
from src.notifications.dependencies import get_connection_manager


router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    # Authenticate via cookie, query, or subprotocol before accepting
    from src.config import settings
    token = websocket.cookies.get(settings.ACCESS_TOKEN_COOKIE_NAME)
    
    if not token:
        # Try to get token from query parameters
        query_params = websocket.query_params
        token = query_params.get("token")
    
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication required")
        return
    
    try:
        # Resolve user from token
        user = resolve_user_from_token(token, db)
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
            return
    except Exception as e:
        print(f"WebSocket authentication error: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed")
        return
    
    # Get connection manager
    manager = get_connection_manager()
    
    # Connect user
    await manager.connect(websocket, user.id, db)
    
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            
            # Handle ping/pong for connection health
            if data == "ping":
                await websocket.send_text("pong")
            elif data == "pong":
                # Client responded to our ping
                pass
            else:
                # Echo back other messages
                await websocket.send_text(f"Echo: {data}")
                
    except WebSocketDisconnect:
        # User disconnected
        await manager.disconnect(websocket, db)
    except Exception as e:
        print(f"WebSocket error: {e}")
        await manager.disconnect(websocket, db)


@router.post("/broadcast", response_model=dict)
async def broadcast_notification(
    request: BroadcastRequest,
    current_user: User = Depends(get_current_active_user),
    manager: ConnectionManager = Depends(get_connection_manager)
):
    """Broadcast a notification to all connected users (Admin only)"""
    # Check if user is admin
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can broadcast notifications"
        )
    
    # Broadcast the message
    await manager.broadcast(request.message)
    
    return {
        "message": "Notification broadcasted successfully",
        "broadcasted_message": request.message,
        "total_connections": len(manager.active_connections)
    }


@router.get("/status", response_model=ConnectionStatus)
async def get_connection_status(
    current_user: User = Depends(get_current_active_user),
    manager: ConnectionManager = Depends(get_connection_manager)
):
    """Get current WebSocket connection status (Admin only)"""
    # Check if user is admin
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view connection status"
        )
    
    return ConnectionStatus(
        connected=True,
        total_connections=len(manager.active_connections),
        user_connections=len(manager.user_connections)
    )