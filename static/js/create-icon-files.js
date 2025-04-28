// Script to create physical icon files if needed
document.addEventListener('DOMContentLoaded', function() {
    // Only try to download the files in developer mode when needed
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        createAndDownloadIcons();
    }
});

// Create icon files and provide them for download
function createAndDownloadIcons() {
    const sizes = [72, 96, 128, 144, 152, 192, 384, 512];
    
    sizes.forEach(size => {
        createAndDownloadIcon(size);
    });
    
    // Also generate the offline image
    createAndDownloadOfflineImage();
}

// Create and download a single icon
function createAndDownloadIcon(size) {
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d');
    
    // Draw background
    ctx.fillStyle = '#2c3e50';
    ctx.fillRect(0, 0, size, size);
    
    // Draw text
    ctx.fillStyle = 'white';
    ctx.font = `bold ${Math.floor(size/2)}px sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('POS', size/2, size/2);
    
    // Convert to data URL
    const dataUrl = canvas.toDataURL('image/png');
    
    // Add a download link for dev purposes
    const downloadDiv = document.createElement('div');
    downloadDiv.style.position = 'fixed';
    downloadDiv.style.bottom = '10px';
    downloadDiv.style.right = '10px';
    downloadDiv.style.zIndex = '10000';
    downloadDiv.style.background = 'rgba(255,255,255,0.8)';
    downloadDiv.style.padding = '5px';
    downloadDiv.style.borderRadius = '5px';
    downloadDiv.style.fontSize = '12px';
    downloadDiv.style.display = 'none';  // Hidden by default
    
    const downloadLink = document.createElement('a');
    downloadLink.href = dataUrl;
    downloadLink.download = `icon-${size}.png`;
    downloadLink.textContent = `Download ${size}x${size} icon`;
    downloadLink.style.display = 'block';
    downloadLink.style.marginBottom = '5px';
    
    downloadDiv.appendChild(downloadLink);
    document.body.appendChild(downloadDiv);
    
    // Add a button to show/hide download options
    if (size === 144) {
        const showButton = document.createElement('button');
        showButton.textContent = 'Download Icon Files';
        showButton.style.position = 'fixed';
        showButton.style.bottom = '10px';
        showButton.style.right = '10px';
        showButton.style.zIndex = '9999';
        showButton.style.padding = '5px 10px';
        
        showButton.addEventListener('click', function() {
            if (downloadDiv.style.display === 'none') {
                downloadDiv.style.display = 'block';
                this.style.display = 'none';
            }
        });
        
        const hideButton = document.createElement('button');
        hideButton.textContent = 'Hide';
        hideButton.addEventListener('click', function() {
            downloadDiv.style.display = 'none';
            showButton.style.display = 'block';
        });
        
        downloadDiv.appendChild(hideButton);
        document.body.appendChild(showButton);
    }
}

// Create and download offline image
function createAndDownloadOfflineImage() {
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
    const dataUrl = canvas.toDataURL('image/png');
    
    // Create download link for developers
    const downloadLink = document.createElement('a');
    downloadLink.href = dataUrl;
    downloadLink.download = 'offline-image.png';
    downloadLink.textContent = 'Download offline image';
    downloadLink.style.display = 'block';
    downloadLink.style.marginBottom = '5px';
    
    // Add to the download div if it exists
    const downloadDiv = document.querySelector('div[style*="position: fixed"][style*="bottom: 10px"]');
    if (downloadDiv) {
        downloadDiv.appendChild(downloadLink);
    }
} 