// Customer Registration Page JavaScript

let localStream = null;
let capturedBase64 = null;

document.addEventListener('DOMContentLoaded', () => {
    initializeWebcam();
});

// Initialize device webcam
async function initializeWebcam() {
    const video = document.getElementById('webcam-stream');
    const loadingText = document.getElementById('camera-loading');
    const scanner = document.getElementById('scanner-outline');
    
    // Reset state
    capturedBase64 = null;
    document.getElementById('register-submit-btn').disabled = true;
    document.getElementById('capture-preview-box').style.display = 'none';

    if (localStream) {
        localStream.getTracks().forEach(track => track.stop());
    }

    loadingText.style.display = 'flex';
    video.style.display = 'none';
    scanner.style.borderStyle = 'dashed';
    scanner.classList.remove('scanning');

    try {
        const constraints = {
            video: {
                width: { ideal: 640 },
                height: { ideal: 480 },
                facingMode: "user"
            },
            audio: false
        };
        
        localStream = await navigator.mediaDevices.getUserMedia(constraints);
        video.srcObject = localStream;
        video.style.display = 'block';
        loadingText.style.display = 'none';
        
        // Add styling scan effect
        scanner.classList.add('scanning');
        scanner.style.borderStyle = 'solid';
        
        console.log("Webcam stream started successfully.");
    } catch (err) {
        console.error("Webcam initiation failed:", err);
        loadingText.style.display = 'flex';
        loadingText.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="#ff0055" stroke-width="2" style="width:48px;height:48px;">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                <line x1="12" y1="9" x2="12" y2="13"/>
                <line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
            <span style="color:#ff0055; font-weight:600;">Camera Blocked or Not Found</span>
            <span style="font-size:0.8rem; color:var(--text-muted);">Please grant camera permissions or check device connection.</span>
        `;
    }
}

// Capture current webcam frame and export to base64
function captureSnapshot() {
    const video = document.getElementById('webcam-stream');
    const canvas = document.getElementById('snapshot-canvas');
    const previewBox = document.getElementById('capture-preview-box');
    const previewImg = document.getElementById('capture-preview');

    if (!localStream || video.style.display === 'none') {
        showNotification('danger', 'Cannot capture frame. Please make sure the camera is running.');
        return;
    }

    const context = canvas.getContext('2d');
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;

    // Draw frame to canvas
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    // Export to base64 data URL (JPEG format)
    capturedBase64 = canvas.toDataURL('image/jpeg', 0.9);
    
    // Set preview image source
    previewImg.src = capturedBase64;
    previewBox.style.display = 'block';
    previewImg.style.transform = 'scaleX(-1)'; // Mirror for webcam
    
    checkFormValidation();
    
    showNotification('success', 'Photo captured! Ready for registration.');
    
    // Simple UI pulse feedback
    const outline = document.getElementById('scanner-outline');
    outline.style.borderColor = 'var(--secondary)';
    setTimeout(() => {
        outline.style.borderColor = 'var(--primary)';
    }, 400);
}

// Handlers for file selection changes
function onProfileFileSelected() {
    const fileInput = document.getElementById('reg-photo-file');
    const previewBox = document.getElementById('capture-preview-box');
    const previewImg = document.getElementById('capture-preview');
    
    if (fileInput.files && fileInput.files[0]) {
        // We no longer reset camera capture state here because both are required
        // capturedBase64 = null;
        
        const reader = new FileReader();
        reader.onload = function(e) {
            previewImg.src = e.target.result;
            previewBox.style.display = 'block';
            // Mirror off for uploaded images
            previewImg.style.transform = 'none';
        };
        reader.readAsDataURL(fileInput.files[0]);
        showNotification('success', 'Profile photo file selected.');
    } else {
        previewBox.style.display = 'none';
    }
    checkFormValidation();
}

function onIdFileSelected() {
    showNotification('success', 'Government ID Document selected.');
    checkFormValidation();
}

// Form validation check
function checkFormValidation() {
    const submitBtn = document.getElementById('register-submit-btn');
    const profileFile = document.getElementById('reg-photo-file').files[0];
    const idFile = document.getElementById('reg-id-file').files[0];
    
    const hasProfile = profileFile;
    const hasLive = capturedBase64;
    const hasId = idFile;
    
    if ((hasProfile || hasLive) && hasId) {
        submitBtn.disabled = false;
    } else {
        submitBtn.disabled = true;
    }
}

// Submit registration form details to backend
async function submitRegistration(event) {
    event.preventDefault();
    
    const idType = document.getElementById('reg-id-type').value;
    
    const profileFileInput = document.getElementById('reg-photo-file');
    const idFileInput = document.getElementById('reg-id-file');
    const submitBtn = document.getElementById('register-submit-btn');

    submitBtn.disabled = true;
    submitBtn.innerText = 'Registering Profile...';

    const formData = new FormData();
    formData.append('id_type', idType);
    
    // Add profile photo (must be a file)
    if (profileFileInput.files && profileFileInput.files[0]) {
        formData.append('photo_file', profileFileInput.files[0]);
    }

    // Add live webcam capture
    if (capturedBase64) {
        formData.append('live_photo', capturedBase64);
    }
    
    if (!profileFileInput.files[0] && !capturedBase64) {
        showNotification('danger', 'Profile photo or live facial verification is required.');
        submitBtn.disabled = false;
        return;
    }

    // Add ID document file
    if (idFileInput.files && idFileInput.files[0]) {
        formData.append('id_photo_file', idFileInput.files[0]);
    } else {
        showNotification('danger', 'Government ID Document file is required.');
        submitBtn.disabled = false;
        return;
    }

    try {
        const response = await fetch('/api/register_customer', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            let extractedInfo = '';
            if (result.extracted) {
                extractedInfo = ` (Extracted: ${result.extracted.name}, ${result.extracted.age} yrs)`;
            }
            showNotification('success', `Success: ${result.message}${extractedInfo}`);
            // Reset form details
            document.getElementById('register-form').reset();
            capturedBase64 = null;
            document.getElementById('capture-preview-box').style.display = 'none';
            document.getElementById('register-submit-btn').disabled = true;
            // Clear inputs
            profileFileInput.value = '';
            idFileInput.value = '';
        } else {
            showNotification('danger', `Registration Failed: ${result.message}`);
            submitBtn.disabled = false;
        }
    } catch (err) {
        console.error("Registration request error:", err);
        showNotification('danger', 'Server connection error occurred. Could not save.');
        submitBtn.disabled = false;
    } finally {
        submitBtn.innerHTML = `
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 0.25rem;">
                <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
                <polyline points="17 21 17 13 7 13 7 21"/>
                <polyline points="7 3 7 8 15 8"/>
            </svg>
            Secure Save & Register
        `;
    }
}

// Dev trigger to populate database
async function populateDatabase() {
    try {
        const response = await fetch('/api/dev/populate', {
            method: 'POST'
        });
        const result = await response.json();
        if (result.success) {
            showNotification('success', result.message);
        } else {
            showNotification('danger', result.message);
        }
    } catch (err) {
        showNotification('danger', 'Failed to connect to backend populator.');
    }
}

// Display helper notification banner
function showNotification(type, message) {
    const banner = document.getElementById('register-notification');
    const textSpan = banner.querySelector('.notification-text');
    
    banner.className = `notification-banner ${type}`;
    textSpan.innerText = message;
    banner.style.display = 'flex';
    
    // Auto scroll to notification
    banner.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}
