from fastapi import Depends
from src.analytics.service import LearningAnalyticsService
from src.analytics.online_service import OnlineAnalyticsService
from src.analytics.streak_service import LoginStreakService


def get_learning_analytics_service() -> LearningAnalyticsService:
    """Get LearningAnalyticsService instance"""
    return LearningAnalyticsService()


def get_online_analytics_service() -> OnlineAnalyticsService:
    """Get OnlineAnalyticsService instance"""
    return OnlineAnalyticsService()


def get_login_streak_service() -> LoginStreakService:
    """Get LoginStreakService instance"""
    return LoginStreakService()
