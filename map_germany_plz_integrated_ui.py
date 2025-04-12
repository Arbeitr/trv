import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog  # Import filedialog for Open File Dialog
import geopandas as gpd
import matplotlib.pyplot as plt
import os
from shapely.geometry import LineString
import pgeocode  # New dependency for postal code to coordinate lookup
import math     # For validating numerical coordinates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backends.backend_pdf import PdfPages
import json  # For saving and loading routes
from math import radians, sin, cos, sqrt, atan2  # For Haversine formula
from geopandas import GeoSeries  # Ensure GeoSeries is imported

# Ensure the root window is defined before creating any widgets
root = tk.Tk()
root.title("City and Connection Manager")

# Use a local shapefile instead of downloading it
shapefile_path = "ne_10m_admin_1_states_provinces.shp"
if not os.path.exists(shapefile_path):
    raise Exception("Shapefile not found. Please download it from Natural Earth and place it in the script directory.")

admin1 = gpd.read_file(shapefile_path)
# Filter dataset for Germany
germany = admin1[admin1['admin'] == 'Germany']

# Initialize cities and connections with predefined values
cities = {
    "Frankfurt": (8.6821, 50.1109),
    "Mannheim": (8.4660, 49.4875),
    "München": (11.5820, 48.1351),
    "Erfurt": (11.0299, 50.9848),
    "Leipzig": (12.3731, 51.3397),
    "Potsdam": (13.0635, 52.3989),
    "Berlin": (13.4050, 52.5200),
    "Magdeburg": (11.6276, 52.1205),
    "Hannover": (9.7320, 52.3759),
    "Bremen": (8.8017, 53.0793),
    "Hamburg": (9.9937, 53.5511),
    "Schwerin": (11.4074, 53.6294),
    "Stralsund": (13.0810, 54.3091),
    "Köln": (6.9603, 50.9375),
    "Saarbrücken": (6.9969, 49.2402),
    "Mainz": (8.2473, 49.9982)
}

connections = [
    ("Frankfurt", "Mannheim"),
    ("Mannheim", "München"),
    ("München", "Erfurt"),
    ("Erfurt", "Leipzig"),
    ("Leipzig", "Potsdam"),
    ("Potsdam", "Berlin"),
    ("Berlin", "Magdeburg"),
    ("Magdeburg", "Hannover"),
    ("Hannover", "Bremen"),
    ("Bremen", "Hamburg"),
    ("Hamburg", "Schwerin"),
    ("Schwerin", "Stralsund"),
    ("Stralsund", "Köln"),
    ("Köln", "Saarbrücken"),
    ("Saarbrücken", "Mainz")
]

connection_colors = [
    "#FFD800", "#F39200", "#A9455D", "#E93E8F", "#814997",
    "#1455C0", "#309FD1", "#00A099", "#408335", "#63A615",
    "#858379", "#646973"
]

# Assign unique IDs to states and create bounding boxes
state_ids = {state: f"state_{i}" for i, state in enumerate(germany['name'])}
germany['state_id'] = germany['name'].map(state_ids)
germany['bounding_box'] = germany.geometry.apply(lambda geom: geom.bounds)

# Assign unique IDs to cities
city_ids = {city: f"city_{i}" for i, city in enumerate(cities.keys())}

# Update the add_city function to assign a unique ID
def add_city():
    postal_code = simpledialog.askstring("Add City", "Enter Postleitzahl:")
    if not postal_code:
        return
    try:
        nomi = pgeocode.Nominatim('de')
        info = nomi.query_postal_code(postal_code)
        if math.isnan(info.latitude) or math.isnan(info.longitude):
            messagebox.showerror("Error", "Postal code not found. Please enter a valid Postleitzahl.")
            return
        city_name = info.place_name if info.place_name else postal_code
        cities[city_name] = (info.longitude, info.latitude)
        city_ids[city_name] = f"city_{len(city_ids)}"  # Assign a unique ID
        messagebox.showinfo("Success", f"City '{city_name}' added successfully!")
    except Exception as e:
        messagebox.showerror("Error", "Error retrieving location data: " + str(e))

