#!/usr/bin/env python3
"""
Quickstart demo for PyAutoGUI mouse and keyboard controls.

This script:
- Prints screen size and current mouse position
- Moves the mouse to a few points with animation
- Performs left/right/double clicks
- Drags the mouse in a small square
- Scrolls up and down
- Types some text and uses hotkeys
- Shows simple alert/confirm/prompt message boxes
- Optionally performs image-based locateOnScreen demo (disabled by default)

Notes:
- On Linux, screenshot features may require: sudo apt-get install scrot
- If running on Wayland and cursor doesn't move, try X11/XWayland session
- Fail-safe: moving mouse to top-left throws PyAutoGUI FailSafeException
"""

import time
import sys
import os

try:
    import pyautogui
except Exception as e:
    print("Failed to import pyautogui:", e)
    sys.exit(1)

def main():
    # Global behavior
    pyautogui.PAUSE = 0.5          # pause after each call
    pyautogui.FAILSAFE = True       # move mouse to top-left to abort

    # Basic info
    print("Screen size:", pyautogui.size())
    print("Initial mouse position:", pyautogui.position())
    print("onScreen(10,10):", pyautogui.onScreen(10, 10))

    # Move examples
    w, h = pyautogui.size()
    path_points = [
        (w//2, h//2),
        (w//2 + 100, h//2),
        (w//2 + 100, h//2 + 100),
        (w//2, h//2 + 100),
        (w//2, h//2),
    ]
    print("Moving to points:", path_points)
    for x, y in path_points:
        pyautogui.moveTo(x, y, duration=0.5)

    # Relative move
    print("Relative move by (+50, -30)")
    pyautogui.moveRel(50, -30, duration=0.4)

    # Clicks
    print("Single left click at current position")
    pyautogui.click()
    print("Right click")
    pyautogui.rightClick()
    print("Double click")
    pyautogui.doubleClick()

    # Drag demo (small square)
    start = pyautogui.position()
    print("Drag starting at:", start)
    pyautogui.dragRel(60, 0, duration=0.4, button='left')
    pyautogui.dragRel(0, 60, duration=0.4, button='left')
    pyautogui.dragRel(-60, 0, duration=0.4, button='left')
    pyautogui.dragRel(0, -60, duration=0.4, button='left')

    # Scroll
    print("Scroll up 500")
    pyautogui.scroll(500)
    print("Scroll down 500")
    pyautogui.scroll(-500)

    # Keyboard typing
    print("Typing demo in 2 seconds... (focus a text field now)")
    time.sleep(2)
    pyautogui.typewrite('Hello world!\n', interval=0.05)
    pyautogui.typewrite(['H', 'e', 'l', 'l', 'o', 'space', 'b', 'a', 'c', 'k', 'space', 't', 'o', 'space', 'y', 'o', 'u', 'enter'], interval=0.05)

    # Hotkeys
    # Example: select-all then copy (Ctrl+A, Ctrl+C) - adjust based on your focused app
    print("Sending hotkeys: Ctrl+A, then Ctrl+C")
    pyautogui.hotkey('ctrl', 'a')
    pyautogui.hotkey('ctrl', 'c')

    # Message boxes (uncomment to use interactively)
    try:
        # alert_result = pyautogui.alert('This displays some text with an OK button.')
        # print("alert returned:", alert_result)

        # confirm_result = pyautogui.confirm('This displays text and has an OK and Cancel button.')
        # print("confirm returned:", confirm_result)

        # prompt_result = pyautogui.prompt('This lets the user type in a string and press OK.')
        # print("prompt returned:", prompt_result)
        pass
    except Exception as e:
        print("Message box functions not available in this environment:", e)

    # Screenshot and image search (optional)
    # On Linux, may require: sudo apt-get install scrot
    try:
        # Save a screenshot
        shot_path = os.path.join(os.getcwd(), 'quickstart_screenshot.png')
        print(f"Taking screenshot to {shot_path}")
        img = pyautogui.screenshot()
        img.save(shot_path)

        # Example of locateOnScreen (disabled by default; provide your own image to search)
        # target = 'looksLikeThis.png'
        # if os.path.exists(target):
        #     print(f"Searching for {target} on screen...")
        #     box = pyautogui.locateOnScreen(target)
        #     print("locateOnScreen returned:", box)
        #     if box:
        #         center = pyautogui.center(box)
        #         print("Center:", center)
        #         pyautogui.moveTo(center.x, center.y, duration=0.5)
        # else:
        #     print(f"Provide an image file (e.g., {target}) to demo locateOnScreen.")
        pass
    except Exception as e:
        print("Screenshot/locateOnScreen features unavailable:", e)

    print("Demo complete.")

if __name__ == "__main__":
    try:
        main()
    except pyautogui.FailSafeException:
        print("PyAutoGUI FailSafe triggered (mouse moved to top-left). Aborting safely.")