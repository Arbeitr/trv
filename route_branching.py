"""
Route Branching System for Train Route Visualizer
Implements DAG-based route branching with split/merge operations and history tracking
"""

import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from tkinter.font import Font
import logging
import copy
import uuid
import math
import functools
from collections import defaultdict, deque
from typing import Dict, List, Tuple, Set, Optional, Any, Callable
import weakref
import time

# Caching decorator for expensive calculations
from functools import lru_cache

# Constants for UI and rendering
BRANCH_COLORS = [
    "#3498db", "#e74c3c", "#2ecc71", "#f39c12", 
    "#9b59b6", "#1abc9c", "#d35400", "#34495e",
]
BRANCH_LINE_STYLES = [
    (0, ()), # solid
    (0, (5, 5)), # dashed
    (0, (1, 1)), # dotted
    (0, (3, 5, 1, 5)), # dashdotted
]

# Maximum history entries before cleanup
MAX_HISTORY_SIZE = 100

class RouteVersion:
    """Represents a version of route data for undo/redo functionality"""
    def __init__(self, route_data, description=""):
        self.data = copy.deepcopy(route_data) 
        self.timestamp = time.time()
        self.description = description
        self.id = str(uuid.uuid4())
    
    def __str__(self):
        return f"RouteVersion({self.description}, {self.timestamp})"

class RouteBranch:
    """Represents a branch in the route system"""
    def __init__(self, name, parent_id=None):
        self.id = str(uuid.uuid4())
        self.name = name
        self.parent_id = parent_id
        self.child_ids = []
        self.route_segments = []  # List of (city1, city2) tuples
        self.color = None  # Will be assigned by the branch manager
        self.line_style = None  # Will be assigned by the branch manager
        self.metadata = {}  # Custom metadata for this branch
    
    def add_segment(self, city1, city2):
        """Add a route segment to this branch"""
        segment = (city1, city2)
        if segment not in self.route_segments and (city2, city1) not in self.route_segments:
            self.route_segments.append(segment)
            return True
        return False
    
    def contains_city(self, city):
        """Check if a city exists in any segment of this branch"""
        for segment in self.route_segments:
            if city in segment:
                return True
        return False
    
    def get_connected_cities(self, city):
        """Get all cities directly connected to the given city in this branch"""
        connected = []
        for c1, c2 in self.route_segments:
            if c1 == city:
                connected.append(c2)
            elif c2 == city:
                connected.append(c1)
        return connected

    def __str__(self):
        return f"Branch({self.name}, segments={len(self.route_segments)})"

