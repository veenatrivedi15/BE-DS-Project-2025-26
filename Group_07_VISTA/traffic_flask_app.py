from flask import Flask, render_template, jsonify, Response, send_file
import time
import numpy as np
import threading
import random
from datetime import datetime
import cv2
import os
from pathlib import Path

# Import Integrated Traffic Service (replaces yolo_service)
try:
    from integrated_traffic_service import initialize_detector, get_detector, cleanup_detector
    YOLO_AVAILABLE = True
except ImportError as e:
    print(f"Integrated traffic service not available: {e}")
    YOLO_AVAILABLE = False
    # Create dummy functions to prevent errors
    def initialize_detector(): return False
    def get_detector(): return None
    def cleanup_detector(): pass

# Import LLM Description Service (separate from core traffic systems)
try:
    from llm_description_service import initialize_description_service, get_description_service, cleanup_description_service
    LLM_AVAILABLE = True
except ImportError as e:
    print(f"LLM description service not available: {e}")
    LLM_AVAILABLE = False
    # Create dummy functions to prevent errors
    def initialize_description_service(): return False
    def get_description_service(): return None
    def cleanup_description_service(): pass

# Import Meta Controller (decision maker between PPO and LLM emergency control)
try:
    from meta_controller import initialize_meta_controller, get_meta_controller, cleanup_meta_controller, get_meta_decision
    META_CONTROLLER_AVAILABLE = True
except ImportError as e:
    print(f"Meta controller not available: {e}")
    META_CONTROLLER_AVAILABLE = False
    # Create dummy functions to prevent errors
    def initialize_meta_controller(ppo_agent=None): return False
    def get_meta_controller(): return None
    def cleanup_meta_controller(): pass
    def get_meta_decision(traffic_data, current_phase, time_remaining): return None

# Import Pedestrian Controller for pedestrian-aware signal control
try:
    from pedestrian_controller import (
        initialize_pedestrian_controller, 
        get_pedestrian_controller, 
        cleanup_pedestrian_controller,
        get_pedestrian_status,
        # NEW: Event-driven, phase-locked functions
        trigger_pedestrian_phase,
        update_global_phase_timer,
        is_pedestrian_phase_active,
        is_pedestrian_phase_locked,
        has_pending_pedestrian_request,
        get_global_pedestrian_state,
        PHASE_DURATION,
        DEBOUNCE_FRAMES
    )
    PEDESTRIAN_CONTROLLER_AVAILABLE = True
except ImportError as e:
    print(f"Pedestrian controller not available: {e}")
    PEDESTRIAN_CONTROLLER_AVAILABLE = False
    # Create dummy functions to prevent errors
    def initialize_pedestrian_controller(video_path=None): return False
    def get_pedestrian_controller(): return None
    def cleanup_pedestrian_controller(): pass
    def get_pedestrian_status(): return {
        'pedestrian_count': 0,
        'pedestrian_detected': False,
        'pedestrian_request_flag': False,
        'pedestrian_phase_active': False,
        'pedestrian_phase_remaining': 0,
        'vehicle_signals_overridden': False
    }
    def trigger_pedestrian_phase(): return False
    def update_global_phase_timer(): return (False, 0, False)
    def is_pedestrian_phase_active(): return False
    def is_pedestrian_phase_locked(): return False
    def has_pending_pedestrian_request(): return False
    def get_global_pedestrian_state(): return {'phase_active': False, 'phase_remaining': 0}
    PHASE_DURATION = 20
    DEBOUNCE_FRAMES = 3

app = Flask(__name__)

# --- Configuration ---
USE_YOLO = True
yolo_detector = None
USE_LLM_DESCRIPTIONS = True
llm_service = None
USE_META_CONTROLLER = True
meta_controller = None
USE_PEDESTRIAN_CONTROLLER = True
pedestrian_controller = None
PEDESTRIAN_PHASE_DURATION = 20
TOTAL_CYCLE_DURATION = 120

@app.route('/toggle_yolo')
def toggle_yolo():
    """Toggle between YOLO and dummy data mode"""
    global USE_YOLO, yolo_detector
    try:
        if USE_YOLO:
            # Switch to dummy mode
            if yolo_detector:
                cleanup_detector()
            USE_YOLO = False
            mode = 'dummy'
            message = 'Switched to dummy data mode'
        else:
            # Switch to traffic detection mode
            if initialize_detector():
                yolo_detector = get_detector()
                USE_YOLO = True
                mode = 'integrated'
                message = 'Switched to Integrated Traffic Detection mode'
            else:
                mode = 'dummy'
                message = 'Failed to initialize Traffic Detection - staying in dummy mode'
        
        return jsonify({
            'success': True,
            'mode': mode,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'mode': 'dummy' if not USE_YOLO else 'yolo'
        })

# --- Traffic Configuration ---
DIRS = ["North", "South", "East", "West"]
ABBR = {"North":"N","South":"S","East":"E","West":"W"}
YELLOW_DURATION = 3

PHASE_NAMES = [
    "North-South Through",
    "North-South Left",  
    "East-West Through",
    "East-West Left"
]

PHASES = [
    {"name":"Phase 1", "movements":"North ↔ South through + Right turns",
     "arrows":{"North":"↑", "South":"↓", "East":"—", "West":"—"}},
    {"name":"Phase 2", "movements":"North ↔ South Left turns",
     "arrows":{"North":"←", "South":"←", "East":"—", "West":"—"}},
    {"name":"Phase 3", "movements":"East ↔ West through + Right turns",
     "arrows":{"North":"—", "South":"—", "East":"→", "West":"←"}},
    {"name":"Phase 4", "movements":"East ↔ West Left turns",
     "arrows":{"North":"—", "South":"—", "East":"←", "West":"→"}},
]

# --- Global State (will be initialized after function definitions) ---
traffic_state = {
    'current_phase': 0,
    'phase_time_remaining': 30,
    'phase_start_time': time.time(),
    'vehicle_counts': {},  # Will be initialized later
    'ppo_decision': {
        'recommended_phase': 0,
        'recommended_duration': 30,
        'confidence': 0.5,
        'reasoning': 'System initializing...',
        'decision_mode': 'initialization'
    },
    'simulation_log': [
        {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'type': 'system',
            'message': '🚦 Traffic Control System initialized successfully',
            'technical_details': 'System startup • Phase 1 • Normal operation',
        }
    ],
    'phase_status': 'GREEN',
    'total_vehicles_served': 0,
    'emergency_status': {},
    'traffic_summary': None,
    # Cycle-based pedestrian crossing state (120s cycle)
    'cycle_start_time': time.time(),
    'cycle_elapsed': 0,
    'pedestrian_request': False,
    'pedestrian_request_time': None,
    'pedestrian_phase_executed': False,
    # Pedestrian phase state
    'pedestrian_status': {
        'pedestrian_count': 0,
        'pedestrian_detected': False,
        'pedestrian_request_flag': False,
        'pedestrian_phase_active': False,
        'pedestrian_phase_remaining': 0,
        'vehicle_signals_overridden': False,
        'cycle_position': 'VEHICLE_PHASE',  # VEHICLE_PHASE or PEDESTRIAN_WINDOW
        'request_queued': False
    }
}

# --- Traffic Logic Functions ---
def get_traffic_counts():
    """Get traffic counts from Integrated Traffic Detector or generate dummy data"""
    global yolo_detector
    
    if USE_YOLO and yolo_detector and yolo_detector.is_healthy():
        # Get real data from Integrated Traffic Detector
        try:
            traffic_summary = yolo_detector.get_traffic_summary()
            return traffic_summary['ppo_format'], traffic_summary
        except Exception as e:
            print(f"Error getting traffic detection data: {e}")
            # Fall back to dummy data
            return generate_realistic_counts(), None
    else:
        # Use dummy data
        return generate_realistic_counts(), None

def generate_realistic_counts():
    """Generate more realistic traffic patterns"""
    base_counts = {}
    hour = datetime.now().hour
    
    # Rush hour patterns
    if 7 <= hour <= 9 or 17 <= hour <= 19:  # Rush hours
        multiplier = 1.5
    elif 22 <= hour or hour <= 6:  # Night time
        multiplier = 0.3
    else:  # Regular hours
        multiplier = 1.0
    
    for d in DIRS:
        for m in ["L", "S", "R"]:
            base = np.random.randint(2, 12)
            counts = int(base * multiplier * np.random.uniform(0.7, 1.3))
            base_counts[f"{ABBR[d]}_{m}"] = max(0, counts)
    
    return base_counts

