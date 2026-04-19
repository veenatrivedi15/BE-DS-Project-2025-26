import numpy as np


class ExerciseManager:
    """Manages all available eye exercises"""
    
    def __init__(self):
        self.exercises = {
            'blink': {
                'id': 'blink',
                'name': 'Blink Exercise',
                'description': 'Regular blinking helps reduce eye strain and keeps eyes moist. Blink consciously and completely.',
                'target_reps': 20,
                'duration': 60,
                'instructions': [
                    'Look straight at the camera',
                    'Blink slowly and completely',
                    'Close eyes fully for each blink',
                    'Repeat 20 times'
                ],
                'benefits': 'Reduces eye dryness and strain from screen time'
            },
            'left_right': {
                'id': 'left_right',
                'name': 'Left-Right Gaze',
                'description': 'Move your eyes from left to right to exercise horizontal eye muscles.',
                'target_reps': 15,
                'duration': 45,
                'instructions': [
                    'Look straight ahead',
                    'Move eyes to extreme left',
                    'Hold for 2 seconds',
                    'Move eyes to extreme right',
                    'Hold for 2 seconds',
                    'Keep head still'
                ],
                'benefits': 'Strengthens lateral eye muscles and improves tracking'
            },
            'up_down': {
                'id': 'up_down',
                'name': 'Up-Down Gaze',
                'description': 'Move your eyes up and down to exercise vertical eye muscles.',
                'target_reps': 15,
                'duration': 45,
                'instructions': [
                    'Look straight ahead',
                    'Move eyes up as far as comfortable',
                    'Hold for 2 seconds',
                    'Move eyes down',
                    'Hold for 2 seconds',
                    'Keep head still'
                ],
                'benefits': 'Strengthens vertical eye muscles and improves flexibility'
            },
            'near_far': {
                'id': 'near_far',
                'name': 'Near-Far Focus',
                'description': 'Alternate focus between near and far objects to exercise focusing muscles.',
                'target_reps': 10,
                'duration': 60,
                'instructions': [
                    'Hold your thumb at arm\'s length',
                    'Focus on your thumb for 2-3 seconds',
                    'Slowly bring thumb close to nose',
                    'Focus on thumb near your face for 2-3 seconds',
                    'Move thumb back to arm\'s length',
                    'Follow the on-screen timing cues'
                ],
                'benefits': 'Reduces eye fatigue and improves focusing ability'
            },
            'palming': {
                'id': 'palming',
                'name': 'Palming',
                'description': 'Rub your palms together and place them over closed eyes to deeply relax eye muscles.',
                'target_reps': 1,
                'duration': 60,
                'instructions': [
                    'Rub palms together vigorously to warm them',
                    'Close your eyes',
                    'Gently place warm palms over your eyes',
                    'Block all light - no pressure on eyeballs',
                    'Relax and breathe deeply for 1 minute'
                ],
                'benefits': 'Deeply relaxes eye muscles, reduces strain and improves circulation'
            }
        }
    
    def get_all_exercises(self):
        """Get list of all exercises"""
        return list(self.exercises.values())
    
    def get_exercise(self, exercise_id):
        """Get specific exercise by ID"""
        return self.exercises.get(exercise_id)
    
    def create_tracker(self, exercise_id):
        """Create appropriate tracker for exercise"""
        if exercise_id == 'blink':
            return BlinkTracker()
        elif exercise_id == 'left_right':
            return LeftRightTracker()
        elif exercise_id == 'up_down':
            return UpDownTracker()
        elif exercise_id == 'near_far':
            return NearFarTracker()
        elif exercise_id == 'palming':
            return PalmingTracker()
        return None