class RouteManager:
    """Manages route branches and version history"""
    def __init__(self, route_data):
        self.route_data = route_data
        self.branches = {}  # id -> RouteBranch
        self.history = []  # List of RouteVersion objects
        self.history_position = -1  # Current position in history
        self.active_branch_id = None
        self._color_index = 0
        self._style_index = 0
        
        # Initialize with a main branch from current route data
        self.initialize_branches()
        
        # Save initial state
        self.save_state("Initial state")
    
    def initialize_branches(self):
        """Initialize branches from existing route chains"""
        chains = self.route_data.get_route_chains()
        
        # Create main branch and add all current connections
        main_branch = RouteBranch("Main")
        main_branch.color = BRANCH_COLORS[0]
        main_branch.line_style = BRANCH_LINE_STYLES[0]
        
        for chain_idx, chain in enumerate(chains):
            branch_name = self.route_data.route_chain_names.get(str(chain_idx), f"Route {chain_idx + 1}")
            branch = RouteBranch(branch_name)
            
            # Assign color and line style
            branch.color = BRANCH_COLORS[self._color_index % len(BRANCH_COLORS)]
            branch.line_style = BRANCH_LINE_STYLES[self._style_index % len(BRANCH_LINE_STYLES)]
            self._color_index += 1
            self._style_index += 1
            
            # Add segments from this chain
            for segment in chain:
                branch.add_segment(segment[0], segment[1])
            
            self.branches[branch.id] = branch
            
            # Set as active if it's the first branch
            if chain_idx == 0:
                self.active_branch_id = branch.id
    
    def save_state(self, description=""):
        """Save current state to history"""
        # If we've gone back in history and are creating a new branch
        if self.history_position < len(self.history) - 1:
            # Remove all history after current position
            self.history = self.history[:self.history_position + 1]
        
        # Create new version
        version = RouteVersion(self.route_data, description)
        
        # Add to history
        self.history.append(version)
        self.history_position = len(self.history) - 1
        
        # Trim history if it's too long
        if len(self.history) > MAX_HISTORY_SIZE:
            self.history = self.history[-MAX_HISTORY_SIZE:]
            self.history_position = len(self.history) - 1
    
    def can_undo(self):
        """Check if undo is available"""
        return self.history_position > 0
    
    def can_redo(self):
        """Check if redo is available"""
        return self.history_position < len(self.history) - 1
    
    def undo(self):
        """Revert to previous state"""
        if not self.can_undo():
            return False, "Nothing to undo"
        
        self.history_position -= 1
        version = self.history[self.history_position]
        
        # Apply previous state
        self.route_data = copy.deepcopy(version.data)
        
        return True, f"Undid: {version.description}"
    
    def redo(self):
        """Redo previously undone action"""
        if not self.can_redo():
            return False, "Nothing to redo"
        
        self.history_position += 1
        version = self.history[self.history_position]
        
        # Apply next state
        self.route_data = copy.deepcopy(version.data)
        
        return True, f"Redid: {version.description}"
    
    def split_route(self, branch_id, city):
        """Split a route at the given city, creating two branches"""
        if branch_id not in self.branches:
            return False, "Invalid branch"
        
        parent_branch = self.branches[branch_id]
        
        # Verify city exists in the branch
        if not parent_branch.contains_city(city):
            return False, f"City {city} not found in branch {parent_branch.name}"
        
        # Find all cities connected to the split point
        connected_cities = parent_branch.get_connected_cities(city)
        if len(connected_cities) < 2:
            return False, f"City {city} is not a valid split point (need at least 2 connections)"
        
        # Create two new branches
        branch1 = RouteBranch(f"{parent_branch.name}-A", parent_branch.id)
        branch2 = RouteBranch(f"{parent_branch.name}-B", parent_branch.id)
        
        # Assign colors and styles
        branch1.color = BRANCH_COLORS[self._color_index % len(BRANCH_COLORS)]
        branch1.line_style = BRANCH_LINE_STYLES[self._style_index % len(BRANCH_LINE_STYLES)]
        self._color_index += 1
        self._style_index = (self._style_index + 1) % len(BRANCH_LINE_STYLES)
        
        branch2.color = BRANCH_COLORS[self._color_index % len(BRANCH_COLORS)]
        branch2.line_style = BRANCH_LINE_STYLES[self._style_index % len(BRANCH_LINE_STYLES)]
        self._color_index += 1
        self._style_index = (self._style_index + 1) % len(BRANCH_LINE_STYLES)
        
        # Add to branch collection
        self.branches[branch1.id] = branch1
        self.branches[branch2.id] = branch2
        
        # Update parent's child references
        parent_branch.child_ids.extend([branch1.id, branch2.id])
        
        # Find connected components after removing the split city
        visited = set()
        components = []
        
        def dfs(start_city, component):
            if start_city in visited or start_city == city:
                return
            visited.add(start_city)
            component.add(start_city)
            
            for c1, c2 in parent_branch.route_segments:
                if c1 == start_city and c2 not in visited and c2 != city:
                    dfs(c2, component)
                elif c2 == start_city and c1 not in visited and c1 != city:
                    dfs(c1, component)
        
        # Start DFS from each connected city
        for connected in connected_cities:
            if connected not in visited:
                component = set()
                dfs(connected, component)
                if component:  # Only add non-empty components
                    components.append(component)
        
        # If we don't have at least 2 components, the split doesn't make sense
        if len(components) < 2:
            return False, "Cannot split at this city - would not create separate branches"
        
        # Distribute segments to the new branches
        for segment in parent_branch.route_segments:
            c1, c2 = segment
            
            # Check which component this segment belongs to
            if city in segment:
                # This segment connects to the split city
                if c1 == city:
                    for i, comp in enumerate(components):
                        if c2 in comp:
                            # Add to appropriate branch based on component
                            branch = branch1 if i == 0 else branch2
                            branch.add_segment(c1, c2)
                            break
                elif c2 == city:
                    for i, comp in enumerate(components):
                        if c1 in comp:
                            # Add to appropriate branch based on component
                            branch = branch1 if i == 0 else branch2
                            branch.add_segment(c1, c2)
                            break
            else:
                # This segment doesn't connect to the split city
                # Find which component it belongs to
                for i, comp in enumerate(components):
                    if c1 in comp and c2 in comp:
                        # Add to appropriate branch based on component
                        branch = branch1 if i == 0 else branch2
                        branch.add_segment(c1, c2)
                        break
        
        # Set one of the new branches as active
        self.active_branch_id = branch1.id
        
        # Save state for undo/redo
        self.save_state(f"Split route at {city}")
        
        return True, f"Split route into {branch1.name} and {branch2.name} at {city}"
    
    def merge_branches(self, branch1_id, branch2_id, city1, city2):
        """Merge two branches, connecting them at the specified cities"""
        if branch1_id not in self.branches or branch2_id not in self.branches:
            return False, "Invalid branch(es)"
        
        branch1 = self.branches[branch1_id]
        branch2 = self.branches[branch2_id]
        
        # Verify cities exist in respective branches
        if not branch1.contains_city(city1):
            return False, f"City {city1} not found in branch {branch1.name}"
        if not branch2.contains_city(city2):
            return False, f"City {city2} not found in branch {branch2.name}"
        
        # Create new merged branch
        merged_branch = RouteBranch(f"{branch1.name}-{branch2.name}-merged")
        
        # Copy segments from both branches
        for segment in branch1.route_segments:
            merged_branch.add_segment(segment[0], segment[1])
        
        for segment in branch2.route_segments:
            merged_branch.add_segment(segment[0], segment[1])
        
        # Add the connecting segment
        merged_branch.add_segment(city1, city2)
        
        # Assign color and style
        merged_branch.color = BRANCH_COLORS[self._color_index % len(BRANCH_COLORS)]
        merged_branch.line_style = BRANCH_LINE_STYLES[self._style_index % len(BRANCH_LINE_STYLES)]
        self._color_index += 1
        self._style_index = (self._style_index + 1) % len(BRANCH_LINE_STYLES)
        
        # Add to branch collection
        self.branches[merged_branch.id] = merged_branch
        
        # Set merged branch as active
        self.active_branch_id = merged_branch.id
        
        # Set this branch as a child of the merged branches
        branch1.child_ids.append(merged_branch.id)
        branch2.child_ids.append(merged_branch.id)
        
        # Set parent branches
        merged_branch.parent_id = branch1.id  # Primary parent
        merged_branch.metadata["secondary_parent"] = branch2.id
        
        # Save state for undo/redo
        self.save_state(f"Merged {branch1.name} and {branch2.name}")
        
        return True, f"Merged branches into {merged_branch.name}"
    
    def update_route_data(self):
        """Update the main route_data object with active branch data"""
        if self.active_branch_id not in self.branches:
            return False, "No active branch selected"
        
        active_branch = self.branches[self.active_branch_id]
        
        # Clear existing connections in route data
        self.route_data.connections.clear()
        
        # Add connections from active branch
        for city1, city2 in active_branch.route_segments:
            if (city1, city2) not in self.route_data.connections and (city2, city1) not in self.route_data.connections:
                self.route_data.connections.append((city1, city2))
        
        # Save state
        self.save_state("Updated route data from active branch")
        
        return True, "Route data updated from active branch"

    def get_branch_tree(self):
        """Return a representation of the branch tree structure for visualization"""
        tree = defaultdict(list)
        
        # Build parent->children mapping
        for branch_id, branch in self.branches.items():
            if branch.parent_id:
                tree[branch.parent_id].append(branch_id)
        
        # Find root branches (those without parents)
        roots = [branch_id for branch_id, branch in self.branches.items() if not branch.parent_id]
        
        return roots, tree
    
    @lru_cache(maxsize=128)
    def get_branch_segments_cached(self, branch_id):
        """Get segments for a branch (with caching for performance)"""
        if branch_id in self.branches:
            return tuple(self.branches[branch_id].route_segments)
        return tuple()


