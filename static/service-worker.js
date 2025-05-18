// Service Worker for POS System
// Handles caching and offline functionality

const CACHE_NAME = 'pos-system-cache-v1';
const urlsToCache = [
    '/',
    '/static/css/style.css',
    '/static/js/app.js',
    '/static/js/inventory_management.js',
    '/static/js/reports.js',
    '/templates/offline.html'
];

// Don't add volatile timestamps that change with every request
// const CACHE_VERSION = new Date().toISOString(); 

// Files to cache for offline use - static files only
const ASSETS_TO_CACHE = [
  '/offline.html',
  '/static/js/app.js',
  '/static/js/service-worker-update.js',
  '/static/js/create-fallback-images.js',
  '/static/js/update-manifest.js',
  '/static/js/icon-handler.js',
  '/static/sounds/notification.wav',
  '/static/favicon.ico',
  '/static/manifest.json',
  // Bootstrap and other third-party assets are cached separately
];

// Dynamic routes that should NEVER be cached
const NEVER_CACHE_ROUTES = [
  '/',
  '/admin',
  '/cart',
  '/checkout',
  '/profile',
  '/login',
  '/inventory_management',
  '/add_product',
  '/in_store_sale',
  '/reports',
  '/index',
  '/edit_product',
  '/api/stock_status',
  '/product',
  '/api/sales',
  '/restock',
  '/staff/orders',
  '/staff/order',
  '/get_cart_count',
  '/receipt'
];

// Flag to know if icon database is ready
let iconDBReady = false;

// Listen for messages from clients
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'ICON_STORAGE_READY') {
    iconDBReady = true;
    console.log('Icon storage is ready');
  }
  
  // Force refresh on content update - add rate limiting
  if (event.data && event.data.type === 'CONTENT_UPDATED') {
    // Check if we've refreshed recently to prevent loops
    const lastRefresh = self.lastRefreshTime || 0;
    const now = Date.now();
    const ONE_MINUTE = 60 * 1000;
    
    // Only refresh if it's been at least a minute since last refresh
    if (now - lastRefresh > ONE_MINUTE) {
      console.log('Content update detected, refreshing caches');
      self.lastRefreshTime = now;
      
      event.waitUntil(
        caches.keys().then(cacheNames => {
          return Promise.all(
            cacheNames.filter(cacheName => {
              return cacheName.startsWith('pos-system-');
            }).map(cacheName => {
              return caches.delete(cacheName);
            })
          );
        }).then(() => {
          // Don't automatically notify clients to refresh
          // Only refresh specific resources
          return self.clients.matchAll().then(clients => {
            clients.forEach(client => {
              client.postMessage({
                type: 'UPDATE_AVAILABLE'
              });
            });
          });
        })
      );
    } else {
      console.log('Ignoring refresh request - too soon since last refresh');
    }
  }
});

// Install event - cache the assets
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(urlsToCache))
    );
});

// Activate event - clean up old caches and claim clients immediately
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== CACHE_NAME) {
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
});

// Fetch event - serve from cache or fetch from network
self.addEventListener('fetch', event => {
    // Bypass Socket.IO requests
    if (event.request.url.includes('/socket.io/')) {
        return;
    }

    event.respondWith(
        caches.match(event.request)
            .then(response => {
                if (response) {
                    return response;
                }
                return fetch(event.request)
                    .catch(() => {
                        if (event.request.mode === 'navigate') {
                            return caches.match('/templates/offline.html');
                        }
                    });
            })
    );
});

// Function to get an icon from IndexedDB
function getIconFromIndexedDB(iconName) {
  return new Promise((resolve) => {
    const openRequest = indexedDB.open('icon-cache-db', 1);
    
    openRequest.onerror = function() {
      // Fallback to generated icon
      resolve(createTextIcon(144));
    };
    
    openRequest.onsuccess = function() {
      const db = openRequest.result;
      
      if (!db.objectStoreNames.contains('icons')) {
        // No object store, fallback to generated icon
        resolve(createTextIcon(144));
        return;
      }
      
      const transaction = db.transaction(['icons'], 'readonly');
      const store = transaction.objectStore('icons');
      const getRequest = store.get(iconName);
      
      getRequest.onsuccess = function() {
        if (getRequest.result && getRequest.result.blob) {
          // Return icon from IndexedDB
          resolve(new Response(getRequest.result.blob, {
            headers: { 'Content-Type': 'image/png' }
          }));
        } else {
          // Icon not found in IndexedDB, create one
          const sizeParts = iconName.split('-');
          const size = sizeParts.length > 1 && sizeParts[1].includes('x') 
                     ? parseInt(sizeParts[1].split('x')[0]) 
                     : 144;
          resolve(createTextIcon(size));
        }
      };
      
      getRequest.onerror = function() {
        // Error getting from IndexedDB, fallback to generated icon
        resolve(createTextIcon(144));
      };
    };
  });
}

