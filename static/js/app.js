// Main application JavaScript for the POS system
// Handles offline functionality and service worker registration

document.addEventListener('DOMContentLoaded', function() {
    // Service worker registration is now handled in service-worker-update.js
    
    // Initialize online/offline status detection
    initOnlineStatusDetection();
    
    // Initialize IndexedDB for offline storage
    initIndexedDB();
    
    // Check for pending offline transactions to sync
    checkPendingTransactions();
    
    // Initialize responsive handlers
    initResponsiveHandlers();
    
    // Add touch event handlers for mobile devices
    initTouchHandlers();
    
    // Handle authentication state changes
    initAuthStateHandler();
    
    // Initialize cart functionality
    initCartFunctionality();
    
    // Refresh stock levels on page load
    if (document.querySelector('.product-stock')) {
        refreshStock();
    }
    
    // Add timestamp to prevent browser caching
    const addTimestampToLinks = () => {
        document.querySelectorAll('a').forEach(link => {
            // Skip external links and special links
            if (link.href.startsWith(window.location.origin) && 
                !link.href.includes('#') && 
                !link.getAttribute('data-no-cache')) {
                
                let url = new URL(link.href);
                url.searchParams.set('_t', new Date().getTime());
                link.href = url.toString();
            }
        });
    };
    
    // Run initially and observe DOM changes
    addTimestampToLinks();
    
    // Create an observer to handle dynamically added links
    const observer = new MutationObserver(mutations => {
        mutations.forEach(mutation => {
            if (mutation.type === 'childList') {
                addTimestampToLinks();
            }
        });
    });
    
    // Start observing
    observer.observe(document.body, { 
        childList: true,
        subtree: true
    });

    // Prevent back/forward cache (bfcache)
    window.addEventListener('pageshow', function(event) {
        if (event.persisted) {
            window.location.reload();
        }
    });
    
    // Force refresh when navigating back
    window.addEventListener('popstate', function() {
        window.location.reload();
    });

    // Initialize cart syncing
    initCartSync();
    
    // Setup event listeners
    setupAddToCartButtons();
    setupQuantityButtons();
    setupFormValidation();
});

// Online/Offline status detection and UI updates
function initOnlineStatusDetection() {
    function updateOnlineStatus() {
        const statusElement = document.getElementById('connectionStatus');
        if (!statusElement) return;
        
        if (navigator.onLine) {
            statusElement.innerHTML = '<span class="badge bg-success"><i class="fas fa-wifi me-1"></i>Online</span>';
            statusElement.classList.remove('offline');
            statusElement.classList.add('online');
            
            // Try to sync pending transactions when coming back online
            syncPendingTransactions();
        } else {
            statusElement.innerHTML = '<span class="badge bg-warning"><i class="fas fa-exclamation-triangle me-1"></i>Offline</span>';
            statusElement.classList.remove('online');
            statusElement.classList.add('offline');
        }
    }
    
    // Add event listeners for online/offline events
    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);
    
    // Initial check
    updateOnlineStatus();
}

// Authentication state handler to prevent caching issues with login/logout
function initAuthStateHandler() {
    // Check if we're on login/logout related pages
    const path = window.location.pathname;
    const isAuthPage = path === '/login' || path === '/logout' || path === '/register';
    
    // Force page reload after login/logout to clear service worker cache
    if (isAuthPage) {
        // Add param to indicate this is a fresh page load post auth action
        const hasReloadParam = new URLSearchParams(window.location.search).has('reload');
        
        if (!hasReloadParam && sessionStorage.getItem('auth_action_performed')) {
            // Clear the flag
            sessionStorage.removeItem('auth_action_performed');
            
            // Redirect to home with cache busting
            const timestamp = new Date().getTime();
            window.location.href = '/?cache_bust=' + timestamp;
        }
    }
    
    // Setup listeners for login and logout forms
    document.addEventListener('submit', function(e) {
        const form = e.target;
        // Check if this is a login or logout action
        if (form.action && (form.action.includes('/login') || form.action.includes('/logout'))) {
            // Set a flag to indicate auth action was performed
            sessionStorage.setItem('auth_action_performed', 'true');
        }
    });
    
    // For the logout link that might not be a form
    const logoutLinks = document.querySelectorAll('a[href="/logout"]');
    logoutLinks.forEach(link => {
        link.addEventListener('click', function() {
            sessionStorage.setItem('auth_action_performed', 'true');
        });
    });
}