# Ensure the plot updates dynamically when a new route is added
def add_connection_dialog():
    if len(cities) < 2:
        messagebox.showerror("Error", "At least two cities are required to add a connection.")
        return

    add_window = tk.Toplevel(root)
    add_window.title("Add Connection")

    tk.Label(add_window, text="Select the first city:").grid(row=0, column=0, padx=5, pady=5)
    city1_var = tk.StringVar(add_window)
    city1_var.set(sorted(cities.keys())[0])
    city1_menu = tk.OptionMenu(add_window, city1_var, *sorted(cities.keys()))
    city1_menu.grid(row=0, column=1, padx=5, pady=5)

    tk.Label(add_window, text="Select the second city:").grid(row=0, column=2, padx=5, pady=5)
    city2_var = tk.StringVar(add_window)
    city2_var.set(sorted(cities.keys())[1])
    city2_menu = tk.OptionMenu(add_window, city2_var, *sorted(cities.keys()))
    city2_menu.grid(row=0, column=3, padx=5, pady=5)

    def create_connection():
        city1 = city1_var.get()
        city2 = city2_var.get()
        if city1 == city2:
            messagebox.showerror("Error", "A city cannot be connected to itself.")
            return
        if (city1, city2) in connections or (city2, city1) in connections:
            messagebox.showerror("Error", "This connection already exists.")
            return
        connections.append((city1, city2))
        messagebox.showinfo("Success", f"Connection added between {city1} and {city2}!")
        add_window.destroy()
        # Update the plot dynamically
        if 'canvas' in globals() and 'ax' in globals() and 'fig' in globals():
            update_plot(canvas, ax, fig)

    tk.Button(add_window, text="Add Connection", command=create_connection).grid(row=1, column=0, columnspan=4, pady=10)

# Ensure the button is defined before updating its configuration
add_connection_button = tk.Button(root, text="Add Connection")
add_connection_button.pack(pady=5)
add_connection_button.config(command=add_connection_dialog)

# Add a debug feature to check functionality
import logging

# Configure logging for debugging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def debug_functionality():
    logging.debug("Starting debug checks...")

    # Check if all cities are plotted
    for city, coord in cities.items():
        logging.debug(f"Checking city: {city} at coordinates {coord}")
        point = GeoSeries([gpd.points_from_xy([coord[0]], [coord[1]])[0]], crs="EPSG:4326")
        if not any(germany.geometry.contains(point.iloc[0])):
            logging.warning(f"City '{city}' is outside the map boundaries.")

    # Check if all connections are valid
    for city1, city2 in connections:
        if city1 not in cities or city2 not in cities:
            logging.error(f"Invalid connection: {city1} -> {city2}")
        else:
            logging.debug(f"Valid connection: {city1} -> {city2}")

    # Check if labels are correctly hidden outside selected states
    if 'filtered_states' in globals():
        verify_labels_hidden(filtered_states)
    else:
        logging.info("No filtered states to verify labels against.")

    logging.debug("Debug checks completed.")

# Add a menu entry to trigger the debug feature
menu_bar = tk.Menu(root)
root.config(menu=menu_bar)
menu_bar.add_command(label="Run Debug Checks", command=debug_functionality)

# Add a debug parameter to visualize cluster radius
# Function to handle labels for congested areas with many cities
# Uses color-coded clusters and combined labels for better visualization

def handle_congested_areas(ax, cities, debug=False):
    cluster_radius = 1.0  # Reduced radius to group cities into clusters more frequently
    clusters = []

    # Group cities into clusters based on proximity
    for city, (x, y) in cities.items():
        added_to_cluster = False
        for cluster in clusters:
            cluster_center = cluster['center']
            if abs(cluster_center[0] - x) < cluster_radius and abs(cluster_center[1] - y) < cluster_radius:
                cluster['cities'].append(city)
                cluster['coords'].append((x, y))
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

    # Draw clusters and labels
    for cluster in clusters:
        if len(cluster['cities']) == 1:
            # Single city, draw normally
            city = cluster['cities'][0]
            x, y = cluster['coords'][0]
            ax.text(x, y, city, fontsize=10, fontfamily='sans-serif',
                    fontweight='bold', color='white',
                    bbox=dict(facecolor='darkgrey', edgecolor='none', boxstyle='round,pad=0.3'),
                    zorder=10)
        else:
            # Multiple cities, combine into a cluster label
            cluster_center = cluster['center']
            cluster_label = ", ".join(cluster['cities'])  # Combine city names into a single label
            ax.text(cluster_center[0], cluster_center[1] + 0.2, cluster_label, fontsize=10, fontfamily='sans-serif',
                    fontweight='bold', color='white',
                    bbox=dict(facecolor='red', edgecolor='none', boxstyle='round,pad=0.3'),
                    zorder=10)

    # Debug mode: visualize cluster radius
    if debug:
        for city, (x, y) in cities.items():
            circle = plt.Circle((x, y), cluster_radius, color='blue', fill=False, linestyle='--', linewidth=0.8, zorder=5)
            ax.add_patch(circle)

    # Hide labels for cities that are part of a cluster
    clustered_cities = set()
    for cluster in clusters:
        if len(cluster['cities']) > 1:
            clustered_cities.update(cluster['cities'])

    return clusters, clustered_cities

# Function to plot the map
def plot_map():
    fig, ax = plt.subplots(figsize=(20, 20))
    ax.set_facecolor('#F5F5F5')
    germany.boundary.plot(ax=ax, linewidth=0.8, color='#CCCCCC')
    # Create labels and adjust positions to prevent overlap
    for city, coord in cities.items():
        ax.plot(coord[0], coord[1], marker='o', markersize=12,
                markeredgecolor='black', markerfacecolor='white')
    for i, (city1, city2) in enumerate(connections):
        line = LineString([cities[city1], cities[city2]])
        color = connection_colors[i % len(connection_colors)]
        ax.plot(*line.xy, color=color, linewidth=2.5, linestyle='-', alpha=0.9)
    ax.set_xlim(5, 15)
    ax.set_ylim(47, 55)
    ax.axis('off')
    plt.show()

