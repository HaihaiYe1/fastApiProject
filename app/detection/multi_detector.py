import os

import cv2
from app.detection.danger_detection import DangerDetector
from app.detection.suffocation_detection import SuffocationDetector
from app.detection.action_detection import ActionDetector
import time


class MultiDetector:
    def __init__(self):
        self.danger_detector = DangerDetector()
        self.suffocation_detector = SuffocationDetector()
        self.action_detector = ActionDetector()

    def detect(self, frame):
        danger_results = self.danger_detector.detect(frame)
        suffocation_results = self.suffocation_detector.detect(frame)
        action_results = self.action_detector.detect(frame)

        # 收集所有风险项
        all_findings = {
            "danger_detection": danger_results,
            "suffocation_detection": suffocation_results,
            "action_detection": action_results,
        }

        # 提取所有 level 并计算最严重等级
        level_priority = {"safe": 0, "warning": 1, "danger": 2}
        max_level = "safe"
        causes = []

        for detection_type, items in all_findings.items():
            for item in items:
                level = item.get("level", "safe")
                if level_priority[level] > level_priority[max_level]:
                    max_level = level
                # 收集原因
                reason = item.get("reason") or item.get("category") or detection_type
                causes.append({
                    "type": detection_type,
                    "reason": reason,
                    "level": level
                })

        return {
            "overall_level": max_level,
            "causes": causes,
            "details": all_findings
        }


# 仅供timing接口测试耗时所用，处理视频并返回耗时信息
def process_video_with_timing(video_bytes: bytes) -> dict:
    import tempfile
    detector = MultiDetector()

    # 写入临时文件用于 VideoCapture
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
        tmp_file.write(video_bytes)
        tmp_path = tmp_file.name

    cap = cv2.VideoCapture(tmp_path)
    if not cap.isOpened():
        os.remove(tmp_path)
        return {"error": "无法打开视频"}

    total_frames = 0
    timings = {
        "preprocess": 0.0,
        "inference": 0.0,
        "postprocess": 0.0
    }

    start_total = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        total_frames += 1

        # 预处理阶段（可根据需要扩展）
        start = time.time()
        input_frame = cv2.resize(frame, (640, 480))
        end = time.time()
        timings["preprocess"] += end - start

        # 推理阶段
        start = time.time()
        _ = detector.detect(input_frame)
        end = time.time()
        timings["inference"] += end - start

        # 后处理阶段
        start = time.time()
        time.sleep(0.001)
        end = time.time()
        timings["postprocess"] += end - start

    cap.release()
    os.remove(tmp_path)

    total_time = time.time() - start_total

    return {
        "frame_count": total_frames,
        "preprocess": round(timings["preprocess"], 4),
        "inference": round(timings["inference"], 4),
        "postprocess": round(timings["postprocess"], 4),
        "total": round(total_time, 4),
        "avg_per_frame": round(total_time / total_frames, 4) if total_frames else 0
    }
