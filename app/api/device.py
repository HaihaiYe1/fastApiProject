from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.models import Device, User
from app.schemas import DeviceCreate, DeviceUpdate
from app.utils.database import get_db
from app.utils.security import get_current_user

router = APIRouter()


@router.post("/add")
def add_device(device: DeviceCreate, db: Session = Depends(get_db)):
    # 添加新设备
    new_device = Device(
        email=device.email,
        name=device.name,
        ip=device.ip,
        status=device.status
    )
    db.add(new_device)
    db.commit()
    db.refresh(new_device)
    return {"message": "Device added successfully"}


@router.get("/list")
def get_devices(
        current_user: User = Depends(get_current_user),  # 自动获取当前登录用户
        db: Session = Depends(get_db),
):
    # 自动获取当前用户的 email，并查询其设备列表
    devices = db.query(Device).filter(Device.email == current_user.email).all()

    return [
        {
            "id": d.id,
            "name": d.name,
            "email": d.email,
            "ip": d.ip,
            "status": d.status,
            "rtsp_url": d.rtsp_url
        }
        for d in devices
    ]


@router.get("/get_rtsp_url")
def get_rtsp_url(email: str, db: Session = Depends(get_db)):
    # 根据用户 email 获取设备的 RTSP 地址
    devices = db.query(Device).filter(Device.email == email).all()
    if not devices:
        raise HTTPException(status_code=404, detail="Devices not found")

    # 返回第一个设备的 RTSP 地址（假设一个用户只有一个设备）
    return {"rtspUrl": devices[0].rtsp_url}


@router.put("/update")
def update_device(device_update: DeviceUpdate, db: Session = Depends(get_db)):
    # 更新设备信息
    device = db.query(Device).filter(Device.id == device_update.id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # 仅更新非 None 字段，避免字段值被 None 覆盖
    device.name = device_update.name or device.name
    device.ip = device_update.ip or device.ip
    device.status = device_update.status or device.status
    device.rtsp_url = device_update.rtsp_url or device.rtsp_url
    device.email = device_update.email  # email 必须传

    db.commit()
    db.refresh(device)
    return {"message": "Device updated successfully"}


@router.delete("/delete")
def delete_device(device_id: int, db: Session = Depends(get_db)):
    # 删除设备
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    db.delete(device)
    db.commit()
    return {"message": "Device deleted successfully"}


@router.get("/{device_id}")
def get_device(device_id: int, db: Session = Depends(get_db)):
    # 获取指定设备信息
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    return {
        "id": device.id,
        "name": device.name,
        "email": device.email,
        "ip": device.ip,
        "status": device.status,
        "rtsp_url": device.rtsp_url
    }
