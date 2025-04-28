// Intercept and handle requests for generated icons

document.addEventListener('DOMContentLoaded', function() {
    // Create the icons in memory and store them for intercept
    createAndStoreIcons();
    
    // Register a fetch event listener if we're in a service worker context
    if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
        // We'll use a message to tell the service worker about our icons
        navigator.serviceWorker.controller.postMessage({
            type: 'ICON_STORAGE_READY'
        });
    }
});

// Create and store icons
function createAndStoreIcons() {
    const iconSizes = [72, 96, 128, 144, 152, 192, 384, 512];
    
    iconSizes.forEach(size => {
        // Create a canvas element to generate the icon
        const canvas = document.createElement('canvas');
        canvas.width = size;
        canvas.height = size;
        const ctx = canvas.getContext('2d');
        
        // Fill background
        ctx.fillStyle = '#2c3e50';
        ctx.fillRect(0, 0, size, size);
        
        // Add text
        ctx.fillStyle = 'white';
        ctx.font = `bold ${Math.floor(size/2)}px sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('POS', size/2, size/2);
        
        // Convert to blob and save to indexedDB for service worker
        canvas.toBlob(function(blob) {
            storeIconInIndexedDB(`icon-${size}x${size}`, blob);
        });
    });
    
    // Create offline fallback image
    const offlineCanvas = document.createElement('canvas');
    offlineCanvas.width = 300;
    offlineCanvas.height = 200;
    const offlineCtx = offlineCanvas.getContext('2d');
    
    // Fill background
    offlineCtx.fillStyle = '#f8f9fa';
    offlineCtx.fillRect(0, 0, offlineCanvas.width, offlineCanvas.height);
    
    // Add border
    offlineCtx.strokeStyle = '#ced4da';
    offlineCtx.lineWidth = 2;
    offlineCtx.strokeRect(5, 5, offlineCanvas.width - 10, offlineCanvas.height - 10);
    
    // Draw text
    offlineCtx.fillStyle = '#6c757d';
    offlineCtx.font = 'bold 24px sans-serif';
    offlineCtx.textAlign = 'center';
    offlineCtx.textBaseline = 'middle';
    offlineCtx.fillText('Image Unavailable', offlineCanvas.width/2, offlineCanvas.height/2 - 15);
    
    offlineCtx.font = '18px sans-serif';
    offlineCtx.fillText('You are currently offline', offlineCanvas.width/2, offlineCanvas.height/2 + 20);
    
    offlineCanvas.toBlob(function(blob) {
        storeIconInIndexedDB('offline-image', blob);
    });
}

// Store icon in IndexedDB for access by service worker
function storeIconInIndexedDB(name, blob) {
    // Open (or create) the database
    const request = indexedDB.open('icon-cache-db', 1);
    
    // Create the schema
    request.onupgradeneeded = function() {
        const db = request.result;
        if (!db.objectStoreNames.contains('icons')) {
            db.createObjectStore('icons', { keyPath: 'name' });
        }
    };
    
    request.onsuccess = function() {
        const db = request.result;
        const transaction = db.transaction(['icons'], 'readwrite');
        const store = transaction.objectStore('icons');
        
        // Add the icon to the store
        store.put({ name: name, blob: blob, timestamp: Date.now() });
        
        // Log success
        transaction.oncomplete = function() {
            console.log(`Stored icon ${name} in IndexedDB`);
        };
        
        transaction.onerror = function(event) {
            console.error(`Error storing icon ${name}:`, event.target.error);
        };
    };
    
    request.onerror = function(event) {
        console.error('Error opening icon cache database:', event.target.error);
    };
} 