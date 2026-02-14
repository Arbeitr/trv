"""
Routing with NetworkX and Overpass Corridor Queries
"""

import logging
import networkx as nx
from shapely.geometry import LineString
from shapely.ops import linemerge
from backend.overpass_client import query_overpass
from backend.station_index import get_station_by_name
from backend.travel_time import estimate_travel_time, format_travel_time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calculate_bbox_corridor(lat1, lon1, lat2, lon2, padding=0.2):
    """
    Calculate bounding box for corridor between two points with padding.
    
    Args:
        lat1, lon1: First point coordinates
        lat2, lon2: Second point coordinates
        padding: Padding in degrees (default 0.2 ≈ 20km)
    
    Returns:
        Tuple of (south, west, north, east)
    """
    south = min(lat1, lat2) - padding
    north = max(lat1, lat2) + padding
    west = min(lon1, lon2) - padding
    east = max(lon1, lon2) + padding
    
    return (south, west, north, east)


def query_railway_routes(bbox):
    """
    Query Overpass for railway route relations in a bounding box.
    
    Args:
        bbox: Tuple of (south, west, north, east)
    
    Returns:
        GeoJSON-like data structure with railway ways
    """
    south, west, north, east = bbox
    
    # Overpass query for railway routes in corridor
    query = f"""
    [out:json][timeout:90];
    (
      way["railway"~"rail|light_rail|subway|tram"]["service"!~".*"]["usage"~"main|branch"]({south},{west},{north},{east});
      way["railway"~"rail|light_rail"]["service"!~".*"]({south},{west},{north},{east});
    );
    out geom;
    """
    
    logger.info(f"Querying railway routes in bbox: {bbox}")
    
    try:
        response = query_overpass(query)
        return response
    except Exception as e:
        logger.error(f"Failed to query railway routes: {e}")
        return None


