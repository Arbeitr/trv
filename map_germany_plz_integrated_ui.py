import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog  # Import filedialog for Open File Dialog
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backends.backend_pdf import PdfPages
import os
import json
import math
import logging
from shapely.geometry import LineString, Point
from geopandas import GeoSeries
import pgeocode
from math import radians, sin, cos, sqrt, atan2

# --- Constants ---
SHAPEFILE_PATH = "ne_10m_admin_1_states_provinces.shp"
DEFAULT_CITIES = {
    "Frankfurt": (8.6821, 50.1109), "Mannheim": (8.4660, 49.4875),
    "München": (11.5820, 48.1351), "Erfurt": (11.0299, 50.9848),
    "Leipzig": (12.3731, 51.3397), "Potsdam": (13.0635, 52.3989),
    "Berlin": (13.4050, 52.5200), "Magdeburg": (11.6276, 52.1205),
    "Hannover": (9.7320, 52.3759), "Bremen": (8.8017, 53.0793),
    "Hamburg": (9.9937, 53.5511), "Schwerin": (11.4074, 53.6294),
    "Stralsund": (13.0810, 54.3091), "Köln": (6.9603, 50.9375),
    "Saarbrücken": (6.9969, 49.2402), "Mainz": (8.2473, 49.9982)
}
DEFAULT_CONNECTIONS = [
    ("Frankfurt", "Mannheim"), ("Mannheim", "München"), ("München", "Erfurt"),
    ("Erfurt", "Leipzig"), ("Leipzig", "Potsdam"), ("Potsdam", "Berlin"),
    ("Berlin", "Magdeburg"), ("Magdeburg", "Hannover"), ("Hannover", "Bremen"),
    ("Bremen", "Hamburg"), ("Hamburg", "Schwerin"), ("Schwerin", "Stralsund"),
    ("Stralsund", "Köln"), ("Köln", "Saarbrücken"), ("Saarbrücken", "Mainz")
]
CONNECTION_COLORS = [
    "#FFD800", "#F39200", "#A9455D", "#E93E8F", "#814997", "#1455C0",
    "#309FD1", "#00A099", "#408335", "#63A615", "#858379", "#646973"
]
DEFAULT_TRAVEL_TIMES = {
    ("Frankfurt", "Mannheim"): 30, ("Mannheim", "München"): 150,
    ("München", "Erfurt"): 180, ("Erfurt", "Leipzig"): 60,
    ("Leipzig", "Potsdam"): 90, ("Potsdam", "Berlin"): 30,
    ("Berlin", "Magdeburg"): 105, ("Magdeburg", "Hannover"): 90,
    ("Hannover", "Bremen"): 75, ("Bremen", "Hamburg"): 60,
    ("Hamburg", "Schwerin"): 90, ("Schwerin", "Stralsund"): 120,
    ("Stralsund", "Köln"): 360, ("Köln", "Saarbrücken"): 180,
    ("Saarbrücken", "Mainz"): 90
}

# Train route types (high-speed, regional, local)
TRAIN_TYPES = {
    "ICE": {"name": "ICE", "speed_factor": 1.5, "color": "#FF0000"},  # High-speed trains
    "IC": {"name": "IC", "speed_factor": 1.2, "color": "#FF6600"},     # Inter-city trains
    "RE": {"name": "RE", "speed_factor": 0.9, "color": "#009900"},     # Regional express
    "RB": {"name": "RB", "speed_factor": 0.7, "color": "#3333FF"},     # Regional train
    "S": {"name": "S", "speed_factor": 0.6, "color": "#33CCFF"}        # S-Bahn (suburban train)
}

# Define which connections use which train type
TRAIN_ROUTES_TYPE = {
    ("Frankfurt", "Mannheim"): "ICE",
    ("Mannheim", "München"): "ICE",
    ("München", "Erfurt"): "ICE",
    ("Erfurt", "Leipzig"): "ICE",
    ("Leipzig", "Potsdam"): "RE",
    ("Potsdam", "Berlin"): "RE",
    ("Berlin", "Magdeburg"): "IC",
    ("Magdeburg", "Hannover"): "IC",
    ("Hannover", "Bremen"): "IC",
    ("Bremen", "Hamburg"): "ICE",
    ("Hamburg", "Schwerin"): "RE",
    ("Schwerin", "Stralsund"): "RB",
    ("Stralsund", "Köln"): "IC",
    ("Köln", "Saarbrücken"): "RE",
    ("Saarbrücken", "Mainz"): "RE"
}

# Default train type for connections not explicitly defined
DEFAULT_TRAIN_TYPE = "RE"

# Add these constants at the top of the file with other constants
ROUTE_COMPLEXITY_FACTOR = 1.2  # Average route is ~20% longer than straight-line distance
STATION_STOP_MINUTES = {
    "ICE": 2,   # High-speed trains have shorter stops
    "IC": 3,    # Inter-city trains have medium stops
    "RE": 3,    # Regional express trains have medium stops
    "RB": 4,    # Regional trains have longer stops
    "S": 2      # S-Bahn trains have short stops for frequent service
}
TYPICAL_STATIONS_PER_100KM = {
    "ICE": 0.5,  # High-speed trains have fewer stops
    "IC": 1,     # Inter-city trains have more stops
    "RE": 2,     # Regional express trains have even more stops
    "RB": 3,     # Regional trains have the most stops
    "S": 4       # S-Bahn has very frequent stops (typically every few km)
}
GEOGRAPHIC_FACTORS = {
    # Regions with hills/mountains have slower average speeds
    "FLAT": 1.0,      # No adjustment for flat terrain
    "HILLS": 1.15,    # 15% slower in hilly areas
    "MOUNTAINS": 1.3, # 30% slower in mountainous areas
    "URBAN": 1.2      # 20% slower in dense urban areas
}

# Route evaluation factors - how curved/indirect is the route between cities
# These factors adjust the direct Haversine distance to account for actual rail paths
ROUTE_CURVATURE_FACTORS = {
    "ICE": 1.1,  # High-speed routes are generally straighter
    "IC": 1.15,  # Inter-city routes are relatively direct
    "RE": 1.25,  # Regional express routes often have more curves
    "RB": 1.35,  # Regional train routes tend to be the most indirect
    "S": 1.4     # S-Bahn routes often follow complex urban/suburban paths
}

# Average elevation gradients for German regions (approximate)
REGION_TOPOGRAPHY = {
    "Bayern": "MOUNTAINS",
    "Baden-Württemberg": "HILLS",
    "Hessen": "HILLS",
    "Thüringen": "HILLS",
    "Sachsen": "HILLS",
    "Rheinland-Pfalz": "HILLS",
    "Saarland": "HILLS",
    "Nordrhein-Westfalen": "FLAT",
    "Niedersachsen": "FLAT",
    "Bremen": "FLAT",
    "Hamburg": "FLAT",
    "Schleswig-Holstein": "FLAT",
    "Mecklenburg-Vorpommern": "FLAT",
    "Brandenburg": "FLAT",
    "Berlin": "URBAN",
    "Sachsen-Anhalt": "FLAT"
}

AVERAGE_TRAIN_SPEED_KMH = 100
EARTH_RADIUS_KM = 6371
DEFAULT_X_LIM = (5, 15)
DEFAULT_Y_LIM = (47, 55)
CRS_EPSG_4326 = "EPSG:4326"

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger('matplotlib').setLevel(logging.WARNING)  # Reduce matplotlib noise

