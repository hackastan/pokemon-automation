"""
FireRed Shiny Hunter
Requires: pip install opencv-python pyserial numpy obsws-python

Type STARTMACRO and press Enter to start the hunt.
Type STOPMACRO and press Enter to stop the macro (program keeps running).
Type EXIT to close the program.
Type TESTMACRO to run the shiny detection check on the current screen.
Type A, B, X, Y, UP, DOWN, LEFT, RIGHT, HOME, STOP, or ABXY for manual commands.
Ctrl+C also stops at any time.

OBS Setup:
- Tools -> WebSocket Server Settings -> Enable, port 4455, no auth
- Settings -> Output -> Replay Buffer -> Enable, set to 600 seconds
- Click Start Replay Buffer before running this script

Logs are saved to shiny_hunter_YYYY-MM-DD_HH-MM-SS.log in the same folder as this script.
"""

import cv2
import serial
import time
import random
import numpy as np
import threading
import sys
import os
from datetime import datetime

# Try to import OBS websocket — gracefully handle if not available
try:
    import obsws_python as obs
    OBS_AVAILABLE = True
except ImportError:
    OBS_AVAILABLE = False

# ── Config ────────────────────────────────────────────────────────────────────
COM_PORT        = "COM5"
BAUD_RATE       = 115200

# Set to None to auto-detect, or set a specific number (0, 1, 2...) to force it
CAPTURE_INDEX   = None

# Detection region — star location in portrait box
STAR_REGION_X1  = 0.431
STAR_REGION_X2  = 0.489
STAR_REGION_Y1  = 0.215
STAR_REGION_Y2  = 0.300

# Star color — bright yellow/gold in HSV
STAR_HUE_LOW    = 20
STAR_HUE_HIGH   = 35
STAR_SAT_LOW    = 150
STAR_SAT_HIGH   = 255
STAR_VAL_LOW    = 200
STAR_VAL_HIGH   = 255

STAR_PIXEL_THRESHOLD = 20

# Random wait after ABXY soft reset (seconds)
RESET_WAIT_MIN  = 5.00
RESET_WAIT_MAX  = 5.50

# Seconds to wait after non-detection before second check
PRE_RESET_WAIT  = 3

# OBS Websocket settings
OBS_HOST        = "localhost"
OBS_PORT        = 4455
OBS_PASSWORD    = ""        # Leave empty if auth is disabled
# ──────────────────────────────────────────────────────────────────────────────

MANUAL_COMMANDS = ["A", "B", "X", "Y", "UP", "DOWN", "LEFT", "RIGHT", "HOME", "STOP", "ABXY"]

stop_flag  = threading.Event()
exit_flag  = threading.Event()  # set this to kill the program cleanly

cap_global = None

# ── Logging setup ─────────────────────────────────────────────────────────────
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
    log_path = os.path.join(script_dir, f"shiny_hunter_{timestamp}.log")
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

def save_obs_replay():
    if not OBS_AVAILABLE:
        print("  [OBS replay save skipped — obsws-python not installed]")
        return
    try:
        print("  [Saving OBS replay buffer...]")
        cl = obs.ReqClient(host=OBS_HOST, port=OBS_PORT, password=OBS_PASSWORD, timeout=3)
        cl.save_replay_buffer()
        print("  [OBS replay buffer saved!]")
    except Exception as e:
        print(f"  [OBS replay save failed: {e}]")
        print("  [Make sure OBS is open, WebSocket is enabled, and Replay Buffer is running]")

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

def detect_shiny_star(frame):
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
    return yellow_pixels >= STAR_PIXEL_THRESHOLD, yellow_pixels, region, mask

def grab_frame(cap, retries=20):
    for i in range(retries):
        ret, frame = cap.read()
        if ret and frame is not None:
            return frame
        time.sleep(0.3)
    print(f"  [frame grab failed after {retries} retries]")
    return None

def run_test_macro(cap):
    """Run the full detection sequence on the current screen and report results."""
    print("\n── TESTMACRO ──────────────────────────────────────")
    print(f"  [{datetime.now().strftime('%H:%M:%S')}] Running detection test on current screen...")

    print("  [CHECK 1 — grabbing frame]")
    frame = grab_frame(cap)
    if frame is None:
        print("  [CHECK 1 FAILED — could not grab frame]")
        print("── TESTMACRO END ──────────────────────────────────\n")
        return

    is_shiny, pixel_count, region, mask = detect_shiny_star(frame)
    print(f"  [CHECK 1 — yellow pixels: {pixel_count} | threshold: {STAR_PIXEL_THRESHOLD}] -> {'SHINY!' if is_shiny else 'not shiny'}")

    debug_mask = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
    combined = np.hstack([region, debug_mask])
    cv2.imshow("Detection Region | Mask", combined)
    cv2.waitKey(1)

    if is_shiny:
        print("  [TESTMACRO RESULT: SHINY DETECTED on check 1]")
        print("── TESTMACRO END ──────────────────────────────────\n")
        return

    print(f"  [waiting {PRE_RESET_WAIT}s before second check...]")
    for i in range(PRE_RESET_WAIT, 0, -1):
        print(f"  [{i}]")
        time.sleep(1)

    print("  [CHECK 2 — grabbing frame]")
    frame2 = grab_frame(cap)
    if frame2 is None:
        print("  [CHECK 2 FAILED — could not grab frame]")
        print("── TESTMACRO END ──────────────────────────────────\n")
        return

    is_shiny2, pixel_count2, region2, mask2 = detect_shiny_star(frame2)
    print(f"  [CHECK 2 — yellow pixels: {pixel_count2} | threshold: {STAR_PIXEL_THRESHOLD}] -> {'SHINY!' if is_shiny2 else 'not shiny'}")

    debug_mask2 = cv2.cvtColor(mask2, cv2.COLOR_GRAY2BGR)
    combined2 = np.hstack([region2, debug_mask2])
    cv2.imshow("Detection Region | Mask", combined2)
    cv2.waitKey(1)

    if is_shiny2:
        print("  [TESTMACRO RESULT: SHINY DETECTED on check 2]")
    else:
        print(f"  [TESTMACRO RESULT: not shiny — check 1: {pixel_count}px, check 2: {pixel_count2}px]")

    print("── TESTMACRO END ──────────────────────────────────\n")

