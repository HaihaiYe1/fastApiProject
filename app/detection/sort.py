# sort.py: Simple Online and Realtime Tracker (SORT)
import numpy as np
from scipy.optimize import linear_sum_assignment
from filterpy.kalman import KalmanFilter


def iou(bb_test, bb_gt):
    # 计算 IOU（Intersection Over Union）用于目标匹配
    xx1 = np.maximum(bb_test[0], bb_gt[0])
    yy1 = np.maximum(bb_test[1], bb_gt[1])
    xx2 = np.minimum(bb_test[2], bb_gt[2])
    yy2 = np.minimum(bb_test[3], bb_gt[3])
    w = np.maximum(0., xx2 - xx1)
    h = np.maximum(0., yy2 - yy1)
    wh = w * h
    o = wh / ((bb_test[2] - bb_test[0]) * (bb_test[3] - bb_test[1]) +
              (bb_gt[2] - bb_gt[0]) * (bb_gt[3] - bb_gt[1]) - wh)
    return o


class KalmanBoxTracker:
    # 目标跟踪的卡尔曼滤波器
    count = 0

    def __init__(self, bbox):
        self.kf = KalmanFilter(dim_x=7, dim_z=4)
        self.kf.F = np.array([[1, 0, 0, 0, 1, 0, 0],
                              [0, 1, 0, 0, 0, 1, 0],
                              [0, 0, 1, 0, 0, 0, 1],
                              [0, 0, 0, 1, 0, 0, 0],
                              [0, 0, 0, 0, 1, 0, 0],
                              [0, 0, 0, 0, 0, 1, 0],
                              [0, 0, 0, 0, 0, 0, 1]])
        self.kf.H = np.array([[1, 0, 0, 0, 0, 0, 0],
                              [0, 1, 0, 0, 0, 0, 0],
                              [0, 0, 1, 0, 0, 0, 0],
                              [0, 0, 0, 1, 0, 0, 0]])
        self.kf.R[2:, 2:] *= 10.
        self.kf.P[4:, 4:] *= 1000.
        self.kf.P *= 10.
        self.kf.Q[-1, -1] *= 0.01
        self.kf.Q[4:, 4:] *= 0.01
        self.kf.x[:4] = np.expand_dims(bbox, axis=0).T
        self.time_since_update = 0
        self.id = KalmanBoxTracker.count
        KalmanBoxTracker.count += 1

    def update(self, bbox):
        self.time_since_update = 0
        self.kf.update(bbox)

    def predict(self):
        if (self.kf.x[6] + self.kf.x[2]) <= 0:
            self.kf.x[6] *= 0.0
        self.kf.predict()
        return self.kf.x[:4].flatten()

    def get_state(self):
        return self.kf.x[:4].flatten()


class Sort:
    # SORT 目标跟踪器

    def __init__(self, max_age=1, min_hits=3, iou_threshold=0.3):
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.trackers = []
        self.frame_count = 0

    def update(self, dets):
        self.frame_count += 1
        ret = []
        if len(self.trackers) == 0:
            for i in range(len(dets)):
                self.trackers.append(KalmanBoxTracker(dets[i, :4]))

        matches, unmatched_dets, unmatched_trks = self.associate_detections_to_trackers(dets, self.trackers)

        for m in matches:
            self.trackers[m[1]].update(dets[m[0], :4])

        for i in unmatched_dets:
            self.trackers.append(KalmanBoxTracker(dets[i, :4]))

        for t in reversed(range(len(self.trackers))):
            pos = self.trackers[t].predict()
            if self.trackers[t].time_since_update > self.max_age:
                del self.trackers[t]
            else:
                ret.append(np.concatenate((pos, [self.trackers[t].id + 1])).reshape(1, -1))

        if len(ret) > 0:
            return np.concatenate(ret)
        return np.empty((0, 5))

    def associate_detections_to_trackers(self, dets, trackers):
        # 进行目标匹配
        if len(trackers) == 0:
            return np.empty((0, 2), dtype=int), np.arange(len(dets)), np.empty((0, 5), dtype=int)
        iou_matrix = np.zeros((len(dets), len(trackers)), dtype=np.float32)
        for d, det in enumerate(dets):
            for t, trk in enumerate(trackers):
                iou_matrix[d, t] = iou(det[:4], trk.get_state())

        matched_indices = linear_sum_assignment(-iou_matrix)
        matched_indices = np.array(list(zip(matched_indices[0], matched_indices[1])))
        unmatched_detections = np.delete(np.arange(len(dets)), matched_indices[:, 0])
        unmatched_trackers = np.delete(np.arange(len(trackers)), matched_indices[:, 1])
        return matched_indices, unmatched_detections, unmatched_trackers