# Initialize traffic state with realistic counts now that function is defined
if not traffic_state['vehicle_counts']:
    traffic_state['vehicle_counts'] = generate_realistic_counts()

def create_traffic_state_for_ppo(counts):
    """Convert vehicle counts into proper state format for PPO agent"""
    # Create exactly the shape expected: (1, 12, 5) for batch processing
    traffic_state = np.zeros((1, 12, 5), dtype=np.float32)
    
    lane_idx = 0
    for d in DIRS:
        for m in ["L", "S", "R"]:
            count = counts[f"{ABBR[d]}_{m}"]
            traffic_state[0, lane_idx, 0] = count  # Raw count
            traffic_state[0, lane_idx, 1] = min(count / 10.0, 1.0)  # Normalized density
            traffic_state[0, lane_idx, 2] = 1.0 if count > 5 else 0.0  # High density flag
            traffic_state[0, lane_idx, 3] = 1.0 if count > 8 else 0.0  # Critical density flag
            traffic_state[0, lane_idx, 4] = count / max(sum(counts.values()), 1)  # Relative density
            lane_idx += 1
    
    return traffic_state

def create_phase_state_for_ppo(current_phase, time_remaining):
    """Create phase state vector for PPO agent"""
    # Create exactly the shape expected: (1, 8) for batch processing
    phase_state = np.zeros((1, 8), dtype=np.float32)
    
    # One-hot encode current phase
    if 0 <= current_phase < 8:
        phase_state[0, current_phase] = 1.0
    
    # Could add more phase-related features here if needed
    # For now, keeping it simple with just one-hot encoding
    
    return phase_state

def calculate_phase_benefit(phase_idx, counts):
    """Calculate traffic benefit score for a given phase"""
    if phase_idx >= len(PHASES):
        return 0
        
    phase = PHASES[phase_idx % len(PHASES)]
    benefit = 0
    
    for direction, arrow in phase["arrows"].items():
        if arrow != "—":  # If direction has green light
            abbr = ABBR[direction]
            if arrow in ["↑", "↓"]:  # Straight traffic
                benefit += counts[f"{abbr}_S"] * 2
            elif arrow in ["←", "→"]:  # Turn traffic
                benefit += counts[f"{abbr}_L"] + counts[f"{abbr}_R"]
    
    return benefit

# --- PPO Agent Integration ---
agent = None
try:
    from ppo_agent import PPOAgent
    
    # Define the state shape for PPO agent (exactly as expected by the constructor)
    state_shape = [(12, 5), (8,)]  # [traffic_state_shape, phase_state_shape]
    phase_dim = 8  # Number of possible phases
    
    # Initialize PPO agent with correct parameters
    agent = PPOAgent(state_shape=state_shape, phase_dim=phase_dim)
    
    # Try to load the trained weights
    try:
        agent.actor.load_weights('models/ppo_actor.weights.h5')
        agent.critic.load_weights('models/ppo_critic.weights.h5')
        print("[INFO] ✅ PPO agent and weights loaded successfully!")
    except Exception as weight_error:
        print(f"[WARNING] PPO agent loaded but weights failed: {weight_error}")
        print("[INFO] Using untrained PPO agent - will use random initialization")
    
    # Initialize Meta Controller with PPO agent - MOVED TO MAIN BLOCK
        
except ImportError as e:
    print(f"[WARNING] Could not import PPO agent: {e}")
    print("[INFO] Falling back to rule-based traffic control")
except Exception as e:
    print(f"[WARNING] Could not load PPO agent: {e}")
    print("[INFO] Falling back to rule-based traffic control")

