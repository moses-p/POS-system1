// Reports JavaScript for sales data refreshing

document.addEventListener('DOMContentLoaded', function() {
    // Set up auto-refresh functionality for reports
    console.log('Initializing reports auto-refresh functionality');
    
    // Initialize refresh timers
    initAutoRefresh();
    
    // Add event listener for tab changes to refresh data when switching tabs
    const tabElements = document.querySelectorAll('button[data-bs-toggle="tab"]');
    tabElements.forEach(tab => {
        tab.addEventListener('shown.bs.tab', function(event) {
            const targetId = event.target.id;
            
            if (targetId === 'daily-tab') {
                refreshCurrentReport('daily');
            } else if (targetId === 'weekly-tab') {
                refreshCurrentReport('weekly');
            } else if (targetId === 'monthly-tab') {
                refreshCurrentReport('monthly');
            } else if (targetId === 'yearly-tab') {
                refreshCurrentReport('yearly');
            }
        });
    });
    
    // Set up manual refresh button
    const refreshBtn = document.getElementById('refreshReportBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function() {
            // Find the active tab
            const activeTab = document.querySelector('.nav-link.active');
            if (activeTab) {
                const tabId = activeTab.id;
                if (tabId === 'daily-tab') {
                    refreshCurrentReport('daily');
                } else if (tabId === 'weekly-tab') {
                    refreshCurrentReport('weekly');
                } else if (tabId === 'monthly-tab') {
                    refreshCurrentReport('monthly');
                } else if (tabId === 'yearly-tab') {
                    refreshCurrentReport('yearly');
                }
            }
        });
    }
    
    // Add cache busting to all fetch requests
    const originalFetch = window.fetch;
    window.fetch = function(url, options = {}) {
        if (typeof url === 'string') {
            // Add cache-busting parameter if it's a reports API call
            if (url.includes('/api/sales/')) {
                const separator = url.includes('?') ? '&' : '?';
                url = `${url}${separator}_t=${Date.now()}`;
            }
        }
        
        // Ensure headers object exists
        if (!options.headers) {
            options.headers = {};
        }
        
        // Add cache control headers
        options.headers = {
            ...options.headers,
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
            'X-Requested-With': 'XMLHttpRequest'
        };
        
        // Ensure cache mode is set to no-store
        options.cache = 'no-store';
        
        return originalFetch(url, options);
    };
});

// Initialize auto-refresh functionality
function initAutoRefresh() {
    // Refresh the active report every 60 seconds
    setInterval(function() {
        console.log("Auto-refreshing report data...");
        // Find the active tab
        const activeTab = document.querySelector('.nav-link.active');
        if (activeTab) {
            const tabId = activeTab.id;
            if (tabId === 'daily-tab') {
                refreshCurrentReport('daily');
            } else if (tabId === 'weekly-tab') {
                refreshCurrentReport('weekly');
            } else if (tabId === 'monthly-tab') {
                refreshCurrentReport('monthly');
            } else if (tabId === 'yearly-tab') {
                refreshCurrentReport('yearly');
            }
        }
    }, 60000); // 60 seconds
    
    // Initial refresh for the default tab (daily)
    setTimeout(function() {
        refreshCurrentReport('daily');
    }, 1000);
}

// Refresh the current report data
function refreshCurrentReport(reportType) {
    console.log(`Refreshing ${reportType} report data...`);
    
    // Add visual feedback to refresh button if one exists
    const refreshBtn = document.getElementById('refreshReportBtn');
    if (refreshBtn) {
        const originalText = refreshBtn.innerHTML;
        refreshBtn.innerHTML = '<i class="fas fa-sync fa-spin me-1"></i> Refreshing...';
        setTimeout(() => {
            refreshBtn.innerHTML = originalText;
        }, 2000);
    }
    
    switch (reportType) {
        case 'daily':
            refreshDailyReport();
            break;
        case 'weekly':
            refreshWeeklyReport();
            break;
        case 'monthly':
            refreshMonthlyReport();
            break;
        case 'yearly':
            refreshYearlyReport();
            break;
    }
}

