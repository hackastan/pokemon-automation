import cv2
for i in range(4):
    cap = cv2.VideoCapture(i)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    ret, frame = cap.read()
    if ret and frame is not None:
        print(f"Index {i} works — {frame.shape[1]}x{frame.shape[0]}")
    else:
        print(f"Index {i} — no device")
    cap.release()