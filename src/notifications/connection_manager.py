from fastapi import WebSocket
from typing import Set, Dict
from sqlalchemy.orm import Session
from src.analytics.service import LearningAnalyticsService
from src.users.models import User
from datetime import datetime, date
import asyncio


class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.user_connections: Dict[int, Set[WebSocket]] = {}
        self.websocket_to_user: Dict[WebSocket, int] = {}
        self.learning_timers: Dict[int, asyncio.Task] = {}  # Track 60-minute learning timers

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
            # First connection for this user → set online status
            await self._set_user_online_status(user_id, True, db)
            
            # Start learning session and 60-minute timer
            await self._start_learning_tracking(user_id, db)

    async def disconnect(self, websocket: WebSocket, db: Session) -> None:
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
            # Last connection for this user → set offline status
            self.user_connections.pop(user_id, None)
            try:
                db.rollback()  # Rollback any failed transaction first
                await self._set_user_online_status(user_id, False, db)
                await self._stop_learning_tracking(user_id, db)
            except Exception as e:
                print(f"Error in disconnect for user {user_id}: {e}")
                db.rollback()

    async def _set_user_online_status(self, user_id: int, is_online: bool, db: Session) -> None:
        """Set user's online status"""
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.is_online = is_online
                db.commit()
        except Exception as e:
            print(f"Error setting online status for user {user_id}: {e}")
            db.rollback()

    async def _start_learning_tracking(self, user_id: int, db: Session) -> None:
        """Start learning session and timer for periodic notifications"""
        try:
            # Start learning session
            learning_service = LearningAnalyticsService()
            await learning_service.start_learning_session(user_id, db)
            
            # Start 30-minute timer for periodic notifications
            timer_task = asyncio.create_task(self._learning_timer(user_id, db, learning_service))
            self.learning_timers[user_id] = timer_task
            
        except Exception as e:
            print(f"Error starting learning tracking for user {user_id}: {e}")
            db.rollback()

    async def _stop_learning_tracking(self, user_id: int, db: Session) -> None:
        """Stop learning session and timer"""
        try:
            # End learning session
            learning_service = LearningAnalyticsService()
            await learning_service.end_learning_session(user_id, db)
            
            # Cancel timer
            if user_id in self.learning_timers:
                self.learning_timers[user_id].cancel()
                del self.learning_timers[user_id]
        except Exception as e:
            print(f"Error stopping learning tracking for user {user_id}: {e}")
            db.rollback()

    async def _learning_timer(self, user_id: int, db: Session, learning_service: LearningAnalyticsService) -> None:
        """30-minute learning timer that sends notifications"""
        try:
            while True:
                await asyncio.sleep(1800)  # Wait 30 minutes (1800 seconds)
                
                # Check if user is still online
                if user_id not in self.user_connections:
                    break
                
                try:
                    # Get today's learning stats only
                    today_stats = await learning_service.get_daily_stats(user_id, date.today(), db)
                    
                    # Calculate real-time learning time for active session
                    active_session = await learning_service.get_active_session(user_id, db)
                    real_time_minutes = today_stats.total_minutes
                    
                    if active_session:
                        # Add current session time (from start to now)
                        from datetime import datetime, timezone
                        current_time = datetime.now(timezone.utc)
                        session_duration = (current_time - active_session.session_start).total_seconds() / 60
                        real_time_minutes += session_duration
                    
                    # Send notification to user's connections
                    message = f"🎓 Hôm nay bạn đã học được {real_time_minutes:.1f} phút! (Thông báo mỗi 30 phút)"
                    await self._send_to_user(user_id, message)
                except Exception as e:
                    print(f"Error in learning timer stats for user {user_id}: {e}")
                    db.rollback()
                
        except asyncio.CancelledError:
            # Timer was cancelled (user disconnected)
            pass
        except Exception as e:
            print(f"Error in learning timer for user {user_id}: {e}")
            db.rollback()

    async def _send_to_user(self, user_id: int, message: str) -> None:
        """Send message to all connections of a specific user"""
        if user_id in self.user_connections:
            user_connections = self.user_connections[user_id].copy()
            for websocket in user_connections:
                try:
                    await websocket.send_text(message)
                except Exception:
                    # Remove broken connection
                    if websocket in self.active_connections:
                        self.active_connections.remove(websocket)
                    if websocket in user_connections:
                        user_connections.remove(websocket)

    async def broadcast(self, message: str) -> None:
        """Broadcast message to all active connections"""
        for connection in self.active_connections.copy():
            try:
                await connection.send_text(message)
            except Exception:
                # Remove broken connection
                self.active_connections.discard(connection)
