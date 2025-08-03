from sqlalchemy.orm import Session

from app import models, schemas
from app.models import User, Notification
from app.utils.security import hash_password, verify_password
from app.schemas import UserCreate


def get_user_by_email(db: Session, email: str):
    # 根据邮箱查询用户
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(db: Session, user: schemas.UserCreate):
    # 创建用户（注册）
    # 检查邮箱是否已存在
    if get_user_by_email(db, user.email):
        raise ValueError("Email already registered")

    hashed_password = hash_password(user.password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        username=user.username
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return {
        "id": db_user.id,
        "email": db_user.email,
        "username": db_user.username
    }


def authenticate_user(db: Session, email: str, password: str):
    # 用户认证（登录）
    user = get_user_by_email(db, email)
    if user and verify_password(password, user.hashed_password):
        return user
    return None


def create_notification(db: Session, notification_data: schemas.NotificationCreate, user_id: int):
    # 创建通知，当设备检测到危险时
    # 判断是否为危险或警告状态
    if notification_data.level == "danger":
        notification_data.message = f"危险：{notification_data.message}"  # 用检测到的危险原因填充通知内容
    elif notification_data.level == "warning":
        notification_data.message = f"警告：{notification_data.message}"
    else:
        notification_data.message = f"状态：{notification_data.message}"  # 其他情况（可以扩展）

    notification = models.Notification(
        user_id=user_id,  # 绑定当前用户
        device_id=notification_data.device_id,
        level=notification_data.level,
        message=notification_data.message,
        pinned=notification_data.pinned if notification_data.pinned is not None else False,
        deleted=notification_data.deleted if notification_data.deleted is not None else False,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def get_notifications(db: Session, user_id: int, skip: int = 0, limit: int = 20):
    # 获取用户通知
    return db.query(models.Notification)\
        .filter(models.Notification.user_id == user_id, models.Notification.deleted == False)\
        .offset(skip).limit(limit).all()
