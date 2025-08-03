from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from app.models import Notification, User
from app.schemas import NotificationCreate, NotificationUpdate
from app.crud import create_notification
from app.utils.database import get_db
from app.api.websocket import send_alert_message
from app.utils.security import get_current_user
import asyncio

router = APIRouter()


# 获取通知列表，确保中文不乱码
@router.get("", response_class=JSONResponse)
def list_notifications(
        skip: int = Query(0, description="跳过前 N 条记录"),
        limit: int = Query(20, description="返回的最大记录数"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)  # ⬅️ 获取当前用户
):
    # 获取当前用户的通知列表，通过分页参数 `skip` 和 `limit` 来控制返回的数据

    try:
        notifications = db.query(Notification).filter(
            Notification.user_id == current_user.id,
            Notification.deleted == False
        ).order_by(Notification.pinned.desc(), Notification.timestamp.desc()
                   ).offset(skip).limit(limit).all()

        # 将通知记录转化为字典格式
        result = [n.to_dict() for n in notifications]
        return JSONResponse(content=jsonable_encoder(result), media_type="application/json")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching notifications: {str(e)}")


# 创建新通知
@router.post("")
async def add_notification(
        notification: NotificationCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)  # 获取当前用户
):
    # 创建一条新通知并推送给用户

    try:
        if not notification.message:
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        if notification.level not in ["safe", "warning", "danger"]:
            raise HTTPException(status_code=400, detail="Invalid level")

        # 创建通知时绑定当前用户
        new_notification = create_notification(
            db=db,
            notification_data=notification,
            user_id=current_user.id  # 将当前用户的 ID 传入
        )

        # ✅ 异步 WebSocket 推送
        # 获取通知数据
        message = f"New alert: {notification.level} - {notification.message}"
        level = notification.level
        alert_id = new_notification.id  # 通过数据库生成的 ID 获取通知 ID

        # 异步推送通知
        asyncio.create_task(send_alert_message(level, message, alert_id))

        return {
            "message": "Notification created successfully",
            "data": new_notification.to_dict()
        }
    except HTTPException as e:
        raise e  # 直接抛出 HTTPException
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating notification: {str(e)}")


@router.put("/{notification_id}")
def update_notification(
        notification_id: int,
        updated_data: NotificationUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    print(f"🔄 收到更新请求 ID={notification_id}, data={updated_data.dict()}")
    try:
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        ).first()

        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")

        # 按需更新字段
        if updated_data.message is not None:
            notification.message = updated_data.message
        if updated_data.level is not None:
            notification.level = updated_data.level
        if updated_data.pinned is not None:
            notification.pinned = updated_data.pinned
        if updated_data.deleted is not None:
            notification.deleted = updated_data.deleted
        if updated_data.device_id is not None:
            notification.device_id = updated_data.device_id

        db.commit()
        db.refresh(notification)
        print(f"通知更新后的数据: {notification.to_dict()}")

        return {"message": "Notification updated", "data": notification.to_dict()}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating notification: {str(e)}")


# 删除单条通知（软删除）
@router.delete("/{notification_id}")
def delete_notification(
        notification_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        ).first()

        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")

        notification.deleted = True
        db.commit()
        return {"message": "Notification deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting notification: {str(e)}")


# 置顶 / 取消置顶
@router.post("/{notification_id}/pin")
def toggle_pin_notification(
        notification_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        print(f"📌 [置顶操作] 接收到请求 - 用户: {current_user.email}, 通知ID: {notification_id}")

        # 查找该通知
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        ).first()

        # 如果找不到通知，返回404错误
        if not notification:
            print(f"⚠️ [置顶操作] 找不到通知 ID: {notification_id}，属于用户: {current_user.email}")
            raise HTTPException(status_code=404, detail="Notification not found")

        old_state = notification.pinned
        notification.pinned = not notification.pinned
        db.commit()  # 提交到数据库
        db.refresh(notification)  # 刷新状态，确保拿到最新的数据
        print(f"✅ [置顶操作] 通知 ID: {notification_id} 状态从 {old_state} -> {notification.pinned}")

        return {
            "message": "Notification pin state updated",
            "pinned": notification.pinned
        }
    except Exception as e:
        print(f"❌ [置顶操作] 更新置顶状态出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating pin status: {str(e)}")


# 清空通知（批量软删除）
@router.delete("/clear")
def clear_all_notifications(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        db.query(Notification).filter(
            Notification.user_id == current_user.id
        ).update({Notification.deleted: True})
        db.commit()
        return {"message": "All notifications cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing notifications: {str(e)}")
