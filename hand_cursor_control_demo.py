import cv2
import numpy as np
import time
import os
import platform

# Use the stable public mediapipe API (avoid direct submodule imports to prevent ModuleNotFoundError)
import mediapipe as mp

# Prefer the stable, public API. Some language servers flag attributes; ignore type for editor only.
# mypy: ignore-errors
# pyright: reportAttributeAccessIssue=false
# pylance: disable=reportAttributeAccessIssue
mp_hands_mod = mp.solutions.hands  # type: ignore[attr-defined]
mp_drawing = mp.solutions.drawing_utils  # type: ignore[attr-defined]
mp_drawing_styles = mp.solutions.drawing_styles  # type: ignore[attr-defined]

# Handy aliases
HandLandmark = mp_hands_mod.HandLandmark
HAND_CONNECTIONS = mp_hands_mod.HAND_CONNECTIONS

# --- Robustly detect and import GUI control libraries ---

PREFERRED_BACKEND = os.environ.get("MOUSE_BACKEND", "").lower()  # "pyautogui" | "pynput" | ""

# 1) Try to import pyautogui (X11/XWayland)
def try_import_pyautogui():
    try:
        if os.environ.get("PYAUTOGUI_HEADLESS", "0") in ("1", "true", "True"):
            return None, False
        if os.name == "posix" and not os.environ.get("DISPLAY"):
            return None, False
        import pyautogui
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0
        pyautogui.size()
        return pyautogui, True
    except Exception:
        return None, False

pyautogui, PYAUTOGUI_AVAILABLE = try_import_pyautogui()

# 2) Fallback to pynput (often works better under Wayland)
def try_import_pynput():
    try:
        from pynput.mouse import Controller, Button
        _ = Controller()  # probe
        return Controller, Button, True
    except Exception:
        return None, None, False

MouseController, MouseButton, PYNPUT_AVAILABLE = try_import_pynput()

# Prefer pynput on Linux if both available, unless overridden
using_linux = (platform.system().lower() == "linux")
if PYNPUT_AVAILABLE and (PREFERRED_BACKEND == "pynput" or (PREFERRED_BACKEND == "" and using_linux)):
    ACTIVE_BACKEND = "pynput"
elif PYAUTOGUI_AVAILABLE and (PREFERRED_BACKEND == "pyautogui" or PREFERRED_BACKEND == "" or not PYNPUT_AVAILABLE):
    ACTIVE_BACKEND = "pyautogui"
elif PYNPUT_AVAILABLE:
    ACTIVE_BACKEND = "pynput"
else:
    ACTIVE_BACKEND = "none"

if ACTIVE_BACKEND == "none":
    print("No GUI mouse backend available. Running in simulation mode (no real mouse control).")
else:
    print(f"Using '{ACTIVE_BACKEND}' backend for mouse control.")

# --- Get Screen Size ---
if ACTIVE_BACKEND == "pyautogui" and pyautogui is not None:
    screen_width, screen_height = pyautogui.size()
else:
    screen_width, screen_height = 1920, 1080  # fallback
    if ACTIVE_BACKEND == "pynput":
        print("pynput does not provide screen size. Using default 1920x1080.")

# --- Initialize Webcam and Mediapipe Hands ---
cap = cv2.VideoCapture(0)
# Lower camera resolution to reduce pipeline cost (adjust if your camera supports it)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)

# Tunables
proc_scale = float(os.environ.get("PROC_SCALE", "0.75"))  # downscale for processing (0.5-1.0)
draw_overlays = os.environ.get("DRAW_OVERLAYS", "1") in ("1", "true", "True")
deadzone_px = int(os.environ.get("MOVE_DEADZONE_PX", "2"))  # ignore tiny jitter
max_update_hz = float(os.environ.get("MAX_UPDATE_HZ", "120"))  # rate limit cursor updates
base_alpha = float(os.environ.get("SMOOTH_ALPHA", "0.25"))  # EMA smoothing (0..1), higher=snappier
accel_gain = float(os.environ.get("ACCEL_GAIN", "0.35"))  # add velocity boost for faster moves

last_move_time = 0.0
min_move_dt = 1.0 / max_update_hz if max_update_hz > 0 else 0.0

