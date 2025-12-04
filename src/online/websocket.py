from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from src.database import get_db
from src.auth.dependencies import resolve_user_from_websocket
from src.online.dependencies import get_connection_manager


async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time streak tracking and notifications.
    
    ## Authentication
    - Requires authentication via cookies (access_token cookie)
    - Token is automatically sent by browser if user is logged in
    - Returns 1008 (Unauthorized) if authentication fails
    
    ## How it works:
    
    1. **Connection**: User connects to `/online/ws` with valid authentication
    2. **Daily Streak Check**: On first connection of the day:
       - Checks if yesterday had a streak
       - If yesterday had no streak → resets current_streak to 0
       - If today has no streak yet → starts a 5-minute timer
    3. **5-Minute Timer**: 
       - User must stay online for 5 minutes to earn streak for the day
       - If user disconnects before 5 minutes → no streak for today
       - After 5 minutes (if still online):
         - If yesterday had streak → current_streak += 1
         - If yesterday had no streak → current_streak = 1 (restart)
         - Creates LoginStreakDaily record (has_streak = true)
         - Sends notification: "🎉 Bạn đã duy trì streak!"
    
    ## Messages:
    - Server may send text messages for streak updates
    - Client can send any text (currently not processed, just keeps connection alive)
    
    ## Disconnection:
    - If user disconnects before 5-minute timer completes → timer is cancelled
    - User must reconnect and stay online for 5 minutes to earn streak
    
    ## Example:
    ```javascript
    const ws = new WebSocket('ws://localhost:8000/online/ws');
    ws.onopen = () => console.log('Connected');
    ws.onmessage = (event) => console.log('Message:', event.data);
    ws.onerror = (error) => console.error('Error:', error);
    ws.onclose = (event) => console.log('Disconnected:', event.code, event.reason);
    ```
    """
    db = next(get_db())
    try:
        user = resolve_user_from_websocket(websocket, db)
        
        if not user:
            await websocket.close(code=1008, reason="Unauthorized")
            return

        # Get connection manager
        manager = get_connection_manager()
        
        # Connect user (accepts connection and adds to connections)
        await manager.connect(websocket, user.id, db)

        try:
            # Keep connection alive and listen for messages
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            await manager.disconnect(websocket, db)
        except Exception:
            await manager.disconnect(websocket, db)
            raise
    finally:
        db.close()

