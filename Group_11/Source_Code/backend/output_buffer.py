import threading
from collections import deque
import time


class ProcessedFrameBuffer:
    def __init__(self, max_frames: int = 10):
        self.buffer = deque(maxlen=max_frames)
        self.lock = threading.Lock()

    def add(self, frame_bytes: bytes, timestamp: float):
        with self.lock:
            self.buffer.append((timestamp, frame_bytes))

    def get_latest(self):
        with self.lock:
            if not self.buffer:
                return None
            return self.buffer[-1]
        
    def get_n_evenly_spaced(self, n: int = 3):
        with self.lock:
            total = len(self.buffer)
            if total == 0:
                return []
            if total <= n:
                return [frame_bytes for _, frame_bytes in self.buffer]

            # calculate evenly spaced indices
            indices = [int(i * (total - 1) / (n - 1)) for i in range(n)]
            return [self.buffer[0][1], self.buffer[total//2][1], self.buffer[-1][1]]
