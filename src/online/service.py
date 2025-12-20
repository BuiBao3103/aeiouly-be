from datetime import date, datetime, timedelta
from typing import Dict, List

from sqlalchemy import desc, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.online.connection_manager import ConnectionManager
from src.online.models import LoginStreak, LoginStreakDaily


class LoginStreakService:
    """Service for tracking login streak statistics (aggregate per user).

    Chuỗi streak được cập nhật thông qua WebSocket khi user kết nối:
    - Kiểm tra hôm qua có đăng nhập không
    - Nếu hôm qua không đăng nhập → reset streak về 0
    - Nếu hôm nay chưa đăng nhập → tăng streak lên 1
    - Mỗi ngày chỉ được tính 1 lần đăng nhập
    """

    async def update_daily_streak(self, user_id: int, db: AsyncSession) -> None:
        """Kiểm tra và cập nhật streak đăng nhập hằng ngày.
        
        Logic:
        - Kiểm tra hôm qua có streak không
        - Nếu hôm qua không có streak → reset streak về 0
        - Mỗi ngày chỉ được tính 1 lần streak
        """
    
        # Lấy hoặc tạo streak record (dùng get_or_create pattern)
        result = await db.execute(
            select(LoginStreak).where(LoginStreak.user_id == user_id)
        )
        streak = result.scalar_one_or_none()
        
        if not streak:
            streak = LoginStreak(
                user_id=user_id,
                current_streak=0,
                longest_streak=0,
            )
            db.add(streak)
            await db.flush()
        else:
            today = date.today()
            yesterday = today - timedelta(days=1)

            # Query yesterday record
            result = await db.execute(
                select(LoginStreakDaily).where(
                    and_(
                        LoginStreakDaily.user_id == user_id,
                        LoginStreakDaily.date.in_([today, yesterday])
                    )
                )
            )
            daily_records = result.scalars().all()
            yesterday_record = next((r for r in daily_records if r.date == yesterday), None)
            today_record = next((r for r in daily_records if r.date == today), None)
            if not today_record and not yesterday_record:
                streak.current_streak = 0

            await db.commit()
            await db.refresh(streak)

    async def increment_streak_after_timer(self, user_id: int, db: AsyncSession) -> LoginStreak:
        """Tăng streak sau khi timer 5 phút hoàn thành.
        
        Chỉ được gọi khi:
        - Hôm nay chưa có streak
        - User đã online đủ 5 phút
        - Việc kiểm tra và reset streak về 0 (nếu hôm qua không có streak) đã được xử lý ở chỗ khác
        
        Logic:
        - Tăng current_streak lên 1
        - Tạo daily record mới cho hôm nay
        - Cập nhật longest_streak nếu cần
        """
        print(f"Incrementing streak for user {user_id}")
        today = date.today()
        
        # Lấy hoặc tạo streak record
        result = await db.execute(
            select(LoginStreak).where(LoginStreak.user_id == user_id)
        )
        streak = result.scalar_one_or_none()
        
        if not streak:
            # Tạo mới streak record
            streak = LoginStreak(
                user_id=user_id,
                current_streak=0,
                longest_streak=0,
            )
            db.add(streak)
            await db.flush()  # Flush để có streak.id cho daily_record
        
        # Tăng current_streak lên 1
        streak.current_streak += 1
        
        # Cập nhật longest_streak nếu cần
        if streak.current_streak > streak.longest_streak:
            streak.longest_streak = streak.current_streak
        
        # Tạo daily record cho hôm nay (record tồn tại = đã có streak)
        daily_record = LoginStreakDaily(
            streak_id=streak.id,
            user_id=user_id,
            date=today,
        )
        db.add(daily_record)
        
        # Commit tất cả thay đổi
        await db.commit()
        await db.refresh(streak)
        return streak

    async def increment_streak_and_notify(
        self, 
        user_id: int, 
        db: AsyncSession, 
        connection_manager: ConnectionManager
    ) -> LoginStreak:
        """Tăng streak sau timer 5 phút và gửi notification.
        
        Args:
            user_id: User ID
            db: Database session
            connection_manager: ConnectionManager để gửi notification
            
        Returns:
            LoginStreak: Updated streak object
        """
        from src.online.schemas import StreakUpdatedMessage
        from datetime import datetime
        
        # Tăng streak
        streak = await self.increment_streak_after_timer(user_id, db)
        
        # Gửi notification
        notification_service = NotificationService(connection_manager)
        streak_message = StreakUpdatedMessage(
            current_streak=streak.current_streak,
            longest_streak=streak.longest_streak,
            message=f"🎉 Bạn đã duy trì streak!\nChuỗi hiện tại: {streak.current_streak} ngày, chuỗi dài nhất: {streak.longest_streak} ngày.",
            timestamp=datetime.now().isoformat()
        )
        await notification_service.send_to_user(user_id, streak_message.model_dump_json())
        
        return streak

    async def get_user_streak_stats(self, user_id: int, db: AsyncSession) -> Dict:
        """Get user's streak statistics from aggregate row."""
        result = await db.execute(
            select(LoginStreak).where(LoginStreak.user_id == user_id)
        )
        streak = result.scalar_one_or_none()

        if not streak:
            return {
                "current_streak": 0,
                "longest_streak": 0,
            }

        return {
            "current_streak": streak.current_streak,
            "longest_streak": streak.longest_streak,
        }

    async def get_top_streak_users(
        self, db: AsyncSession, limit: int = 10
    ) -> List[Dict]:
        """Get users with highest current streaks (aggregate per user)."""
        result = await db.execute(
            select(LoginStreak)
            .order_by(desc(LoginStreak.current_streak))
            .limit(limit)
        )
        top_users = result.scalars().all()

        return [
            {
                "user_id": streak.user_id,
                "current_streak": streak.current_streak,
                "longest_streak": streak.longest_streak,
            }
            for streak in top_users
        ]

    async def get_weekly_streak_status(self, user_id: int, db: AsyncSession) -> Dict:
        """Get weekly streak status - danh sách các ngày trong tuần hiện tại (thứ 2 đến chủ nhật).
        
        Sử dụng update_daily_streak để kiểm tra và cập nhật streak.
        """
        today = date.today()
        # Tính ngày đầu tuần (thứ 2)
        # weekday() trả về: 0=Monday, 1=Tuesday, ..., 6=Sunday
        monday = today - timedelta(days=today.weekday())
        # Ngày cuối tuần (chủ nhật)
        sunday = monday + timedelta(days=6)

        # Sử dụng update_daily_streak để kiểm tra và cập nhật streak
        await self.update_daily_streak(user_id, db)
        
        # Lấy streak sau khi đã cập nhật
        result = await db.execute(
            select(LoginStreak).where(LoginStreak.user_id == user_id)
        )
        streak = result.scalar_one_or_none()
        current_streak = streak.current_streak if streak else 0

        # Query daily records trong tuần hiện tại (thứ 2 đến chủ nhật) để thống kê
        # Bao gồm cả hôm nay để kiểm tra today_has_streak
        result = await db.execute(
            select(LoginStreakDaily).where(
                and_(
                    LoginStreakDaily.user_id == user_id,
                    LoginStreakDaily.date >= monday,
                    LoginStreakDaily.date <= sunday
                )
            )
        )
        daily_records = result.scalars().all()

        # Tạo dict để dễ lookup: ngày nào có streak
        dates_with_streak = {
            record.date: True 
            for record in daily_records
        }

        # Kiểm tra hôm nay có streak không
        today_has_streak = dates_with_streak.get(today, False)

        # Tạo danh sách 7 ngày trong tuần (thứ 2 đến chủ nhật)
        weekly_days = []
        for i in range(7):
            current_date = monday + timedelta(days=i)
            weekly_days.append({
                "date": current_date.isoformat(),
                "has_streak": dates_with_streak.get(current_date, False),
            })

        return {
            "current_streak": current_streak,
            "today_has_streak": today_has_streak,
            "days": weekly_days,
        }


class NotificationService:
    """Service for managing notifications and WebSocket connections"""

    def __init__(self, connection_manager: ConnectionManager | None = None) -> None:
        # Use provided connection manager or create a new one
        # (Routers that need the shared global manager should use
        #  get_connection_manager() from online.dependencies instead.)
        self.connection_manager = connection_manager or ConnectionManager()

    async def send_to_user(self, user_id: int, message: str) -> bool:
        """Send notification to a specific user"""
        try:
            await self.connection_manager._send_to_user(user_id, message)
            return True
        except Exception as e:  # pragma: no cover - logging only
            print(f"Error sending notification to user {user_id}: {e}")
            return False


