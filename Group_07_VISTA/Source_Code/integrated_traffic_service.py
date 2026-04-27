import cv2
import time
import torch
import numpy as np
from ultralytics import YOLO
from threading import Thread, Lock
from queue import Queue
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntegratedTrafficDetector:
    """
    Integrated traffic detection service that combines the functionality 
    of test_both2.py with Flask app requirements
    """
    
    def __init__(self):
        # Video configuration
        self.VIDEO_PATHS = [
            r"videos/v1.mp4",
            r"videos/v2.mp4", 
            r"videos/v3.mp4",
            r"videos/v4.mp4"
        ]
        self.RESIZE_WIDTH = 256
        self.RESIZE_HEIGHT = 144
        self.FRAME_SKIP = 4
        self.MODEL_PATH = "yolo11n.pt"
        self.AMBULANCE_MODEL_PATH = r"best.pt"
        self.VEHICLE_CLASSES = [1, 2, 3, 5, 6, 7]
        self.AMBULANCE_CONFIDENCE = 0.7
        self.QUEUE_SIZE = 60
        self.INFERENCE_INTERVAL = 4
        self.FPS_TARGET = 30
        
        # Scale factor for new resolution
        self.SCALE_X = self.RESIZE_WIDTH / 320
        self.SCALE_Y = self.RESIZE_HEIGHT / 180
        
        # Define lanes (scaled and precomputed)
        self.LANES_ORIGINAL = [
            [  # Video 1 (North)
                [(88, 7), (99, 5), (101, 48), (85, 93), (56, 143), (37, 177), (1, 150), (27, 113), (57, 81), (69, 60), (85, 13)],
                [(95, 9), (108, 7), (113, 21), (121, 41), (129, 67), (128, 93), (121, 133), (119, 163), (107, 177), (44, 177),
                 (87, 94), (101, 56), (99, 9)],
                [(110, 9), (127, 7), (149, 23), (176, 58), (193, 85), (210, 153), (213, 173), (128, 172), (129, 96), (132, 68),
                 (122, 37), (112, 13)]
            ],
            [  # Video 2 (South)
                [(202, 2), (214, 2), (203, 22), (186, 50), (182, 89), (194, 178), (131, 177), (131, 102), (145, 56), (168, 29), (195, 4)],
                [(213, 1), (219, 2), (219, 25), (218, 54), (229, 85), (250, 122), (281, 176), (209, 178), (196, 103), (197, 41),
                 (206, 17), (213, 4)],
                [(220, 4), (237, 3), (251, 62), (287, 103), (315, 144), (317, 178), (286, 178), (238, 98), (221, 38), (221, 9)]
            ],
            [  # Video 3 (East)
                [(111, 76), (139, 69), (153, 76), (148, 93), (133, 114), (117, 141), (106, 167), (97, 178), (10, 173), (50, 137),
                 (82, 105), (109, 80)],
                [(139, 81), (161, 80), (173, 89), (176, 111), (176, 131), (179, 154), (179, 176), (107, 176), (125, 129), (141, 103),
                 (150, 82)],
                [(173, 89), (194, 92), (223, 102), (240, 127), (256, 147), (272, 173), (184, 175), (181, 138), (175, 92)]
            ],
            [  # Video 4 (West)
                [(117, 4), (161, 2), (76, 164), (0, 134), (109, 5)],
                [(161, 4), (203, 2), (186, 171), (79, 167), (160, 5)],
                [(202, 4), (254, 2), (316, 167), (190, 176), (203, 9)]
            ]
        ]
        
        self.LANES = self._scale_lanes(self.LANES_ORIGINAL)
        
        # Direction mapping for Flask app compatibility
        self.DIRS = ["North", "South", "East", "West"]
        self.ABBR = {"North":"N","South":"S","East":"E","West":"W"}
        
        # State variables
        self.device = None
        self.model = None
        self.model_ambulance = None
        self.use_half = False
        self.readers = []
        self.inference_processor = None
        self.current_frames = [None, None, None, None]
        self.latest_results = None
        self.latest_ambulance_results = None
        self.is_running = False
        self.is_initialized = False
        self.frame_lock = Lock()
        self.results_lock = Lock()
        
        # Traffic counting state
        self.latest_traffic_counts = {
            'frame_counts': [0]*4,
            'lane_counts': [[0,0,0] for _ in range(4)],
            'ambulance_counts': [0]*4,
            'ambulance_lane_counts': [[0,0,0] for _ in range(4)]
        }
        
    def _scale_lanes(self, lanes_original):
        """Scale lanes to current resolution"""
        scaled = []
        for video_lanes in lanes_original:
            video_scaled = []
            for lane in video_lanes:
                scaled_lane = [(int(x * self.SCALE_X), int(y * self.SCALE_Y)) for x, y in lane]
                video_scaled.append(np.array(scaled_lane, np.int32))
            scaled.append(video_scaled)
        return scaled
    
    def initialize(self):
        """Initialize the detection system"""
        try:
            logger.info("Initializing Integrated Traffic Detection System...")
            
            # Setup device
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Using device: {self.device}")
            
            # Load models
            logger.info("Loading YOLO models...")
            self.model = YOLO(self.MODEL_PATH)
            self.model_ambulance = YOLO(self.AMBULANCE_MODEL_PATH)
            
            # Move models to device
            self.model.to(self.device)
            self.model_ambulance.to(self.device)
            
            # Enable optimizations for CUDA
            self.use_half = False
            if self.device == "cuda":
                try:
                    torch.cuda.is_available() and torch.cuda.get_device_capability()[0] >= 7
                    self.use_half = True
                    logger.info("FP16 (Half precision) will be used during inference")
                except:
                    self.use_half = False
                    logger.info("Using FP32 precision")
            else:
                logger.info("Using FP32 precision on CPU")
            
            # Warm up models
            logger.info("Warming up models...")
            dummy = np.zeros((self.RESIZE_HEIGHT, self.RESIZE_WIDTH, 3), dtype=np.uint8)
            with torch.no_grad():
                self.model.predict(dummy, classes=self.VEHICLE_CLASSES, device=self.device, verbose=False, half=self.use_half)
                self.model_ambulance.predict(dummy, device=self.device, verbose=False, half=self.use_half)
            logger.info("Models ready!")
            
            self.is_initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            return False
    
    def start(self):
        """Start the detection system"""
        if not self.is_initialized:
            if not self.initialize():
                return False
        
        try:
            logger.info("Starting video streams...")
            
            # Start video readers
            self.readers = [VideoReader(path, self.RESIZE_WIDTH, self.RESIZE_HEIGHT, i).start() 
                           for i, path in enumerate(self.VIDEO_PATHS)]
            time.sleep(1.5)  # Buffer time
            
            # Start inference processor
            logger.info("Starting inference processor...")
            self.inference_processor = InferenceProcessor(
                self.model, self.model_ambulance, self.device, self.use_half
            ).start()
            
            # Start main processing loop
            self.is_running = True
            self.processing_thread = Thread(target=self._processing_loop, daemon=True)
            self.processing_thread.start()
            
            time.sleep(0.5)
            logger.info("Traffic detection system started successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start: {e}")
            self.stop()
            return False
    
    def _processing_loop(self):
        """Main processing loop (runs in background thread)"""
        frame_counter = 0
        last_inference_time = 0
        
        while self.is_running:
            try:
                if not self.readers:
                    time.sleep(0.1)
                    continue
                
                # Read frames from all cameras
                frames = []
                for reader in self.readers:
                    try:
                        frame = reader.read()
                        frames.append(frame)
                    except:
                        # Create dummy frame if video reader fails
                        dummy_frame = np.zeros((self.RESIZE_HEIGHT, self.RESIZE_WIDTH, 3), dtype=np.uint8)
                        frames.append(dummy_frame)
                
                # Update current frames for streaming
                with self.frame_lock:
                    self.current_frames = [f.copy() for f in frames]
                
                frame_counter += 1
                
                # Submit frames for inference at intervals
                if frame_counter % self.INFERENCE_INTERVAL == 0:
                    current_time = time.time()
                    if current_time - last_inference_time >= 0.1:  # Throttle submissions
                        if self.inference_processor and self.inference_processor.submit([f.copy() for f in frames]):
                            last_inference_time = current_time
                
                # Get latest inference results
                if self.inference_processor:
                    inference_results = self.inference_processor.get_results()
                    if inference_results is not None:
                        results, results_ambulance = inference_results
                        
                        # Process detections
                        counts = self._process_detections_fast(results, results_ambulance)
                        
                        with self.results_lock:
                            self.latest_results = results
                            self.latest_ambulance_results = results_ambulance
                            self.latest_traffic_counts = counts
                
                time.sleep(1.0 / self.FPS_TARGET)  # Frame rate control
                
            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                time.sleep(0.1)
    
    def _process_detections_fast(self, results, results_ambulance):
        """Process detections and count vehicles"""
        counts = {
            'frame_counts': [0]*4,
            'lane_counts': [[0,0,0] for _ in range(4)],
            'ambulance_counts': [0]*4,
            'ambulance_lane_counts': [[0,0,0] for _ in range(4)]
        }
        
        for i in range(4):
            # Vehicles
            if results[i].boxes.data is not None and len(results[i].boxes.data) > 0:
                boxes = results[i].boxes.xyxy.cpu().numpy()
                classes = results[i].boxes.cls.int().cpu().numpy()
                
                for box, cls in zip(boxes, classes):
                    if cls in self.VEHICLE_CLASSES:
                        cx = int((box[0] + box[2]) * 0.5)
                        cy = int((box[1] + box[3]) * 0.5)
                        counts['frame_counts'][i] += 1
                        
                        for lane_idx, polygon in enumerate(self.LANES[i]):
                            if cv2.pointPolygonTest(polygon, (cx, cy), False) >= 0:
                                counts['lane_counts'][i][lane_idx] += 1
                                break
            
            # Ambulances
            if results_ambulance[i].boxes.data is not None and len(results_ambulance[i].boxes.data) > 0:
                boxes = results_ambulance[i].boxes.xyxy.cpu().numpy()
                
                for box in boxes:
                    cx = int((box[0] + box[2]) * 0.5)
                    cy = int((box[1] + box[3]) * 0.5)
                    counts['ambulance_counts'][i] += 1
                    
                    for lane_idx, polygon in enumerate(self.LANES[i]):
                        if cv2.pointPolygonTest(polygon, (cx, cy), False) >= 0:
                            counts['ambulance_lane_counts'][i][lane_idx] += 1
                            break
        
        return counts
    
    def get_current_frames(self):
        """Get current frames for video streaming"""
        with self.frame_lock:
            return [f.copy() if f is not None else None for f in self.current_frames]
    
    def get_traffic_summary(self):
        """Get traffic summary compatible with Flask app"""
        with self.results_lock:
            counts = self.latest_traffic_counts.copy()
        
        # Convert to PPO format expected by Flask app
        ppo_format = {}
        
        # Map camera indices to directions
        direction_mapping = [0, 1, 2, 3]  # North, South, East, West
        
        for cam_idx in range(4):
            direction = self.DIRS[cam_idx]
            abbr = self.ABBR[direction]
            
            # Distribute vehicles across movement types (L, S, R)
            total_vehicles = counts['frame_counts'][cam_idx]
            lane_vehicles = counts['lane_counts'][cam_idx]
            
            # Simple distribution: assume lane 0=Left, lane 1=Straight, lane 2=Right
            left_count = lane_vehicles[0] if len(lane_vehicles) > 0 else total_vehicles // 3
            straight_count = lane_vehicles[1] if len(lane_vehicles) > 1 else total_vehicles // 3
            right_count = lane_vehicles[2] if len(lane_vehicles) > 2 else total_vehicles - left_count - straight_count
            
            ppo_format[f"{abbr}_L"] = max(0, left_count)
            ppo_format[f"{abbr}_S"] = max(0, straight_count)
            ppo_format[f"{abbr}_R"] = max(0, right_count)
        
        # Emergency status
        emergency_detected = any(counts['ambulance_counts'][i] > 0 for i in range(4))
        emergency_directions = []
        if emergency_detected:
            for i in range(4):
                if counts['ambulance_counts'][i] > 0:
                    emergency_directions.append(self.DIRS[i])
        
        emergency_status = {
            'emergency_detected': emergency_detected,
            'emergency_directions': emergency_directions,
            'ambulance_counts': counts['ambulance_counts']
        }
        
        return {
            'ppo_format': ppo_format,
            'emergency_status': emergency_status,
            'raw_counts': counts,
            'timestamp': datetime.now().isoformat()
        }
    
    def is_healthy(self):
        """Check if the system is running properly"""
        return (self.is_running and 
                self.is_initialized and 
                self.inference_processor is not None and
                len(self.readers) == 4)
    
    def stop(self):
        """Stop the detection system"""
        logger.info("Stopping traffic detection system...")
        
        self.is_running = False
        
        # Stop inference processor
        if self.inference_processor:
            self.inference_processor.stop()
            self.inference_processor = None
        
        # Stop video readers
        for reader in self.readers:
            reader.stop()
        self.readers = []
        
        # Clear state
        with self.frame_lock:
            self.current_frames = [None, None, None, None]
        
        with self.results_lock:
            self.latest_results = None
            self.latest_ambulance_results = None
        
        logger.info("Traffic detection system stopped")


