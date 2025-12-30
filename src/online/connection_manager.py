import logging
from typing import Set, Dict
import asyncio

from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from src.users.models import User
from src.online.models import LoginStreakDaily

# Khởi tạo logger
logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: Set[WebSocket] = set()
        self.user_connections: Dict[int, Set[WebSocket]] = {}
        self.websocket_to_user: Dict[WebSocket, int] = {}
        # Timer để track 5 phút online cho streak (chỉ khi hôm qua có đăng nhập)
        self.streak_timers: Dict[int, asyncio.Task] = {}

    async def connect(self, websocket: WebSocket, user_id: int, db: AsyncSession) -> None:
        """Connect WebSocket (accepts connection first)."""
        await websocket.accept()
        self.active_connections.add(websocket)

        user_set = self.user_connections.get(user_id)
        if user_set is None:
            user_set = set()
            self.user_connections[user_id] = user_set

        was_empty = len(user_set) == 0
        user_set.add(websocket)
        self.websocket_to_user[websocket] = user_id
        
        logger.info(f"User {user_id} connected. Active connections for user: {len(user_set)}")

        if was_empty:
            logger.info(f"First connection for user {user_id}. Setting status to online.")
            # First connection for this user → set online status
            await self._set_user_online_status(user_id, True, db)
            
            # Nếu hôm nay chưa có streak → bắt đầu timer
            if not await self._check_today_has_streak(user_id, db):
                await self._start_streak_timer(user_id)

    async def disconnect(self, websocket: WebSocket, db: AsyncSession) -> None:
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

        logger.info(f"User {user_id} disconnected a connection. Remaining for user: {len(user_set)}")

        if len(user_set) == 0:
            logger.info(f"Last connection for user {user_id} closed. Setting status to offline.")
            # Last connection for this user → set offline status
            self.user_connections.pop(user_id, None)
            # Huỷ timer nếu có
            if user_id in self.streak_timers:
                logger.info(f"Cancelling streak timer for user {user_id}")
                self.streak_timers[user_id].cancel()
                self.streak_timers.pop(user_id, None)
            try:
                await db.rollback()  # Rollback any failed transaction first
                await self._set_user_online_status(user_id, False, db)
            except Exception as e:
                logger.error(f"Error in disconnect for user {user_id}: {e}", exc_info=True)
                await db.rollback()

    async def _set_user_online_status(
        self, user_id: int, is_online: bool, db: AsyncSession
    ) -> None:
        """Set user's online status"""
        try:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user:
                user.is_online = is_online
                await db.commit()
                logger.debug(f"User {user_id} online status set to {is_online}")
        except Exception as e:
            logger.error(f"Error setting online status for user {user_id}: {e}", exc_info=True)
            await db.rollback()

    async def _check_today_has_streak(self, user_id: int, db: AsyncSession) -> bool:
        """Kiểm tra và cập nhật streak đăng nhập hằng ngày khi user kết nối socket."""
        try:
            result = await db.execute(
                select(LoginStreakDaily).where(
                    LoginStreakDaily.user_id == user_id,
                    LoginStreakDaily.date == datetime.now().date()
                )
            )
            daily_record = result.scalar_one_or_none()
            return daily_record is not None
        except Exception as e:
            logger.error(f"Error checking daily streak for user {user_id}: {e}", exc_info=True)
            await db.rollback()
            return False

    async def _start_streak_timer(self, user_id: int) -> None:
        """Khởi động timer 5 phút để tăng streak."""
        # Huỷ timer cũ nếu có
        if user_id in self.streak_timers:
            self.streak_timers[user_id].cancel()

        async def _timer():
            from src.database import get_db
            db_new = next(get_db())
            try:
                logger.info(f"Streak timer started for user {user_id} (20s for testing)")
                await asyncio.sleep(20) # Bạn có thể đổi lại thành 300s (5p) cho production
                
                if user_id not in self.user_connections:
                    logger.info(f"User {user_id} disconnected before timer finished.")
                    return

                from src.online.service import LoginStreakService
                streak_service = LoginStreakService()
                await streak_service.increment_streak_and_notify(user_id, db_new, self)
                logger.info(f"Streak timer completed and processed for user {user_id}")
                
            except asyncio.CancelledError:
                logger.info(f"Streak timer for user {user_id} was cancelled.")
                raise
            except Exception as e:
                logger.error(f"Error in streak timer for user {user_id}: {e}", exc_info=True)
                db_new.rollback()
            finally:
                db_new.close()
                if user_id in self.streak_timers and self.streak_timers[user_id].done():
                    self.streak_timers.pop(user_id, None)

        task = asyncio.create_task(_timer())
        self.streak_timers[user_id] = task

    async def _send_to_user(self, user_id: int, message: str) -> None:
        """Send message to all connections of a specific user"""
        if user_id in self.user_connections:
            user_connections = self.user_connections[user_id].copy()
            for websocket in user_connections:
                try:
                    await websocket.send_text(message)
                except Exception as e:
                    logger.warning(f"Failed to send message to user {user_id} on a websocket: {e}")
                    if websocket in self.active_connections:
                        self.active_connections.remove(websocket)
                    if websocket in user_connections:
                        user_connections.remove(websocket)

    async def broadcast(self, message: str) -> None:
        """Broadcast message to all active connections"""
        logger.debug(f"Broadcasting message: {message[:50]}...")
        for connection in self.active_connections.copy():
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to broadcast to a connection: {e}")
                self.active_connections.discard(connection)