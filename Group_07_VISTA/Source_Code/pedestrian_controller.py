"""
Pedestrian-Aware Traffic Signal Controller
Dynamically allocates pedestrian crossing time based on footpath ROI detections.

System behavior:
- Total signal cycle = 120 seconds
- 20 seconds reserved for pedestrian crossing (only when pedestrians detected)
- During pedestrian phase → all vehicle signals turn RED
- Persistence buffer (5 sec) to prevent signal flickering
"""

import cv2
import numpy as np
from ultralytics import YOLO
import os
import time
import threading
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# GLOBAL PHASE-LOCKED STATE (Event-driven, instant synchronization)
# ============================================================================
# These global variables provide INSTANT state sharing across all components
# No polling delay - state changes are immediately visible everywhere

_global_pedestrian_state = {
    'phase_active': False,           # Is pedestrian phase currently active?
    'phase_start_time': None,        # When did the phase start?
    'phase_remaining': 0,            # Seconds remaining in phase
    'phase_locked': False,           # Prevent retriggering during active phase
    'detection_confirmed': False,    # Has detection been confirmed (debounced)?
    'detection_count': 0,            # Current pedestrian count
    'consecutive_frames': 0,         # Frames with consecutive detection (for debounce)
    'last_detection_time': None,     # Last time pedestrians were detected
    'vehicle_signals_red': False,    # Should all vehicle signals be RED?
    'request_pending': False,        # Is there a pending request for pedestrian phase?
}
_global_state_lock = threading.Lock()

# Configuration constants (exposed globally for instant access)
PHASE_DURATION = 20           # Fixed 20-second pedestrian phase (LOCKED)
DEBOUNCE_FRAMES = 5           # Require 5 consecutive frames of detection (prevents false positives)
PERSISTENCE_BUFFER = 5        # Seconds to wait after last detection before clearing request
WAIT_THRESHOLD = 10           # Seconds pedestrian must wait in ROI before being counted


def get_global_pedestrian_state():
    """Get instant access to global pedestrian state (thread-safe)"""
    with _global_state_lock:
        return _global_pedestrian_state.copy()


def trigger_pedestrian_phase():
    """
    EVENT-DRIVEN: Immediately trigger and LOCK pedestrian phase for full 20 seconds.
    Returns True if phase was triggered, False if already locked.
    """
    with _global_state_lock:
        # Prevent retriggering during active/locked phase
        if _global_pedestrian_state['phase_locked']:
            return False
        
        # Only trigger if there's actually a confirmed detection
        if not _global_pedestrian_state['detection_confirmed']:
            logger.warning("⚠️ Pedestrian phase trigger attempted without confirmed detection - ignoring")
            return False
        
        # LOCK the phase for full duration
        start_time = time.time()
        _global_pedestrian_state['phase_active'] = True
        _global_pedestrian_state['phase_locked'] = True
        _global_pedestrian_state['phase_start_time'] = start_time
        _global_pedestrian_state['phase_remaining'] = PHASE_DURATION
        _global_pedestrian_state['vehicle_signals_red'] = True
        _global_pedestrian_state['request_pending'] = False
        # Clear detection_confirmed to prevent retriggering
        _global_pedestrian_state['detection_confirmed'] = False
        
        logger.info(f"🚶 PEDESTRIAN PHASE TRIGGERED - LOCKED for {PHASE_DURATION} seconds")
        return True


