import cv2
import mediapipe as mp
import numpy as np

# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# Initialize webcam
cap = cv2.VideoCapture(0)

# Configure hand detection
with mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5) as hands:

    while cap.isOpened():
        success, image = cap.read()
        if not success:
            print("Ignoring empty camera frame.")
            continue

        # Flip the image horizontally for a selfie-view display
        image = cv2.flip(image, 1)

        # Convert the BGR image to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Process the image and detect hands
        results = hands.process(image_rgb)

        # Draw hand landmarks
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(
                    image,
                    hand_landmarks,
                    mp_hands.HAND_CONNECTIONS,
                    mp_drawing_styles.get_default_hand_landmarks_style(),
                    mp_drawing_styles.get_default_hand_connections_style())

                # Get finger positions for gesture recognition
                landmarks = hand_landmarks.landmark

                # Thumb
                thumb_tip = landmarks[mp_hands.HandLandmark.THUMB_TIP]
                thumb_ip = landmarks[mp_hands.HandLandmark.THUMB_IP]

                # Index finger
                index_tip = landmarks[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                index_dip = landmarks[mp_hands.HandLandmark.INDEX_FINGER_DIP]

                # Middle finger
                middle_tip = landmarks[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
                middle_dip = landmarks[mp_hands.HandLandmark.MIDDLE_FINGER_DIP]

                # Ring finger
                ring_tip = landmarks[mp_hands.HandLandmark.RING_FINGER_TIP]
                ring_dip = landmarks[mp_hands.HandLandmark.RING_FINGER_DIP]

                # Pinky
                pinky_tip = landmarks[mp_hands.HandLandmark.PINKY_TIP]
                pinky_pip = landmarks[mp_hands.HandLandmark.PINKY_PIP]

                # Simple gesture detection
                fingers_up = []

                # Check if fingers are extended (tip higher than DIP joint)
                fingers_up.append(thumb_tip.x > thumb_ip.x)  # Thumb (horizontal check)
                fingers_up.append(index_tip.y < index_dip.y)
                fingers_up.append(middle_tip.y < middle_dip.y)
                fingers_up.append(ring_tip.y < ring_dip.y)
                fingers_up.append(pinky_tip.y < pinky_pip.y)

                # Determine gesture
                if fingers_up == [False, False, False, False, False]:
                    gesture = "Fist"
                elif fingers_up == [True, True, True, True, True]:
                    gesture = "Open Hand"
                elif fingers_up == [False, True, False, False, False]:
                    gesture = "Pointing"
                elif fingers_up == [True, True, False, False, False]:
                    gesture = "Peace Sign"
                elif fingers_up == [False, True, True, False, False]:
                    gesture = "Two Fingers"
                else:
                    gesture = "Unknown"

                # Display gesture
                cv2.putText(image, f"Gesture: {gesture}", (10, 50),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

       
        cv2.imshow('Hand Gesture Detection', image)

        if cv2.waitKey(5) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()