// Refresh daily report data
function refreshDailyReport() {
    // Get current date range from form fields
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    
    if (!startDate || !endDate) {
        console.warn("Cannot refresh daily report: date range not set");
        return; // Don't refresh if dates aren't set
    }
    
    // Fetch updated data with cache busting
    const timestamp = Date.now();
    fetch(`/api/sales/daily?start_date=${startDate}&end_date=${endDate}&_t=${timestamp}`, {
        method: 'GET',
        cache: 'no-store',
        headers: {
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Server returned ${response.status}: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        if (typeof updateDailyChart === 'function') {
            updateDailyChart(data);
            updateDailyTable(data);
            
            // Flash feedback that data was updated
            const reportCard = document.querySelector('#daily .card');
            if (reportCard) {
                reportCard.style.transition = 'background-color 0.5s ease';
                reportCard.style.backgroundColor = '#d1e7dd';
                setTimeout(() => {
                    reportCard.style.backgroundColor = '';
                }, 1000);
            }
            
            console.log("Daily report data updated successfully");
        } else {
            console.error("updateDailyChart function not found");
        }
    })
    .catch(error => {
        console.error('Error refreshing daily report:', error);
    });
}

// Refresh weekly report data
function refreshWeeklyReport() {
    const timestamp = Date.now();
    fetch(`/api/sales/weekly?_t=${timestamp}`, {
        method: 'GET',
        cache: 'no-store',
        headers: {
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Server returned ${response.status}: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        if (typeof updateWeeklyChart === 'function') {
            updateWeeklyChart(data);
            updateWeeklyTable(data);
            
            // Flash feedback
            const reportCard = document.querySelector('#weekly .card');
            if (reportCard) {
                reportCard.style.transition = 'background-color 0.5s ease';
                reportCard.style.backgroundColor = '#d1e7dd';
                setTimeout(() => {
                    reportCard.style.backgroundColor = '';
                }, 1000);
            }
            
            console.log("Weekly report data updated successfully");
        } else {
            console.error("updateWeeklyChart function not found");
        }
    })
    .catch(error => {
        console.error('Error refreshing weekly report:', error);
    });
}

// Refresh monthly report data
function refreshMonthlyReport() {
    const timestamp = Date.now();
    fetch(`/api/sales/monthly?_t=${timestamp}`, {
        method: 'GET',
        cache: 'no-store',
        headers: {
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Server returned ${response.status}: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        if (typeof updateMonthlyChart === 'function') {
            updateMonthlyChart(data);
            updateMonthlyTable(data);
            
            // Flash feedback
            const reportCard = document.querySelector('#monthly .card');
            if (reportCard) {
                reportCard.style.transition = 'background-color 0.5s ease';
                reportCard.style.backgroundColor = '#d1e7dd';
                setTimeout(() => {
                    reportCard.style.backgroundColor = '';
                }, 1000);
            }
            
            console.log("Monthly report data updated successfully");
        } else {
            console.error("updateMonthlyChart function not found");
        }
    })
    .catch(error => {
        console.error('Error refreshing monthly report:', error);
    });
}

// Refresh yearly report data
function refreshYearlyReport() {
    const timestamp = Date.now();
    fetch(`/api/sales/yearly?_t=${timestamp}`, {
        method: 'GET',
        cache: 'no-store',
        headers: {
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Server returned ${response.status}: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        if (typeof updateYearlyChart === 'function') {
            updateYearlyChart(data);
            updateYearlyTable(data);
            
            // Flash feedback
            const reportCard = document.querySelector('#yearly .card');
            if (reportCard) {
                reportCard.style.transition = 'background-color 0.5s ease';
                reportCard.style.backgroundColor = '#d1e7dd';
                setTimeout(() => {
                    reportCard.style.backgroundColor = '';
                }, 1000);
            }
            
            console.log("Yearly report data updated successfully");
        } else {
            console.error("updateYearlyChart function not found");
        }
    })
    .catch(error => {
        console.error('Error refreshing yearly report:', error);
    });
} 