class BranchingDialog(tk.Toplevel):
    """Dialog for managing route branches with split/merge operations"""
    def __init__(self, parent, route_data, map_plotter):
        super().__init__(parent)
        self.title("Route Branch Manager")
        self.geometry("800x600")
        self.minsize(600, 400)
        
        self.route_data = route_data
        self.map_plotter = map_plotter
        self.parent = parent
        
        # Create route manager
        self.route_manager = RouteManager(route_data)
        
        # Create UI elements
        self.create_widgets()
        
        # Set up event bindings
        self.setup_bindings()
        
        # Initialize UI state
        self.refresh_branch_list()
        self.update_preview()
    
    def create_widgets(self):
        """Create all UI components"""
        # Main layout - split into left panel (controls) and right panel (preview)
        self.paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel - controls
        self.left_frame = ttk.Frame(self.paned)
        self.paned.add(self.left_frame, weight=1)
        
        # Right panel - preview
        self.right_frame = ttk.Frame(self.paned)
        self.paned.add(self.right_frame, weight=2)
        
        # Create tabs for different operations
        self.notebook = ttk.Notebook(self.left_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Split tab
        self.split_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.split_tab, text="Split Route")
        
        # Merge tab
        self.merge_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.merge_tab, text="Merge Routes")
        
        # Setup each tab
        self._setup_split_tab()
        self._setup_merge_tab()
        
        # Bottom control panel (common buttons)
        self.bottom_frame = ttk.Frame(self.left_frame)
        self.bottom_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Undo/Redo buttons
        self.history_frame = ttk.Frame(self.bottom_frame)
        self.history_frame.pack(fill=tk.X, pady=5)
        
        self.undo_button = ttk.Button(self.history_frame, text="Undo", command=self.undo_action)
        self.undo_button.pack(side=tk.LEFT, padx=5)
        
        self.redo_button = ttk.Button(self.history_frame, text="Redo", command=self.redo_action)
        self.redo_button.pack(side=tk.LEFT, padx=5)
        
        # Apply/Cancel buttons
        self.button_frame = ttk.Frame(self.bottom_frame)
        self.button_frame.pack(fill=tk.X, pady=10)
        
        self.apply_button = ttk.Button(self.button_frame, text="Apply Changes", command=self.apply_changes)
        self.apply_button.pack(side=tk.RIGHT, padx=5)
        
        self.cancel_button = ttk.Button(self.button_frame, text="Cancel", command=self.cancel)
        self.cancel_button.pack(side=tk.RIGHT, padx=5)
        
        # Preview canvas
        self.preview_frame = ttk.LabelFrame(self.right_frame, text="Route Preview")
        self.preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.canvas = tk.Canvas(self.preview_frame, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Zoom controls for preview
        self.zoom_frame = ttk.Frame(self.preview_frame)
        self.zoom_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.zoom_in_button = ttk.Button(self.zoom_frame, text="Zoom In", command=self.zoom_in)
        self.zoom_in_button.pack(side=tk.LEFT, padx=5)
        
        self.zoom_out_button = ttk.Button(self.zoom_frame, text="Zoom Out", command=self.zoom_out)
        self.zoom_out_button.pack(side=tk.LEFT, padx=5)
        
        self.reset_zoom_button = ttk.Button(self.zoom_frame, text="Reset Zoom", command=self.reset_zoom)
        self.reset_zoom_button.pack(side=tk.LEFT, padx=5)
    
    def _setup_split_tab(self):
        """Setup the split tab UI"""
        # Branch selection
        ttk.Label(self.split_tab, text="Select Branch to Split:").pack(anchor=tk.W, padx=5, pady=5)
        
        self.split_branch_var = tk.StringVar()
        self.split_branch_combo = ttk.Combobox(self.split_tab, textvariable=self.split_branch_var, state="readonly")
        self.split_branch_combo.pack(fill=tk.X, padx=5, pady=5)
        self.split_branch_combo.bind("<<ComboboxSelected>>", self.on_split_branch_selected)
        
        # City selection (with autocomplete)
        ttk.Label(self.split_tab, text="Select Split Point (City):").pack(anchor=tk.W, padx=5, pady=5)
        
        self.city_frame = ttk.Frame(self.split_tab)
        self.city_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.split_city_var = tk.StringVar()
        self.split_city_combo = ttk.Combobox(self.city_frame, textvariable=self.split_city_var)
        self.split_city_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Enable autocomplete
        self.split_city_combo.bind("<KeyRelease>", self.autocomplete_city)
        
        # Split button
        self.split_button = ttk.Button(self.split_tab, text="Split Route", command=self.split_route)
        self.split_button.pack(pady=10)
        
        # Status message
        self.split_status_var = tk.StringVar(value="Select a branch and city to split")
        ttk.Label(self.split_tab, textvariable=self.split_status_var, wraplength=250).pack(pady=5)
    
    def _setup_merge_tab(self):
        """Setup the merge tab UI"""
        # First branch selection
        ttk.Label(self.merge_tab, text="First Branch:").pack(anchor=tk.W, padx=5, pady=5)
        
        self.merge_branch1_var = tk.StringVar()
        self.merge_branch1_combo = ttk.Combobox(self.merge_tab, textvariable=self.merge_branch1_var, state="readonly")
        self.merge_branch1_combo.pack(fill=tk.X, padx=5, pady=5)
        self.merge_branch1_combo.bind("<<ComboboxSelected>>", lambda e: self.on_merge_branch_selected(1))
        
        # Connect city from first branch
        ttk.Label(self.merge_tab, text="Connect from City:").pack(anchor=tk.W, padx=5, pady=5)
        
        self.merge_city1_var = tk.StringVar()
        self.merge_city1_combo = ttk.Combobox(self.merge_tab, textvariable=self.merge_city1_var)
        self.merge_city1_combo.pack(fill=tk.X, padx=5, pady=5)
        self.merge_city1_combo.bind("<KeyRelease>", lambda e: self.autocomplete_city_merge(1))
        
        # Second branch selection
        ttk.Label(self.merge_tab, text="Second Branch:").pack(anchor=tk.W, padx=5, pady=5)
        
        self.merge_branch2_var = tk.StringVar()
        self.merge_branch2_combo = ttk.Combobox(self.merge_tab, textvariable=self.merge_branch2_var, state="readonly")
        self.merge_branch2_combo.pack(fill=tk.X, padx=5, pady=5)
        self.merge_branch2_combo.bind("<<ComboboxSelected>>", lambda e: self.on_merge_branch_selected(2))
        
        # Connect city from second branch
        ttk.Label(self.merge_tab, text="Connect to City:").pack(anchor=tk.W, padx=5, pady=5)
        
        self.merge_city2_var = tk.StringVar()
        self.merge_city2_combo = ttk.Combobox(self.merge_tab, textvariable=self.merge_city2_var)
        self.merge_city2_combo.pack(fill=tk.X, padx=5, pady=5)
        self.merge_city2_combo.bind("<KeyRelease>", lambda e: self.autocomplete_city_merge(2))
        
        # Merge button
        self.merge_button = ttk.Button(self.merge_tab, text="Merge Routes", command=self.merge_routes)
        self.merge_button.pack(pady=10)
        
        # Status message
        self.merge_status_var = tk.StringVar(value="Select branches and connection points")
        ttk.Label(self.merge_tab, textvariable=self.merge_status_var, wraplength=250).pack(pady=5)
    
    def setup_bindings(self):
        """Set up event bindings"""
        # Canvas events for panning/zooming
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)  # Windows
        self.canvas.bind("<Button-4>", self.on_mouse_wheel)    # Linux scroll up
        self.canvas.bind("<Button-5>", self.on_mouse_wheel)    # Linux scroll down
        
        # Initialize canvas state
        self.canvas_scale = 1.0
        self.canvas_offset_x = 0
        self.canvas_offset_y = 0
        self.drag_start_x = 0
        self.drag_start_y = 0
    
    def refresh_branch_list(self):
        """Update branch selection dropdown menus"""
        branches = [(branch_id, branch.name) for branch_id, branch in self.route_manager.branches.items()]
        
        # Update split tab
        self.split_branch_combo['values'] = [f"{name} ({bid})" for bid, name in branches]
        if branches:
            self.split_branch_combo.current(0)
            self.on_split_branch_selected()
        
        # Update merge tab
        self.merge_branch1_combo['values'] = [f"{name} ({bid})" for bid, name in branches]
        self.merge_branch2_combo['values'] = [f"{name} ({bid})" for bid, name in branches]
        
        if len(branches) >= 2:
            self.merge_branch1_combo.current(0)
            self.merge_branch2_combo.current(1)
            self.on_merge_branch_selected(1)
            self.on_merge_branch_selected(2)
    
    def get_branch_id_from_selection(self, selection):
        """Extract branch ID from selection string"""
        if not selection:
            return None
        # Format: "Branch Name (id)"
        try:
            return selection.split("(")[1].strip(")")
        except (IndexError, ValueError):
            return None
    
    def on_split_branch_selected(self, event=None):
        """Handle branch selection in split tab"""
        branch_selection = self.split_branch_var.get()
        branch_id = self.get_branch_id_from_selection(branch_selection)
        
        if not branch_id or branch_id not in self.route_manager.branches:
            self.split_city_combo['values'] = []
            return
        
        # Get all cities in this branch
        branch = self.route_manager.branches[branch_id]
        cities = set()
        
        for city1, city2 in branch.route_segments:
            cities.add(city1)
            cities.add(city2)
        
        self.split_city_combo['values'] = sorted(list(cities))
        if cities:
            self.split_city_combo.set(next(iter(cities)))
        
        # Update preview
        self.update_preview()
    
    def on_merge_branch_selected(self, branch_num):
        """Handle branch selection in merge tab"""
        if branch_num == 1:
            branch_selection = self.merge_branch1_var.get()
        else:
            branch_selection = self.merge_branch2_var.get()
            
        branch_id = self.get_branch_id_from_selection(branch_selection)
        
        if not branch_id or branch_id not in self.route_manager.branches:
            if branch_num == 1:
                self.merge_city1_combo['values'] = []
            else:
                self.merge_city2_combo['values'] = []
            return
        
        # Get all cities in this branch
        branch = self.route_manager.branches[branch_id]
        cities = set()
        
        for city1, city2 in branch.route_segments:
            cities.add(city1)
            cities.add(city2)
        
        if branch_num == 1:
            self.merge_city1_combo['values'] = sorted(list(cities))
            if cities:
                self.merge_city1_combo.set(next(iter(cities)))
        else:
            self.merge_city2_combo['values'] = sorted(list(cities))
            if cities:
                self.merge_city2_combo.set(next(iter(cities)))
        
        # Update preview
        self.update_preview()
    
    def autocomplete_city(self, event=None):
        """Autocomplete functionality for city selection"""
        typed = self.split_city_var.get().lower()
        
        if not typed:
            return
            
        matches = []
        for value in self.split_city_combo['values']:
            if value.lower().startswith(typed):
                matches.append(value)
        
        if matches:
            self.split_city_combo['values'] = matches
        
    def autocomplete_city_merge(self, branch_num):
        """Autocomplete for cities in merge tab"""
        if branch_num == 1:
            typed = self.merge_city1_var.get().lower()
            combo = self.merge_city1_combo
        else:
            typed = self.merge_city2_var.get().lower()
            combo = self.merge_city2_combo
            
        if not typed:
            return
            
        matches = []
        for value in combo['values']:
            if value.lower().startswith(typed):
                matches.append(value)
        
        if matches:
            combo['values'] = matches
    
    def update_preview(self):
        """Update the route preview canvas"""
        self.canvas.delete("all")
        
        # Draw the branch structure
        self._draw_branches()
        
        # Draw legend
        self._draw_legend()
    
    def _draw_branches(self):
        """Draw branch routes on the canvas"""
        # Get canvas dimensions
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # Don't draw if canvas isn't ready yet
        if canvas_width <= 1 or canvas_height <= 1:
            self.canvas.after(100, self.update_preview)
            return
        
        # Calculate scale to fit all cities
        min_x, max_x = float('inf'), float('-inf')
        min_y, max_y = float('inf'), float('-inf')
        
        cities_coords = {}
        
        # Collect all cities and their coordinates
        for city, (lon, lat) in self.route_data.cities.items():
            # Convert coordinates to canvas space
            x = (lon - 5) / (15 - 5) * canvas_width
            y = canvas_height - ((lat - 47) / (55 - 47) * canvas_height)
            
            cities_coords[city] = (x, y)
            
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)
        
        # Calculate margins
        margin = 50
        content_width = max_x - min_x + 2 * margin
        content_height = max_y - min_y + 2 * margin
        
        # Calculate scale and offset for centering and zoom
        scale_x = canvas_width / content_width if content_width > 0 else 1
        scale_y = canvas_height / content_height if content_height > 0 else 1
        base_scale = min(scale_x, scale_y)
        
        # Apply user zoom and pan
        effective_scale = base_scale * self.canvas_scale
        offset_x = self.canvas_offset_x + (canvas_width - content_width * effective_scale) / 2 - min_x * effective_scale + margin * effective_scale
        offset_y = self.canvas_offset_y + (canvas_height - content_height * effective_scale) / 2 - min_y * effective_scale + margin * effective_scale
        
        # Draw branches
        for branch_id, branch in self.route_manager.branches.items():
            # Highlight active branch
            is_active = (branch_id == self.route_manager.active_branch_id)
            line_width = 3 if is_active else 2
            
            # Draw connections with branch-specific style
            for city1, city2 in branch.route_segments:
                if city1 in cities_coords and city2 in cities_coords:
                    x1, y1 = cities_coords[city1]
                    x2, y2 = cities_coords[city2]
                    
                    # Transform coordinates based on zoom and pan
                    tx1 = x1 * effective_scale + offset_x
                    ty1 = y1 * effective_scale + offset_y
                    tx2 = x2 * effective_scale + offset_x
                    ty2 = y2 * effective_scale + offset_y
                    
                    # Draw curved connection line
                    if branch.line_style[0] == 0:  # Solid line
                        dash = ()
                    else:
                        dash = branch.line_style[1]
                    
                    # Calculate control point for curved line
                    distance = math.sqrt((tx2 - tx1) ** 2 + (ty2 - ty1) ** 2)
                    midx = (tx1 + tx2) / 2
                    midy = (ty1 + ty2) / 2
                    
                    # Calculate normal vector for curve control point
                    dx = (tx2 - tx1) / distance if distance > 0 else 0
                    dy = (ty2 - ty1) / distance if distance > 0 else 0
                    
                    # Perpendicular vector
                    px = -dy
                    py = dx
                    
                    # Control point - curve out from the line
                    curve_factor = min(100, distance / 4)  # Limit curvature
                    cx = midx + px * curve_factor
                    cy = midy + py * curve_factor
                    
                    # Draw using quadratic Bezier curve for smooth appearance
                    self.canvas.create_line(
                        tx1, ty1, cx, cy, tx2, ty2,
                        width=line_width, fill=branch.color, 
                        dash=dash, smooth=True, splinesteps=36,
                        tags=("connection", branch_id)
                    )
        
        # Draw cities (after connections so they're on top)
        for city, (x, y) in cities_coords.items():
            # Transform coordinates
            tx = x * effective_scale + offset_x
            ty = y * effective_scale + offset_y
            
            # Draw city dot
            self.canvas.create_oval(
                tx-6, ty-6, tx+6, ty+6, 
                fill="white", outline="black", width=2,
                tags=("city", city)
            )
            
            # Draw city label
            self.canvas.create_text(
                tx, ty+15, text=city, fill="black",
                font=("Arial", 8, "bold"), tags=("label", city)
            )
    
    def _draw_legend(self):
        """Draw a legend showing branch colors and styles"""
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # Create legend box in top-right corner
        legend_width = 180
        legend_height = 20 + 20 * len(self.route_manager.branches)
        legend_x = canvas_width - legend_width - 10
        legend_y = 10
        
        # Draw legend background
        self.canvas.create_rectangle(
            legend_x, legend_y, 
            legend_x + legend_width, legend_y + legend_height,
            fill="white", outline="black", width=1,
            tags=("legend", "background")
        )
        
        # Draw title
        self.canvas.create_text(
            legend_x + legend_width/2, legend_y + 10,
            text="Route Branches", font=("Arial", 10, "bold"),
            tags=("legend", "title")
        )
        
        # Draw branch entries
        y_offset = legend_y + 25
        for branch_id, branch in self.route_manager.branches.items():
            # Indicate active branch
            is_active = (branch_id == self.route_manager.active_branch_id)
            name_text = f"➤ {branch.name}" if is_active else branch.name
            
            # Draw color sample
            if branch.line_style[0] == 0:  # Solid line
                dash = ()
            else:
                dash = branch.line_style[1]
                
            self.canvas.create_line(
                legend_x + 10, y_offset, legend_x + 50, y_offset,
                width=3, fill=branch.color, dash=dash,
                tags=("legend", "sample", branch_id)
            )
            
            # Draw branch name
            self.canvas.create_text(
                legend_x + 60, y_offset,
                text=name_text, font=("Arial", 9),
                anchor="w", tags=("legend", "name", branch_id)
            )
            
            y_offset += 20
    
    def split_route(self):
        """Execute the split operation"""
        branch_selection = self.split_branch_var.get()
        branch_id = self.get_branch_id_from_selection(branch_selection)
        city = self.split_city_var.get()
        
        if not branch_id or not city:
            self.split_status_var.set("Please select a branch and city")
            return
        
        # Execute split operation
        success, message = self.route_manager.split_route(branch_id, city)
        
        if success:
            self.split_status_var.set(message)
            # Update UI to reflect changes
            self.refresh_branch_list()
            self.update_preview()
        else:
            self.split_status_var.set(f"Error: {message}")
    
    def merge_routes(self):
        """Execute the merge operation"""
        branch1_selection = self.merge_branch1_var.get()
        branch1_id = self.get_branch_id_from_selection(branch1_selection)
        city1 = self.merge_city1_var.get()
        
        branch2_selection = self.merge_branch2_var.get()
        branch2_id = self.get_branch_id_from_selection(branch2_selection)
        city2 = self.merge_city2_var.get()
        
        if not branch1_id or not branch2_id or not city1 or not city2:
            self.merge_status_var.set("Please select both branches and cities")
            return
        
        if branch1_id == branch2_id:
            self.merge_status_var.set("Cannot merge a branch with itself")
            return
        
        # Execute merge operation
        success, message = self.route_manager.merge_branches(branch1_id, branch2_id, city1, city2)
        
        if success:
            self.merge_status_var.set(message)
            # Update UI to reflect changes
            self.refresh_branch_list()
            self.update_preview()
        else:
            self.merge_status_var.set(f"Error: {message}")
    
    def undo_action(self):
        """Undo the last operation"""
        if not self.route_manager.can_undo():
            messagebox.showinfo("Info", "Nothing to undo")
            return
            
        success, message = self.route_manager.undo()
        if success:
            messagebox.showinfo("Undo", message)
            self.update_preview()
    
    def redo_action(self):
        """Redo the previously undone operation"""
        if not self.route_manager.can_redo():
            messagebox.showinfo("Info", "Nothing to redo")
            return
            
        success, message = self.route_manager.redo()
        if success:
            messagebox.showinfo("Redo", message)
            self.update_preview()
    
    def apply_changes(self):
        """Apply changes to the main route data"""
        success, message = self.route_manager.update_route_data()
        
        if success:
            messagebox.showinfo("Success", "Changes applied successfully")
            
            # Update the main application's map
            if self.map_plotter:
                self.map_plotter.update_plot()
                
            self.destroy()
        else:
            messagebox.showerror("Error", f"Failed to apply changes: {message}")
    
    def cancel(self):
        """Cancel and close the dialog"""
        if messagebox.askyesno("Confirm", "Discard all changes?"):
            self.destroy()
    
    def on_canvas_click(self, event):
        """Handle canvas click for panning"""
        self.drag_start_x = event.x
        self.drag_start_y = event.y
    
    def on_canvas_drag(self, event):
        """Handle canvas drag for panning"""
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y
        
        self.canvas_offset_x += dx
        self.canvas_offset_y += dy
        
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        
        self.update_preview()
    
    def on_mouse_wheel(self, event):
        """Handle mouse wheel for zooming"""
        # Handle different event types on different platforms
        delta = 0
        
        if event.num == 4:
            delta = 1  # Linux scroll up
        elif event.num == 5:
            delta = -1  # Linux scroll down
        else:
            # Windows and macOS
            delta = event.delta / 120
        
        # Apply zoom
        zoom_factor = 1.1 if delta > 0 else 0.9
        self.canvas_scale *= zoom_factor
        
        # Limit zoom range
        self.canvas_scale = max(0.1, min(10.0, self.canvas_scale))
        
        self.update_preview()
    
    def zoom_in(self):
        """Zoom in button handler"""
        self.canvas_scale *= 1.2
        self.canvas_scale = min(10.0, self.canvas_scale)
        self.update_preview()
    
    def zoom_out(self):
        """Zoom out button handler"""
        self.canvas_scale *= 0.8
        self.canvas_scale = max(0.1, self.canvas_scale)
        self.update_preview()
    
    def reset_zoom(self):
        """Reset zoom and pan"""
        self.canvas_scale = 1.0
        self.canvas_offset_x = 0
        self.canvas_offset_y = 0
        self.update_preview()
