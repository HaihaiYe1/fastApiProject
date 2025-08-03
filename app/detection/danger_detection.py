# detection/danger_detection.py
import torch
import numpy as np
from ultralytics import YOLO
from app.detection.sort import Sort


class DangerDetector:
    def __init__(self, model_path="yolov8n.pt", device=None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = YOLO(model_path).to(self.device)
        self.tracker = Sort(max_age=10, min_hits=3, iou_threshold=0.3)

        self.danger_categories = {
            "sharp_objects": {"ids": {42, 43, 44, 76}, "level": "danger"},
            "fragile_objects": {"ids": {39, 40, 41, 45, 74, 75}, "level": "warning"},
            "choking_objects": {"ids": {46, 47, 48, 49, 52, 53, 54, 55, 64, 65, 77, 79}, "level": "danger"},
            "hot_objects": {"ids": {68, 69, 70, 78}, "level": "danger"},
            "heavy_objects": {"ids": {56, 57, 58, 59, 60, 72}, "level": "warning"},
            "small_electronics": {"ids": {24, 25, 26, 27, 28, 63, 66, 67, 73}, "level": "safe"},
        }

    def detect(self, frame):
        results = self.model(frame, conf=0.3, iou=0.5)
        dangers = []
        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls.item())
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())

                # Use the tracker to track the object across frames
                detections = np.array([[x1, y1, x2, y2, box.conf.item()]])
                tracked_objects = self.tracker.update(detections)

                # Check if any tracked object matches the danger categories
                for category, info in self.danger_categories.items():
                    if cls_id in info["ids"]:
                        danger_info = {
                            "category": category,
                            "level": info["level"],
                            "bbox": (x1, y1, x2, y2),
                            "confidence": float(box.conf.item()),
                            "cls_id": cls_id
                        }
                        # Add the detection to the results list
                        dangers.append(danger_info)

        return dangers
