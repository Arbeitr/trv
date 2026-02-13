"""
Project File I/O (.trv v3 format)
"""

import os
import json
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECTS_DIR = os.path.join(BASE_DIR, "data", "projects")


def save_project_file(filename, project_data):
    """
    Save project data to a .trv file.
    
    Args:
        filename: Filename (will be saved in data/projects/)
        project_data: Project data dictionary
    
    Returns:
        Full filepath where project was saved
    """
    if not filename.endswith('.trv'):
        filename += '.trv'
    
    filepath = os.path.join(PROJECTS_DIR, filename)
    
    # Ensure directory exists
    os.makedirs(PROJECTS_DIR, exist_ok=True)
    
    # Add/update metadata
    if 'metadata' not in project_data:
        project_data['metadata'] = {}
    
    project_data['version'] = '3.0'
    project_data['metadata']['modified'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    
    if 'created' not in project_data['metadata']:
        project_data['metadata']['created'] = project_data['metadata']['modified']
    
    if 'region' not in project_data['metadata']:
        project_data['metadata']['region'] = 'germany'
    
    # Save to file
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(project_data, f, indent=2, ensure_ascii=False)
    
    return filepath


def load_project_file(filename):
    """
    Load project data from a .trv file.
    
    Args:
        filename: Filename in data/projects/ directory
    
    Returns:
        Project data dictionary
    """
    if not filename.endswith('.trv'):
        filename += '.trv'
    
    filepath = os.path.join(PROJECTS_DIR, filename)
    
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Project file not found: {filename}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        project_data = json.load(f)
    
    # Validate version
    version = project_data.get('version', '2.0')
    if not version.startswith('3.'):
        # Could add migration logic here for older formats
        pass
    
    return project_data


def create_project_structure(name, stations, connections):
    """
    Create a new project data structure in v3 format.
    
    Args:
        name: Project name
        stations: Dict of {station_id: {name, lat, lon}}
        connections: List of connection dicts
    
    Returns:
        Project data dictionary in v3 format
    """
    return {
        "version": "3.0",
        "metadata": {
            "name": name,
            "created": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            "modified": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            "region": "germany"
        },
        "stations": stations,
        "connections": connections
    }
