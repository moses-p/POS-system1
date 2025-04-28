// Script to fix manifest by using data URLs directly for icons
document.addEventListener('DOMContentLoaded', function() {
    // Apply fix immediately to resolve manifest issues
    fixManifest();
});

// Fix the manifest by replacing it with an inline data URL version
function fixManifest() {
    // Find the manifest link element
    const manifestLink = document.querySelector('link[rel="manifest"]');
    if (!manifestLink) {
        console.log('No manifest link found');
        return;
    }

    // Create a minimal valid manifest with data URL icons
    const manifest = {
        name: "POS System",
        short_name: "POS",
        description: "Point of Sale System with online and offline capabilities",
        start_url: window.location.origin + "/",
        display: "standalone",
        background_color: "#ffffff",
        theme_color: "#2c3e50",
        icons: [
            {
                src: createIconDataURL(144),
                sizes: "144x144",
                type: "image/png",
                purpose: "any maskable"
            }
        ]
    };

    // Create a blob URL for the manifest
    const manifestBlob = new Blob([JSON.stringify(manifest)], {type: 'application/json'});
    const manifestURL = URL.createObjectURL(manifestBlob);

    // Replace the existing manifest href
    manifestLink.href = manifestURL;
    console.log('Manifest fixed with inline data URL icons');
    
    // Also fix favicon and apple-touch-icon
    const iconDataURL = createIconDataURL(144);
    
    // Add or replace favicon
    let favicon = document.querySelector('link[rel="icon"]');
    if (!favicon) {
        favicon = document.createElement('link');
        favicon.rel = 'icon';
        favicon.type = 'image/png';
        document.head.appendChild(favicon);
    }
    favicon.href = iconDataURL;
    
    // Add or replace apple-touch-icon
    let appleIcon = document.querySelector('link[rel="apple-touch-icon"]');
    if (!appleIcon) {
        appleIcon = document.createElement('link');
        appleIcon.rel = 'apple-touch-icon';
        document.head.appendChild(appleIcon);
    }
    appleIcon.href = iconDataURL;
}

// Create a data URL for an icon of the specified size
function createIconDataURL(size) {
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
    
    return canvas.toDataURL('image/png');
} 