# Migration Guide: From Tkinter to Web Version

## Overview

The Train Route Visualizer has been completely rewritten from a Tkinter desktop app to a modern web-based architecture. This guide helps existing users understand the changes and migrate their workflows.

## What Changed?

### Technology Stack

**Before (Tkinter Version):**
- Desktop GUI with Tkinter
- matplotlib embedded canvas
- Natural Earth shapefiles (~36 MB)
- geopandas, pgeocode, geopy
- Straight-line routes only

**After (Web Version):**
- Flask web server + Leaflet.js
- Interactive web maps
- Real railway routes from OpenStreetMap
- NetworkX routing on actual rail networks
- Much lighter dependencies (~5 MB vs ~50 MB)

### User Experience

| Feature | Old (Tkinter) | New (Web) |
|---------|---------------|-----------|
| **Launch** | Double-click Python script | `./run_tool.sh` or `run_tool.bat` |
| **Interface** | Desktop window | Web browser |
| **Map** | Static matplotlib | Interactive Leaflet |
| **Routes** | Straight lines | Real rail geometry |
| **Save/Load** | File dialog | Browser download/upload |
| **Export PDF** | File dialog | Browser download |
| **Zoom** | State selection | Pan/zoom anywhere |
| **Station Data** | ZIP code lookup | OSM station database |

## Migration Steps

### 1. Install New Dependencies

The new version has lighter dependencies. No need to uninstall old packages.

**Ubuntu 24.04 / Debian:**
```bash
sudo apt install python3-venv
```

**Windows/macOS:**
No system dependencies needed (Python 3.8+ required)

### 2. Launch the New Version

**Linux/macOS:**
```bash
./run_tool.sh
```

**Windows:**
```cmd
run_tool.bat
```

The launcher will:
1. Create a virtual environment automatically
2. Install dependencies
3. Start the Flask server
4. Open your browser

### 3. First-Time Setup

On first run, the app downloads ~6000 German railway stations from OpenStreetMap (1-2 minutes). This is cached permanently.

### 4. Migrating Old .trv Files

The new version uses `.trv v3.0` format with better structure:

**Old format issues:**
- Tuple keys serialized as strings `"('City1', 'City2')"`
- Manual parsing needed
- No route geometry

**New format:**
- String IDs as keys: `"sta_1"`, `"conn_1"`
- Full route geometry stored
- Route quality indicators
- Better metadata

**Note:** Old `.trv` files are not directly compatible. You'll need to recreate routes, but this is quick thanks to the new station search with autocomplete.

## Key Workflow Changes

### Adding Stations

**Old way:**
1. Click "Add City"
2. Enter ZIP code
3. City added from ZIP database

**New way:**
1. Type station name in search box
2. Autocomplete shows matches
3. Click to add (6000+ German stations)

### Adding Connections

**Old way:**
1. Select two cities
2. Choose train type
3. Straight line drawn

**New way:**
1. Select two stations
2. Choose train type
3. **Real railway route queried from OSM**
4. Route rendered with actual geometry

### Exporting PDF

**Old way:**
1. Menu → Export PDF
2. File dialog
3. PDF saved

**New way:**
1. Click "Export PDF" button
2. Browser downloads PDF
3. Same two-page layout preserved

## New Features

### 1. Real Railway Routes

Routes now follow actual rail lines from OpenStreetMap, not straight lines.

**Route Quality Indicators:**
- **Solid line**: Confirmed rail route
- **Dashed line**: Approximate (with gaps)
- **Dotted line**: Straight line fallback

### 2. Station Search

- Instant autocomplete
- 6000+ German stations
- Search by name (no ZIP codes needed)

### 3. Interactive Map

- Pan and zoom freely
- Click routes/stations for info
- OpenStreetMap tiles

### 4. Smart Caching

The app caches:
- Station database (permanent)
- Overpass queries (30 days)
- Routes in project files (offline)

This respects Overpass API rate limits (1 req/min).

## Common Questions

### Q: Can I use the old Tkinter version alongside the new one?

**A:** Yes! They don't interfere with each other. The old version is still in `map_germany_plz_integrated_ui.py`.

### Q: Why doesn't the browser open automatically?

**A:** Some systems don't support auto-browser-open. Just navigate to the URL shown in the terminal (e.g., `http://127.0.0.1:5000`).

### Q: Do I need internet access?

**A:** 
- **First run**: Yes (to download station index and map tiles)
- **After caching**: Partially (map tiles need internet, but routes work offline if cached)

### Q: What about the shapefiles?

**A:** They're no longer used. The new version uses OpenStreetMap tiles and data. You can delete the `ne_10m_*` files to save ~36 MB.

### Q: Can I still use ZIP codes?

**A:** Not directly. Use the station search instead - it has more accurate data and covers all railway stations.

### Q: What about travel time calculations?

**A:** Fully preserved! The new version uses the same logic:
- Terrain factors
- Train type speeds
- Station stops
- Route curvature
- **Plus**: Real distance from actual rail routes

### Q: Is PEP 668 handled?

**A:** Yes! The launchers auto-create virtual environments, which is required on Ubuntu 24.04.

## Performance Comparison

| Metric | Old (Tkinter) | New (Web) |
|--------|---------------|-----------|
| **Install size** | ~50 MB | ~5 MB |
| **Startup time** | 5-10 seconds | 2-3 seconds |
| **Route calculation** | Instant (straight line) | 2-10 seconds (real rail, cached after) |
| **Map rendering** | 1-2 seconds | Instant (interactive) |
| **PDF export** | 3-5 seconds | 3-5 seconds |

## Troubleshooting

### "python3-venv not installed"

Ubuntu 24.04 doesn't include `python3-venv` by default:
```bash
sudo apt install python3-venv
```

### "Rate limited by Overpass API"

The app respects 1 request/minute limit. Wait 60 seconds or use cached data.

### "Station index download slow"

First run downloads ~6000 stations (1-2 minutes). This is one-time only.

### "Routes look different"

That's expected! The new version uses real rail routes from OpenStreetMap, not straight lines.

### "Can't find my station"

Try different spellings:
- "Frankfurt Hbf"
- "Frankfurt (Main) Hauptbahnhof"
- "Frankfurt am Main"

The autocomplete shows all matches.

## Getting Help

1. Check the terminal output for error messages
2. See README.md for detailed documentation
3. Most issues are related to:
   - Missing `python3-venv` on Ubuntu
   - Overpass API rate limiting
   - Network connectivity

## Benefits of the New Version

✅ **Real railway routes** from OpenStreetMap  
✅ **Lighter dependencies** (~5 MB vs ~50 MB)  
✅ **Better station data** (6000+ stations vs ZIP-based)  
✅ **Interactive maps** with pan/zoom  
✅ **Smart caching** for offline use  
✅ **Cross-platform** (Ubuntu 24.04 PEP 668 compliant)  
✅ **Modern web UI** with better UX  
✅ **Same business logic** for travel times  
✅ **Same PDF export** format  

## Timeline

- **Tkinter version**: Will remain in repo as `map_germany_plz_integrated_ui.py`
- **Web version**: Now the default (launched via `run_tool.sh` / `run_tool.bat`)
- **Old .trv files**: Not directly compatible, but easy to recreate

## Feedback

The new architecture is designed for future enhancements:
- More countries (beyond Germany)
- More route quality improvements
- Better offline support
- API for automation

Enjoy the new version! 🚂
