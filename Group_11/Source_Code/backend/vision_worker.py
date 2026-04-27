import time
import cv2
from ultralytics import YOLO
from object_tracker.tracker import Tracker  # Your existing tracker module

from frame_buffer import FrameBuffer
from output_buffer import ProcessedFrameBuffer
from vlm_buffer import VLMFrameBuffer

import sys
import os

# Add object_tracker repo to path
# sys.path.insert(0, os.path.join(os.path.dirname(__file__), "object_tracker"))

class VisionWorker:
    def __init__(
        self,
        frame_buffer: FrameBuffer,
        output_buffer: ProcessedFrameBuffer,
        vlm_buffer: VLMFrameBuffer,
        target_fps: int = 10,
    ):
        self.frame_buffer = frame_buffer
        self.output_buffer = output_buffer
        self.vlm_buffer = vlm_buffer
        self.model = YOLO("yolov8n.pt")
        self.tracker = Tracker()
        self.frame_interval = 1.0 / target_fps
        self.last_run = 0
        self.last_processed_frame = 0

        # Colors for drawing different track IDs
        self.colors = [
            (255, 0, 0),
            (0, 255, 0),
            (0, 0, 255),
            (255, 255, 0),
            (255, 165, 0),
            (255, 0, 255),
            (0, 255, 255),
        ]

    def run(self):
        while True:
            now = time.time()

            if now - self.last_run < self.frame_interval:
                time.sleep(0.01)
                continue

            data = self.frame_buffer.get_latest_frame()
            if data is None:
                continue

            timestamp, frame = data
            self.last_run = now

            if self.last_processed_frame == timestamp:
                continue

            self.last_processed_frame = timestamp
            results = self.model(frame, verbose=False)

            detections = []
            for r in results:
                for box in r.boxes.data.tolist():
                    x1, y1, x2, y2, conf, cls = box
                    if int(cls) == 0 and conf > 0.35:
                        x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])
                        detections.append([x1, y1, x2, y2, conf])

            # Update tracker with current frame detections
            self.tracker.update(frame, detections)

            # Draw tracked boxes with IDs
            for track in self.tracker.tracks:
                x1, y1, x2, y2 = track.bbox
                track_id = track.track_id
                color = self.colors[track_id % len(self.colors)]

                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                cv2.putText(
                    frame,
                    f"ID: {track_id}",
                    (int(x1), int(y1) - 8),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    color,
                    2,
                )

            # Encode frame and send to output buffer
            success, encoded = cv2.imencode(
                ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70]
            )
            if success:
                self.output_buffer.add(encoded.tobytes(), timestamp)

                last_vlm_frame_timestamp = self.vlm_buffer.get_latest_timestamp() or 0

            if (success) and (len(detections) != 0) and (now - last_vlm_frame_timestamp > 5):
                self.vlm_buffer.add(encoded.tobytes(), timestamp)
