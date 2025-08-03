import time
from ultralytics import YOLO
import torch


class SuffocationDetector:
    def __init__(self, model_path="best_WIDER.pt", device=None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = YOLO(model_path).to(self.device)
        self.no_face_start_time = None  # 开始没有检测到脸的时间
        self.danger_threshold_sec = 10  # 设置为 10 秒

    def detect(self, frame):
        results = self.model(frame)
        suffocations = []

        faces_detected = 0
        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls.item())
                if cls_id == 0:  # 假设 0 是人脸类别
                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                    suffocations.append({
                        "bbox": (x1, y1, x2, y2),
                        "confidence": float(box.conf.item()),
                        "level": "safe"
                    })
                    faces_detected += 1

        current_time = time.time()

        if faces_detected == 0:
            if self.no_face_start_time is None:
                self.no_face_start_time = current_time  # 记录开始无脸的时间
            duration = current_time - self.no_face_start_time
            level = "danger" if duration >= self.danger_threshold_sec else "warning"
            suffocations.append({
                "bbox": None,
                "confidence": 0.0,
                "level": level,
                "duration": round(duration, 2)
            })
        else:
            self.no_face_start_time = None  # 重置定时器

        return suffocations