def get_ppo_decision(counts, current_phase, time_remaining):
    """Get decision from PPO agent"""
    if agent is None:
        # Fallback decision - choose phase with highest benefit
        best_phase = current_phase
        best_benefit = calculate_phase_benefit(current_phase, counts)
        
        for phase in range(min(4, len(PHASES))):  # Only check first 4 phases
            benefit = calculate_phase_benefit(phase, counts)
            if benefit > best_benefit:
                best_benefit = benefit
                best_phase = phase
        
        total_vehicles = sum(counts.values())
        duration = min(max(15, total_vehicles // 2), 45)
        
        return {
            'recommended_phase': best_phase,
            'recommended_duration': duration,
            'state_value': 0.5,
            'confidence': 0.7,
            'reasoning': f'Fallback logic: Phase {best_phase + 1} serves {best_benefit} vehicles'
        }
    
    try:
        # Create state inputs in the exact format PPO agent expects
        traffic_state_input = create_traffic_state_for_ppo(counts)
        phase_state_input = create_phase_state_for_ppo(current_phase, time_remaining)
        
        # Pass state as list [traffic_state, phase_state]
        state = [traffic_state_input, phase_state_input]
        
        # Get action from PPO agent
        phase_action, duration, state_value, logp_phase, logp_duration = agent.get_action(state)
        
        # Ensure phase is within valid range (0-3 for 4 phases)
        phase_action = max(0, min(phase_action, 3))
        
        # Calculate confidence from log probability (clip to reasonable range)
        raw_confidence = np.exp(logp_phase)
        # Map very small values to a reasonable range (0.3 to 0.9)
        confidence = max(0.3, min(0.9, raw_confidence * 100)) if raw_confidence < 0.01 else min(1.0, max(0.0, raw_confidence))
        
        return {
            'recommended_phase': int(phase_action),
            'recommended_duration': int(duration),
            'state_value': float(state_value),
            'confidence': float(confidence),
            'reasoning': f'PPO analysis: {sum(counts.values())} vehicles, conf={confidence:.3f}'
        }
        
    except Exception as e:
        # Fallback if PPO fails
        print(f"PPO Error: {e}")
        best_phase = 0
        total_vehicles = sum(counts.values())
        for phase in range(min(4, len(PHASES))):
            if calculate_phase_benefit(phase, counts) > calculate_phase_benefit(best_phase, counts):
                best_phase = phase
        
        return {
            'recommended_phase': best_phase,
            'recommended_duration': 25,
            'state_value': 0.0,
            'confidence': 0.3,
            'reasoning': f'PPO error fallback: {str(e)[:50]}...'
        }

# --- Traffic Simulation Thread ---
def traffic_simulation():
    """Main traffic simulation loop with cycle-based pedestrian execution"""
    global traffic_state, yolo_detector, pedestrian_controller
    
    # Wait a moment for initialization
    time.sleep(2)
    
    # Initialize pedestrian controller if available
    if USE_PEDESTRIAN_CONTROLLER and PEDESTRIAN_CONTROLLER_AVAILABLE:
        try:
            print("[INFO] 🚶 Initializing Pedestrian Controller...")
            if initialize_pedestrian_controller(video_path="videos/v6.mp4"):
                pedestrian_controller = get_pedestrian_controller()
                print("[INFO] ✅ Pedestrian Controller initialized successfully!")
            else:
                print("[WARNING] Pedestrian Controller initialization failed")
        except Exception as e:
            print(f"[ERROR] Pedestrian Controller setup failed: {e}")
    
    # Initialize cycle timing
    traffic_state['cycle_start_time'] = time.time()
    
    while True:
        try:
            # ============================================
            # CYCLE TIMING CALCULATION (120s cycle)
            # ============================================
            current_time = time.time()
            cycle_elapsed = current_time - traffic_state['cycle_start_time']
            traffic_state['cycle_elapsed'] = cycle_elapsed
            
            # Determine cycle position
            # First 100 seconds = Vehicle-only phase
            # Last 20 seconds (100-120) = Pedestrian window
            VEHICLE_PHASE_DURATION = 100  # seconds
            PEDESTRIAN_WINDOW_START = 100  # seconds
            CYCLE_DURATION = 120  # seconds
            
            in_pedestrian_window = (cycle_elapsed >= PEDESTRIAN_WINDOW_START and cycle_elapsed < CYCLE_DURATION)
            
            # ============================================
            # PEDESTRIAN DETECTION (Continuous monitoring)
            # ============================================
            if USE_PEDESTRIAN_CONTROLLER and PEDESTRIAN_CONTROLLER_AVAILABLE and pedestrian_controller:
                ped_status = get_pedestrian_status()
                pedestrian_detected = ped_status.get('pedestrian_detected', False)
                pedestrian_count = ped_status.get('pedestrian_count', 0)
                
                # Register pedestrian request if detected during vehicle phase
                if pedestrian_detected and not in_pedestrian_window:
                    if not traffic_state['pedestrian_request']:
                        traffic_state['pedestrian_request'] = True
                        traffic_state['pedestrian_request_time'] = current_time
                        print(f"🚶 PEDESTRIAN DETECTED at t={int(cycle_elapsed)}s - Request queued for pedestrian window (t=100s)")
                        
                        # Update status
                        traffic_state['pedestrian_status']['request_queued'] = True
                        traffic_state['pedestrian_status']['cycle_position'] = 'VEHICLE_PHASE'
                        
                        # Log request
                        log_entry = create_human_friendly_log_entry('pedestrian_detected', {
                            'pedestrian_count': pedestrian_count,
                            'cycle_time': int(cycle_elapsed),
                            'queued': True
                        })
                        traffic_state['simulation_log'].append(log_entry)
            
            # ============================================
            # PEDESTRIAN PHASE EXECUTION (Time-gated)
            # ============================================
            if in_pedestrian_window:
                traffic_state['pedestrian_status']['cycle_position'] = 'PEDESTRIAN_WINDOW'
                
                # Calculate remaining time in pedestrian window
                pedestrian_window_elapsed = cycle_elapsed - PEDESTRIAN_WINDOW_START
                pedestrian_remaining = PEDESTRIAN_PHASE_DURATION - pedestrian_window_elapsed
                
                # Check if we should execute pedestrian phase
                if traffic_state['pedestrian_request'] and not traffic_state['pedestrian_phase_executed']:
                    # EXECUTE PEDESTRIAN PHASE
                    traffic_state['pedestrian_phase_executed'] = True
                    traffic_state['pedestrian_status']['pedestrian_phase_active'] = True
                    traffic_state['pedestrian_status']['vehicle_signals_overridden'] = True
                    
                    # Update remaining time
                    traffic_state['pedestrian_status']['pedestrian_phase_remaining'] = max(0, pedestrian_remaining)
                    
                    # Turn all vehicle signals RED
                    traffic_state['phase_status'] = 'RED'
                    
                    # Log only once
                    if not hasattr(traffic_simulation, '_ped_phase_logged'):
                        print(f"🚶 PEDESTRIAN PHASE ACTIVE at t={int(cycle_elapsed)}s - All vehicle signals RED for {PEDESTRIAN_PHASE_DURATION}s")
                        traffic_simulation._ped_phase_logged = True
                        
                        log_entry = create_human_friendly_log_entry('pedestrian_phase_started', {
                            'pedestrian_count': traffic_state['pedestrian_status'].get('pedestrian_count', 0),
                            'duration': PEDESTRIAN_PHASE_DURATION,
                            'cycle_time': int(cycle_elapsed)
                        })
                        traffic_state['simulation_log'].append(log_entry)
                    
                    # Update countdown every second
                    if int(pedestrian_remaining) != getattr(traffic_simulation, '_last_countdown', -1):
                        traffic_simulation._last_countdown = int(pedestrian_remaining)
                        if int(pedestrian_remaining) % 5 == 0 and int(pedestrian_remaining) > 0:
                            print(f"🚶 PEDESTRIAN CROSSING: {int(pedestrian_remaining)}s remaining")
                
                elif traffic_state['pedestrian_phase_executed']:
                    # CONTINUE UPDATING countdown during active phase
                    traffic_state['pedestrian_status']['pedestrian_phase_remaining'] = max(0, pedestrian_remaining)
                    
                    # Update countdown every second
                    if int(pedestrian_remaining) != getattr(traffic_simulation, '_last_countdown', -1):
                        traffic_simulation._last_countdown = int(pedestrian_remaining)
                        if int(pedestrian_remaining) % 5 == 0 and int(pedestrian_remaining) > 0:
                            print(f"🚶 PEDESTRIAN CROSSING: {int(pedestrian_remaining)}s remaining")
                
                elif not traffic_state['pedestrian_request'] and not hasattr(traffic_simulation, '_skip_logged'):
                    # NO REQUEST - Skip pedestrian phase
                    print(f"🚶 PEDESTRIAN PHASE SKIPPED at t={int(cycle_elapsed)}s - No active request")
                    traffic_simulation._skip_logged = True
                    
                    log_entry = {
                        'timestamp': datetime.now().strftime('%H:%M:%S'),
                        'type': 'pedestrian_skipped',
                        'message': 'Pedestrian phase skipped - no pending requests',
                        'technical_details': f'Cycle time: {int(cycle_elapsed)}s • No pedestrian detected in this cycle'
                    }
                    traffic_state['simulation_log'].append(log_entry)
            
            # ============================================
            # CYCLE RESET (After 120 seconds)
            # ============================================
            if cycle_elapsed >= CYCLE_DURATION:
                print(f"🔄 CYCLE COMPLETE at t={int(cycle_elapsed)}s - Starting new 120s cycle")
                
                # Reset cycle
                traffic_state['cycle_start_time'] = time.time()
                traffic_state['cycle_elapsed'] = 0
                traffic_state['pedestrian_request'] = False
                traffic_state['pedestrian_request_time'] = None
                traffic_state['pedestrian_phase_executed'] = False
                
                # Reset pedestrian status
                traffic_state['pedestrian_status']['pedestrian_phase_active'] = False
                traffic_state['pedestrian_status']['vehicle_signals_overridden'] = False
                traffic_state['pedestrian_status']['pedestrian_phase_remaining'] = 0
                traffic_state['pedestrian_status']['cycle_position'] = 'VEHICLE_PHASE'
                traffic_state['pedestrian_status']['request_queued'] = False
                
                # Clear logging flags
                if hasattr(traffic_simulation, '_ped_phase_logged'):
                    delattr(traffic_simulation, '_ped_phase_logged')
                if hasattr(traffic_simulation, '_skip_logged'):
                    delattr(traffic_simulation, '_skip_logged')
                if hasattr(traffic_simulation, '_last_countdown'):
                    delattr(traffic_simulation, '_last_countdown')
                
                log_entry = {
                    'timestamp': datetime.now().strftime('%H:%M:%S'),
                    'type': 'cycle_reset',
                    'message': '🔄 New traffic cycle started - 120 second cycle initialized',
                    'technical_details': 'Cycle reset • Vehicle phase active • Pedestrian requests cleared'
                }
                traffic_state['simulation_log'].append(log_entry)
            
            # ============================================
            # NORMAL TRAFFIC OPERATIONS (Vehicle phases)
            # ============================================
            # Get traffic counts from Integrated Traffic Detector or dummy data
            counts, traffic_summary = get_traffic_counts()
            traffic_state['vehicle_counts'] = counts
            
            # Store emergency status if available from Traffic Detector
            if traffic_summary:
                traffic_state['emergency_status'] = traffic_summary.get('emergency_status', {})
                traffic_state['traffic_summary'] = traffic_summary
            
            # Calculate time remaining in current phase
            elapsed = time.time() - traffic_state['phase_start_time']
            time_remaining = max(0, traffic_state['phase_time_remaining'] - elapsed)
            
            # Update pedestrian status for API
            if USE_PEDESTRIAN_CONTROLLER and PEDESTRIAN_CONTROLLER_AVAILABLE and pedestrian_controller:
                ped_status = get_pedestrian_status()
                # Merge with cycle-based status
                traffic_state['pedestrian_status'].update({
                    'pedestrian_count': ped_status.get('pedestrian_count', 0),
                    'pedestrian_detected': ped_status.get('pedestrian_detected', False)
                })
            
            # Get decision from Meta Controller
            if USE_META_CONTROLLER and meta_controller:
                # Create traffic data package for meta controller
                # Only signal pedestrian mode when actually in pedestrian window (T>=100s) and phase is active
                # Don't send queued requests during vehicle phase to avoid premature fallback mode
                traffic_data = {
                    'vehicle_counts': counts,
                    'emergency_status': traffic_summary.get('emergency_status', {}) if traffic_summary else {},
                    'emergency_counts': {},  # Add emergency counts
                    'current_phase': traffic_state['current_phase'],
                    'time_remaining': time_remaining,
                    'pedestrian_status': {
                        'pedestrian_phase_active': traffic_state['pedestrian_status']['pedestrian_phase_active'],
                        'pedestrian_phase_remaining': traffic_state['pedestrian_status']['pedestrian_phase_remaining'],
                        'vehicle_signals_overridden': traffic_state['pedestrian_status']['vehicle_signals_overridden'],
                        # Don't include detection/request flags that trigger premature mode switch
                        'pedestrian_count': traffic_state['pedestrian_status'].get('pedestrian_count', 0),
                        'pedestrian_detected': False,  # Don't signal detection during vehicle phase
                        'pedestrian_request_flag': False
                    },
                    'cycle_elapsed': traffic_state['cycle_elapsed'],
                    'pedestrian_request': False  # Don't signal request during vehicle phase to avoid fallback mode
                }
                
                # Add emergency counts to traffic data
                if traffic_summary and traffic_summary.get('emergency_status', {}):
                    emergency_status = traffic_summary['emergency_status']
                    ambulance_counts = emergency_status.get('ambulance_counts', [0, 0, 0, 0])
                    for i, direction in enumerate(["North", "South", "East", "West"]):
                        abbr = {"North":"N","South":"S","East":"E","West":"W"}[direction]
                        traffic_data['emergency_counts'][f"{abbr}_E"] = ambulance_counts[i] if i < len(ambulance_counts) else 0
                
                # Get meta controller decision
                meta_decision = get_meta_decision(traffic_data, traffic_state['current_phase'], time_remaining)
                traffic_state['ppo_decision'] = meta_decision
                traffic_state['meta_decision'] = meta_decision
                
                # Log mode changes
                current_mode = meta_decision.get('current_mode')
                last_mode = getattr(traffic_simulation, '_last_mode_logged', None)
                
                if current_mode != last_mode:
                    traffic_simulation._last_mode_logged = current_mode
                    
            else:
                # Fallback to direct PPO decision
                ppo_decision = get_ppo_decision(counts, traffic_state['current_phase'], time_remaining)
                traffic_state['ppo_decision'] = ppo_decision
            
            # Emergency override: force immediate phase change if emergency vehicle detected
            if traffic_summary and traffic_summary.get('emergency_status', {}).get('emergency_detected', False):
                if time_remaining > 5:
                    traffic_state['phase_time_remaining'] = 5
            
            # Determine current phase status based on time remaining
            if time_remaining > YELLOW_DURATION:
                traffic_state['phase_status'] = 'GREEN'
            elif time_remaining > 0:
                traffic_state['phase_status'] = 'YELLOW'  
            else:
                traffic_state['phase_status'] = 'RED'
            
            # Only change phase when current phase is completely finished
            if time_remaining <= 0:
                # Get recommendation for NEXT phase from Meta Controller
                if USE_META_CONTROLLER and meta_controller:
                    # Create traffic data for next phase decision
                    next_traffic_data = {
                        'vehicle_counts': counts,
                        'emergency_status': traffic_summary.get('emergency_status', {}) if traffic_summary else {},
                        'current_phase': traffic_state['current_phase'],
                        'time_remaining': 0
                    }
                    next_decision = get_meta_decision(next_traffic_data, traffic_state['current_phase'], 0)
                else:
                    next_decision = get_ppo_decision(counts, traffic_state['current_phase'], 0)
                
                # Log the completed phase
                completion_data = {
                    'completed_phase': traffic_state['current_phase'],
                    'completed_duration': int(elapsed),
                    'total_vehicles': sum(counts.values())
                }
                log_entry = create_human_friendly_log_entry('phase_completed', completion_data)
                traffic_state['simulation_log'].append(log_entry)
                
                # Start new phase
                new_phase = next_decision['recommended_phase']
                new_duration = max(15, min(next_decision['recommended_duration'], 60))
                
                # Update to new phase
                traffic_state['current_phase'] = new_phase
                traffic_state['phase_time_remaining'] = new_duration
                traffic_state['phase_start_time'] = time.time()
                traffic_state['phase_status'] = 'GREEN'
                
                # Log the new phase start
                start_data = {
                    'new_phase': new_phase,
                    'duration': new_duration,
                    'total_vehicles': sum(counts.values()),
                    'reasoning': next_decision['reasoning'],
                    'decision_mode': next_decision.get('decision_mode', 'unknown'),
                    'emergency_override': next_decision.get('emergency_override', False)
                }
                log_entry = create_human_friendly_log_entry('phase_started', start_data)
                traffic_state['simulation_log'].append(log_entry)
            
            # Calculate vehicles served
            if traffic_state['phase_status'] == 'GREEN':
                vehicles_served = calculate_phase_benefit(traffic_state['current_phase'], counts)
                traffic_state['total_vehicles_served'] += vehicles_served * 0.1
            
            # Keep only last 15 log entries
            if len(traffic_state['simulation_log']) > 15:
                traffic_state['simulation_log'] = traffic_state['simulation_log'][-15:]
            
            time.sleep(1)
            
        except Exception as e:
            print(f"Simulation error: {e}")
            time.sleep(2)

# --- Flask Routes ---
@app.route('/')
def index():
    return render_template('traffic_dashboard.html')

@app.route('/api/traffic_status')
def get_traffic_status():
    """Main API endpoint for traffic status"""
    try:
        # Get current state
        current_time = time.time()
        elapsed_time = current_time - traffic_state.get('phase_start_time', current_time)
        time_remaining = max(0, int(traffic_state.get('phase_time_remaining', 30) - elapsed_time))
        
        # Show next phase recommendation when current phase is almost done
        next_phase_info = ""
        if time_remaining <= 5 and traffic_state.get('ppo_decision'):
            ppo_decision = traffic_state['ppo_decision']
            if isinstance(ppo_decision, dict) and 'recommended_phase' in ppo_decision:
                next_phase_info = f" → Next: Phase {ppo_decision['recommended_phase'] + 1} ({ppo_decision.get('recommended_duration', 30)}s)"
        
        # Get detailed phase data for each direction
        current_phase = traffic_state.get('current_phase', 0)
        phase_status = traffic_state.get('phase_status', 'GREEN')
        
        phase_data = get_detailed_phase_data(current_phase, phase_status, time_remaining)
        
        # Prepare emergency vehicle counts
        emergency_counts = {}
        if 'traffic_summary' in traffic_state and traffic_state['traffic_summary']:
            emergency_status = traffic_state['traffic_summary'].get('emergency_status', {})
            ambulance_counts = emergency_status.get('ambulance_counts', [0, 0, 0, 0])
            for i, direction in enumerate(DIRS):
                emergency_counts[f"{ABBR[direction]}_E"] = ambulance_counts[i] if i < len(ambulance_counts) else 0
        else:
            for direction in DIRS:
                emergency_counts[f"{ABBR[direction]}_E"] = 0

        # Get pedestrian status
        ped_status = traffic_state.get('pedestrian_status', {})
        is_pedestrian_phase = ped_status.get('pedestrian_phase_active', False)

        # Add meta controller information
        meta_controller_info = {}
        if USE_META_CONTROLLER and 'meta_decision' in traffic_state:
            meta_decision = traffic_state.get('meta_decision', {})
            
            # Override current_mode if pedestrian phase is active
            current_mode = meta_decision.get('current_mode', 'normal')
            decision_mode = meta_decision.get('decision_mode', 'ppo_agent')
            
            if is_pedestrian_phase:
                current_mode = 'pedestrian'
                decision_mode = 'pedestrian_phase'
            
            meta_controller_info = {
                'active': True,
                'current_mode': current_mode,
                'decision_mode': decision_mode,
                'emergency_override': meta_decision.get('emergency_override', False),
                'pedestrian_override': is_pedestrian_phase,
                'emergency_severity': meta_decision.get('emergency_severity', 0.0),
                'confidence': meta_decision.get('confidence', 0.0)
            }
        else:
            ppo_decision = traffic_state.get('ppo_decision', {})
            
            current_mode = 'direct_ppo'
            decision_mode = 'ppo_agent'
            
            if is_pedestrian_phase:
                current_mode = 'pedestrian'
                decision_mode = 'pedestrian_phase'
            
            meta_controller_info = {
                'active': False,
                'current_mode': current_mode,
                'decision_mode': decision_mode,
                'emergency_override': False,
                'pedestrian_override': is_pedestrian_phase,
                'emergency_severity': 0.0,
                'confidence': ppo_decision.get('confidence', 0.0) if isinstance(ppo_decision, dict) else 0.0
            }

        # Safe access to phase name
        if is_pedestrian_phase:
            phase_name = "🚶 Pedestrian Crossing Phase"
        elif current_phase < len(PHASE_NAMES):
            phase_name = PHASE_NAMES[current_phase] + next_phase_info
        else:
            phase_name = f"Phase {current_phase + 1}" + next_phase_info

        # Prepare response with safe defaults
        response_data = {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'current_phase': current_phase,
            'time_remaining': time_remaining,
            'elapsed_time': int(elapsed_time),
            'total_phase_duration': traffic_state.get('phase_time_remaining', 30),
            'phase_status': phase_status,
            'phase_name': phase_name,
            'phase_movements': get_phase_movements_text(current_phase),
            'phase_data': phase_data,
            'vehicle_counts': traffic_state.get('vehicle_counts', {}),
            'emergency_counts': emergency_counts,
            'emergency_status': traffic_state.get('emergency_status', {}),
            'total_vehicles_served': int(traffic_state.get('total_vehicles_served', 0)),
            'ppo_decision': traffic_state.get('ppo_decision', {}),
            'meta_controller': meta_controller_info,
            'simulation_log': traffic_state.get('simulation_log', [])[-10:],
            'system_status': 'ACTIVE',
            'cycle_elapsed': traffic_state.get('cycle_elapsed', 0),
            'cycle_duration': TOTAL_CYCLE_DURATION,
            'pedestrian_request': traffic_state.get('pedestrian_request', False),
            'pedestrian_status': traffic_state.get('pedestrian_status', {
                'pedestrian_count': 0,
                'pedestrian_detected': False,
                'pedestrian_request_flag': False,
                'pedestrian_phase_active': False,
                'pedestrian_phase_remaining': 0,
                'vehicle_signals_overridden': False,
                'cycle_position': 'VEHICLE_PHASE',
                'request_queued': False
            })
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"ERROR in traffic_status API: {e}")
        
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'current_phase': 0,
            'time_remaining': 0,
            'phase_status': 'GREEN',
            'phase_data': get_detailed_phase_data(0, 'GREEN', 30),
            'vehicle_counts': generate_realistic_counts(),
            'emergency_counts': {'N_E': 0, 'S_E': 0, 'E_E': 0, 'W_E': 0},
            'emergency_status': {},
            'total_vehicles_served': 0,
            'ppo_decision': {
                'recommended_phase': 0,
                'recommended_duration': 30,
                'confidence': 0.5,
                'reasoning': 'API Error - using fallback values'
            },
            'meta_controller': {
                'active': False,
                'current_mode': 'error_fallback',
                'decision_mode': 'error_fallback',
                'emergency_override': False,
                'emergency_severity': 0.0,
                'confidence': 0.0
            },
            'simulation_log': [],
            'system_status': 'ERROR'
        })