# Function to edit a city's coordinates using a dialog box
def edit_city_dialog():
    city_list = list(cities.keys())
    if not city_list:
        messagebox.showinfo("Info", "No cities available to edit.")
        return
    edit_window = tk.Toplevel(root)
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
            cities[city_name] = (lon, lat)
            messagebox.showinfo("Success", f"City {city_name} updated successfully!")
        except ValueError:
            messagebox.showerror("Error", "Invalid coordinates. Please enter numeric values.")
    tk.Button(edit_window, text="Edit City", command=update_city).pack(pady=5)

# Function to remove a city using a dialog box and handle indirect connections
def remove_city_dialog():
    city_list = list(cities.keys())
    if not city_list:
        messagebox.showinfo("Info", "No cities available to remove.")
        return
    remove_window = tk.Toplevel(root)
    remove_window.title("Remove Cities")
    tk.Label(remove_window, text="Select a city to remove:").pack(pady=5)
    city_var = tk.StringVar(remove_window)
    city_var.set(city_list[0])
    city_menu = tk.OptionMenu(remove_window, city_var, *city_list)
    city_menu.pack(pady=5)
    def delete_city():
        city_name = city_var.get()
        if city_name in cities:
            del cities[city_name]
            global connections
            new_connections = []
            directly_connected = [conn for conn in connections if city_name in conn]
            for conn1 in directly_connected:
                for conn2 in directly_connected:
                    if conn1 != conn2:
                        city_a = conn1[0] if conn1[1] == city_name else conn1[1]
                        city_b = conn2[0] if conn2[1] == city_name else conn2[1]
                        if (city_a, city_b) not in connections and (city_b, city_a) not in connections:
                            new_connections.append((city_a, city_b))
            connections = [conn for conn in connections if city_name not in conn]
            connections.extend(new_connections)
            messagebox.showinfo("Success", f"City {city_name} and its connections removed successfully! Indirect connections added where applicable.")
            remove_window.destroy()
        else:
            messagebox.showerror("Error", f"City {city_name} does not exist.")
    tk.Button(remove_window, text="Remove City", command=delete_city).pack(pady=5)

# Function to remove all default cities
def remove_default_cities():
    default_cities = [
        "Frankfurt", "Mannheim", "München", "Erfurt", "Leipzig", "Potsdam", "Berlin",
        "Magdeburg", "Hannover", "Bremen", "Hamburg", "Schwerin", "Stralsund", "Köln",
        "Saarbrücken", "Mainz"
    ]
    for city in default_cities:
        if city in cities:
            del cities[city]
    global connections
    connections = [conn for conn in connections if conn[0] not in default_cities and conn[1] not in default_cities]
    messagebox.showinfo("Success", "All default cities and their connections have been removed.")

# Function to remove a route using a dialog box
def remove_route_dialog():
    if not connections:
        messagebox.showinfo("Info", "No routes available to remove.")
        return
    remove_window = tk.Toplevel(root)
    remove_window.title("Remove Routes")
    tk.Label(remove_window, text="Select a route to remove:").pack(pady=5)
    route_var = tk.StringVar(remove_window)
    route_var.set(f"{connections[0][0]} -> {connections[0][1]}")
    route_menu = tk.OptionMenu(remove_window, route_var, *[f"{conn[0]} -> {conn[1]}" for conn in connections])
    route_menu.pack(pady=5)

    def delete_route():
        selected_route = route_var.get()
        city1, city2 = selected_route.split(" -> ")
        if (city1, city2) in connections:
            connections.remove((city1, city2))
        elif (city2, city1) in connections:
            connections.remove((city2, city1))
        messagebox.showinfo("Success", f"Route {city1} -> {city2} removed successfully!")
        remove_window.destroy()

    tk.Button(remove_window, text="Remove Route", command=delete_route).pack(pady=5)

# Static dataset of train travel times between cities (in minutes)
travel_times_data = {
    ("Frankfurt", "Mannheim"): 30,
    ("Mannheim", "München"): 150,
    ("München", "Erfurt"): 180,
    ("Erfurt", "Leipzig"): 60,
    ("Leipzig", "Potsdam"): 90,
    ("Potsdam", "Berlin"): 30,
    ("Berlin", "Magdeburg"): 105,
    ("Magdeburg", "Hannover"): 90,
    ("Hannover", "Bremen"): 75,
    ("Bremen", "Hamburg"): 60,
    ("Hamburg", "Schwerin"): 90,
    ("Schwerin", "Stralsund"): 120,
    ("Stralsund", "Köln"): 360,
    ("Köln", "Saarbrücken"): 180,
    ("Saarbrücken", "Mainz"): 90
}

