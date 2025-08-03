import time
from ultralytics import YOLO
import torch
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import matplotlib

matplotlib.use("TkAgg")  # Mac用户可用 "MacOSX"


class SuffocationDetector:
    def __init__(self, model_path="/Users/apple/Documents/PycharmProjects/fastApiProject/best_WIDER.pt", device=None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = YOLO(model_path).to(self.device)
        self.no_face_start_time = None
        self.danger_threshold_sec = 10

    def detect(self, frame):
        results = self.model(frame)
        suffocations = []
        faces_detected = 0

        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls.item())
                if cls_id == 0:  # 只处理人脸类别
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
                self.no_face_start_time = current_time
            duration = current_time - self.no_face_start_time
            level = "danger" if duration >= self.danger_threshold_sec else "warning"
            suffocations.append({
                "bbox": None,
                "confidence": 0.0,
                "level": level,
                "duration": round(duration, 2)
            })
        else:
            self.no_face_start_time = None

        return suffocations


def draw_results(image, results):
    draw = ImageDraw.Draw(image)

    # 使用系统字体（适配中文/大字号）
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 24)
    except:
        font = ImageFont.load_default()

    # 先画人脸框
    for res in results:
        bbox = res.get("bbox")
        level = res.get("level")
        if bbox:
            x1, y1, x2, y2 = bbox
            color = "green" if level == "safe" else "yellow" if level == "warning" else "red"
            draw.rectangle([x1, y1, x2, y2], outline=color, width=3)

    # 再统一显示文字信息在右上角
    text_x = image.width - 350
    text_y = 20
    line_spacing = 35

    for idx, res in enumerate(results):
        bbox = res.get("bbox")
        level = res.get("level")
        conf = res.get("confidence", 0.0)
        duration = res.get("duration", None)

        if bbox:
            label = f"[{idx + 1}] Face: {level} ({conf:.2f})"
        else:
            label = f"[!] No Face: {level}, {duration:.1f}s"

        color = "green" if level == "safe" else "yellow" if level == "warning" else "red"
        draw.text((text_x, text_y + idx * line_spacing), label, fill=color, font=font)

    return image


if __name__ == "__main__":
    # 本地图像路径
    image_path = "/Users/apple/Documents/PycharmProjects/fastApiProject/etc/test_picture/suff测试图.png"
    image = Image.open(image_path).convert("RGB")

    # 初始化检测器
    detector = SuffocationDetector(
        model_path="/Users/apple/Documents/PycharmProjects/fastApiProject/best_WIDER.pt"
    )

    # 执行检测
    results = detector.detect(image)

    # 绘制并展示
    image_with_boxes = draw_results(image, results)
    plt.imshow(image_with_boxes)
    plt.axis("off")
    plt.title("Detection Result")
    plt.show()
