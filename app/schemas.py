from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr


# 用户注册请求
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    username: str  # 新增，用于注册时接收用户名


# 用户登录请求
class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserLoginSchema(BaseModel):
    email: str
    password: str


# 错误响应
class HTTPValidationError(BaseModel):
    detail: list


# 修改用户名
class UserUpdate(BaseModel):
    username: str


# 修改密码请求
class ChangePasswordRequest(BaseModel):
    email: EmailStr
    old_password: str
    new_password: str


# Device相关
class DeviceCreate(BaseModel):
    email: EmailStr
    name: str
    ip: str
    status: str = "offline"


class DeviceUpdate(BaseModel):
    id: int
    name: Optional[str] = None  # 允许不传 name
    ip: Optional[str] = None
    status: Optional[str] = None
    rtsp_url: Optional[str] = None
    email: EmailStr  # 必须有 email，否则 update_device 里会报错


# Notification 相关
class NotificationBase(BaseModel):
    message: str
    level: str  # 如 "safe", "warning", "danger"
    pinned: Optional[bool] = False
    deleted: Optional[bool] = False
    device_id: Optional[int]


class NotificationCreate(NotificationBase):
    message: str
    level: str
    device_id: int


class Notification(NotificationBase):
    id: int
    user_id: int  # 用于响应
    timestamp: datetime

    class Config:
        orm_mode = True


class NotificationUpdate(BaseModel):
    message: Optional[str]
    level: Optional[str]
    pinned: Optional[bool]
    deleted: Optional[bool]
    device_id: Optional[int]
