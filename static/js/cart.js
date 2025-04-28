function scanBarcode() {
    const barcode = document.getElementById('barcodeInput').value;
    if (!barcode) {
        document.getElementById('barcodeError').textContent = 'Please enter a barcode';
        return;
    }

    fetch('/add_to_cart_barcode', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ barcode: barcode })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById('barcodeInput').value = '';
            document.getElementById('barcodeError').textContent = '';
            window.location.reload();
        } else {
            document.getElementById('barcodeError').textContent = data.error;
        }
    })
    .catch(error => {
        document.getElementById('barcodeError').textContent = 'Error adding product to cart';
    });
}

// Add event listener for Enter key in barcode input
document.getElementById('barcodeInput').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        scanBarcode();
    }
});

function updateQuantity(itemId, change, newValue = null) {
    const input = document.querySelector(`input[data-item-id="${itemId}"]`);
    if (!input) {
        console.error(`Input element for item ${itemId} not found`);
        return;
    }
    const quantity = newValue !== null ? newValue : (parseInt(input.value) + change);
    
    fetch(`/update_cart/${itemId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ quantity: quantity })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            window.location.reload();
        } else {
            alert(data.error);
        }
    })
    .catch(error => {
        alert('Error updating cart');
    });
}

function removeItem(itemId) {
    if (confirm('Are you sure you want to remove this item?')) {
        fetch(`/update_cart/${itemId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ quantity: 0 })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                window.location.reload();
            } else {
                alert(data.error);
            }
        })
        .catch(error => {
            alert('Error removing item');
        });
    }
} 