from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import datetime, date, timedelta
from typing import List, Optional
from src.users.models import User


class OnlineAnalyticsService:
    def __init__(self):
        pass

    async def get_user_online_status(self, user_id: int, target_date: date, db: Session) -> dict:
        """Get user's online status"""
        user = db.query(User).filter(User.id == user_id).first()
        
        if user:
            return {
                "is_online": user.is_online,
            }
        else:
            return {
                "is_online": False,
            }

    async def get_online_users_today(self, db: Session) -> List[User]:
        """Get all users who are online today"""
        online_users = db.query(User).filter(User.is_online == True).all()
        return online_users

    async def get_online_stats_by_date(self, target_date: date, db: Session) -> dict:
        """Get online statistics for a specific date"""
        total_users = db.query(User).count()
        online_users = db.query(User).filter(User.is_online == True).count()
        
        return {
            'date': target_date,
            'total_users': total_users,
            'online_users': online_users,
            'offline_users': total_users - online_users
        }

    async def get_online_stats_range(self, start_date: date, end_date: date, db: Session) -> List[dict]:
        """Get online statistics for a date range"""
        # Since we're using User.is_online, we can only get current stats
        # For historical data, we'd need to implement a different approach
        total_users = db.query(User).count()
        online_users = db.query(User).filter(User.is_online == True).count()
        
        result = []
        current_date = start_date
        while current_date <= end_date:
            result.append({
                'date': current_date,
                'total_users': total_users,
                'online_users': online_users if current_date == date.today() else 0,
                'offline_users': total_users - (online_users if current_date == date.today() else 0)
            })
            current_date += timedelta(days=1)
        
        return result

    async def get_user_online_history(self, user_id: int, db: Session, days: int = 30) -> List[dict]:
        """Get user's online history for the last N days"""
        # Since we're using User.is_online, we can only get current status
        # For historical data, we'd need to implement a different approach
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            return []
        
        result = []
        end_date = date.today()
        start_date = end_date - timedelta(days=days-1)
        
        current_date = start_date
        while current_date <= end_date:
            result.append({
                'date': current_date,
                'is_online': user.is_online if current_date == date.today() else False,
            })
            current_date += timedelta(days=1)
        
        return result