// Prevent double submissions on in-store sale page
document.addEventListener('DOMContentLoaded', function() {
    const saleForm = document.getElementById('saleForm');
    
    if (saleForm) {
        // Flag to track if form has been submitted
        let formSubmitted = false;
        
        // Store original button text
        const submitButton = document.getElementById('completeSaleBtn');
        const originalButtonText = submitButton ? submitButton.textContent : 'Complete Sale';
        
        // Add additional storage to prevent duplicate submission
        const preventDuplicateSale = () => {
            // Save timestamp of submission attempt to localStorage
            localStorage.setItem('lastSaleSubmitTime', Date.now());
        };
        
        // Check if form was recently submitted (within 10 seconds)
        const wasRecentlySubmitted = () => {
            const lastSubmitTime = localStorage.getItem('lastSaleSubmitTime');
            if (!lastSubmitTime) return false;
            
            const timeDiff = Date.now() - parseInt(lastSubmitTime);
            return timeDiff < 10000; // 10 seconds
        };
        
        // If there was a very recent submission, disable the button initially
        if (wasRecentlySubmitted() && submitButton) {
            submitButton.disabled = true;
            submitButton.textContent = 'Sale Processing...';
            
            // Re-enable after 10 seconds in case there was an error
            setTimeout(() => {
                submitButton.disabled = false;
                submitButton.textContent = originalButtonText;
            }, 10000);
        }
        
        saleForm.addEventListener('submit', function(e) {
            // If the form has already been submitted, prevent another submission
            if (formSubmitted || wasRecentlySubmitted()) {
                console.log('Preventing duplicate sale submission');
                e.preventDefault();
                
                if (submitButton) {
                    submitButton.disabled = true;
                    submitButton.textContent = 'Sale Processing...';
                }
                
                // Show message to user
                const formAlert = document.createElement('div');
                formAlert.className = 'alert alert-warning mt-3';
                formAlert.innerHTML = 'Your sale is already being processed. Please wait...';
                
                // Insert alert after the button
                submitButton.parentNode.appendChild(formAlert);
                
                return false;
            }
            
            // Set the flag to indicate form has been submitted
            formSubmitted = true;
            preventDuplicateSale();
            
            // Disable the submit button to provide visual feedback
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.textContent = 'Processing...';
            }
            
            // Allow the form to submit
            return true;
        });
    }
}); 