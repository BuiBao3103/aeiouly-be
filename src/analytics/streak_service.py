from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from datetime import datetime, date, timedelta, timezone
from typing import Optional, List, Dict
from src.analytics.models import LoginStreak


class LoginStreakService:
    def __init__(self):
        pass

    async def record_login(self, user_id: int, db: Session) -> LoginStreak:
        """Record a login and update streak"""
        today = date.today()
        
        # Check if user already logged in today
        existing_streak = db.query(LoginStreak).filter(
            and_(
                LoginStreak.user_id == user_id,
                LoginStreak.date == today
            )
        ).first()
        
        if existing_streak:
            # User already logged in today, just increment login count
            existing_streak.login_count += 1
            db.commit()
            db.refresh(existing_streak)
            return existing_streak
        
        # New login for today
        # Calculate current streak
        current_streak = await self._calculate_current_streak(db, user_id)
        new_streak = current_streak + 1
        
        # Get longest streak
        longest_streak = await self._get_longest_streak(db, user_id)
        if new_streak > longest_streak:
            longest_streak = new_streak
        
        # Create new streak record
        streak = LoginStreak(
            user_id=user_id,
            date=today,
            login_count=1,
            current_streak=new_streak,
            longest_streak=longest_streak
        )
        db.add(streak)
        db.commit()
        db.refresh(streak)
        
        return streak

    async def _calculate_current_streak(self, db: Session, user_id: int) -> int:
        """Calculate current consecutive login streak"""
        today = date.today()
        streak_days = 0
        
        # Check consecutive days backwards from yesterday
        check_date = today - timedelta(days=1)
        
        while True:
            streak_record = db.query(LoginStreak).filter(
                and_(
                    LoginStreak.user_id == user_id,
                    LoginStreak.date == check_date
                )
            ).first()
            
            if streak_record:
                streak_days += 1
                check_date -= timedelta(days=1)
            else:
                break
        
        return streak_days

    async def _get_longest_streak(self, db: Session, user_id: int) -> int:
        """Get user's longest streak"""
        longest = db.query(func.max(LoginStreak.longest_streak)).filter(
            LoginStreak.user_id == user_id
        ).scalar()
        return longest or 0

    async def get_user_streak_stats(self, user_id: int, db: Session) -> Dict:
        """Get user's streak statistics"""
        today = date.today()
        
        # Get today's streak
        today_streak = db.query(LoginStreak).filter(
            and_(
                LoginStreak.user_id == user_id,
                LoginStreak.date == today
            )
        ).first()
        
        # Get longest streak
        longest_streak = await self._get_longest_streak(db, user_id)
        
        # Get current streak
        current_streak = await self._calculate_current_streak(db, user_id)
        
        # Add today if user logged in today
        if today_streak:
            current_streak += 1
        
        return {
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "today_logins": today_streak.login_count if today_streak else 0,
            "last_login_date": today_streak.date if today_streak else None
        }

    async def get_streak_history(self, db: Session, user_id: int, days: int = 30) -> List[Dict]:
        """Get user's streak history for the last N days"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days-1)
        
        streaks = db.query(LoginStreak).filter(
            and_(
                LoginStreak.user_id == user_id,
                LoginStreak.date >= start_date,
                LoginStreak.date <= end_date
            )
        ).order_by(LoginStreak.date).all()
        
        result = []
        current_date = start_date
        while current_date <= end_date:
            day_streak = next((s for s in streaks if s.date == current_date), None)
            result.append({
                'date': current_date,
                'login_count': day_streak.login_count if day_streak else 0,
                'current_streak': day_streak.current_streak if day_streak else 0,
                'logged_in': day_streak is not None
            })
            current_date += timedelta(days=1)
        
        return result

    async def get_top_streak_users(self, db: Session, limit: int = 10) -> List[Dict]:
        """Get users with highest current streaks"""
        # Get latest streak for each user
        subquery = db.query(
            LoginStreak.user_id,
            func.max(LoginStreak.date).label('latest_date')
        ).group_by(LoginStreak.user_id).subquery()
        
        top_users = db.query(LoginStreak).join(
            subquery,
            and_(
                LoginStreak.user_id == subquery.c.user_id,
                LoginStreak.date == subquery.c.latest_date
            )
        ).order_by(desc(LoginStreak.current_streak)).limit(limit).all()
        
        return [
            {
                'user_id': streak.user_id,
                'current_streak': streak.current_streak,
                'longest_streak': streak.longest_streak,
                'last_login': streak.date
            }
            for streak in top_users
        ]
