# Train Route Visualizer (TRV)

A web-based train route planning and visualization tool for German railway networks. Displays routes on an interactive map with real rail geometry from OpenStreetMap.

## Features

- 🗺️ **Interactive Web Map**: Leaflet.js-based map with OpenStreetMap tiles
- 🚂 **Real Rail Routes**: Uses OpenStreetMap railway data via Overpass API
- ⚡ **Smart Routing**: NetworkX-based pathfinding on actual rail networks
- 🎨 **DB Design System**: Deutsche Bahn color scheme (ICE red, IC orange, RE blue, RB green)
- 📊 **Travel Time Estimation**: Terrain-aware calculations with station stops
- 💾 **Save/Load Projects**: .trv v3 file format (JSON-based)
- 📄 **PDF Export**: DIN A4 two-page PDF (map + legend)
- 🔄 **Smart Caching**: 3-tier cache system (memory → SQLite → project file)

## Quick Start

### Ubuntu 24.04 / Linux

```bash
./run_tool.sh
```

**First-time setup** (Ubuntu 24.04):
```bash
# Install python3-venv (not pre-installed on Ubuntu 24.04)
sudo apt install python3-venv

# Run the tool
./run_tool.sh
```

The launcher will:
1. Auto-create a virtual environment (`.venv/`)
2. Install dependencies from `requirements.txt`
3. Start the Flask server on a free port
4. Open your browser automatically

### Windows

Double-click `run_tool.bat` or run:
```cmd
run_tool.bat
```

The launcher will auto-create a virtual environment and install dependencies on first run.

### macOS

```bash
./run_tool.sh
```

## Architecture

### All-in-One Desktop Tool

**No server setup, no database configuration, no API keys, no Docker.** Everything runs in one Python process:

- Flask embedded localhost server (auto-finds free port)
- SQLite cache (auto-created)
- Browser auto-opens via `webbrowser.open()`
- All data directories auto-created

### File Structure

```
trv/
├── app.py                      # Flask entry point
├── requirements.txt            # Dependencies (Flask, NetworkX, Shapely, etc.)
├── run_tool.sh                 # Linux/macOS launcher
├── run_tool.bat                # Windows launcher
│
├── backend/
│   ├── overpass_client.py      # Overpass API with rate limiting
│   ├── routing.py              # NetworkX routing
│   ├── station_index.py        # Station database (6000+ German stations)
│   ├── travel_time.py          # Travel time estimation
│   ├── project_io.py           # .trv file format
│   └── pdf_export.py           # PDF generation
│
├── static/
│   ├── css/style.css           # DB Netzplan design
│   ├── js/
│   │   ├── map.js              # Leaflet map
│   │   ├── ui.js               # Station search & CRUD
│   │   └── export.js           # Save/load/PDF
│   └── lib/                    # Leaflet.js bundle (CDN fallback)
│
├── templates/
│   └── index.html              # Single-page app
│
└── data/                       # Auto-created at runtime
    ├── cache/                  # SQLite caches
    │   └── overpass_cache.db
    ├── projects/               # Saved .trv files
    └── export/                 # Generated PDFs
```

## Technology Stack

### Backend
- **Flask 3.0+**: Web framework
- **NetworkX 3.2+**: Graph-based routing
- **Shapely 2.0+**: Geometry operations
- **Matplotlib 3.8+**: PDF generation
- **SQLite**: Built-in caching

### Frontend
- **Leaflet.js 1.9+**: Interactive maps (Canvas renderer for performance)
- **Vanilla JavaScript**: No frameworks, minimal dependencies
- **OpenStreetMap**: Map tiles

### Data Source
- **Overpass API**: Real-time railway data from OpenStreetMap
- **Rate Limiting**: 1 request/minute with 3-tier caching

## Usage