class RouteData:
    """Class for managing cities, connections, and travel times data"""
    
    def __init__(self):
        self.cities = DEFAULT_CITIES.copy()
        self.connections = DEFAULT_CONNECTIONS.copy()
        self.travel_times_data = DEFAULT_TRAVEL_TIMES.copy()
        self.city_ids = {city: f"city_{i}" for i, city in enumerate(self.cities.keys())}
        self.connection_train_types = TRAIN_ROUTES_TYPE.copy()
        
        # Add geodata access for improved calculations
        try:
            import geopy.geocoders
            from geopy.extra.rate_limiter import RateLimiter
            self.geolocator = geopy.geocoders.Nominatim(user_agent="train_route_visualizer")
            self.geocode = RateLimiter(self.geolocator.geocode, min_delay_seconds=1)
            self.has_geopy = True
            logging.info("Geopy available - using enhanced geographic data for calculations")
        except ImportError:
            self.has_geopy = False
            logging.info("Geopy not available - install it with 'pip install geopy' for more accurate terrain data. Using approximations for now.")
    
    def add_city(self, postal_code):
        """Add a city based on postal code"""
        try:
            nomi = pgeocode.Nominatim('de')
            info = nomi.query_postal_code(postal_code)
            if math.isnan(info.latitude) or math.isnan(info.longitude):
                return False, "Postal code not found. Please enter a valid Postleitzahl."
            
            city_name = info.place_name if info.place_name else postal_code
            self.cities[city_name] = (info.longitude, info.latitude)
            self.city_ids[city_name] = f"city_{len(self.city_ids)}"
            return True, f"City '{city_name}' added successfully!"
        except Exception as e:
            return False, f"Error retrieving location data: {str(e)}"
    
    def add_connection(self, city1, city2, train_type=DEFAULT_TRAIN_TYPE):
        """Add a connection between two cities with specified train type"""
        if city1 == city2:
            return False, "A city cannot be connected to itself."
        
        if (city1, city2) in self.connections or (city2, city1) in self.connections:
            return False, "This connection already exists."
        
        self.connections.append((city1, city2))
        self.connection_train_types[(city1, city2)] = train_type
        return True, f"Connection added between {city1} and {city2} ({train_type})!"
    
    def remove_city(self, city_name):
        """Remove a city and handle its connections"""
        if city_name not in self.cities:
            return False, f"City {city_name} does not exist."
        
        del self.cities[city_name]
        
        # Find directly connected cities and create new connections between them
        directly_connected = [conn for conn in self.connections if city_name in conn]
        new_connections = []
        
        for conn1 in directly_connected:
            for conn2 in directly_connected:
                if conn1 != conn2:
                    city_a = conn1[0] if conn1[1] == city_name else conn1[1]
                    city_b = conn2[0] if conn2[1] == city_name else conn2[1]
                    if (city_a, city_b) not in self.connections and (city_b, city_a) not in self.connections:
                        new_connections.append((city_a, city_b))
        
        # Remove connections with the deleted city and add new ones
        self.connections = [conn for conn in self.connections if city_name not in conn]
        self.connections.extend(new_connections)
        
        # Also remove train type info for removed connections
        for conn in list(self.connection_train_types.keys()):
            if city_name in conn:
                del self.connection_train_types[conn]
        
        return True, f"City {city_name} and its connections removed successfully!"
    
    def remove_connection(self, city1, city2):
        """Remove a connection between cities"""
        if (city1, city2) in self.connections:
            self.connections.remove((city1, city2))
            if (city1, city2) in self.connection_train_types:
                del self.connection_train_types[(city1, city2)]
            return True
        elif (city2, city1) in self.connections:
            self.connections.remove((city2, city1))
            if (city2, city1) in self.connection_train_types:
                del self.connection_train_types[(city2, city1)]
            return True
        return False
    
    def get_train_type(self, city1, city2):
        """Get the train type for a connection"""
        if (city1, city2) in self.connection_train_types:
            return self.connection_train_types[(city1, city2)]
        elif (city2, city1) in self.connection_train_types:
            return self.connection_train_types[(city2, city1)]
        return DEFAULT_TRAIN_TYPE
    
    def update_travel_time(self, city1, city2, minutes):
        """Update or set a custom travel time between two cities in minutes"""
        if (city1, city2) in self.connections:
            self.travel_times_data[(city1, city2)] = minutes
            return True
        elif (city2, city1) in self.connections:
            self.travel_times_data[(city2, city1)] = minutes
            return True
        return False
    
    def has_custom_travel_time(self, city1, city2):
        """Check if a custom travel time is set for this connection"""
        return (city1, city2) in self.travel_times_data or (city2, city1) in self.travel_times_data
    
    def get_travel_time(self, city1, city2):
        """Get travel time between two cities considering train type"""
        logging.debug(f"Calculating travel time for {city1} -> {city2}")
        if (city1, city2) in self.travel_times_data:
            # Use custom travel time directly if available (no train type adjustment)
            travel_time = self.travel_times_data[(city1, city2)]
            # Format travel time
            hours = travel_time // 60
            minutes = travel_time % 60
            return f"{hours}h {minutes}m" if hours > 0 else f"{minutes} min"
        elif (city2, city1) in self.travel_times_data:
            # Use custom travel time directly if available (no train type adjustment)
            travel_time = self.travel_times_data[(city2, city1)]
            # Format travel time
            hours = travel_time // 60
            minutes = travel_time % 60
            return f"{hours}h {minutes}m" if hours > 0 else f"{minutes} min"
        elif city1 in self.cities and city2 in self.cities:
            # Calculate travel time for user-added cities, considering train type
            return self.estimate_travel_time(self.cities[city1], self.cities[city2], 
                                            self.get_train_type(city1, city2))
        else:
            return "N/A"
        # The following code will no longer be reached for custom times
        train_type = self.get_train_type(city1, city2)
        adjusted_time = round(travel_time / TRAIN_TYPES[train_type]["speed_factor"])
        logging.debug(f"Predefined travel time: {travel_time} minutes")
        logging.debug(f"Train type: {train_type}, Speed factor: {TRAIN_TYPES[train_type]['speed_factor']}")
        logging.debug(f"Adjusted travel time: {adjusted_time} minutes")
        # Format travel time
        hours = adjusted_time // 60
        minutes = adjusted_time % 60
        return f"{hours}h {minutes}m" if hours > 0 else f"{minutes} min"
    
    def get_raw_travel_time(self, city1, city2):
        """Get the raw travel time in minutes without formatting"""
        if (city1, city2) in self.travel_times_data:
            return self.travel_times_data[(city1, city2)]
        elif (city2, city1) in self.travel_times_data:
            return self.travel_times_data[(city2, city1)]
        return None
    
    def estimate_travel_time(self, coord1, coord2, train_type=DEFAULT_TRAIN_TYPE):
        """Estimate travel time based on multiple realistic factors"""
        # Get base straight-line distance using the appropriate method
        if self.has_geopy:
            try:
                # Use geopy for more accurate distance calculation that considers Earth's curvature
                from geopy.distance import geodesic
                base_distance_km = geodesic(
                    (coord1[1], coord1[0]),  # Geopy expects (lat, lon) format
                    (coord2[1], coord2[0])
                ).kilometers
                logging.debug(f"Using geopy distance: {base_distance_km:.2f} km")
            except Exception as e:
                logging.warning(f"Geopy distance calculation failed: {e}. Falling back to haversine.")
                base_distance_km = self.haversine_distance(coord1, coord2)
        else:
            # Fall back to haversine if geopy is not available
            base_distance_km = self.haversine_distance(coord1, coord2)
        
        # Apply route complexity factor based on train type (different types use different route networks)
        route_curvature = ROUTE_CURVATURE_FACTORS.get(train_type, ROUTE_COMPLEXITY_FACTOR)
        adjusted_distance = base_distance_km * route_curvature
        
        # 2. Account for geographic features
        terrain_factor = self.get_terrain_factor(coord1, coord2)
        
        # 3. Apply speed factor based on train type
        speed_factor = TRAIN_TYPES[train_type]["speed_factor"]
        adjusted_speed = AVERAGE_TRAIN_SPEED_KMH * speed_factor / terrain_factor
        
        # 4. Calculate base travel time
        travel_time_hours = adjusted_distance / adjusted_speed
        travel_time_minutes = travel_time_hours * 60
        
        # 5. Add time for station stops
        station_stops = self.estimate_station_stops(base_distance_km, train_type)
        stop_time_minutes = station_stops * STATION_STOP_MINUTES[train_type]
        
        # Total adjusted travel time
        total_minutes = int(travel_time_minutes + stop_time_minutes)
        
        # Log detailed calculation for debugging
        logging.debug(f"Enhanced travel time calculation for {coord1} -> {coord2}:")
        logging.debug(f"  Base distance (km): {base_distance_km:.2f}")
        logging.debug(f"  Route complexity adjustment: {ROUTE_COMPLEXITY_FACTOR}")
        logging.debug(f"  Terrain factor: {terrain_factor}")
        logging.debug(f"  Adjusted distance (km): {adjusted_distance:.2f}")
        logging.debug(f"  Train speed factor: {speed_factor}")
        logging.debug(f"  Adjusted speed (km/h): {adjusted_speed:.2f}")
        logging.debug(f"  Base travel time (min): {travel_time_minutes:.2f}")
        logging.debug(f"  Estimated station stops: {station_stops}")
        logging.debug(f"  Stop time (min): {stop_time_minutes}")
        logging.debug(f"  Total travel time (min): {total_minutes}")
        
        # Format travel time
        hours = total_minutes // 60
        minutes = total_minutes % 60
        return f"{hours}h {minutes}m" if hours > 0 else f"{minutes} min"
    
    def get_terrain_factor(self, coord1, coord2):
        """Determine the terrain factor between two coordinates"""
        # Try to get the regions for both coordinates
        region1 = self.get_region_from_coordinates(coord1)
        region2 = self.get_region_from_coordinates(coord2)
        
        # If we can identify both regions, use the more challenging terrain
        if region1 in REGION_TOPOGRAPHY and region2 in REGION_TOPOGRAPHY:
            terrain_type1 = REGION_TOPOGRAPHY[region1]
            terrain_type2 = REGION_TOPOGRAPHY[region2]
            # Use the more challenging terrain between the two points
            terrain_types = [terrain_type1, terrain_type2]
            if "MOUNTAINS" in terrain_types:
                return GEOGRAPHIC_FACTORS["MOUNTAINS"]
            elif "HILLS" in terrain_types:
                return GEOGRAPHIC_FACTORS["HILLS"]
            elif "URBAN" in terrain_types:
                return GEOGRAPHIC_FACTORS["URBAN"]
            else:
                return GEOGRAPHIC_FACTORS["FLAT"]
        
        # If we can't determine regions, use a default factor
        return 1.15  # Assume slightly complex terrain as default
    
    def get_region_from_coordinates(self, coords):
        """Get the German state/region from coordinates"""
        if self.has_geopy:
            try:
                # Reverse geocode to get location information
                location = self.geolocator.reverse(f"{coords[1]}, {coords[0]}", language="de", timeout=5)
                if location and location.raw.get('address'):
                    address = location.raw['address']
                    # Try to get state information
                    state = address.get('state')
                    if state:
                        return state
            except Exception as e:
                logging.error(f"Error in reverse geocoding: {e}")
                # Fall through to approximation
        
        # More complete approximation of German states based on coordinates
        lat, lon = coords[1], coords[0]
        
        # More precise mapping of coordinates to German states
        if 47.5 <= lat <= 49.8 and 8.9 <= lon <= 13.8:
            return "Bayern"
        elif 47.5 <= lat <= 49.8 and 7.5 <= lon <= 9.8:
            return "Baden-Württemberg"
        elif 49.3 <= lat <= 51.5 and 7.7 <= lon <= 10.2:
            return "Hessen"
        elif 50.2 <= lat <= 51.6 and 9.9 <= lon <= 12.6:
            return "Thüringen"
        elif 50.1 <= lat <= 51.7 and 11.8 <= lon <= 15.0:
            return "Sachsen"
        elif 48.9 <= lat <= 50.9 and 6.1 <= lon <= 8.5:
            return "Rheinland-Pfalz"
        elif 49.1 <= lat <= 49.6 and 6.3 <= lon <= 7.4:
            return "Saarland"
        elif 50.3 <= lat <= 52.5 and 5.8 <= lon <= 9.5:
            return "Nordrhein-Westfalen"
        elif 51.2 <= lat <= 54.0 and 6.5 <= lon <= 11.6:
            return "Niedersachsen"
        elif 53.0 <= lat <= 53.6 and 8.4 <= lon <= 9.0:
            return "Bremen"
        elif 53.4 <= lat <= 53.7 and 9.6 <= lon <= 10.3:
            return "Hamburg"
        elif 53.3 <= lat <= 55.1 and 8.4 <= lon <= 11.3:
            return "Schleswig-Holstein"
        elif 53.0 <= lat <= 54.9 and 10.5 <= lon <= 14.5:
            return "Mecklenburg-Vorpommern"
        elif 51.3 <= lat <= 53.6 and 11.2 <= lon <= 14.8:
            return "Brandenburg"
        elif 52.3 <= lat <= 52.7 and 13.0 <= lon <= 13.8:
            return "Berlin"
        elif 50.8 <= lat <= 53.1 and 10.5 <= lon <= 13.2:
            return "Sachsen-Anhalt"
        
        # If coordinates don't match any of the defined regions, determine general terrain
        # North Germany is generally flat, South Germany has more hills and mountains
        if lat >= 52.0:
            return "FLAT_REGION"
        elif lat >= 50.0:
            return "HILLY_REGION"
        else:
            return "MOUNTAINOUS_REGION"
    
    def estimate_station_stops(self, distance_km, train_type):
        """Estimate the number of station stops based on distance and train type"""
        # Calculate approximate number of stops based on distance and train type
        estimated_stops = distance_km / 100 * TYPICAL_STATIONS_PER_100KM[train_type]
        # Round to nearest whole number but ensure at least 0
        return max(0, round(estimated_stops))
    
    def save_to_file(self, filepath):
        """Save cities, connections, and train types to a file"""
        try:
            with open(filepath, 'w') as file:
                json.dump({
                    "cities": self.cities, 
                    "connections": self.connections, 
                    "train_types": {str(k): v for k, v in self.connection_train_types.items()},
                    "travel_times": {str(k): v for k, v in self.travel_times_data.items()}
                }, file)
            return True, f"Routes saved successfully to {filepath}."
        except Exception as e:
            return False, f"Failed to save routes: {str(e)}"
    
    def load_from_file(self, filepath):
        """Load cities, connections, and train types from a file"""
        try:
            with open(filepath, 'r') as file:
                data = json.load(file)
                self.cities = data.get("cities", {})
                self.connections = data.get("connections", [])
                
                # Handle train types - convert string tuple keys back to actual tuples
                train_types_data = data.get("train_types", {})
                self.connection_train_types = {}
                for k, v in train_types_data.items():
                    # Convert string representation of tuple to actual tuple
                    # Format is typically: "('City1', 'City2')"
                    tuple_str = k.strip("()").replace("'", "").split(", ")
                    if len(tuple_str) == 2:
                        self.connection_train_types[(tuple_str[0], tuple_str[1])] = v
                
                # Handle travel times data - convert string tuple keys back to actual tuples
                travel_times_data = data.get("travel_times", {})
                self.travel_times_data = {}
                for k, v in travel_times_data.items():
                    tuple_str = k.strip("()").replace("'", "").split(", ")
                    if len(tuple_str) == 2:
                        self.travel_times_data[(tuple_str[0], tuple_str[1])] = v
                
                self.city_ids = {city: f"city_{i}" for i, city in enumerate(self.cities.keys())}
            return True, f"Routes loaded successfully from {filepath}."
        except Exception as e:
            return False, f"Failed to load routes: {str(e)}"
    
    def update_city_coordinates(self, city_name, lon, lat):
        """Update coordinates for an existing city"""
        if city_name in self.cities:
            self.cities[city_name] = (lon, lat)
            return True
        return False
    
    def remove_default_cities(self):
        """Remove all default cities and their connections"""
        default_city_names = list(DEFAULT_CITIES.keys())
        for city in default_city_names:
            if city in self.cities:
                del self.cities[city]
        
        # Remove connections involving default cities
        self.connections = [conn for conn in self.connections 
                           if conn[0] not in default_city_names and conn[1] not in default_city_names]
        
        # Remove train types for connections involving default cities
        for conn in list(self.connection_train_types.keys()):
            if conn[0] in default_city_names or conn[1] in default_city_names:
                del self.connection_train_types[conn]


