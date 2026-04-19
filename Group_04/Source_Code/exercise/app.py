from flask import Flask, render_template, request, jsonify, session
import cv2
import numpy as np
import base64
from io import BytesIO
from PIL import Image
import uuid
from datetime import datetime
from exercises import ExerciseManager
from face_tracker import FaceTracker
import logging

app = Flask(__name__)
app.secret_key = 'eye-trainer-secret-key-2026'

# Disable only the HTTP request logs, keep startup messages
logging.getLogger('werkzeug').setLevel(logging.WARNING)
logging.getLogger('werkzeug.serving').setLevel(logging.INFO)

# Initialize exercise manager and face tracker
exercise_manager = ExerciseManager()
face_tracker = FaceTracker()

# Store active sessions
active_sessions = {}


@app.route('/')
def index():
    """Main page with list of exercises"""
    return render_template('index.html')


@app.route('/exercise')
def exercise():
    """Exercise session page"""
    return render_template('exercise.html')


@app.route('/api/exercises', methods=['GET'])
def get_exercises():
    """Get list of all available exercises"""
    exercises = exercise_manager.get_all_exercises()
    return jsonify(exercises)


@app.route('/api/exercise/<exercise_id>', methods=['GET'])
def get_exercise_detail(exercise_id):
    """Get details for a specific exercise"""
    exercise = exercise_manager.get_exercise(exercise_id)
    if exercise:
        return jsonify(exercise)
    return jsonify({'error': 'Exercise not found'}), 404


