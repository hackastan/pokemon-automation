import cv2
import numpy as np

cap = cv2.VideoCapture(1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

def click(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        h, w = param.shape[:2]
        print(f"Pixel: ({x}, {y}) | Proportion: ({x/w:.3f}, {y/h:.3f})")

cv2.namedWindow("Click to get coords", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Click to get coords", 960, 540)

while True:
    ret, frame = cap.read()
    if ret:
        cv2.setMouseCallback("Click to get coords", click, frame)
        cv2.imshow("Click to get coords", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()