import cv2
from ultralytics import YOLO

class PoseEstimator:
    def __init__(self, model_path="Code/yolo26n-pose.pt", camera_index=0):
        self.model = YOLO(model_path)
        self.cap = cv2.VideoCapture(camera_index)
        self.last_keypoints = None

    def get_frame_and_keypoints(self):
        ret, frame = self.cap.read()
        if not ret:
            return None, None, None
        results = self.model(frame)
        keypoints = None
        pose_overlay = None
        if results[0].keypoints is not None and len(results[0].keypoints.xy) > 0:
            keypoints = results[0].keypoints.xy[0]  # First person detected
            self.last_keypoints = keypoints
            pose_overlay = results[0].plot()
        else:
            pose_overlay = frame.copy()
        return frame, keypoints, pose_overlay

    def release(self):
        self.cap.release()
        cv2.destroyAllWindows()
