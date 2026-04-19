// Global variables
let currentExercise = null;
let sessionId = null;
let webcamStream = null;
let processingInterval = null;
let isProcessing = false;

// Get URL parameters
function getUrlParameter(name) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(name);
}

// Load exercise details
async function loadExerciseDetails() {
    const exerciseId = getUrlParameter('id');
    
    if (!exerciseId) {
        window.location.href = '/';
        return;
    }
    
    try {
        const response = await fetch(`/api/exercise/${exerciseId}`);
        currentExercise = await response.json();
        
        // Update UI with exercise details
        document.getElementById('exerciseName').textContent = currentExercise.name;
        document.getElementById('demoImage').src = getExerciseImage(currentExercise.id);
        document.getElementById('benefitsText').textContent = currentExercise.benefits;
        
        const instructionsList = document.getElementById('instructionsList');
        instructionsList.innerHTML = '';
        currentExercise.instructions.forEach(instruction => {
            const li = document.createElement('li');
            li.textContent = instruction;
            instructionsList.appendChild(li);
        });
        
    } catch (error) {
        console.error('Error loading exercise:', error);
        alert('Failed to load exercise details');
        window.location.href = '/';
    }
}

function getExerciseImage(exerciseId) {
    const images = {
        'blink': '/static/demo/Blink Eye.jpg',
        'left_right': '/static/demo/Left Right Gaze.jpg',
        'up_down': '/static/demo/Up Down Gaze.webp',
        'near_far': '/static/demo/Near far.webp',
        'palming': '/static/demo/Plaming.webp'
    };
    return images[exerciseId] || '/static/demo/Blink Eye.jpg';
}

// Start exercise session
async function startSession() {
    try {
        // Request webcam access
        webcamStream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: 1280 },
                height: { ideal: 720 },
                facingMode: 'user'
            }
        });
        
        const videoElement = document.getElementById('webcam');
        videoElement.srcObject = webcamStream;
        
    } catch (error) {
        console.error('Error accessing webcam:', error);
        alert('Failed to access webcam. Please ensure camera permissions are granted.');
        return;
    }
    
    try {
        // Start session on backend
        const response = await fetch('/api/session/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ exercise_id: currentExercise.id })
        });
        
        if (!response.ok) {
            throw new Error('Failed to start session on server');
        }
        
        const data = await response.json();
        sessionId = data.session_id;
        
        // Switch to session view
        document.getElementById('instructionsSection').style.display = 'none';
        document.getElementById('sessionSection').style.display = 'block';
        
        // Start processing frames
        startFrameProcessing();
        
    } catch (error) {
        console.error('Error starting session:', error);
        alert('Failed to start exercise session. Please try again.');
        
        // Clean up webcam if session start failed
        if (webcamStream) {
            webcamStream.getTracks().forEach(track => track.stop());
            webcamStream = null;
        }
    }
}

// Process video frames
function startFrameProcessing() {
    const videoElement = document.getElementById('webcam');
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    
    processingInterval = setInterval(async () => {
        if (isProcessing || !videoElement.videoWidth) return;
        
        isProcessing = true;
        
        try {
            // Capture frame
            canvas.width = videoElement.videoWidth;
            canvas.height = videoElement.videoHeight;
            ctx.drawImage(videoElement, 0, 0);
            
            const frameData = canvas.toDataURL('image/jpeg', 0.8);
            
            // Send to backend for processing
            const response = await fetch('/api/session/process_frame', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sessionId,
                    frame: frameData
                })
            });
            
            const result = await response.json();
            
            // Update UI
            if (result.success) {
                document.getElementById('repsCount').textContent = result.reps;
                document.getElementById('accuracyValue').textContent = 
                    result.accuracy > 0 ? `${result.accuracy}%` : '-';
                document.getElementById('progressValue').textContent = result.progress || '-';
                document.getElementById('feedbackBox').textContent = result.feedback;
                
                // Change feedback box color based on status
                const feedbackBox = document.getElementById('feedbackBox');
                if (result.feedback_color === 'success') {
                    feedbackBox.style.background = 'linear-gradient(135deg, rgba(16, 185, 129, 0.95) 0%, rgba(5, 150, 105, 0.95) 100%)';
                } else if (result.feedback_color === 'warning') {
                    feedbackBox.style.background = 'linear-gradient(135deg, rgba(245, 158, 11, 0.95) 0%, rgba(217, 119, 6, 0.95) 100%)';
                } else if (result.feedback_color === 'danger') {
                    feedbackBox.style.background = 'linear-gradient(135deg, rgba(239, 68, 68, 0.95) 0%, rgba(220, 38, 38, 0.95) 100%)';
                } else {
                    feedbackBox.style.background = 'linear-gradient(135deg, rgba(99, 102, 241, 0.95) 0%, rgba(79, 70, 229, 0.95) 100%)';
                }
                
                // Show lighting warning if needed
                if (!result.lighting_ok && result.lighting_message) {
                    showTemporaryWarning(result.lighting_message);
                }
            } else {
                // Handle errors and warnings
                const feedbackBox = document.getElementById('feedbackBox');
                feedbackBox.textContent = result.message || 'No face detected';
                feedbackBox.style.background = 'linear-gradient(135deg, rgba(239, 68, 68, 0.95) 0%, rgba(220, 38, 38, 0.95) 100%)';
                
                document.getElementById('repsCount').textContent = result.reps || 0;
                
                // Show additional warning if needed
                if (result.lighting_message) {
                    showTemporaryWarning(result.lighting_message);
                }
            }
            
        } catch (error) {
            console.error('Error processing frame:', error);
            document.getElementById('feedbackBox').textContent = '⚠️ Processing error - please try again';
        } finally {
            isProcessing = false;
        }
    }, 200); // Process every 200ms (~5 fps)
}

