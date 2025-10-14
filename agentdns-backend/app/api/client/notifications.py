"""
Client notifications APIs
"""

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from pydantic import BaseModel

from ...database import get_db
from ...models.user import User
from ...api.deps import get_current_client_user

router = APIRouter()


class NotificationResponse(BaseModel):
    """Notification response"""
    id: int
    type: str  # system, billing, security, service
    title: str
    message: str
    is_read: bool
    priority: str  # low, normal, high, urgent
    created_at: datetime
    expires_at: Optional[datetime]
    action_url: Optional[str]
    action_text: Optional[str]


class NotificationStatsResponse(BaseModel):
    """Notification statistics response"""
    total_count: int
    unread_count: int
    urgent_count: int
    recent_count: int  # 最近7天


# Mock notification data (should be loaded from DB in production)
MOCK_NOTIFICATIONS = [
    {
        "id": 1,
        "type": "system",
        "title": "System Maintenance",
        "message": "Scheduled maintenance tonight 23:00-01:00; some services may be impacted.",
        "is_read": False,
        "priority": "high",
        "created_at": datetime.utcnow() - timedelta(hours=2),
        "expires_at": datetime.utcnow() + timedelta(days=1),
        "action_url": "/dashboard/support",
        "action_text": "View details"
    },
    {
        "id": 2,
        "type": "billing",
        "title": "Low Balance Alert",
        "message": "Your account balance is below CNY 10. Please top up to avoid service interruption.",
        "is_read": False,
        "priority": "urgent",
        "created_at": datetime.utcnow() - timedelta(hours=6),
        "expires_at": None,
        "action_url": "/dashboard/billing",
        "action_text": "Top up now"
    },
    {
        "id": 3,
        "type": "security",
        "title": "New Device Login",
        "message": "A new device signed in to your account. If this wasn't you, change your password immediately.",
        "is_read": True,
        "priority": "normal",
        "created_at": datetime.utcnow() - timedelta(days=1),
        "expires_at": datetime.utcnow() + timedelta(days=7),
        "action_url": "/dashboard/profile",
        "action_text": "View details"
    },
    {
        "id": 4,
        "type": "service",
        "title": "API Call Issues",
        "message": "Multiple failed API calls with your API key in the past hour. Please check service status.",
        "is_read": True,
        "priority": "normal",
        "created_at": datetime.utcnow() - timedelta(hours=3),
        "expires_at": None,
        "action_url": "/dashboard/logs",
        "action_text": "View logs"
    },
    {
        "id": 5,
        "type": "system",
        "title": "New Feature Released",
        "message": "We added API usage analytics so you can view service usage more intuitively.",
        "is_read": False,
        "priority": "low",
        "created_at": datetime.utcnow() - timedelta(days=3),
        "expires_at": datetime.utcnow() + timedelta(days=30),
        "action_url": "/dashboard/logs",
        "action_text": "Try now"
    }
]


@router.get("/", response_model=List[NotificationResponse])
async def get_notifications(
    type: Optional[str] = None,
    is_read: Optional[bool] = None,
    priority: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_client_user)
):
    """Get notification list"""
    
    # Filter notifications (should query DB in production)
    notifications = MOCK_NOTIFICATIONS.copy()
    
    if type:
        notifications = [n for n in notifications if n["type"] == type]
    
    if is_read is not None:
        notifications = [n for n in notifications if n["is_read"] == is_read]
    
    if priority:
        notifications = [n for n in notifications if n["priority"] == priority]
    
    # Pagination
    notifications = notifications[offset:offset + limit]
    
    return [
        NotificationResponse(**notification)
        for notification in notifications
    ]


@router.get("/stats", response_model=NotificationStatsResponse)
async def get_notification_stats(
    current_user: User = Depends(get_current_client_user)
):
    """Get notification statistics"""
    
    notifications = MOCK_NOTIFICATIONS
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    
    total_count = len(notifications)
    unread_count = len([n for n in notifications if not n["is_read"]])
    urgent_count = len([n for n in notifications if n["priority"] == "urgent" and not n["is_read"]])
    recent_count = len([n for n in notifications if n["created_at"] >= seven_days_ago])
    
    return NotificationStatsResponse(
        total_count=total_count,
        unread_count=unread_count,
        urgent_count=urgent_count,
        recent_count=recent_count
    )


