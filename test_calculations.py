import logging
import unittest
from map_germany_plz_integrated_ui import RouteData, DEFAULT_TRAVEL_TIMES, TRAIN_TYPES

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class TestRouteCalculations(unittest.TestCase):

    def setUp(self):
        self.route_data = RouteData()

    def test_travel_time_accuracy(self):
        """Test the accuracy of travel time calculations."""
        for (city1, city2), predefined_time in DEFAULT_TRAVEL_TIMES.items():
            calculated_time = self.route_data.get_travel_time(city1, city2)

            # Convert predefined time to minutes for comparison
            predefined_minutes = predefined_time
            if isinstance(predefined_time, str):
                hours, minutes = 0, 0
                if "h" in predefined_time:
                    time_parts = predefined_time.split("h")
                    hours = int(time_parts[0].strip())
                    minutes = int(time_parts[1].replace("m", "").strip()) if "m" in time_parts[1] else 0
                elif "min" in predefined_time:
                    minutes = int(predefined_time.replace("min", "").strip())
                predefined_minutes = hours * 60 + minutes

            # Convert calculated time to minutes for comparison
            calculated_minutes = 0
            if "h" in calculated_time:
                time_parts = calculated_time.split("h")
                hours = int(time_parts[0].strip())
                minutes = int(time_parts[1].replace("m", "").strip()) if "m" in time_parts[1] else 0
                calculated_minutes = hours * 60 + minutes
            elif "min" in calculated_time:
                calculated_minutes = int(calculated_time.replace("min", "").strip())

            # Assert the difference is within an acceptable range (e.g., 5 minutes)
            self.assertAlmostEqual(predefined_minutes, calculated_minutes, delta=5,
                                   msg=f"Mismatch for {city1} -> {city2}: Predefined={predefined_minutes} min, Calculated={calculated_minutes} min")

if __name__ == "__main__":
    unittest.main(verbosity=2)