# Average train speed in km/h (adjust as needed)
AVERAGE_TRAIN_SPEED_KMH = 100

# Function to calculate the Haversine distance between two coordinates
def haversine_distance(coord1, coord2):
    lon1, lat1 = radians(coord1[0]), radians(coord1[1])
    lon2, lat2 = radians(coord2[0]), radians(coord2[1])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    earth_radius_km = 6371  # Earth's radius in kilometers
    return earth_radius_km * c

# Function to estimate travel time based on distance
def estimate_travel_time(coord1, coord2):
    distance_km = haversine_distance(coord1, coord2)
    travel_time_hours = distance_km / AVERAGE_TRAIN_SPEED_KMH
    travel_time_minutes = int(travel_time_hours * 60)
    hours = travel_time_minutes // 60
    minutes = travel_time_minutes % 60
    return f"{hours}h {minutes}m" if hours > 0 else f"{minutes} min"

# Fix the TypeError in get_travel_time by ensuring travel_time is always an integer when performing calculations.
def get_travel_time(city1, city2):
    if (city1, city2) in travel_times_data:
        travel_time = travel_times_data[(city1, city2)]
    elif (city2, city1) in travel_times_data:
        travel_time = travel_times_data[(city2, city1)]
    elif city1 in cities and city2 in cities:
        # Interpolate travel time for user-added cities
        travel_time = estimate_travel_time(cities[city1], cities[city2])
        return travel_time  # Return the string directly for interpolated times
    else:
        return "N/A"

    # Ensure travel_time is an integer for predefined travel times
    hours = travel_time // 60
    minutes = travel_time % 60
    return f"{hours}h {minutes}m" if hours > 0 else f"{minutes} min"

# Function to dynamically adjust travel time label positions to avoid overlap with city labels
def adjust_travel_time_labels(ax, cities, connections):
    # Ensure only one travel time label is displayed
    existing_labels = set()
    for city1, city2 in connections:
        if city1 not in cities or city2 not in cities:
            continue

        travel_time = get_travel_time(city1, city2)
        if travel_time in existing_labels:
            continue  # Skip if the label already exists

        existing_labels.add(travel_time)

        # Calculate the midpoint of the line
        x1, y1 = cities[city1]
        x2, y2 = cities[city2]
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2

        # Draw the travel time label
        ax.text(mid_x, mid_y, travel_time, fontsize=8, fontfamily='sans-serif',
                fontweight='bold', color='black', bbox=dict(facecolor='white', edgecolor='none', boxstyle='round,pad=0.2'),
                zorder=11)

# Add debug visualization for label placement and explanation
# Function to adjust city labels and provide debug information

def adjust_city_labels(ax, cities, clusters, connections, debug=False):
    for city, (x, y) in cities.items():
        # Skip cities that are part of a cluster
        if any(city in cluster['cities'] for cluster in clusters):
            continue

        # Check if there are other cities on the same vertical axis
        same_vertical_cities = [other_city for other_city, (other_x, other_y) in cities.items() if abs(other_x - x) < 0.01 and other_city != city]

        if same_vertical_cities:
            # If there are cities on the same vertical axis, place the label to the right
            label_x = x + 0.2
            alignment = 'left'
            reason = "Placed to the right due to overlap on the vertical axis."
        else:
            # Otherwise, place the label to the left
            label_x = x - 0.2
            alignment = 'right'
            reason = "Placed to the left as no vertical overlap detected."

        # Draw the city label with adjusted alignment
        ax.text(label_x, y, city, fontsize=10, fontfamily='sans-serif',
                fontweight='bold', color='white', ha=alignment,
                bbox=dict(facecolor='darkgrey', edgecolor='none', boxstyle='round,pad=0.3'),
                zorder=10)

# Modify the update_plot function to preserve zoom unless reset_zoom is used
# Store the current zoom state globally
global current_zoom_bounds
current_zoom_bounds = None

# Ensure `filtered_states` is globally accessible
filtered_states = None  # Initialize as None globally

# Update the update_plot function to use the current zoom bounds if available
def update_plot(canvas, ax, fig):
    global current_zoom_bounds, filtered_states

    # Debugging: Log the current zoom bounds
    if current_zoom_bounds is not None:
        logging.debug(f"Restoring zoom bounds: {current_zoom_bounds}")
    else:
        logging.debug("No zoom bounds to restore. Defaulting to full map view.")

    ax.clear()
    ax.set_facecolor('#F5F5F5')
    germany.boundary.plot(ax=ax, linewidth=0.8, color='#CCCCCC')

    # Plot cities and connections
    for city, coord in cities.items():
        ax.plot(coord[0], coord[1], marker='o', markersize=12,
                markeredgecolor='black', markerfacecolor='white')

    for i, (city1, city2) in enumerate(connections):
        line = LineString([cities[city1], cities[city2]])
        color = connection_colors[i % len(connection_colors)]
        ax.plot(*line.xy, color=color, linewidth=2.5, linestyle='-', alpha=0.9)

    # Adjust travel time labels to avoid overlap
    adjust_travel_time_labels(ax, cities, connections)

    # Use the new congestion handling system
    clusters, clustered_cities = handle_congested_areas(ax, cities)

    # Call the adjust_city_labels function to apply label adjustments
    adjust_city_labels(ax, cities, clusters, connections)

    # Restore zoom bounds if available
    if current_zoom_bounds is not None and current_zoom_bounds.size > 0:
        ax.set_xlim(current_zoom_bounds[0], current_zoom_bounds[2])
        ax.set_ylim(current_zoom_bounds[1], current_zoom_bounds[3])
    else:
        ax.set_xlim(5, 15)
        ax.set_ylim(47, 55)

    # Debugging: Verify labels after update
    verify_labels_hidden()

    ax.axis('off')
    canvas.draw()

