# detection/action_detection.py
import cv2
import mediapipe as mp


class ActionDetector:
    def __init__(self, detection_confidence=0.5):
        self.pose = mp.solutions.pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            enable_segmentation=False,
            min_detection_confidence=detection_confidence
        )

    def detect(self, frame):
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(frame_rgb)

        if not results.pose_landmarks:
            # 返回明确的错误信息
            return [{"level": "danger", "reason": "no_pose_detected"}]

        landmarks = results.pose_landmarks.landmark

        # 关键点索引
        NOSE = 0
        LEFT_SHOULDER = 11
        RIGHT_SHOULDER = 12
        LEFT_HIP = 23
        RIGHT_HIP = 24

        # 获取关键点坐标
        nose_y = landmarks[NOSE].y
        shoulder_y = (landmarks[LEFT_SHOULDER].y + landmarks[RIGHT_SHOULDER].y) / 2
        hip_y = (landmarks[LEFT_HIP].y + landmarks[RIGHT_HIP].y) / 2

        # 逻辑判断
        if nose_y > hip_y + 0.05:
            # 脸远低于臀部：可能跌倒
            return [{"level": "danger", "reason": "fall_detected"}]
        elif nose_y > shoulder_y:
            # 脸低于肩膀（趴着）
            return [{"level": "warning", "reason": "face_down"}]
        else:
            # 正常坐/立状态
            return [{"level": "safe", "reason": "normal"}]
