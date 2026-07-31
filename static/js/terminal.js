// POS Terminal Page JavaScript

let webcamStream = null;
let currentCustomer = null;
let currentLimits = null;
let selectedQuantity = 0;
let checkoutStep = 1;

document.addEventListener('DOMContentLoaded', () => {
    // Listen for shop counter changes
    const shopSelect = document.getElementById('active-shop-select');
    if (shopSelect) {
        shopSelect.addEventListener('change', () => {
            resetTerminal();
        });
    }
});

// Start laptop camera and trigger face recognition scan
async function startCameraVerification() {
    const video = document.getElementById('terminal-webcam');
    const loadingText = document.getElementById('terminal-camera-loading');
    const loadingMsg = document.getElementById('camera-loading-text');
    const scanner = document.getElementById('terminal-scanner-outline');
    const scanBtn = document.getElementById('start-scan-btn');
    const faceBadge = document.getElementById('face-badge');

    // Clean up old streams
    if (webcamStream) {
        webcamStream.getTracks().forEach(track => track.stop());
    }

    scanBtn.disabled = true;
    scanBtn.innerText = 'Scanning Face...';
    faceBadge.innerText = 'Scanning...';
    faceBadge.className = 'status-badge badge-warning';
    
    loadingText.style.display = 'flex';
    loadingMsg.innerText = 'Initializing camera sensor...';
    video.style.display = 'none';
    scanner.classList.add('scanning');

    try {
        const constraints = {
            video: { width: 640, height: 480, facingMode: "user" },
            audio: false
        };
        
        webcamStream = await navigator.mediaDevices.getUserMedia(constraints);
        video.srcObject = webcamStream;
        video.style.display = 'block';
        loadingText.style.display = 'none';

        // Wait 1.5 seconds to simulate high-fidelity neural facial mapping scan
        loadingText.style.display = 'none';
        
        setTimeout(() => {
            performFaceRecognitionScan();
        }, 1500);

    } catch (err) {
        console.error("Camera access failed:", err);
        scanner.classList.remove('scanning');
        scanBtn.disabled = false;
        scanBtn.innerHTML = `
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
                <circle cx="12" cy="13" r="4"/>
            </svg>
            Initialize Face Scan
        `;
        faceBadge.innerText = 'Camera Error';
        faceBadge.className = 'status-badge badge-danger';
        showTerminalNotification('danger', 'Camera permissions denied or device occupied.');
    }
}

// Capture frame and send to backend verification endpoint
async function performFaceRecognitionScan() {
    const video = document.getElementById('terminal-webcam');
    const canvas = document.getElementById('terminal-canvas');
    const scanBtn = document.getElementById('start-scan-btn');
    const faceBadge = document.getElementById('face-badge');
    const customerSelect = document.getElementById('terminal-customer-select');
    const shopSelect = document.getElementById('active-shop-select');
    const forceFail = document.getElementById('sim-force-fail').checked;

    if (!webcamStream) return;

    const context = canvas.getContext('2d');
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    const base64Frame = canvas.toDataURL('image/jpeg', 0.9);
    
    // Check if customer ID is explicitly selected or is auto-detect 1:N
    const selectedCustomerId = customerSelect.value || null;
    const shopId = shopSelect.value;

    try {
        const response = await fetch('/api/verify_customer_face', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                customer_id: selectedCustomerId,
                shop_id: shopId,
                live_image: base64Frame,
                force_fail: forceFail
            })
        });

        const result = await response.json();

        if (result.success) {
            if (result.eligible) {
                // Customer is 18+ and face matches
                currentCustomer = result.customer;
                currentLimits = result.limits;
                
                faceBadge.innerText = `Verified: ${result.confidence}% Match`;
                faceBadge.className = 'status-badge badge-success';
                
                showTerminalNotification('success', `Face verification successful: Eligible (Age: ${result.age} yrs).`);
                
                // Populating checkout card details
                populateCustomerDetails();
                
                // Go to step 2 automatically
                setTimeout(() => {
                    goToStep(2);
                }, 1000);
            } else {
                // Customer matches but is underage (< 18)
                faceBadge.innerText = 'NOT ELIGIBLE';
                faceBadge.className = 'status-badge badge-danger';
                showTerminalNotification('danger', `Verification Blocked: Underage customer detected (${result.message})`);
                
                // Lock screen overlay indicators
                document.getElementById('terminal-scanner-outline').style.borderColor = 'var(--danger)';
            }
        } else {
            // Face does not match or no face detected
            faceBadge.innerText = 'VERIFICATION FAILED';
            faceBadge.className = 'status-badge badge-danger';
            showTerminalNotification('danger', result.message);
            document.getElementById('terminal-scanner-outline').style.borderColor = 'var(--danger)';
        }
    } catch (err) {
        console.error("Verification API request failed:", err);
        faceBadge.innerText = 'Server Error';
        faceBadge.className = 'status-badge badge-danger';
        showTerminalNotification('danger', 'Server connection error during face recognition.');
    } finally {
        scanBtn.disabled = false;
        scanBtn.innerHTML = `
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
                <circle cx="12" cy="13" r="4"/>
            </svg>
            Re-Initialize Scan
        `;
    }
}

