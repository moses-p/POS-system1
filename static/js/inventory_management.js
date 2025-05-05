// Inventory Management JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Check if we have a refresh parameter in the URL
    const urlParams = new URLSearchParams(window.location.search);
    const hasRefresh = urlParams.get('refresh');
    
    // Set up force refresh button functionality
    const refreshBtn = document.getElementById('forceRefreshBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function() {
            forceRefresh();
        });
    }
    
    // If we've redirected here after a stock update, force a complete page reload
    // This bypasses any browser caching issues
    if (document.referrer.includes('restock') || hasRefresh === 'true') {
        console.log("Detected return from restock page, forcing reload");
        // Clear URL parameter and reload
        const url = new URL(window.location.href);
        url.searchParams.delete('refresh');
        window.location.href = url.toString();
        return; // Skip further execution to prevent double loading
    }
    
    // Auto-refresh stock data every 30 seconds
    setInterval(refreshStock, 30000);
    
    // Initial refresh
    refreshStock();
});

// Function to force refresh the page and stock data
function forceRefresh() {
    const btn = document.getElementById('forceRefreshBtn');
    if (!btn) return;
    
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Refreshing...';
    
    try {
        // Instead of using the API which might have caching issues,
        // do a hard reload of the page with cache-busting
        const timestamp = new Date().getTime();
        window.location.href = `${window.location.pathname}?refresh=true&t=${timestamp}`;
    } catch (e) {
        console.error('Error refreshing stock:', e);
        btn.innerHTML = '<i class="fas fa-exclamation-triangle me-1"></i> Error!';
        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }, 1500);
    }
}

// Function to refresh stock information via API
function refreshStock() {
    console.log('Refreshing inventory data...');
    
    // Build URL with cache-busting timestamp
    const timestamp = Date.now();
    const url = `/api/stock_status?_t=${timestamp}`;
    
    // Add visual feedback if the refresh button exists
    const refreshBtn = document.getElementById('forceRefreshBtn');
    let originalText = '';
    if (refreshBtn) {
        originalText = refreshBtn.innerHTML;
        refreshBtn.innerHTML = '<i class="fas fa-sync fa-spin me-1"></i> Refreshing...';
    }
    
    // Fetch the latest stock data
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
        if (data.success && data.products) {
            // Update the stock display for all products
            updateInventoryTable(data.products);
            
            // Update summary counts
            if (typeof updateSummaryCounts === 'function') {
                updateSummaryCounts(data.products);
            }
            
            // Show success feedback
            if (refreshBtn) {
                refreshBtn.innerHTML = '<i class="fas fa-check me-1"></i> Updated!';
                setTimeout(() => {
                    refreshBtn.innerHTML = originalText;
                }, 1500);
            }
        } else {
            throw new Error(data.error || 'Unknown API error');
        }
    })
    .catch(error => {
        console.error('Error refreshing stock:', error);
        
        // Show error feedback
        if (refreshBtn) {
            refreshBtn.innerHTML = '<i class="fas fa-exclamation-triangle me-1"></i> Failed!';
            setTimeout(() => {
                refreshBtn.innerHTML = originalText;
            }, 2000);
        }
    });
}

// Update the inventory table with fresh stock data
function updateInventoryTable(products) {
    // Find all stock cells in the inventory table with the product-stock class
    const stockCells = document.querySelectorAll('.product-stock[data-product-id]');
    
    stockCells.forEach(cell => {
        const productId = cell.getAttribute('data-product-id');
        if (products[productId]) {
            // Get the current stock text which may include the unit
            const currentText = cell.textContent.trim();
            const stockInfo = products[productId];
            
            // Extract the unit from current text (anything after the number)
            const matches = currentText.match(/[\d.]+\s*(.*)$/);
            const unit = matches && matches[1] ? matches[1].trim() : '';
            
            // Update the text with the new stock value and the unit
            cell.textContent = `${stockInfo.stock} ${unit}`;
            
            // Highlight the cell to show it was updated
            cell.classList.add('bg-light');
            
            // Add a flashy transition
            cell.style.transition = 'background-color 0.5s ease';
            cell.style.backgroundColor = '#d1e7dd';  // light green
            setTimeout(() => {
                cell.style.backgroundColor = '';
            }, 2000);
            
            // Also update the status cell (column 6)
            const row = cell.closest('tr');
            if (row) {
                const statusCell = row.querySelector('td:nth-child(6)');
                if (statusCell) {
                    const badgeSpan = statusCell.querySelector('.badge');
                    if (badgeSpan) {
                        if (stockInfo.stock <= 0) {
                            // Out of stock
                            badgeSpan.className = 'badge bg-danger';
                            badgeSpan.textContent = 'Out of Stock';
                        } else if (stockInfo.low_stock_threshold && stockInfo.stock <= stockInfo.low_stock_threshold) {
                            // Low stock
                            badgeSpan.className = 'badge bg-warning';
                            badgeSpan.textContent = 'Low Stock';
                        } else if (stockInfo.max_stock && stockInfo.stock >= stockInfo.max_stock) {
                            // Overstocked
                            badgeSpan.className = 'badge bg-info';
                            badgeSpan.textContent = 'Overstocked';
                        } else {
                            // Normal stock level
                            badgeSpan.className = 'badge bg-success';
                            badgeSpan.textContent = 'In Stock';
                        }
                    }
                }
            }
        }
    });
}

// Recompute summary counts
function updateSummaryCounts(products) {
    let total = 0;
    let low = 0;
    let out = 0;
    Object.values(products).forEach(p => {
        total++;
        if (p.stock <= 0) {
            out++;
        } else if ((p.reorder_point && p.stock <= p.reorder_point)) {
            low++;
        }
    });
    const totalEl = document.getElementById('totalProductsCount');
    if (totalEl) totalEl.textContent = total;
    const lowEl = document.getElementById('lowStockCount');
    if (lowEl) lowEl.textContent = low;
    const outEl = document.getElementById('outOfStockCount');
    if (outEl) outEl.textContent = out;
} 