class MapPlotter:
    """Class for handling map visualization"""
    
    def __init__(self, route_data):
        self.route_data = route_data
        self.fig, self.ax = plt.subplots(figsize=(10, 10))
        self.canvas = None
        self.germany_map = None
        self.filtered_states = None
        self.current_zoom_bounds = None
        self.state_ids = {}
        
    def initialize_map(self, germany_map):
        """Initialize the map with Germany data"""
        self.germany_map = germany_map
        self.state_ids = {state: f"state_{i}" for i, state in enumerate(germany_map['name'])}
        self.germany_map['state_id'] = self.germany_map['name'].map(self.state_ids)
        self.germany_map['bounding_box'] = self.germany_map.geometry.apply(lambda geom: geom.bounds)
    
    def set_canvas(self, master):
        """Set up the matplotlib canvas in the Tkinter window"""
        self.ax.set_facecolor('#F5F5F5')
        self.germany_map.boundary.plot(ax=self.ax, linewidth=0.8, color='#CCCCCC')
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=master)
        canvas_widget = self.canvas.get_tk_widget()
        canvas_widget.pack(fill=tk.BOTH, expand=True)
        
        # Initial plot
        self.update_plot()
        return canvas_widget
    
    def update_plot(self):
        """Update the map with current data"""
        self.ax.clear()
        self.ax.set_facecolor('#F5F5F5')
        self.germany_map.boundary.plot(ax=self.ax, linewidth=0.8, color='#CCCCCC')

        # Plot cities
        for city, coord in self.route_data.cities.items():
            self.ax.plot(coord[0], coord[1], marker='o', markersize=12,
                    markeredgecolor='black', markerfacecolor='white')

        # Plot connections with train type colors
        for i, (city1, city2) in enumerate(self.route_data.connections):
            if city1 in self.route_data.cities and city2 in self.route_data.cities:
                line = LineString([self.route_data.cities[city1], self.route_data.cities[city2]])
                
                # Get line color based on train type
                train_type = self.route_data.get_train_type(city1, city2)
                line_color = TRAIN_TYPES[train_type]["color"]
                
                # Draw the connection line with train-specific color and style
                self.ax.plot(*line.xy, color=line_color, linewidth=2.5, 
                           linestyle='-', alpha=0.9)

        # Handle congested areas and adjust labels
        clusters, clustered_cities = self.handle_congested_areas()
        self.adjust_city_labels(clusters)
        self.adjust_travel_time_labels()

        # Apply zoom if it exists
        if self.current_zoom_bounds is not None:
            self.ax.set_xlim(self.current_zoom_bounds[0], self.current_zoom_bounds[2])
            self.ax.set_ylim(self.current_zoom_bounds[1], self.current_zoom_bounds[3])
        else:
            self.ax.set_xlim(*DEFAULT_X_LIM)
            self.ax.set_ylim(*DEFAULT_Y_LIM)

        # Hide labels outside filtered states
        if self.filtered_states is not None:
            self.verify_labels_hidden()

        self.ax.axis('off')
        if self.canvas:
            self.canvas.draw()
    
    def zoom_into_states(self, state_list):
        """Zoom into specific German states"""
        logging.info(f"Zooming into states: {state_list}")
        
        # Filter the map
        self.filtered_states = self.germany_map[self.germany_map['name'].isin(state_list)]
        if self.filtered_states.empty:
            return False, "No matching states found. Please enter valid German state names."
        
        # Ensure CRS consistency
        self.filtered_states = self.filtered_states.to_crs(epsg=4326)
        
        # Set zoom bounds
        self.current_zoom_bounds = self.filtered_states.total_bounds
        
        # Update plot
        self.update_plot()
        return True, "Zoomed into selected states."
    
    def reset_zoom(self):
        """Reset zoom to show the entire map"""
        self.current_zoom_bounds = None
        self.filtered_states = None
        self.update_plot()
        
        # Make all labels visible
        for text in self.ax.texts:
            text.set_visible(True)
    
    def handle_congested_areas(self):
        """Group nearby cities into clusters to prevent label overlap"""
        cluster_radius = self.adjust_cluster_radius()
        clusters = []

        # Group cities into clusters based on proximity
        for city, (x, y) in self.route_data.cities.items():
            added_to_cluster = False
            for cluster in clusters:
                cluster_center = cluster['center']
                if abs(cluster_center[0] - x) < cluster_radius and abs(cluster_center[1] - y) < cluster_radius:
                    cluster['cities'].append(city)
                    cluster['coords'].append((x, y))
                    # Recalculate center
                    cluster['center'] = (
                        sum(coord[0] for coord in cluster['coords']) / len(cluster['coords']),
                        sum(coord[1] for coord in cluster['coords']) / len(cluster['coords'])
                    )
                    added_to_cluster = True
                    break

            if not added_to_cluster:
                clusters.append({
                    'cities': [city],
                    'coords': [(x, y)],
                    'center': (x, y)
                })

        # Draw cluster labels
        clustered_cities = set()
        for cluster in clusters:
            if len(cluster['cities']) > 1:
                # Multiple cities in cluster
                cluster_center = cluster['center']
                cluster_label = ", ".join(cluster['cities'])
                self.ax.text(cluster_center[0], cluster_center[1] + 0.2, cluster_label, 
                        fontsize=10, fontfamily='sans-serif', fontweight='bold', color='white',
                        bbox=dict(facecolor='red', edgecolor='none', boxstyle='round,pad=0.3'),
                        zorder=10)
                clustered_cities.update(cluster['cities'])

        return clusters, clustered_cities
    
    def adjust_cluster_radius(self):
        """Calculate cluster radius based on zoom level"""
        if self.current_zoom_bounds is None:
            return 1.0  # Default radius
            
        zoom_width = self.current_zoom_bounds[2] - self.current_zoom_bounds[0]
        zoom_height = self.current_zoom_bounds[3] - self.current_zoom_bounds[1]
        # Smaller zoom area means higher zoom level, so reduce the radius
        return max(0.1, min(1.0, (zoom_width + zoom_height) / 20))
    
    def adjust_city_labels(self, clusters):
        """Position city labels to avoid overlap"""
        for city, (x, y) in self.route_data.cities.items():
            # Skip cities that are part of a cluster
            if any(city in cluster['cities'] for cluster in clusters if len(cluster['cities']) > 1):
                continue

            # Check if there are other cities on the same vertical axis
            same_vertical_cities = [
                other_city for other_city, (other_x, other_y) 
                in self.route_data.cities.items() 
                if abs(other_x - x) < 0.01 and other_city != city
            ]

            if same_vertical_cities:
                # Place label to the right
                label_x = x + 0.2
                alignment = 'left'
            else:
                # Place label to the left
                label_x = x - 0.2
                alignment = 'right'

            # Draw the city label
            self.ax.text(label_x, y, city, fontsize=10, fontfamily='sans-serif',
                    fontweight='bold', color='white', ha=alignment,
                    bbox=dict(facecolor='darkgrey', edgecolor='none', boxstyle='round,pad=0.3'),
                    zorder=10, gid=self.route_data.city_ids.get(city, f"city_{len(self.route_data.city_ids)}"))
    
    def adjust_travel_time_labels(self):
        """Add travel time labels at the midpoint of connections"""
        existing_labels = set()
        
        for city1, city2 in self.route_data.connections:
            if city1 not in self.route_data.cities or city2 not in self.route_data.cities:
                continue

            travel_time = self.route_data.get_travel_time(city1, city2)
            train_type = self.route_data.get_train_type(city1, city2)
            label = f"{train_type}: {travel_time}"
            
            if label in existing_labels:
                continue  # Skip duplicate labels

            existing_labels.add(label)

            # Calculate midpoint
            x1, y1 = self.route_data.cities[city1]
            x2, y2 = self.route_data.cities[city2]
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2

            # Draw travel time label with train type
            self.ax.text(mid_x, mid_y, label, fontsize=8, fontfamily='sans-serif',
                    fontweight='bold', color='black', 
                    bbox=dict(facecolor='white', edgecolor=TRAIN_TYPES[train_type]["color"], 
                             boxstyle='round,pad=0.2', alpha=0.9),
                    zorder=11)

        # Remove the problematic code that's causing the crash
        # The below line had an unterminated string literal causing the syntax error
        # for text in self.ax.texts:
        #    if text.get_gid() in clustered_cities: this method anyway, as it's handled elsewhere
        #        text.set_visible(False)
    
    def verify_labels_hidden(self):
        """Hide labels for cities outside the filtered states"""
        if self.filtered_states is None:
            return
        for text in self.ax.texts:
            label_coords = (text.get_position()[0], text.get_position()[1])
            point = GeoSeries([gpd.points_from_xy([label_coords[0]], [label_coords[1]])[0]], crs=CRS_EPSG_4326)
            # Check if point is within any filtered state
            if not self.filtered_states.geometry.apply(lambda geom: point.iloc[0].within(geom)).any():
                text.set_visible(False)
            else:
                text.set_visible(True)
    
    def add_legend(self):
        """Add a legend to the current plot"""
        # Clear any existing legends
        for child in self.fig.get_children():
            if isinstance(child, plt.Axes) and child != self.ax:
                child.remove()
        
        # Create a new axes for the legend at the bottom of the plot
        # Use less space than before to avoid squishing
        legend_ax = self.fig.add_axes([0.1, 0.02, 0.8, 0.2])
        legend_ax.axis('off')
        
        # Draw the legend using the shared method
        self.draw_legend_on_axes(legend_ax)
    
    def draw_legend_on_axes(self, ax, full_page=False):
        """Draw legend on the given axes (reusable for both main plot and PDF export)"""
        # Group connections into chains
        chains = []
        visited = set()
        def dfs(city, chain):
            for conn in self.route_data.connections:
                if city in conn:
                    other_city = conn[1] if conn[0] == city else conn[0]
                    if other_city not in visited:
                        visited.add(other_city)
                        chain.append(conn)  # Store the original connection tuple
                        dfs(other_city, chain)
        
        for city in self.route_data.cities:
            if city not in visited:
                visited.add(city)
                chain = []
                dfs(city, chain)
                if chain:
                    chains.append(chain)
        
        if not chains:
            return
            
        # Adjust layout parameters based on whether this is a full page or not
        if full_page:
            columns = min(4, len(chains))  # Max 4 chains per row
            x_spacing = 0.9 / columns
            x_start = 0.05
            y_start_top = 0.9  # Start from top
            y_decrement = 0.04
        else:
            columns = min(3, len(chains)) 
            x_spacing = 0.7 / columns
            x_start = 0.1
            y_start_top = 0.3
            y_decrement = 0.05
        
        # Draw route chains in columns
        for chain_idx, chain in enumerate(chains):
            column = chain_idx % columns
            row = chain_idx // columns
            
            # Calculate position
            x_pos = x_start + (column * x_spacing)
            y_start = y_start_top - (row * y_decrement * len(chain))
            chain_y = y_start
            
            # Draw chain title
            ax.text(x_pos, chain_y + 0.02, f"Route {chain_idx + 1}", 
                    fontsize=12 if full_page else 10, fontweight='bold', 
                    transform=ax.transAxes, ha='left')
            chain_y -= y_decrement
            
            # Draw each segment in the chain
            for conn in chain:
                city1, city2 = conn
                # Create a unique route identifier
                route_id = (city1, city2) if (city1, city2) in self.route_data.connection_train_types else (city2, city1)
                
                # Retrieve the correct train type using the route identifier
                train_type = self.route_data.connection_train_types.get(route_id, DEFAULT_TRAIN_TYPE)
                line_color = TRAIN_TYPES[train_type]["color"]
                
                # Draw connecting line with train type color
                ax.plot([x_pos, x_pos], 
                        [chain_y, chain_y - y_decrement],  # Adjusted to start at the current city and end one city lower
                        color=line_color, linewidth=3 if full_page else 2, 
                        linestyle='-', alpha=0.9,
                        transform=ax.transAxes, clip_on=False)

                # Add train type label
                ax.text(x_pos - 0.02, chain_y - y_decrement / 2, train_type,  # Adjusted to align with the middle of the line
                        fontsize=8 if full_page else 6, fontweight='bold', 
                        ha='right', va='center',
                        transform=ax.transAxes, clip_on=False)
                
                # Draw station symbol
                ax.plot(x_pos, chain_y, marker='o', markersize=10 if full_page else 8,
                        markeredgecolor='black', markerfacecolor='white', 
                        transform=ax.transAxes, clip_on=False)
                
                # Add city label
                ax.text(x_pos + 0.02, chain_y, city1, 
                        fontsize=10 if full_page else 7, fontfamily='sans-serif', 
                        ha='left', va='center', transform=ax.transAxes, clip_on=False, 
                        bbox=dict(facecolor='white', edgecolor='none', 
                                 boxstyle='round,pad=0.2' if full_page else 'round,pad=0.1'))
                
                chain_y -= y_decrement
            
            # Add the last city in the chain
            if chain:
                last_city = chain[-1][1]
                ax.plot(x_pos, chain_y, marker='o', markersize=10 if full_page else 8,
                        markeredgecolor='black', markerfacecolor='white', 
                        transform=ax.transAxes, clip_on=False)
                ax.text(x_pos + 0.02, chain_y, last_city, 
                        fontsize=10 if full_page else 7, fontfamily='sans-serif', 
                        ha='left', va='center', transform=ax.transAxes, clip_on=False, 
                        bbox=dict(facecolor='white', edgecolor='none', 
                                 boxstyle='round,pad=0.2' if full_page else 'round,pad=0.1'))

    def export_as_pdf(self, filepath):
        """Export the map as a DIN A4 PDF"""
        try:
            # Create directory only if it doesn't already exist in the path
            directory = os.path.dirname(filepath)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            # Save the original figure size to restore it later
            original_figsize = self.fig.get_size_inches()
            
            with PdfPages(filepath) as pdf:
                # First page - Map only (full page)
                self.fig.set_size_inches(8.27, 11.69)  # DIN A4 dimensions
                
                # Save current axes position
                original_position = self.ax.get_position()
                
                # Maximize map to use full page
                self.ax.set_position([0.05, 0.05, 0.9, 0.9])
                
                # Save the map page (without legend)
                pdf.savefig(self.fig, bbox_inches='tight')
                
                # Second page - Legend only
                legend_fig = plt.figure(figsize=(8.27, 11.69))  # New figure for legend
                legend_ax = legend_fig.add_subplot(111)
                legend_ax.axis('off')
                
                # Draw the legend on the new figure
                self.draw_legend_on_axes(legend_ax, full_page=True)
                
                # Add title to the legend page
                legend_fig.suptitle("Train Route Legend", fontsize=16, y=0.98)
                
                # Save the legend page
                pdf.savefig(legend_fig, bbox_inches='tight')
                plt.close(legend_fig)  # Close the legend figure
            
            # Restore original map settings
            self.ax.set_position(original_position)
            self.fig.set_size_inches(original_figsize)
            
            return True, f"Plot exported successfully to {filepath}."
        except Exception as e:
            logging.error(f"Failed to export plot: {str(e)}", exc_info=True)
            return False, f"Failed to export plot: {str(e)}"

