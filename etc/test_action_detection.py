import cv2
import mediapipe as mp
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import matplotlib

matplotlib.use("TkAgg")  # Mac用户可用 "MacOSX"

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils


class ActionDetector:
    def __init__(self, detection_confidence=0.5):
        self.pose = mp_pose.Pose(
            static_image_mode=True,
            model_complexity=1,
            enable_segmentation=False,
            min_detection_confidence=detection_confidence
        )

    def detect(self, frame_bgr):
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        results = self.pose.process(frame_rgb)

        h, w, _ = frame_bgr.shape

        if not results.pose_landmarks:
            return {
                "level": "danger",
                "reason": "no_pose_detected",
                "landmarks": None,
                "results": results
            }

        landmarks = results.pose_landmarks.landmark

        # 关键点索引
        NOSE = 0
        LEFT_SHOULDER = 11
        RIGHT_SHOULDER = 12
        LEFT_HIP = 23
        RIGHT_HIP = 24

        nose_y = landmarks[NOSE].y
        shoulder_y = (landmarks[LEFT_SHOULDER].y + landmarks[RIGHT_SHOULDER].y) / 2
        hip_y = (landmarks[LEFT_HIP].y + landmarks[RIGHT_HIP].y) / 2

        if nose_y > hip_y + 0.05:
            level = "danger"
            reason = "fall_detected"
        elif nose_y > shoulder_y:
            level = "warning"
            reason = "face_down"
        else:
            level = "safe"
            reason = "normal"

        return {
            "level": level,
            "reason": reason,
            "landmarks": results.pose_landmarks,
            "results": results
        }


def visualize_pose(image_bgr, detection_info):
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

    if detection_info["landmarks"]:
        mp_drawing.draw_landmarks(
            image_rgb,
            detection_info["landmarks"],
            mp_pose.POSE_CONNECTIONS,
            mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=3),
            mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2)
        )

    # 转为 PIL 图像以添加大字号文字
    image_pil = Image.fromarray(image_rgb)
    draw = ImageDraw.Draw(image_pil)

    # macOS 字体路径；Windows 可用 "arialbd.ttf"
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", size=26)
    except:
        font = ImageFont.load_default()

    summary_text = f"{detection_info['level'].upper()}: {detection_info['reason'].replace('_', ' ').title()}"
    draw.text((10, 10), summary_text, fill="black", font=font)

    return image_pil


if __name__ == "__main__":
    img_path = "/Users/apple/Documents/PycharmProjects/fastApiProject/etc/test_picture/nofall测试图.png"
    image_bgr = cv2.imread(img_path)

    detector = ActionDetector()
    result = detector.detect(image_bgr)

    image_with_pose = visualize_pose(image_bgr, result)

    plt.figure(figsize=(10, 8))
    plt.imshow(image_with_pose)
    plt.axis("off")
    plt.title("Pose Detection Result")
    plt.show()
