import time
import threading
from collections import deque
from typing import Deque, Tuple
import numpy as np
import cv2


class FrameBuffer:
    """
    Time-based bounded frame buffer.
    Stores compressed frames to avoid memory blowup.
    """

    def __init__(self, max_seconds: int = 20, target_fps: int = 10):
        self.max_frames = max_seconds * target_fps
        self.buffer: Deque[Tuple[float, bytes]] = deque(maxlen=self.max_frames)
        self.lock = threading.Lock()

    def add_frame(self, frame: np.ndarray, timestamp: float):
        """
        Compress and store frame with timestamp.
        """
        # Resize to keep memory low (IMPORTANT)
        frame = cv2.resize(frame, (640, 360))

        # JPEG compress
        success, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        if not success:
            return

        with self.lock:
            self.buffer.append((timestamp, encoded.tobytes()))

    def get_latest_frame(self):
        """
        Returns the most recent frame (decoded).
        """
        with self.lock:
            if not self.buffer:
                return None
            timestamp, frame_bytes = self.buffer[-1]

        frame = cv2.imdecode(
            np.frombuffer(frame_bytes, np.uint8),
            cv2.IMREAD_COLOR
        )
        return timestamp, frame

    def get_frames_between(self, start_time: float, end_time: float):
        """
        Returns decoded frames within a time window.
        """
        frames = []

        with self.lock:
            relevant = [
                (ts, fb) for ts, fb in self.buffer
                if start_time <= ts <= end_time
            ]

        for ts, frame_bytes in relevant:
            frame = cv2.imdecode(
                np.frombuffer(frame_bytes, np.uint8),
                cv2.IMREAD_COLOR
            )
            frames.append((ts, frame))

        return frames
