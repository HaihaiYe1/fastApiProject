from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, text
from sqlalchemy.orm import relationship
from app.utils.database import Base
from datetime import datetime


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    username = Column(String(100), nullable=False)

    devices = relationship("Device", back_populates="user")  # 关联设备
    notifications = relationship("Notification", back_populates="user")  # 关联通知


class Device(Base):
    __tablename__ = "device"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    rtsp_url = Column(String, nullable=False)
    ip = Column(String, nullable=False)
    status = Column(String, nullable=False, default="offline")
    email = Column(String, ForeignKey("users.email"))  # 确保外键正确

    user = relationship("User", back_populates="devices")  # 关联 User
    notifications = relationship("Notification", back_populates="device")  # 关联通知


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    device_id = Column(Integer, ForeignKey("device.id"), nullable=True)
    level = Column(String(10), nullable=False)
    message = Column(String(255), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # ✅ 显式设置 server_default='0' 防止 MySQL 报错
    pinned = Column(Boolean, nullable=False, default=False, server_default=text("0"))
    deleted = Column(Boolean, nullable=False, default=False, server_default=text("0"))

    user = relationship("User", back_populates="notifications")
    device = relationship("Device", back_populates="notifications")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "device_id": self.device_id,
            "level": self.level,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "pinned": self.pinned,
            "deleted": self.deleted,
        }
