"""
nugget_bridge.py
Automates the Nugget Bridge loop in Pokemon FireRed/LeafGreen.

Type STARTMACRO and press Enter to begin.
Type STOPMACRO to stop the macro (program keeps running).
Type EXIT to close the program.
Type TESTDETECT to run the battle detection check on the current screen.
Type A, B, X, Y, UP, DOWN, LEFT, RIGHT, L, R, START, SELECT, HOME, STOP, ABXY for manual commands.
Ctrl+C also stops at any time.

Logs are saved to nugget_bridge_YYYY-MM-DD_HH-MM-SS.log in the same folder as this script.
"""

import cv2
import serial
import time
import numpy as np
import threading
import sys
import os
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
COM_PORT      = "COM5"
BAUD_RATE     = 115200

# Set to None to auto-detect, or force a specific index (0, 1, 2...)
CAPTURE_INDEX = None

# Battle detection — Rattata's position accounting for black bars on left/right.
# Game image starts ~10% in from left edge. Rattata is lower-left of game area.
RATTATA_ROI_X1 = 0.10
RATTATA_ROI_X2 = 0.34
RATTATA_ROI_Y1 = 0.43
RATTATA_ROI_Y2 = 0.69

# Rattata's purple/violet body color in HSV
# Saturation floor raised to 120 to exclude the low-sat text shadow pixels
PURPLE_HUE_LOW  = 125
PURPLE_HUE_HIGH = 160
PURPLE_SAT_LOW  = 120
PURPLE_SAT_HIGH = 255
PURPLE_VAL_LOW  = 60
PURPLE_VAL_HIGH = 255

# Fewer purple pixels than this = Rattata gone = battle over
PURPLE_PIXEL_THRESHOLD = 150
# ──────────────────────────────────────────────────────────────────────────────

MANUAL_COMMANDS = ["A", "B", "X", "Y", "UP", "DOWN", "LEFT", "RIGHT",
                   "L", "R", "ZL", "ZR", "START", "SELECT", "HOME", "STOP", "ABXY"]

stop_flag  = threading.Event()
exit_flag  = threading.Event()

cap_global = None

# ── Logging ───────────────────────────────────────────────────────────────────
class Logger:
    def __init__(self, log_path):
        self.terminal = sys.stdout
        self.log_file = open(log_path, "w", encoding="utf-8", buffering=1)
        self.log_path = log_path

    def write(self, message):
        self.terminal.write(message)
        self.log_file.write(message)

    def flush(self):
        self.terminal.flush()
        self.log_file.flush()

    def close(self):
        self.log_file.close()

def setup_logging():
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(script_dir, f"nugget_bridge_{timestamp}.log")
    logger = Logger(log_path)
    sys.stdout = logger
    print(f"Logging to: {log_path}")
    return logger
# ──────────────────────────────────────────────────────────────────────────────

def find_capture_index():
    print("Auto-detecting capture card index...")
    for i in range(6):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            for _ in range(10):
                ret, frame = cap.read()
                if ret and frame is not None:
                    h, w = frame.shape[:2]
                    print(f"  Index {i}: {w}x{h}")
                    cap.release()
                    return i
                time.sleep(0.2)
            print(f"  Index {i}: opened but no frame.")
            cap.release()
        else:
            print(f"  Index {i}: no device.")
    return None

def send(ser, cmd, delay=0):
    if stop_flag.is_set():
        return
    print(f"  >> PRESS {cmd}")
    ser.write((cmd + "\n").encode())
    if delay > 0:
        print(f"     waiting {delay}s...")
        end = time.time() + delay
        while time.time() < end:
            if stop_flag.is_set():
                return
            time.sleep(0.1)

def interruptible_sleep(seconds):
    end = time.time() + seconds
    while time.time() < end:
        if stop_flag.is_set():
            return
        time.sleep(0.1)

def handle_command(ser, cmd):
    if cmd in MANUAL_COMMANDS:
        print(f"  >> PRESS {cmd}")
        ser.write((cmd + "\n").encode())
    else:
        print(f"  [unknown command: {cmd}]")

