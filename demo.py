import cv2
import numpy as np

# Create a simple image (black square)
img = np.zeros((300, 300, 3), dtype=np.uint8)

# Draw a red circle in the center
cv2.circle(img, (150, 150), 100, (0, 0, 255), -1)

# Add text
cv2.putText(img, 'OpenCV Demo', (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

# Save the image
cv2.imwrite('demo_output.png', img)

print("Demo image created: demo_output.png")
print("OpenCV version:", cv2.__version__)