@app.route('/api/session/start', methods=['POST'])
def start_session():
    """Start a new exercise session"""
    try:
        data = request.json
        exercise_id = data.get('exercise_id')
        
        print(f"Starting session for exercise: {exercise_id}")
        
        exercise = exercise_manager.get_exercise(exercise_id)
        if not exercise:
            print(f"Exercise not found: {exercise_id}")
            return jsonify({'error': 'Exercise not found'}), 404
        
        # Create session
        session_id = str(uuid.uuid4())
        
        print(f"Creating tracker for exercise: {exercise_id}")
        tracker = exercise_manager.create_tracker(exercise_id)
        
        if tracker is None:
            print(f"Failed to create tracker for exercise: {exercise_id}")
            return jsonify({'error': 'Failed to create exercise tracker'}), 500
        
        active_sessions[session_id] = {
            'exercise_id': exercise_id,
            'start_time': datetime.now(),
            'reps_completed': 0,
            'frames_processed': 0,
            'accuracy_scores': [],
            'tracker': tracker
        }
        
        print(f"Session created successfully: {session_id}")
        
        return jsonify({
            'session_id': session_id,
            'exercise': exercise
        })
        
    except Exception as e:
        print(f"Error in start_session: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to start session: {str(e)}'}), 500


@app.route('/api/session/process_frame', methods=['POST'])
def process_frame():
    """Process a video frame for exercise tracking"""
    data = request.json
    session_id = data.get('session_id')
    frame_data = data.get('frame')
    
    if session_id not in active_sessions:
        return jsonify({'error': 'Invalid session'}), 400
    
    session = active_sessions[session_id]
    
    try:
        # Decode base64 image
        image_data = base64.b64decode(frame_data.split(',')[1])
        image = Image.open(BytesIO(image_data))
        frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Process frame with face tracker
        landmarks = face_tracker.process_frame(frame)
        
        # Handle no face or poor conditions
        if landmarks is None or landmarks.get('status') != 'success':
            status = landmarks.get('status', 'error') if landmarks else 'no_face'
            message = landmarks.get('message', 'No face detected') if landmarks else 'No face detected'
            lighting_msg = landmarks.get('lighting_message', '') if landmarks else ''
            
            # For palming exercise, no face is actually expected (hands covering face)
            if session['exercise_id'] == 'palming':
                # Pass None to tracker for palming to indicate face is covered
                tracker = session['tracker']
                result = tracker.update(None)
                
                return jsonify({
                    'success': True,
                    'status': 'tracking',
                    'reps': session['reps_completed'],
                    'accuracy': result['accuracy'],
                    'feedback': result['feedback'],
                    'feedback_color': 'success' if result['accuracy'] > 0 else 'info',
                    'progress': result['progress'],
                    'lighting_ok': True,
                    'lighting_message': '',
                    'show_warning': False
                })
            
            # For up-down and rotation exercises, brief face loss is OK (extreme angles)
            if session['exercise_id'] in ['up_down', 'rotation']:
                # Use last known state or neutral gaze
                tracker = session['tracker']
                # Provide neutral landmarks to continue tracking
                neutral_landmarks = {
                    'status': 'success',
                    'gaze_direction': np.array([0.0, 0.0]),
                    'left_eye': np.zeros((6, 2)),
                    'right_eye': np.zeros((6, 2))
                }
                result = tracker.update(neutral_landmarks)
                
                session['frames_processed'] += 1
                
                # Check if rep was completed even without face detection
                if result['rep_completed']:
                    session['reps_completed'] += 1
                    session['accuracy_scores'].append(result['accuracy'])
                
                # Determine feedback color
                feedback_color = 'warning'
                if result['rep_completed']:
                    feedback_color = 'success'
                
                return jsonify({
                    'success': True,
                    'status': 'tracking',
                    'reps': session['reps_completed'],
                    'accuracy': result['accuracy'],
                    'feedback': result['feedback'],
                    'feedback_color': feedback_color,
                    'progress': result['progress'],
                    'lighting_ok': True,
                    'lighting_message': 'Face tracking temporarily lost - normal at extreme angles',
                    'show_warning': False
                })
            
            return jsonify({
                'success': False,
                'status': status,
                'message': message,
                'lighting_message': lighting_msg,
                'reps': session['reps_completed'],
                'show_warning': True
            })
        
        # Check position quality (skip for palming and up_down as they involve extreme positions)
        if session['exercise_id'] not in ['palming', 'up_down'] and not landmarks.get('position_ok', True):
            return jsonify({
                'success': False,
                'status': 'poor_position',
                'message': landmarks.get('position_message', 'Adjust your position'),
                'lighting_message': landmarks.get('lighting_message', ''),
                'reps': session['reps_completed'],
                'show_warning': True
            })
        
        # Update exercise tracker
        tracker = session['tracker']
        result = tracker.update(landmarks)
        
        session['frames_processed'] += 1
        
        if result['rep_completed']:
            session['reps_completed'] += 1
            session['accuracy_scores'].append(result['accuracy'])
            print(f"Rep completed! Total reps: {session['reps_completed']}, Accuracy: {result['accuracy']}")
        
        # Determine feedback color and icon
        feedback_icon = '✓'
        if result['accuracy'] >= 80:
            feedback_color = 'success'
            feedback_icon = '✓'
        elif result['accuracy'] >= 60:
            feedback_color = 'warning'
            feedback_icon = '⚠'
        elif result['accuracy'] > 0:
            feedback_color = 'danger'
            feedback_icon = '✗'
        else:
            feedback_color = 'info'
            feedback_icon = 'ℹ'
        
        return jsonify({
            'success': True,
            'status': 'tracking',
            'reps': session['reps_completed'],
            'accuracy': result['accuracy'],
            'feedback': f"{feedback_icon} {result['feedback']}",
            'feedback_color': feedback_color,
            'progress': result['progress'],
            'lighting_ok': landmarks.get('lighting_ok', True),
            'lighting_message': landmarks.get('lighting_message', ''),
            'show_warning': False
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'error',
            'message': f'Error processing frame: {str(e)}',
            'reps': session.get('reps_completed', 0)
        }), 500


@app.route('/api/session/stop', methods=['POST'])
def stop_session():
    """Stop an exercise session and get summary"""
    data = request.json
    session_id = data.get('session_id')
    
    if session_id not in active_sessions:
        return jsonify({'error': 'Invalid session'}), 400
    
    session = active_sessions[session_id]
    
    # Calculate summary
    duration = (datetime.now() - session['start_time']).total_seconds()
    avg_accuracy = np.mean(session['accuracy_scores']) if session['accuracy_scores'] else 0
    
    # Calculate score (0-100)
    exercise = exercise_manager.get_exercise(session['exercise_id'])
    target_reps = exercise.get('target_reps', 10)
    completion_rate = min(session['reps_completed'] / target_reps, 1.0) * 100
    score = (completion_rate * 0.5 + avg_accuracy * 0.5)
    
    summary = {
        'exercise_name': exercise['name'],
        'duration': round(duration, 1),
        'reps_completed': session['reps_completed'],
        'target_reps': target_reps,
        'avg_accuracy': round(avg_accuracy, 1),
        'score': round(score, 1),
        'frames_processed': session['frames_processed']
    }
    
    # Clean up session
    del active_sessions[session_id]
    
    return jsonify(summary)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