// Initialize cart functionality
function initCartFunctionality() {
    // Do not add event handlers here - they're already defined in index.html
    // Just define the global addToCart function for use elsewhere
    
    // Generic add to cart function
    window.addToCart = function(productId, buttonElement) {
        if (!buttonElement) {
            buttonElement = document.querySelector(`.add-to-cart[data-product-id="${productId}"]`);
        }
        
        let originalText = '';
        if (buttonElement) {
            originalText = buttonElement.innerHTML;
            buttonElement.disabled = true;
            buttonElement.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Adding...';
        }
        
        // Get customer info if available
        let customerInfo = {};
        try {
            const savedInfo = localStorage.getItem('customerInfo');
            if (savedInfo) {
                customerInfo = JSON.parse(savedInfo);
            }
        } catch (e) {
            console.error('Error parsing customer info:', e);
        }
        
        // Make the API call
        fetch('/add_to_cart/' + productId, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                quantity: 1,
                customer_name: customerInfo.name || '',
                customer_phone: customerInfo.phone || '',
                customer_email: customerInfo.email || '',
                customer_address: customerInfo.address || ''
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            console.log('Add to cart response:', data);
            if (data.success) {
                // Play success sound if available
                const successSound = document.getElementById('successSound');
                if (successSound) {
                    successSound.play().catch(e => console.log('Sound play error:', e));
                }
                
                // Update cart counter if available
                updateCartCounter();
                
                // Add refreshStock call to update UI
                refreshStock(productId);
                
                // Update button
                if (buttonElement) {
                    buttonElement.innerHTML = '<i class="fas fa-check me-2"></i>Added to Cart';
                    setTimeout(() => {
                        buttonElement.innerHTML = originalText;
                        buttonElement.disabled = false;
                    }, 2000);
                }
            } else {
                // Show error
                if (buttonElement) {
                    buttonElement.innerHTML = '<i class="fas fa-exclamation-triangle me-2"></i>Error';
                    setTimeout(() => {
                        buttonElement.innerHTML = originalText;
                        buttonElement.disabled = false;
                    }, 2000);
                }
                alert(data.error || 'Error adding to cart');
            }
        })
        .catch(error => {
            console.error('Error adding to cart:', error);
            if (buttonElement) {
                buttonElement.innerHTML = '<i class="fas fa-exclamation-triangle me-2"></i>Error';
                setTimeout(() => {
                    buttonElement.innerHTML = originalText;
                    buttonElement.disabled = false;
                }, 2000);
            }
        });
    };
    
    // Function to update cart counter
    function updateCartCounter() {
        fetch('/get_cart_count', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            const cartCountElements = document.querySelectorAll('#cartCount, .cart-count');
            cartCountElements.forEach(element => {
                if (data.count > 0) {
                    element.textContent = data.count;
                    element.style.display = 'inline-block';
                } else {
                    element.textContent = '0';
                    element.style.display = 'none';
                }
            });
        })
        .catch(error => console.error('Error updating cart count:', error));
    }
    
    // Initial cart count update
    updateCartCounter();
}

// IndexedDB initialization for offline storage
function initIndexedDB() {
    // Check if IndexedDB is supported
    if (!window.indexedDB) {
        console.log("Your browser doesn't support IndexedDB for offline storage.");
        return;
    }
    
    // Open the database (or create it if it doesn't exist)
    const request = indexedDB.open("POSOfflineDB", 1);
    
    request.onerror = function(event) {
        console.error("IndexedDB error:", event.target.errorCode);
    };
    
    request.onupgradeneeded = function(event) {
        const db = event.target.result;
        
        // Create object stores for offline data
        if (!db.objectStoreNames.contains("pendingOrders")) {
            db.createObjectStore("pendingOrders", { keyPath: "id", autoIncrement: true });
        }
        
        if (!db.objectStoreNames.contains("pendingCartItems")) {
            db.createObjectStore("pendingCartItems", { keyPath: "id", autoIncrement: true });
        }
    };
    
    request.onsuccess = function(event) {
        window.offlineDB = event.target.result;
        console.log("IndexedDB initialized successfully");
    };
}

