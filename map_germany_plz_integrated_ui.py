import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog
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
    
    def add_connection(self, city1, city2):
        """Add a connection between two cities"""
        if city1 == city2:
            return False, "A city cannot be connected to itself."
        
        if (city1, city2) in self.connections or (city2, city1) in self.connections:
            return False, "This connection already exists."
        
        self.connections.append((city1, city2))
        return True, f"Connection added between {city1} and {city2}!"
    
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
        
        return True, f"City {city_name} and its connections removed successfully!"
    
    def remove_connection(self, city1, city2):
        """Remove a connection between cities"""
        if (city1, city2) in self.connections:
            self.connections.remove((city1, city2))
            return True
        elif (city2, city1) in self.connections:
            self.connections.remove((city2, city1))
            return True
        return False
    
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
        
        self.connections = [conn for conn in self.connections 
                          if conn[0] not in default_city_names and conn[1] not in default_city_names]
    
    def get_travel_time(self, city1, city2):
        """Get travel time between two cities"""
        if (city1, city2) in self.travel_times_data:
            travel_time = self.travel_times_data[(city1, city2)]
        elif (city2, city1) in self.travel_times_data:
            travel_time = self.travel_times_data[(city2, city1)]
        elif city1 in self.cities and city2 in self.cities:
            # Calculate travel time for user-added cities
            return self.estimate_travel_time(self.cities[city1], self.cities[city2])
        else:
            return "N/A"

        # Format travel time
        hours = travel_time // 60
        minutes = travel_time % 60
        return f"{hours}h {minutes}m" if hours > 0 else f"{minutes} min"
    
    def estimate_travel_time(self, coord1, coord2):
        """Estimate travel time based on Haversine distance"""
        distance_km = self.haversine_distance(coord1, coord2)
        travel_time_hours = distance_km / AVERAGE_TRAIN_SPEED_KMH
        travel_time_minutes = int(travel_time_hours * 60)
        hours = travel_time_minutes // 60
        minutes = travel_time_minutes % 60
        return f"{hours}h {minutes}m" if hours > 0 else f"{minutes} min"
    
    @staticmethod
    def haversine_distance(coord1, coord2):
        """Calculate Haversine distance between two coordinates"""
        lon1, lat1 = radians(coord1[0]), radians(coord1[1])
        lon2, lat2 = radians(coord2[0]), radians(coord2[1])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return EARTH_RADIUS_KM * c
    
    def save_to_file(self, filepath):
        """Save cities and connections to a file"""
        try:
            with open(filepath, 'w') as file:
                json.dump({"cities": self.cities, "connections": self.connections}, file)
            return True, f"Routes saved successfully to {filepath}."
        except Exception as e:
            return False, f"Failed to save routes: {str(e)}"
    
    def load_from_file(self, filepath):
        """Load cities and connections from a file"""
        try:
            with open(filepath, 'r') as file:
                data = json.load(file)
                self.cities = data.get("cities", {})
                self.connections = data.get("connections", [])
                self.city_ids = {city: f"city_{i}" for i, city in enumerate(self.cities.keys())}
            return True, f"Routes loaded successfully from {filepath}."
        except Exception as e:
            return False, f"Failed to load routes: {str(e)}"


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

        # Plot cities and connections
        for city, coord in self.route_data.cities.items():
            self.ax.plot(coord[0], coord[1], marker='o', markersize=12,
                    markeredgecolor='black', markerfacecolor='white')

        for i, (city1, city2) in enumerate(self.route_data.connections):
            if city1 in self.route_data.cities and city2 in self.route_data.cities:
                line = LineString([self.route_data.cities[city1], self.route_data.cities[city2]])
                color = CONNECTION_COLORS[i % len(CONNECTION_COLORS)]
                self.ax.plot(*line.xy, color=color, linewidth=2.5, linestyle='-', alpha=0.9)

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
            if travel_time in existing_labels:
                continue  # Skip duplicate labels

            existing_labels.add(travel_time)

            # Calculate midpoint
            x1, y1 = self.route_data.cities[city1]
            x2, y2 = self.route_data.cities[city2]
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2

            # Draw travel time label
            self.ax.text(mid_x, mid_y, travel_time, fontsize=8, fontfamily='sans-serif',
                    fontweight='bold', color='black', 
                    bbox=dict(facecolor='white', edgecolor='none', boxstyle='round,pad=0.2'),
                    zorder=11)
    
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
        """Add a legend showing route chains and travel times"""
        # Clear existing legends
        for child in self.fig.get_children():
            if isinstance(child, plt.Axes) and child != self.ax:
                child.remove()

        # Group connections into chains
        chains = []
        visited = set()

        def dfs(city, chain):
            for conn in self.route_data.connections:
                if city in conn:
                    other_city = conn[1] if conn[0] == city else conn[0]
                    if other_city not in visited:
                        visited.add(other_city)
                        chain.append((city, other_city))
                        dfs(other_city, chain)

        for city in self.route_data.cities:
            if city not in visited:
                visited.add(city)
                chain = []
                dfs(city, chain)
                if chain:
                    chains.append(chain)

        # Define legend positioning
        x_start = 0.1
        y_start = -0.1
        x_increment = 0.3
        y_decrement = 0.05

        # Draw legends for each chain
        for chain_idx, chain in enumerate(chains):
            x_pos = x_start + (chain_idx * x_increment)
            chain_y = y_start
            total_time_minutes = 0

            for i, (city1, city2) in enumerate(chain):
                # Draw connecting line
                if i > 0:
                    self.ax.plot([x_pos, x_pos], [chain_y + y_decrement, chain_y],
                            color=CONNECTION_COLORS[i % len(CONNECTION_COLORS)], 
                            linewidth=2.5, transform=self.ax.transAxes, clip_on=False)

                # Draw station symbol
                self.ax.plot(x_pos, chain_y, marker='o', markersize=10,
                        markeredgecolor='black', markerfacecolor='white', 
                        transform=self.ax.transAxes, clip_on=False)

                # Add city label
                self.ax.text(x_pos + 0.05, chain_y, city1, fontsize=8, fontfamily='sans-serif', 
                        ha='left', transform=self.ax.transAxes, clip_on=False, 
                        bbox=dict(facecolor='white', edgecolor='none', boxstyle='round,pad=0.2'))

                # Calculate travel time
                travel_time = self.route_data.get_travel_time(city1, city2)
                if travel_time != "N/A":
                    hours, minutes = 0, 0
                    if "h" in travel_time:
                        time_parts = travel_time.split("h")
                        hours = int(time_parts[0].strip())
                        minutes = int(time_parts[1].replace("m", "").strip()) if "m" in time_parts[1] else 0
                    elif "min" in travel_time:
                        minutes = int(travel_time.replace("min", "").strip())
                    total_time_minutes += hours * 60 + minutes

                chain_y -= y_decrement

            # Add chain title with total time
            total_hours = total_time_minutes // 60
            total_minutes = total_time_minutes % 60
            total_time_str = f"Total: {total_hours}h {total_minutes}m" if total_hours > 0 else f"Total: {total_minutes} min"
            self.ax.text(x_pos, chain_y - 0.05, f"Route {chain_idx + 1} ({total_time_str})",
                    fontsize=10, fontfamily='sans-serif', ha='left', transform=self.ax.transAxes, 
                    clip_on=False, fontweight='bold', 
                    bbox=dict(facecolor='lightgrey', edgecolor='none', boxstyle='round,pad=0.3'))
    
    def export_as_pdf(self, filepath):
        """Export the map as a DIN A4 PDF"""
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with PdfPages(filepath) as pdf:
                # Set to DIN A4 dimensions
                self.fig.set_size_inches(8.27, 11.69)
                # Add legend for the PDF export
                self.add_legend()
                pdf.savefig(self.fig, bbox_inches='tight')
                # Reset to original size after export
                self.fig.set_size_inches(10, 10)
            return True, f"Plot exported successfully to {filepath}."
        except Exception as e:
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
        """Dialog to add a connection between cities"""
        if len(self.route_data.cities) < 2:
            messagebox.showerror("Error", "At least two cities are required to add a connection.")
            return

        add_window = tk.Toplevel(self.root if not hasattr(self, 'integrated_window') else self.integrated_window)
        add_window.title("Add Connection")

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

        def create_connection():
            city1 = city1_var.get()
            city2 = city2_var.get()
            success, message = self.route_data.add_connection(city1, city2)
            
            if success:
                messagebox.showinfo("Success", message)
                add_window.destroy()
                if update_plot:
                    self.map_plotter.update_plot()
            else:
                messagebox.showerror("Error", message)

        tk.Button(add_window, text="Add Connection", command=create_connection).grid(
            row=1, column=0, columnspan=4, pady=10)
    
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
        route_menu = tk.OptionMenu(remove_window, route_var, 
                                  *[f"{conn[0]} -> {conn[1]}" for conn in self.route_data.connections])
        route_menu.pack(pady=5)
        
        def delete_route():
            selected_route = route_var.get()
            city1, city2 = selected_route.split(" -> ")
            
            if self.route_data.remove_connection(city1, city2):
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
        save_path = filedialog.asksaveasfilename(
            defaultextension=".trv", 
            filetypes=[("TRV files", "*.trv"), ("All files", "*.*")]
        )
        if not save_path:
            return
            
        success, message = self.route_data.save_to_file(save_path)
        if success:
            messagebox.showinfo("Success", message)
        else:
            messagebox.showerror("Error", message)
    
    def load_routes(self):
        """Load route data from file"""
        load_path = filedialog.askopenfilename(
            filetypes=[("TRV files", "*.trv"), ("All files", "*.*")]
        )
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
        export_path = os.path.join("export", "Plot_DIN_A4.pdf")
        success, message = self.map_plotter.export_as_pdf(export_path)
        
        if success:
            messagebox.showinfo("Export Success", message)
        else:
            messagebox.showerror("Export Error", message)
    
    def plot_map(self):
        """Plot the map in a matplotlib window (legacy function)"""
        fig, ax = plt.subplots(figsize=(20, 20))
        ax.set_facecolor('#F5F5F5')
        self.germany.boundary.plot(ax=ax, linewidth=0.8, color='#CCCCCC')
        
        # Plot cities and connections
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


if __name__ == "__main__":
    app = TrainRouteApp(tk.Tk())
    app.root.mainloop()