def grab_frame(cap, retries=20, flush=False):
    # Flush stale buffered frames before reading when asked.
    # OpenCV queues several frames internally — without flushing you can
    # get a frame that's several seconds old.
    if flush:
        for _ in range(5):
            cap.read()
    for _ in range(retries):
        ret, frame = cap.read()
        if ret and frame is not None:
            return frame
        time.sleep(0.1)
    print(f"  [frame grab failed after {retries} retries]")
    return None

def is_battle_over(cap):
    """
    Returns True when Rattata is no longer visible.
    High purple pixel count = Rattata present = battle ongoing.
    Low purple pixel count  = Rattata gone   = battle over.
    """
    frame = grab_frame(cap, flush=True)
    if frame is None:
        return False  # safe default — don't skip a round on a bad frame

    h, w = frame.shape[:2]
    x1 = int(w * RATTATA_ROI_X1)
    x2 = int(w * RATTATA_ROI_X2)
    y1 = int(h * RATTATA_ROI_Y1)
    y2 = int(h * RATTATA_ROI_Y2)

    roi = frame[y1:y2, x1:x2]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    lower = np.array([PURPLE_HUE_LOW,  PURPLE_SAT_LOW,  PURPLE_VAL_LOW])
    upper = np.array([PURPLE_HUE_HIGH, PURPLE_SAT_HIGH, PURPLE_VAL_HIGH])
    mask  = cv2.inRange(hsv, lower, upper)
    pixel_count = cv2.countNonZero(mask)

    over = pixel_count < PURPLE_PIXEL_THRESHOLD
    print(f"  [Battle check — purple px: {pixel_count} | threshold: {PURPLE_PIXEL_THRESHOLD}] -> {'OVER' if over else 'ongoing'}")
    return over

def run_test_detect(cap):
    """Check the current frame and report battle detection result."""
    print("\n── TESTDETECT ──────────────────────────────────────")
    print(f"  [{datetime.now().strftime('%H:%M:%S')}] Running detection test on current screen...")
    frame = grab_frame(cap, flush=True)
    if frame is None:
        print("  [FAILED — could not grab frame]")
        print("── TESTDETECT END ──────────────────────────────────\n")
        return

    h, w = frame.shape[:2]
    x1 = int(w * RATTATA_ROI_X1)
    x2 = int(w * RATTATA_ROI_X2)
    y1 = int(h * RATTATA_ROI_Y1)
    y2 = int(h * RATTATA_ROI_Y2)
    roi = frame[y1:y2, x1:x2]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    lower = np.array([PURPLE_HUE_LOW,  PURPLE_SAT_LOW,  PURPLE_VAL_LOW])
    upper = np.array([PURPLE_HUE_HIGH, PURPLE_SAT_HIGH, PURPLE_VAL_HIGH])
    mask  = cv2.inRange(hsv, lower, upper)
    pixel_count = cv2.countNonZero(mask)

    over = pixel_count < PURPLE_PIXEL_THRESHOLD
    print(f"  [purple px: {pixel_count} | threshold: {PURPLE_PIXEL_THRESHOLD}] -> {'battle OVER' if over else 'battle ONGOING'}")
    print("── TESTDETECT END ──────────────────────────────────\n")

def battle_round(ser, cap):
    """Loop A presses until battle ends or macro is stopped.
    Second round only: after first A press, press RIGHT to select move.
    First and subsequent rounds just double-press A.
    """
    round_num = 0
    while not stop_flag.is_set():
        round_num += 1
        print("  [Battle] Round — pressing A...")
        send(ser, "A", delay=1.5)
        if stop_flag.is_set():
            return
        if round_num == 2:
            send(ser, "RIGHT", delay=1.0)
            if stop_flag.is_set():
                return
        send(ser, "A", delay=12.0)
        if stop_flag.is_set():
            return
        if is_battle_over(cap):
            return
        print("  [Battle] Still going — looping.")

