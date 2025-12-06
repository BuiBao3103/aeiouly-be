from datetime import date, datetime, timedelta
from typing import Dict, List

from sqlalchemy import desc, and_
from sqlalchemy.orm import Session

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

    async def check_and_update_daily_streak(self, user_id: int, db: Session) -> tuple[LoginStreak, bool]:
        """Kiểm tra và cập nhật streak đăng nhập hằng ngày.
        
        Logic:
        - Kiểm tra hôm qua có streak không
        - Nếu hôm qua không có streak → reset streak về 0
        - Nếu hôm nay chưa có streak → cần timer 5 phút (MỖI NGÀY đều phải online 5 phút mới tính streak)
        - Mỗi ngày chỉ được tính 1 lần streak
        
        Returns:
            (streak, needs_timer): streak object và boolean cho biết có cần timer 5 phút không
        """
        today = date.today()
        yesterday = today - timedelta(days=1)

        # Tối ưu: Query cả yesterday và today records trong 1 lần
        daily_records = (
            db.query(LoginStreakDaily)
            .filter(
                and_(
                    LoginStreakDaily.user_id == user_id,
                    LoginStreakDaily.date.in_([yesterday, today])
                )
            )
            .all()
        )

        # Tách ra yesterday và today records
        yesterday_record = next((r for r in daily_records if r.date == yesterday), None)
        today_record = next((r for r in daily_records if r.date == today), None)

        # Lấy hoặc tạo streak record (dùng get_or_create pattern)
        streak = db.query(LoginStreak).filter(LoginStreak.user_id == user_id).first()
        
        if not streak:
            streak = LoginStreak(
                user_id=user_id,
                current_streak=0,
                longest_streak=0,
            )
            db.add(streak)
            db.flush()  # Flush để có streak.id

        # Nếu hôm qua không có streak → reset streak về 0
        if not yesterday_record:
            streak.current_streak = 0

        # Nếu hôm nay chưa có streak → cần timer 5 phút (MỖI NGÀY đều phải online 5 phút)
        needs_timer = not today_record

        db.commit()
        db.refresh(streak)
        return streak, needs_timer

    async def increment_streak_after_timer(self, user_id: int, db: Session) -> LoginStreak:
        """Tăng streak sau khi timer 5 phút hoàn thành.
        
        Chỉ được gọi khi:
        - Hôm nay chưa có streak
        - User đã online đủ 5 phút
        
        Logic:
        - Nếu hôm qua không có streak → streak = 1 (bắt đầu lại)
        - Nếu hôm qua có streak → streak += 1 (tiếp tục)
        """
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        # Kiểm tra lại hôm nay đã có streak chưa (tránh race condition)
        today_record = (
            db.query(LoginStreakDaily)
            .filter(
                and_(
                    LoginStreakDaily.user_id == user_id,
                    LoginStreakDaily.date == today
                )
            )
            .first()
        )
        
        # Nếu đã có record rồi thì không làm gì (có thể đã được tạo bởi request khác)
        if today_record:
            streak = db.query(LoginStreak).filter(LoginStreak.user_id == user_id).first()
            if streak:
                db.refresh(streak)
                return streak
            # Nếu có today_record nhưng không có streak record → tạo mới (edge case)
            streak = LoginStreak(
                user_id=user_id,
                current_streak=1,
                longest_streak=1,
            )
            db.add(streak)
            db.commit()
            db.refresh(streak)
            return streak
        
        # Kiểm tra hôm qua có streak không
        yesterday_record = (
            db.query(LoginStreakDaily)
            .filter(
                and_(
                    LoginStreakDaily.user_id == user_id,
                    LoginStreakDaily.date == yesterday
                )
            )
            .first()
        )
        
        # Lấy streak record
        streak = db.query(LoginStreak).filter(LoginStreak.user_id == user_id).first()
        
        if not streak:
            # Tạo mới streak record
            streak = LoginStreak(
                user_id=user_id,
                current_streak=1,
                longest_streak=1,
            )
            db.add(streak)
            db.flush()  # Flush để có streak.id cho daily_record
        else:
            # Cập nhật current_streak dựa trên yesterday_record
            if not yesterday_record:
                # Hôm qua không có streak → reset về 1 (bắt đầu lại)
                streak.current_streak = 1
            else:
                # Hôm qua có streak → tăng lên 1 (tiếp tục)
                streak.current_streak += 1
            
            # Cập nhật longest streak nếu cần
            if streak.current_streak > streak.longest_streak:
                streak.longest_streak = streak.current_streak
        
        # Tạo daily record cho hôm nay (record tồn tại = đã có streak)
        daily_record = LoginStreakDaily(
            streak_id=streak.id,
            user_id=user_id,
            date=today,
        )
        db.add(daily_record)
        
        # Flush trước commit để đảm bảo tất cả thay đổi được lưu
        db.flush()
        db.commit()
        db.refresh(streak)
        return streak

    async def increment_streak_and_notify(
        self, 
        user_id: int, 
        db: Session, 
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

    async def get_user_streak_stats(self, user_id: int, db: Session) -> Dict:
        """Get user's streak statistics from aggregate row."""
        streak = (
            db.query(LoginStreak)
            .filter(LoginStreak.user_id == user_id)
            .first()
        )

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
        self, db: Session, limit: int = 10
    ) -> List[Dict]:
        """Get users with highest current streaks (aggregate per user)."""
        top_users = (
            db.query(LoginStreak)
            .order_by(desc(LoginStreak.current_streak))
            .limit(limit)
            .all()
        )

        return [
            {
                "user_id": streak.user_id,
                "current_streak": streak.current_streak,
                "longest_streak": streak.longest_streak,
            }
            for streak in top_users
        ]

    async def get_weekly_streak_status(self, user_id: int, db: Session) -> Dict:
        """Get weekly streak status - danh sách các ngày trong tuần hiện tại (thứ 2 đến chủ nhật).
        
        Tối ưu: Query streak và daily records trong 1 lần để giảm số queries.
        """
        today = date.today()
        # Tính ngày đầu tuần (thứ 2)
        # weekday() trả về: 0=Monday, 1=Tuesday, ..., 6=Sunday
        monday = today - timedelta(days=today.weekday())
        # Ngày cuối tuần (chủ nhật)
        sunday = monday + timedelta(days=6)

        # Tối ưu: Query cả streak và daily records cùng lúc
        streak = (
            db.query(LoginStreak)
            .filter(LoginStreak.user_id == user_id)
            .first()
        )
        current_streak = streak.current_streak if streak else 0

        # Query daily records trong tuần hiện tại (thứ 2 đến chủ nhật)
        daily_records = (
            db.query(LoginStreakDaily)
            .filter(
                and_(
                    LoginStreakDaily.user_id == user_id,
                    LoginStreakDaily.date >= monday,
                    LoginStreakDaily.date <= sunday
                )
            )
            .all()
        )

        # Tạo dict để dễ lookup: ngày nào có streak
        # Record tồn tại trong LoginStreakDaily = đã có streak (đã online 5 phút hoặc đã được tính streak)
        dates_with_streak = {
            record.date: True 
            for record in daily_records
        }

        # Kiểm tra hôm nay đã có streak chưa
        today_has_streak = dates_with_streak.get(today, False)

        # Tạo danh sách 7 ngày trong tuần (thứ 2 đến chủ nhật)
        # Tối ưu: Pre-generate dates list để tránh tính toán lặp lại
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


