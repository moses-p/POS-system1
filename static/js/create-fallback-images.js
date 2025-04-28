// Script to create fallback images for offline use
document.addEventListener('DOMContentLoaded', function() {
    // Create offline icon images if needed
    createOfflineImages();
});

// Function to create offline images
function createOfflineImages() {
    // Create all the icon sizes
    const iconSizes = [72, 96, 128, 144, 152, 192, 384, 512];
    
    iconSizes.forEach(size => {
        createIconImage(size);
    });
    
    // Create offline image
    createOfflineImage();
}

// Create icon image with given size
function createIconImage(size) {
    // Create canvas for icon
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d');
    
    // Fill background
    ctx.fillStyle = '#2c3e50';
    ctx.fillRect(0, 0, size, size);
    
    // Draw text
    ctx.fillStyle = 'white';
    ctx.font = `bold ${Math.floor(size/2)}px sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('POS', size/2, size/2);
    
    // Convert to data URL and create download link
    const iconDataUrl = canvas.toDataURL('image/png');
    
    // Save to localStorage for future use
    localStorage.setItem(`icon-${size}x${size}`, iconDataUrl);
    
    // Add icon to page (hidden)
    addImageToPage(iconDataUrl, `icon-${size}x${size}`);
}

// Create offline image placeholder
function createOfflineImage() {
    // Create canvas for generic offline image
    const canvas = document.createElement('canvas');
    canvas.width = 300;
    canvas.height = 200;
    const ctx = canvas.getContext('2d');
    
    // Fill background
    ctx.fillStyle = '#f8f9fa';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Add border
    ctx.strokeStyle = '#ced4da';
    ctx.lineWidth = 2;
    ctx.strokeRect(5, 5, canvas.width - 10, canvas.height - 10);
    
    // Draw text
    ctx.fillStyle = '#6c757d';
    ctx.font = 'bold 24px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('Image Unavailable', canvas.width/2, canvas.height/2 - 15);
    
    ctx.font = '18px sans-serif';
    ctx.fillText('You are currently offline', canvas.width/2, canvas.height/2 + 20);
    
    // Convert to data URL
    const offlineImageUrl = canvas.toDataURL('image/png');
    
    // Save to localStorage
    localStorage.setItem('offline-image', offlineImageUrl);
    
    // Add to page (hidden)
    addImageToPage(offlineImageUrl, 'offline-image');
}

// Add image to page (hidden) for caching
function addImageToPage(dataUrl, id) {
    const img = document.createElement('img');
    img.src = dataUrl;
    img.id = id;
    img.style.display = 'none';
    img.dataset.generated = 'true';
    document.body.appendChild(img);
    
    // Create a fetch request to cache this image
    if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
        // Create a blob and object URL
        fetch(dataUrl)
            .then(response => response.blob())
            .then(blob => {
                const url = URL.createObjectURL(blob);
                // Now create a link for service worker to cache
                const link = document.createElement('link');
                link.rel = 'prefetch';
                link.href = url;
                link.dataset.generatedImage = id;
                document.head.appendChild(link);
            })
            .catch(err => console.error('Error creating prefetch link:', err));
    }
} 