// Populate UI step 2 details
function populateCustomerDetails() {
    if (!currentCustomer || !currentLimits) return;

    document.getElementById('card-cust-name').innerText = currentCustomer.name;
    document.getElementById('card-cust-id').innerText = `${currentCustomer.id_type}: ${currentCustomer.id_number}`;
    document.getElementById('card-cust-dob').innerText = `DOB: ${currentCustomer.dob}`;
    
    // Set photo path
    const photoImg = document.getElementById('card-cust-photo');
    photoImg.src = `/static/${currentCustomer.photo_path}`;

    // Set identity document path
    const idDocWrapper = document.getElementById('card-id-doc-wrapper');
    const idDocPhoto = document.getElementById('card-id-doc-photo');
    if (currentCustomer.id_photo_path) {
        idDocPhoto.src = `/static/${currentCustomer.id_photo_path}`;
        idDocWrapper.style.display = 'block';
    } else {
        idDocWrapper.style.display = 'none';
    }

    // Limits
    const weeklyRem = currentLimits.remaining_weekly;
    const monthlyRem = currentLimits.remaining_monthly;
    
    document.getElementById('weekly-limit-text').innerText = `Remaining: ${weeklyRem} ml`;
    document.getElementById('monthly-limit-text').innerText = `Remaining: ${monthlyRem} ml`;
    document.getElementById('total-purchased-qty').innerText = `${currentLimits.previously_purchased} ml`;

    // Progress Bars width calculation
    const weeklyPct = Math.min(100, (weeklyRem / currentLimits.weekly_limit) * 100);
    const monthlyPct = Math.min(100, (monthlyRem / currentLimits.monthly_limit) * 100);

    const weeklyBar = document.getElementById('weekly-limit-bar');
    const monthlyBar = document.getElementById('monthly-limit-bar');

    weeklyBar.style.width = `${weeklyPct}%`;
    monthlyBar.style.width = `${monthlyPct}%`;

    // Progress bar alert colors
    weeklyBar.className = 'limit-bar-inner';
    if (weeklyRem <= 50) weeklyBar.classList.add('warning');
    if (weeklyRem <= 0) weeklyBar.classList.add('danger');

    monthlyBar.className = 'limit-bar-inner';
    if (monthlyRem <= 200) monthlyBar.classList.add('warning');
    if (monthlyRem <= 0) monthlyBar.classList.add('danger');
}

// Step wizard panel controller
function goToStep(step) {
    // Hide all step panels
    for (let i = 1; i <= 5; i++) {
        const panel = document.getElementById(`step-panel-${i}`);
        if (panel) panel.style.display = 'none';
        
        const node = document.getElementById(`step-node-${i}`);
        if (node) {
            node.classList.remove('active', 'completed');
            if (i < step) {
                node.classList.add('completed');
            } else if (i === step) {
                node.classList.add('active');
            }
        }
    }

    checkoutStep = step;
    
    // Show active step panel
    const activePanel = document.getElementById(`step-panel-${step}`);
    if (activePanel) activePanel.style.display = 'block';

    // Step-specific settings
    const badge = document.getElementById('step-badge');
    if (step === 1) {
        badge.innerText = 'Verification';
        badge.className = 'status-badge badge-warning';
    } else if (step === 2) {
        badge.innerText = 'Limits Checked';
        badge.className = 'status-badge badge-success';
    } else if (step === 3) {
        badge.innerText = 'Select Volume';
        badge.className = 'status-badge badge-warning';
        validateQuantityInput();
    } else if (step === 4) {
        badge.innerText = 'Final Checkout';
        badge.className = 'status-badge badge-warning';
        document.getElementById('summary-quantity').innerText = `${selectedQuantity} ml`;
    } else if (step === 5) {
        badge.innerText = 'Purchase Completed';
        badge.className = 'status-badge badge-success';
    }
}

// Step 3: Button clicks setting quantity
function setQuantity(amt) {
    document.getElementById('purchase-quantity').value = amt;
    validateQuantityInput();
}