// Show temporary warning message
function showTemporaryWarning(message) {
    let warningDiv = document.getElementById('lightingWarning');
    
    if (!warningDiv) {
        warningDiv = document.createElement('div');
        warningDiv.id = 'lightingWarning';
        warningDiv.style.cssText = `
            position: absolute;
            top: 80px;
            left: 50%;
            transform: translateX(-50%);
            background: linear-gradient(135deg, rgba(245, 158, 11, 0.95) 0%, rgba(217, 119, 6, 0.95) 100%);
            color: white;
            padding: 12px 24px;
            border-radius: 12px;
            font-weight: 600;
            font-size: 0.95rem;
            box-shadow: 0 4px 12px rgba(245, 158, 11, 0.4);
            z-index: 1000;
            pointer-events: none;
        `;
        document.querySelector('.video-container').appendChild(warningDiv);
    }
    
    warningDiv.textContent = '⚠️ ' + message;
    warningDiv.style.display = 'block';
    
    // Auto-hide after 3 seconds
    setTimeout(() => {
        if (warningDiv) {
            warningDiv.style.display = 'none';
        }
    }, 3000);
}

// Stop exercise session
async function stopSession() {
    // Stop processing
    if (processingInterval) {
        clearInterval(processingInterval);
        processingInterval = null;
    }
    
    // Stop webcam
    if (webcamStream) {
        webcamStream.getTracks().forEach(track => track.stop());
        webcamStream = null;
    }
    
    try {
        // Get session summary
        const response = await fetch('/api/session/stop', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId })
        });
        
        const summary = await response.json();
        
        // Display summary
        displaySummary(summary);
        
    } catch (error) {
        console.error('Error stopping session:', error);
        alert('Failed to get session summary');
    }
}

// Display session summary
function displaySummary(summary) {
    document.getElementById('sessionSection').style.display = 'none';
    document.getElementById('summarySection').style.display = 'block';
    
    document.getElementById('summaryExercise').textContent = summary.exercise_name;
    document.getElementById('summaryDuration').textContent = `${summary.duration}s`;
    document.getElementById('summaryReps').textContent = 
        `${summary.reps_completed} / ${summary.target_reps}`;
    document.getElementById('summaryAccuracy').textContent = `${summary.avg_accuracy}%`;
    document.getElementById('summaryScore').textContent = `${summary.score}`;
    
    // Add performance message
    let performanceMsg = '';
    if (summary.score >= 90) {
        performanceMsg = 'Excellent! 🌟';
    } else if (summary.score >= 75) {
        performanceMsg = 'Great job! 👍';
    } else if (summary.score >= 60) {
        performanceMsg = 'Good effort! 💪';
    } else {
        performanceMsg = 'Keep practicing! 📈';
    }
    
    const scoreDisplay = document.querySelector('.score-display');
    const msgElement = document.createElement('p');
    msgElement.textContent = performanceMsg;
    msgElement.style.marginTop = '10px';
    msgElement.style.fontSize = '1.2rem';
    scoreDisplay.appendChild(msgElement);
}

// Restart exercise
function restartExercise() {
    document.getElementById('summarySection').style.display = 'none';
    document.getElementById('instructionsSection').style.display = 'grid';
    
    // Reset stats
    document.getElementById('repsCount').textContent = '0';
    document.getElementById('accuracyValue').textContent = '-';
    document.getElementById('progressValue').textContent = '-';
    document.getElementById('feedbackBox').textContent = 'Position your face in front of the camera';
    document.getElementById('feedbackBox').style.background = 'rgba(102, 126, 234, 0.95)';
}

// Initialize page
document.addEventListener('DOMContentLoaded', () => {
    // Only load exercise details if we're on the exercise page
    if (window.location.pathname.includes('exercise')) {
        loadExerciseDetails();
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (webcamStream) {
        webcamStream.getTracks().forEach(track => track.stop());
    }
    if (processingInterval) {
        clearInterval(processingInterval);
    }
});