def update_global_phase_timer():
    """
    Update the phase timer - call this frequently to keep remaining time accurate.
    Returns: (phase_active, phase_remaining, phase_just_ended)
    """
    with _global_state_lock:
        if _global_pedestrian_state['phase_active'] and _global_pedestrian_state['phase_start_time']:
            elapsed = time.time() - _global_pedestrian_state['phase_start_time']
            remaining = max(0, PHASE_DURATION - elapsed)
            _global_pedestrian_state['phase_remaining'] = remaining
            
            # Phase completed - auto-unlock
            if remaining <= 0:
                _global_pedestrian_state['phase_active'] = False
                _global_pedestrian_state['phase_locked'] = False
                _global_pedestrian_state['vehicle_signals_red'] = False
                _global_pedestrian_state['phase_start_time'] = None
                _global_pedestrian_state['phase_remaining'] = 0
                _global_pedestrian_state['detection_confirmed'] = False
                _global_pedestrian_state['consecutive_frames'] = 0
                logger.info("🚗 PEDESTRIAN PHASE COMPLETED (20s) - Phase unlocked, resuming vehicle flow")
                return (False, 0, True)  # Phase ended
            return (True, remaining, False)  # Phase still active
        return (False, 0, False)  # Phase not active


def is_pedestrian_phase_locked():
    """Check if pedestrian phase is locked (prevents retriggering)"""
    with _global_state_lock:
        return _global_pedestrian_state['phase_locked']


def is_pedestrian_phase_active():
    """Check if pedestrian phase is currently active"""
    with _global_state_lock:
        return _global_pedestrian_state['phase_active']


def get_pedestrian_phase_remaining():
    """Get remaining time in pedestrian phase"""
    with _global_state_lock:
        return _global_pedestrian_state['phase_remaining']


def set_detection_confirmed(confirmed: bool, count: int = 0):
    """Set detection confirmed state (after debounce)"""
    with _global_state_lock:
        _global_pedestrian_state['detection_confirmed'] = confirmed
        _global_pedestrian_state['detection_count'] = count
        if confirmed:
            _global_pedestrian_state['request_pending'] = True
            _global_pedestrian_state['last_detection_time'] = time.time()


def has_pending_pedestrian_request():
    """Check if there's a confirmed pending request for pedestrian phase"""
    with _global_state_lock:
        return (_global_pedestrian_state['request_pending'] and 
                _global_pedestrian_state['detection_confirmed'] and
                _global_pedestrian_state['detection_count'] > 0 and
                not _global_pedestrian_state['phase_locked'])


def clear_pending_request():
    """Clear the pending request (used after persistence buffer expires)"""
    with _global_state_lock:
        _global_pedestrian_state['request_pending'] = False
        _global_pedestrian_state['detection_confirmed'] = False
        _global_pedestrian_state['consecutive_frames'] = 0
        _global_pedestrian_state['detection_count'] = 0


