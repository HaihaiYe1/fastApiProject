import cv2
import torch
import time
import numpy as np
import mediapipe as mp
from PIL import Image, ImageDraw, ImageFont
from ultralytics import YOLO
from app.detection.sort import Sort
import matplotlib

matplotlib.use("TkAgg")  # Mac用户可用 "MacOSX"


class UnifiedDetector:
    def __init__(self,
                 danger_model_path="/Users/apple/Documents/PycharmProjects/fastApiProject/yolov8n.pt",
                 face_model_path="/Users/apple/Documents/PycharmProjects/fastApiProject/best_WIDER.pt",
                 device=None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        # YOLOv8 检测危险物品
        self.danger_model = YOLO(danger_model_path).to(self.device)
        self.danger_tracker = Sort(max_age=10, min_hits=3, iou_threshold=0.3)

        # WIDER 人脸模型检测窒息
        self.face_model = YOLO(face_model_path).to(self.device)
        self.no_face_start_time = None
        self.danger_threshold_sec = 10

        # MediaPipe 姿态检测
        self.pose = mp.solutions.pose.Pose(static_image_mode=True, model_complexity=1)

        # 类别定义
        self.danger_categories = {
            "sharp_objects": {"ids": {42, 43, 44, 76}, "level": "danger"},
            "fragile_objects": {"ids": {39, 40, 41, 45, 74, 75}, "level": "warning"},
            "choking_objects": {"ids": {46, 47, 48, 49, 52, 53, 54, 55, 64, 65, 77, 79}, "level": "danger"},
            "hot_objects": {"ids": {68, 69, 70, 78}, "level": "danger"},
            "heavy_objects": {"ids": {56, 57, 58, 59, 60, 72}, "level": "warning"},
            "small_electronics": {"ids": {24, 25, 26, 27, 28, 63, 66, 67, 73}, "level": "safe"},
        }
        self.allowed_ids = set()
        for c in self.danger_categories.values():
            self.allowed_ids |= c["ids"]

    def detect(self, frame_bgr):
        results = {
            "danger_objects": [],
            "suffocation": [],
            "posture": []
        }

        ### 1. 危险物检测
        danger_result = self.danger_model(frame_bgr, conf=0.3, iou=0.5)[0]
        for box in danger_result.boxes:
            cls_id = int(box.cls.item())
            if cls_id not in self.allowed_ids:
                continue
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            for category, info in self.danger_categories.items():
                if cls_id in info["ids"]:
                    results["danger_objects"].append({
                        "category": category,
                        "level": info["level"],
                        "bbox": (x1, y1, x2, y2),
                        "confidence": float(box.conf.item()),
                        "cls_id": cls_id
                    })
                    break

        ### 2. 窒息检测
        face_result = self.face_model(frame_bgr)[0]
        faces_detected = 0
        for box in face_result.boxes:
            if int(box.cls.item()) == 0:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                results["suffocation"].append({
                    "bbox": (x1, y1, x2, y2),
                    "confidence": float(box.conf.item()),
                    "level": "safe"
                })
                faces_detected += 1

        current_time = time.time()
        if faces_detected == 0:
            if self.no_face_start_time is None:
                self.no_face_start_time = current_time
            duration = current_time - self.no_face_start_time
            level = "danger" if duration >= self.danger_threshold_sec else "warning"
            results["suffocation"].append({
                "bbox": None,
                "confidence": 0.0,
                "level": level,
                "duration": round(duration, 2)
            })
        else:
            self.no_face_start_time = None

        ### 3. 姿态检测
        image_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        pose_result = self.pose.process(image_rgb)

        if pose_result.pose_landmarks:
            landmarks = pose_result.pose_landmarks.landmark
            nose = landmarks[mp.solutions.pose.PoseLandmark.NOSE.value]
            left_shoulder = landmarks[mp.solutions.pose.PoseLandmark.LEFT_SHOULDER.value]
            right_shoulder = landmarks[mp.solutions.pose.PoseLandmark.RIGHT_SHOULDER.value]
            shoulder_height = (left_shoulder.y + right_shoulder.y) / 2
            is_facedown = nose.y > shoulder_height + 0.05
            results["posture"].append({
                "facedown": is_facedown,
                "level": "danger" if is_facedown else "safe"
            })

        return results


def draw_all_results(frame_bgr, results, model_names):
    image_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    image_pil = Image.fromarray(image_rgb)
    draw = ImageDraw.Draw(image_pil)

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", size=24)
        small_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", size=18)
    except:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    danger_level_priority = {"safe": 0, "warning": 1, "danger": 2}
    max_level = "safe"

    # 危险物绘制
    for det in results["danger_objects"]:
        x1, y1, x2, y2 = det["bbox"]
        level = det["level"]
        cls_id = det["cls_id"]
        label = f"{model_names[cls_id]} ({level})"
        color = {"danger": "red", "warning": "orange", "safe": "green"}.get(level, "gray")
        draw.rectangle([(x1, y1), (x2, y2)], outline=color, width=3)
        draw.text((x1, max(y1 - 25, 0)), label, fill=color, font=small_font)
        if danger_level_priority[level] > danger_level_priority[max_level]:
            max_level = level

    # 窒息检测提示
    for suf in results["suffocation"]:
        level = suf["level"]
        color = {"danger": "red", "warning": "orange", "safe": "green"}.get(level, "gray")
        if suf["bbox"]:
            x1, y1, x2, y2 = suf["bbox"]
            draw.rectangle([(x1, y1), (x2, y2)], outline=color, width=3)
        else:
            draw.text((10, 80), f"No Face: {level}, {suf['duration']}s", fill=color, font=font)
        if danger_level_priority[level] > danger_level_priority[max_level]:
            max_level = level

    # 姿态检测提示 + 骨架绘制
    for act in results["posture"]:
        level = act["level"]
        label = f"Posture: {level}"
        color = {"danger": "red", "warning": "orange", "safe": "green"}.get(level, "gray")
        draw.text((10, 120), label, fill=color, font=font)
        if danger_level_priority[level] > danger_level_priority[max_level]:
            max_level = level

    # === 新增骨骼绘制 ===
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
    annotated_image = np.array(image_pil)  # 转换为 OpenCV 图像供 MediaPipe 画图
    image_rgb = cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR)

    pose = mp_pose.Pose(static_image_mode=True)
    pose_results = pose.process(cv2.cvtColor(image_rgb, cv2.COLOR_BGR2RGB))
    if pose_results.pose_landmarks:
        mp_drawing.draw_landmarks(
            image=image_rgb,
            landmark_list=pose_results.pose_landmarks,
            connections=mp_pose.POSE_CONNECTIONS,
            landmark_drawing_spec=mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=3),
            connection_drawing_spec=mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2),
        )

    # 总体危险等级
    image_pil = Image.fromarray(cv2.cvtColor(image_rgb, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(image_pil)
    draw.text((10, 20), f"Overall: {max_level.upper()}", fill="black", font=font)
    return image_pil


if __name__ == "__main__":
    image_path = "/Users/apple/Documents/PycharmProjects/fastApiProject/etc/test_picture/multi测试图.png"
    image_bgr = cv2.imread(image_path)

    detector = UnifiedDetector(
        danger_model_path="/Users/apple/Documents/PycharmProjects/fastApiProject/yolov8n.pt",
        face_model_path="/Users/apple/Documents/PycharmProjects/fastApiProject/best_WIDER.pt"
    )

    results = detector.detect(image_bgr)
    model_names = detector.danger_model.model.names
    image_out = draw_all_results(image_bgr, results, model_names)

    import matplotlib.pyplot as plt

    plt.imshow(image_out)
    plt.axis("off")
    plt.title("Unified Danger Detection")
    plt.show()
