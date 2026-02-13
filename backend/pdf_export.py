"""
PDF Export using matplotlib (server-side, headless)
Generates DIN A4 two-page PDF (map + legend)
"""

import os
import matplotlib
matplotlib.use('Agg')  # Headless backend
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from backend.travel_time import TRAIN_TYPES, format_travel_time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORT_DIR = os.path.join(BASE_DIR, "data", "export")

# Ensure export directory exists
os.makedirs(EXPORT_DIR, exist_ok=True)


def generate_pdf(project_data):
    """
    Generate a DIN A4 PDF from project data.
    
    Args:
        project_data: Project data dictionary with stations and connections
    
    Returns:
        Path to generated PDF file
    """
    import time
    timestamp = int(time.time())
    filename = f"route_map_{timestamp}.pdf"
    filepath = os.path.join(EXPORT_DIR, filename)
    
    stations = project_data.get('stations', {})
    connections = project_data.get('connections', [])
    metadata = project_data.get('metadata', {})
    
    with PdfPages(filepath) as pdf:
        # Page 1: Map
        fig1, ax1 = plt.subplots(figsize=(8.27, 11.69))  # DIN A4 portrait
        ax1.set_facecolor('#F5F5F5')
        ax1.axis('off')
        
        # Plot connections
        for conn in connections:
            from_id = conn.get('from')
            to_id = conn.get('to')
            train_type = conn.get('train_type', 'RE')
            geometry = conn.get('geometry_simplified', conn.get('geometry', []))
            route_quality = conn.get('route_quality', 'rail')
            
            if from_id in stations and to_id in stations and geometry:
                # Extract coordinates
                lons = [coord[0] for coord in geometry]
                lats = [coord[1] for coord in geometry]
                
                # Get color
                color = TRAIN_TYPES.get(train_type, TRAIN_TYPES['RE'])['color']
                
                # Determine line style based on route quality
                if route_quality == 'straight_line':
                    linestyle = ':'  # Dotted
                elif route_quality == 'rail_approx':
                    linestyle = '--'  # Dashed
                else:
                    linestyle = '-'  # Solid
                
                # Plot line
                ax1.plot(lons, lats, color=color, linewidth=2.5, 
                        linestyle=linestyle, alpha=0.9)
        
        # Plot stations
        for station_id, station_data in stations.items():
            lon = station_data.get('lon')
            lat = station_data.get('lat')
            name = station_data.get('name', station_id)
            
            if lon and lat:
                ax1.plot(lon, lat, marker='o', markersize=10,
                        markeredgecolor='black', markerfacecolor='white', zorder=10)
                ax1.text(lon + 0.1, lat, name, fontsize=8, fontweight='bold',
                        color='white', ha='left', va='center',
                        bbox=dict(facecolor='darkgrey', edgecolor='none', 
                                boxstyle='round,pad=0.3'), zorder=11)
        
        # Set title
        project_name = metadata.get('name', 'Train Route Map')
        fig1.suptitle(project_name, fontsize=14, fontweight='bold')
        
        # Auto-adjust limits
        if stations:
            lons = [s['lon'] for s in stations.values() if 'lon' in s]
            lats = [s['lat'] for s in stations.values() if 'lat' in s]
            
            if lons and lats:
                lon_range = max(lons) - min(lons)
                lat_range = max(lats) - min(lats)
                padding = max(lon_range, lat_range) * 0.1
                
                ax1.set_xlim(min(lons) - padding, max(lons) + padding)
                ax1.set_ylim(min(lats) - padding, max(lats) + padding)
        
        pdf.savefig(fig1, bbox_inches='tight')
        plt.close(fig1)
        
        # Page 2: Legend
        fig2, ax2 = plt.subplots(figsize=(8.27, 11.69))  # DIN A4 portrait
        ax2.axis('off')
        
        # Title
        fig2.suptitle("Route Legend", fontsize=16, fontweight='bold', y=0.98)
        
        # Draw legend content
        y_pos = 0.9
        x_pos = 0.1
        
        for i, conn in enumerate(connections):
            from_id = conn.get('from')
            to_id = conn.get('to')
            train_type = conn.get('train_type', 'RE')
            distance_km = conn.get('distance_km', 0)
            travel_time_minutes = conn.get('travel_time_minutes', 0)
            
            if from_id in stations and to_id in stations:
                from_name = stations[from_id].get('name', from_id)
                to_name = stations[to_id].get('name', to_id)
                
                # Connection header
                ax2.text(x_pos, y_pos, f"Connection {i+1}:", 
                        fontsize=11, fontweight='bold', transform=ax2.transAxes)
                y_pos -= 0.03
                
                # From station
                ax2.plot(x_pos, y_pos, marker='o', markersize=8,
                        markeredgecolor='black', markerfacecolor='white',
                        transform=ax2.transAxes)
                ax2.text(x_pos + 0.03, y_pos, from_name,
                        fontsize=9, va='center', transform=ax2.transAxes)
                y_pos -= 0.03
                
                # Line with train type
                color = TRAIN_TYPES.get(train_type, TRAIN_TYPES['RE'])['color']
                ax2.plot([x_pos, x_pos], [y_pos + 0.02, y_pos - 0.01],
                        color=color, linewidth=3, transform=ax2.transAxes)
                ax2.text(x_pos + 0.03, y_pos, 
                        f"{train_type} • {distance_km:.1f} km • {format_travel_time(travel_time_minutes)}",
                        fontsize=8, va='center', color='#555555',
                        transform=ax2.transAxes)
                y_pos -= 0.03
                
                # To station
                ax2.plot(x_pos, y_pos, marker='o', markersize=8,
                        markeredgecolor='black', markerfacecolor='white',
                        transform=ax2.transAxes)
                ax2.text(x_pos + 0.03, y_pos, to_name,
                        fontsize=9, va='center', transform=ax2.transAxes)
                y_pos -= 0.06
                
                # Check if we need a new column
                if y_pos < 0.1 and i < len(connections) - 1:
                    x_pos += 0.45
                    y_pos = 0.9
                    
                    if x_pos > 0.9:  # Out of space
                        break
        
        pdf.savefig(fig2, bbox_inches='tight')
        plt.close(fig2)
    
    return filepath