@app.route('/api/pedestrian_status')
def get_pedestrian_status_api():
    """Dedicated API endpoint for pedestrian detection status"""
    try:
        ped_status = traffic_state.get('pedestrian_status', {})
        
        return jsonify({
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'pedestrian_controller_enabled': USE_PEDESTRIAN_CONTROLLER,
            'pedestrian_controller_available': PEDESTRIAN_CONTROLLER_AVAILABLE,
            'pedestrian_count': ped_status.get('pedestrian_count', 0),
            'pedestrian_detected': ped_status.get('pedestrian_detected', False),
            'pedestrian_request_flag': ped_status.get('pedestrian_request_flag', False),
            'pedestrian_phase_active': ped_status.get('pedestrian_phase_active', False),
            'pedestrian_phase_remaining': ped_status.get('pedestrian_phase_remaining', 0),
            'vehicle_signals_overridden': ped_status.get('vehicle_signals_overridden', False),
            'persistence_buffer': ped_status.get('persistence_buffer', 5),
            'phase_duration': ped_status.get('phase_duration', PEDESTRIAN_PHASE_DURATION),
            'total_cycle_duration': TOTAL_CYCLE_DURATION
        })
        
    except Exception as e:
        print(f"ERROR in pedestrian_status API: {e}")
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'pedestrian_controller_enabled': False,
            'pedestrian_count': 0,
            'pedestrian_phase_active': False
        })