1. **Search for stations**: Type in the search box (autocomplete from 6000+ German stations)
2. **Add connections**: Select from/to stations and train type (ICE/IC/RE/RB)
3. **View routes**: Routes appear on map with real rail geometry
4. **Save project**: Download `.trv` file to your computer
5. **Load project**: Upload saved `.trv` file
6. **Export PDF**: Generate DIN A4 PDF for printing

## Train Types

- **ICE** (Red): High-speed trains (speed factor 1.5x)
- **IC** (Orange): Inter-city trains (speed factor 1.2x)
- **RE** (Blue): Regional express (speed factor 0.9x)
- **RB** (Green): Regional trains (speed factor 0.7x)

## Route Quality Indicators

Routes are displayed with different line styles:
- **Solid line**: Confirmed rail route from OSM data
- **Dashed line**: Approximate route (graph has gaps)
- **Dotted line**: Straight-line fallback (no rail data found)

## .trv File Format (v3.0)

JSON-based project format:

```json
{
  "version": "3.0",
  "metadata": {
    "name": "My Route Plan",
    "created": "2026-02-13T10:00:00Z",
    "modified": "2026-02-13T14:30:00Z",
    "region": "germany"
  },
  "stations": {
    "sta_1": {"name": "Frankfurt (Main) Hbf", "lat": 50.1109, "lon": 8.6821},
    "sta_2": {"name": "Mannheim Hbf", "lat": 49.4795, "lon": 8.4700}
  },
  "connections": [
    {
      "id": "conn_1",
      "from": "sta_1",
      "to": "sta_2",
      "train_type": "ICE",
      "route_quality": "rail",
      "geometry": [[50.1109, 8.6821], ...],
      "geometry_simplified": [[50.1109, 8.6821], ...],
      "distance_km": 78.5,
      "travel_time_minutes": 30
    }
  ]
}
```

## Caching Strategy

### 3-Tier Cache (to respect Overpass API rate limits)

1. **Memory Cache**: Fast in-process cache (current session)
2. **SQLite Cache**: Persistent cache across sessions (30-day expiry)
3. **Project File Cache**: Routes stored in .trv files (fully offline)

Overpass public API allows **1 request per minute per IP**. The caching system ensures you rarely hit this limit.

## Development

### Running Tests

```bash
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
python test_backend.py
```

### Requirements

- Python 3.8+ (3.12 recommended for Ubuntu 24.04)
- Internet connection (for OSM tiles and Overpass API)
- ~50 MB disk space for cache

## Troubleshooting

### Ubuntu 24.04: "python3-venv not installed"

```bash
sudo apt install python3-venv
```

### Browser doesn't open automatically

Manually navigate to the URL shown in the terminal (e.g., `http://127.0.0.1:5000`)

### "Rate limited" message from Overpass API

Wait 60 seconds. The app uses cached data when available to minimize API calls.

### Station index download takes time on first run

The first run downloads ~6000 German railway stations from Overpass API (can take 1-2 minutes). This is cached permanently.

## Comparison with Original Version

### Removed (~36 MB)
- Natural Earth shapefiles (all `.shp`, `.dbf`, etc.)
- `geopandas` dependency
- `pgeocode` dependency (replaced by station index)
- `geopy` dependency (replaced by Overpass geocoding)
- Tkinter GUI

### Added
- Flask web server
- Leaflet.js web maps
- Real railway routing from OpenStreetMap
- Smarter caching system
- Browser-based UI

### Lighter & Faster
- Old: ~50 MB with shapefiles + geopandas
- New: ~5 MB with NetworkX + Shapely

## License

See original license terms. OpenStreetMap data © OpenStreetMap contributors.

## Credits

- **Railway data**: OpenStreetMap via Overpass API
- **Map tiles**: OpenStreetMap contributors
- **Design**: Deutsche Bahn design system colors
- **Original concept**: Tkinter train route visualizer

## Support

For issues, check the terminal output for error messages. Most issues are related to:
1. Missing `python3-venv` on Ubuntu 24.04
2. Overpass API rate limiting (wait 60 seconds)
3. Network connectivity for first-time station index download
