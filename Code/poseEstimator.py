import cv2
from ultralytics import YOLO

# Load the YOLO pose model
model = YOLO("Code/yolo26n-pose.pt")

# Initialize the camera
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Run YOLO pose estimation on the frame
    results = model(frame)

    # Check if any person is detected
    if results[0].keypoints is not None and len(results[0].keypoints.xy) > 0:
        pose_img = results[0].plot()
        keypoints = results[0].keypoints
        # Check if there are at least 13 keypoints (COCO format)
        if keypoints.xy.shape[1] > 12:
            left_hip = keypoints.xy[0][11]
            right_hip = keypoints.xy[0][12]
            cv2.putText(pose_img, f"Left Hip: {left_hip}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
            cv2.putText(pose_img, f"Right Hip: {right_hip}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
        else:
            cv2.putText(pose_img, "Not enough keypoints", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
    else:
        # If no person detected, just show the original frame with a message
        pose_img = frame.copy()
        cv2.putText(pose_img, "No person detected", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)

    cv2.imshow('YOLO Pose', pose_img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()