def build_graph_from_overpass(overpass_data):
    """
    Build a NetworkX graph from Overpass railway data.
    
    Args:
        overpass_data: Response from Overpass API
    
    Returns:
        NetworkX Graph with railway network
    """
    G = nx.Graph()
    
    if not overpass_data or 'elements' not in overpass_data:
        return G
    
    for element in overpass_data['elements']:
        if element['type'] == 'way' and 'geometry' in element:
            coords = [(node['lon'], node['lat']) for node in element['geometry']]
            
            # Add edges between consecutive nodes
            for i in range(len(coords) - 1):
                node1 = coords[i]
                node2 = coords[i + 1]
                
                # Calculate edge length
                from backend.travel_time import haversine_distance
                length = haversine_distance(node1, node2)
                
                # Add edge with length as weight
                G.add_edge(node1, node2, length=length)
    
    logger.info(f"Built graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G


def find_nearest_node(G, target_coord):
    """
    Find the nearest node in the graph to a target coordinate.
    
    Args:
        G: NetworkX graph
        target_coord: Tuple of (lon, lat)
    
    Returns:
        Nearest node coordinate tuple
    """
    from backend.travel_time import haversine_distance
    
    if not G.nodes():
        return None
    
    min_dist = float('inf')
    nearest_node = None
    
    for node in G.nodes():
        dist = haversine_distance(node, target_coord)
        if dist < min_dist:
            min_dist = dist
            nearest_node = node
    
    return nearest_node


def route_on_graph(G, start_coord, end_coord):
    """
    Find shortest path on railway graph between two coordinates.
    
    Args:
        G: NetworkX graph
        start_coord: Start coordinate tuple (lon, lat)
        end_coord: End coordinate tuple (lon, lat)
    
    Returns:
        Tuple of (path_coords, distance_km, quality)
        where quality is "rail", "rail_approx", or None (for fallback)
    """
    # Find nearest nodes
    start_node = find_nearest_node(G, start_coord)
    end_node = find_nearest_node(G, end_coord)
    
    if not start_node or not end_node:
        logger.warning("Could not find nodes in graph")
        return None, 0, None
    
    # Check if path exists
    if not nx.has_path(G, start_node, end_node):
        logger.warning("No path found in graph")
        
        # Try using largest connected component
        if len(G) > 0:
            largest_cc = max(nx.connected_components(G), key=len)
            G_largest = G.subgraph(largest_cc).copy()
            
            # Re-snap to largest component
            start_node = find_nearest_node(G_largest, start_coord)
            end_node = find_nearest_node(G_largest, end_coord)
            
            if start_node and end_node and nx.has_path(G_largest, start_node, end_node):
                try:
                    path = nx.shortest_path(G_largest, start_node, end_node, weight='length')
                    distance = nx.shortest_path_length(G_largest, start_node, end_node, weight='length')
                    return path, distance, "rail_approx"
                except nx.NetworkXError:
                    pass
        
        return None, 0, None
    
    # Find shortest path
    try:
        path = nx.shortest_path(G, start_node, end_node, weight='length')
        distance = nx.shortest_path_length(G, start_node, end_node, weight='length')
        
        logger.info(f"Found path: {len(path)} nodes, {distance:.2f} km")
        return path, distance, "rail"
        
    except nx.NetworkXNoPath:
        logger.warning("No path found")
        return None, 0, None


def simplify_geometry(coords, tolerance=0.001):
    """
    Simplify geometry using Douglas-Peucker algorithm.
    
    Args:
        coords: List of (lon, lat) tuples
        tolerance: Simplification tolerance (default 0.001 ≈ 100m)
    
    Returns:
        Simplified list of coordinates
    """
    if len(coords) < 3:
        return coords
    
    try:
        line = LineString(coords)
        simplified = line.simplify(tolerance, preserve_topology=True)
        return list(simplified.coords)
    except Exception as e:
        logger.warning(f"Geometry simplification failed: {e}")
        return coords


def calculate_route_geometry(from_station_data, to_station_data, train_type="RE", force_refresh=False):
    """
    Calculate route geometry between two stations.
    
    Args:
        from_station_data: Dict with station info {name, lat, lon}
        to_station_data: Dict with station info {name, lat, lon}
        train_type: Train type string (default "RE")
        force_refresh: Force refresh from Overpass (skip cache)
    
    Returns:
        Dict with route information including geometry and travel time
    """
    from_lat = from_station_data['lat']
    from_lon = from_station_data['lon']
    to_lat = to_station_data['lat']
    to_lon = to_station_data['lon']
    
    from_coord = (from_lon, from_lat)
    to_coord = (to_lon, to_lat)
    
    # Calculate corridor bounding box
    bbox = calculate_bbox_corridor(from_lat, from_lon, to_lat, to_lon)
    
    # Query Overpass for railway data
    overpass_data = query_railway_routes(bbox)
    
    if not overpass_data:
        # Fallback to straight line
        logger.warning("No railway data found, using straight line")
        geometry = [[from_lon, from_lat], [to_lon, to_lat]]
        geometry_simplified = geometry
        
        travel_time_minutes = estimate_travel_time(from_coord, to_coord, train_type)
        from backend.travel_time import haversine_distance
        distance_km = haversine_distance(from_coord, to_coord)
        
        return {
            "geometry": geometry,
            "geometry_simplified": geometry_simplified,
            "distance_km": distance_km,
            "travel_time_minutes": travel_time_minutes,
            "route_quality": "straight_line"
        }
    
    # Build graph and route
    G = build_graph_from_overpass(overpass_data)
    path, distance_km, route_quality = route_on_graph(G, from_coord, to_coord)
    
    if not path or route_quality is None:
        # Fallback to straight line
        logger.warning("Routing failed, using straight line")
        geometry = [[from_lon, from_lat], [to_lon, to_lat]]
        geometry_simplified = geometry
        
        travel_time_minutes = estimate_travel_time(from_coord, to_coord, train_type)
        from backend.travel_time import haversine_distance
        distance_km = haversine_distance(from_coord, to_coord)
        
        return {
            "geometry": geometry,
            "geometry_simplified": geometry_simplified,
            "distance_km": distance_km,
            "travel_time_minutes": travel_time_minutes,
            "route_quality": "straight_line"
        }
    
    # Convert path to geometry
    geometry = [[lon, lat] for lon, lat in path]
    geometry_simplified = simplify_geometry(path)
    geometry_simplified = [[lon, lat] for lon, lat in geometry_simplified]
    
    # Calculate travel time with actual distance
    travel_time_minutes = estimate_travel_time(from_coord, to_coord, train_type, distance_km)
    
    return {
        "geometry": geometry,
        "geometry_simplified": geometry_simplified,
        "distance_km": distance_km,
        "travel_time_minutes": travel_time_minutes,
        "route_quality": route_quality
    }