// Function to create a simple text-based icon as fallback
function createTextIcon(size) {
  // Create a simple icon with text in memory
  const canvas = new OffscreenCanvas(size, size);
  const ctx = canvas.getContext('2d');
  
  // Draw background
  ctx.fillStyle = '#2c3e50';
  ctx.fillRect(0, 0, size, size);
  
  // Draw text
  ctx.fillStyle = 'white';
  ctx.font = `bold ${Math.floor(size/2)}px Arial, sans-serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText('POS', size/2, size/2);
  
  // Convert to response
  return canvas.convertToBlob({type: 'image/png'})
    .then(blob => {
      return new Response(blob, {
        status: 200,
        headers: {'Content-Type': 'image/png'}
      });
    });
}

// Function to create a simple text-based icon response
function createIconResponse(size) {
  // Create a simple icon with text in memory
  const canvas = new OffscreenCanvas(size, size);
  const ctx = canvas.getContext('2d');
  
  // Draw background
  ctx.fillStyle = '#2c3e50';
  ctx.fillRect(0, 0, size, size);
  
  // Draw text
  ctx.fillStyle = 'white';
  ctx.font = `bold ${Math.floor(size/2)}px Arial, sans-serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText('POS', size/2, size/2);
  
  // Convert to response
  return canvas.convertToBlob({type: 'image/png'})
    .then(blob => {
      return new Response(blob, {
        status: 200,
        headers: {'Content-Type': 'image/png'}
      });
    });
}

// Handle background sync for offline orders
self.addEventListener('sync', event => {
  if (event.tag === 'sync-offline-orders') {
    event.waitUntil(syncOfflineOrders());
  }
});

// Function to sync offline orders
function syncOfflineOrders() {
  return new Promise((resolve, reject) => {
    // We'll handle this in the main app.js file
    resolve();
  });
}

// Listen for push notifications
self.addEventListener('push', event => {
  if (!event.data) {
    console.log('This push event has no data.');
    return;
  }

  const notification = event.data.json();
  const title = notification.title || 'POS System Notification';
  const options = {
    body: notification.body || 'You have a new notification',
    icon: notification.icon || '/static/images/icons/icon-72x72.png',
    badge: notification.badge || '/static/images/icons/icon-72x72.png',
    data: notification.data
  };

  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

// Handle notification clicks
self.addEventListener('notificationclick', event => {
  event.notification.close();

  // This looks to see if the current is already open and focuses it
  event.waitUntil(
    clients.matchAll({
      type: 'window'
    })
    .then(function(clientList) {
      for (var i = 0; i < clientList.length; i++) {
        var client = clientList[i];
        if (client.url.includes('/in_store_sale') && 'focus' in client)
          return client.focus();
      }
      if (clients.openWindow)
        return clients.openWindow('/in_store_sale');
    })
  );
});

// Additional check to prevent caching for any URLs with product-related information
function shouldAvoidCaching(url) {
  const path = new URL(url).pathname;
  const urlObj = new URL(url);
  
  // Check for paths that should never be cached
  if (path.includes('product') || 
      path.includes('inventory') || 
      path.includes('stock') || 
      path.includes('cart') ||
      path.includes('order') ||
      path.includes('api') ||
      path.includes('checkout') ||
      path.includes('receipt')) {
    return true;
  }
  
  // Check for query params that indicate fresh data is needed
  if (urlObj.searchParams.has('_t') || 
      urlObj.searchParams.has('cache_bust') ||
      urlObj.searchParams.has('fresh')) {
    return true;
  }
  
  return false;
} 