def run_reset_sequence(ser, first_run=False):
    print("Starting reset sequence...")
    if stop_flag.is_set():
        return

    if first_run:
        print("  [initial soft reset]")
        ser.write(b"ABXY\n")

    wait = round(random.uniform(RESET_WAIT_MIN, RESET_WAIT_MAX), 2)
    print(f"  [waiting {wait}s after reset...]")
    interruptible_sleep(wait)
    if stop_flag.is_set():
        return

    steps = [
        ("A", 0.5),
        ("A", 0.5),
        ("A", 3.5),
        ("A", 1.5),
        ("B", 2.5),
        ("A", 1.5),
        ("B", 1.5),
        ("A", 1.5),
        ("B", 5),
        ("B", 3.0),
        ("B", 5),
        ("X", 0.5),
        ("A", 1),
        ("A", 1),
        ("A", 2),
    ]
    for btn, delay in steps:
        if stop_flag.is_set():
            return
        send(ser, btn, delay=delay)

    print("  [sequence complete — checking for shiny]")

def run_shiny_sequence(ser):
    print("SHINY DETECTED — saving replay buffer then running save sequence...")
    save_obs_replay()

    interruptible_sleep(2)
    send(ser, "B",    delay=2)
    send(ser, "B",    delay=2)
    send(ser, "B",    delay=2)
    send(ser, "DOWN", delay=2)
    send(ser, "DOWN", delay=2)
    send(ser, "DOWN", delay=2)
    send(ser, "A",    delay=2)
    send(ser, "A",    delay=2)
    send(ser, "A",    delay=2)
    send(ser, "STOP")
    print("Done. Shiny saved!")

def soft_reset(ser):
    if stop_flag.is_set():
        return
    print("  >> SOFT RESET (ABXY)")
    ser.write(b"ABXY\n")
    print("  [waiting for reset to complete...]")
    interruptible_sleep(3.0)

def pre_reset_countdown():
    print(f"  [not shiny — second check in {PRE_RESET_WAIT}s... Ctrl+C to abort]")
    for i in range(PRE_RESET_WAIT, 0, -1):
        if stop_flag.is_set():
            return True
        print(f"  [{i}]")
        time.sleep(1)
    return stop_flag.is_set()

def listen_for_commands(ser, cap):
    while not stop_flag.is_set() and not exit_flag.is_set():
        try:
            cmd = input()
            cmd = cmd.strip().upper()
            if cmd == "STOPMACRO":
                print("\n[STOPMACRO received — stopping hunt, program still running]")
                stop_flag.set()
                break
            elif cmd == "EXIT":
                print("\n[EXIT received — shutting down]")
                stop_flag.set()
                exit_flag.set()
                break
            elif cmd == "TESTMACRO":
                threading.Thread(target=run_test_macro, args=(cap,), daemon=True).start()
            else:
                handle_command(ser, cmd)
        except:
            break