class TrainRouteApp:
    """Main application class"""
    def __init__(self, root):
        self.root = root
        self.root.title("City and Connection Manager")
        # Initialize data
        self.route_data = RouteData()
        # Load map data
        if not os.path.exists(SHAPEFILE_PATH):
            raise Exception(f"Shapefile not found at {SHAPEFILE_PATH}. Please download it from Natural Earth.")
        admin1 = gpd.read_file(SHAPEFILE_PATH)
        admin1 = admin1[admin1['admin'] == 'Germany']
        self.germany = admin1[admin1['admin'] == 'Germany']
        # Initialize map plotter
        self.map_plotter = MapPlotter(self.route_data)
        self.map_plotter.initialize_map(self.germany)
        # Set up old UI (minimized)
        self.setup_old_ui()
        # Open integrated UI automatically
        self.open_integrated_ui()
    def setup_old_ui(self):
        """Set up the original UI (will be minimized)"""
        # These buttons are just for compatibility and won't be visible
        tk.Button(self.root, text="Add City", command=self.add_city_dialog).pack(pady=5)
        tk.Button(self.root, text="Plot Map", command=self.plot_map).pack(pady=5)
        tk.Button(self.root, text="Edit City", command=self.edit_city_dialog).pack(pady=5)
        tk.Button(self.root, text="Remove City", command=self.remove_city_dialog).pack(pady=5)
        tk.Button(self.root, text="Remove Default Cities", command=self.remove_default_cities).pack(pady=5)
        tk.Button(self.root, text="Remove Route", command=self.remove_route_dialog).pack(pady=5)
        tk.Button(self.root, text="Add Connection", command=self.add_connection_dialog).pack(pady=5)
        tk.Button(self.root, text="Open Integrated UI and Plot", command=self.open_integrated_ui).pack(pady=5)
        # Debug menu
        menu_bar = tk.Menu(self.root)
        self.root.config(menu=menu_bar)
        menu_bar.add_command(label="Run Debug Checks", command=self.debug_functionality)
    def open_integrated_ui(self):
        """Open the integrated UI window and minimize the old one"""
        self.root.withdraw()  # Hide the old UI
        # Create new window
        self.integrated_window = tk.Toplevel(self.root)
        self.integrated_window.title("Train Route Visualizer")
        # Set up menu
        self.create_integrated_menu()
        # Create plot frame
        plot_frame = tk.Frame(self.integrated_window)
        plot_frame.pack(fill=tk.BOTH, expand=True)
        # Set up the matplotlib canvas
        self.map_plotter.set_canvas(plot_frame)
        # Close handler
        self.integrated_window.protocol("WM_DELETE_WINDOW", self.on_close)
    def create_integrated_menu(self):
        """Create menu for the integrated UI"""
        menu_bar = tk.Menu(self.integrated_window)
        self.integrated_window.config(menu=menu_bar)
        # File menu
        file_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Save Routes", command=self.save_routes)
        file_menu.add_command(label="Load Routes", command=self.load_routes)
        # City menu
        city_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="City", menu=city_menu)
        city_menu.add_command(label="Add City", command=lambda: self.add_city_dialog(update_plot=True))
        city_menu.add_command(label="Edit City", command=lambda: self.edit_city_dialog(update_plot=True))
        city_menu.add_command(label="Remove City", command=lambda: self.remove_city_dialog(update_plot=True))
        city_menu.add_command(label="Remove Default Cities", command=lambda: self.remove_default_cities(update_plot=True))
        # Connections menu
        conn_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Connections", menu=conn_menu)
        conn_menu.add_command(label="Add Connection", command=lambda: self.add_connection_dialog(update_plot=True))
        conn_menu.add_command(label="Edit Connection", command=lambda: self.edit_connection_dialog(update_plot=True))
        conn_menu.add_command(label="Remove Connection", command=lambda: self.remove_route_dialog(update_plot=True))
        # Export menu
        export_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Export", menu=export_menu)
        export_menu.add_command(label="Export as DIN A4 PDF", command=self.export_as_pdf)
        # Zoom menu
        zoom_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Zoom", menu=zoom_menu)
        zoom_menu.add_command(label="Zoom into States", command=self.zoom_into_states_dialog)
        zoom_menu.add_command(label="Reset Zoom", command=self.reset_zoom)
        # Update plot commands
        menu_bar.add_command(label="Update Plot", command=self.reset_zoom)
        menu_bar.add_command(label="Update Plot (Selected State)", command=self.map_plotter.update_plot)
    def on_close(self):
        """Handle window closing"""
        self.integrated_window.destroy()
        self.root.destroy()
    def add_city_dialog(self, update_plot=False):
        """Dialog to add a new city by postal code"""
        postal_code = simpledialog.askstring("Add City", "Enter Postleitzahl:")
        if not postal_code:
            return
        success, message = self.route_data.add_city(postal_code)
        if success:
            messagebox.showinfo("Success", message)
            if update_plot:
                self.map_plotter.update_plot()
        else:
            messagebox.showerror("Error", message)
    def add_connection_dialog(self, update_plot=False):
        """Dialog to add a connection between cities with train type selection"""
        if len(self.route_data.cities) < 2:
            messagebox.showerror("Error", "At least two cities are required to add a connection.")
            return
        add_window = tk.Toplevel(self.root if not hasattr(self, 'integrated_window') else self.integrated_window)
        add_window.title("Add Connection")
        # City selection
        tk.Label(add_window, text="Select the first city:").grid(row=0, column=0, padx=5, pady=5)
        city1_var = tk.StringVar(add_window)
        city1_var.set(sorted(self.route_data.cities.keys())[0])
        city1_menu = tk.OptionMenu(add_window, city1_var, *sorted(self.route_data.cities.keys()))
        city1_menu.grid(row=0, column=1, padx=5, pady=5)
        tk.Label(add_window, text="Select the second city:").grid(row=0, column=2, padx=5, pady=5)
        city2_var = tk.StringVar(add_window)
        city2_var.set(sorted(self.route_data.cities.keys())[1])
        city2_menu = tk.OptionMenu(add_window, city2_var, *sorted(self.route_data.cities.keys()))
        city2_menu.grid(row=0, column=3, padx=5, pady=5)
        # Train type selection
        tk.Label(add_window, text="Select train type:").grid(row=1, column=0, padx=5, pady=5)
        train_type_var = tk.StringVar(add_window)
        train_type_var.set(DEFAULT_TRAIN_TYPE) 
        train_menu = tk.OptionMenu(add_window, train_type_var, *TRAIN_TYPES.keys())
        train_menu.grid(row=1, column=1, padx=5, pady=5)
        # Train description
        train_desc_var = tk.StringVar(add_window)
        train_desc_var.set(f"Speed: {int(TRAIN_TYPES[DEFAULT_TRAIN_TYPE]['speed_factor'] * 100)}% of base")
        tk.Label(add_window, textvariable=train_desc_var).grid(row=1, column=2, columnspan=2, sticky='w')
        # Update description when train type changes
        def update_train_desc(*args):
            train_type = train_type_var.get()
            train_desc_var.set(f"Speed: {int(TRAIN_TYPES[train_type]['speed_factor'] * 100)}% of base")
        train_type_var.trace('w', update_train_desc)
        def create_connection():
            city1 = city1_var.get()
            city2 = city2_var.get()
            train_type = train_type_var.get()
            success, message = self.route_data.add_connection(city1, city2, train_type)
            if success:
                messagebox.showinfo("Success", message)
                add_window.destroy()
                if update_plot:
                    self.map_plotter.update_plot()
            else:
                messagebox.showerror("Error", message)
        tk.Button(add_window, text="Add Connection", command=create_connection).grid(
            row=2, column=0, columnspan=4, pady=10)
    def edit_city_dialog(self, update_plot=False):
        """Dialog to edit a city's coordinates"""
        city_list = list(self.route_data.cities.keys())
        if not city_list:
            messagebox.showinfo("Info", "No cities available to edit.")
            return
        edit_window = tk.Toplevel(self.root if not hasattr(self, 'integrated_window') else self.integrated_window)
        edit_window.title("Edit Cities")
        tk.Label(edit_window, text="Select a city to edit:").pack(pady=5)
        city_var = tk.StringVar(edit_window)
        city_var.set(city_list[0])
        city_menu = tk.OptionMenu(edit_window, city_var, *city_list)
        city_menu.pack(pady=5)
        def update_city():
            city_name = city_var.get()
            try:
                lon = float(simpledialog.askstring("Edit City", f"Enter new longitude for {city_name}:"))
                lat = float(simpledialog.askstring("Edit City", f"Enter new latitude for {city_name}:"))
                if self.route_data.update_city_coordinates(city_name, lon, lat):
                    messagebox.showinfo("Success", f"City {city_name} updated successfully!")
                    if update_plot:
                        self.map_plotter.update_plot()
                else:
                    messagebox.showerror("Error", f"City {city_name} could not be updated.")
            except ValueError:
                messagebox.showerror("Error", "Invalid coordinates. Please enter numeric values.")
        tk.Button(edit_window, text="Edit City", command=update_city).pack(pady=5)
    def remove_city_dialog(self, update_plot=False):
        """Dialog to remove a city"""
        city_list = list(self.route_data.cities.keys())
        if not city_list:
            messagebox.showinfo("Info", "No cities available to remove.")
            return
        remove_window = tk.Toplevel(self.root if not hasattr(self, 'integrated_window') else self.integrated_window)
        remove_window.title("Remove Cities")
        tk.Label(remove_window, text="Select a city to remove:").pack(pady=5)
        city_var = tk.StringVar(remove_window)
        city_var.set(city_list[0])
        city_menu = tk.OptionMenu(remove_window, city_var, *city_list)
        city_menu.pack(pady=5)
        def delete_city():
            city_name = city_var.get()
            success, message = self.route_data.remove_city(city_name)
            if success:
                messagebox.showinfo("Success", message)
                remove_window.destroy()
                if update_plot:
                    self.map_plotter.update_plot()
            else:
                messagebox.showerror("Error", message)
        tk.Button(remove_window, text="Remove City", command=delete_city).pack(pady=5)
    def remove_default_cities(self, update_plot=False):
        """Remove all default cities"""
        self.route_data.remove_default_cities()
        messagebox.showinfo("Success", "All default cities and their connections have been removed.")
        if update_plot:
            self.map_plotter.update_plot()
    def remove_route_dialog(self, update_plot=False):
        """Dialog to remove a connection"""
        if not self.route_data.connections:
            messagebox.showinfo("Info", "No routes available to remove.")
            return
        remove_window = tk.Toplevel(self.root if not hasattr(self, 'integrated_window') else self.integrated_window)
        remove_window.title("Remove Routes")
        tk.Label(remove_window, text="Select a route to remove:").pack(pady=5)
        route_var = tk.StringVar(remove_window)
        route_var.set(f"{self.route_data.connections[0][0]} -> {self.route_data.connections[0][1]}")
        route_menu = tk.OptionMenu(remove_window, route_var,  *[f"{conn[0]} -> {conn[1]}" for conn in self.route_data.connections])
        route_menu.pack(pady=5)
        def delete_route():
            selected_route = route_var.get().split(" -> ")
            city1, city2 = selected_route[0], selected_route[1]
            success = self.route_data.remove_connection(city1, city2)
            if success:
                messagebox.showinfo("Success", f"Route {city1} -> {city2} removed successfully!")
                remove_window.destroy()
                if update_plot:
                    self.map_plotter.update_plot()
            else:
                messagebox.showerror("Error", f"Route {city1} -> {city2} could not be removed.")
        tk.Button(remove_window, text="Remove Route", command=delete_route).pack(pady=5)
    def zoom_into_states_dialog(self):
        """Dialog to zoom into specific German states"""
        states = simpledialog.askstring("Zoom", "Enter German states to zoom into (comma-separated):")
        if not states:
            return
        state_list = [state.strip() for state in states.split(",")]
        success, message = self.map_plotter.zoom_into_states(state_list)
        if not success:
            messagebox.showerror("Error", message)
    def reset_zoom(self):
        """Reset map zoom to default"""
        self.map_plotter.reset_zoom()
    def save_routes(self):
        """Save route data to file"""
        save_path = filedialog.asksaveasfilename(defaultextension=".trv", filetypes=[("TRV files", "*.trv"), ("All files", "*.*")])
        if not save_path:
            return
        success, message = self.route_data.save_to_file(save_path)
        if success:
            messagebox.showinfo("Success", message)
        else:
            messagebox.showerror("Error", message)
    def load_routes(self):
        """Load route data from file"""
        load_path = filedialog.askopenfilename(filetypes=[("TRV files", "*.trv"), ("All files", "*.*")])
        if not load_path:
            return
        success, message = self.route_data.load_from_file(load_path)
        if success:
            messagebox.showinfo("Success", message)
            self.map_plotter.update_plot()
        else:
            messagebox.showerror("Error", message)
    def export_as_pdf(self):
        """Export current map as PDF"""
        # Ask user for save location instead of using fixed path
        export_path = filedialog.asksaveasfilename(
            defaultextension=".pdf", 
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            title="Save Train Route Map as PDF"
        )
        
        if not export_path:  # User cancelled the dialog
            return
        
        success, message = self.map_plotter.export_as_pdf(export_path)
        if success:
            messagebox.showinfo("Export Success", message)
        else:
            messagebox.showerror("Export Error", message)
            
    def edit_connection_dialog(self, update_plot=False):
        """Dialog to edit an existing connection's train type and travel time"""
        if not self.route_data.connections:
            messagebox.showinfo("Info", "No connections available to edit.")
            return
            
        edit_window = tk.Toplevel(self.root if not hasattr(self, 'integrated_window') else self.integrated_window)
        edit_window.title("Edit Connection")
        
        # Connection selection
        tk.Label(edit_window, text="Select connection to edit:").grid(row=0, column=0, padx=5, pady=5)
        connection_var = tk.StringVar(edit_window)
        connections_list = [f"{conn[0]} → {conn[1]}" for conn in self.route_data.connections]
        connection_var.set(connections_list[0])
        connection_menu = tk.OptionMenu(edit_window, connection_var, *connections_list)
        connection_menu.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky='ew')
        
        # Train type selection
        tk.Label(edit_window, text="Select train type:").grid(row=1, column=0, padx=5, pady=5)
        train_type_var = tk.StringVar(edit_window)
        
        # Get the current train type for the selected connection
        def update_train_type(*args):
            selected_conn = connection_var.get().split(" → ")
            city1, city2 = selected_conn[0], selected_conn[1]
            current_type = self.route_data.get_train_type(city1, city2)
            train_type_var.set(current_type)
            
            # Update description based on train type
            speed_percent = int(TRAIN_TYPES[current_type]['speed_factor'] * 100)
            train_desc_var.set(f"Speed: {speed_percent}% of base")
        
        # Initial train type setup
        first_conn = connections_list[0].split(" → ")
        first_type = self.route_data.get_train_type(first_conn[0], first_conn[1])
        train_type_var.set(first_type)
        
        train_menu = tk.OptionMenu(edit_window, train_type_var, *TRAIN_TYPES.keys())
        train_menu.grid(row=1, column=1, padx=5, pady=5)
        
        # Set up description label
        train_desc_var = tk.StringVar(edit_window)
        speed_percent = int(TRAIN_TYPES[first_type]['speed_factor'] * 100)
        train_desc_var.set(f"Speed: {speed_percent}% of base")
        tk.Label(edit_window, textvariable=train_desc_var).grid(row=1, column=2, padx=5, sticky='w')
        
        # Travel time input
        tk.Label(edit_window, text="Travel time (minutes):").grid(row=2, column=0, padx=5, pady=5)
        travel_time_entry = tk.Entry(edit_window, width=10)
        travel_time_entry.grid(row=2, column=1, padx=5, pady=5)
        
        # Custom travel time status
        custom_time_var = tk.StringVar(edit_window)
        custom_time_var.set("")
        custom_time_label = tk.Label(edit_window, textvariable=custom_time_var)
        custom_time_label.grid(row=2, column=2, padx=5, pady=5, sticky='w')
        
        # Travel time preview 
        travel_time_var = tk.StringVar(edit_window)
        
        def update_connection_info(*args):
            selected_conn = connection_var.get().split(" → ")
            city1, city2 = selected_conn[0], selected_conn[1]
            
            # Update train type
            current_type = self.route_data.get_train_type(city1, city2)
            train_type_var.set(current_type)
            
            # Update speed description
            speed_percent = int(TRAIN_TYPES[current_type]['speed_factor'] * 100)
            train_desc_var.set(f"Speed: {speed_percent}% of base")
            
            # Update travel time display
            travel_time = self.route_data.get_travel_time(city1, city2)
            travel_time_var.set(f"Current travel time: {travel_time}")
            
            # Check if there's a custom travel time and update the entry
            raw_time = self.route_data.get_raw_travel_time(city1, city2)
            if raw_time is not None:
                travel_time_entry.delete(0, tk.END)
                travel_time_entry.insert(0, str(raw_time))
                custom_time_var.set("(Custom time set)")
                custom_time_label.config(foreground="blue")
            else:
                travel_time_entry.delete(0, tk.END)
                custom_time_var.set("(Using calculated time)")
                custom_time_label.config(foreground="grey")
        
        # Display current travel time
        travel_time = self.route_data.get_travel_time(first_conn[0], first_conn[1])
        travel_time_var.set(f"Current travel time: {travel_time}")
        tk.Label(edit_window, text="Travel time preview:").grid(row=3, column=0, padx=5, pady=5)
        tk.Label(edit_window, textvariable=travel_time_var).grid(row=3, column=1, columnspan=2, padx=5, pady=5, sticky='w')
        
        # Initialize the travel time entry with current value if exists
        raw_time = self.route_data.get_raw_travel_time(first_conn[0], first_conn[1])
        if raw_time is not None:
            travel_time_entry.insert(0, str(raw_time))
            custom_time_var.set("(Custom time set)")
            custom_time_label.config(foreground="blue")
        else:
            custom_time_var.set("(Using calculated time)")
            custom_time_label.config(foreground="grey")
        
        # Connect the connection selector to update all fields
        connection_var.trace('w', update_connection_info)
        
        # Update description when train type changes
        def update_train_desc(*args):
            train_type = train_type_var.get()
            speed_percent = int(TRAIN_TYPES[train_type]['speed_factor'] * 100)
            train_desc_var.set(f"Speed: {speed_percent}% of base")
        
        train_type_var.trace('w', update_train_desc)
        
        # Calculate button to show estimated time
        def calculate_estimated_time():
            selected_conn = connection_var.get().split(" → ")
            city1, city2 = selected_conn[0], selected_conn[1]
            
            if city1 not in self.route_data.cities or city2 not in self.route_data.cities:
                messagebox.showerror("Error", "One or both cities not found.")
                return
            
            # Get coordinates and train type
            coord1 = self.route_data.cities[city1]
            coord2 = self.route_data.cities[city2]
            train_type = train_type_var.get()
            
            # Calculate estimated time (without setting it)
            estimated_time = self.route_data.estimate_travel_time(coord1, coord2, train_type)
            messagebox.showinfo("Estimated Travel Time", 
                              f"Estimated travel time between {city1} and {city2} by {train_type}: {estimated_time}")
        
        # Reset to calculated time
        def reset_to_calculated():
            selected_conn = connection_var.get().split(" → ")
            city1, city2 = selected_conn[0], selected_conn[1]
            
            # Remove custom travel time
            if (city1, city2) in self.route_data.travel_times_data:
                del self.route_data.travel_times_data[(city1, city2)]
            elif (city2, city1) in self.route_data.travel_times_data:
                del self.route_data.travel_times_data[(city2, city1)]
            
            # Update display
            travel_time_entry.delete(0, tk.END)
            custom_time_var.set("(Using calculated time)")
            custom_time_label.config(foreground="grey")
            
            # Update preview
            travel_time = self.route_data.get_travel_time(city1, city2)
            travel_time_var.set(f"Current travel time: {travel_time}")
        
        # Create buttons frame
        button_frame = tk.Frame(edit_window)
        button_frame.grid(row=4, column=0, columnspan=3, pady=10)
        
        tk.Button(button_frame, text="Calculate Estimate", command=calculate_estimated_time).grid(
            row=0, column=0, padx=5
        )
        tk.Button(button_frame, text="Reset to Calculated", command=reset_to_calculated).grid(
            row=0, column=1, padx=5
        )
        
        def save_changes():
            selected_conn = connection_var.get().split(" → ")
            city1, city2 = selected_conn[0], selected_conn[1]
            train_type = train_type_var.get()
            
            # Find the actual connection tuple
            connection_tuple = None
            for conn in self.route_data.connections:
                if (conn[0] == city1 and conn[1] == city2) or (conn[0] == city2 and conn[1] == city1):
                    connection_tuple = conn
                    break
            
            if connection_tuple:
                # Ensure we have a tuple (not a list) for use as dictionary key
                if isinstance(connection_tuple, list):
                    connection_tuple = tuple(connection_tuple)
                
                # Update the train type in the routedata
                self.route_data.connection_train_types[connection_tuple] = train_type
                
                # Update travel time if entered
                custom_time = travel_time_entry.get().strip()
                if custom_time:
                    try:
                        minutes = int(custom_time)
                        if minutes <= 0:
                            messagebox.showerror("Error", "Travel time must be positive")
                            return
                        self.route_data.update_travel_time(connection_tuple[0], connection_tuple[1], minutes)
                        time_status = "custom time"
                    except ValueError:
                        messagebox.showerror("Error", "Travel time must be a number in minutes")
                        return
                else:
                    # If field is empty, use calculated time
                    if (connection_tuple[0], connection_tuple[1]) in self.route_data.travel_times_data:
                        del self.route_data.travel_times_data[(connection_tuple[0], connection_tuple[1])]
                    elif (connection_tuple[1], connection_tuple[0]) in self.route_data.travel_times_data:
                        del self.route_data.travel_times_data[(connection_tuple[1], connection_tuple[0])]
                    time_status = "calculated time"  # Add this line to fix the error
                
                messagebox.showinfo("Success", 
                                 f"Connection {city1} → {city2} updated to {train_type} with {time_status}!");
                edit_window.destroy()
                if update_plot:
                    self.map_plotter.update_plot()
        
        tk.Button(edit_window, text="Save Changes", command=save_changes).grid(
            row=5, column=0, columnspan=3, pady=10)
            
    def plot_map(self):
        """Plot the map in a matplotlib window (legacy function)"""
        fig, ax = plt.subplots(figsize=(20, 20))
        ax.set_facecolor('#F5F5F5')
        self.germany.boundary.plot(ax=ax, linewidth=0.8, color='#CCCCCC')
        # Plot cities
        for city, coord in self.route_data.cities.items():
            ax.plot(coord[0], coord[1], marker='o', markersize=12,
                    markeredgecolor='black', markerfacecolor='white')
        for i, (city1, city2) in enumerate(self.route_data.connections):
            line = LineString([self.route_data.cities[city1], self.route_data.cities[city2]])
            color = CONNECTION_COLORS[i % len(CONNECTION_COLORS)]
            ax.plot(*line.xy, color=color, linewidth=2.5, linestyle='-', alpha=0.9)
        ax.set_xlim(5, 15)
        ax.set_ylim(47, 55)
        ax.axis('off')
        plt.show()
    def debug_functionality(self):
        """Run debug checks on the map data"""
        logging.debug("Starting debug checks...")
        # Check if all cities are plotted
        for city, coord in self.route_data.cities.items():
            logging.debug(f"Checking city: {city} at coordinates {coord}")
            point = GeoSeries([gpd.points_from_xy([coord[0]], [coord[1]])[0]], crs=CRS_EPSG_4326)
            if not any(self.germany.geometry.contains(point.iloc[0])):
                logging.warning(f"City '{city}' is outside the map boundaries.")
        # Check if all connections are valid
        for city1, city2 in self.route_data.connections:
            if city1 not in self.route_data.cities or city2 not in self.route_data.cities:
                logging.error(f"Invalid connection: {city1} -> {city2}")
            else:
                logging.debug(f"Valid connection: {city1} -> {city2}")
        logging.debug("Debug checks completed.")

    @staticmethod
    def haversine_distance(coord1, coord2):
        """Calculate Haversine distance between two coordinates (lon, lat)"""
        lon1, lat1 = radians(coord1[0]), radians(coord1[1])
        lon2, lat2 = radians(coord2[0]), radians(coord2[1])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(a))
        logging.debug(f"Calculating Haversine distance between {coord1} and {coord2}")
        logging.debug(f"Converted coordinates to radians: ({lon1}, {lat1}), ({lon2}, {lat2})")
        logging.debug(f"Final computed Haversine distance (in kilometers): {EARTH_RADIUS_KM * c}")
        logging.debug("Haversine distance calculation completed.")
        return EARTH_RADIUS_KM * c

if __name__ == "__main__":
    app = TrainRouteApp(tk.Tk())
    app.root.mainloop()