@router.post("/{notification_id}/read")
async def mark_as_read(
    notification_id: int,
    current_user: User = Depends(get_current_client_user)
):
    """Mark notification as read"""
    
    # Find notification (should use DB)
    notification = None
    for n in MOCK_NOTIFICATIONS:
        if n["id"] == notification_id:
            notification = n
            break
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    # Mark as read
    notification["is_read"] = True
    
    return {
        "message": "Notification marked as read",
        "notification_id": notification_id
    }


@router.post("/mark-all-read")
async def mark_all_as_read(
    type: Optional[str] = None,
    current_user: User = Depends(get_current_client_user)
):
    """Mark all notifications as read"""
    
    updated_count = 0
    for notification in MOCK_NOTIFICATIONS:
        if not notification["is_read"]:
            if type is None or notification["type"] == type:
                notification["is_read"] = True
                updated_count += 1
    
    return {
        "message": f"Marked {updated_count} notification(s) as read",
        "updated_count": updated_count
    }


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: int,
    current_user: User = Depends(get_current_client_user)
):
    """Delete notification"""
    
    # 查找并删除通知
    for i, notification in enumerate(MOCK_NOTIFICATIONS):
        if notification["id"] == notification_id:
            del MOCK_NOTIFICATIONS[i]
            return {
                "message": "Notification deleted",
                "notification_id": notification_id
            }
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Notification not found"
    )


@router.get("/types")
async def get_notification_types(
    current_user: User = Depends(get_current_client_user)
):
    """Get notification types"""
    
    types = {}
    for notification in MOCK_NOTIFICATIONS:
        type_name = notification["type"]
        if type_name not in types:
            types[type_name] = {
                "type": type_name,
                "name": {
                    "system": "System",
                    "billing": "Billing",
                    "security": "Security",
                    "service": "Service"
                }.get(type_name, type_name),
                "count": 0,
                "unread_count": 0
            }
        
        types[type_name]["count"] += 1
        if not notification["is_read"]:
            types[type_name]["unread_count"] += 1
    
    return list(types.values())


@router.get("/recent")
async def get_recent_notifications(
    days: int = 7,
    limit: int = 10,
    current_user: User = Depends(get_current_client_user)
):
    """Get recent notifications"""
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    recent_notifications = [
        n for n in MOCK_NOTIFICATIONS
        if n["created_at"] >= cutoff_date
    ]
    
    # 按时间排序并限制数量
    recent_notifications.sort(key=lambda x: x["created_at"], reverse=True)
    recent_notifications = recent_notifications[:limit]
    
    return [
        {
            "id": n["id"],
            "type": n["type"],
            "title": n["title"],
            "message": n["message"][:100] + "..." if len(n["message"]) > 100 else n["message"],
            "is_read": n["is_read"],
            "priority": n["priority"],
            "created_at": n["created_at"],
            "time_ago": _get_time_ago(n["created_at"])
        }
        for n in recent_notifications
    ]


def _get_time_ago(dt: datetime) -> str:
    """Humanized time delta"""
    now = datetime.utcnow()
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days} days ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hours ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minutes ago"
    else:
        return "just now"


@router.post("/settings")
async def update_notification_settings(
    email_notifications: bool = True,
    sms_notifications: bool = False,
    push_notifications: bool = True,
    notification_types: List[str] = None,
    current_user: User = Depends(get_current_client_user)
):
    """Update notification settings"""
    
    if notification_types is None:
        notification_types = ["system", "billing", "security"]
    
    # Persist to database in production
    settings = {
        "email_notifications": email_notifications,
        "sms_notifications": sms_notifications,
        "push_notifications": push_notifications,
        "notification_types": notification_types,
        "updated_at": datetime.utcnow().isoformat()
    }
    
    return {
        "message": "Notification settings updated",
        "settings": settings
    }


@router.get("/settings")
async def get_notification_settings(
    current_user: User = Depends(get_current_client_user)
):
    """Get notification settings"""
    
    # Load from database in production
    return {
        "email_notifications": True,
        "sms_notifications": False,
        "push_notifications": True,
        "notification_types": ["system", "billing", "security"],
        "quiet_hours": {
            "enabled": False,
            "start": "22:00",
            "end": "08:00"
        }
    }