def wait_for_startmacro(ser, cap):
    """Drop back to a prompt after STOPMACRO. Returns False if EXIT was typed."""
    print("\n[Stopped — type STARTMACRO to run again, EXIT to quit]")
    while True:
        try:
            cmd = input("> ").strip().upper()
        except:
            return False
        if cmd == "STARTMACRO":
            print(f"Hunt restarted — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            return True
        elif cmd == "EXIT":
            print("[EXIT received — shutting down]")
            exit_flag.set()
            return False
        elif cmd == "TESTMACRO":
            threading.Thread(target=run_test_macro, args=(cap,), daemon=True).start()
        else:
            handle_command(ser, cmd)

def main():
    global cap_global
    logger = setup_logging()

    print(f"Hunt started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Opening {COM_PORT}...")
    ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
    print("Serial open.")

    capture_index = CAPTURE_INDEX
    if capture_index is None:
        capture_index = find_capture_index()
        if capture_index is None:
            print("ERROR: Could not find any capture device.")
            print("Make sure OBS Virtual Camera is running and try again.")
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
        print("Make sure OBS Virtual Camera is running and try again.")
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

    if OBS_AVAILABLE:
        try:
            cl = obs.ReqClient(host=OBS_HOST, port=OBS_PORT, password=OBS_PASSWORD, timeout=3)
            print("OBS WebSocket connected.")
        except Exception as e:
            print(f"[WARNING] Could not connect to OBS WebSocket: {e}")
            print("[WARNING] Replay buffer will NOT be saved on shiny detection.")
    else:
        print("[WARNING] obsws-python not installed. OBS replay save disabled.")

    print("\nCommands: A B X Y UP DOWN LEFT RIGHT HOME STOP ABXY")
    print("Type STARTMACRO to begin the hunt, STOPMACRO to stop, EXIT to quit.")
    print("Type TESTMACRO to test detection on the current screen.\n")

    while True:
        try:
            cmd = input("> ")
        except:
            break
        cmd = cmd.strip().upper()
        if cmd == "STARTMACRO":
            print(f"Hunt started — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            break
        elif cmd == "EXIT":
            print("[EXIT received — shutting down]")
            exit_flag.set()
            ser.close()
            sys.stdout = logger.terminal
            logger.close()
            return
        elif cmd == "TESTMACRO":
            run_test_macro(cap)
        else:
            handle_command(ser, cmd)

    attempt = 0

    try:
        while not exit_flag.is_set():
            stop_flag.clear()

            stop_thread = threading.Thread(target=listen_for_commands, args=(ser, cap), daemon=True)
            stop_thread.start()

            while not stop_flag.is_set() and not exit_flag.is_set():
                attempt += 1
                loop_start = time.time()
                print(f"\n── Attempt {attempt} — {datetime.now().strftime('%H:%M:%S')} ──────────────────")

                run_reset_sequence(ser, first_run=(attempt == 1))

                if stop_flag.is_set() or exit_flag.is_set():
                    break

                interruptible_sleep(0.5)

                # ── First detection check ──────────────────────────────────
                print("  [CHECK 1 — grabbing frame]")
                frame = grab_frame(cap)
                if frame is None:
                    print("WARNING: Check 1 frame grab failed. Skipping to reset.")
                    soft_reset(ser)
                    elapsed = time.time() - loop_start
                    print(f"  [loop time: {elapsed:.1f}s]")
                    continue

                is_shiny, pixel_count, region, mask = detect_shiny_star(frame)
                print(f"  [CHECK 1 — yellow pixels: {pixel_count} | threshold: {STAR_PIXEL_THRESHOLD}] -> {'SHINY!' if is_shiny else 'not shiny'}")

                debug_mask = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
                combined = np.hstack([region, debug_mask])
                cv2.imshow("Detection Region | Mask", combined)
                cv2.waitKey(1)

                if is_shiny:
                    elapsed = time.time() - loop_start
                    print(f"  [loop time: {elapsed:.1f}s]")
                    run_shiny_sequence(ser)
                    stop_flag.set()
                    break

                # ── Countdown then second detection check ──────────────────
                aborted = pre_reset_countdown()
                if aborted:
                    elapsed = time.time() - loop_start
                    print(f"  [loop time: {elapsed:.1f}s]")
                    break

                print("  [CHECK 2 — grabbing frame]")
                frame2 = grab_frame(cap)
                if frame2 is None:
                    print("WARNING: Check 2 frame grab failed. Proceeding to reset.")
                    soft_reset(ser)
                    elapsed = time.time() - loop_start
                    print(f"  [loop time: {elapsed:.1f}s]")
                    continue

                is_shiny2, pixel_count2, region2, mask2 = detect_shiny_star(frame2)
                print(f"  [CHECK 2 — yellow pixels: {pixel_count2} | threshold: {STAR_PIXEL_THRESHOLD}] -> {'SHINY!' if is_shiny2 else 'not shiny'}")

                debug_mask2 = cv2.cvtColor(mask2, cv2.COLOR_GRAY2BGR)
                combined2 = np.hstack([region2, debug_mask2])
                cv2.imshow("Detection Region | Mask", combined2)
                cv2.waitKey(1)

                if is_shiny2:
                    elapsed = time.time() - loop_start
                    print(f"  [loop time: {elapsed:.1f}s]")
                    run_shiny_sequence(ser)
                    stop_flag.set()
                    break
                else:
                    soft_reset(ser)
                    elapsed = time.time() - loop_start
                    print(f"  [loop time: {elapsed:.1f}s]")

            stop_thread.join(timeout=0.5)

            if exit_flag.is_set():
                break

            # STOPMACRO was hit — wait for STARTMACRO or EXIT
            should_continue = wait_for_startmacro(ser, cap)
            if not should_continue:
                break

    except KeyboardInterrupt:
        print("\nStopped by keyboard.")

    finally:
        send(ser, "STOP")
        cap.release()
        cv2.destroyAllWindows()
        ser.close()
        print(f"\nHunt ended after {attempt} attempts at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Log saved to: {logger.log_path}")
        sys.stdout = logger.terminal
        logger.close()

if __name__ == "__main__":
    main()
