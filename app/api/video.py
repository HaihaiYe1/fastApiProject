from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from app.utils.database import get_db
from app.models import Device
from app.detection.multi_detector import MultiDetector
from app.utils.video_utils import get_video_capture, read_frame
import time
import os
import threading

from app.schemas import NotificationCreate
from app.crud import create_notification
from app.api.websocket import send_alert_message  # ✅ 新增
from app.utils.security import get_current_user  # ✅ 引入当前用户依赖
from app.models import User

router = APIRouter()
multi_detector = MultiDetector()

# 冷却时间（秒）
COOL_DOWN_TIME = 5  # 每5秒内同一通知不重复发送
DETECTION_THREADS = {}
STOP_FLAGS = {}


# 启动持续检测
@router.post("/start-detect")
def start_detect(
        device_id: int = Query(..., description="设备 ID"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    if device_id in DETECTION_THREADS:
        raise HTTPException(status_code=400, detail="检测已在运行")

    device = db.query(Device).filter(Device.id == device_id).first()
    if not device or not device.rtsp_url:
        raise HTTPException(status_code=404, detail="设备不存在或未配置 RTSP 流地址")

    stop_flag = threading.Event()
    STOP_FLAGS[device_id] = stop_flag

    def detection_loop():
        cap = get_video_capture(device.rtsp_url)
        notified_messages = {}

        while not stop_flag.is_set():
            frame = read_frame(cap)
            if frame is None:
                continue

            detection = multi_detector.detect(frame)

            if isinstance(detection, dict):
                causes = detection.get("causes", [])
                for cause in causes:
                    level = cause.get("level")
                    message = cause.get("reason")

                    if level in ["warning", "danger"]:
                        current_time = time.time()
                        if message not in notified_messages or current_time - notified_messages[
                            message] >= COOL_DOWN_TIME:
                            notification_data = NotificationCreate(
                                device_id=device_id,
                                level=level,
                                message=message
                            )
                            notification = create_notification(db, notification_data, user_id=current_user.id)

                            try:
                                import asyncio
                                asyncio.run(send_alert_message(level=level, message=message, alert_id=notification.id))
                            except RuntimeError:
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                loop.run_until_complete(
                                    send_alert_message(level=level, message=message, alert_id=notification.id))
                                loop.close()

                            notified_messages[message] = current_time

            time.sleep(0.1)

        cap.release()

    t = threading.Thread(target=detection_loop, daemon=True)
    DETECTION_THREADS[device_id] = t
    t.start()

    return {"message": f"已启动设备 {device.name} 的持续检测"}


# 停止持续检测
@router.post("/stop-detect")
def stop_detect(
        device_id: int = Query(..., description="设备 ID"),
):
    if device_id not in DETECTION_THREADS:
        raise HTTPException(status_code=400, detail="该设备未在检测中")

    STOP_FLAGS[device_id].set()
    DETECTION_THREADS[device_id].join()

    del DETECTION_THREADS[device_id]
    del STOP_FLAGS[device_id]

    return {"message": f"已停止设备 {device_id} 的检测"}


# 没有用的接口，还不知道怎么用
@router.get("/detect")
async def detect_video_source(
        device_id: int = Query(None, description="设备 ID（用于从数据库获取 RTSP 地址）"),
        video_path: str = Query(None, description="本地测试视频路径（如传入则优先使用）"),
        max_frames: int = Query(10, description="最多处理多少帧"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)  # ✅ 获取当前登录用户
):

    # 检测接口：支持本地视频或设备 ID 对应的 RTSP 流。
    # 优先使用本地视频路径，如未提供则使用数据库中设备的 RTSP 地址。

    # 优先使用本地视频路径
    if video_path:
        if not os.path.exists(video_path):
            raise HTTPException(status_code=400, detail="本地视频文件不存在")

        cap = get_video_capture(video_path)
        source_info = video_path  # 视频路径作为源信息
        device_name = "LocalTest"
        device_id = None  # 本地视频测试时没有设备 ID，设为 None
    elif device_id is not None:
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            raise HTTPException(status_code=404, detail="设备不存在")
        if not device.rtsp_url:
            raise HTTPException(status_code=400, detail="设备未配置 RTSP 流地址")

        cap = get_video_capture(device.rtsp_url)
        source_info = device.rtsp_url
        device_name = device.name

    else:
        raise HTTPException(status_code=400, detail="请提供 device_id 或 video_path")

    # 帧检测循环
    results = []
    count = 0
    notified_messages = {}  # 用于记录已经通知的 (frame_index, message) 和通知时间

    while count < max_frames:
        frame = read_frame(cap)
        if frame is None:
            break

        # 执行检测
        detection = multi_detector.detect(frame)

        # 遍历检测结果并根据危险级别创建通知 + 推送
        if isinstance(detection, dict):  # ensure detection is valid
            overall_level = detection.get("overall_level")
            causes = detection.get("causes", [])

            for cause in causes:
                level = cause.get("level")  # 修改为 level
                message = cause.get("reason")  # 修改为 message

                # 只处理 level 为 'warning' 或 'danger' 的情况
                if level in ['warning', 'danger']:
                    current_time = time.time()
                    # 检查是否已经通知过该消息，且冷却时间是否到
                    if message not in notified_messages or current_time - notified_messages[message] >= COOL_DOWN_TIME:
                        if level and message:
                            # 本地视频测试时 device_id 传入 None 或虚拟 ID
                            notification_data = NotificationCreate(
                                device_id=device_id or 1,  # 本地视频时传入 1 或其他虚拟值
                                level=level,
                                message=message
                            )

                            notification = create_notification(
                                db, notification_data,
                                user_id=current_user.id  # 只传 user_id, 因为 level 和 message 已经在 NotificationCreate 中
                            )

                            # ✅ 异步推送 WebSocket 通知
                            await send_alert_message(  # 使用 await
                                level=level,  # 修改为 level
                                message=message,  # 修改为 message
                                alert_id=notification.id
                            )

                            # 更新通知时间
                            notified_messages[message] = current_time

        results.append({
            "frame_index": count,
            "detection": detection
        })

        count += 1
        time.sleep(0.1)

    cap.release()

    return {
        "device_name": device_name,
        "video_source": source_info,
        "frames_processed": count,
        "results": results
    }
