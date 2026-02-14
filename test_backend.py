"""
Unit tests for the new Flask-based Train Route Visualizer backend.
"""

import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.travel_time import (
    haversine_distance, estimate_travel_time, format_travel_time,
    get_terrain_factor, get_region_from_coordinates,
    TRAIN_TYPES
)


class TestTravelTime(unittest.TestCase):
    """Test travel time calculation functions."""
    
    def test_haversine_distance(self):
        """Test haversine distance calculation."""
        # Frankfurt to Mannheim (approximately 78 km)
        frankfurt = (8.6821, 50.1109)
        mannheim = (8.4660, 49.4875)
        
        distance = haversine_distance(frankfurt, mannheim)
        
        # Should be around 75-80 km
        self.assertGreater(distance, 70)
        self.assertLess(distance, 85)
    
    def test_estimate_travel_time(self):
        """Test travel time estimation."""
        # Frankfurt to Mannheim
        frankfurt = (8.6821, 50.1109)
        mannheim = (8.4660, 49.4875)
        
        # Test with different train types
        time_ice = estimate_travel_time(frankfurt, mannheim, "ICE")
        time_re = estimate_travel_time(frankfurt, mannheim, "RE")
        time_rb = estimate_travel_time(frankfurt, mannheim, "RB")
        
        # ICE should be fastest, RB slowest
        self.assertLess(time_ice, time_re)
        self.assertLess(time_re, time_rb)
        
        # ICE time should be reasonable (20-40 minutes for ~75km)
        self.assertGreater(time_ice, 15)
        self.assertLess(time_ice, 50)
    
    def test_format_travel_time(self):
        """Test travel time formatting."""
        self.assertEqual(format_travel_time(30), "30 min")
        self.assertEqual(format_travel_time(90), "1h 30m")
        self.assertEqual(format_travel_time(120), "2h 0m")
        self.assertEqual(format_travel_time(0), "0 min")
    
    def test_get_region_from_coordinates(self):
        """Test region detection from coordinates."""
        # Munich coordinates (Bayern)
        munich = (11.5820, 48.1351)
        region = get_region_from_coordinates(munich)
        self.assertEqual(region, "Bayern")
        
        # Hamburg area (should be Hamburg or Niedersachsen)
        hamburg = (9.9937, 53.5511)
        region = get_region_from_coordinates(hamburg)
        self.assertIn(region, ["Hamburg", "Niedersachsen"], 
                     f"Expected Hamburg region area, got {region}")
    
    def test_terrain_factor(self):
        """Test terrain factor calculation."""
        # Berlin to Hamburg (flat)
        berlin = (13.4050, 52.5200)
        hamburg = (9.9937, 53.5511)
        
        factor = get_terrain_factor(berlin, hamburg)
        # Should be flat terrain (1.0)
        self.assertLessEqual(factor, 1.1)
        
        # Munich area (mountainous)
        munich = (11.5820, 48.1351)
        innsbruck = (11.3927, 47.2692)
        
        factor = get_terrain_factor(munich, innsbruck)
        # Should have higher factor for mountains
        self.assertGreaterEqual(factor, 1.15)
    
    def test_train_types_exist(self):
        """Test that all train types are defined."""
        required_types = ['ICE', 'IC', 'RE', 'RB']
        for train_type in required_types:
            self.assertIn(train_type, TRAIN_TYPES)
            self.assertIn('speed_factor', TRAIN_TYPES[train_type])
            self.assertIn('color', TRAIN_TYPES[train_type])


class TestProjectIO(unittest.TestCase):
    """Test project file I/O."""
    
    def test_create_project_structure(self):
        """Test project structure creation."""
        from backend.project_io import create_project_structure
        
        stations = {
            'sta_1': {'name': 'Frankfurt Hbf', 'lat': 50.1109, 'lon': 8.6821},
            'sta_2': {'name': 'Mannheim Hbf', 'lat': 49.4875, 'lon': 8.4660}
        }
        
        connections = [
            {
                'id': 'conn_1',
                'from': 'sta_1',
                'to': 'sta_2',
                'train_type': 'ICE'
            }
        ]
        
        project = create_project_structure('Test Project', stations, connections)
        
        self.assertEqual(project['version'], '3.0')
        self.assertEqual(project['metadata']['name'], 'Test Project')
        self.assertEqual(project['stations'], stations)
        self.assertEqual(project['connections'], connections)


if __name__ == '__main__':
    unittest.main(verbosity=2)
