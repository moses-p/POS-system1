// Simple PWA fix for missing icons
document.addEventListener('DOMContentLoaded', function() {
    // Check for PWA icon errors
    window.addEventListener('error', function(event) {
        if (event.target && event.target.src && event.target.src.includes('/images/icons/')) {
            console.log('Icon loading error detected, applying PWA fixes');
            applyPWAFixes();
        }
    }, true);
    
    // Also try to apply fixes proactively
    setTimeout(applyPWAFixes, 1000);
});

// Apply all the PWA fixes in one go
function applyPWAFixes() {
    const baseUrl = window.location.origin;
    
    // Generate all icons first, we'll need the data URLs
    const iconDataUrls = {};
    createAllIconDataUrls(iconDataUrls);
    
    // Wait briefly for the icons to be generated
    setTimeout(() => {
        // 1. Create a valid manifest with data URLs instead of file paths
        const manifest = {
            name: "POS System",
            short_name: "POS",
            description: "Point of Sale System with online and offline capabilities",
            start_url: baseUrl + "/",
            display: "standalone",
            background_color: "#ffffff",
            theme_color: "#2c3e50",
            icons: generateIconsWithDataUrls(iconDataUrls)
        };
        
        // 2. Create a blob URL for the manifest
        const manifestStr = JSON.stringify(manifest, null, 2);
        const manifestBlob = new Blob([manifestStr], {type: 'application/json'});
        const manifestUrl = URL.createObjectURL(manifestBlob);
        
        // 3. Replace the manifest link
        const manifestLink = document.querySelector('link[rel="manifest"]');
        if (manifestLink) {
            manifestLink.href = manifestUrl;
            console.log('PWA manifest updated with data URL icons');
        }
        
        // 4. Add the apple icons
        addAppleIcons(iconDataUrls);
    }, 100);
}

// Create data URLs for all icons and store in the provided object
function createAllIconDataUrls(iconDataUrls) {
    // Create all the icon sizes
    const sizes = [72, 96, 128, 144, 152, 192, 384, 512];
    
    // Generate each icon as data URL
    sizes.forEach(size => {
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
        
        // Get the data URL
        iconDataUrls[size] = canvas.toDataURL('image/png');
    });
}

// Add apple-touch-icon links using data URLs
function addAppleIcons(iconDataUrls) {
    // Remove any existing apple touch icons we've created
    document.querySelectorAll('link[rel="apple-touch-icon"][data-generated="true"]').forEach(link => {
        link.remove();
    });
    
    // Add the main apple-touch-icon (152px is typically used)
    if (iconDataUrls[152]) {
        const appleLink = document.createElement('link');
        appleLink.rel = 'apple-touch-icon';
        appleLink.href = iconDataUrls[152];
        appleLink.setAttribute('data-generated', 'true');
        document.head.appendChild(appleLink);
    }
    
    // Add icon as favicon too
    if (iconDataUrls[144]) {
        const favicon = document.createElement('link');
        favicon.rel = 'icon';
        favicon.type = 'image/png';
        favicon.href = iconDataUrls[144];
        favicon.setAttribute('data-generated', 'true');
        document.head.appendChild(favicon);
    }
}

// Generate icon definitions with data URLs
function generateIconsWithDataUrls(iconDataUrls) {
    const icons = [];
    
    // Create icon entries for all sizes
    [72, 96, 128, 144, 152, 192, 384, 512].forEach(size => {
        if (iconDataUrls[size]) {
            icons.push({
                src: iconDataUrls[size],  // Use data URL directly
                sizes: `${size}x${size}`,
                type: "image/png",
                purpose: "any maskable"
            });
        }
    });
    
    return icons;
} 