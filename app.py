#!/usr/bin/env python3
"""
Train Route Visualizer - Flask Web Application
Main entry point with auto-port finding, auto-browser launch, and embedded server.
"""

import os
import sys
import socket
import threading
import webbrowser
import sqlite3
import time
from flask import Flask, render_template, jsonify, request, send_file

# Determine base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Auto-create directories
for directory in ["data", "data/cache", "data/projects"]:
    os.makedirs(os.path.join(BASE_DIR, directory), exist_ok=True)


def init_db():
    """Initialize SQLite database for caching Overpass queries and station index."""
    db_path = os.path.join(BASE_DIR, "data", "cache", "overpass_cache.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Overpass query cache table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS overpass_cache (
            query_hash TEXT PRIMARY KEY,
            query_text TEXT NOT NULL,
            response_data TEXT NOT NULL,
            timestamp INTEGER NOT NULL
        )
    """)
    
    # Station index table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS station_index (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            railway_type TEXT,
            updated INTEGER NOT NULL
        )
    """)
    
    # Create index on station name for fast autocomplete
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_station_name ON station_index(name)
    """)
    
    conn.commit()
    conn.close()
    print(f"✓ Database initialized: {db_path}")


def find_free_port():
    """Find a free port for the Flask server."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))  # Bind to localhost only for security
        s.listen(1)
        port = s.getsockname()[1]
    return port


# Initialize database
init_db()

# Create Flask app
app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, "templates"),
            static_folder=os.path.join(BASE_DIR, "static"))

# Configure app
app.config['SECRET_KEY'] = os.urandom(24)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload


# --- Routes ---

@app.route('/')
def index():
    """Serve the main single-page application."""
    return render_template('index.html')


@app.route('/api/stations')
def get_stations():
    """Return all cached stations for autocomplete."""
    from backend.station_index import get_all_stations
    stations = get_all_stations()
    return jsonify({"stations": stations})


@app.route('/api/stations/search', methods=['POST'])
def search_stations():
    """Search stations by name substring."""
    from backend.station_index import search_stations
    data = request.get_json()
    query = data.get('query', '')
    limit = data.get('limit', 10)
    
    results = search_stations(query, limit)
    return jsonify({"results": results})


@app.route('/api/route', methods=['POST'])
def calculate_route():
    """Calculate route between two stations using Overpass corridor query."""
    from backend.routing import calculate_route_geometry
    
    data = request.get_json()
    from_station = data.get('from')
    to_station = data.get('to')
    train_type = data.get('train_type', 'RE')
    
    if not from_station or not to_station:
        return jsonify({"error": "Missing from or to station"}), 400
    
    try:
        result = calculate_route_geometry(from_station, to_station, train_type)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/export/pdf', methods=['POST'])
def export_pdf():
    """Generate and return a DIN A4 PDF of the current route."""
    from backend.pdf_export import generate_pdf
    
    data = request.get_json()
    
    try:
        pdf_path = generate_pdf(data)
        return send_file(pdf_path, as_attachment=True, download_name='route_map.pdf')
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/projects', methods=['GET'])
def list_projects():
    """List all saved .trv project files."""
    projects_dir = os.path.join(BASE_DIR, "data", "projects")
    projects = []
    
    for filename in os.listdir(projects_dir):
        if filename.endswith('.trv'):
            filepath = os.path.join(projects_dir, filename)
            stat = os.stat(filepath)
            projects.append({
                "name": filename,
                "size": stat.st_size,
                "modified": stat.st_mtime
            })
    
    return jsonify({"projects": projects})


@app.route('/api/projects/save', methods=['POST'])
def save_project():
    """Save project to server (optional server-side storage)."""
    from backend.project_io import save_project_file
    
    data = request.get_json()
    filename = data.get('filename', 'project.trv')
    project_data = data.get('data')
    
    if not project_data:
        return jsonify({"error": "No project data provided"}), 400
    
    try:
        filepath = save_project_file(filename, project_data)
        return jsonify({"success": True, "path": filepath})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/projects/load', methods=['POST'])
def load_project():
    """Load project from server."""
    from backend.project_io import load_project_file
    
    data = request.get_json()
    filename = data.get('filename')
    
    if not filename:
        return jsonify({"error": "No filename provided"}), 400
    
    try:
        project_data = load_project_file(filename)
        return jsonify(project_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/connection/refresh', methods=['POST'])
def refresh_connection():
    """Re-query Overpass for updated route geometry."""
    from backend.routing import calculate_route_geometry
    
    data = request.get_json()
    from_station = data.get('from')
    to_station = data.get('to')
    train_type = data.get('train_type', 'RE')
    force_refresh = True  # Skip cache
    
    try:
        result = calculate_route_geometry(from_station, to_station, train_type, force_refresh)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    """Browser heartbeat for shutdown detection."""
    return jsonify({"status": "ok"})


# --- Error handlers ---

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500


# --- Main execution ---

def open_browser(url):
    """Open browser after a short delay."""
    time.sleep(1.5)
    print(f"🌐 Opening browser: {url}")
    webbrowser.open(url)


if __name__ == '__main__':
    # Check if station index needs initialization
    from backend.station_index import ensure_station_index_initialized
    ensure_station_index_initialized()
    
    # Find free port
    port = find_free_port()
    url = f"http://127.0.0.1:{port}"
    
    print("=" * 60)
    print("🚂 Train Route Visualizer")
    print("=" * 60)
    print(f"Server starting on: {url}")
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    
    # Start browser in background thread
    threading.Timer(1.5, lambda: open_browser(url)).start()
    
    # Start Flask server
    app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)
