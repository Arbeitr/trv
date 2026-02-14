/**
 * Map Module - Leaflet map initialization and rendering
 */

const MapModule = (function() {
    let map = null;
    let routeLayers = {};
    let stationMarkers = {};
    
    // Initialize Leaflet map with Canvas renderer
    function init() {
        // Use Canvas renderer for better performance with many points
        const canvas = L.canvas();
        
        map = L.map('map', {
            center: [51.1657, 10.4515],  // Center on Germany
            zoom: 6,
            preferCanvas: true,
            renderer: canvas
        });
        
        // Add OpenStreetMap tiles
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
        }).addTo(map);
        
        return map;
    }
    
    // Add a station marker to the map
    function addStationMarker(stationId, stationData) {
        if (stationMarkers[stationId]) {
            return; // Already exists
        }
        
        const marker = L.circleMarker([stationData.lat, stationData.lon], {
            radius: 8,
            fillColor: '#FFFFFF',
            color: '#000000',
            weight: 2,
            opacity: 1,
            fillOpacity: 1
        }).addTo(map);
        
        marker.bindPopup(`<strong>${stationData.name}</strong>`);
        stationMarkers[stationId] = marker;
    }
    
    // Remove a station marker from the map
    function removeStationMarker(stationId) {
        if (stationMarkers[stationId]) {
            map.removeLayer(stationMarkers[stationId]);
            delete stationMarkers[stationId];
        }
    }
    
    // Add a connection route to the map
    function addRoute(connectionId, connectionData) {
        if (routeLayers[connectionId]) {
            return; // Already exists
        }
        
        const geometry = connectionData.geometry_simplified || connectionData.geometry;
        if (!geometry || geometry.length < 2) {
            return;
        }
        
        // Convert to Leaflet LatLng format
        const latlngs = geometry.map(coord => [coord[1], coord[0]]);
        
        // Determine line style based on route quality
        const quality = connectionData.route_quality || 'rail';
        let dashArray = null;
        
        if (quality === 'straight_line') {
            dashArray = '2, 8'; // Dotted
        } else if (quality === 'rail_approx') {
            dashArray = '10, 5'; // Dashed
        }
        
        // Get color from train type
        const trainType = connectionData.train_type || 'RE';
        const colors = {
            'ICE': '#EC0016',
            'IC': '#FF6600',
            'RE': '#1455C0',
            'RB': '#408335'
        };
        const color = colors[trainType] || colors['RE'];
        
        // Create polyline
        const polyline = L.polyline(latlngs, {
            color: color,
            weight: 3,
            opacity: 0.9,
            dashArray: dashArray
        }).addTo(map);
        
        // Add popup with connection info
        const travelTime = Utils.formatTravelTime(connectionData.travel_time_minutes);
        const distanceKm = connectionData.distance_km.toFixed(1);
        
        polyline.bindPopup(`
            <strong>${trainType}</strong><br>
            ${distanceKm} km<br>
            ${travelTime}
        `);
        
        routeLayers[connectionId] = polyline;
    }
    
    // Remove a connection route from the map
    function removeRoute(connectionId) {
        if (routeLayers[connectionId]) {
            map.removeLayer(routeLayers[connectionId]);
            delete routeLayers[connectionId];
        }
    }
    
    // Clear all routes and markers
    function clearAll() {
        Object.keys(routeLayers).forEach(id => removeRoute(id));
        Object.keys(stationMarkers).forEach(id => removeStationMarker(id));
    }
    
    // Fit map bounds to show all stations
    function fitBounds() {
        const markerCoords = Object.values(stationMarkers).map(marker => marker.getLatLng());
        if (markerCoords.length > 0) {
            const bounds = L.latLngBounds(markerCoords);
            map.fitBounds(bounds, { padding: [50, 50] });
        }
    }
    
    // Public API
    return {
        init,
        addStationMarker,
        removeStationMarker,
        addRoute,
        removeRoute,
        clearAll,
        fitBounds
    };
})();

// Initialize map on load
document.addEventListener('DOMContentLoaded', function() {
    MapModule.init();
});
