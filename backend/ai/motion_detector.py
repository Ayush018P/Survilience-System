"""
NeuroGuard AI - Motion Detection
================================
Lightweight motion detection using frame differencing to avoid running
heavy neural networks on empty frames.
"""

import cv2
import numpy as np


class MotionDetector:
    def __init__(self, threshold=25, min_area=500):
        """
        Args:
            threshold: Pixel intensity difference threshold to be considered motion.
            min_area: Minimum bounding box area of motion to trigger detection.
        """
        self.threshold = threshold
        self.min_area = min_area
        self.previous_frame = None

    def detect(self, current_frame_rgb: np.ndarray) -> bool:
        """
        Detects if significant motion has occurred compared to the previous frame.
        
        Args:
            current_frame_rgb: The current frame as a numpy array in RGB format.
            
        Returns:
            bool: True if motion detected, False otherwise.
        """
        # Convert to grayscale for simple differencing
        gray = cv2.cvtColor(current_frame_rgb, cv2.COLOR_RGB2GRAY)
        
        # Apply Gaussian blur to reduce noise and false positives
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if self.previous_frame is None:
            self.previous_frame = gray
            return True  # Always process the first frame

        # Compute absolute difference between current frame and previous frame
        frame_delta = cv2.absdiff(self.previous_frame, gray)
        
        # Threshold the delta
        thresh = cv2.threshold(frame_delta, self.threshold, 255, cv2.THRESH_BINARY)[1]
        
        # Dilate the threshold image to fill in holes
        thresh = cv2.dilate(thresh, None, iterations=2)
        
        # Find contours on thresholded image
        contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        motion_detected = False
        for c in contours:
            if cv2.contourArea(c) > self.min_area:
                motion_detected = True
                break

        # Update previous frame
        self.previous_frame = gray
        
        return motion_detected