# Update the reset_zoom function to clear the current zoom bounds
def reset_zoom():
    global current_zoom_bounds
    logging.info("Reset zoom feature triggered.")
    current_zoom_bounds = None
    update_plot(canvas, ax, fig)
    logging.info("Zoom reset to full map view.")

# Update the zoom_into_states function to include log messages
def zoom_into_states():
    global current_zoom_bounds, filtered_states
    logging.info("Zoom into states feature triggered.")
    states = simpledialog.askstring("Zoom", "Enter German states to zoom into (comma-separated):")
    if not states:
        logging.warning("No states entered for zooming.")
        return
    state_list = [state.strip() for state in states.split(",")]
    logging.debug(f"States entered for zooming: {state_list}")

    # Filter the map to only include the selected states
    filtered_states = germany[germany['name'].isin(state_list)]
    if filtered_states.empty:
        logging.error("No matching states found for the entered names.")
        messagebox.showerror("Error", "No matching states found. Please enter valid German state names.")
        return

    logging.info("Matching states found. Proceeding with zoom.")

    # Ensure CRS consistency and resolve alignment issues
    filtered_states = filtered_states.to_crs(epsg=4326)
    logging.debug("CRS consistency ensured for filtered states.")

    ax.clear()
    ax.set_facecolor('#F5F5F5')
    # Clip the map to the selected states to hide anything outside their borders
    clipped_map = gpd.clip(germany, filtered_states.geometry)
    clipped_map.boundary.plot(ax=ax, linewidth=0.8, color='#CCCCCC')
    logging.info("Map clipped to selected states.")

    # Plot cities and connections within the selected states
    for city, coord in cities.items():
        point = GeoSeries([gpd.points_from_xy([coord[0]], [coord[1]])[0]], crs="EPSG:4326")
        label_id = city_ids[city]  # Use the unique label ID for each city

        # Check if the city is within the bounding box of any selected state
        within_bounding_box = filtered_states['bounding_box'].apply(
            lambda bbox: bbox[0] <= coord[0] <= bbox[2] and bbox[1] <= coord[1] <= bbox[3]
        ).any()

        if within_bounding_box:
            ax.plot(coord[0], coord[1], marker='o', markersize=12,
                    markeredgecolor='black', markerfacecolor='white')
            ax.text(coord[0], coord[1], city, fontsize=10, fontfamily='sans-serif',
                    fontweight='bold', color='white',
                    bbox=dict(facecolor='darkgrey', edgecolor='none', boxstyle='round,pad=0.3'),
                    zorder=10, gid=label_id)  # Assign the label ID to the text object
            logging.debug(f"City '{city}' plotted within the selected states.")
        else:
            # Hide city label
            for text in ax.texts:
                if text.get_gid() == label_id:
                    text.set_visible(False)
                    logging.debug(f"City label for '{city}' hidden as it is outside the selected states.")

            # Hide time labels associated with the city
            for text in ax.texts:
                if text.get_text() in travel_times_data and not within_bounding_box:
                    text.set_visible(False)
                    logging.debug(f"Time label for '{city}' hidden as it is outside the selected states.")

    for i, (city1, city2) in enumerate(connections):
        if city1 in cities and city2 in cities:
            line = LineString([cities[city1], cities[city2]])
            point1 = GeoSeries([gpd.points_from_xy([cities[city1][0]], [cities[city1][1]])[0]], crs="EPSG:4326")
            point2 = GeoSeries([gpd.points_from_xy([cities[city2][0]], [cities[city2][1]])[0]], crs="EPSG:4326")
            if any(filtered_states.geometry.contains(point1.iloc[0])) and any(filtered_states.geometry.contains(point2.iloc[0])):
                color = connection_colors[i % len(connection_colors)]
                ax.plot(*line.xy, color=color, linewidth=2.5, linestyle='-', alpha=0.9)
                logging.debug(f"Connection between '{city1}' and '{city2}' plotted within the selected states.")

    # Set and store the current zoom bounds
    current_zoom_bounds = filtered_states.total_bounds
    ax.set_xlim(current_zoom_bounds[0], current_zoom_bounds[2])
    ax.set_ylim(current_zoom_bounds[1], current_zoom_bounds[3])
    logging.info(f"Zoom bounds set to: {current_zoom_bounds}")
    ax.axis('off')
    canvas.draw()
    logging.info("Zoom into states completed.")