class BlinkTracker:
    """Tracks blinking exercise"""
    
    def __init__(self):
        self.eye_closed_threshold = 0.2
        self.was_open = True
        self.blink_started = False
        
    def update(self, landmarks):
        """Update tracker with new landmarks"""
        # Calculate eye aspect ratio (EAR)
        left_ear = self._calculate_ear(landmarks['left_eye'])
        right_ear = self._calculate_ear(landmarks['right_eye'])
        ear = (left_ear + right_ear) / 2.0
        
        is_closed = ear < self.eye_closed_threshold
        
        rep_completed = False
        accuracy = 0
        feedback = "Keep your eyes open"
        
        if is_closed and self.was_open:
            self.blink_started = True
            feedback = "Good - eyes closing"
        elif not is_closed and self.blink_started:
            rep_completed = True
            self.blink_started = False
            accuracy = 90 + np.random.randint(-10, 10)  # Simulate accuracy
            feedback = "Great blink!"
        
        self.was_open = not is_closed
        
        return {
            'rep_completed': rep_completed,
            'accuracy': max(0, min(100, accuracy)),
            'feedback': feedback,
            'progress': 'closed' if is_closed else 'open'
        }
    
    def _calculate_ear(self, eye_points):
        """Calculate Eye Aspect Ratio"""
        # Vertical distances
        v1 = np.linalg.norm(eye_points[1] - eye_points[5])
        v2 = np.linalg.norm(eye_points[2] - eye_points[4])
        # Horizontal distance
        h = np.linalg.norm(eye_points[0] - eye_points[3])
        
        ear = (v1 + v2) / (2.0 * h)
        return ear


class LeftRightTracker:
    """Tracks left-right gaze exercise"""
    
    def __init__(self):
        self.state = 'center'  # center, left, right
        self.threshold = 0.08  # Lower threshold for easier detection
        self.frames_in_state = 0
        self.min_frames = 3  # Need to hold position for 3 frames
        
    def update(self, landmarks):
        """Update tracker with new landmarks"""
        gaze_x = landmarks['gaze_direction'][0]
        
        rep_completed = False
        accuracy = 0
        feedback = "Look far left, then far right"
        
        # State machine for left-right movement
        if self.state == 'center':
            if gaze_x < -self.threshold:
                self.frames_in_state += 1
                if self.frames_in_state >= self.min_frames:
                    self.state = 'left'
                    self.frames_in_state = 0
                    feedback = "✓ Left position - now look right"
            elif gaze_x > self.threshold:
                self.frames_in_state += 1
                if self.frames_in_state >= self.min_frames:
                    self.state = 'right'
                    self.frames_in_state = 0
                    feedback = "✓ Right position - now look left"
            else:
                self.frames_in_state = 0
                feedback = "Look far left or right"
                
        elif self.state == 'left':
            if gaze_x > self.threshold:
                self.frames_in_state += 1
                if self.frames_in_state >= self.min_frames:
                    rep_completed = True
                    accuracy = 85 + np.random.randint(-10, 15)
                    feedback = "✓ Complete! Great job!"
                    self.state = 'center'
                    self.frames_in_state = 0
            else:
                feedback = "Now look far right"
                
        elif self.state == 'right':
            if gaze_x < -self.threshold:
                self.frames_in_state += 1
                if self.frames_in_state >= self.min_frames:
                    rep_completed = True
                    accuracy = 85 + np.random.randint(-10, 15)
                    feedback = "✓ Complete! Great job!"
                    self.state = 'center'
                    self.frames_in_state = 0
            else:
                feedback = "Now look far left"
        
        return {
            'rep_completed': rep_completed,
            'accuracy': max(0, min(100, accuracy)),
            'feedback': feedback,
            'progress': self.state
        }


