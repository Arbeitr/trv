# Architecture Diagram

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER (Web Browser)                            │
│  Double-click run_tool.sh/bat → Browser auto-opens to localhost     │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     FRONTEND (Leaflet.js)                            │
│  ┌────────────────┐  ┌────────────────┐  ┌─────────────────┐      │
│  │   Leaflet Map  │  │  Station       │  │  Connection     │      │
│  │   (Canvas)     │  │  Search UI     │  │  CRUD           │      │
│  │                │  │  (Autocomplete)│  │  (Add/Remove)   │      │
│  │  - Pan/Zoom    │  │                │  │                 │      │
│  │  - Routes      │  │  - 6000+ DB    │  │  - Train types  │      │
│  │  - Stations    │  │  - Instant     │  │  - Travel time  │      │
│  │  - Popups      │  │    search      │  │  - Distance     │      │
│  └────────────────┘  └────────────────┘  └─────────────────┘      │
│                                                                      │
│  map.js | ui.js | export.js | utils.js | style.css | index.html   │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ AJAX/Fetch API
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  FLASK WEB SERVER (Python)                           │
│                     app.py (localhost:auto-port)                     │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    API ENDPOINTS                               │  │
│  │                                                                │  │
│  │  GET  /                    → Serve index.html                 │  │
│  │  GET  /api/stations        → Get all stations                 │  │
│  │  POST /api/stations/search → Search stations                  │  │
│  │  POST /api/route           → Calculate route                  │  │
│  │  POST /api/export/pdf      → Generate PDF                     │  │
│  │  POST /api/projects/*      → Save/load projects               │  │
│  └──────────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                ▼               ▼               ▼
    ┌───────────────┐  ┌───────────────┐  ┌──────────────┐
    │   BACKEND     │  │   BACKEND     │  │   BACKEND    │
    │   MODULES     │  │   MODULES     │  │   MODULES    │
    └───────────────┘  └───────────────┘  └──────────────┘
                │               │               │
                ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        BACKEND MODULES                               │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  overpass_client.py                                          │   │
│  │  - 3-tier caching (memory → SQLite → project file)         │   │
│  │  - Rate limiting (1 req/min)                                │   │
│  │  - Exponential backoff                                      │   │
│  │  - HTTP 429 handling                                        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  station_index.py                                            │   │
│  │  - 6000+ German railway stations                            │   │
│  │  - SQLite storage with indexing                             │   │
│  │  - Autocomplete support                                     │   │
│  │  - 30-day refresh cycle                                     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  routing.py                                                  │   │
│  │  - NetworkX graph building                                  │   │
│  │  - Shortest path calculation                                │   │
│  │  - Disconnected component handling                          │   │
│  │  - Douglas-Peucker simplification                           │   │
│  │  - Route quality indicators                                 │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  travel_time.py                                              │   │
│  │  - Haversine distance calculation                           │   │
│  │  - Terrain-aware speed factors                              │   │
│  │  - Train type speeds (ICE/IC/RE/RB)                        │   │
│  │  - Station stop estimation                                  │   │
│  │  - Route curvature factors                                  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  project_io.py                                               │   │
│  │  - .trv v3.0 file format (JSON)                            │   │
│  │  - String-based station IDs                                 │   │
│  │  - Metadata management                                      │   │
│  │  - Save/load with timestamps                                │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  pdf_export.py                                               │   │
│  │  - Matplotlib Agg backend (headless)                        │   │
│  │  - DIN A4 two-page layout                                   │   │
│  │  - DB design colors                                         │   │
│  │  - WCAG-compliant contrast                                  │   │
│  └─────────────────────────────────────────────────────────────┘   │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                ▼               ▼               ▼
    ┌───────────────┐  ┌───────────────┐  ┌──────────────┐
    │   SQLite      │  │   Overpass    │  │   OSM Tiles  │
    │   Cache DB    │  │   API         │  │   (CDN)      │
    └───────────────┘  └───────────────┘  └──────────────┘
            │                   │                  │
            ▼                   ▼                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       DATA PERSISTENCE                               │
│                                                                      │
│  data/                                                              │
│  ├── cache/                                                         │
│  │   └── overpass_cache.db    (SQLite: queries + stations)        │
│  ├── projects/                                                      │
│  │   └── *.trv                (User project files)                 │
│  └── export/                                                        │
│      └── *.pdf                (Generated PDFs)                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Route Calculation Flow

```
1. User searches station → UI shows autocomplete
   ↓
2. User adds station → Added to state, marker on map
   ↓
3. User selects from/to/type → Click "Add Connection"
   ↓
4. Frontend sends POST /api/route
   ↓
5. Backend: station_index.py gets station coords
   ↓
6. Backend: routing.py calculates bbox corridor
   ↓
7. Backend: overpass_client.py queries Overpass API
   ↓
   ├─ Cache hit? → Return cached data
   ├─ Cache miss? → Query Overpass → Wait 60s (rate limit) → Cache result
   ↓
8. Backend: routing.py builds NetworkX graph
   ↓
9. Backend: routing.py finds shortest path
   ↓
10. Backend: travel_time.py estimates travel time
   ↓
11. Backend: Returns route JSON (geometry, distance, time, quality)
   ↓
12. Frontend: map.js renders route polyline
   ↓
13. Frontend: ui.js updates connection list
```

### Caching Strategy

```
┌──────────────────────────────────────────────────────────────┐
│                    REQUEST FOR ROUTE DATA                     │
└────────────────────────────┬─────────────────────────────────┘
                             │
                             ▼
                 ┌───────────────────────┐
                 │  Check Memory Cache   │ ← Layer 1 (fastest)
                 │  (Python dict)        │
                 └───────┬───────────────┘
                         │
              ┌──────────┴──────────┐
              │  HIT?               │
              └──────────┬──────────┘
                  YES ←──┤
                  │      NO
                  │      │
                  │      ▼
                  │  ┌───────────────────────┐
                  │  │  Check SQLite Cache   │ ← Layer 2 (30-day expiry)
                  │  │  (overpass_cache.db)  │
                  │  └───────┬───────────────┘
                  │          │
                  │   ┌──────┴──────────┐
                  │   │  HIT & VALID?   │
                  │   └──────┬──────────┘
                  │     YES ←┤
                  │     │    NO
                  │     │    │
                  │     │    ▼
                  │     │  ┌────────────────────────┐
                  │     │  │  Query Overpass API    │ ← Layer 3 (live)
                  │     │  │  - Wait for rate limit │
                  │     │  │  - Retry on 429        │
                  │     │  │  - Exponential backoff │
                  │     │  └────────┬───────────────┘
                  │     │           │
                  │     │           ▼
                  │     │     ┌──────────────┐
                  │     │     │ Store in     │
                  │     │     │ SQLite cache │
                  │     │     └──────┬───────┘
                  │     │            │
                  │     └────────────┼────────────┐
                  │                  │            │
                  ▼                  ▼            ▼
            ┌──────────────────────────────────────┐
            │  Store in memory cache (Layer 1)     │
            └──────────────┬───────────────────────┘
                           │
                           ▼
            ┌──────────────────────────────────────┐
            │  Return data to routing.py           │
            └──────────────────────────────────────┘
```

## Security Model

```
┌──────────────────────────────────────────────────────────────────┐
│                      SECURITY BOUNDARIES                          │
└──────────────────────────────────────────────────────────────────┘

Internet
    │
    │  Outbound only (API queries, map tiles)
    ▼
┌─────────────────────────────────────────────────┐
│  Flask Server (127.0.0.1:random-port)          │ ← Localhost only
│  - No external access                          │
│  - Random port per launch                      │
│  - CORS not configured (same-origin only)      │
└─────────────────────────────────────────────────┘
    │
    │  Browser same-origin policy
    ▼
┌─────────────────────────────────────────────────┐
│  Web Browser (localhost:port)                  │
│  - FileReader API for .trv files              │
│  - Blob API for downloads                      │
│  - No cookies, no tracking                     │
└─────────────────────────────────────────────────┘
    │
    │  User file system access (via browser)
    ▼
┌─────────────────────────────────────────────────┐
│  Local File System                              │
│  - data/cache/ (SQLite DB)                     │
│  - data/projects/ (.trv files)                 │
│  - data/export/ (PDF files)                    │
└─────────────────────────────────────────────────┘

Security Features:
✅ Localhost-only binding (127.0.0.1)
✅ No authentication needed (single-user, local-only)
✅ Input validation on all API endpoints
✅ Specific exception handling (no bare excepts)
✅ CORS restricted (same-origin)
✅ CodeQL verified (0 alerts)
```

## Cross-Platform Launchers

```
┌──────────────────────────────────────────────────────────────────┐
│                      LAUNCHER WORKFLOW                            │
└──────────────────────────────────────────────────────────────────┘

User double-clicks run_tool.sh (Linux/macOS) or run_tool.bat (Windows)
    │
    ▼
┌─────────────────────────────────────────────┐
│  1. Check for python3-venv                  │
│     - Ubuntu 24.04: Not pre-installed       │
│     - Show install instructions if missing  │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  2. Check if .venv/ exists                  │
│     - NO: Create venv                       │
│     - YES: Skip creation                    │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  3. Activate virtual environment            │
│     - Linux/macOS: source .venv/bin/activate│
│     - Windows: .venv\Scripts\activate.bat   │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  4. Check if dependencies installed         │
│     - Compare requirements.txt timestamp    │
│     - Install/upgrade if needed             │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  5. Launch Flask app                        │
│     - python3 app.py                        │
│     - Auto-find free port                   │
│     - Auto-open browser                     │
└─────────────────────────────────────────────┘
```

## Technology Choices Rationale

| Component | Choice | Why? |
|-----------|--------|------|
| Backend Framework | Flask | Lightweight, easy to embed, no boilerplate |
| Frontend Maps | Leaflet.js | Open-source, performant, Canvas renderer |
| Routing Library | NetworkX | Graph algorithms, well-maintained, pure Python |
| Geometry Library | Shapely | Industry standard, GEOS-based, fast |
| PDF Generation | Matplotlib | Reuse existing code, no new dependencies |
| Database | SQLite | Built-in Python, no setup, file-based |
| Data Source | Overpass API | Free, up-to-date OSM data, no account needed |
| Station Data | Overpass query | 6000+ stations, better than ZIP codes |
| Caching | 3-tier system | Respects rate limits, offline-capable |
| Launcher | Shell/Batch | Cross-platform, no build step, handles PEP 668 |

---

**Last Updated**: February 13, 2026  
**Architecture Version**: 3.0  
**Status**: ✅ Production Ready
