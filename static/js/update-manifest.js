// Script to dynamically update the manifest.json with valid icons

document.addEventListener('DOMContentLoaded', function() {
    // Wait for fallback images to be created
    setTimeout(updateManifest, 1000);
});

// Update the manifest dynamically
function updateManifest() {
    // Only update manifest if there are icon issues
    const iconIssues = document.querySelector('img[data-generated="true"]') !== null;
    
    if (!iconIssues) return;
    
    console.log('Updating manifest with valid icons...');
    
    // Get the base URL for absolute URLs
    const baseUrl = window.location.origin;
    
    // Create new manifest link
    const newManifest = {
        name: "POS System",
        short_name: "POS",
        description: "Point of Sale System with online and offline capabilities",
        start_url: baseUrl + "/",
        display: "standalone",
        background_color: "#ffffff",
        theme_color: "#2c3e50",
        icons: generateIconsArray()
    };
    
    // Create a blob of the manifest
    const manifestBlob = new Blob(
        [JSON.stringify(newManifest, null, 2)], 
        {type: 'application/json'}
    );
    
    // Create a URL for the blob
    const manifestUrl = URL.createObjectURL(manifestBlob);
    
    // Replace the old manifest link with the new one
    const oldManifest = document.querySelector('link[rel="manifest"]');
    if (oldManifest) {
        oldManifest.href = manifestUrl;
        oldManifest.dataset.dynamic = 'true';
        console.log('Manifest updated dynamically');
    }
}

// Generate icons array based on created images
function generateIconsArray() {
    const iconSizes = [72, 96, 128, 144, 152, 192, 384, 512];
    const icons = [];
    const baseUrl = window.location.origin;
    
    // Add a fixed set of icons using proper URLs
    iconSizes.forEach(size => {
        // Use actual path-based URLs for the manifest
        icons.push({
            src: baseUrl + `/generated-icon-${size}.png`, // Full absolute URL
            sizes: `${size}x${size}`,
            type: "image/png",
            purpose: "any maskable"
        });
    });
    
    return icons;
} 