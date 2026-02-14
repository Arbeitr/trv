/**
 * UI Module - Station search, connection management, sidebar controls
 */

const UIModule = (function() {
    // Application state
    const state = {
        stations: {},  // {station_id: {name, lat, lon}}
        connections: [],  // [{id, from, to, train_type, geometry, ...}]
        stationIdCounter: 0,
        connectionIdCounter: 0
    };
    
    // Initialize UI
    function init() {
        setupStationSearch();
        setupConnectionControls();
        updateStationSelects();
    }
    
    // Setup station search with autocomplete
    function setupStationSearch() {
        const searchInput = document.getElementById('station-search');
        const resultsDiv = document.getElementById('station-results');
        
        let searchTimeout;
        
        searchInput.addEventListener('input', function() {
            const query = this.value.trim();
            
            clearTimeout(searchTimeout);
            
            if (query.length < 2) {
                resultsDiv.classList.remove('show');
                return;
            }
            
            searchTimeout = setTimeout(() => {
                searchStations(query);
            }, 300);
        });
        
        // Close results when clicking outside
        document.addEventListener('click', function(e) {
            if (!searchInput.contains(e.target) && !resultsDiv.contains(e.target)) {
                resultsDiv.classList.remove('show');
            }
        });
    }
    
    // Search stations via API
    async function searchStations(query) {
        const resultsDiv = document.getElementById('station-results');
        
        try {
            const response = await fetch('/api/stations/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query, limit: 10 })
            });
            
            const data = await response.json();
            displaySearchResults(data.results);
            
        } catch (error) {
            console.error('Search error:', error);
        }
    }
    
    // Display search results
    function displaySearchResults(results) {
        const resultsDiv = document.getElementById('station-results');
        resultsDiv.innerHTML = '';
        
        if (results.length === 0) {
            resultsDiv.innerHTML = '<div class="autocomplete-item">No stations found</div>';
            resultsDiv.classList.add('show');
            return;
        }
        
        results.forEach(station => {
            const item = document.createElement('div');
            item.className = 'autocomplete-item';
            item.textContent = `${station.name} (${station.type})`;
            // Use mousedown instead of click to fire before the document click handler
            item.addEventListener('mousedown', (e) => {
                e.preventDefault(); // Prevent blur/focus issues
                addStation(station);
            });
            resultsDiv.appendChild(item);
        });
        
        resultsDiv.classList.add('show');
    }
    
    // Add station to project
    function addStation(stationData) {
        const stationId = `sta_${state.stationIdCounter++}`;
        
        state.stations[stationId] = {
            name: stationData.name,
            lat: stationData.lat,
            lon: stationData.lon
        };
        
        // Add to map
        MapModule.addStationMarker(stationId, state.stations[stationId]);
        
        // Update UI
        updateStationList();
        updateStationSelects();
        MapModule.fitBounds();
        
        // Clear search
        document.getElementById('station-search').value = '';
        document.getElementById('station-results').classList.remove('show');
    }
    
    // Remove station from project
    function removeStation(stationId) {
        // Remove station
        delete state.stations[stationId];
        MapModule.removeStationMarker(stationId);
        
        // Remove connections involving this station
        state.connections = state.connections.filter(conn => {
            if (conn.from === stationId || conn.to === stationId) {
                MapModule.removeRoute(conn.id);
                return false;
            }
            return true;
        });
        
        // Update UI
        updateStationList();
        updateConnectionList();
        updateStationSelects();
    }
    
    // Update station list display
    function updateStationList() {
        const ul = document.getElementById('stations-ul');
        ul.innerHTML = '';
        
        Object.entries(state.stations).forEach(([id, station]) => {
            const li = document.createElement('li');
            li.className = 'station-item';
            li.innerHTML = `
                <span>${station.name}</span>
                <button onclick="UIModule.removeStation('${id}')">🗑️</button>
            `;
            ul.appendChild(li);
        });
    }
    
    // Update station select dropdowns
    function updateStationSelects() {
        const fromSelect = document.getElementById('from-station');
        const toSelect = document.getElementById('to-station');
        
        fromSelect.innerHTML = '<option value="">Select from...</option>';
        toSelect.innerHTML = '<option value="">Select to...</option>';
        
        Object.entries(state.stations).forEach(([id, station]) => {
            const option1 = document.createElement('option');
            option1.value = id;
            option1.textContent = station.name;
            fromSelect.appendChild(option1);
            
            const option2 = document.createElement('option');
            option2.value = id;
            option2.textContent = station.name;
            toSelect.appendChild(option2);
        });
    }
    
    // Setup connection controls
    function setupConnectionControls() {
        document.getElementById('btn-add-connection').addEventListener('click', addConnection);
    }
    
    // Add connection
    async function addConnection() {
        const fromId = document.getElementById('from-station').value;
        const toId = document.getElementById('to-station').value;
        const trainType = document.getElementById('train-type').value;
        
        if (!fromId || !toId) {
            alert('Please select both stations');
            return;
        }
        
        if (fromId === toId) {
            alert('Cannot connect a station to itself');
            return;
        }
        
        // Show loading
        document.getElementById('loading').style.display = 'flex';
        
        try {
            // Request route from backend
            const response = await fetch('/api/route', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    from: state.stations[fromId],
                    to: state.stations[toId],
                    train_type: trainType
                })
            });
            
            const routeData = await response.json();
            
            // Create connection
            const connectionId = `conn_${state.connectionIdCounter++}`;
            const connection = {
                id: connectionId,
                from: fromId,
                to: toId,
                train_type: trainType,
                ...routeData
            };
            
            state.connections.push(connection);
            
            // Add to map
            MapModule.addRoute(connectionId, connection);
            
            // Update UI
            updateConnectionList();
            
        } catch (error) {
            console.error('Error adding connection:', error);
            alert('Failed to calculate route. Please try again.');
        } finally {
            document.getElementById('loading').style.display = 'none';
        }
    }
    
    // Remove connection
    function removeConnection(connectionId) {
        state.connections = state.connections.filter(conn => conn.id !== connectionId);
        MapModule.removeRoute(connectionId);
        updateConnectionList();
    }
    
    // Update connection list display
    function updateConnectionList() {
        const ul = document.getElementById('connections-ul');
        ul.innerHTML = '';
        
        state.connections.forEach(conn => {
            const fromName = state.stations[conn.from].name;
            const toName = state.stations[conn.to].name;
            const travelTime = Utils.formatTravelTime(conn.travel_time_minutes);
            
            const li = document.createElement('li');
            li.className = 'connection-item';
            li.innerHTML = `
                <span>
                    <strong class="train-${conn.train_type}">${conn.train_type}</strong>
                    ${fromName} → ${toName}<br>
                    <small>${conn.distance_km.toFixed(1)} km • ${travelTime}</small>
                </span>
                <button onclick="UIModule.removeConnection('${conn.id}')">🗑️</button>
            `;
            ul.appendChild(li);
        });
    }
    
    // Get current project state
    function getProjectState() {
        return {
            version: '3.0',
            metadata: {
                name: 'Train Route Project',
                created: new Date().toISOString(),
                modified: new Date().toISOString(),
                region: 'germany'
            },
            stations: state.stations,
            connections: state.connections
        };
    }
    
    // Load project state
    function loadProjectState(projectData) {
        // Clear current state
        MapModule.clearAll();
        state.stations = {};
        state.connections = [];
        state.stationIdCounter = 0;
        state.connectionIdCounter = 0;
        
        // Load stations
        state.stations = projectData.stations || {};
        Object.entries(state.stations).forEach(([id, station]) => {
            MapModule.addStationMarker(id, station);
        });
        
        // Load connections
        state.connections = projectData.connections || [];
        state.connections.forEach(conn => {
            MapModule.addRoute(conn.id, conn);
        });
        
        // Update UI
        updateStationList();
        updateConnectionList();
        updateStationSelects();
        MapModule.fitBounds();
    }
    
    // Public API
    return {
        init,
        removeStation,
        removeConnection,
        getProjectState,
        loadProjectState
    };
})();

// Initialize UI on load
document.addEventListener('DOMContentLoaded', function() {
    UIModule.init();
});
