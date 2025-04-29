// Main JavaScript functionality
document.addEventListener('DOMContentLoaded', function() {
    // Initialize cart counter updates
    updateCartCount();
    
    // Connection status indicator
    updateConnectionStatus();
    
    // Listen for online/offline events
    window.addEventListener('online', updateConnectionStatus);
    window.addEventListener('offline', updateConnectionStatus);
});

// Update the cart count in the navbar
function updateCartCount() {
    // Only run if cart count element exists
    const cartCountElement = document.getElementById('cartCount');
    if (!cartCountElement) return;
    
    // Fetch the current cart count
    fetch('/get_cart_count')
        .then(response => response.json())
        .then(data => {
            cartCountElement.textContent = data.count;
            // Hide count if zero
            if (data.count == 0) {
                cartCountElement.style.display = 'none';
            } else {
                cartCountElement.style.display = 'inline-block';
            }
        })
        .catch(error => console.error('Error updating cart count:', error));
}

// Update connection status indicator
function updateConnectionStatus() {
    const statusElement = document.getElementById('connectionStatus');
    if (!statusElement) return;
    
    if (navigator.onLine) {
        statusElement.innerHTML = '<span class="badge bg-success"><i class="fas fa-wifi me-1"></i>Online</span>';
        statusElement.classList.add('online');
        statusElement.classList.remove('offline');
    } else {
        statusElement.innerHTML = '<span class="badge bg-danger"><i class="fas fa-exclamation-triangle me-1"></i>Offline</span>';
        statusElement.classList.add('offline');
        statusElement.classList.remove('online');
    }
} 