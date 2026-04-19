// Get DOM elements
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const browseBtn = document.getElementById('browseBtn');
const previewSection = document.getElementById('previewSection');
const imagePreview = document.getElementById('imagePreview');
const analyzeBtn = document.getElementById('analyzeBtn');
const clearBtn = document.getElementById('clearBtn');
const loading = document.getElementById('loading');
const resultsSection = document.getElementById('resultsSection');
const errorSection = document.getElementById('errorSection');
const errorMessage = document.getElementById('errorMessage');
const retryBtn = document.getElementById('retryBtn');
const newAnalysisBtn = document.getElementById('newAnalysisBtn');

let selectedFile = null;

// Upload area click to open file dialog
uploadArea.addEventListener('click', () => {
    fileInput.click();
});

// Browse button click
browseBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    fileInput.click();
});

// File input change
fileInput.addEventListener('change', (e) => {
    handleFileSelect(e.target.files[0]);
});

// Drag and drop functionality
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragover');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    
    const file = e.dataTransfer.files[0];
    handleFileSelect(file);
});

// Handle file selection
function handleFileSelect(file) {
    if (!file) return;
    
    // Validate file type
    const validTypes = ['image/png', 'image/jpeg', 'image/jpg'];
    if (!validTypes.includes(file.type)) {
        showError('Invalid file type. Please upload PNG, JPG, or JPEG image.');
        return;
    }
    
    // Validate file size (16MB)
    if (file.size > 16 * 1024 * 1024) {
        showError('File size exceeds 16MB. Please upload a smaller image.');
        return;
    }
    
    selectedFile = file;
    
    // Show preview
    const reader = new FileReader();
    reader.onload = (e) => {
        imagePreview.src = e.target.result;
        document.querySelector('.upload-section').style.display = 'none';
        previewSection.style.display = 'block';
        hideError();
        hideResults();
    };
    reader.readAsDataURL(file);
}

// Clear button
clearBtn.addEventListener('click', () => {
    resetUI();
});

// Analyze button
analyzeBtn.addEventListener('click', () => {
    if (!selectedFile) return;
    analyzeImage();
});

// New analysis button
newAnalysisBtn.addEventListener('click', () => {
    resetUI();
});

// Retry button
retryBtn.addEventListener('click', () => {
    hideError();
    document.querySelector('.upload-section').style.display = 'block';
});

// Collect questionnaire data
function collectQuestionnaireData() {
    const formData = new FormData();
    formData.append('file', selectedFile);
    
    // Get all radio button values
    const burning = document.querySelector('input[name="burning"]:checked')?.value || 'no';
    const itching = document.querySelector('input[name="itching"]:checked')?.value || 'no';
    const watery_eyes = document.querySelector('input[name="watery_eyes"]:checked')?.value || 'no';
    const sensitivity = document.querySelector('input[name="sensitivity"]:checked')?.value || 'no';
    const redness_visible = document.querySelector('input[name="redness_visible"]:checked')?.value || 'no';
    const contact_lens = document.querySelector('input[name="contact_lens"]:checked')?.value || 'no';
    
    // Get select values
    const screen_time = document.getElementById('screenTime').value;
    const sleep_hours = document.getElementById('sleepHours').value;
    
    // Append to form data
    formData.append('burning', burning);
    formData.append('itching', itching);
    formData.append('watery_eyes', watery_eyes);
    formData.append('sensitivity', sensitivity);
    formData.append('redness_visible', redness_visible);
    formData.append('contact_lens', contact_lens);
    formData.append('screen_time', screen_time);
    formData.append('sleep_hours', sleep_hours);
    
    return formData;
}