@app.route('/api/traffic_descriptions')
def get_traffic_descriptions():
    """Dedicated API endpoint for LLM-generated traffic descriptions"""
    global llm_service
    
    try:
        if not USE_LLM_DESCRIPTIONS or not llm_service:
            return jsonify({
                'camera_descriptions': [
                    "LLM service not available - using basic traffic monitoring",
                    "LLM service not available - using basic traffic monitoring", 
                    "LLM service not available - using basic traffic monitoring",
                    "LLM service not available - using basic traffic monitoring"
                ],
                'overall_summary': "LLM description service is not available. Using standard traffic control.",
                'timestamp': datetime.now().isoformat(),
                'llm_available': False
            })
        
        # Prepare traffic data for LLM (same format as traffic_status)
        current_time = time.time()
        elapsed_time = current_time - traffic_state['phase_start_time']
        time_remaining = max(0, int(traffic_state['phase_time_remaining'] - elapsed_time))
        
        # Get phase data
        phase_data = get_detailed_phase_data(
            traffic_state['current_phase'], 
            traffic_state['phase_status'], 
            time_remaining
        )
        emergency_counts = prepare_emergency_counts()
        
        # Traffic data for LLM
        traffic_data = {
            'current_phase': traffic_state['current_phase'],
            'time_remaining': time_remaining,
            'phase_status': traffic_state['phase_status'],
            'phase_data': phase_data,
            'vehicle_counts': traffic_state['vehicle_counts'],
            'emergency_counts': emergency_counts,
            'emergency_status': traffic_state.get('emergency_status', {}),
            'total_vehicles_served': int(traffic_state['total_vehicles_served']),
            'ppo_decision': traffic_state['ppo_decision']
        }
        
        # Get descriptions from LLM service
        descriptions = llm_service.get_descriptions(traffic_data)
        
        return jsonify({
            'camera_descriptions': descriptions['camera_descriptions'],
            'overall_summary': descriptions['overall_summary'],
            'timestamp': datetime.now().isoformat(),
            'llm_available': True,
            'last_update': descriptions['last_update']
        })
        
    except Exception as e:
        return jsonify({
            'camera_descriptions': [
                f"Error generating description: {str(e)[:50]}...",
                f"Error generating description: {str(e)[:50]}...",
                f"Error generating description: {str(e)[:50]}...",
                f"Error generating description: {str(e)[:50]}..."
            ],
            'overall_summary': f"Error in LLM service: {str(e)}",
            'timestamp': datetime.now().isoformat(),
            'llm_available': False,
            'error': str(e)
        })

def prepare_emergency_counts():
    """Helper to prepare emergency counts from traffic summary"""
    emergency_counts = {}
    if traffic_state.get('traffic_summary'):
        ambulance_counts = traffic_state['traffic_summary'].get('emergency_status', {}).get('ambulance_counts', [0, 0, 0, 0])
        for i, direction in enumerate(DIRS):
            emergency_counts[f"{ABBR[direction]}_E"] = ambulance_counts[i] if i < len(ambulance_counts) else 0
    else:
        for direction in DIRS:
            emergency_counts[f"{ABBR[direction]}_E"] = 0
    return emergency_counts