// Initialize responsive handlers for different device sizes
function initResponsiveHandlers() {
    // Get the current device type (mobile, tablet, desktop)
    const deviceType = getDeviceType();
    document.body.classList.add(deviceType);
    
    // Handle orientation changes
    window.addEventListener('resize', handleResize);
    
    // Initial setup
    handleResize();
    
    // Initialize tables for better mobile experience
    initResponsiveTables();
}

// Get device type based on screen width
function getDeviceType() {
    const width = window.innerWidth;
    if (width < 768) {
        return 'mobile-device';
    } else if (width < 1024) {
        return 'tablet-device';
    } else {
        return 'desktop-device';
    }
}

// Handle window resize and orientation changes
function handleResize() {
    const width = window.innerWidth;
    const height = window.innerHeight;
    const isLandscape = width > height;
    
    // Remove all orientation classes
    document.body.classList.remove('landscape', 'portrait');
    
    // Add new orientation class
    document.body.classList.add(isLandscape ? 'landscape' : 'portrait');
    
    // Update device type class if necessary
    const currentDeviceType = getDeviceType();
    if (!document.body.classList.contains(currentDeviceType)) {
        document.body.classList.remove('mobile-device', 'tablet-device', 'desktop-device');
        document.body.classList.add(currentDeviceType);
    }
    
    // Adjust UI elements based on screen size
    adjustUIForScreenSize();
}

// Adjust UI elements based on screen size
function adjustUIForScreenSize() {
    // Shorten certain text elements on small screens
    if (window.innerWidth < 576) {
        // Example: Shorten long button text
        const buttons = document.querySelectorAll('.btn-responsive-text');
        buttons.forEach(button => {
            if (button.dataset.shortText) {
                button.setAttribute('data-full-text', button.textContent);
                button.textContent = button.dataset.shortText;
            }
        });
    } else {
        // Restore original text on larger screens
        const buttons = document.querySelectorAll('.btn-responsive-text');
        buttons.forEach(button => {
            if (button.dataset.fullText) {
                button.textContent = button.dataset.fullText;
            }
        });
    }
}

// Make tables more responsive on mobile
function initResponsiveTables() {
    const tables = document.querySelectorAll('table.table-responsive-data');
    
    tables.forEach(table => {
        if (window.innerWidth < 768) {
            // Get all headers
            const headers = Array.from(table.querySelectorAll('thead th')).map(th => th.textContent);
            
            // Process each row to add data labels
            const rows = table.querySelectorAll('tbody tr');
            rows.forEach(row => {
                const cells = row.querySelectorAll('td');
                cells.forEach((cell, index) => {
                    if (headers[index]) {
                        cell.setAttribute('data-label', headers[index]);
                    }
                });
            });
        }
    });
}

// Add enhanced touch event handlers for mobile devices
function initTouchHandlers() {
    // Only apply touch handlers if on a touch device
    if (!('ontouchstart' in window) && !navigator.maxTouchPoints) return;
    
    // Add active class for touch feedback on buttons
    document.querySelectorAll('.btn').forEach(button => {
        button.addEventListener('touchstart', function() {
            this.classList.add('touch-active');
        }, { passive: true });
        
        button.addEventListener('touchend', function() {
            this.classList.remove('touch-active');
        }, { passive: true });
        
        button.addEventListener('touchcancel', function() {
            this.classList.remove('touch-active');
        }, { passive: true });
    });
    
    // Add swipe handlers for mobile interactions
    initSwipeHandlers();
}

