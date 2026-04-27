import threading
from collections import deque
from typing import Optional, Tuple


class VLMFrameBuffer:
    def __init__(self, max_frames: int = 20):
        self.buffer = deque(maxlen=max_frames)
        self.lock = threading.Lock()

    def add(self, frame_bytes: bytes, timestamp: float):
        with self.lock:
            self.buffer.append((timestamp, frame_bytes))

    def get_latest_timestamp(self):
        with self.lock:
            if not self.buffer:
                return None
            return self.buffer[-1][0]

    def pop(self):
        with self.lock:
            if not self.buffer:
                return None
            return self.buffer.popleft()

    def size(self):
        with self.lock:
            return len(self.buffer)

    def is_empty(self):
        with self.lock:
            return len(self.buffer) == 0
        
    def get_full_buffer(self):
        with self.lock:
            return [frame_bytes for _, frame_bytes in self.buffer]