"""
Station Index Management
Downloads and caches all German railway stations from OpenStreetMap via Overpass API.
"""

import os
import sqlite3
import time
import logging

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "cache", "overpass_cache.db")

# Station index refresh interval (30 days)
STATION_INDEX_EXPIRY_DAYS = 30
STATION_INDEX_EXPIRY_SECONDS = STATION_INDEX_EXPIRY_DAYS * 24 * 60 * 60

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def ensure_station_index_initialized():
    """Ensure station index is initialized and up-to-date."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if we have stations and when they were last updated
    cursor.execute("SELECT COUNT(*), MAX(updated) FROM station_index")
    count, last_updated = cursor.fetchone()
    
    conn.close()
    
    current_time = int(time.time())
    needs_refresh = (
        count == 0 or 
        last_updated is None or 
        (current_time - last_updated) > STATION_INDEX_EXPIRY_SECONDS
    )
    
    if needs_refresh:
        logger.info("Station index needs initialization or refresh...")
        download_german_stations()
    else:
        logger.info(f"Station index up-to-date: {count} stations")


def download_german_stations():
    """Download all German railway stations from Overpass API."""
    from backend.overpass_client import query_overpass
    
    logger.info("Downloading German railway stations from OpenStreetMap...")
    
    # Overpass query for all German railway stations
    query = """
    [out:json][timeout:120];
    area["ISO3166-1"="DE"][admin_level=2]->.germany;
    (
      node["railway"="station"](area.germany);
      node["railway"="halt"](area.germany);
    );
    out body;
    """
    
    try:
        response = query_overpass(query, cache=False)  # Don't cache this large query
        
        if not response or 'elements' not in response:
            logger.error("Failed to download station index")
            return False
        
        stations = response['elements']
        logger.info(f"Downloaded {len(stations)} stations")
        
        # Store in database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Clear old station data
        cursor.execute("DELETE FROM station_index")
        
        # Insert new stations
        current_time = int(time.time())
        for station in stations:
            tags = station.get('tags', {})
            name = tags.get('name', f"Station {station['id']}")
            lat = station.get('lat')
            lon = station.get('lon')
            railway_type = tags.get('railway', 'station')
            
            if lat and lon:
                cursor.execute("""
                    INSERT INTO station_index (name, lat, lon, railway_type, updated)
                    VALUES (?, ?, ?, ?, ?)
                """, (name, lat, lon, railway_type, current_time))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✓ Station index updated: {len(stations)} stations")
        return True
        
    except Exception as e:
        logger.error(f"Error downloading station index: {e}")
        return False


def get_all_stations():
    """Get all stations from the cache."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT name, lat, lon, railway_type 
        FROM station_index 
        ORDER BY name
    """)
    
    stations = []
    for row in cursor.fetchall():
        stations.append({
            "name": row[0],
            "lat": row[1],
            "lon": row[2],
            "type": row[3]
        })
    
    conn.close()
    return stations


def search_stations(query, limit=10):
    """Search stations by name substring."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Case-insensitive search
    cursor.execute("""
        SELECT name, lat, lon, railway_type 
        FROM station_index 
        WHERE name LIKE ? 
        ORDER BY 
            CASE WHEN name LIKE ? THEN 0 ELSE 1 END,
            name
        LIMIT ?
    """, (f"%{query}%", f"{query}%", limit))
    
    results = []
    for row in cursor.fetchall():
        results.append({
            "name": row[0],
            "lat": row[1],
            "lon": row[2],
            "type": row[3]
        })
    
    conn.close()
    return results


def get_station_by_name(name):
    """Get a station by exact name match."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT name, lat, lon, railway_type 
        FROM station_index 
        WHERE name = ?
    """, (name,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "name": row[0],
            "lat": row[1],
            "lon": row[2],
            "type": row[3]
        }
    return None