class UpDownTracker:
    """Tracks up-down gaze exercise"""
    
    def __init__(self):
        self.state = 'center'  # center, up, down
        self.threshold = 0.12  # Balanced threshold
        self.frames_in_state = 0
        self.min_frames = 2  # Reduced for faster response
        self.frames_without_detection = 0
        
    def update(self, landmarks):
        """Update tracker with new landmarks"""
        gaze_y = landmarks['gaze_direction'][1]
        
        # If gaze is neutral (0,0), might be face not detected
        is_neutral = abs(gaze_y) < 0.01
        
        rep_completed = False
        accuracy = 0
        feedback = "Look up, then down"
        
        if is_neutral:
            self.frames_without_detection += 1
            # If looking down and face not detected, count it as down
            if self.state == 'up' and self.frames_without_detection > 1:
                self.frames_in_state += 1
                if self.frames_in_state >= self.min_frames:
                    rep_completed = True
                    accuracy = 85 + np.random.randint(-10, 15)
                    feedback = "✓ Complete! (Looking down detected)"
                    self.state = 'center'
                    self.frames_in_state = 0
                    self.frames_without_detection = 0
                else:
                    feedback = "Looking down... (extreme angle)"
            else:
                feedback = "Look UP or DOWN (extreme angles OK)"
            return {
                'rep_completed': rep_completed,
                'accuracy': max(0, min(100, accuracy)),
                'feedback': feedback,
                'progress': self.state
            }
        
        self.frames_without_detection = 0
        
        # State machine for up-down movement
        if self.state == 'center':
            if gaze_y < -self.threshold:
                self.frames_in_state += 1
                if self.frames_in_state >= self.min_frames:
                    self.state = 'up'
                    self.frames_in_state = 0
                    feedback = "✓ Up position - now look down"
            elif gaze_y > self.threshold:
                self.frames_in_state += 1
                if self.frames_in_state >= self.min_frames:
                    self.state = 'down'
                    self.frames_in_state = 0
                    feedback = "✓ Down position - now look up"
            else:
                self.frames_in_state = 0
                feedback = f"Look UP or DOWN (gaze: {gaze_y:.2f})"
                
        elif self.state == 'up':
            if gaze_y > self.threshold:
                self.frames_in_state += 1
                if self.frames_in_state >= self.min_frames:
                    rep_completed = True
                    accuracy = 85 + np.random.randint(-10, 15)
                    feedback = "✓ Complete! Excellent!"
                    self.state = 'center'
                    self.frames_in_state = 0
            else:
                feedback = f"Now look DOWN (gaze: {gaze_y:.2f})"
                
        elif self.state == 'down':
            if gaze_y < -self.threshold:
                self.frames_in_state += 1
                if self.frames_in_state >= self.min_frames:
                    rep_completed = True
                    accuracy = 85 + np.random.randint(-10, 15)
                    feedback = "✓ Complete! Excellent!"
                    self.state = 'center'
                    self.frames_in_state = 0
            else:
                feedback = f"Now look UP (gaze: {gaze_y:.2f})"
        
        return {
            'rep_completed': rep_completed,
            'accuracy': max(0, min(100, accuracy)),
            'feedback': feedback,
            'progress': self.state
        }


