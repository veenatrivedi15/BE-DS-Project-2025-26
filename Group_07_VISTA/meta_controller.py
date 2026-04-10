"""
Meta Controller for Traffic Management System
Decides between PPO agent and emergency control with pedestrian phase awareness
"""

import time
import logging
import numpy as np
from datetime import datetime
from threading import Lock

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import global pedestrian state functions for instant synchronization
try:
    from pedestrian_controller import (
        is_pedestrian_phase_active as global_is_pedestrian_phase_active,
        is_pedestrian_phase_locked as global_is_pedestrian_phase_locked,
        get_global_pedestrian_state,
        PHASE_DURATION as PEDESTRIAN_PHASE_DURATION
    )
    PEDESTRIAN_GLOBALS_AVAILABLE = True
except ImportError:
    PEDESTRIAN_GLOBALS_AVAILABLE = False
    def global_is_pedestrian_phase_active(): return False
    def global_is_pedestrian_phase_locked(): return False
    def get_global_pedestrian_state(): return {'phase_active': False, 'phase_remaining': 0}
    PEDESTRIAN_PHASE_DURATION = 20


class TrafficMetaController:
    """Meta controller for PPO agent and emergency control with pedestrian phase awareness"""
    
    def __init__(self, ppo_agent=None):
        self.ppo_agent = ppo_agent
        self.is_initialized = False
        self.decision_lock = Lock()
        
        # Emergency detection parameters
        self.emergency_threshold = 1
        self.emergency_phase_extension = 30
        self.min_emergency_duration = 45
        self.max_emergency_duration = 90
        
        # Decision tracking
        self.last_decision_time = time.time()
        self.decision_history = []
        self.current_mode = "normal"
        self.emergency_start_time = None
        
        # Pedestrian phase tracking (kept for backward compatibility)
        self.pedestrian_phase_active = False
        self.pedestrian_phase_start_time = None
        self.pedestrian_phase_duration = 20
        
        # Emergency vehicle tracking
        self.emergency_vehicle_tracker = {
            'last_seen': {},
            'timeout_duration': 10.0,
            'active_emergency_dirs': set(),
            'emergency_phase_forced': False,
            'original_phase': None,
            'original_remaining_time': None
        }
        
        # Traffic directions mapping
        self.DIRS = ["North", "South", "East", "West"]
        self.ABBR = {"North":"N","South":"S","East":"E","West":"W"}
        
        # Phase definitions
        self.PHASE_NAMES = [
            "North-South Through",
            "North-South Left", 
            "East-West Through",
            "East-West Left"
        ]
        
        # Emergency priority phases
        self.EMERGENCY_PHASES = {
            "North": [0, 1],
            "South": [0, 1],
            "East": [2, 3],
            "West": [2, 3]
        }
    
    def initialize(self):
        """Initialize the meta controller"""
        try:
            self.is_initialized = True
            logger.info("Meta Controller initialized successfully!")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize meta controller: {e}")
            return False
    
    def analyze_emergency_situation(self, traffic_data):
        """Analyze emergency situation with severity levels and frame-based tracking"""
        emergency_status = traffic_data.get('emergency_status', {})
        emergency_counts = traffic_data.get('emergency_counts', {})
        
        current_time = time.time()
        total_emergency = 0
        emergency_directions = []
        max_emergency_in_direction = 0
        currently_detected_dirs = set()
        
        # Count emergency vehicles by direction
        for i, direction in enumerate(self.DIRS):
            abbr = self.ABBR[direction]
            emergency_count = emergency_counts.get(f"{abbr}_E", 0)
            
            if emergency_count > 0:
                total_emergency += emergency_count
                emergency_directions.append(direction)
                max_emergency_in_direction = max(max_emergency_in_direction, emergency_count)
                currently_detected_dirs.add(direction)
                self.emergency_vehicle_tracker['last_seen'][direction] = current_time
        
        # Check for expired emergency vehicles
        expired_dirs = set()
        for direction, last_seen_time in self.emergency_vehicle_tracker['last_seen'].items():
            if current_time - last_seen_time > self.emergency_vehicle_tracker['timeout_duration']:
                expired_dirs.add(direction)
        
        # Remove expired directions
        for direction in expired_dirs:
            if direction in self.emergency_vehicle_tracker['last_seen']:
                del self.emergency_vehicle_tracker['last_seen'][direction]
        
        # Update active emergency directions
        self.emergency_vehicle_tracker['active_emergency_dirs'] = set(
            dir for dir, last_seen in self.emergency_vehicle_tracker['last_seen'].items()
            if current_time - last_seen <= self.emergency_vehicle_tracker['timeout_duration']
        )
        
        # Include recently seen emergency vehicles
        all_emergency_dirs = list(currently_detected_dirs.union(
            self.emergency_vehicle_tracker['active_emergency_dirs']
        ))
        
        # Calculate severity based on multiple factors
        severity = 0.0
        total_active_emergency = len(all_emergency_dirs)
        
        if total_active_emergency > 0:
            severity = min(total_active_emergency / 3.0, 1.0)
            
            if len(all_emergency_dirs) > 1:
                severity *= 1.3
            
            if max_emergency_in_direction >= 2:
                severity *= 1.2
            
            if self.emergency_vehicle_tracker['emergency_phase_forced']:
                severity = max(severity, 0.8)
            
            severity = min(severity, 1.0)
        
        emergency_vehicles_cleared = (
            len(all_emergency_dirs) == 0 and 
            self.emergency_vehicle_tracker['emergency_phase_forced']
        )
        
        return {
            'emergency_detected': len(all_emergency_dirs) >= self.emergency_threshold,
            'total_emergency_vehicles': total_emergency,
            'emergency_directions': all_emergency_dirs,
            'currently_detected_dirs': list(currently_detected_dirs),
            'recently_active_dirs': list(self.emergency_vehicle_tracker['active_emergency_dirs']),
            'emergency_vehicles_cleared': emergency_vehicles_cleared,
            'severity': severity,
            'max_per_direction': max_emergency_in_direction,
            'requires_immediate_action': severity > 0.7 or max_emergency_in_direction >= 2,
            'primary_emergency_direction': all_emergency_dirs[0] if all_emergency_dirs else None
        }
    
    def get_normal_decision(self, traffic_data, current_phase, time_remaining):
        """Get decision from PPO agent for normal conditions"""
        try:
            if self.ppo_agent is None:
                return self._fallback_normal_decision(traffic_data, current_phase, time_remaining)
            
            vehicle_counts = traffic_data.get('vehicle_counts', {})
            
            try:
                from traffic_flask_app import create_traffic_state_for_ppo, create_phase_state_for_ppo
                traffic_state_input = create_traffic_state_for_ppo(vehicle_counts)
                phase_state_input = create_phase_state_for_ppo(current_phase, time_remaining)
            except ImportError:
                return self._fallback_normal_decision(traffic_data, current_phase, time_remaining)
            
            state = [traffic_state_input, phase_state_input]
            
            # Get action from PPO
            phase_action, duration, state_value, logp_phase, logp_duration = self.ppo_agent.get_action(state)
            
            phase_action = max(0, min(phase_action, len(self.PHASE_NAMES) - 1))
            confidence = min(1.0, max(0.0, np.exp(logp_phase)))
            
            return {
                'recommended_phase': int(phase_action),
                'recommended_duration': int(duration),
                'state_value': float(state_value),
                'confidence': float(confidence),
                'reasoning': f'PPO decision: {sum(vehicle_counts.values())} vehicles',
                'decision_mode': 'ppo_agent',
                'emergency_override': False,
                'emergency_severity': 0.0
            }
            
        except Exception as e:
            logger.error(f"Error in PPO decision: {e}")
            return self._fallback_normal_decision(traffic_data, current_phase, time_remaining)
    
    def _fallback_normal_decision(self, traffic_data, current_phase, time_remaining):
        """Fallback decision when PPO agent is unavailable"""
        from traffic_flask_app import calculate_phase_benefit, PHASES
        
        vehicle_counts = traffic_data.get('vehicle_counts', {})
        best_phase = current_phase
        best_benefit = calculate_phase_benefit(current_phase, vehicle_counts)
        
        for phase in range(min(4, len(PHASES))):
            benefit = calculate_phase_benefit(phase, vehicle_counts)
            if benefit > best_benefit:
                best_benefit = benefit
                best_phase = phase
        
        total_vehicles = sum(vehicle_counts.values())
        duration = min(max(15, total_vehicles // 2), 45)
        
        return {
            'recommended_phase': best_phase,
            'recommended_duration': duration,
            'state_value': 0.5,
            'confidence': 0.7,
            'reasoning': f'Fallback logic: Phase {best_phase + 1} serves {best_benefit} vehicles',
            'decision_mode': 'rule_based_fallback',
            'emergency_override': False,
            'emergency_severity': 0.0
        }

    def _check_emergency_conflict(self, current_phase_dirs, emergency_dirs):
        """Check if current phase conflicts with emergency vehicle directions"""
        conflicts = {
            'North': ['East', 'West'],
            'South': ['East', 'West'], 
            'East': ['North', 'South'],
            'West': ['North', 'South']
        }
        
        for current_dir in current_phase_dirs:
            for emergency_dir in emergency_dirs:
                if emergency_dir in conflicts.get(current_dir, []):
                    return True
        return False

    def _find_optimal_emergency_phase(self, emergency_dirs, traffic_data):
        """Find best phase for emergency vehicles with minimal traffic disruption"""
        best_phase = 0
        best_score = -1
        
        for phase_idx in range(4):
            score = 0
            phase_dirs = self._get_phase_directions(phase_idx)
            
            for emergency_dir in emergency_dirs:
                if emergency_dir in phase_dirs:
                    score += 10
            
            vehicle_counts = traffic_data.get('vehicle_counts', {})
            for direction in phase_dirs:
                abbr = self.ABBR[direction]
                score += vehicle_counts.get(f"{abbr}_S", 0) * 0.1
                score += vehicle_counts.get(f"{abbr}_L", 0) * 0.1
                score += vehicle_counts.get(f"{abbr}_R", 0) * 0.1
            
            if score > best_score:
                best_score = score
                best_phase = phase_idx
        
        return best_phase

    def _calculate_emergency_duration(self, severity, emergency_dirs):
        """Calculate duration for emergency phase based on severity"""
        base_duration = self.min_emergency_duration
        severity_bonus = int(severity * 20)
        direction_bonus = len(emergency_dirs) * 5
        total_duration = base_duration + severity_bonus + direction_bonus
        return min(max(total_duration, self.min_emergency_duration), self.max_emergency_duration)

    def _get_phase_directions(self, phase_idx):
        """Get which directions are active for a phase"""
        phase_mappings = {
            0: ['North', 'South'],
            1: ['North', 'South'],
            2: ['East', 'West'],
            3: ['East', 'West']
        }
        return phase_mappings.get(phase_idx, [])

    def _is_emergency_compatible_phase(self, current_phase, emergency_dirs):
        """Check if current phase is compatible with emergency directions"""
        current_dirs = self._get_phase_directions(current_phase)
        for emergency_dir in emergency_dirs:
            if emergency_dir in current_dirs:
                return True
        return False

    def _prepare_for_emergency(self, traffic_data, current_phase, time_remaining, emergency_analysis):
        """Prepare for emergency while maintaining current phase"""
        return {
            'recommended_phase': current_phase,
            'recommended_duration': min(time_remaining, 15),
            'emergency_override': True,
            'conflict_resolution': False,
            'current_mode': 'emergency',
            'decision_mode': 'emergency_preparation',
            'emergency_severity': emergency_analysis['severity'],
            'state_value': 0.7,
            'confidence': 0.75,
            'reasoning': f'EMERGENCY PREP: Shortening phase {current_phase + 1} to prepare for emergency',
            'immediate_action': 'shorten_current_phase',
            'affected_directions': emergency_analysis['emergency_directions']
        }

    def _handle_emergency_reset(self, traffic_data, current_phase, time_remaining):
        """Handle transition back to normal operations when emergency clears"""
        
        # Reset emergency tracking
        original_phase = self.emergency_vehicle_tracker.get('original_phase')
        original_time = self.emergency_vehicle_tracker.get('original_remaining_time', 0)
        
        # Clear emergency state
        self.emergency_vehicle_tracker['emergency_phase_forced'] = False
        self.emergency_vehicle_tracker['active_emergency_dirs'].clear()
        self.emergency_vehicle_tracker['last_seen'].clear()
        
        # Determine reset strategy
        if original_phase is not None and time_remaining > 20:
            reset_duration = min(max(15, time_remaining // 2), 30)
            
            decision = {
                'recommended_phase': current_phase,
                'recommended_duration': reset_duration,
                'emergency_override': False,
                'conflict_resolution': False,
                'current_mode': 'emergency_reset',
                'decision_mode': 'emergency_reset_continue',
                'emergency_severity': 0.0,
                'state_value': 0.8,
                'confidence': 0.85,
                'reasoning': f'EMERGENCY RESET: Continuing phase {current_phase + 1} with reduced duration ({reset_duration}s)',
                'immediate_action': 'smart_reset_continue',
                'reset_from_emergency': True
            }
            
        else:
            vehicle_counts = traffic_data.get('vehicle_counts', {})
            optimal_phase = self._find_optimal_normal_phase(vehicle_counts, current_phase)
            optimal_duration = self._calculate_normal_duration(vehicle_counts)
            
            decision = {
                'recommended_phase': optimal_phase,
                'recommended_duration': optimal_duration,
                'emergency_override': False,
                'conflict_resolution': False,
                'current_mode': 'emergency_reset',
                'decision_mode': 'emergency_reset_transition',
                'emergency_severity': 0.0,
                'state_value': 0.75,
                'confidence': 0.8,
                'reasoning': f'EMERGENCY RESET: Transitioning to optimal phase {optimal_phase + 1} ({optimal_duration}s)',
                'immediate_action': 'smart_reset_transition',
                'reset_from_emergency': True
            }
        
        # Log the reset
        self.decision_history.append({
            'timestamp': time.time(),
            'decision_type': 'emergency_reset',
            'reset_phase': decision['recommended_phase'],
            'reset_duration': decision['recommended_duration'],
            'reset_strategy': decision['decision_mode']
        })
        
        return decision

    def _find_optimal_normal_phase(self, vehicle_counts, current_phase):
        """Find optimal phase for normal traffic"""
        best_phase = current_phase
        best_score = 0
        
        from traffic_flask_app import calculate_phase_benefit, PHASES
        
        for phase in range(min(4, len(PHASES))):
            score = calculate_phase_benefit(phase, vehicle_counts)
            if score > best_score:
                best_score = score
                best_phase = phase
        
        return best_phase

    def _calculate_normal_duration(self, vehicle_counts):
        """Calculate duration for normal traffic phase"""
        total_vehicles = sum(vehicle_counts.values())
        if total_vehicles <= 5:
            return 20
        elif total_vehicles <= 15:
            return 30
        else:
            return 40

    def _fallback_decision(self, traffic_data, current_phase, time_remaining):
        """Fallback decision when main logic fails"""
        return {
            'recommended_phase': current_phase,
            'recommended_duration': 30,
            'state_value': 0.5,
            'confidence': 0.3,
            'reasoning': 'Meta controller error fallback - using safe defaults',
            'meta_controller_active': False,
            'current_mode': 'error_fallback',
            'decision_mode': 'error_fallback'
        }
    
    def set_pedestrian_phase_active(self, active, duration=20):
        """Set pedestrian phase status"""
        with self.decision_lock:
            previous_state = self.pedestrian_phase_active
            self.pedestrian_phase_active = active
            self.pedestrian_phase_duration = duration
            
            if active and not previous_state:
                self.pedestrian_phase_start_time = time.time()
                self.current_mode = "pedestrian"
            elif not active and previous_state:
                self.pedestrian_phase_start_time = None
                self.current_mode = "normal"
    
    def is_pedestrian_phase_active(self):
        """Check if pedestrian phase is active"""
        return self.pedestrian_phase_active
    
    def make_decision(self, traffic_data, current_phase, time_remaining):
        """Main decision logic with pedestrian and emergency handling"""
        with self.decision_lock:
            try:
                # Check cycle-based pedestrian phase
                pedestrian_status = traffic_data.get('pedestrian_status', {})
                cycle_elapsed = traffic_data.get('cycle_elapsed', 0)
                pedestrian_request = traffic_data.get('pedestrian_request', False)
                
                # Handle active pedestrian phase (100-120s window)
                if pedestrian_status.get('pedestrian_phase_active', False):
                    return self._handle_pedestrian_phase(traffic_data, current_phase, pedestrian_status, cycle_elapsed)
                
                # Handle pedestrian request queued (detected during 0-100s)
                if pedestrian_request and cycle_elapsed < 100:
                    return self._handle_pedestrian_request_queued(traffic_data, current_phase, pedestrian_status, cycle_elapsed)
                
                # Analyze emergency
                emergency_analysis = self.analyze_emergency_situation(traffic_data)
                
                if emergency_analysis['emergency_detected']:
                    if self.pedestrian_phase_active:
                        logger.warning("Emergency detected during pedestrian phase - emergency takes priority")
                    return self._handle_emergency_situation(traffic_data, current_phase, time_remaining, emergency_analysis)
                else:
                    return self._handle_normal_situation(traffic_data, current_phase, time_remaining)
                    
            except Exception as e:
                logger.error(f"Meta controller decision error: {e}")
                return self._fallback_decision(traffic_data, current_phase, time_remaining)
    
    def _handle_pedestrian_request_queued(self, traffic_data, current_phase, pedestrian_status, cycle_elapsed):
        """Handle queued pedestrian request waiting for execution window"""
        ped_count = pedestrian_status.get('pedestrian_count', 0)
        time_until_window = 100 - cycle_elapsed
        
        self.current_mode = "normal"
        self.pedestrian_phase_active = False
        
        return {
            'recommended_phase': current_phase,
            'recommended_duration': 30,
            'state_value': 0.8,
            'confidence': 0.9,
            'reasoning': f'PEDESTRIAN REQUEST QUEUED: {ped_count} pedestrians detected at t={int(cycle_elapsed)}s. Execution deferred to t=100s (in {int(time_until_window)}s)',
            'decision_mode': 'pedestrian_request_queued',
            'current_mode': 'normal',
            'emergency_override': False,
            'pedestrian_override': False,
            'pedestrian_count': ped_count,
            'pedestrian_request_queued': True,
            'time_until_pedestrian_window': int(time_until_window),
            'emergency_severity': 0.0,
            'meta_controller_active': True,
            'vehicle_signals_red': False
        }
    
    def _handle_pedestrian_phase(self, traffic_data, current_phase, pedestrian_status, cycle_elapsed):
        """Handle active pedestrian phase - all vehicle signals RED (100-120s window)"""
        ped_remaining = pedestrian_status.get('pedestrian_phase_remaining', 0)
        ped_count = pedestrian_status.get('pedestrian_count', 0)
        
        self.current_mode = "pedestrian"
        self.pedestrian_phase_active = True
        
        return {
            'recommended_phase': current_phase,
            'recommended_duration': int(ped_remaining) if ped_remaining > 0 else 20,
            'state_value': 1.0,
            'confidence': 1.0,
            'reasoning': f'PEDESTRIAN PHASE ACTIVE: Cycle t={int(cycle_elapsed)}s (pedestrian window). All vehicle signals RED for {int(ped_remaining)}s. {ped_count} pedestrians crossing.',
            'decision_mode': 'pedestrian_phase_active',
            'current_mode': 'pedestrian',
            'emergency_override': False,
            'pedestrian_override': True,
            'pedestrian_count': ped_count,
            'pedestrian_remaining': ped_remaining,
            'cycle_position': 'PEDESTRIAN_WINDOW',
            'emergency_severity': 0.0,
            'meta_controller_active': True,
            'vehicle_signals_red': True
        }

    def _handle_emergency_situation(self, traffic_data, current_phase, time_remaining, emergency_analysis):
        """Handle emergency with conflict resolution and green extension"""
        emergency_dirs = emergency_analysis['emergency_directions']
        emergency_severity = emergency_analysis['severity']
        
        # Check for emergency vehicle clearance
        if emergency_analysis['emergency_vehicles_cleared']:
            return self._handle_emergency_reset(traffic_data, current_phase, time_remaining)
        
        # Update mode
        previous_mode = self.current_mode
        self.current_mode = "emergency"
        
        if previous_mode != "emergency":
            self.emergency_start_time = time.time()
            self.emergency_vehicle_tracker['original_phase'] = current_phase
            self.emergency_vehicle_tracker['original_remaining_time'] = time_remaining
        
        # Check for conflict
        current_phase_dirs = self._get_phase_directions(current_phase)
        emergency_conflict = self._check_emergency_conflict(current_phase_dirs, emergency_dirs)
        
        if emergency_conflict and time_remaining > 5:
            # Force immediate transition
            optimal_emergency_phase = self._find_optimal_emergency_phase(emergency_dirs, traffic_data)
            emergency_duration = self._calculate_emergency_duration(emergency_severity, emergency_dirs)
            
            decision = {
                'recommended_phase': optimal_emergency_phase,
                'recommended_duration': emergency_duration,
                'emergency_override': True,
                'conflict_resolution': True,
                'current_mode': 'emergency',
                'decision_mode': 'emergency_conflict',
                'emergency_severity': emergency_severity,
                'state_value': 1.0,  # High value for emergency
                'confidence': 0.95,
                'reasoning': f'EMERGENCY CONFLICT: Forcing phase {optimal_emergency_phase + 1} for {emergency_dirs} (severity: {emergency_severity:.2f})',
                'immediate_action': 'force_phase_change',
                'affected_directions': emergency_dirs
            }
            
            self.emergency_vehicle_tracker['emergency_phase_forced'] = True
            self.decision_history.append({
                'timestamp': time.time(),
                'decision_type': 'emergency_conflict_resolution',
                'old_phase': current_phase,
                'new_phase': optimal_emergency_phase,
                'emergency_dirs': emergency_dirs,
                'forced_transition': True
            })
            
            return decision
        
        elif not emergency_conflict:
            if self._is_emergency_compatible_phase(current_phase, emergency_dirs):
                # Smart green extension
                base_extension = self.emergency_phase_extension
                severity_multiplier = 1.0 + (emergency_severity * 0.5)
                extended_duration = min(
                    int(base_extension * severity_multiplier),
                    self.max_emergency_duration
                )
                total_emergency_time = max(extended_duration, self.min_emergency_duration)
                
                decision = {
                    'recommended_phase': current_phase,
                    'recommended_duration': total_emergency_time,
                    'emergency_override': True,
                    'conflict_resolution': False,
                    'current_mode': 'emergency',
                    'decision_mode': 'emergency_extension',
                    'emergency_severity': emergency_severity,
                    'state_value': 0.9,
                    'confidence': 0.9,
                    'reasoning': f'EMERGENCY EXTENSION: Extending phase {current_phase + 1} to {total_emergency_time}s for {emergency_dirs}',
                    'immediate_action': 'extend_current_phase',
                    'affected_directions': emergency_dirs,
                    'extension_time': extended_duration
                }
                
                return decision
        
        # Plan for next phase
        if time_remaining <= 10:
            optimal_emergency_phase = self._find_optimal_emergency_phase(emergency_dirs, traffic_data)
            emergency_duration = self._calculate_emergency_duration(emergency_severity, emergency_dirs)
            
            decision = {
                'recommended_phase': optimal_emergency_phase,
                'recommended_duration': emergency_duration,
                'emergency_override': True,
                'conflict_resolution': False,
                'current_mode': 'emergency',
                'decision_mode': 'emergency_planning',
                'emergency_severity': emergency_severity,
                'state_value': 0.85,
                'confidence': 0.85,
                'reasoning': f'EMERGENCY PLANNING: Next phase {optimal_emergency_phase + 1} for {emergency_dirs}',
                'immediate_action': 'plan_next_phase',
                'affected_directions': emergency_dirs
            }
            
            return decision
        
        return self._prepare_for_emergency(traffic_data, current_phase, time_remaining, emergency_analysis)

    def _handle_normal_situation(self, traffic_data, current_phase, time_remaining):
        """Handle normal traffic using PPO agent"""
        previous_mode = self.current_mode
        self.current_mode = "normal"
        
        # Reset tracking if coming from other modes
        if previous_mode == "pedestrian":
            self.pedestrian_phase_active = False
            self.pedestrian_phase_start_time = None
        
        if previous_mode == "emergency":
            self.emergency_vehicle_tracker['emergency_phase_forced'] = False
            self.emergency_vehicle_tracker['active_emergency_dirs'].clear()
            self.emergency_vehicle_tracker['original_phase'] = None
            self.emergency_vehicle_tracker['original_remaining_time'] = None
        
        # Get PPO decision
        decision = self.get_normal_decision(traffic_data, current_phase, time_remaining)
        
        # Add metadata
        decision.update({
            'meta_controller_active': True,
            'current_mode': self.current_mode,
            'pedestrian_override': False,
            'emergency_analysis': {'emergency_detected': False, 'emergency_directions': []},
            'decision_timestamp': datetime.now().isoformat()
        })
        
        # Track decision
        self.decision_history.append({
            'timestamp': time.time(),
            'mode': self.current_mode,
            'phase': decision['recommended_phase'],
            'duration': decision['recommended_duration'],
            'emergency_vehicles': 0
        })
        
        # Keep recent history
        if len(self.decision_history) > 50:
            self.decision_history = self.decision_history[-50:]
        
        self.last_decision_time = time.time()
        return decision
    
    def get_status(self):
        """Get current meta controller status"""
        return {
            'is_initialized': self.is_initialized,
            'current_mode': self.current_mode,
            'emergency_start_time': self.emergency_start_time,
            'pedestrian_phase_active': self.pedestrian_phase_active,
            'pedestrian_phase_start_time': self.pedestrian_phase_start_time,
            'pedestrian_phase_duration': self.pedestrian_phase_duration,
            'last_decision_time': self.last_decision_time,
            'decision_history_count': len(self.decision_history),
            'emergency_threshold': self.emergency_threshold,
            'emergency_phase_extension': self.emergency_phase_extension,
            'min_emergency_duration': self.min_emergency_duration,
            'max_emergency_duration': self.max_emergency_duration
        }
    
    def get_recent_decisions(self, count=10):
        """Get recent decision history"""
        return self.decision_history[-count:] if self.decision_history else []


# Global meta controller instance
_meta_controller = None

def initialize_meta_controller(ppo_agent=None):
    """Initialize the meta controller"""
    global _meta_controller
    try:
        _meta_controller = TrafficMetaController(ppo_agent=ppo_agent)
        return _meta_controller.initialize()
    except Exception as e:
        logger.error(f"Failed to initialize meta controller: {e}")
        return False

def get_meta_controller():
    """Get the meta controller instance"""
    return _meta_controller

def cleanup_meta_controller():
    """Cleanup the meta controller"""
    global _meta_controller
    if _meta_controller:
        _meta_controller = None
    logger.info("Meta controller cleaned up")


# Utility function for easy integration
def get_meta_decision(traffic_data, current_phase, time_remaining):
    """Get decision from meta controller with fallback"""
    global _meta_controller
    
    if _meta_controller and _meta_controller.is_initialized:
        return _meta_controller.make_decision(traffic_data, current_phase, time_remaining)
    else:
        try:
            from traffic_flask_app import get_ppo_decision
            vehicle_counts = traffic_data.get('vehicle_counts', {})
            decision = get_ppo_decision(vehicle_counts, current_phase, time_remaining)
            decision.update({
                'meta_controller_active': False,
                'current_mode': 'fallback',
                'decision_mode': 'ppo_fallback'
            })
            return decision
        except Exception as e:
            logger.error(f"Error in fallback decision: {e}")
            return {
                'recommended_phase': current_phase,
                'recommended_duration': 30,
                'state_value': 0.5,
                'confidence': 0.3,
                'reasoning': 'Meta controller unavailable - using safe defaults',
                'meta_controller_active': False,
                'current_mode': 'error_fallback',
                'decision_mode': 'error_fallback'
            }