class VideoReader:
    def __init__(self, path, resize_width, resize_height, index):
        self.cap = cv2.VideoCapture(path)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
        self.resize_width = resize_width
        self.resize_height = resize_height
        self.index = index
        self.queue = Queue(maxsize=60)
        self.stopped = False
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        
    def start(self):
        Thread(target=self.update, daemon=True).start()
        return self
    
    def update(self):
        while not self.stopped:
            if not self.queue.full():
                ret, frame = self.cap.read()
                if not ret:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = self.cap.read()
                
                if ret:
                    frame = cv2.resize(frame, (self.resize_width, self.resize_height), 
                                     interpolation=cv2.INTER_LINEAR)
                    self.queue.put(frame)
            else:
                time.sleep(0.001)
    
    def read(self):
        return self.queue.get()
    
    def stop(self):
        self.stopped = True
        self.cap.release()


class InferenceProcessor:
    def __init__(self, model, model_ambulance, device, use_half=False):
        self.model = model
        self.model_ambulance = model_ambulance
        self.device = device
        self.use_half = use_half
        self.input_queue = Queue(maxsize=3)
        self.output_queue = Queue(maxsize=3)
        self.stopped = False
        self.lock = Lock()
        self.last_results = None
        self.processing = False
        
    def start(self):
        Thread(target=self.process, daemon=True).start()
        return self
    
    def process(self):
        while not self.stopped:
            try:
                frames = self.input_queue.get(timeout=0.1)
                self.processing = True
                
                with torch.no_grad():
                    # Batch inference with optimizations
                    results = self.model.predict(
                        frames, 
                        classes=[1, 2, 3, 5, 6, 7], 
                        device=self.device, 
                        verbose=False,
                        half=self.use_half,
                        imgsz=256,
                        conf=0.25,
                        iou=0.45
                    )
                    results_ambulance = self.model_ambulance.predict(
                        frames, 
                        device=self.device, 
                        verbose=False,
                        half=self.use_half,
                        imgsz=256,
                        conf=0.7,
                        iou=0.45
                    )
                
                with self.lock:
                    self.last_results = (results, results_ambulance)
                
                if not self.output_queue.full():
                    self.output_queue.put((results, results_ambulance))
                
                self.processing = False
                    
            except Exception as e:
                self.processing = False
                continue
    
    def submit(self, frames):
        if not self.input_queue.full() and not self.processing:
            self.input_queue.put(frames)
            return True
        return False
    
    def get_results(self):
        try:
            return self.output_queue.get_nowait()
        except:
            with self.lock:
                return self.last_results
    
    def stop(self):
        self.stopped = True


# Global detector instance
_detector = None

def initialize_detector():
    """Initialize the integrated traffic detector"""
    global _detector
    try:
        _detector = IntegratedTrafficDetector()
        return _detector.start()
    except Exception as e:
        logger.error(f"Failed to initialize detector: {e}")
        return False

def get_detector():
    """Get the detector instance"""
    return _detector

def cleanup_detector():
    """Cleanup the detector"""
    global _detector
    if _detector:
        _detector.stop()
        _detector = None