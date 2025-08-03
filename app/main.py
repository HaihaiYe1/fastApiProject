from fastapi import FastAPI
from .api import auth, device, notification, websocket, video, timing
from .utils.database import Base, engine

# tags是用于自动文档（Swagger UI）的分组显示

# 生成数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI()

# 注册路由
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(device.router, prefix="/device", tags=["Device"])
app.include_router(notification.router, prefix="/notification", tags=["Notification"])
app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])
app.include_router(video.router, prefix="/video", tags=["Video"])
# timing仅供测试
app.include_router(timing.router, prefix="/timing", tags=["Timing"])