# Update the verify_labels_hidden function to not require arguments
def verify_labels_hidden():
    global filtered_states
    if filtered_states is None:
        logging.warning("No filtered states available to verify labels.")
        return

    for text in ax.texts:
        label_coords = (text.get_position()[0], text.get_position()[1])
        point = GeoSeries([gpd.points_from_xy([label_coords[0]], [label_coords[1]])[0]], crs="EPSG:4326")

        # Debugging: Log the label being checked
        logging.debug(f"Checking label '{text.get_text()}' at coordinates {label_coords}")

        if not filtered_states.geometry.apply(lambda geom: point.iloc[0].within(geom)).any():
            text.set_visible(False)  # Hide the label
            logging.debug(f"Label '{text.get_text()}' is outside the selected states and has been hidden.")
        else:
            text.set_visible(True)  # Ensure the label is visible if within the states
            logging.debug(f"Label '{text.get_text()}' is within the selected states and remains visible.")

# Function to export the plot as a DIN A4 PDF
def export_plot_as_pdf(fig):
    export_path = os.path.join("export", "Plot_DIN_A4.pdf")
    with PdfPages(export_path) as pdf:
        fig.set_size_inches(8.27, 11.69)  # Set size to DIN A4 dimensions in inches
        add_legend(ax, fig)  # Add the legend only during export
        pdf.savefig(fig, bbox_inches='tight')
    messagebox.showinfo("Export Success", f"Plot exported successfully to {export_path}.")

# Function to save the current cities and connections to a .trv file
def save_routes():
    save_path = filedialog.asksaveasfilename(defaultextension=".trv", filetypes=[("TRV files", "*.trv"), ("All files", "*.*")])
    if not save_path:
        return
    try:
        with open(save_path, 'w') as file:
            json.dump({"cities": cities, "connections": connections}, file)
        messagebox.showinfo("Success", f"Routes saved successfully to {save_path}.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save routes: {str(e)}")

# Function to load cities and connections from a .trv file
def load_routes():
    load_path = filedialog.askopenfilename(filetypes=[("TRV files", "*.trv"), ("All files", "*.*")])
    if not load_path:
        return
    try:
        with open(load_path, 'r') as file:
            data = json.load(file)
            global cities, connections
            cities = data.get("cities", {})
            connections = data.get("connections", [])
        messagebox.showinfo("Success", f"Routes loaded successfully from {load_path}.")
        if 'canvas' in globals() and 'ax' in globals() and 'fig' in globals():
            update_plot(canvas, ax, fig)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load routes: {str(e)}")

# Function to add a legend for the map, showing route chains and their total travel times
def add_legend(ax, fig):
    # Clear any existing legends
    for child in fig.get_children():
        if isinstance(child, plt.Axes) and child != ax:
            child.remove()

    # Group connections into separate chains
    chains = []
    visited = set()

    def dfs(city, chain):
        for conn in connections:
            if city in conn:
                other_city = conn[1] if conn[0] == city else conn[0]
                if other_city not in visited:
                    visited.add(other_city)
                    chain.append((city, other_city))
                    dfs(other_city, chain)

    for city in cities:
        if city not in visited:
            visited.add(city)
            chain = []
            dfs(city, chain)
            if chain:
                chains.append(chain)

    # Define the starting position for the legend items
    x_start = 0.1  # Start position for the first legend
    y_start = -0.1  # Start below the map
    x_increment = 0.3  # Horizontal spacing between legends
    y_decrement = 0.05  # Vertical spacing between items in a legend

    for chain_index, chain in enumerate(chains):
        # Calculate the x and y positions for the current chain
        x_position = x_start + (chain_index * x_increment)
        chain_y_start = y_start

        total_travel_time = 0  # Initialize total travel time for the chain

        # Draw the legend for this chain
        for i, (city1, city2) in enumerate(chain):
            # Draw the line connecting the stations
            if i > 0:
                ax.plot([x_position, x_position], [chain_y_start + y_decrement, chain_y_start],
                        color=connection_colors[i % len(connection_colors)], linewidth=2.5, transform=ax.transAxes, clip_on=False)

            # Draw the station symbol (white dot with black outline)
            ax.plot(x_position, chain_y_start, marker='o', markersize=10,
                    markeredgecolor='black', markerfacecolor='white', transform=ax.transAxes, clip_on=False)

            # Add the city label
            ax.text(x_position + 0.05, chain_y_start, city1,
                    fontsize=8, fontfamily='sans-serif', ha='left', transform=ax.transAxes, clip_on=False, wrap=True, bbox=dict(facecolor='white', edgecolor='none', boxstyle='round,pad=0.2'))

            # Calculate and accumulate travel time for the chain
            travel_time = get_travel_time(city1, city2)
            if travel_time != "N/A":
                hours, minutes = 0, 0
                if "h" in travel_time:
                    time_parts = travel_time.split("h")
                    hours = int(time_parts[0].strip())
                    minutes = int(time_parts[1].replace("m", "").strip()) if "m" in time_parts[1] else 0
                elif "min" in travel_time:
                    minutes = int(travel_time.replace("min", "").strip())
                total_travel_time += hours * 60 + minutes

            # Decrement the y position for the next item
            chain_y_start -= y_decrement

        # Add a separator or title for the chain
        total_hours = total_travel_time // 60
        total_minutes = total_travel_time % 60
        total_time_str = f"Total: {total_hours}h {total_minutes}m" if total_hours > 0 else f"Total: {total_minutes} min"
        ax.text(x_position, chain_y_start - 0.05, f"Route {chain_index + 1} ({total_time_str})",
                fontsize=10, fontfamily='sans-serif', ha='left', transform=ax.transAxes, clip_on=False, fontweight='bold', bbox=dict(facecolor='lightgrey', edgecolor='none', boxstyle='round,pad=0.3'))

