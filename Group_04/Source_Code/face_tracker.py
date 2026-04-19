import cv2
import mediapipe as mp
import numpy as np


class FaceTracker:
    """Face and eye tracking using MediaPipe Face Mesh"""
    
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.3,  # Lowered from 0.5
            min_tracking_confidence=0.3     # Lowered from 0.5
        )
        
        # Eye landmark indices
        self.LEFT_EYE = [362, 385, 387, 263, 373, 380]
        self.RIGHT_EYE = [33, 160, 158, 133, 153, 144]
        
        # Iris landmark indices
        self.LEFT_IRIS = [474, 475, 476, 477]
        self.RIGHT_IRIS = [469, 470, 471, 472]
    
    def check_lighting_quality(self, frame):
        """Check if lighting is adequate"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean_brightness = np.mean(gray)
        std_brightness = np.std(gray)
        
        # Check if too dark, too bright, or low contrast
        if mean_brightness < 50:
            return False, "Too dark - please increase lighting"
        elif mean_brightness > 200:
            return False, "Too bright - reduce direct light on face"
        elif std_brightness < 20:
            return False, "Low contrast - adjust lighting"
        
        return True, "Lighting OK"
    
    def check_face_position(self, face_landmarks, frame_width, frame_height):
        """Check if face is properly positioned"""
        nose_tip = face_landmarks.landmark[1]
        
        # Check if face is centered (more lenient)
        nose_x = nose_tip.x * frame_width
        nose_y = nose_tip.y * frame_height
        
        center_x = frame_width / 2
        center_y = frame_height / 2
        
        x_offset = abs(nose_x - center_x) / frame_width
        y_offset = abs(nose_y - center_y) / frame_height
        
        # Much more lenient thresholds
        if x_offset > 0.35:
            if nose_x < center_x:
                return False, "Move your face to the right"
            else:
                return False, "Move your face to the left"
        
        if y_offset > 0.3:
            if nose_y < center_y:
                return False, "Move your face down slightly"
            else:
                return False, "Move your face up slightly"
        
        # Check distance (face size) - very lenient for normal sitting distance
        chin = face_landmarks.landmark[152]
        face_height_ratio = abs(nose_tip.y - chin.y)
        
        if face_height_ratio < 0.08:  # Much smaller minimum - allows far distance
            return False, "Move closer to camera"
        elif face_height_ratio > 0.65:  # Much larger maximum - allows close distance
            return False, "Move back from camera"
        
        return True, "Position good!"
        
    def process_frame(self, frame):
        """Process frame and extract eye landmarks with quality checks"""
        h, w, _ = frame.shape
        
        # Check lighting quality first
        lighting_ok, lighting_msg = self.check_lighting_quality(frame)
        
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process with MediaPipe
        results = self.face_mesh.process(rgb_frame)
        
        if not results.multi_face_landmarks:
            return {
                'status': 'no_face',
                'message': '❌ No face detected - position yourself in frame',
                'lighting_ok': lighting_ok,
                'lighting_message': lighting_msg
            }
        
        # Get first face
        face_landmarks = results.multi_face_landmarks[0]
        
        # Check face position
        position_ok, position_msg = self.check_face_position(face_landmarks, w, h)
        
        # Extract eye landmarks
        left_eye_points = []
        right_eye_points = []
        
        for idx in self.LEFT_EYE:
            landmark = face_landmarks.landmark[idx]
            left_eye_points.append([landmark.x * w, landmark.y * h])
        
        for idx in self.RIGHT_EYE:
            landmark = face_landmarks.landmark[idx]
            right_eye_points.append([landmark.x * w, landmark.y * h])
        
        left_eye_points = np.array(left_eye_points)
        right_eye_points = np.array(right_eye_points)
        
        # Check if eyes are visible (not occluded)
        left_eye_area = cv2.contourArea(left_eye_points.astype(int))
        right_eye_area = cv2.contourArea(right_eye_points.astype(int))
        
        if left_eye_area < 50 or right_eye_area < 50:
            return {
                'status': 'eyes_not_visible',
                'message': '⚠️ Eyes not clearly visible - adjust angle or lighting',
                'lighting_ok': lighting_ok,
                'lighting_message': lighting_msg
            }
        
        # Extract iris positions
        left_iris_points = []
        right_iris_points = []
        
        for idx in self.LEFT_IRIS:
            landmark = face_landmarks.landmark[idx]
            left_iris_points.append([landmark.x * w, landmark.y * h])
        
        for idx in self.RIGHT_IRIS:
            landmark = face_landmarks.landmark[idx]
            right_iris_points.append([landmark.x * w, landmark.y * h])
        
        left_iris_center = np.mean(left_iris_points, axis=0)
        right_iris_center = np.mean(right_iris_points, axis=0)
        
        # Calculate gaze direction
        left_eye_center = np.mean(left_eye_points, axis=0)
        right_eye_center = np.mean(right_eye_points, axis=0)
        
        left_gaze = left_iris_center - left_eye_center
        right_gaze = right_iris_center - right_eye_center
        
        avg_gaze = (left_gaze + right_gaze) / 2.0
        
        # Normalize gaze direction more aggressively for better detection
        eye_width = np.linalg.norm(left_eye_points[0] - left_eye_points[3])
        eye_height = np.linalg.norm(left_eye_points[1] - left_eye_points[5])
        
        # Normalize by eye dimensions
        normalized_gaze = np.array([
            avg_gaze[0] / (eye_width * 0.5),  # Horizontal normalized
            avg_gaze[1] / (eye_height * 0.5)  # Vertical normalized
        ])
        
        # Calculate face size (for near-far tracking)
        nose_tip = face_landmarks.landmark[1]
        chin = face_landmarks.landmark[152]
        face_height = abs(nose_tip.y - chin.y)
        
        return {
            'status': 'success',
            'left_eye': left_eye_points,
            'right_eye': right_eye_points,
            'left_iris': left_iris_center,
            'right_iris': right_iris_center,
            'gaze_direction': normalized_gaze,
            'face_size': face_height,
            'raw_landmarks': face_landmarks,
            'lighting_ok': lighting_ok,
            'lighting_message': lighting_msg,
            'position_ok': position_ok,
            'position_message': position_msg
        }
    
    def __del__(self):
        """Cleanup"""
        if hasattr(self, 'face_mesh'):
            self.face_mesh.close()