def run_walk(ser, cap):
    print(f"\n=== Walk Sequence START — {datetime.now().strftime('%H:%M:%S')} ===")

    # ── Exit Pokemon Center — Down x6 ────────────────────────────────────────
    for _ in range(6):
        send(ser, "DOWN",  delay=0.4)

    interruptible_sleep(3.0)

    # ── Left x5 ──────────────────────────────────────────────────────────────
    for _ in range(5):
        send(ser, "LEFT",  delay=0.4)

    # ── Down x10 ─────────────────────────────────────────────────────────────
    for _ in range(10):
        send(ser, "DOWN",  delay=0.4)

    # ── Left x12 ─────────────────────────────────────────────────────────────
    for _ in range(12):
        send(ser, "LEFT",  delay=0.4)

    # ── Up x10 ───────────────────────────────────────────────────────────────
    for _ in range(10):
        send(ser, "UP",    delay=0.4)

    # ── Right x3 ─────────────────────────────────────────────────────────────
    for _ in range(3):
        send(ser, "RIGHT", delay=0.4)

    # ── Up x8 ────────────────────────────────────────────────────────────────
    for _ in range(8):
        send(ser, "UP",    delay=0.4)

    # ── Right x15 ────────────────────────────────────────────────────────────
    for _ in range(15):
        send(ser, "RIGHT", delay=0.4)

    # ── Up x38 ───────────────────────────────────────────────────────────────
    for _ in range(38):
        send(ser, "UP",    delay=0.4)

    if stop_flag.is_set():
        print("=== Walk STOPPED ===")
    else:
        print(f"=== Walk Sequence COMPLETE — {datetime.now().strftime('%H:%M:%S')} ===")


def run_macro(ser, cap):
    stop_flag.clear()
    print(f"\n=== Nugget Bridge Macro START — {datetime.now().strftime('%H:%M:%S')} ===")

    # ── Approach / dialog ────────────────────────────────────────────────────
    send(ser, "UP",    delay=3)
    send(ser, "B",     delay=2.0)
    send(ser, "B",     delay=2.0)
    send(ser, "B",     delay=4.0)
    send(ser, "B",     delay=2.0)
    send(ser, "B",     delay=2.0)
    send(ser, "B",     delay=1.0)
    send(ser, "B",     delay=1.0)
    send(ser, "B",     delay=1.0)
    send(ser, "B",     delay=2.0)
    send(ser, "B",     delay=2.0)
    send(ser, "B",     delay=6.0)
    send(ser, "B",     delay=10.0)

    # ── Battle ───────────────────────────────────────────────────────────────
    if not stop_flag.is_set():
        battle_round(ser, cap)

    # ── Post-battle dialog ───────────────────────────────────────────────────
    send(ser, "B",     delay=2.0)
    send(ser, "B",     delay=5.0)
    send(ser, "B",     delay=5.0)
    send(ser, "B",     delay=1.0)
    send(ser, "B",     delay=1.0)
    send(ser, "B",     delay=8.0)
    send(ser, "B",     delay=3.0)
    send(ser, "B",     delay=5.0)
    send(ser, "B",     delay=2.0)
    send(ser, "B",     delay=2.0)

    # ── Walk ─────────────────────────────────────────────────────────────────
    if not stop_flag.is_set():
        run_walk(ser, cap)

    if not stop_flag.is_set():
        print(f"=== Nugget Bridge Macro COMPLETE — {datetime.now().strftime('%H:%M:%S')} ===")
    else:
        print("=== Macro STOPPED ===")

def listen_for_commands(ser, cap):
    while not stop_flag.is_set() and not exit_flag.is_set():
        try:
            cmd = input()
            cmd = cmd.strip().upper()
            if cmd == "STOPMACRO":
                print("\n[STOPMACRO received — stopping macro, program still running]")
                stop_flag.set()
                break
            elif cmd == "EXIT":
                print("\n[EXIT received — shutting down]")
                stop_flag.set()
                exit_flag.set()
                break
            elif cmd == "TESTDETECT":
                threading.Thread(target=run_test_detect, args=(cap,), daemon=True).start()
            elif cmd == "STARTWALK":
                print("[CMD] STARTWALK received — but a macro is already running. Use STOPMACRO first.")
            else:
                handle_command(ser, cmd)
        except:
            break

