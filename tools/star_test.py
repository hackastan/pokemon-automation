"""
Star Detection Test
Left window: full frame with detection region highlighted in red
Right window: zoomed detection region and yellow mask
Press Q to quit.
"""

import cv2
import numpy as np

# ── Config — must match shiny_hunter.py ──────────────────────────────────────
CAPTURE_INDEX   = 1

STAR_REGION_X1  = 0.431
STAR_REGION_X2  = 0.489
STAR_REGION_Y1  = 0.215
STAR_REGION_Y2  = 0.300

STAR_HUE_LOW    = 20
STAR_HUE_HIGH   = 35
STAR_SAT_LOW    = 150
STAR_SAT_HIGH   = 255
STAR_VAL_LOW    = 200
STAR_VAL_HIGH   = 255

STAR_PIXEL_THRESHOLD = 20
# ──────────────────────────────────────────────────────────────────────────────

cap = cv2.VideoCapture(CAPTURE_INDEX)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

cv2.namedWindow("Full Frame", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Full Frame", 960, 540)

cv2.namedWindow("Region Zoom", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Region Zoom", 600, 300)

print("Running — press Q to quit.")

while True:
    ret, frame = cap.read()
    if not ret:
        continue

    h, w = frame.shape[:2]
    x1 = int(w * STAR_REGION_X1)
    x2 = int(w * STAR_REGION_X2)
    y1 = int(h * STAR_REGION_Y1)
    y2 = int(h * STAR_REGION_Y2)

    region = frame[y1:y2, x1:x2]
    hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
    lower = np.array([STAR_HUE_LOW,  STAR_SAT_LOW,  STAR_VAL_LOW])
    upper = np.array([STAR_HUE_HIGH, STAR_SAT_HIGH, STAR_VAL_HIGH])
    mask  = cv2.inRange(hsv, lower, upper)
    yellow_pixels = cv2.countNonZero(mask)

    status = "SHINY DETECTED" if yellow_pixels >= STAR_PIXEL_THRESHOLD else "not shiny"
    print(f"Yellow pixels: {yellow_pixels:4d} | {status}")

    # Draw red rectangle on full frame showing detection region
    display_frame = frame.copy()
    cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
    cv2.putText(display_frame, f"px: {yellow_pixels} | {status}", (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0,
                (0, 0, 255) if yellow_pixels >= STAR_PIXEL_THRESHOLD else (0, 255, 0), 2)
    cv2.imshow("Full Frame", display_frame)

    # Show zoomed region and mask
    region_big = cv2.resize(region, (300, 300))
    mask_big   = cv2.resize(cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR), (300, 300))
    combined = np.hstack([region_big, mask_big])
    cv2.imshow("Region Zoom", combined)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
