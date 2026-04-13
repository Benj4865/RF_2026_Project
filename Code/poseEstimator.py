import cv2
from ultralytics import YOLO
import numpy as np

class PoseEstimator:
    def __init__(
        self,
        model_path="Code/yolo26n-pose.pt",
        camera_index=0,
        inference_width=256,
        confidence=0.35,
        iou=0.45,
        max_detections=1,
    ):
        self.model = YOLO(model_path)
        self.cap = cv2.VideoCapture(camera_index)
        self.last_keypoints = None
        self.inference_width = inference_width
        self.confidence = confidence
        self.iou = iou
        self.max_detections = max_detections

    def _prepare_inference_frame(self, frame):
        frame_height, frame_width = frame.shape[:2]
        if self.inference_width is None or frame_width <= self.inference_width:
            return frame, 1.0, 1.0

        inference_scale = self.inference_width / float(frame_width)
        resized_height = max(1, int(frame_height * inference_scale))
        resized_frame = cv2.resize(frame, (self.inference_width, resized_height), interpolation=cv2.INTER_LINEAR)
        scale_x = frame_width / float(self.inference_width)
        scale_y = frame_height / float(resized_height)
        return resized_frame, scale_x, scale_y

    def get_frame_and_keypoints(self):
        ret, frame = self.cap.read()
        if not ret:
            return None, None, None

        inference_frame, scale_x, scale_y = self._prepare_inference_frame(frame)
        results = self.model(
            inference_frame,
            verbose=False,
            conf=self.confidence,
            iou=self.iou,
            max_det=self.max_detections,
        )

        keypoints = None
        if results[0].keypoints is not None and len(results[0].keypoints.xy) > 0:
            keypoints = results[0].keypoints.xy[0].cpu().numpy().astype(np.float32)
            keypoints[:, 0] *= scale_x
            keypoints[:, 1] *= scale_y
            self.last_keypoints = keypoints

        return frame, keypoints, None

    def release(self):
        self.cap.release()
        cv2.destroyAllWindows()