@app.route('/api/meta_controller_status')
def get_meta_controller_status():
    """API endpoint for meta controller status and recent decisions"""
    global meta_controller
    
    try:
        if not USE_META_CONTROLLER or not meta_controller:
            return jsonify({
                'error': 'Meta controller not available',
                'active': False,
                'timestamp': datetime.now().isoformat()
            })
        
        # Get meta controller status
        status = meta_controller.get_status()
        recent_decisions = meta_controller.get_recent_decisions(10)
        
        # Add current decision info if available
        current_decision = traffic_state.get('meta_decision', {})
        
        return jsonify({
            'active': True,
            'status': status,
            'recent_decisions': recent_decisions,
            'current_decision': {
                'mode': current_decision.get('current_mode', 'unknown'),
                'decision_mode': current_decision.get('decision_mode', 'unknown'),
                'emergency_override': current_decision.get('emergency_override', False),
                'confidence': current_decision.get('confidence', 0.0),
                'reasoning': current_decision.get('reasoning', 'No current decision')
            },
            'configuration': {
                'emergency_threshold': status.get('emergency_threshold', 1),
                'emergency_phase_extension': status.get('emergency_phase_extension', 30),
                'min_emergency_duration': status.get('min_emergency_duration', 45),
                'max_emergency_duration': status.get('max_emergency_duration', 90)
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'error': f'Failed to get meta controller status: {str(e)}',
            'active': False,
            'timestamp': datetime.now().isoformat()
        })

def prepare_emergency_counts():
    """Helper to prepare emergency counts from traffic summary"""
    emergency_counts = {}
    if traffic_state.get('traffic_summary'):
        ambulance_counts = traffic_state['traffic_summary'].get('emergency_status', {}).get('ambulance_counts', [0, 0, 0, 0])
        for i, direction in enumerate(DIRS):
            emergency_counts[f"{ABBR[direction]}_E"] = ambulance_counts[i] if i < len(ambulance_counts) else 0
    else:
        for direction in DIRS:
            emergency_counts[f"{ABBR[direction]}_E"] = 0
    return emergency_counts

def get_detailed_phase_data(current_phase, phase_status, time_remaining):
    """Generate detailed traffic light data for each direction"""
    phase_directions = {
        0: {'north': ['straight', 'right'], 'south': ['straight', 'right']},
        1: {'north': ['left'], 'south': ['left']},
        2: {'east': ['straight', 'right'], 'west': ['straight', 'right']},
        3: {'east': ['left'], 'west': ['left']},
    }
    
    active_directions = phase_directions.get(current_phase, {})
    phase_data = {}
    
    for direction in ['north', 'south', 'east', 'west']:
        if direction in active_directions:
            phase_data[direction] = {
                'status': phase_status,
                'countdown': time_remaining,
                'movements': active_directions[direction]
            }
        else:
            phase_data[direction] = {
                'status': 'RED',
                'countdown': time_remaining + 15,
                'movements': []
            }
    
    return phase_data

# ==========================
# VIDEO STREAMING ROUTES
# ==========================

def generate_dummy_frame(camera_id):
    """Generate a dummy video frame for testing"""
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
    color = colors[camera_id % 4]
    
    frame = np.full((180, 320, 3), color, dtype=np.uint8)
    
    # Add text overlay
    cv2.putText(frame, f"Camera {camera_id + 1}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(frame, f"Direction: {DIRS[camera_id]}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(frame, f"Time: {datetime.now().strftime('%H:%M:%S')}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    return frame

def generate_video_stream(camera_id):
    """Generate MJPEG video stream for a specific camera"""
    global yolo_detector
    
    target_fps = 20
    frame_time = 1.0 / target_fps
    last_frame_time = 0
    
    while True:
        try:
            current_time = time.time()
            
            # Control frame rate
            if current_time - last_frame_time < frame_time:
                time.sleep(0.005)
                continue
            
            frame = None
            
            # Try to get processed frame from Integrated Traffic Detector
            if USE_YOLO and yolo_detector and yolo_detector.is_healthy():
                try:
                    frames = yolo_detector.get_current_frames()
                    if frames and camera_id < len(frames) and frames[camera_id] is not None:
                        frame = frames[camera_id].copy()
                except Exception as e:
                    pass
            
            # Fall back to dummy frame
            if frame is None:
                frame = generate_dummy_frame(camera_id)
            
            # Encode frame
            encode_param = [cv2.IMWRITE_JPEG_QUALITY, 90, cv2.IMWRITE_JPEG_OPTIMIZE, 1]
            _, buffer = cv2.imencode('.jpg', frame, encode_param)
            frame_bytes = buffer.tobytes()
            
            # Yield frame in MJPEG format
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n'
                   b'Content-Length: ' + str(len(frame_bytes)).encode() + b'\r\n\r\n' + 
                   frame_bytes + b'\r\n')
            
            last_frame_time = current_time
            
        except Exception as e:
            error_frame = generate_dummy_frame(camera_id)
            cv2.putText(error_frame, "ERROR", (120, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            
            _, buffer = cv2.imencode('.jpg', error_frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.5)

@app.route('/video_feed/<int:camera_id>')
def video_feed(camera_id):
    """Video streaming route for individual cameras"""
    if camera_id < 0 or camera_id > 3:
        return "Invalid camera ID", 404
    
    return Response(generate_video_stream(camera_id),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/pedestrian_video_feed')
def pedestrian_video_feed():
    """Dedicated video streaming route for pedestrian detection from v6.mp4"""
    def generate_pedestrian_stream():
        global pedestrian_controller
        
        import cv2
        video_path = 'videos/v6.mp4'
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            # Fallback to dummy frame
            dummy_frame = np.full((180, 320, 3), (100, 100, 100), dtype=np.uint8)
            cv2.putText(dummy_frame, "Pedestrian Video", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(dummy_frame, "Not Available", (40, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            _, buffer = cv2.imencode('.jpg', dummy_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            frame_bytes = buffer.tobytes()
            while True:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                time.sleep(0.1)
        
        target_fps = 20
        frame_time = 1.0 / target_fps
        last_frame_time = 0
        
        while True:
            try:
                current_time = time.time()
                
                # Control frame rate
                if current_time - last_frame_time < frame_time:
                    time.sleep(0.005)
                    continue
                
                ret, frame = cap.read()
                
                # Loop video when it ends
                if not ret:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = cap.read()
                    if not ret:
                        break
                
                # Resize frame if needed
                if frame.shape[0] > 480:
                    scale = 480 / frame.shape[0]
                    width = int(frame.shape[1] * scale)
                    frame = cv2.resize(frame, (width, 480))
                
                # Get pedestrian detection overlay if available
                if USE_PEDESTRIAN_CONTROLLER and pedestrian_controller:
                    try:
                        ped_status = get_pedestrian_status()
                        ped_count = ped_status.get('pedestrian_count', 0)
                        ped_detected = ped_status.get('pedestrian_detected', False)
                        
                        # Add detection overlay
                        if ped_detected:
                            cv2.putText(frame, f"Pedestrians: {ped_count}", (10, 30), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                            cv2.putText(frame, "DETECTED", (10, 60), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                        else:
                            cv2.putText(frame, "No Pedestrians", (10, 30), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
                    except:
                        pass
                
                # Encode frame
                encode_param = [cv2.IMWRITE_JPEG_QUALITY, 85]
                _, buffer = cv2.imencode('.jpg', frame, encode_param)
                frame_bytes = buffer.tobytes()
                
                # Yield frame in MJPEG format
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n'
                       b'Content-Length: ' + str(len(frame_bytes)).encode() + b'\r\n\r\n' + 
                       frame_bytes + b'\r\n')
                
                last_frame_time = current_time
                
            except Exception as e:
                print(f"Error in pedestrian video stream: {e}")
                time.sleep(0.5)
        
        cap.release()
    
    return Response(generate_pedestrian_stream(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/video_status')
def video_status():
    """Get video streaming status"""
    global yolo_detector
    
    if USE_YOLO and YOLO_AVAILABLE:
        if yolo_detector and yolo_detector.is_healthy():
            stream_type = 'integrated'
            status = 'active'
        else:
            stream_type = 'integrated_initializing'
            status = 'initializing'
    elif USE_YOLO:
        stream_type = 'integrated_error'
        status = 'fallback'
    else:
        stream_type = 'dummy'
        status = 'active'
    
    cameras = [{'id': i, 'name': f"Camera {i+1}", 'direction': DIRS[i], 'active': True} for i in range(4)]
    
    return jsonify({
        'status': status,
        'cameras': cameras,
        'stream_type': stream_type,
        'traffic_detection_enabled': USE_YOLO,
        'traffic_detection_available': YOLO_AVAILABLE,
        'traffic_detection_healthy': yolo_detector.is_healthy() if yolo_detector else False,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/debug_traffic')
def debug_traffic():
    """Debug endpoint to check Traffic Detection status""
    debug_info = {
        'USE_INTEGRATED_DETECTION': USE_YOLO,
        'INTEGRATED_DETECTION_AVAILABLE': YOLO_AVAILABLE,
        'traffic_detector_exists': yolo_detector is not None,
        'traffic_detector_healthy': yolo_detector.is_healthy() if yolo_detector else False
    }
    
    for module in ['torch', 'ultralytics', 'cv2']:
        try:
            mod = __import__(module)
            debug_info[f'{module}_available'] = True
            if hasattr(mod, '__version__'):
                debug_info[f'{module}_version'] = mod.__version__
        except:
            debug_info[f'{module}_available'] = False
    
    return jsonify(debug_info)

@app.route('/force_init_traffic')
def force_init_traffic():
    """Force Traffic Detection initialization"""
    global yolo_detector, USE_YOLO
    
    if not YOLO_AVAILABLE:
        return jsonify({'error': 'Traffic Detection not available', 'success': False})
    
    try:
        if yolo_detector:
            cleanup_detector()
        USE_YOLO = True
        success = initialize_detector()
        if success:
            yolo_detector = get_detector()
            return jsonify({'success': True, 'message': 'Traffic Detection initialized successfully'})
        else:
            return jsonify({'success': False, 'message': 'Traffic Detection initialization failed'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ========================================
# DEMO VIDEO ROUTES
# ========================================

@app.route('/api/demo_violation_video')
def demo_violation_video():
    """Serve the traffic signal violation demonstration video"""
    try:
        signal_jumping_path = Path('videos/traffic_violation.mp4')
        
        if signal_jumping_path.exists():
            return send_file(
                str(signal_jumping_path),
                mimetype='video/mp4',
                as_attachment=False,
                download_name='signal_jumping_demo.mp4'
            )
        
        outputs_dir = Path('outputs')
        video_files = list(outputs_dir.glob('traffic_violation_*.mp4'))
        
        if video_files:
            return send_file(
                str(video_files[0]),
                mimetype='video/mp4',
                as_attachment=False,
                download_name='violation_demo.mp4'
            )
        
        return jsonify({'error': 'No demo video available'}), 404
            
    except Exception as e:
        print(f"[ERROR] Failed to serve violation video: {e}")
        return jsonify({'error': f'Failed to load video: {str(e)}'}), 500

@app.route('/api/demo_accident_video')
def demo_accident_video():
    """Serve the crash/accident detection demonstration video"""
    try:
        accident_video_path = Path('videos/car_crash.mp4')
        
        if accident_video_path.exists():
            return send_file(
                str(accident_video_path),
                mimetype='video/mp4',
                as_attachment=False,
                download_name='car_crash.mp4'
            )
        
        accident_fallback = Path('output_accident_detection.avi')
        if accident_fallback.exists():
            return send_file(
                str(accident_fallback),
                mimetype='video/x-msvideo',
                as_attachment=False,
                download_name='accident_demo.avi'
            )
        
        outputs_dir = Path('outputs')
        video_files = list(outputs_dir.glob('traffic_violation_*.mp4'))
        if video_files:
            return send_file(
                str(video_files[-1] if len(video_files) > 1 else video_files[0]),
                mimetype='video/mp4',
                as_attachment=False,
                download_name='accident_demo.mp4'
            )
        
        return jsonify({'error': 'No demo video available'}), 404
            
    except Exception as e:
        print(f"[ERROR] Failed to serve accident video: {e}")
        return jsonify({'error': f'Failed to load video: {str(e)}'}), 500

@app.route('/api/demo_videos_status')
def demo_videos_status():
    """Check availability of demo videos"""
    try:
        signal_jumping_path = Path('videos/traffic_violation.mp4')
        accident_video_path = Path('videos/car_crash.mp4')
        outputs_dir = Path('outputs')
        violation_videos = list(outputs_dir.glob('traffic_violation_*.mp4')) if outputs_dir.exists() else []
        accident_fallback = Path('output_accident_detection.avi')
        
        return jsonify({
            'primary_sources': {
                'signal_jumping': signal_jumping_path.exists(),
                'accident_detection': accident_video_path.exists(),
            },
            'fallback_sources': {
                'violation_videos_in_outputs': len(violation_videos) > 0,
                'accident_fallback_avi': accident_fallback.exists(),
            },
            'file_details': {
                'signal_jumping': {
                    'path': str(signal_jumping_path),
                    'exists': signal_jumping_path.exists(),
                    'size_mb': signal_jumping_path.stat().st_size / (1024 * 1024) if signal_jumping_path.exists() else 0
                },
                'accident_detection': {
                    'path': str(accident_video_path),
                    'exists': accident_video_path.exists(),
                    'size_mb': accident_video_path.stat().st_size / (1024 * 1024) if accident_video_path.exists() else 0
                }
            },
            'total_violation_videos': len(violation_videos),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_phase_movements_text(phase):
    """Get human readable text for phase movements"""
    if phase < len(PHASE_NAMES):
        return PHASE_NAMES[phase]
    return "Unknown Phase"

def create_human_friendly_log_entry(entry_type, data):
    """Create human-friendly log entries for better readability"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    
    if entry_type == 'phase_completed':
        phase_num = data['completed_phase'] + 1
        duration = data['completed_duration']
        vehicles = data['total_vehicles']
        phase_name = PHASE_NAMES[data['completed_phase']] if data['completed_phase'] < len(PHASE_NAMES) else "Unknown Phase"
        completion_messages = [
            f"✅ Successfully completed {phase_name} (Phase {phase_num}) after running for {duration} seconds",
            f"🏁 Finished {phase_name} phase - {duration}s cycle completed with {vehicles} vehicles processed",
            f"⏰ Phase {phase_num} ({phase_name}) cycle ended after {duration} seconds of operation",
            f"🔄 Concluded {phase_name} sequence - {duration}s duration with {vehicles} vehicles in queue"
        ]
        message = random.choice(completion_messages)
        
        return {
            'timestamp': timestamp,
            'type': 'completion',
            'message': message,
            'technical_details': f"Phase {phase_num} • {duration}s • {vehicles} vehicles",
            'phase': data['completed_phase'],
            'duration': duration,
            'vehicles': vehicles,
            'priority': 'normal'
        }
    
    elif entry_type == 'phase_started':
        phase_num = data['new_phase'] + 1
        duration = data['duration']
        vehicles = data['total_vehicles']
        decision_mode = data.get('decision_mode', 'unknown')
        emergency = data.get('emergency_override', False)
        reasoning = data.get('reasoning', '')
        phase_name = PHASE_NAMES[data['new_phase']] if data['new_phase'] < len(PHASE_NAMES) else "Unknown Phase"
        if emergency:
            start_messages = [
                f"🚨 EMERGENCY: Activating {phase_name} (Phase {phase_num}) for {duration}s to clear emergency vehicles",
                f"🚑 Emergency Override: Switching to Phase {phase_num} ({phase_name}) - {duration}s priority timing",
                f"⚠️ Emergency Response: {phase_name} activated for {duration}s emergency vehicle clearance",
                f"🚨 Priority Mode: Phase {phase_num} ({phase_name}) started with {duration}s emergency extension"
            ]
            priority = 'emergency'
            mode_text = "Emergency Override"
        elif decision_mode == 'ppo_agent':
            start_messages = [
                f"🤖 AI Decision: Starting {phase_name} (Phase {phase_num}) for {duration}s based on traffic analysis",
                f"🧠 Neural Network: Activating Phase {phase_num} ({phase_name}) - {duration}s optimal timing",
                f"📊 PPO Agent: {phase_name} selected for {duration}s to maximize traffic flow efficiency",
                f"🎯 Smart Control: Phase {phase_num} ({phase_name}) initiated for {duration}s intelligent management"
            ]
            priority = 'ai'
            mode_text = "AI Decision"
        elif 'rule_based' in decision_mode:
            start_messages = [
                f"📋 Rule-Based: {phase_name} (Phase {phase_num}) activated for {duration}s using traffic rules",
                f"⚖️ Logic Control: Starting Phase {phase_num} ({phase_name}) - {duration}s based on traffic patterns",
                f"🔧 Standard Protocol: {phase_name} initiated for {duration}s following traffic management rules",
                f"📐 Algorithm: Phase {phase_num} ({phase_name}) selected for {duration}s systematic control"
            ]
            priority = 'standard'
            mode_text = "Rule-Based Logic"
        else:
            start_messages = [
                f"🚦 Traffic Control: {phase_name} (Phase {phase_num}) started for {duration}s traffic management",
                f"⏱️ Phase Activation: Starting Phase {phase_num} ({phase_name}) - {duration}s cycle initiated",
                f"🔄 System Control: {phase_name} activated for {duration}s intersection management",
                f"🚥 Signal Change: Phase {phase_num} ({phase_name}) operational for {duration}s"
            ]
            priority = 'normal'
            mode_text = "System Control"
        message = random.choice(start_messages)
        
        # Add reasoning context
        context = ""
        if reasoning and len(reasoning) > 10:
            import re
            cleaned_reasoning = reasoning
            cleaned_reasoning = re.sub(r',\s*value=[^,\s]+', '', cleaned_reasoning)
            cleaned_reasoning = re.sub(r'value=[^,\s]+,?\s*', '', cleaned_reasoning)
            if "PPO" in cleaned_reasoning:
                context = f" • AI Analysis: {cleaned_reasoning.replace('PPO', 'Neural Network')}"
            elif "emergency" in cleaned_reasoning.lower():
                context = f" • Emergency: {cleaned_reasoning}"
            elif "vehicles" in cleaned_reasoning:
                context = f" • Traffic: {cleaned_reasoning}"
            else:
                context = f" • Logic: {cleaned_reasoning}"
        
        return {
            'timestamp': timestamp,
            'type': 'activation',
            'message': message,
            'context': context,
            'technical_details': f"Phase {phase_num} • {duration}s • {vehicles} vehicles • {mode_text}",
            'phase': data['new_phase'],
            'duration': duration,
            'vehicles': vehicles,
            'priority': priority,
            'emergency': emergency,
            'decision_mode': mode_text
        }
    
    elif entry_type == 'pedestrian_phase_started':
        ped_count = data.get('pedestrian_count', 0)
        duration = data.get('duration', PEDESTRIAN_PHASE_DURATION)
        start_messages = [
            f"🚶 Pedestrian Phase ACTIVATED - {ped_count} pedestrians detected, all vehicle signals RED for {duration}s",
            f"🚸 Pedestrian Crossing: {ped_count} pedestrians waiting - vehicles stopped for {duration}s",
            f"⏸️ Vehicle Flow PAUSED - Pedestrian phase started for {duration} seconds ({ped_count} pedestrians)",
            f"🛑 ALL STOP for pedestrians - {ped_count} detected, {duration}s crossing time allocated"
        ]
        message = random.choice(start_messages)
        
        return {
            'timestamp': timestamp,
            'type': 'pedestrian',
            'message': message,
            'technical_details': f"Pedestrian Phase • {duration}s • {ped_count} pedestrians",
            'pedestrian_count': ped_count,
            'duration': duration,
            'priority': 'pedestrian'
        }
    
    elif entry_type == 'pedestrian_phase_ended':
        ped_count = data.get('pedestrian_count', 0)
        duration = data.get('duration', PEDESTRIAN_PHASE_DURATION)
        end_messages = [
            f"🚗 Pedestrian Phase COMPLETED - Resuming vehicle flow after {duration}s crossing time",
            f"✅ Pedestrian crossing finished - Vehicle signals returning to normal operation",
            f"🔄 Transitioning from pedestrian phase back to vehicle control cycle",
            f"🚦 Pedestrian phase ended - Vehicle traffic resuming normal flow"
        ]
        message = random.choice(end_messages)
        
        return {
            'timestamp': timestamp,
            'type': 'pedestrian_complete',
            'message': message,
            'technical_details': f"Pedestrian Phase Complete • {duration}s duration",
            'duration': duration,
            'priority': 'normal'
        }
    
    # Fallback
    return {
        'timestamp': timestamp,
        'type': 'unknown',
        'message': f"System activity recorded at {timestamp}",
        'technical_details': str(data),
        'priority': 'normal'
    }

if __name__ == '__main__':
    print("🚦 Starting Traffic Control Dashboard...")
    
    if not traffic_state.get('vehicle_counts'):
        traffic_state['vehicle_counts'] = generate_realistic_counts()
    
    # Initialize Integrated Traffic Detector
    if USE_YOLO:
        print("🤖 Initializing Integrated Traffic Detection System...")
        try:
            if initialize_detector():
                yolo_detector = get_detector()
                print("✅ Integrated Traffic Detection System started successfully")
            else:
                print("❌ Failed to start Integrated Traffic Detection System - using dummy data")
                USE_YOLO = False
        except Exception as e:
            print(f"❌ Traffic detection initialization error: {e} - using dummy data")
            USE_YOLO = False
    else:
        print("📺 Using dummy data mode (Traffic detection disabled)")
    
    # Initialize LLM Description Service (separate from core systems)
    if USE_LLM_DESCRIPTIONS:
        print("🤖 Initializing LLM Description Service...")
        try:
            if initialize_description_service():
                llm_service = get_description_service()
                print("✅ LLM Description Service started successfully")
            else:
                print("❌ Failed to start LLM Description Service - using fallback descriptions")
                USE_LLM_DESCRIPTIONS = False
        except Exception as e:
            print(f"❌ LLM service initialization error: {e} - using fallback descriptions")
            USE_LLM_DESCRIPTIONS = False
    else:
        print("📝 Using fallback descriptions (LLM service disabled)")
    
    # Initialize Meta Controller
    print(f"🔍 META CONTROLLER STATUS CHECK:")
    print(f"   • USE_META_CONTROLLER: {USE_META_CONTROLLER}")
    print(f"   • META_CONTROLLER_AVAILABLE: {META_CONTROLLER_AVAILABLE}")
    print(f"   • meta_controller exists: {meta_controller is not None}")
    print(f"   • agent exists: {agent is not None}")
    
    if USE_META_CONTROLLER and META_CONTROLLER_AVAILABLE:
        print("🧠 Ensuring Meta Controller is initialized...")
        try:
            if initialize_meta_controller(ppo_agent=agent):
                meta_controller = get_meta_controller()
                print("✅ Meta Controller initialized successfully")
                print(f"   • Emergency threshold: {meta_controller.emergency_threshold} vehicles")
                print(f"   • Emergency extension: +{meta_controller.emergency_phase_extension}s")
                print(f"   • Emergency duration range: {meta_controller.min_emergency_duration}-{meta_controller.max_emergency_duration}s")
            else:
                print("❌ Failed to initialize Meta Controller - using direct PPO")
                USE_META_CONTROLLER = False
        except Exception as e:
            print(f"❌ Meta Controller initialization error: {e} - using direct PPO")
            import traceback
            traceback.print_exc()
            USE_META_CONTROLLER = False
    else:
        print("📊 Using direct PPO agent (Meta Controller disabled)")
    
    # Print Pedestrian Controller status
    print(f"🚶 PEDESTRIAN CONTROLLER STATUS:")
    print(f"   • USE_PEDESTRIAN_CONTROLLER: {USE_PEDESTRIAN_CONTROLLER}")
    print(f"   • PEDESTRIAN_CONTROLLER_AVAILABLE: {PEDESTRIAN_CONTROLLER_AVAILABLE}")
    print(f"   • Pedestrian phase duration: {PEDESTRIAN_PHASE_DURATION}s")
    print(f"   • Total cycle duration: {TOTAL_CYCLE_DURATION}s")
    if USE_PEDESTRIAN_CONTROLLER:
        print("   • Pedestrian controller will be initialized in simulation thread")
    
    # Start simulation in background thread
    print("🎬 Starting traffic simulation thread...")
    simulation_thread = threading.Thread(target=traffic_simulation, daemon=True)
    simulation_thread.start()
    
    print("🌐 Open http://localhost:5000 in your browser")
    print("📹 Video streams available at:")
    print("   • Camera 1 (North): http://localhost:5000/video_feed/0")
    print("   • Camera 2 (South): http://localhost:5000/video_feed/1") 
    print("   • Camera 3 (East): http://localhost:5000/video_feed/2")
    print("   • Camera 4 (West): http://localhost:5000/video_feed/3")
    print("✅ System ready - all components initialized")
    
    try:
        app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
    finally:
        if USE_YOLO:
            print("🔄 Cleaning up Traffic Detection System...")
            cleanup_detector()
        if USE_LLM_DESCRIPTIONS:
            print("🔄 Cleaning up LLM Description Service...")
            cleanup_description_service()
        if USE_META_CONTROLLER:
            print("🔄 Cleaning up Meta Controller...")
            cleanup_meta_controller()
        if USE_PEDESTRIAN_CONTROLLER:
            print("🔄 Cleaning up Pedestrian Controller...")
            cleanup_pedestrian_controller()