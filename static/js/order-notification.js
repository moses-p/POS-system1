// Order notification system
let orderAlarm;
let currentAlarmOrderId = null;
let lastCheckTime = 0;
let isAdmin = false;
let isStaff = false;
let pendingOrderIds = new Set(); // Keep track of all unviewed orders

// Create a data URL for a simple beep sound as fallback
const ALARM_SOUND_DATA_URL = 'data:audio/mp3;base64,SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU4Ljc2LjEwMAAAAAAAAAAAAAAA//tQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAASW5mbwAAAA8AAABEAABwmgAFBwoPEhUXHyIkJy8yMzs+QEhLTVVYWmJlaGpydXd/goSMj5GZnJ6mqKyvsLi7vcXHyNDT1dfe4OLq7e/x+fv9AAAA//tQxAADwAABpAAAACAAADSAAAAETEFNRTMuMTAwVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVX/+1DEBgPAAAGkAAAAIAAANIAAAARVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV//tQxAeD0AAAaQAAAAgAAA0gAAABFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV';

// Detect user role from meta tag or body class
function detectUserRole() {
    // Method 1: Check if admin username is displayed in nav
    const navUsername = document.querySelector('.navbar-nav .nav-link');
    if (navUsername && navUsername.textContent.includes('Admin:')) {
        isAdmin = true;
        console.log('User detected as admin');
    }
    
    // Method 2: Check for admin panel link
    const adminLink = document.querySelector('a[href*="admin"]');
    if (adminLink) {
        isAdmin = true;
        console.log('Admin panel link found, user is admin');
    }
    
    // Method 3: Check for staff pages
    const staffLink = document.querySelector('a[href*="staff_dashboard"]');
    if (staffLink) {
        isStaff = true;
        console.log('Staff dashboard link found, user is staff');
    }
    
    // Always report role for debugging
    console.log('User roles:', { isAdmin, isStaff });
}

// Create audio element with fallback beep sound
let alarmSound = new Audio(ALARM_SOUND_DATA_URL);
alarmSound.loop = true;

// Try to load the custom sound file if it exists
fetch('/static/sounds/order-alarm.mp3')
    .then(response => {
        if (response.ok) {
            alarmSound = new Audio('/static/sounds/order-alarm.mp3');
            alarmSound.loop = true;
            console.log('Custom alarm sound loaded successfully');
        } else {
            console.log('Using fallback alarm sound');
        }
    })
    .catch(error => {
        console.log('Error loading custom alarm sound, using fallback');
    });

// Function to check for new orders
function checkForNewOrders() {
    // Prevent too frequent checks (at least 5 seconds apart)
    const now = Date.now();
    if (now - lastCheckTime < 5000) {
        return;
    }
    lastCheckTime = now;
    
    console.log('Checking for new orders...');
    fetch('/api/check_new_orders')
        .then(response => {
            // Check if the response is JSON
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                // Not JSON, likely an HTML error page
                throw new Error('Response is not JSON');
            }
            return response.json();
        })
        .then(data => {
            console.log('Order check response:', data);
            
            // Both admin and staff should receive notifications
            // Remove the authentication check as we want to allow
            // admin to receive notifications too
            
            // If we have new orders
            if (data.new_order && data.order_id) {
                // Add to our pending orders set
                pendingOrderIds.add(data.order_id);
                
                // Start the alarm if not already playing
                if (!orderAlarm) {
                    console.log(`New order detected: Order #${data.order_id}`);
                    startAlarm();
                    showOrderNotification(data);
                }
            } else if (data.new_orders === 0) {
                // If there are no new orders at all, clear our tracking and stop alarm
                pendingOrderIds.clear();
                stopAlarm();
            }
        })
        .catch(error => {
            console.error('Error checking for new orders:', error);
            // Don't keep retrying if there's an auth issue
            if (error.message === 'Response is not JSON') {
                console.log('Pausing order checks due to authentication issue');
                // Pause checks for 30 seconds
                setTimeout(() => {
                    console.log('Resuming order checks after auth error pause');
                    lastCheckTime = 0;  // Reset to allow immediate check
                }, 30000);
            }
        });
}