// Check if quantity is within remaining limits
function validateQuantityInput() {
    const qtyInput = document.getElementById('purchase-quantity');
    const confirmBtn = document.getElementById('qty-confirm-btn');
    const errorMsg = document.getElementById('limit-error-msg');
    
    const amt = parseInt(qtyInput.value) || 0;
    selectedQuantity = amt;

    if (amt <= 0) {
        confirmBtn.disabled = true;
        errorMsg.style.display = 'none';
        return;
    }

    const weeklyRem = currentLimits.remaining_weekly;
    const monthlyRem = currentLimits.remaining_monthly;

    if (amt > weeklyRem || amt > monthlyRem) {
        confirmBtn.disabled = true;
        errorMsg.style.display = 'flex';
        errorMsg.querySelector('span').innerText = `Exceeds limits! Max purchasable: ${Math.min(weeklyRem, monthlyRem)} ml`;
    } else {
        confirmBtn.disabled = false;
        errorMsg.style.display = 'none';
    }
}

// Step 4: Final verification and submit
async function submitFinalCheckout() {
    const video = document.getElementById('terminal-webcam');
    const canvas = document.getElementById('terminal-canvas');
    const submitBtn = document.getElementById('submit-purchase-btn');
    const shopSelect = document.getElementById('active-shop-select');
    const forceFail = document.getElementById('sim-force-fail').checked;

    if (!webcamStream) {
        showTerminalNotification('danger', 'Checkout camera is offline. Please initialize face scan.');
        return;
    }

    submitBtn.disabled = true;
    submitBtn.innerText = 'Processing Final Face Scan...';

    // Capture final photo for transaction validation
    const context = canvas.getContext('2d');
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    const finalBase64Frame = canvas.toDataURL('image/jpeg', 0.9);

    try {
        const response = await fetch('/api/submit_purchase', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                customer_id: currentCustomer.id,
                shop_id: shopSelect.value,
                quantity: selectedQuantity,
                live_image: finalBase64Frame,
                force_fail: forceFail
            })
        });

        const result = await response.json();

        if (result.success) {
            // Purchase confirmed
            showTerminalNotification('success', 'Purchase completed successfully!');
            populateReceipt(result.purchase_details);
            goToStep(5);
        } else {
            showTerminalNotification('danger', `Transaction Blocked: ${result.message}`);
            // If verification failed, reset back to step 1
            if (result.reason === 'checkout_face_failed') {
                setTimeout(() => {
                    resetTerminal();
                }, 2000);
            }
        }
    } catch (err) {
        console.error("Submit purchase API error:", err);
        showTerminalNotification('danger', 'Server connection failure during checkout submission.');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = `
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="20 6 9 17 4 12"/>
            </svg>
            Submit & Verify Checkout
        `;
    }
}

// Populate Receipt template details
function populateReceipt(details) {
    document.getElementById('rec-tx-id').innerText = `TX-${Math.floor(100000 + Math.random() * 900000)}`;
    document.getElementById('rec-cust-name').innerText = currentCustomer.name;
    document.getElementById('rec-datetime').innerText = `${details.date} ${details.time}`;
    
    const shopSelect = document.getElementById('active-shop-select');
    document.getElementById('rec-shop-name').innerText = shopSelect.options[shopSelect.selectedIndex].text;
    
    document.getElementById('rec-qty').innerText = `${details.purchased_quantity} ml`;
    document.getElementById('rec-rem-weekly').innerText = `${details.remaining_weekly} ml`;
    document.getElementById('rec-rem-monthly').innerText = `${details.remaining_monthly} ml`;
}

// Notification helper
function showTerminalNotification(type, message) {
    const banner = document.getElementById('terminal-notification');
    const textSpan = document.getElementById('terminal-notification-text');
    
    banner.className = `notification-banner ${type} mt-2`;
    textSpan.innerText = message;
    banner.style.display = 'flex';
}

// Reset terminal to initial state
function resetTerminal() {
    // Stop camera
    if (webcamStream) {
        webcamStream.getTracks().forEach(track => track.stop());
        webcamStream = null;
    }

    currentCustomer = null;
    currentLimits = null;
    selectedQuantity = 0;
    
    document.getElementById('terminal-webcam').style.display = 'none';
    document.getElementById('terminal-camera-loading').style.display = 'flex';
    document.getElementById('start-scan-btn').innerHTML = `
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
            <circle cx="12" cy="13" r="4"/>
        </svg>
        Initialize Face Scan
    `;
    
    const scanner = document.getElementById('terminal-scanner-outline');
    scanner.className = 'scanner-frame';
    scanner.style.borderColor = 'rgba(0, 255, 136, 0.4)';

    document.getElementById('face-badge').innerText = 'Camera Idle';
    document.getElementById('face-badge').className = 'status-badge badge-warning';
    
    document.getElementById('terminal-notification').style.display = 'none';
    document.getElementById('purchase-quantity').value = '';
    
    goToStep(1);
}
