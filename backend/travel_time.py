"""
Travel Time Estimation
Migrated from map_germany_plz_integrated_ui.py RouteData class.
"""

import math
import logging
from math import radians, sin, cos, sqrt, atan2

# Constants from original code
EARTH_RADIUS_KM = 6371
AVERAGE_TRAIN_SPEED_KMH = 100

# Train type definitions
TRAIN_TYPES = {
    "ICE": {"name": "ICE", "speed_factor": 1.5, "color": "#EC0016"},  # DB Red
    "IC": {"name": "IC", "speed_factor": 1.2, "color": "#FF6600"},    # DB Orange
    "RE": {"name": "RE", "speed_factor": 0.9, "color": "#1455C0"},    # DB Blue
    "RB": {"name": "RB", "speed_factor": 0.7, "color": "#408335"}     # DB Green
}

# Station stop times per train type (minutes)
STATION_STOP_MINUTES = {
    "ICE": 2,
    "IC": 3,
    "RE": 3,
    "RB": 4
}

# Typical stations per 100km
TYPICAL_STATIONS_PER_100KM = {
    "ICE": 0.5,
    "IC": 1,
    "RE": 2,
    "RB": 3
}

# Route curvature factors (how indirect routes are by train type)
ROUTE_CURVATURE_FACTORS = {
    "ICE": 1.1,
    "IC": 1.15,
    "RE": 1.25,
    "RB": 1.35
}

# Geographic terrain factors
GEOGRAPHIC_FACTORS = {
    "FLAT": 1.0,
    "HILLS": 1.15,
    "MOUNTAINS": 1.3,
    "URBAN": 1.2
}

