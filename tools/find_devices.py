import cv2

for i in range(6):
    cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
    if cap.isOpened():
        ret, frame = cap.read()
        status = f"{frame.shape[1]}x{frame.shape[0]}" if ret and frame is not None else "opened but no frame"
        print(f"Index {i}: {status}")
        cap.release()
    else:
        print(f"Index {i}: no device")