/**
 * Enhanced File Upload Component
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM loaded - initializing file upload");
    initializeFileUpload();
    setupDirectFileInput();
});

/**
 * Sets up the direct file input for quick uploads
 */
function setupDirectFileInput() {
    const directFileInput = document.getElementById('direct-file-input');
    if (!directFileInput) {
        console.warn("Direct file input not found");
        return;
    }
    
    console.log("Setting up direct file input");
    
    directFileInput.addEventListener('change', function() {
        if (!this.files || this.files.length === 0) {
            console.warn("No files selected in direct input");
            return;
        }
        
        const file = this.files[0];
        console.log("File selected via direct input:", file.name);
        
        // Validate file type
        const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'application/pdf', 'image/svg+xml'];
        if (!validTypes.includes(file.type)) {
            alert('File type not supported. Please use JPG, PNG, or PDF files.');
            return;
        }
        
        // Validate file size (max 10MB)
        if (file.size > 10 * 1024 * 1024) {
            alert('File size exceeds the 10MB limit.');
            return;
        }
        
        // Create a loading indicator
        const previewList = document.getElementById('file-preview-list');
        if (previewList) {
            previewList.innerHTML = `
                <div class="flex items-center justify-center p-4">
                    <svg class="animate-spin h-8 w-8 text-green-500 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span>Processing your file...</span>
                </div>
            `;
            previewList.classList.remove('hidden');
        }
        
        // Process the file
        const reader = new FileReader();
        
        reader.onload = function(e) {
            const proofUploadInput = document.getElementById('proof-upload');
            if (proofUploadInput) {
                proofUploadInput.value = e.target.result;
                updateFilePreviewList(file, e.target.result);
                
                // Generate a unique filename for server-side storage
                const ext = file.name.split('.').pop().toLowerCase();
                const uniqueFileName = generateUniqueFileName(ext);
                const filePath = `trip_proofs/${uniqueFileName}`;
                
                // Store file path in the hidden input
                const filePathInput = document.getElementById('proof-file-path');
                if (filePathInput) {
                    filePathInput.value = filePath;
                }
            } else {
                console.error("Hidden proof upload input not found");
                if (previewList) {
                    previewList.innerHTML = `
                        <div class="text-red-600 p-4">
                            Error processing file. Please try again.
                        </div>
                    `;
                }
            }
        };
        
        reader.onerror = function() {
            console.error("Error reading file");
            if (previewList) {
                previewList.innerHTML = `
                    <div class="text-red-600 p-4">
                        Error processing file. Please try again.
                    </div>
                `;
            }
        };
        
        reader.readAsDataURL(file);
    });
}

/**
 * Initializes the modal file upload component
 */