# Configure hand detection
with mp_hands_mod.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.5
) as hands:

    # --- Variables for Cursor Control and Gesture Detection ---
    prev_x, prev_y = 0, 0
    vel_x, vel_y = 0.0, 0.0

    last_click_time = 0.0
    click_cooldown = 0.35  # slightly shorter

    mouse_controller = None  # lazy-init for pynput

    while cap.isOpened():
        success, image = cap.read()
        if not success:
            print("Ignoring empty camera frame.")
            continue

        # Flip for natural selfie view
        image = cv2.flip(image, 1)
        image_h, image_w, _ = image.shape

        # Downscale for processing to speed up Mediapipe
        if 0.2 <= proc_scale < 1.0:
            proc_image = cv2.resize(image, (int(image_w * proc_scale), int(image_h * proc_scale)), interpolation=cv2.INTER_LINEAR)
        else:
            proc_image = image

        # Optimize for Mediapipe: mark not writeable and use RGB
        proc_image.flags.writeable = False
        image_rgb = cv2.cvtColor(proc_image, cv2.COLOR_BGR2RGB)

        # Process the image and detect hands
        results = hands.process(image_rgb)

        # Prepare display image (use original-sized image)
        disp_image = image

        if results.multi_hand_landmarks:
            # We only use the first detected hand for cursor
            hand_landmarks = results.multi_hand_landmarks[0]

            if draw_overlays:
                # Draw landmarks on display image (not the downscaled one)
                mp_drawing.draw_landmarks(
                    disp_image,
                    hand_landmarks,
                    HAND_CONNECTIONS,
                    mp_drawing_styles.get_default_hand_landmarks_style(),
                    mp_drawing_styles.get_default_hand_connections_style()
                )

            # Get landmarks from the results produced on the scaled image.
            landmarks = hand_landmarks.landmark
            index_tip = landmarks[HandLandmark.INDEX_FINGER_TIP]
            thumb_tip = landmarks[HandLandmark.THUMB_TIP]

            # Because Mediapipe returns normalized coords, scaling doesn't affect mapping.
            target_x = int(index_tip.x * screen_width)
            target_y = int(index_tip.y * screen_height)

            # Adaptive smoothing: EMA + velocity boost
            dx = target_x - prev_x
            dy = target_y - prev_y
            speed = np.hypot(dx, dy)

            # Increase responsiveness when moving faster
            alpha = min(1.0, base_alpha + accel_gain * (speed / max(screen_width, screen_height)))
            cursor_x = int(prev_x + alpha * dx)
            cursor_y = int(prev_y + alpha * dy)

            # Deadzone to skip tiny jitter updates
            if abs(cursor_x - prev_x) >= deadzone_px or abs(cursor_y - prev_y) >= deadzone_px:
                now = time.time()
                if min_move_dt == 0.0 or (now - last_move_time) >= min_move_dt:
                    if ACTIVE_BACKEND == "pyautogui" and pyautogui is not None:
                        try:
                            pyautogui.moveTo(cursor_x, cursor_y)
                        except Exception as e:
                            print(f"[BACKEND FALLBACK] pyautogui move failed: {e}")
                    elif ACTIVE_BACKEND == "pynput" and MouseController is not None:
                        try:
                            if mouse_controller is None:
                                mouse_controller = MouseController()
                            mouse_controller.position = (cursor_x, cursor_y)
                        except Exception as e:
                            print(f"[SIM FALLBACK] pynput move failed: {e}")
                    else:
                        # Simulation mode: print at ~10 Hz
                        if int(now * 10) % 10 == 0:
                            print(f"[SIM] Move -> ({cursor_x}, {cursor_y})")
                    last_move_time = now

            prev_x, prev_y = cursor_x, cursor_y

            # Click Detection (pinch)
            distance = np.hypot(thumb_tip.x - index_tip.x, thumb_tip.y - index_tip.y)
            current_time = time.time()
            if distance < 0.04 and (current_time - last_click_time) > click_cooldown:
                if ACTIVE_BACKEND == "pyautogui" and pyautogui is not None:
                    try:
                        pyautogui.click()
                    except Exception as e:
                        print(f"[BACKEND FALLBACK] pyautogui click failed: {e}")
                elif ACTIVE_BACKEND == "pynput" and MouseController is not None:
                    try:
                        if mouse_controller is None:
                            mouse_controller = MouseController()
                        if 'MouseButton' not in globals() or MouseButton is None:
                            from pynput.mouse import Button as MouseButton  # type: ignore
                        mouse_controller.click(MouseButton.left, 1)
                    except Exception as e:
                        print(f"[SIM FALLBACK] pynput click failed: {e}")
                else:
                    print("[SIM] Click")
                last_click_time = current_time
                if draw_overlays:
                    cv2.putText(disp_image, "CLICK!", (50, 50),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)

            if draw_overlays:
                cv2.putText(disp_image, f"Cursor(screen): ({prev_x}, {prev_y})", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                cv2.putText(disp_image, f"PinchDist(norm): {distance:.3f}", (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Show at lower wait time to reduce blocking
        cv2.imshow('Hand Cursor Control', disp_image)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

# --- Cleanup ---
cap.release()
cv2.destroyAllWindows()