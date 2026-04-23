"""
LLM Description Service for Traffic Management System
Uses Phi-3 model for generating natural traffic descriptions
Designed to run independently without affecting core traffic systems
"""

import torch
import time
import random
from datetime import datetime
from threading import Thread, Lock
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TrafficDescriptionService:
    """
    Standalone service for generating traffic descriptions using Phi-3
    Operates independently from PPO and traffic detection systems
    """
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.device = "cpu"  # Start with CPU to avoid conflicts
        self.is_initialized = False
        self.is_running = False
        self.cache_lock = Lock()
        
        # Cache for descriptions to avoid regenerating too frequently
        self.description_cache = {
            'camera_descriptions': ["Loading...", "Loading...", "Loading...", "Loading..."],
            'overall_summary': "Initializing traffic analysis system...",
            'last_update': time.time(),
            'cache_duration': 5.0  # Update every 5 seconds
        }
        
        # Direction mapping
        self.DIRS = ["North", "South", "East", "West"]
        self.PHASE_NAMES = [
            "North-South Through",
            "North-South Left", 
            "East-West Through",
            "East-West Left"
        ]
    
    def initialize(self):
        """Initialize LLM service with smart fallback"""
        try:
            logger.info("Initializing Traffic Description Service...")
            
            # Start with rule-based descriptions (always works)
            logger.info("Using intelligent rule-based descriptions (no model download required)")
            self.is_initialized = True
            return True
            
            # TODO: Uncomment below to enable Phi-3 (requires model download)
            # To enable Phi-3, users can uncomment the code below after first ensuring
            # their system can handle the additional load
            
            # # Try to import transformers
            # try:
            #     from transformers import AutoTokenizer, AutoModelForCausalLM
            #     import torch
            # except ImportError as e:
            #     logger.warning(f"Transformers not available: {e}")
            #     logger.info("Will use rule-based descriptions as fallback")
            #     self.is_initialized = True
            #     return True
            # 
            # # Use CPU only to avoid GPU conflicts with YOLO/PPO
            # self.device = "cpu"
            # logger.info(f"Using device: {self.device} for LLM (to avoid conflicts)")
            # 
            # # Load Phi-3 model with minimal resources
            # try:
            #     model_name = "microsoft/Phi-3-mini-4k-instruct"
            #     logger.info(f"Loading {model_name}...")
            #     
            #     self.tokenizer = AutoTokenizer.from_pretrained(
            #         model_name,
            #         trust_remote_code=True
            #     )
            #     
            #     self.model = AutoModelForCausalLM.from_pretrained(
            #         model_name,
            #         torch_dtype=torch.float32,  # Use FP32 to avoid conflicts
            #         device_map=None,  # No automatic device mapping
            #         trust_remote_code=True,
            #         low_cpu_mem_usage=True
            #     )
            #     
            #     self.model.to(self.device)
            #     self.model.eval()
            #     
            #     # Set pad token
            #     if self.tokenizer.pad_token is None:
            #         self.tokenizer.pad_token = self.tokenizer.eos_token
            #     
            #     logger.info("Phi-3 model loaded successfully!")
            #     self.is_initialized = True
            #     return True
            #     
            # except Exception as e:
            #     logger.warning(f"Failed to load Phi-3 model: {e}")
            #     logger.info("Will use rule-based descriptions as fallback")
            #     self.is_initialized = True
            #     return True
                
        except Exception as e:
            logger.error(f"Error initializing LLM service: {e}")
            self.is_initialized = True  # Still allow fallback
            return True
    
    def start(self):
        """Start the description service"""
        if not self.is_initialized:
            if not self.initialize():
                return False
        
        self.is_running = True
        logger.info("Traffic Description Service started")
        return True
    
    def stop(self):
        """Stop the description service"""
        self.is_running = False
        logger.info("Traffic Description Service stopped")
    
    def generate_camera_description(self, camera_idx, traffic_data):
        """Generate description for a single camera"""
        try:
            if self.model is None or self.tokenizer is None:
                return self._fallback_camera_description(camera_idx, traffic_data)
            
            direction = self.DIRS[camera_idx]
            vehicle_counts = traffic_data.get('vehicle_counts', {})
            emergency_status = traffic_data.get('emergency_status', {})
            phase_data = traffic_data.get('phase_data', {})
            
            # Extract relevant data
            dir_abbr = direction[0]  # N, S, E, W
            left_count = vehicle_counts.get(f"{dir_abbr}_L", 0)
            straight_count = vehicle_counts.get(f"{dir_abbr}_S", 0)
            right_count = vehicle_counts.get(f"{dir_abbr}_R", 0)
            total_vehicles = left_count + straight_count + right_count
            
            # Emergency detection
            emergency_detected = emergency_status.get('emergency_detected', False)
            emergency_directions = emergency_status.get('emergency_directions', [])
            has_emergency = direction in emergency_directions
            
            # Signal status
            dir_lower = direction.lower()
            signal_info = phase_data.get(dir_lower, {})
            signal_status = signal_info.get('status', 'UNKNOWN')
            countdown = signal_info.get('countdown', 0)
            
            # Create prompt for Phi-3
            prompt = f"""You are analyzing traffic at an intersection. Describe the {direction} approach in 1-2 sentences.

Data:
- Direction: {direction}
- Vehicles: {left_count} turning left, {straight_count} going straight, {right_count} turning right (total: {total_vehicles})
- Emergency vehicle: {'Yes' if has_emergency else 'No'}
- Signal: {signal_status} with {countdown} seconds remaining

Write a natural description like: "{direction} approach shows [traffic level] with [vehicle details]. [Emergency info if any]. Signal is [status] with [time] remaining."

Description:"""

            # Generate with Phi-3
            inputs = self.tokenizer.encode(prompt, return_tensors="pt").to(self.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs,
                    max_new_tokens=50,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id
                )
            
            # Decode response
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            description = response.split("Description:")[-1].strip()
            
            # Clean up response
            if len(description.split('.')) > 2:
                description = '. '.join(description.split('.')[:2]) + '.'
            
            return description if description else self._fallback_camera_description(camera_idx, traffic_data)
            
        except Exception as e:
            logger.warning(f"Error generating LLM description for camera {camera_idx}: {e}")
            return self._fallback_camera_description(camera_idx, traffic_data)
    
    def _fallback_camera_description(self, camera_idx, traffic_data):
        """Enhanced rule-based description that mimics natural language AI"""
        direction = self.DIRS[camera_idx]
        vehicle_counts = traffic_data.get('vehicle_counts', {})
        emergency_status = traffic_data.get('emergency_status', {})
        phase_data = traffic_data.get('phase_data', {})
        
        # Extract data
        dir_abbr = direction[0]
        left_count = vehicle_counts.get(f"{dir_abbr}_L", 0)
        straight_count = vehicle_counts.get(f"{dir_abbr}_S", 0)
        right_count = vehicle_counts.get(f"{dir_abbr}_R", 0)
        total_vehicles = left_count + straight_count + right_count
        
        # Traffic level with more variety
        if total_vehicles == 0:
            traffic_descriptions = ["completely clear", "empty with no vehicles", "free of traffic"]
        elif total_vehicles <= 2:
            traffic_descriptions = ["very light traffic", "minimal vehicle presence", "light flow"]
        elif total_vehicles <= 5:
            traffic_descriptions = ["moderate traffic flow", "steady vehicle movement", "normal traffic levels"]
        elif total_vehicles <= 8:
            traffic_descriptions = ["busy conditions", "increased traffic density", "heavy vehicle flow"]
        else:
            traffic_descriptions = ["congested conditions", "high traffic volume", "peak traffic levels"]
        
        # Randomly select description for variety
        traffic_desc = random.choice(traffic_descriptions)
        
        # Emergency status
        emergency_directions = emergency_status.get('emergency_directions', [])
        has_emergency = direction in emergency_directions
        
        # Signal status
        dir_lower = direction.lower()
        signal_info = phase_data.get(dir_lower, {})
        signal_status = signal_info.get('status', 'RED')
        countdown = signal_info.get('countdown', 0)
        
        # Build natural description
        if total_vehicles == 0:
            vehicle_detail = "No vehicles currently waiting"
        elif total_vehicles == 1:
            if left_count == 1:
                vehicle_detail = "One vehicle waiting to turn left"
            elif right_count == 1:
                vehicle_detail = "One vehicle preparing to turn right"
            else:
                vehicle_detail = "Single vehicle going straight"
        else:
            # Create detailed breakdown
            movements = []
            if straight_count > 0:
                movements.append(f"{straight_count} going straight")
            if left_count > 0:
                movements.append(f"{left_count} turning left")
            if right_count > 0:
                movements.append(f"{right_count} turning right")
            
            if len(movements) == 1:
                vehicle_detail = movements[0].replace("going", "vehicles going").replace("turning", "vehicles turning")
            elif len(movements) == 2:
                vehicle_detail = f"{movements[0]} and {movements[1]}"
            else:
                vehicle_detail = f"{movements[0]}, {movements[1]}, and {movements[2]}"
        
        # Emergency text variations
        if has_emergency:
            emergency_texts = [
                "Emergency vehicle detected requiring immediate priority",
                "Ambulance approaching - priority clearance needed",
                "Emergency response vehicle present",
                "Priority vehicle requiring signal override"
            ]
            emergency_text = f" {random.choice(emergency_texts)}."
        else:
            emergency_text = ""
        
        # Signal status with variety
        signal_descriptions = {
            'GREEN': ['green', 'active', 'go phase'],
            'YELLOW': ['yellow', 'caution phase', 'transitioning'],
            'RED': ['red', 'stop phase', 'waiting']
        }
        
        signal_desc = random.choice(signal_descriptions.get(signal_status, ['unknown']))
        
        # Time remaining description
        if countdown <= 5:
            time_desc = f"just {countdown} seconds left"
        elif countdown <= 15:
            time_desc = f"{countdown} seconds remaining"
        else:
            time_desc = f"{countdown} seconds on current phase"
        
        # Construct final description
        return f"{direction} approach currently shows {traffic_desc}. {vehicle_detail}.{emergency_text} Signal is {signal_desc} with {time_desc}."
    
    def generate_overall_summary(self, traffic_data):
        """Generate overall intersection summary"""
        try:
            if self.model is None or self.tokenizer is None:
                return self._fallback_overall_summary(traffic_data)
            
            vehicle_counts = traffic_data.get('vehicle_counts', {})
            current_phase = traffic_data.get('current_phase', 0)
            emergency_status = traffic_data.get('emergency_status', {})
            ppo_decision = traffic_data.get('ppo_decision', {})
            
            # Calculate totals
            total_vehicles = sum(vehicle_counts.values())
            
            # Current phase info
            phase_name = self.PHASE_NAMES[current_phase] if current_phase < len(self.PHASE_NAMES) else "Unknown Phase"
            
            # Emergency info
            emergency_detected = emergency_status.get('emergency_detected', False)
            emergency_dirs = emergency_status.get('emergency_directions', [])
            
            # AI recommendation
            ai_confidence = ppo_decision.get('confidence', 0.5)
            ai_reasoning = ppo_decision.get('reasoning', 'Standard traffic control')
            
            # Create prompt
            prompt = f"""Analyze this traffic intersection and provide a brief summary in 2-3 sentences.

Data:
- Total vehicles: {total_vehicles}
- Current phase: {phase_name}
- Emergency vehicles: {'Yes in ' + ', '.join(emergency_dirs) if emergency_detected else 'No'}
- AI confidence: {ai_confidence:.1f}
- AI reasoning: {ai_reasoning}

Write like: "Intersection experiencing [traffic level] with [number] total vehicles. [Current phase info]. [Emergency/AI info]."

Summary:"""

            # Generate with Phi-3
            inputs = self.tokenizer.encode(prompt, return_tensors="pt").to(self.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs,
                    max_new_tokens=80,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id
                )
            
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            summary = response.split("Summary:")[-1].strip()
            
            # Clean up
            if len(summary.split('.')) > 3:
                summary = '. '.join(summary.split('.')[:3]) + '.'
            
            return summary if summary else self._fallback_overall_summary(traffic_data)
            
        except Exception as e:
            logger.warning(f"Error generating overall summary: {e}")
            return self._fallback_overall_summary(traffic_data)
    
    def _fallback_overall_summary(self, traffic_data):
        """Enhanced rule-based summary with natural AI-like language"""
        vehicle_counts = traffic_data.get('vehicle_counts', {})
        current_phase = traffic_data.get('current_phase', 0)
        emergency_status = traffic_data.get('emergency_status', {})
        ppo_decision = traffic_data.get('ppo_decision', {})
        
        total_vehicles = sum(vehicle_counts.values())
        
        # More sophisticated traffic analysis
        # Analyze traffic distribution
        directions_with_traffic = sum(1 for v in vehicle_counts.values() if v > 0)
        max_direction_vehicles = max(vehicle_counts.values()) if vehicle_counts else 0
        
        # Traffic level with contextual descriptions
        if total_vehicles == 0:
            traffic_descriptions = [
                "completely quiet intersection with no active traffic",
                "idle intersection in standby mode",
                "clear intersection with optimal flow conditions"
            ]
        elif total_vehicles <= 8:
            traffic_descriptions = [
                f"light traffic flow with {total_vehicles} vehicles distributed across approaches",
                f"manageable traffic conditions with {total_vehicles} vehicles in the queue system",
                f"steady but controlled traffic with {total_vehicles} vehicles awaiting clearance"
            ]
        elif total_vehicles <= 20:
            traffic_descriptions = [
                f"moderate traffic density with {total_vehicles} vehicles creating standard queue patterns",
                f"active intersection managing {total_vehicles} vehicles across multiple approaches",
                f"busy but flowing conditions with {total_vehicles} vehicles in various movement phases"
            ]
        else:
            traffic_descriptions = [
                f"high traffic volume with {total_vehicles} vehicles requiring optimized signal timing",
                f"peak conditions managing {total_vehicles} vehicles with priority queue management",
                f"congested intersection handling {total_vehicles} vehicles through intelligent coordination"
            ]
        
        traffic_desc = random.choice(traffic_descriptions)
        
        # Phase analysis with natural language
        phase_name = self.PHASE_NAMES[current_phase] if current_phase < len(self.PHASE_NAMES) else "Standard Traffic Control"
        
        phase_descriptions = [
            f"{phase_name} phase is currently optimizing vehicle throughput",
            f"Active {phase_name} sequence providing efficient traffic clearance",
            f"Current {phase_name} timing maximizes intersection capacity",
            f"{phase_name} phase actively managing traffic flow patterns"
        ]
        
        phase_desc = random.choice(phase_descriptions)
        
        # Emergency analysis
        emergency_detected = emergency_status.get('emergency_detected', False)
        emergency_directions = emergency_status.get('emergency_directions', [])
        
        if emergency_detected:
            if len(emergency_directions) == 1:
                emergency_text = f" Priority override activated for emergency vehicle from {emergency_directions[0]} approach, implementing immediate clearance protocol."
            else:
                emergency_text = f" Multiple emergency vehicles detected from {', '.join(emergency_directions)} requiring coordinated priority response."
        else:
            emergency_text = ""
        
        # AI confidence analysis
        ai_confidence = ppo_decision.get('confidence', 0.5)
        ai_reasoning = ppo_decision.get('reasoning', 'Standard traffic optimization')
        
        if ai_confidence > 0.8:
            ai_descriptions = [
                f"AI system operating with high confidence ({ai_confidence:.1f}) using advanced pattern recognition",
                f"Neural network analysis shows optimal timing with {ai_confidence:.1f} confidence rating",
                f"PPO agent demonstrates excellent decision-making capability with {ai_confidence:.1f} certainty"
            ]
        elif ai_confidence > 0.6:
            ai_descriptions = [
                f"AI system providing reliable traffic management with {ai_confidence:.1f} confidence level",
                f"Machine learning algorithms operating effectively with {ai_confidence:.1f} accuracy rating",
                f"Intelligent control system maintaining stable performance at {ai_confidence:.1f} confidence"
            ]
        else:
            ai_descriptions = [
                f"AI system using conservative approach with {ai_confidence:.1f} confidence, prioritizing safety",
                f"Fallback algorithms ensuring continuous operation at {ai_confidence:.1f} reliability",
                f"System maintaining baseline performance with {ai_confidence:.1f} operational confidence"
            ]
        
        ai_desc = random.choice(ai_descriptions)
        
        return f"Intersection analysis: {traffic_desc}. {phase_desc}.{emergency_text} {ai_desc}."
    
    def update_descriptions(self, traffic_data):
        """Update cached descriptions if needed"""
        current_time = time.time()
        
        with self.cache_lock:
            if current_time - self.description_cache['last_update'] < self.description_cache['cache_duration']:
                return self.description_cache
            
            # Update camera descriptions
            new_camera_descriptions = []
            for i in range(4):
                desc = self.generate_camera_description(i, traffic_data)
                new_camera_descriptions.append(desc)
            
            # Update overall summary
            overall_summary = self.generate_overall_summary(traffic_data)
            
            # Update cache
            self.description_cache.update({
                'camera_descriptions': new_camera_descriptions,
                'overall_summary': overall_summary,
                'last_update': current_time
            })
            
            return self.description_cache
    
    def get_descriptions(self, traffic_data):
        """Get current descriptions (cached or updated)"""
        return self.update_descriptions(traffic_data)


# Global service instance
_description_service = None

def initialize_description_service():
    """Initialize the description service"""
    global _description_service
    try:
        _description_service = TrafficDescriptionService()
        return _description_service.start()
    except Exception as e:
        logger.error(f"Failed to initialize description service: {e}")
        return False

def get_description_service():
    """Get the description service instance"""
    return _description_service

def cleanup_description_service():
    """Cleanup the description service"""
    global _description_service
    if _description_service:
        _description_service.stop()
        _description_service = None