class PedestrianController:
    """
    Controls pedestrian phase based on ROI detections from footpath areas.
    Uses EVENT-DRIVEN, PHASE-LOCKED model for instant response.
    
    Key features:
    - Debounce: Requires DEBOUNCE_FRAMES consecutive frames with detection
    - Phase Lock: Once triggered, phase runs for full PHASE_DURATION seconds
    - No Early Exit: Phase cannot be interrupted once started
    - Instant State: Uses global state variables for zero-latency sharing
    """
    
    def __init__(self, video_path=None, model_path="yolo11n.pt"):
        # Configuration
        self.VIDEO_PATH = video_path or "videos/v6.mp4"
        self.MODEL_PATH = model_path
        self.FRAME_WIDTH = 256
        self.FRAME_HEIGHT = 144
        
        # State variables
        self.model = None
        self.cap = None
        self.footpath_rois = []
        self.is_running = False
        self.is_initialized = False
        
        # Local tracking for debounce (synced to global state)
        self._consecutive_detection_frames = 0
        self._last_no_detection_time = None
        
        # Pedestrian tracking with wait threshold (10 seconds)
        self.pedestrian_tracker = {}  # {ped_id: {'first_seen': time, 'last_seen': time, 'last_pos': (x,y), 'counted': bool}}
        self.next_pedestrian_id = 0
        self.counted_pedestrians = 0
        
        # Thread safety
        self.state_lock = threading.Lock()
        self.processing_thread = None
        
        # Current frame for display
        self.current_frame = None
        self.frame_lock = threading.Lock()
        
    def _load_footpath_rois(self):
        """Load all footpath ROI files"""
        self.footpath_rois = []
        i = 1
        while True:
            filename = f"footpath_roi_{i}.txt"
            if not os.path.exists(filename):
                break
            try:
                roi = np.loadtxt(filename, dtype=np.int32)
                self.footpath_rois.append(roi.reshape((-1, 1, 2)))
                logger.info(f"Loaded {filename}")
            except Exception as e:
                logger.error(f"Error loading {filename}: {e}")
            i += 1
        
        if len(self.footpath_rois) == 0:
            logger.warning("No footpath ROI files found! Pedestrian detection disabled.")
            return False
        
        logger.info(f"Loaded {len(self.footpath_rois)} footpath ROI polygons")
        return True
    
    def initialize(self):
        """Initialize the pedestrian detection system"""
        try:
            logger.info("Initializing Pedestrian Controller...")
            
            # Load YOLO model
            logger.info("Loading YOLO model for pedestrian detection...")
            self.model = YOLO(self.MODEL_PATH)
            
            # Load footpath ROIs
            if not self._load_footpath_rois():
                logger.warning("No ROIs loaded - pedestrian phase will be disabled")
            
            # Open video capture
            self.cap = cv2.VideoCapture(self.VIDEO_PATH)
            if not self.cap.isOpened():
                logger.error(f"Could not open video: {self.VIDEO_PATH}")
                return False
            
            self.is_initialized = True
            logger.info("Pedestrian Controller initialized successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Pedestrian Controller: {e}")
            return False
    
    def start(self):
        """Start the pedestrian detection processing"""
        if not self.is_initialized:
            if not self.initialize():
                return False
        
        self.is_running = True
        self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.processing_thread.start()
        logger.info("Pedestrian Controller started")
        return True
    
    def stop(self):
        """Stop the pedestrian detection system"""
        logger.info("Stopping Pedestrian Controller...")
        self.is_running = False
        
        if self.cap:
            self.cap.release()
            self.cap = None
        
        logger.info("Pedestrian Controller stopped")
    
    def _processing_loop(self):
        """Main processing loop for pedestrian detection"""
        while self.is_running:
            try:
                if not self.cap or not self.cap.isOpened():
                    # Try to reopen video
                    self.cap = cv2.VideoCapture(self.VIDEO_PATH)
                    if not self.cap.isOpened():
                        time.sleep(1)
                        continue
                
                ret, frame = self.cap.read()
                if not ret:
                    # Loop video
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                
                # Resize frame
                frame = cv2.resize(frame, (self.FRAME_WIDTH, self.FRAME_HEIGHT))
                
                # Run YOLO detection for persons only
                results = self.model(
                    frame,
                    conf=0.4,
                    classes=[0],  # person class only
                    verbose=False
                )
                
                # Count pedestrians in footpath ROIs
                footpath_count = 0
                detected_positions = []  # Store (cx, cy) for tracking
                
                for r in results:
                    for box in r.boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        cx = (x1 + x2) // 2
                        cy = (y1 + y2) // 2
                        
                        # Check if person is inside any footpath ROI
                        for roi in self.footpath_rois:
                            if cv2.pointPolygonTest(roi, (cx, cy), True) >= 0:
                                footpath_count += 1
                                detected_positions.append((x1, y1, x2, y2, cx, cy))  # Store full box + center for visualization
                                break
                
                # EVENT-DRIVEN: Update detection with debounce logic and 10s wait tracking
                self._update_detection_with_debounce(footpath_count, detected_positions)
                
                # Update global phase timer
                update_global_phase_timer()
                
                # Draw visualization on frame
                display_frame = self._draw_visualization(frame, detected_positions)
                
                with self.frame_lock:
                    self.current_frame = display_frame
                
                # Control frame rate
                time.sleep(1.0 / 30)  # ~30 FPS
                
            except Exception as e:
                logger.error(f"Error in pedestrian processing loop: {e}")
                time.sleep(0.1)
    
    def _update_detection_with_debounce(self, footpath_count, detected_positions):
        """
        EVENT-DRIVEN detection update with debounce mechanism.
        Requires DEBOUNCE_FRAMES consecutive frames with detection to confirm.
        Pedestrians must wait 10 seconds in ROI before being counted.
        """
        current_time = time.time()
        
        # Don't process detection if phase is locked (prevents retriggering)
        if is_pedestrian_phase_locked():
            # Just update the count in global state for display
            with _global_state_lock:
                _global_pedestrian_state['detection_count'] = self.counted_pedestrians
            return
        
        # ============================================
        # PEDESTRIAN TRACKING WITH 10-SECOND WAIT
        # ============================================
        # Remove old pedestrians from tracker (when they leave ROI)
        ids_to_remove = []
        for ped_id, data in self.pedestrian_tracker.items():
            if current_time - data['last_seen'] > 1.0:  # Remove if not seen for 1 second
                ids_to_remove.append(ped_id)
        
        for ped_id in ids_to_remove:
            del self.pedestrian_tracker[ped_id]
        
        # Match detected pedestrians with tracked ones (simple proximity matching)
        for detection in detected_positions:
            # Extract center coordinates from detection tuple (x1, y1, x2, y2, cx, cy)
            cx, cy = detection[4], detection[5]
            matched = False
            for ped_id, data in self.pedestrian_tracker.items():
                # Simple distance-based matching (within 50 pixels)
                last_cx, last_cy = data.get('last_pos', (cx, cy))
                dist = np.sqrt((cx - last_cx)**2 + (cy - last_cy)**2)
                if dist < 50:
                    # Update existing pedestrian
                    data['last_seen'] = current_time
                    data['last_pos'] = (cx, cy)
                    
                    # Check if pedestrian has been waiting long enough to be counted
                    wait_time = current_time - data['first_seen']
                    if wait_time >= WAIT_THRESHOLD and not data['counted']:
                        data['counted'] = True
                        logger.info(f"✅ [COUNTED] Pedestrian waited {wait_time:.1f}s and is now counted")
                    
                    matched = True
                    break
            
            if not matched:
                # New pedestrian detected
                self.pedestrian_tracker[self.next_pedestrian_id] = {
                    'first_seen': current_time,
                    'last_seen': current_time,
                    'last_pos': (cx, cy),
                    'counted': False
                }
                logger.debug(f"🆕 New pedestrian {self.next_pedestrian_id} detected at ({cx}, {cy})")
                self.next_pedestrian_id += 1
        
        # Calculate current count of pedestrians who have waited 10+ seconds
        self.counted_pedestrians = sum(1 for data in self.pedestrian_tracker.values() if data['counted'])
        
        # Use counted pedestrians (not raw detection count)
        if self.counted_pedestrians >= 1:
            # Counted pedestrian present - increment consecutive frame counter
            self._consecutive_detection_frames += 1
            self._last_no_detection_time = None  # Reset no-detection timer
            
            # Log detection for debugging (only on frame count change)
            if self._consecutive_detection_frames <= DEBOUNCE_FRAMES:
                logger.debug(f"🔍 Counted pedestrians: {self.counted_pedestrians}, consecutive_frames={self._consecutive_detection_frames}/{DEBOUNCE_FRAMES}")
            
            # Update global state with counted pedestrians
            with _global_state_lock:
                _global_pedestrian_state['detection_count'] = self.counted_pedestrians
                _global_pedestrian_state['consecutive_frames'] = self._consecutive_detection_frames
                _global_pedestrian_state['last_detection_time'] = current_time
                
                # Check if debounce threshold met (confirmed detection)
                if self._consecutive_detection_frames >= DEBOUNCE_FRAMES and self.counted_pedestrians > 0:
                    if not _global_pedestrian_state['detection_confirmed']:
                        _global_pedestrian_state['detection_confirmed'] = True
                        _global_pedestrian_state['request_pending'] = True
                        logger.info(f"✅ PEDESTRIAN DETECTION CONFIRMED: {self.counted_pedestrians} pedestrians (after {DEBOUNCE_FRAMES} consecutive frames + 10s wait)")
        else:
            # No counted pedestrians - reset consecutive counter IMMEDIATELY
            was_detecting = self._consecutive_detection_frames > 0
            self._consecutive_detection_frames = 0
            
            # Log when detection stops
            if was_detecting:
                logger.debug(f"❌ Counted pedestrian count dropped to 0 - resetting debounce")
            
            # Update global state - clear count immediately
            with _global_state_lock:
                _global_pedestrian_state['detection_count'] = 0
                _global_pedestrian_state['consecutive_frames'] = 0
                
                # If detection was previously confirmed but not yet triggered, clear it
                if _global_pedestrian_state['detection_confirmed'] and not _global_pedestrian_state['phase_active']:
                    logger.warning("⚠️ Counted pedestrians dropped to 0 before phase trigger - clearing confirmed status")
                    _global_pedestrian_state['detection_confirmed'] = False
                    _global_pedestrian_state['request_pending'] = False
            
            # Check persistence buffer for clearing request
            if self._last_no_detection_time is None:
                self._last_no_detection_time = current_time
            elif current_time - self._last_no_detection_time >= PERSISTENCE_BUFFER:
                # Persistence buffer expired - clear the pending request
                if has_pending_pedestrian_request():
                    clear_pending_request()
                    logger.info(f"⏱️ Pedestrian request cleared after {PERSISTENCE_BUFFER}s persistence buffer")
    
    def _update_phase_control(self):
        """Update pedestrian phase timing control - DEPRECATED, use update_global_phase_timer()"""
        # Now handled by global state - this method kept for compatibility
        pass
    
    def _draw_visualization(self, frame, detected_positions):
        """Draw ROIs and detection visualization using global state"""
        display_frame = frame.copy()
        
        # Draw footpath ROIs
        for roi in self.footpath_rois:
            cv2.polylines(display_frame, [roi], True, (255, 255, 0), 2)
        
        # Draw detected pedestrians
        for x1, y1, x2, y2, cx, cy in detected_positions:
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), (255, 255, 0), 2)
            cv2.circle(display_frame, (cx, cy), 4, (0, 0, 255), -1)
        
        # Get global state for display
        global_state = get_global_pedestrian_state()
        
        # Display status based on global state
        if global_state['phase_active']:
            status_text = f"🚶 PEDESTRIAN PHASE: {int(global_state['phase_remaining'])}s [LOCKED]"
            status_color = (0, 0, 255)  # Red for vehicles
        elif global_state['request_pending']:
            status_text = f"⚠️ PED REQUEST ({global_state['detection_count']}) - {global_state['consecutive_frames']}/{DEBOUNCE_FRAMES}"
            status_color = (0, 165, 255)  # Orange
        else:
            status_text = "🚗 VEHICLE FLOW"
            status_color = (0, 255, 0)  # Green
        
        cv2.putText(
            display_frame,
            status_text,
            (10, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            status_color,
            2
        )
        
        # Show pedestrian count and debounce progress
        debounce_text = f"Pedestrians: {global_state['detection_count']} | Frames: {global_state['consecutive_frames']}/{DEBOUNCE_FRAMES}"
        cv2.putText(
            display_frame,
            debounce_text,
            (10, 45),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (255, 255, 255),
            1
        )
        
        return display_frame
    
    def start_pedestrian_phase(self):
        """
        EVENT-DRIVEN: Start the pedestrian crossing phase using global state.
        Phase will be LOCKED for full PHASE_DURATION seconds.
        """
        return trigger_pedestrian_phase()
    
    def _end_pedestrian_phase(self):
        """End the pedestrian crossing phase - DEPRECATED, handled by global timer"""
        self.vehicle_signals_overridden = False
        self.pedestrian_request_flag = False  # Clear request after phase completes
        self.last_pedestrian_time = None
        pass  # Handled by global timer
    
    def force_end_pedestrian_phase(self):
        """Force end pedestrian phase (for emergency override only)"""
        # Note: This bypasses the phase lock - use only for true emergencies
        with _global_state_lock:
            if _global_pedestrian_state['phase_active']:
                _global_pedestrian_state['phase_active'] = False
                _global_pedestrian_state['phase_locked'] = False
                _global_pedestrian_state['vehicle_signals_red'] = False
                _global_pedestrian_state['phase_start_time'] = None
                _global_pedestrian_state['phase_remaining'] = 0
                logger.warning("⚠️ PEDESTRIAN PHASE FORCE-ENDED (Emergency override)")
    
    def get_status(self):
        """
        Get current pedestrian controller status using GLOBAL STATE.
        This provides instant access to phase-locked state.
        """
        global_state = get_global_pedestrian_state()
        return {
            'pedestrian_count': global_state['detection_count'],
            'pedestrian_detected': global_state['detection_count'] > 0,
            'pedestrian_request_flag': global_state['request_pending'],
            'pedestrian_phase_active': global_state['phase_active'],
            'pedestrian_phase_remaining': global_state['phase_remaining'],
            'vehicle_signals_overridden': global_state['vehicle_signals_red'],
            'phase_locked': global_state['phase_locked'],
            'detection_confirmed': global_state['detection_confirmed'],
            'consecutive_frames': global_state['consecutive_frames'],
            'persistence_buffer': PERSISTENCE_BUFFER,
            'phase_duration': PHASE_DURATION,
            'debounce_frames': DEBOUNCE_FRAMES
        }
    
    def should_activate_pedestrian_phase(self):
        """Check if pedestrian phase should be activated using global state"""
        return has_pending_pedestrian_request() and len(self.footpath_rois) > 0
    
    def get_current_frame(self):
        """Get current processed frame for display"""
        with self.frame_lock:
            return self.current_frame.copy() if self.current_frame is not None else None
    
    def is_healthy(self):
        """Check if the system is running properly"""
        return self.is_running and self.is_initialized


# Global pedestrian controller instance
_pedestrian_controller = None


def initialize_pedestrian_controller(video_path=None):
    """Initialize the global pedestrian controller"""
    global _pedestrian_controller
    try:
        _pedestrian_controller = PedestrianController(video_path=video_path)
        if _pedestrian_controller.initialize():
            _pedestrian_controller.start()
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to initialize pedestrian controller: {e}")
        return False


def get_pedestrian_controller():
    """Get the global pedestrian controller instance"""
    return _pedestrian_controller


def cleanup_pedestrian_controller():
    """Cleanup the pedestrian controller"""
    global _pedestrian_controller
    if _pedestrian_controller:
        _pedestrian_controller.stop()
        _pedestrian_controller = None
    logger.info("Pedestrian controller cleaned up")


def get_pedestrian_status():
    """
    Convenience function to get pedestrian status.
    Uses GLOBAL STATE for instant access (zero latency).
    """
    global _pedestrian_controller
    
    # Always update the global timer first
    update_global_phase_timer()
    
    if _pedestrian_controller and _pedestrian_controller.is_healthy():
        return _pedestrian_controller.get_status()
    
    # Fallback - still use global state if available
    global_state = get_global_pedestrian_state()
    return {
        'pedestrian_count': global_state['detection_count'],
        'pedestrian_detected': global_state['detection_count'] > 0,
        'pedestrian_request_flag': global_state['request_pending'],
        'pedestrian_phase_active': global_state['phase_active'],
        'pedestrian_phase_remaining': global_state['phase_remaining'],
        'vehicle_signals_overridden': global_state['vehicle_signals_red'],
        'phase_locked': global_state['phase_locked'],
        'detection_confirmed': global_state['detection_confirmed'],
        'consecutive_frames': global_state['consecutive_frames'],
        'persistence_buffer': PERSISTENCE_BUFFER,
        'phase_duration': PHASE_DURATION,
        'debounce_frames': DEBOUNCE_FRAMES
    }
