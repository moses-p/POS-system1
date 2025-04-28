// Script to update service worker behavior for icon fallbacks

document.addEventListener('DOMContentLoaded', function() {
    // Register service worker with improved fallback handling
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/service-worker.js')
            .then(registration => {
                console.log('Service Worker registered with scope:', registration.scope);
                
                // Create a serviceWorkerReady flag in localStorage
                localStorage.setItem('serviceWorkerReady', 'true');
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
});

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