// Analyze image function
async function analyzeImage() {
    // Hide other sections
    previewSection.style.display = 'none';
    hideError();
    hideResults();
    
    // Show loading
    loading.style.display = 'block';
    
    // Collect form data with questionnaire
    const formData = collectQuestionnaireData();
    
    try {
        // Send request to backend
        const response = await fetch('/predict', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        // Hide loading
        loading.style.display = 'none';
        
        if (response.ok) {
            // Show results
            displayResults(data);
        } else {
            // Show error
            showError(data.error || 'An error occurred during analysis.');
        }
    } catch (error) {
        loading.style.display = 'none';
        showError('Failed to connect to server. Please try again.');
        console.error('Error:', error);
    }
}

// Display results
function displayResults(data) {
    const diagnosis = data.diagnosis;
    
    // Update overall status
    const overallStatus = document.getElementById('overallStatus');
    const statusText = document.getElementById('statusText');
    const overallScoreValue = document.getElementById('overallScoreValue');
    
    statusText.textContent = diagnosis.status;
    overallScoreValue.textContent = diagnosis.overall_score;
    
    // Set status color
    if (diagnosis.severity === 'low') {
        overallStatus.className = 'overall-status healthy';
    } else if (diagnosis.severity === 'moderate') {
        overallStatus.className = 'overall-status moderate';
    } else {
        overallStatus.className = 'overall-status attention';
    }
    
    // Update detection scores with circular progress
    updateCircularProgress('rednessProgress', data.redness_score, 'redness');
    document.getElementById('rednessValue').textContent = data.redness_score + '%';
    document.getElementById('rednessStatus').textContent = data.redness_score > 50 ? 'Detected' : 'Normal';
    
    updateCircularProgress('fatigueProgress', data.fatigue_score, 'fatigue');
    document.getElementById('fatigueValue').textContent = data.fatigue_score + '%';
    document.getElementById('fatigueStatus').textContent = data.fatigue_status;
    
    updateCircularProgress('drynessProgress', data.dryness_score, 'dryness');
    document.getElementById('drynessValue').textContent = data.dryness_score + '%';
    document.getElementById('drynessStatus').textContent = data.dryness_status;
    
    // Display conditions
    const conditionsList = document.getElementById('conditionsList');
    if (diagnosis.conditions.length > 0) {
        conditionsList.innerHTML = '<div class="conditions-header">Detected Conditions:</div>' +
            diagnosis.conditions.map(c => `<span class="condition-badge">${c}</span>`).join('');
    } else {
        conditionsList.innerHTML = '<div class="no-conditions">✓ No significant conditions detected</div>';
    }
    
    // Display findings
    const findingsList = document.getElementById('findingsList');
    if (diagnosis.findings.length > 0) {
        findingsList.innerHTML = '<ul>' + 
            diagnosis.findings.map(f => `<li>${f}</li>`).join('') +
            '</ul>';
    } else {
        findingsList.innerHTML = '';
    }
    
    // Display recommendations
    const recommendationsList = document.getElementById('recommendationsList');
    recommendationsList.innerHTML = '<ul class="recommendations">' +
        diagnosis.recommendations.map((rec, index) => {
            const isUrgent = rec.includes('⚠️') || rec.includes('🚨');
            return `<li class="${isUrgent ? 'urgent' : ''}">${rec}</li>`;
        }).join('') +
        '</ul>';
    
    // Display medical disclaimer
    const medicalNote = document.getElementById('medicalNote');
    if (diagnosis.medical_note) {
        medicalNote.textContent = diagnosis.medical_note;
    }
    
    // Update analyzed image
    const analyzedImage = document.getElementById('analyzedImage');
    analyzedImage.src = data.image;
    
    // Show results section
    resultsSection.style.display = 'block';
    
    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

// Update circular progress
function updateCircularProgress(elementId, percentage, type) {
    const element = document.getElementById(elementId);
    const degrees = (percentage / 100) * 360;
    
    // Determine color based on type and percentage
    let color;
    if (percentage > 70) {
        color = '#e74c3c';
    } else if (percentage > 50) {
        color = '#f39c12';
    } else {
        color = '#27ae60';
    }
    
    element.style.background = `conic-gradient(${color} ${degrees}deg, #e0e0e0 ${degrees}deg)`;
}

// Show error
function showError(message) {
    errorMessage.textContent = message;
    errorSection.style.display = 'block';
    previewSection.style.display = 'none';
    loading.style.display = 'none';
}

// Hide error
function hideError() {
    errorSection.style.display = 'none';
}

// Hide results
function hideResults() {
    resultsSection.style.display = 'none';
}

// Reset UI
function resetUI() {
    selectedFile = null;
    fileInput.value = '';
    imagePreview.src = '';
    
    // Reset questionnaire
    document.querySelectorAll('input[type="radio"]').forEach(radio => {
        if (radio.value === 'no') {
            radio.checked = true;
        } else {
            radio.checked = false;
        }
    });
    document.getElementById('screenTime').selectedIndex = 0;
    document.getElementById('sleepHours').selectedIndex = 0;
    
    document.querySelector('.upload-section').style.display = 'block';
    previewSection.style.display = 'none';
    loading.style.display = 'none';
    hideError();
    hideResults();
    
    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}