function initializeFileUpload() {
    const fileUploadModal = document.getElementById('file-upload-modal');
    const fileDropArea = document.getElementById('file-drop-area');
    const browseFilesBtn = document.getElementById('browse-files-btn');
    const closeModalBtn = document.getElementById('close-modal-btn');
    const fileInput = document.getElementById('file-input');
    const uploadsList = document.getElementById('uploads-list');
    
    // Show modal when trigger is clicked
    document.querySelectorAll('.file-upload-trigger').forEach(trigger => {
        trigger.addEventListener('click', function(e) {
            e.preventDefault();
            if (fileUploadModal) {
                fileUploadModal.classList.remove('hidden');
                document.body.classList.add('modal-open');
            }
        });
    });
    
    // Close modal functionality
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', function() {
            fileUploadModal.classList.add('hidden');
            document.body.classList.remove('modal-open');
        });
    }
    
    // Close modal if clicked outside content area
    fileUploadModal?.addEventListener('click', function(e) {
        if (e.target === fileUploadModal) {
            fileUploadModal.classList.add('hidden');
            document.body.classList.remove('modal-open');
        }
    });
    
    // Trigger file input when browse button is clicked
    if (browseFilesBtn && fileInput) {
        browseFilesBtn.addEventListener('click', function() {
            fileInput.click();
        });
    }
    
    // Handle file selection via input
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            if (this.files && this.files.length > 0) {
                handleFiles(this.files);
            }
        });
    }
    
    // Setup drag and drop area
    if (fileDropArea) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            fileDropArea.addEventListener(eventName, preventDefaults, false);
        });
        
        ['dragenter', 'dragover'].forEach(eventName => {
            fileDropArea.addEventListener(eventName, highlight, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            fileDropArea.addEventListener(eventName, unhighlight, false);
        });
        
        fileDropArea.addEventListener('drop', handleDrop, false);
    }
    
    // Prevent default behaviors for drag events
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    // Highlight drop area when file is dragged over
    function highlight() {
        fileDropArea.classList.add('border-blue-500');
        fileDropArea.classList.remove('border-gray-300');
    }
    
    // Remove highlight when file is no longer over drop area
    function unhighlight() {
        fileDropArea.classList.remove('border-blue-500');
        fileDropArea.classList.add('border-gray-300');
    }
    
    // Handle file drop
    function handleDrop(e) {
        console.log("Files dropped");
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files && files.length > 0) {
            handleFiles(files);
        }
    }
    
    // Process the dropped or selected files
    function handleFiles(files) {
        if (!files.length) {
            console.warn("No files to process");
            return;
        }
        
        // Clear existing uploads list
        if (uploadsList) {
            uploadsList.innerHTML = '';
        }
        
        // We only handle one file at a time for trip proof
        const file = files[0];
        
        // Validate file type
        const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'application/pdf', 'image/svg+xml'];
        if (!validTypes.includes(file.type)) {
            showFileError(file.name, 'File type not supported');
            return;
        }
        
        // Validate file size (max 10MB)
        if (file.size > 10 * 1024 * 1024) {
            showFileError(file.name, 'File size exceeds the 10MB limit');
            return;
        }
        
        // Process file immediately
        processUploadedFile(file);
    }
    
    // Show error for invalid files
    function showFileError(fileName, errorMessage) {
        console.error(`File error: ${errorMessage} for file ${fileName}`);
        
        if (!uploadsList) return;
        
        const fileItem = document.createElement('div');
        fileItem.className = 'flex items-center justify-between p-2 mb-2';
        fileItem.innerHTML = `
            <div class="flex items-center">
                <div class="mr-3 text-red-500">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                    </svg>
                </div>
                <div>
                    <p class="text-sm font-medium text-gray-700">${fileName}</p>
                    <p class="text-xs text-red-500">${errorMessage}</p>
                </div>
            </div>
        `;
        
        uploadsList.appendChild(fileItem);
        
        // Remove error message after 5 seconds
        setTimeout(() => {
            if (fileItem.parentNode) {
                fileItem.remove();
            }
        }, 5000);
    }
    
    // Process uploaded file
    function processUploadedFile(file) {
        // Add a loading entry to the uploads list
        if (uploadsList) {
            uploadsList.innerHTML = `
                <div class="flex items-center justify-between p-2 mb-2">
                    <div class="flex items-center flex-grow">
                        <div class="mr-3">
                            <svg class="animate-spin h-5 w-5 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                        </div>
                        <div class="w-full">
                            <div class="flex justify-between">
                                <p class="text-sm font-medium text-gray-700">${file.name}</p>
                                <p class="text-xs text-gray-500">${formatFileSize(file.size)}</p>
                            </div>
                            <div class="mt-1 w-full bg-gray-200 rounded-full h-2">
                                <div id="file-progress" class="progress-bar bg-blue-500 h-2 rounded-full" style="width: 0%"></div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        // Process the file with FileReader
        const reader = new FileReader();
        
        reader.onprogress = function(e) {
            if (e.lengthComputable) {
                const percentLoaded = Math.round((e.loaded / e.total) * 100);
                const progressBar = document.getElementById('file-progress');
                if (progressBar) {
                    progressBar.style.width = `${percentLoaded}%`;
                }
            }
        };
        
        reader.onerror = function() {
            console.error(`Error reading file "${file.name}"`);
            
            if (uploadsList) {
                uploadsList.innerHTML = `
                    <div class="flex items-center justify-between p-2 mb-2">
                        <div class="flex items-center">
                            <div class="mr-3 text-red-500">
                                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                                </svg>
                            </div>
                            <div>
                                <p class="text-sm font-medium text-gray-700">${file.name}</p>
                                <p class="text-xs text-red-500">Error processing file</p>
                            </div>
                        </div>
                    </div>
                `;
            }
        };
        
        reader.onload = function(e) {
            console.log(`File "${file.name}" processed successfully`);
            
            // Update the hidden input field
            const proofUploadInput = document.getElementById('proof-upload');
            if (proofUploadInput) {
                // Set the base64 data as the hidden input value
                proofUploadInput.value = e.target.result;
                
                // Generate a unique filename for server-side storage
                const ext = file.name.split('.').pop().toLowerCase();
                const uniqueFileName = generateUniqueFileName(ext);
                const filePath = `trip_proofs/${uniqueFileName}`;
                
                // Store file path in the hidden input
                const filePathInput = document.getElementById('proof-file-path');
                if (filePathInput) {
                    filePathInput.value = filePath;
                }
                
                // Also add the file to the preview list
                updateFilePreviewList(file, e.target.result);
            }
            
            // Show success status in the uploads list
            if (uploadsList) {
                uploadsList.innerHTML = `
                    <div class="flex items-center justify-between p-2 mb-2">
                        <div class="flex items-center">
                            <div class="mr-3 text-green-500">
                                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                                </svg>
                            </div>
                            <div>
                                <p class="text-sm font-medium text-gray-700">${file.name}</p>
                                <p class="text-xs text-green-500">File processed successfully</p>
                            </div>
                        </div>
                    </div>
                `;
            }
            
            // Close the modal after a short delay to show success state
            setTimeout(() => {
                if (fileUploadModal) {
                    fileUploadModal.classList.add('hidden');
                    document.body.classList.remove('modal-open');
                }
            }, 500);
        };
        
        // Start reading the file as data URL
        reader.readAsDataURL(file);
    }
    
    // Format file size in a human-readable format
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }
}

/**
 * Generate a unique filename with UUID-like string
 */
function generateUniqueFileName(extension) {
    // Create a timestamp-based unique ID
    const timestamp = new Date().getTime();
    const randomStr = Math.random().toString(36).substring(2, 10);
    return `${timestamp}_${randomStr}.${extension}`;
}

/**
 * Update the preview list in the trip form with the uploaded file
 */
function updateFilePreviewList(file, dataUrl) {
    const previewList = document.getElementById('file-preview-list');
    if (!previewList) {
        console.error("File preview list not found");
        return;
    }
    
    console.log("Updating file preview list");
    
    // Clear existing previews
    previewList.innerHTML = '';
    
    // Show the preview list container
    previewList.classList.remove('hidden');
    
    // Create preview item
    const previewItem = document.createElement('div');
    previewItem.className = 'flex items-center justify-between p-3 border border-gray-200 rounded-lg bg-white';
    
    // Determine icon based on file type
    let icon;
    
    // For images, show a thumbnail
    if (file.type.startsWith('image/')) {
        icon = `<img src="${dataUrl}" class="h-16 w-16 object-cover rounded" alt="Preview">`;
    } else if (file.type === 'application/pdf') {
        icon = `
            <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 text-red-500" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd" />
            </svg>
        `;
    } else {
        icon = `
            <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 text-gray-400" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd" />
            </svg>
        `;
    }
    
    previewItem.innerHTML = `
        <div class="flex items-center">
            <div class="mr-3">
                ${icon}
            </div>
            <div>
                <p class="text-sm font-medium text-gray-700">${file.name}</p>
                <p class="text-xs text-gray-500">${formatFileSize(file.size)}</p>
                <p class="text-xs text-green-600 mt-1">✓ Ready to submit with your trip</p>
            </div>
        </div>
        <button type="button" class="text-gray-400 hover:text-red-500" id="remove-preview-file">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
            </svg>
        </button>
    `;
    
    previewList.appendChild(previewItem);
    
    // Add remove functionality
    const removeBtn = document.getElementById('remove-preview-file');
    if (removeBtn) {
        removeBtn.addEventListener('click', function() {
            // Clear the input fields
            const proofUploadInput = document.getElementById('proof-upload');
            if (proofUploadInput) {
                proofUploadInput.value = '';
            }
            
            const filePathInput = document.getElementById('proof-file-path');
            if (filePathInput) {
                filePathInput.value = '';
            }
            
            // Reset the file inputs
            const directFileInput = document.getElementById('direct-file-input');
            if (directFileInput) {
                directFileInput.value = '';
            }
            
            const fileInput = document.getElementById('file-input');
            if (fileInput) {
                fileInput.value = '';
            }
            
            // Remove the preview
            previewList.innerHTML = '';
            previewList.classList.add('hidden');
            
            // Show notification if addNotification is defined
            if (typeof addNotification === 'function') {
                addNotification('File removed', 'info');
            }
        });
    }
}

/**
 * Helper function to format file size
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
} 