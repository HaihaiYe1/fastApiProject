from datetime import time

import cv2


def get_video_capture(source: str):
    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        raise ValueError(f"无法打开视频源: {source}")

    return cap


# min_interval = 0.2 表示每秒抽取 5 帧
def read_frame(cap, min_interval=0.2, last_time=[0]):
    now = time.time()
    if now - last_time[0] < min_interval:
        return None
    ret, frame = cap.read()
    if not ret:
        return None
    last_time[0] = now
    return frame
