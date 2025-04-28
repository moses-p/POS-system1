// Script to update service worker behavior for icon fallbacks

document.addEventListener('DOMContentLoaded', function() {
    // Check if Service Worker is supported
    if ('serviceWorker' in navigator) {
        // Add timestamp to ensure fresh service worker
        const timestamp = Date.now();
        
        // Register the service worker with cache-busting parameter
        navigator.serviceWorker.register(`/service-worker.js?v=${timestamp}`)
            .then(registration => {
                console.log('Service Worker registered with scope:', registration.scope);
                
                // Set up update detection
                setupServiceWorkerUpdates(registration);
                
                // Listen for messages from service worker
                setupServiceWorkerMessages();
            })
            .catch(error => {
                console.error('Service Worker registration failed:', error);
            });
    }
    
    // Handle specific icon errors
    window.addEventListener('error', function(event) {
        // Check if the error is related to icon loading
        if (event.target.tagName === 'IMG' || 
            (typeof event.target.src === 'string' && event.target.src.includes('/icons/'))) {
            console.log('PWA icon load error:', event.target.src);
        }
    }, true);
    
    // Listen for page visibility changes to reload on focus
    document.addEventListener('visibilitychange', function() {
        if (document.visibilityState === 'visible' && sessionStorage.getItem('pendingRefresh')) {
            sessionStorage.removeItem('pendingRefresh');
            window.location.reload();
        }
    });
});

// Setup update detection for service worker
function setupServiceWorkerUpdates(registration) {
    // Flag to track if we've triggered a refresh
    let refreshTriggered = false;
    
    // Check for updates every 2 minutes
    setInterval(() => {
        if (!refreshTriggered) {
            registration.update()
                .then(() => {
                    // If new service worker is installing, prepare for refresh
                    if (registration.installing && !refreshTriggered) {
                        console.log('New service worker is installing...');
                        sessionStorage.setItem('pendingRefresh', 'true');
                    }
                })
                .catch(error => {
                    console.error('Error checking for service worker updates:', error);
                });
        }
    }, 120000); // 2 minutes
    
    // Look for service worker updates on page load
    registration.addEventListener('updatefound', () => {
        if (refreshTriggered) return; // Prevent multiple updates
        
        const newWorker = registration.installing;
        
        newWorker.addEventListener('statechange', () => {
            // When the new service worker is activated
            if (newWorker.state === 'activated' && !refreshTriggered) {
                refreshTriggered = true; // Prevent multiple refreshes
                
                // Notify all open tabs about the update
                if (navigator.serviceWorker.controller) {
                    navigator.serviceWorker.controller.postMessage({
                        type: 'CONTENT_UPDATED'
                    });
                }
                
                // Don't automatically reload - let user choose
                // window.location.reload();
                
                // Instead, show update notification
                showUpdateNotification();
            }
        });
    });
}

// Setup message listeners for communication with service worker
function setupServiceWorkerMessages() {
    // Track last update notification time to prevent spam
    let lastUpdateTime = 0;
    const UPDATE_COOLDOWN = 30000; // 30 seconds

    navigator.serviceWorker.addEventListener('message', event => {
        const now = Date.now();
        
        // Handle messages from service worker
        if (event.data) {
            // Handle traditional refresh message
            if (event.data.type === 'REFRESH_PAGE') {
                // Only refresh if we haven't shown an update recently
                if (now - lastUpdateTime > UPDATE_COOLDOWN) {
                    lastUpdateTime = now;
                    
                    console.log('Received refresh request from service worker');
                    
                    // Only refresh if user is not in the middle of something important
                    const isFormActive = document.querySelector('form:focus-within') !== null;
                    const hasUnsavedChanges = window.unsavedChanges || false;
                    
                    if (!isFormActive && !hasUnsavedChanges) {
                        // Don't automatically refresh, just show notification
                        // window.location.reload();
                        showUpdateNotification();
                    } else {
                        // Set flag to refresh when user finishes their current task
                        sessionStorage.setItem('pendingRefresh', 'true');
                        
                        // Show a notification that an update is available
                        showUpdateNotification();
                    }
                }
            }
            
            // Handle the new update available message
            if (event.data.type === 'UPDATE_AVAILABLE') {
                // Only show notification if we haven't shown one recently
                if (now - lastUpdateTime > UPDATE_COOLDOWN) {
                    lastUpdateTime = now;
                    console.log('Received update notification from service worker');
                    
                    // Show update notification without automatic refresh
                    showUpdateNotification();
                }
            }
        }
    });
}

// Show a notification about pending update
function showUpdateNotification() {
    const notificationArea = document.getElementById('updateNotification');
    if (!notificationArea) {
        // Create notification area if it doesn't exist
        const notification = document.createElement('div');
        notification.id = 'updateNotification';
        notification.className = 'update-notification';
        notification.innerHTML = `
            <div class="alert alert-info alert-dismissible fade show" role="alert">
                <strong>Update Available!</strong> Refresh the page to see the latest changes.
                <button type="button" class="btn btn-sm btn-primary ms-3" onclick="window.location.reload()">
                    Refresh Now
                </button>
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        document.body.appendChild(notification);
    } else {
        notificationArea.style.display = 'block';
    }
}

// Function to create a simple fallback icon using canvas
function createFallbackIcon() {
    // Check if icons are already created
    if (document.querySelector('link[rel="icon"][data-fallback="true"]')) {
        return;
    }
    
    // Create canvas for fallback icon
    const canvas = document.createElement('canvas');
    canvas.width = 144;
    canvas.height = 144;
    const ctx = canvas.getContext('2d');
    
    // Fill background
    ctx.fillStyle = '#2c3e50';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Add text
    ctx.fillStyle = 'white';
    ctx.font = 'bold 72px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('POS', canvas.width/2, canvas.height/2);
    
    // Convert to data URL
    const iconDataUrl = canvas.toDataURL('image/png');
    
    // Add as fallback icon
    const link = document.createElement('link');
    link.rel = 'icon';
    link.type = 'image/png';
    link.href = iconDataUrl;
    link.dataset.fallback = 'true';
    document.head.appendChild(link);
    
    // Also add as apple-touch-icon
    const appleLink = document.createElement('link');
    appleLink.rel = 'apple-touch-icon';
    appleLink.href = iconDataUrl;
    appleLink.dataset.fallback = 'true';
    document.head.appendChild(appleLink);
    
    console.log('Fallback icons created');
} 