# Update the integrate_ui_with_plot function to include the export feature
def integrate_ui_with_plot():
    # Create a new window for the integrated UI and plot
    integrated_window = tk.Toplevel(root)
    integrated_window.title("Train Route Visualizer")

    # Create a menu bar
    menu_bar = tk.Menu(integrated_window)
    integrated_window.config(menu=menu_bar)

    # Reorganize menus to make 'File' the leftmost menu
    file_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="File", menu=file_menu)
    file_menu.add_command(label="Save Routes", command=save_routes)
    file_menu.add_command(label="Load Routes", command=load_routes)

    city_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="City", menu=city_menu)
    city_menu.add_command(label="Add City", command=lambda: [add_city(), update_plot(canvas, ax, fig)])
    city_menu.add_command(label="Edit City", command=lambda: [edit_city_dialog(), update_plot(canvas, ax, fig)])
    city_menu.add_command(label="Remove City", command=lambda: [remove_city_dialog(), update_plot(canvas, ax, fig)])
    city_menu.add_command(label="Remove Default Cities", command=lambda: [remove_default_cities(), update_plot(canvas, ax, fig)])

    route_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="Connections", menu=route_menu)
    route_menu.add_command(label="Add Connection", command=lambda: [add_connection_dialog(), update_plot(canvas, ax, fig)])
    route_menu.add_command(label="Remove Connection", command=lambda: [remove_route_dialog(), update_plot(canvas, ax, fig)])

    export_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="Export", menu=export_menu)
    export_menu.add_command(label="Export as DIN A4 PDF", command=lambda: export_plot_as_pdf(fig))

    # Add a menu entry to zoom into one or several German states and reset zoom
    zoom_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="Zoom", menu=zoom_menu)

    # Function to zoom into selected states
    def zoom_into_states():
        global current_zoom_bounds, filtered_states
        logging.info("Zoom into states feature triggered.")
        states = simpledialog.askstring("Zoom", "Enter German states to zoom into (comma-separated):")
        if not states:
            logging.warning("No states entered for zooming.")
            return
        state_list = [state.strip() for state in states.split(",")]
        logging.debug(f"States entered for zooming: {state_list}")

        # Filter the map to only include the selected states
        filtered_states = germany[germany['name'].isin(state_list)]
        if filtered_states.empty:
            logging.error("No matching states found for the entered names.")
            messagebox.showerror("Error", "No matching states found. Please enter valid German state names.")
            return

        logging.info("Matching states found. Proceeding with zoom.")

        # Ensure CRS consistency and resolve alignment issues
        filtered_states = filtered_states.to_crs(epsg=4326)
        logging.debug("CRS consistency ensured for filtered states.")

        ax.clear()
        ax.set_facecolor('#F5F5F5')
        # Clip the map to the selected states to hide anything outside their borders
        clipped_map = gpd.clip(germany, filtered_states.geometry)
        clipped_map.boundary.plot(ax=ax, linewidth=0.8, color='#CCCCCC')
        logging.info("Map clipped to selected states.")

        # Plot cities and connections within the selected states
        for city, coord in cities.items():
            point = GeoSeries([gpd.points_from_xy([coord[0]], [coord[1]])[0]], crs="EPSG:4326")
            label_id = city_ids[city]  # Use the unique label ID for each city

            # Check if the city is within the bounding box of any selected state
            within_bounding_box = filtered_states['bounding_box'].apply(
                lambda bbox: bbox[0] <= coord[0] <= bbox[2] and bbox[1] <= coord[1] <= bbox[3]
            ).any()

            if within_bounding_box:
                ax.plot(coord[0], coord[1], marker='o', markersize=12,
                        markeredgecolor='black', markerfacecolor='white')
                ax.text(coord[0], coord[1], city, fontsize=10, fontfamily='sans-serif',
                        fontweight='bold', color='white',
                        bbox=dict(facecolor='darkgrey', edgecolor='none', boxstyle='round,pad=0.3'),
                        zorder=10, gid=label_id)  # Assign the label ID to the text object
                logging.debug(f"City '{city}' plotted within the selected states.")
            else:
                # Hide city label
                for text in ax.texts:
                    if text.get_gid() == label_id:
                        text.set_visible(False)
                        logging.debug(f"City label for '{city}' hidden as it is outside the selected states.")

                # Hide time labels associated with the city
                for text in ax.texts:
                    if text.get_text() in travel_times_data and not within_bounding_box:
                        text.set_visible(False)
                        logging.debug(f"Time label for '{city}' hidden as it is outside the selected states.")

        for i, (city1, city2) in enumerate(connections):
            if city1 in cities and city2 in cities:
                line = LineString([cities[city1], cities[city2]])
                point1 = GeoSeries([gpd.points_from_xy([cities[city1][0]], [cities[city1][1]])[0]], crs="EPSG:4326")
                point2 = GeoSeries([gpd.points_from_xy([cities[city2][0]], [cities[city2][1]])[0]], crs="EPSG:4326")
                if any(filtered_states.geometry.contains(point1.iloc[0])) and any(filtered_states.geometry.contains(point2.iloc[0])):
                    color = connection_colors[i % len(connection_colors)]
                    ax.plot(*line.xy, color=color, linewidth=2.5, linestyle='-', alpha=0.9)
                    logging.debug(f"Connection between '{city1}' and '{city2}' plotted within the selected states.")

        # Set and store the current zoom bounds
        current_zoom_bounds = filtered_states.total_bounds
        ax.set_xlim(current_zoom_bounds[0], current_zoom_bounds[2])
        ax.set_ylim(current_zoom_bounds[1], current_zoom_bounds[3])
        logging.info(f"Zoom bounds set to: {current_zoom_bounds}")
        ax.axis('off')
        canvas.draw()
        logging.info("Zoom into states completed.")

    # Function to reset zoom to the full map
    def reset_zoom():
        global current_zoom_bounds
        logging.info("Reset zoom feature triggered.")
        current_zoom_bounds = None
        update_plot(canvas, ax, fig)
        logging.info("Zoom reset to full map view.")

    zoom_menu.add_command(label="Zoom into States", command=zoom_into_states)
    zoom_menu.add_command(label="Reset Zoom", command=reset_zoom)

    # Add a menu entry to manually update the plot
    menu_bar.add_command(label="Update Plot", command=lambda: [update_plot(canvas, ax, fig), reset_zoom()])

    # Add a new menu entry for "Update Plot Zoomed In"
    menu_bar.add_command(label="Update Plot Zoomed In", command=lambda: update_plot(canvas, ax, fig))

    # Create a frame for the plot
    plot_frame = tk.Frame(integrated_window)
    plot_frame.pack(fill=tk.BOTH, expand=True)

    # Ensure canvas, ax, and fig are globally accessible
    global canvas, ax, fig
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_facecolor('#F5F5F5')
    germany.boundary.plot(ax=ax, linewidth=0.8, color='#CCCCCC')

    canvas = FigureCanvasTkAgg(fig, master=plot_frame)
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.pack(fill=tk.BOTH, expand=True)

    # Initial plot rendering
    update_plot(canvas, ax, fig)

    # Bind the close event of the integrated UI to terminate the script
    integrated_window.protocol("WM_DELETE_WINDOW", lambda: [integrated_window.destroy(), root.destroy()])