// Initialize swipe gesture handlers
function initSwipeHandlers() {
    let touchStartX = 0;
    let touchStartY = 0;
    let touchEndX = 0;
    let touchEndY = 0;
    
    // Elements that should respond to swipe gestures
    const swipeElements = document.querySelectorAll('.swipe-container');
    
    swipeElements.forEach(element => {
        element.addEventListener('touchstart', function(event) {
            touchStartX = event.changedTouches[0].screenX;
            touchStartY = event.changedTouches[0].screenY;
        }, { passive: true });
        
        element.addEventListener('touchend', function(event) {
            touchEndX = event.changedTouches[0].screenX;
            touchEndY = event.changedTouches[0].screenY;
            handleSwipe(this);
        }, { passive: true });
    });
    
    function handleSwipe(element) {
        const deltaX = touchEndX - touchStartX;
        const deltaY = touchEndY - touchStartY;
        
        // Check if horizontal swipe was significantly greater than vertical movement
        if (Math.abs(deltaX) > Math.abs(deltaY) * 2 && Math.abs(deltaX) > 50) {
            if (deltaX > 0) {
                // Swipe right
                element.dispatchEvent(new CustomEvent('swiperight'));
            } else {
                // Swipe left
                element.dispatchEvent(new CustomEvent('swipeleft'));
            }
        }
    }
}

// Check for pending transactions to sync with server
function checkPendingTransactions() {
    if (!window.offlineDB) return;
    
    const transaction = window.offlineDB.transaction(["pendingOrders"], "readonly");
    const store = transaction.objectStore("pendingOrders");
    const countRequest = store.count();
    
    countRequest.onsuccess = function() {
        if (countRequest.result > 0) {
            // Show notification about pending orders
            showPendingOrdersNotification(countRequest.result);
        }
    };
}

