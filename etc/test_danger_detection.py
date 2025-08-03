import cv2
import torch
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
from ultralytics import YOLO
from app.detection.sort import Sort
import matplotlib

matplotlib.use("TkAgg")  # macOS 建议使用 TkAgg

class DangerDetector:
    def __init__(self, model_path="/Users/apple/Documents/PycharmProjects/fastApiProject/yolov8n.pt", device=None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = YOLO(model_path).to(self.device)
        self.tracker = Sort(max_age=10, min_hits=3, iou_threshold=0.3)

        # 指定只检测以下类别
        self.danger_categories = {
            "sharp_objects": {"ids": {42, 43, 44, 76}, "level": "danger"},
            "fragile_objects": {"ids": {39, 40, 41, 45, 74, 75}, "level": "warning"},
            "choking_objects": {"ids": {46, 47, 48, 49, 52, 53, 54, 55, 64, 65, 77, 79}, "level": "danger"},
            "hot_objects": {"ids": {68, 69, 70, 78}, "level": "danger"},
            "heavy_objects": {"ids": {56, 57, 58, 59, 60, 72}, "level": "warning"},
            "small_electronics": {"ids": {24, 25, 26, 27, 28, 63, 66, 67, 73}, "level": "safe"},
        }

        # 展平所有合法 ID 集合，用于过滤
        self.allowed_ids = set()
        for category in self.danger_categories.values():
            self.allowed_ids |= category["ids"]

    def detect(self, frame):
        results = self.model(frame, conf=0.3, iou=0.5)
        dangers = []

        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls.item())

                # 只检测指定类别
                if cls_id not in self.allowed_ids:
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                detections = np.array([[x1, y1, x2, y2, box.conf.item()]])
                _ = self.tracker.update(detections)

                for category, info in self.danger_categories.items():
                    if cls_id in info["ids"]:
                        danger_info = {
                            "category": category,
                            "level": info["level"],
                            "bbox": (x1, y1, x2, y2),
                            "confidence": float(box.conf.item()),
                            "cls_id": cls_id
                        }
                        dangers.append(danger_info)
                        break

        return dangers


def draw_detections(image_bgr, detections, model_names):
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    image_pil = Image.fromarray(image_rgb)
    draw = ImageDraw.Draw(image_pil)

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", size=36)
        small_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", size=20)
    except:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    danger_level_priority = {"safe": 0, "warning": 1, "danger": 2}
    max_level = "safe"

    for det in detections:
        x1, y1, x2, y2 = det["bbox"]
        level = det["level"]
        cls_id = det["cls_id"]
        conf = det["confidence"]
        label = f"{model_names[cls_id]} {conf:.2f} ({level})"

        color = {"danger": "red", "warning": "orange", "safe": "green"}.get(level, "gray")

        draw.rectangle([(x1, y1), (x2, y2)], outline=color, width=3)
        draw.text((x1, max(y1 - 25, 0)), label, fill=color, font=small_font)

        if danger_level_priority[level] > danger_level_priority[max_level]:
            max_level = level

    summary = f"{max_level.upper()}: dangerous object detected" if max_level != "safe" else "SAFE: no danger"
    draw.text((10, 10), summary, fill="black", font=font)

    return image_pil


if __name__ == "__main__":
    image_path = "/Users/apple/Documents/PycharmProjects/fastApiProject/etc/test_picture/fall测试图.png"
    model_path = "/Users/apple/Documents/PycharmProjects/fastApiProject/yolov8n.pt"

    image_bgr = cv2.imread(image_path)
    detector = DangerDetector(model_path)
    detections = detector.detect(image_bgr)
    model_names = detector.model.model.names
    image_out = draw_detections(image_bgr, detections, model_names)

    plt.figure(figsize=(12, 8))
    plt.imshow(image_out)
    plt.axis("off")
    plt.title("Danger Detection Result")
    plt.show()