# Add a button to open the integrated UI and plot window
integrate_ui_button = tk.Button(root, text="Open Integrated UI and Plot", command=integrate_ui_with_plot)
integrate_ui_button.pack(pady=5)

# Automatically open the integrated UI and minimize the old UI
def open_integrated_ui():
    root.withdraw()  # Minimize or hide the old UI
    integrate_ui_with_plot()

# Automatically call the function to open the integrated UI
open_integrated_ui()

# Create the GUI
add_city_button = tk.Button(root, text="Add City", command=add_city)
add_city_button.pack(pady=5)
plot_map_button = tk.Button(root, text="Plot Map", command=plot_map)
plot_map_button.pack(pady=5)
edit_city_button = tk.Button(root, text="Edit City", command=edit_city_dialog)
edit_city_button.pack(pady=5)
remove_city_button = tk.Button(root, text="Remove City", command=remove_city_dialog)
remove_city_button.pack(pady=5)
remove_default_cities_button = tk.Button(root, text="Remove Default Cities", command=remove_default_cities)
remove_default_cities_button.pack(pady=5)
remove_route_button = tk.Button(root, text="Remove Route", command=remove_route_dialog)
remove_route_button.pack(pady=5)

# Remove font-related log messages by adjusting Matplotlib's logging level
import logging
logging.getLogger('matplotlib').setLevel(logging.WARNING)

root.mainloop()