// Show notification for pending orders
function showPendingOrdersNotification(count) {
    const notificationArea = document.getElementById('offlineNotifications');
    if (!notificationArea) return;
    
    notificationArea.innerHTML = `
        <div class="alert alert-warning alert-dismissible fade show" role="alert">
            <i class="fas fa-cloud-upload-alt me-2"></i>
            <strong>${count} order(s)</strong> waiting to be synced when you're back online.
            <button type="button" class="btn btn-sm btn-primary ms-3" onclick="syncPendingTransactions()">
                Sync Now
            </button>
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    
    notificationArea.classList.remove('d-none');
}

// Sync pending transactions with server when online
function syncPendingTransactions() {
    if (!navigator.onLine) {
        alert("You're offline. Please try again when you have an internet connection.");
        return;
    }
    
    if (!window.offlineDB) return;
    
    const transaction = window.offlineDB.transaction(["pendingOrders"], "readonly");
    const store = transaction.objectStore("pendingOrders");
    const getAll = store.getAll();
    
    getAll.onsuccess = function() {
        const pendingOrders = getAll.result;
        if (pendingOrders.length === 0) return;
        
        // Show progress indicator
        const notificationArea = document.getElementById('offlineNotifications');
        if (notificationArea) {
            notificationArea.innerHTML = `
                <div class="alert alert-info alert-dismissible fade show" role="alert">
                    <div class="d-flex align-items-center">
                        <div class="spinner-border spinner-border-sm me-2" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <div>Syncing ${pendingOrders.length} offline order(s)...</div>
                    </div>
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>
            `;
        }
        
        // Attempt to sync each pending order
        let successCount = 0;
        let failCount = 0;
        
        pendingOrders.forEach(order => {
            // Send order to server
            fetch('/api/sync_offline_order', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(order)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Remove synced order from IndexedDB
                    removeOrderFromIndexedDB(order.id);
                    successCount++;
                } else {
                    failCount++;
                }
            })
            .catch(error => {
                console.error('Error syncing order:', error);
                failCount++;
            })
            .finally(() => {
                if (successCount + failCount === pendingOrders.length) {
                    // All orders processed
                    showSyncResult(successCount, failCount);
                }
            });
        });
    };
}

// Remove synced order from IndexedDB
function removeOrderFromIndexedDB(orderId) {
    if (!window.offlineDB) return;
    
    const transaction = window.offlineDB.transaction(["pendingOrders"], "readwrite");
    const store = transaction.objectStore("pendingOrders");
    store.delete(orderId);
}

// Show sync result notification
function showSyncResult(successCount, failCount) {
    const notificationArea = document.getElementById('offlineNotifications');
    
    if (notificationArea) {
        if (successCount > 0 && failCount === 0) {
            notificationArea.innerHTML = `
                <div class="alert alert-success alert-dismissible fade show" role="alert">
                    <i class="fas fa-check-circle me-2"></i>
                    Successfully synced ${successCount} order(s).
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>
            `;
        } else if (successCount > 0 && failCount > 0) {
            notificationArea.innerHTML = `
                <div class="alert alert-warning alert-dismissible fade show" role="alert">
                    <i class="fas fa-exclamation-circle me-2"></i>
                    Synced ${successCount} order(s), but failed to sync ${failCount} order(s).
                    <button type="button" class="btn btn-sm btn-primary ms-3" onclick="syncPendingTransactions()">
                        Retry
                    </button>
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>
            `;
        } else if (failCount > 0) {
            notificationArea.innerHTML = `
                <div class="alert alert-danger alert-dismissible fade show" role="alert">
                    <i class="fas fa-times-circle me-2"></i>
                    Failed to sync ${failCount} order(s).
                    <button type="button" class="btn btn-sm btn-primary ms-3" onclick="syncPendingTransactions()">
                        Retry
                    </button>
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>
            `;
        }
    }
    
    // If all orders synced successfully, remove notification after a delay
    if (failCount === 0) {
        setTimeout(() => {
            if (notificationArea) {
                notificationArea.classList.add('d-none');
            }
        }, 5000);
    }
}

// Store order to IndexedDB when offline
function storeOrderOffline(orderData) {
    if (!window.offlineDB) {
        alert("Offline database not initialized. Please try again later.");
        return;
    }
    
    const transaction = window.offlineDB.transaction(["pendingOrders"], "readwrite");
    const store = transaction.objectStore("pendingOrders");
    
    // Add timestamp and device info for offline order
    orderData.offlineTimestamp = new Date().toISOString();
    orderData.deviceInfo = {
        userAgent: navigator.userAgent,
        screenWidth: window.innerWidth,
        screenHeight: window.innerHeight
    };
    
    const request = store.add(orderData);
    
    request.onsuccess = function() {
        alert("Order saved locally. It will be synced when you're back online.");
        
        // Update notification about pending orders
        checkPendingTransactions();
    };
    
    request.onerror = function() {
        alert("Error saving order locally. Please try again.");
    };
}

// Sync cart data with server periodically
function initCartSync() {
    // Sync cart on page load
    syncCart();
    
    // Setup periodic sync every 30 seconds
    setInterval(syncCart, 30000);
    
    // Check for pending online orders (for staff and admin)
    checkPendingOnlineOrders();
    setInterval(checkPendingOnlineOrders, 60000); // Check every minute
}

// Check for pending online orders
function checkPendingOnlineOrders() {
    // Only run if user might be staff or admin
    if (!document.querySelector('a[href="/admin"]') && 
        !document.querySelector('a[href="/in_store_sale"]')) {
        return;
    }
    
    fetch('/api/pending_orders', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'same-origin'
    })
    .then(response => response.json())
    .then(data => {
        const pendingCount = data.pending_orders ? data.pending_orders.length : 0;
        
        // Update UI with pending orders count
        updatePendingOrdersNotification(pendingCount);
    })
    .catch(error => {
        console.error('Error checking pending orders:', error);
    });
}

// Update pending online orders notification
function updatePendingOrdersNotification(count) {
    const notificationElement = document.getElementById('onlineOrdersNotification');
    const countElement = document.getElementById('pendingOrdersCount');
    
    if (!notificationElement || !countElement) return;
    
    if (count > 0) {
        countElement.textContent = count;
        notificationElement.classList.remove('d-none');
        
        // Add click handler to open modal if clicked (and user is on in-store sale page)
        notificationElement.addEventListener('click', function(event) {
            // Only handle if they click alert but not the close button
            if (event.target.classList.contains('btn-close')) return;
            
            // Navigate to in-store sale page if not already there
            if (!window.location.pathname.includes('/in_store_sale')) {
                window.location.href = '/in_store_sale?openOrdersModal=true';
            } else {
                // Try to open the online orders modal if we're already on the page
                try {
                    const orderModal = new bootstrap.Modal(document.getElementById('onlineOrdersModal'));
                    orderModal.show();
                } catch (e) {
                    console.error("Error opening orders modal:", e);
                }
            }
        });
    } else {
        notificationElement.classList.add('d-none');
    }
}

// Sync cart data with the server
function syncCart() {
    // Only run on pages with cart elements
    if (document.getElementById('cart-count') || document.getElementById('cart-total')) {
        fetch('/sync_cart', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update cart count badge
                const cartCountBadge = document.getElementById('cart-count');
                if (cartCountBadge) {
                    cartCountBadge.textContent = data.cart_count;
                }
                
                // Update cart total if on cart page
                const cartTotalElement = document.getElementById('cart-total');
                if (cartTotalElement) {
                    cartTotalElement.textContent = formatCurrency(data.cart_total);
                }
            }
        })
        .catch(error => console.error('Error syncing cart:', error));
    }
}

// Setup "Add to Cart" buttons
function setupAddToCartButtons() {
    // Keep track of button processing state to prevent double submission
    window.cartButtonsProcessing = window.cartButtonsProcessing || {};
    
    document.querySelectorAll('.add-to-cart-btn').forEach(button => {
        // Remove any existing listeners first
        button.removeEventListener('click', addToCartHandler);
        // Add the event listener
        button.addEventListener('click', addToCartHandler);
    });
    
    function addToCartHandler(event) {
        event.preventDefault();
        const productId = this.getAttribute('data-product-id');
        
        // Check if this button is already processing a request
        if (window.cartButtonsProcessing[productId]) {
            console.log('Preventing duplicate add to cart request for product ID:', productId);
            return;
        }
        
        // Mark this button as processing
        window.cartButtonsProcessing[productId] = true;
        
        // Show loading state
        this.disabled = true;
        this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Adding...';
        
        fetch(`/add_to_cart/${productId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({})
        })
        .then(response => response.json())
        .then(data => {
            // Reset button
            this.disabled = false;
            this.innerHTML = 'Add to Cart';
            
            if (data.success) {
                // Update cart count badge
                const cartCountBadge = document.getElementById('cart-count');
                if (cartCountBadge) {
                    cartCountBadge.textContent = data.cart_count;
                }
                
                // Show success toast
                showToast(`Added ${data.product_name} to cart!`, 'success');
            } else {
                // Show error toast
                showToast(data.error || 'Error adding to cart', 'danger');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            this.disabled = false;
            this.innerHTML = 'Add to Cart';
            showToast('Error adding to cart', 'danger');
        })
        .finally(() => {
            // Reset processing state after a delay to prevent accidental double-clicks
            setTimeout(() => {
                window.cartButtonsProcessing[productId] = false;
            }, 1000);
            this.disabled = false;
        });
    }
}