def wait_for_startmacro(ser, cap):
    """Drop back to a prompt after STOPMACRO. Returns (False, None) if EXIT was typed."""
    print("\n[Stopped — type STARTMACRO or STARTWALK to run, EXIT to quit]")
    while True:
        try:
            cmd = input("> ").strip().upper()
        except:
            return False, None
        if cmd == "STARTMACRO":
            print(f"Restarting — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            return True, "macro"
        elif cmd == "STARTWALK":
            print(f"Starting walk — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            return True, "walk"
        elif cmd == "EXIT":
            print("[EXIT received — shutting down]")
            exit_flag.set()
            return False, None
        elif cmd == "TESTDETECT":
            threading.Thread(target=run_test_detect, args=(cap,), daemon=True).start()
        else:
            handle_command(ser, cmd)

def main():
    global cap_global
    logger = setup_logging()

    print(f"Nugget Bridge started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Opening {COM_PORT}...")
    ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
    print("Serial open.")

    capture_index = CAPTURE_INDEX
    if capture_index is None:
        capture_index = find_capture_index()
        if capture_index is None:
            print("ERROR: Could not find any capture device.")
            ser.close()
            sys.stdout = logger.terminal
            logger.close()
            return
    else:
        print(f"Using configured capture index: {capture_index}")

    print(f"Opening capture card at index {capture_index}...")
    cap = cv2.VideoCapture(capture_index)
    cap_global = cap
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    if not cap.isOpened():
        print(f"ERROR: Could not open capture card at index {capture_index}.")
        ser.close()
        sys.stdout = logger.terminal
        logger.close()
        return
    print("Capture card open.")

    print("Warming up capture feed...")
    for _ in range(10):
        cap.read()
        time.sleep(0.1)

    ret, test_frame = cap.read()
    if ret and test_frame is not None:
        print(f"Capture resolution: {test_frame.shape[1]}x{test_frame.shape[0]}")
    else:
        print("[WARNING] Could not read test frame — capture may be unstable.")

    print("\nCommands: A B X Y UP DOWN LEFT RIGHT L R START SELECT HOME STOP ABXY")
    print("Type STARTMACRO to begin, STARTWALK to skip to the walk, STOPMACRO to stop, EXIT to quit.")
    print("Type TESTDETECT to test battle detection on the current screen.\n")

    # Pre-start manual command loop
    start_mode = "macro"
    while True:
        try:
            cmd = input("> ")
        except:
            break
        cmd = cmd.strip().upper()
        if cmd == "STARTMACRO":
            print(f"Macro starting — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            start_mode = "macro"
            break
        elif cmd == "STARTWALK":
            print(f"Walk starting — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            start_mode = "walk"
            break
        elif cmd == "EXIT":
            print("[EXIT received — shutting down]")
            ser.close()
            sys.stdout = logger.terminal
            logger.close()
            return
        elif cmd == "TESTDETECT":
            run_test_detect(cap)
        else:
            handle_command(ser, cmd)

    try:
        first_run = True
        while not exit_flag.is_set():
            stop_flag.clear()

            stop_thread = threading.Thread(target=listen_for_commands, args=(ser, cap), daemon=True)
            stop_thread.start()

            if first_run and start_mode == "walk":
                # First run only — skip straight to the walk
                run_walk(ser, cap)
            else:
                # Full macro every other time
                run_macro(ser, cap)
            first_run = False

            # Kill the listener thread cleanly before next iteration
            stop_flag.set()
            stop_thread.join(timeout=2.0)
            stop_flag.clear()

            if exit_flag.is_set():
                break

            # Always loop back through the full macro

    except KeyboardInterrupt:
        print("\nStopped by keyboard.")

    finally:
        ser.write(b"STOP\n")
        cap.release()
        ser.close()
        print(f"\nEnded at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Log saved to: {logger.log_path}")
        sys.stdout = logger.terminal
        logger.close()

if __name__ == "__main__":
    main()