// Function to start the alarm
function startAlarm() {
    console.log(`Starting alarm for unviewed orders`);
    
    // Try to play the sound
    try {
        alarmSound.play()
            .catch(e => console.log('Failed to play alarm sound:', e));
    } catch (e) {
        console.error('Error playing alarm sound:', e);
    }
    
    // Visual indicator - flash the title
    if (!orderAlarm) {
        let originalTitle = document.title;
        let newOrderTitle = "🔔 NEW ORDER! 🔔";
        let titleToggle = false;
        
        orderAlarm = setInterval(() => {
            document.title = titleToggle ? originalTitle : newOrderTitle;
            titleToggle = !titleToggle;
        }, 1000);
    }
}

// Function to stop the alarm
function stopAlarm() {
    if (orderAlarm) {
        console.log('Stopping alarm - all orders viewed');
        
        // Stop audio
        alarmSound.pause();
        alarmSound.currentTime = 0;
        
        // Stop title flashing
        clearInterval(orderAlarm);
        orderAlarm = null;
        document.title = document.title.includes("NEW ORDER") ? 
            "POS System" : document.title;
    }
}

// Function to show notification for new order
function showOrderNotification(orderData) {
    const notifyContainer = document.getElementById('orderNotificationContainer');
    if (!notifyContainer) {
        console.error('Notification container not found');
        return;
    }
    
    console.log(`Creating notification for order #${orderData.order_id}`);
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = 'order-notification alert alert-warning alert-dismissible fade show';
    notification.setAttribute('data-order-id', orderData.order_id);
    
    // Determine the correct URL based on user role - both admin and staff can see orders
    let orderViewUrl = '/staff/order/' + orderData.order_id;
    
    notification.innerHTML = `
        <strong>New Order #${orderData.order_id}!</strong>
        <p>${orderData.customer_name || 'Customer'} - ${orderData.total_amount} ${orderData.currency || 'UGX'}</p>
        <a href="${orderViewUrl}" class="btn btn-sm btn-primary view-order-btn">View Order</a>
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Add notification to container
    notifyContainer.appendChild(notification);
    
    // Auto-dismiss notification after 30 seconds (but keep the alarm going)
    setTimeout(() => {
        if (notification.parentNode) {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 500);
        }
    }, 30000);
    
    // Handle view order click to mark order as viewed
    const viewBtn = notification.querySelector('.view-order-btn');
    viewBtn.addEventListener('click', () => {
        markOrderViewed(orderData.order_id);
    });
    
    // Handle notification close button (only closes notification, doesn't mark as viewed)
    const closeBtn = notification.querySelector('.btn-close');
    closeBtn.addEventListener('click', () => notification.remove());
}

// Function to mark an order as viewed
function markOrderViewed(orderId) {
    console.log(`Marking order #${orderId} as viewed`);
    fetch(`/api/mark_order_viewed/${orderId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        console.log('Mark viewed response:', data);
        if (data.success) {
            // Remove this order from our pending set
            pendingOrderIds.delete(orderId);
            
            // If there are no more unviewed orders, stop the alarm
            if (pendingOrderIds.size === 0) {
                stopAlarm();
            }
            
            // Close any remaining notifications for this order
            document.querySelectorAll(`.order-notification[data-order-id="${orderId}"]`)
                .forEach(notification => {
                    notification.classList.remove('show');
                    setTimeout(() => notification.remove(), 500);
                });
        }
    })
    .catch(error => console.error('Error marking order as viewed:', error));
}

// Check for new orders on page load and every 10 seconds
document.addEventListener('DOMContentLoaded', function() {
    console.log('Order notification system initializing...');
    
    // Detect user role first
    detectUserRole();
    
    // Create notification container if it doesn't exist
    if (!document.getElementById('orderNotificationContainer')) {
        console.log('Creating notification container');
        const container = document.createElement('div');
        container.id = 'orderNotificationContainer';
        container.className = 'order-notifications';
        document.body.appendChild(container);
        
        // Add CSS for notifications
        const style = document.createElement('style');
        style.textContent = `
            .order-notifications {
                position: fixed;
                top: 70px;
                right: 20px;
                z-index: 1050;
                max-width: 350px;
            }
            .order-notification {
                margin-bottom: 10px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.15);
                border-left: 4px solid #fd7e14;
            }
        `;
        document.head.appendChild(style);
    } else {
        console.log('Notification container already exists');
    }
    
    // Initial check
    console.log('Performing initial order check');
    checkForNewOrders();
    
    // Start periodic checks
    console.log('Setting up periodic order checks every 10 seconds');
    setInterval(checkForNewOrders, 10000);
}); 