# Region topography mapping
REGION_TOPOGRAPHY = {
    "Bayern": "MOUNTAINS",
    "Baden-Württemberg": "HILLS",
    "Hessen": "HILLS",
    "Thüringen": "HILLS",
    "Sachsen": "HILLS",
    "Rheinland-Pfalz": "HILLS",
    "Saarland": "HILLS",
    "Nordrhein-Westfalen": "FLAT",
    "Niedersachsen": "FLAT",
    "Bremen": "FLAT",
    "Hamburg": "FLAT",
    "Schleswig-Holstein": "FLAT",
    "Mecklenburg-Vorpommern": "FLAT",
    "Brandenburg": "FLAT",
    "Berlin": "URBAN",
    "Sachsen-Anhalt": "FLAT"
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def haversine_distance(coord1, coord2):
    """
    Calculate Haversine distance between two coordinates.
    
    Args:
        coord1: Tuple of (lon, lat)
        coord2: Tuple of (lon, lat)
    
    Returns:
        Distance in kilometers
    """
    lon1, lat1 = radians(coord1[0]), radians(coord1[1])
    lon2, lat2 = radians(coord2[0]), radians(coord2[1])
    
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    distance = EARTH_RADIUS_KM * c
    logger.debug(f"Haversine distance: {distance:.2f} km")
    
    return distance


def get_terrain_factor(coord1, coord2):
    """
    Determine the terrain factor between two coordinates.
    
    Args:
        coord1: Tuple of (lon, lat)
        coord2: Tuple of (lon, lat)
    
    Returns:
        Terrain factor (>= 1.0, higher = slower)
    """
    region1 = get_region_from_coordinates(coord1)
    region2 = get_region_from_coordinates(coord2)
    
    # If we can identify both regions, use the more challenging terrain
    if region1 in REGION_TOPOGRAPHY and region2 in REGION_TOPOGRAPHY:
        terrain_type1 = REGION_TOPOGRAPHY[region1]
        terrain_type2 = REGION_TOPOGRAPHY[region2]
        
        # Use the more challenging terrain between the two points
        terrain_types = [terrain_type1, terrain_type2]
        if "MOUNTAINS" in terrain_types:
            return GEOGRAPHIC_FACTORS["MOUNTAINS"]
        elif "HILLS" in terrain_types:
            return GEOGRAPHIC_FACTORS["HILLS"]
        elif "URBAN" in terrain_types:
            return GEOGRAPHIC_FACTORS["URBAN"]
        else:
            return GEOGRAPHIC_FACTORS["FLAT"]
    
    # Default: slightly complex terrain
    return 1.15


def get_region_from_coordinates(coords):
    """
    Approximate German state/region from coordinates.
    
    Args:
        coords: Tuple of (lon, lat)
    
    Returns:
        Region name string
    """
    lon, lat = coords[0], coords[1]
    
    # Approximate mapping of coordinates to German states
    if 47.5 <= lat <= 49.8 and 8.9 <= lon <= 13.8:
        return "Bayern"
    elif 47.5 <= lat <= 49.8 and 7.5 <= lon <= 9.8:
        return "Baden-Württemberg"
    elif 49.3 <= lat <= 51.5 and 7.7 <= lon <= 10.2:
        return "Hessen"
    elif 50.2 <= lat <= 51.6 and 9.9 <= lon <= 12.6:
        return "Thüringen"
    elif 50.1 <= lat <= 51.7 and 11.8 <= lon <= 15.0:
        return "Sachsen"
    elif 48.9 <= lat <= 50.9 and 6.1 <= lon <= 8.5:
        return "Rheinland-Pfalz"
    elif 49.1 <= lat <= 49.6 and 6.3 <= lon <= 7.4:
        return "Saarland"
    elif 50.3 <= lat <= 52.5 and 5.8 <= lon <= 9.5:
        return "Nordrhein-Westfalen"
    elif 51.2 <= lat <= 54.0 and 6.5 <= lon <= 11.6:
        return "Niedersachsen"
    elif 53.0 <= lat <= 53.6 and 8.4 <= lon <= 9.0:
        return "Bremen"
    elif 53.4 <= lat <= 53.7 and 9.6 <= lon <= 10.3:
        return "Hamburg"
    elif 53.3 <= lat <= 55.1 and 8.4 <= lon <= 11.3:
        return "Schleswig-Holstein"
    elif 53.0 <= lat <= 54.9 and 10.5 <= lon <= 14.5:
        return "Mecklenburg-Vorpommern"
    elif 51.3 <= lat <= 53.6 and 11.2 <= lon <= 14.8:
        return "Brandenburg"
    elif 52.3 <= lat <= 52.7 and 13.0 <= lon <= 13.8:
        return "Berlin"
    elif 50.8 <= lat <= 53.1 and 10.5 <= lon <= 13.2:
        return "Sachsen-Anhalt"
    
    # General terrain based on latitude
    if lat >= 52.0:
        return "FLAT_REGION"
    elif lat >= 50.0:
        return "HILLY_REGION"
    else:
        return "MOUNTAINOUS_REGION"


def estimate_station_stops(distance_km, train_type):
    """
    Estimate the number of station stops based on distance and train type.
    
    Args:
        distance_km: Distance in kilometers
        train_type: Train type string (ICE, IC, RE, RB)
    
    Returns:
        Number of stops (integer)
    """
    estimated_stops = distance_km / 100 * TYPICAL_STATIONS_PER_100KM.get(train_type, 1)
    return max(0, round(estimated_stops))


def estimate_travel_time(coord1, coord2, train_type="RE", actual_distance_km=None):
    """
    Estimate travel time between two coordinates considering multiple factors.
    
    Args:
        coord1: Tuple of (lon, lat) for start
        coord2: Tuple of (lon, lat) for end
        train_type: Train type string (default: "RE")
        actual_distance_km: If provided, use this distance instead of calculating
    
    Returns:
        Travel time in minutes (integer)
    """
    # Calculate or use provided distance
    if actual_distance_km is not None:
        adjusted_distance = actual_distance_km
        logger.debug(f"Using actual route distance: {adjusted_distance:.2f} km")
    else:
        # Calculate base straight-line distance
        base_distance_km = haversine_distance(coord1, coord2)
        
        # Apply route curvature factor
        route_curvature = ROUTE_CURVATURE_FACTORS.get(train_type, 1.2)
        adjusted_distance = base_distance_km * route_curvature
        logger.debug(f"Base distance: {base_distance_km:.2f} km, adjusted: {adjusted_distance:.2f} km")
    
    # Account for geographic features
    terrain_factor = get_terrain_factor(coord1, coord2)
    
    # Apply speed factor based on train type
    speed_factor = TRAIN_TYPES.get(train_type, TRAIN_TYPES["RE"])["speed_factor"]
    adjusted_speed = AVERAGE_TRAIN_SPEED_KMH * speed_factor / terrain_factor
    
    # Calculate base travel time
    travel_time_hours = adjusted_distance / adjusted_speed
    travel_time_minutes = travel_time_hours * 60
    
    # Add time for station stops
    station_stops = estimate_station_stops(adjusted_distance, train_type)
    stop_time_minutes = station_stops * STATION_STOP_MINUTES.get(train_type, 3)
    
    # Total travel time
    total_minutes = int(travel_time_minutes + stop_time_minutes)
    
    logger.debug(f"Travel time estimate for {train_type}:")
    logger.debug(f"  Distance: {adjusted_distance:.2f} km")
    logger.debug(f"  Terrain factor: {terrain_factor}")
    logger.debug(f"  Adjusted speed: {adjusted_speed:.2f} km/h")
    logger.debug(f"  Base travel time: {travel_time_minutes:.2f} min")
    logger.debug(f"  Station stops: {station_stops}")
    logger.debug(f"  Total time: {total_minutes} min")
    
    return total_minutes


def format_travel_time(minutes):
    """
    Format travel time in minutes to a readable string.
    
    Args:
        minutes: Travel time in minutes
    
    Returns:
        Formatted string like "2h 30m" or "45 min"
    """
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    if hours > 0:
        return f"{hours}h {remaining_minutes}m"
    else:
        return f"{remaining_minutes} min"