// Setup quantity update buttons on cart page
function setupQuantityButtons() {
    // Quantity increment/decrement
    document.querySelectorAll('.quantity-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const input = this.parentElement.querySelector('.quantity-input');
            const itemId = input.getAttribute('data-item-id');
            const action = this.getAttribute('data-action');
            
            let currentValue = parseInt(input.value, 10);
            
            if (action === 'increase') {
                currentValue++;
            } else if (action === 'decrease' && currentValue > 1) {
                currentValue--;
            }
            
            input.value = currentValue;
            
            // Update cart on server
            updateCartItem(itemId, currentValue);
        });
    });
    
    // Manual quantity input
    document.querySelectorAll('.quantity-input').forEach(input => {
        input.addEventListener('change', function() {
            const itemId = this.getAttribute('data-item-id');
            let quantity = parseInt(this.value, 10);
            
            // Validate quantity
            if (isNaN(quantity) || quantity < 1) {
                quantity = 1;
                this.value = 1;
            }
            
            // Update cart on server
            updateCartItem(itemId, quantity);
        });
    });
}

// Update cart item quantity
function updateCartItem(itemId, quantity) {
    fetch(`/update_cart/${itemId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify({ quantity: quantity })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update cart count badge
            const cartCountBadge = document.getElementById('cart-count');
            if (cartCountBadge) {
                cartCountBadge.textContent = data.cart_count;
            }
            
            // Update cart total
            const cartTotalElement = document.getElementById('cart-total');
            if (cartTotalElement) {
                cartTotalElement.textContent = formatCurrency(data.cart_total);
            }
            
            // Update item subtotal if applicable
            const itemSubtotalElement = document.querySelector(`.item-subtotal[data-item-id="${itemId}"]`);
            if (itemSubtotalElement) {
                const priceElement = document.querySelector(`.item-price[data-item-id="${itemId}"]`);
                if (priceElement) {
                    const price = parseFloat(priceElement.getAttribute('data-price'));
                    const subtotal = price * quantity;
                    itemSubtotalElement.textContent = formatCurrency(subtotal);
                }
            }
            
            // Show success message
            showToast('Cart updated', 'success');
        } else {
            // Show error message
            showToast(data.error || 'Error updating cart', 'danger');
            
            // Reset quantity to previous value if error
            const input = document.querySelector(`.quantity-input[data-item-id="${itemId}"]`);
            if (input) {
                // Fetch current quantity from server
                syncCart();
            }
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Error updating cart', 'danger');
    });
}

// Setup form validation for checkout and customer forms
function setupFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');
    
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            form.classList.add('was-validated');
        }, false);
    });

    // Listen for checkout form completion
    const checkoutForm = document.getElementById('checkoutForm');
    if (checkoutForm) {
        checkoutForm.addEventListener('submit', function(e) {
            // After form submission is processed successfully
            // This will happen after redirect, using the DOMContentLoaded event
            if (document.referrer.includes('/checkout')) {
                // Refresh all product stock levels after checkout
                setTimeout(() => refreshStock(), 1000);
            }
        });
    }
}

// Helper function to format currency
function formatCurrency(amount) {
    // Use locale from HTML lang attribute or default to 'en-US'
    const locale = document.documentElement.lang || 'en-US';
    
    // Get currency from meta tag or default to 'UGX'
    const currencyMeta = document.querySelector('meta[name="currency"]');
    const currency = currencyMeta ? currencyMeta.getAttribute('content') : 'UGX';
    
    return new Intl.NumberFormat(locale, {
        style: 'currency',
        currency: currency
    }).format(amount);
}

// Helper function to show toast notifications
function showToast(message, type = 'info') {
    // Check if toast container exists, create if not
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toastId = 'toast-' + Date.now();
    const toast = document.createElement('div');
    toast.className = `toast bg-${type} text-white`;
    toast.setAttribute('id', toastId);
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="toast-header bg-${type} text-white">
            <strong class="me-auto">POS System</strong>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
            ${message}
        </div>
    `;
    
    // Add toast to container
    toastContainer.appendChild(toast);
    
    // Initialize and show toast
    const bsToast = new bootstrap.Toast(toast, {
        autohide: true,
        delay: 3000
    });
    bsToast.show();
    
    // Remove toast after it's hidden
    toast.addEventListener('hidden.bs.toast', function() {
        this.remove();
    });
}

// Function to refresh stock information for a product
function refreshStock(productId = null) {
    // Build URL depending on whether we have a specific product ID
    const timestamp = Date.now();
    const url = productId ? 
        `/api/stock_status?product_id=${productId}&_t=${timestamp}` : 
        `/api/stock_status?_t=${timestamp}`;
    
    // Check if we're on the inventory management page
    const isInventoryPage = window.location.pathname.includes('/inventory_management');
    const isAdminPage = window.location.pathname === '/admin';
    
    // For inventory page, we handle refreshes differently (via inventory_management.js)
    // to avoid conflicts between multiple refresh mechanisms
    if (isInventoryPage && !productId) {
        console.log('Skipping refreshStock on inventory page - handled by inventory_management.js');
        return Promise.resolve({success: true, message: 'Handled by inventory_management.js'});
    }
    
    return new Promise((resolve, reject) => {
        let retryCount = 0;
        const maxRetries = 2;
        
        function fetchWithRetry() {
            console.log(`Fetching stock data from ${url}`);
            fetch(url, {
                method: 'GET',
                cache: 'no-store',
                headers: {
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0',
                    'X-Requested-With': 'fetch',
                    'X-Timestamp': timestamp.toString()
                }
            })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`Network response error: ${response.status} ${response.statusText}`);
                    }
                    return response.json();
                })
                .then(data => {
                    console.log('Stock data received:', data);
                    if (data.success) {
                        if (productId && data.product_id == productId) {
                            // Single product update
                            updateProductStockUI(data.product_id, data.stock);
                        } else if (data.products) {
                            // Multiple products update
                            Object.keys(data.products).forEach(id => {
                                const stockInfo = data.products[id];
                                updateProductStockUI(id, stockInfo.stock);
                            });
                        }
                        
                        // For admin page with stock movements, do a hard reload to see updated movements
                        if (isAdminPage && !productId) {
                            // Only reload if there's a stock movements table
                            const movementsTable = document.querySelector('#stock-movements-table');
                            if (movementsTable) {
                                // Special admin reload handling
                                window.location.reload();
                                return;
                            }
                        }
                        
                        resolve(data);
                    } else {
                        console.error('API returned error:', data);
                        reject(new Error(data.error || 'Unknown API error'));
                    }
                })
                .catch(error => {
                    console.error('Error fetching stock data:', error);
                    if (retryCount < maxRetries) {
                        retryCount++;
                        console.log(`Retrying (${retryCount}/${maxRetries})...`);
                        setTimeout(fetchWithRetry, 1000);
                    } else {
                        reject(error);
                    }
                });
        }
        
        fetchWithRetry();
    });
}

