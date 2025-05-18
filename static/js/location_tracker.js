// Function to get location name from coordinates using reverse geocoding
async function getLocationName(latitude, longitude) {
    try {
        const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${latitude}&lon=${longitude}`);
        const data = await response.json();
        return data.display_name || 'Unknown location';
    } catch (error) {
        console.error('Error getting location name:', error);
        return 'Unknown location';
    }
}

// Function to update user's location
async function updateLocation(position) {
    try {
        const latitude = position.coords.latitude;
        const longitude = position.coords.longitude;
        const locationName = await getLocationName(latitude, longitude);

        const response = await fetch('/api/update_location', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                latitude,
                longitude,
                location_name: locationName
            })
        });

        if (!response.ok) {
            throw new Error('Failed to update location');
        }
    } catch (error) {
        console.error('Error updating location:', error);
    }
}

// Function to start location tracking
function startLocationTracking() {
    if ("geolocation" in navigator) {
        // Update location immediately
        navigator.geolocation.getCurrentPosition(updateLocation);
        
        // Then update every 5 minutes
        setInterval(() => {
            navigator.geolocation.getCurrentPosition(updateLocation);
        }, 5 * 60 * 1000);
    } else {
        console.error('Geolocation is not supported by this browser');
    }
}

// Start tracking when the script loads
document.addEventListener('DOMContentLoaded', startLocationTracking); 