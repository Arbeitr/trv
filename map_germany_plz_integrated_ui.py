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

# Modified function to add a new city using the postal code (Postleitzahl)
def add_city():
    postal_code = simpledialog.askstring("Add City", "Enter Postleitzahl:")
    if not postal_code:
        return
    try:
        # Create a pgeocode Nominatim object for Germany
        nomi = pgeocode.Nominatim('de')
        info = nomi.query_postal_code(postal_code)
        # If postal code not found, latitude and longitude will be NaN
        if math.isnan(info.latitude) or math.isnan(info.longitude):
            messagebox.showerror("Error", "Postal code not found. Please enter a valid Postleitzahl.")
            return
        # Use the place name provided by pgeocode; if absent, default to the postal code
        city_name = info.place_name if info.place_name else postal_code
        cities[city_name] = (info.longitude, info.latitude)
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
    city1_var.set(list(cities.keys())[0])
    city1_menu = tk.OptionMenu(add_window, city1_var, *cities.keys())
    city1_menu.grid(row=0, column=1, padx=5, pady=5)

    tk.Label(add_window, text="Select the second city:").grid(row=0, column=2, padx=5, pady=5)
    city2_var = tk.StringVar(add_window)
    city2_var.set(list(cities.keys())[1])
    city2_menu = tk.OptionMenu(add_window, city2_var, *cities.keys())
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
        if 'canvas' in globals() and 'ax' in globals():
            update_plot(canvas, ax)

    tk.Button(add_window, text="Add Connection", command=create_connection).grid(row=1, column=0, columnspan=4, pady=10)

# Ensure the button is defined before updating its configuration
add_connection_button = tk.Button(root, text="Add Connection")
add_connection_button.pack(pady=5)
add_connection_button.config(command=add_connection_dialog)

# Function to check and adjust label positions to avoid overlap
def adjust_label_positions(labels):
    adjusted_positions = {}
    for city, (x, y) in labels.items():
        for other_city, (other_x, other_y) in adjusted_positions.items():
            if abs(x - other_x) < 0.5 and abs(y - other_y) < 0.5:
                if y > other_y:
                    y += 0.2
                else:
                    adjusted_positions[other_city] = (other_x, other_y + 0.2)
        adjusted_positions[city] = (x, y)
    return adjusted_positions

# Function to plot the map
def plot_map():
    fig, ax = plt.subplots(figsize=(20, 20))
    ax.set_facecolor('#F5F5F5')
    germany.boundary.plot(ax=ax, linewidth=0.8, color='#CCCCCC')
    # Create labels and adjust positions to prevent overlap
    labels = {city: (coord[0] + 0.2, coord[1]) for city, coord in cities.items()}
    adjusted_labels = adjust_label_positions(labels)
    for city, coord in cities.items():
        ax.plot(coord[0], coord[1], marker='o', markersize=12,
                markeredgecolor='black', markerfacecolor='white')
        label_x, label_y = adjusted_labels[city]
        ax.text(label_x, label_y, city, fontsize=10, fontfamily='sans-serif',
                fontweight='bold', color='white',
                bbox=dict(facecolor='darkgrey', edgecolor='none', boxstyle='round,pad=0.3'),
                zorder=10)
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

# Function to update the plot dynamically
def update_plot(canvas, ax):
    ax.clear()
    ax.set_facecolor('#F5F5F5')
    germany.boundary.plot(ax=ax, linewidth=0.8, color='#CCCCCC')

    # Plot cities and connections
    labels = {city: (coord[0] + 0.2, coord[1]) for city, coord in cities.items()}
    adjusted_labels = adjust_label_positions(labels)
    for city, coord in cities.items():
        ax.plot(coord[0], coord[1], marker='o', markersize=12,
                markeredgecolor='black', markerfacecolor='white')
        label_x, label_y = adjusted_labels[city]
        ax.text(label_x, label_y, city, fontsize=10, fontfamily='sans-serif',
                fontweight='bold', color='white',
                bbox=dict(facecolor='darkgrey', edgecolor='none', boxstyle='round,pad=0.3'),
                zorder=10)
    for i, (city1, city2) in enumerate(connections):
        line = LineString([cities[city1], cities[city2]])
        color = connection_colors[i % len(connection_colors)]
        ax.plot(*line.xy, color=color, linewidth=2.5, linestyle='-', alpha=0.9)

    ax.set_xlim(5, 15)
    ax.set_ylim(47, 55)
    ax.axis('off')
    canvas.draw()

# Function to export the plot as a DIN A4 PDF
def export_plot_as_pdf(fig):
    export_path = os.path.join("export", "Plot_DIN_A4.pdf")
    with PdfPages(export_path) as pdf:
        fig.set_size_inches(8.27, 11.69)  # Set size to DIN A4 dimensions in inches
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
        if 'canvas' in globals() and 'ax' in globals():
            update_plot(canvas, ax)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load routes: {str(e)}")

# Modify the integrate_ui_with_plot function to include the export feature
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
    city_menu.add_command(label="Add City", command=lambda: [add_city(), update_plot(canvas, ax)])
    city_menu.add_command(label="Edit City", command=lambda: [edit_city_dialog(), update_plot(canvas, ax)])
    city_menu.add_command(label="Remove City", command=lambda: [remove_city_dialog(), update_plot(canvas, ax)])
    city_menu.add_command(label="Remove Default Cities", command=lambda: [remove_default_cities(), update_plot(canvas, ax)])

    route_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="Connections", menu=route_menu)
    route_menu.add_command(label="Add Connection", command=lambda: [add_connection_dialog(), update_plot(canvas, ax)])
    route_menu.add_command(label="Remove Connection", command=lambda: [remove_route_dialog(), update_plot(canvas, ax)])

    export_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="Export", menu=export_menu)
    export_menu.add_command(label="Export as DIN A4 PDF", command=lambda: export_plot_as_pdf(fig))

    # Add a menu entry to manually update the plot
    menu_bar.add_command(label="Update Plot", command=lambda: update_plot(canvas, ax))

    # Create a frame for the plot
    plot_frame = tk.Frame(integrated_window)
    plot_frame.pack(fill=tk.BOTH, expand=True)

    # Generate the plot and embed it in the Tkinter window
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_facecolor('#F5F5F5')
    germany.boundary.plot(ax=ax, linewidth=0.8, color='#CCCCCC')

    canvas = FigureCanvasTkAgg(fig, master=plot_frame)
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.pack(fill=tk.BOTH, expand=True)

    # Initial plot rendering
    update_plot(canvas, ax)

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
root.mainloop()