// Function to update product stock UI elements
function updateProductStockUI(productId, stockLevel) {
    // First find all elements that display stock for this product
    const stockElements = document.querySelectorAll(`.product-stock[data-product-id="${productId}"]`);
    
    if (stockElements.length === 0) {
        console.log(`No product-stock elements found for product ID ${productId}`);
        return;
    }
    
    console.log(`Updating UI for product ID ${productId} with stock level ${stockLevel}`);
    
    stockElements.forEach(element => {
        // Get the original content to preserve format
        const originalContent = element.textContent.trim();
        
        // Check which format is being used
        if (originalContent.toLowerCase().includes('stock:')) {
            // Format: "Stock: X"
            element.textContent = `Stock: ${stockLevel}`;
        } else if (originalContent.toLowerCase().includes('in stock:')) {
            // Format: "In Stock: X {unit}"
            const parts = originalContent.split(' ');
            const unitIndex = parts.findIndex(p => p.trim().length > 0 && !p.includes(':') && isNaN(parseFloat(p)));
            const unit = unitIndex >= 0 ? parts[unitIndex].trim() : '';
            element.textContent = `In Stock: ${stockLevel} ${unit}`;
        } else {
            // Just update the number directly
            element.textContent = stockLevel.toString();
        }
        
        // Update color based on stock level
        const product = element.closest('.product-card') || element.closest('.product-item');
        if (product) {
            const addToCartBtn = product.querySelector('.add-to-cart');
            if (addToCartBtn) {
                if (stockLevel <= 0) {
                    addToCartBtn.classList.add('btn-secondary');
                    addToCartBtn.classList.remove('btn-primary');
                    addToCartBtn.disabled = true;
                    addToCartBtn.textContent = 'Out of Stock';
                } else {
                    addToCartBtn.classList.add('btn-primary');
                    addToCartBtn.classList.remove('btn-secondary');
                    addToCartBtn.disabled = false;
                    addToCartBtn.innerHTML = '<i class="fas fa-cart-plus me-1"></i>Add to Cart';
                }
            }
        }
    });
} 