// Service Worker for POS System
// Handles caching and offline functionality

const CACHE_NAME = 'pos-system-v2'; // Increment cache version
const OFFLINE_URL = '/offline.html';

// Files to cache for offline use
const ASSETS_TO_CACHE = [
  '/',
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

// Flag to know if icon database is ready
let iconDBReady = false;

// Listen for messages from clients
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'ICON_STORAGE_READY') {
    iconDBReady = true;
    console.log('Icon storage is ready');
  }
});

// Install event - cache the assets
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Opened cache');
        return cache.addAll(ASSETS_TO_CACHE);
      })
      .then(() => self.skipWaiting())
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.filter(cacheName => {
          return cacheName !== CACHE_NAME;
        }).map(cacheName => {
          return caches.delete(cacheName);
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch event - serve from cache or fetch from network
self.addEventListener('fetch', event => {
  // Skip cross-origin requests
  if (!event.request.url.startsWith(self.location.origin)) {
    return;
  }

  // Skip non-GET requests
  if (event.request.method !== 'GET') {
    // For API calls when offline, we'll handle them in the app
    if (event.request.url.includes('/api/') && !navigator.onLine) {
      event.respondWith(
        new Response(JSON.stringify({ 
          error: 'You are offline',
          offline: true
        }), {
          headers: { 'Content-Type': 'application/json' }
        })
      );
    }
    return;
  }

  // Handle generated icon requests - these are special URLs we'll intercept
  if (event.request.url.includes('generated-icons/icon-')) {
    const sizeMatch = event.request.url.match(/icon-(\d+)\.png/);
    if (sizeMatch && sizeMatch[1]) {
      const size = parseInt(sizeMatch[1]);
      event.respondWith(createIconResponse(size));
      return;
    }
  }

  // Special handling for icon requests from the manifest
  if (event.request.url.includes('/images/icons/')) {
    event.respondWith(
      caches.match(event.request)
        .then(cachedResponse => {
          if (cachedResponse) {
            return cachedResponse;
          }
          
          // Try to get from network
          return fetch(event.request)
            .then(response => {
              // Clone the response - one to return, one to cache
              if (response && response.status === 200) {
                const responseToCache = response.clone();
                caches.open(CACHE_NAME)
                  .then(cache => {
                    cache.put(event.request, responseToCache);
                  });
                return response;
              }
              
              // If icon not found, get a dynamically generated one
              const sizeMatch = event.request.url.match(/icon-(\d+)x(\d+)\.png/);
              if (sizeMatch && sizeMatch[1]) {
                const size = parseInt(sizeMatch[1]);
                return getIconFromIndexedDB(`icon-${size}x${size}`);
              }
              
              // Default fallback
              return getIconFromIndexedDB('icon-144x144');
            })
            .catch(() => {
              // Network error, try to get from IndexedDB
              const sizeMatch = event.request.url.match(/icon-(\d+)x(\d+)\.png/);
              if (sizeMatch && sizeMatch[1]) {
                const size = parseInt(sizeMatch[1]);
                return getIconFromIndexedDB(`icon-${size}x${size}`);
              }
              
              // Default fallback
              return getIconFromIndexedDB('icon-144x144');
            });
        })
    );
    return;
  }

  // Handle other requests
  event.respondWith(
    caches.match(event.request)
      .then(cachedResponse => {
        if (cachedResponse) {
          return cachedResponse;
        }

        return fetch(event.request)
          .then(response => {
            // Don't cache responses that aren't successful
            if (!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }

            // Clone the response - one to return, one to cache
            const responseToCache = response.clone();

            caches.open(CACHE_NAME)
              .then(cache => {
                cache.put(event.request, responseToCache);
              });

            return response;
          })
          .catch(error => {
            // If the network is unavailable, try to serve the offline page
            if (event.request.mode === 'navigate') {
              return caches.match(OFFLINE_URL);
            }
            
            // For image requests, return a fallback
            if (event.request.destination === 'image') {
              return getIconFromIndexedDB('offline-image');
            }

            return new Response('Network error happened', {
              status: 408,
              headers: { 'Content-Type': 'text/plain' }
            });
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