class NearFarTracker:
    """Tracks near-far focus exercise using finger movement"""
    
    def __init__(self):
        self.state = 'instruction'  # instruction -> far -> moving_near -> near -> moving_far -> complete
        self.instruction_frames = 0
        self.frames_in_state = 0
        self.min_frames = 3
        self.completed_cycles = 0
        
    def update(self, landmarks):
        """Update tracker - user should move finger, not face"""
        rep_completed = False
        accuracy = 0
        feedback = ""
        
        # Since we're tracking finger (object in front of face), face should stay relatively stable
        # We can't directly track the finger, so we give timed instructions
        
        if self.state == 'instruction':
            self.instruction_frames += 1
            if self.instruction_frames < 15:  # 3 seconds
                feedback = "👍 Hold your thumb at arm's length in front of you"
            else:
                self.state = 'far'
                self.frames_in_state = 0
                feedback = "✓ Now focus on your thumb"
                
        elif self.state == 'far':
            self.frames_in_state += 1
            if self.frames_in_state < 10:  # 2 seconds
                feedback = "👁️ Focus on your thumb at arm's length (2-3 sec)"
            else:
                self.state = 'moving_near'
                self.frames_in_state = 0
                feedback = "➡️ Slowly bring thumb close to your nose"
                
        elif self.state == 'moving_near':
            self.frames_in_state += 1
            if self.frames_in_state < 8:  # ~1.5 seconds
                feedback = "🤏 Bring thumb closer... keep focusing on it"
            else:
                self.state = 'near'
                self.frames_in_state = 0
                
        elif self.state == 'near':
            self.frames_in_state += 1
            if self.frames_in_state < 10:  # 2 seconds
                feedback = "👁️ Focus on thumb near your nose (2-3 sec)"
            else:
                self.state = 'moving_far'
                self.frames_in_state = 0
                feedback = "⬅️ Slowly move thumb back to arm's length"
                
        elif self.state == 'moving_far':
            self.frames_in_state += 1
            if self.frames_in_state < 8:  # ~1.5 seconds
                feedback = "↔️ Moving back... keep eyes focused on thumb"
            else:
                # Complete one cycle
                rep_completed = True
                accuracy = 90 + np.random.randint(-5, 10)
                self.completed_cycles += 1
                self.state = 'far'
                self.frames_in_state = 0
                feedback = "✓ Complete! Great focusing exercise"
        
        # Calculate progress through the cycle
        total_frames = 15 + 10 + 8 + 10 + 8  # Total frames in one cycle
        cycle_progress = 0
        if self.state == 'instruction':
            cycle_progress = (self.instruction_frames / 15) * 20
        elif self.state == 'far':
            cycle_progress = 20 + (self.frames_in_state / 10) * 20
        elif self.state == 'moving_near':
            cycle_progress = 40 + (self.frames_in_state / 8) * 15
        elif self.state == 'near':
            cycle_progress = 55 + (self.frames_in_state / 10) * 20
        elif self.state == 'moving_far':
            cycle_progress = 75 + (self.frames_in_state / 8) * 25
        
        return {
            'rep_completed': rep_completed,
            'accuracy': max(0, min(100, accuracy)),
            'feedback': feedback,
            'progress': f"{int(cycle_progress)}%"
        }


class PalmingTracker:
    """Tracks palming exercise - focuses on covering eyes properly"""
    
    def __init__(self):
        self.covering_frames = 0
        self.covering_target = 12 * 5  # 60 seconds of covering at ~5fps (1 minute)
        self.completed = False
        self.face_not_detected_frames = 0
        self.face_detected_frames = 0
        self.instruction_shown = False
        
    def update(self, landmarks):
        """Update tracker - single phase: cover eyes"""
        rep_completed = False
        accuracy = 0
        feedback = ""
        
        # Check if face is covered - if face not detected, assume hands are covering
        # Check if face is covered - if face not detected, assume hands are covering
        if landmarks is None or landmarks.get('status') != 'success':
            self.face_not_detected_frames += 1
            self.face_detected_frames = 0
            is_covered = self.face_not_detected_frames >= 2  # Need 2+ frames of no detection
        else:
            self.face_detected_frames += 1
            self.face_not_detected_frames = 0
            is_covered = False  # Face visible means not covered
        
        if is_covered:
            self.covering_frames += 1
        
        progress = min(100, (self.covering_frames / self.covering_target) * 100)
        time_remaining = max(0, int((self.covering_target - self.covering_frames) * 0.2))
        accuracy = int(progress)
        
        if self.covering_frames >= self.covering_target:
            rep_completed = True
            self.completed = True
            feedback = "✓ Palming complete! Your eyes are deeply relaxed 🎉"
        elif self.covering_frames == 0:
            feedback = "🙌 First, rub your palms together to warm them, then cover your eyes"
        elif not is_covered:
            feedback = f"🤲 Cover your closed eyes with warm palms - {time_remaining}s remaining"
        elif progress < 25:
            feedback = f"😌 Good! Breathe slowly and relax - {time_remaining}s"
        elif progress < 50:
            feedback = f"😊 Feel the warmth and darkness - {time_remaining}s"
        elif progress < 75:
            feedback = f"🧘 Deep relaxation, keep breathing - {time_remaining}s"
        else:
            feedback = f"✨ Almost complete, stay relaxed - {time_remaining}s"
        
        return {
            'rep_completed': rep_completed,
            'accuracy': accuracy,
            'feedback': feedback,
            'progress': f"{int(progress)}%"
        }
