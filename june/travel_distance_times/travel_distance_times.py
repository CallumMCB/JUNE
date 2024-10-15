import logging
from typing import List, Dict, Tuple, Optional
from shapely.geometry import Point, Polygon
import numpy as np
import pandas as pd
import googlemaps
import openrouteservice

from june import paths
from june.geography import SuperArea, Geography

#Please Add your own API keys here
gmaps = googlemaps.Client(key='AIzaSyDrK9LA1BxhyPeRLMFNjtOc1-khWBg10kY')
ors = openrouteservice.Client(key='5b3ce3597851110001cf6248f96d911f6af6482da55ac46c48eb6f41')

default_hierarchy_filename = (
    paths.data_path / "input/geography/area_super_area_region.csv"
)
default_area_coord_filename = (
    paths.data_path / "input/geography/area_coordinates_sorted.csv"
)
default_superarea_coord_filename = (
    paths.data_path / "input/geography/super_area_coordinates_sorted.csv"
)

logger = logging.getLogger(__name__)

# load london super areas
london_areas = np.loadtxt("../../example_scripts/london_areas.txt", dtype=np.str_)[40:45]

# add King's cross area for station
if "E00004734" not in london_areas:
    london_areas = np.append(london_areas, "E02000187")

# add some people commuting from Cambridge
london_areas = np.concatenate((london_areas, ["E02003719", "E02003720", "E02003721"]))
#
# add Bath as well to have a city with no stations
london_areas = np.concatenate(
    (london_areas, ["E02002988", "E02002989", "E02002990", "E02002991", "E02002992"])
)

class TravelDistanceTimes:
    def __init__(self):
        self.gmaps = gmaps
        self.ors = ors

    def get_isochrone(
            self,
            coordinates: Tuple[float, float],
            profile: str,
            duration: int
    ) -> Polygon:
        """Generate an isochrone for a given set of coordinates using ORS."""
        try:
            isochrone = self.ors.isochrones(
                locations=[coordinates],
                profile=profile,
                range=[duration] # In Seconds
            )
            coordinates_list = isochrone['features'][0]['geometry']['coordinates'][0]
            polygon = Polygon(coordinates_list)
            print("Calculated Polygon")
            return polygon
        except Exception as e:
            logger.error(f"Error fetching isochrone for {coordinates}: {e}")
            exit()

    def is_within_isochrone(
            self,
            coords: Tuple[float, float],
            isochrone: Polygon
    ) -> bool:
        """Check if a destination's coordinates are within the isochrone region."""
        point = Point([coords[1], coords[0]]) # ORS takes [longitude, latitude]
        return isochrone.contains(point)

    def calculate_travel_time_google(
            self,
            origin: Tuple[float, float],
            destination: Tuple[float, float],
            mode: str
    ) -> Optional[float]:
        """Calculate travel time using Google Maps Distance Matrix API."""
        try:
            result = self.gmaps.distance_matrix(
                origins=[origin],
                destinations=[destination],
                mode=mode
            )
            travel_time = result['rows'][0]['elements'][0]['duration']['value'] / 60  # Convert from seconds to minutes
            return travel_time
        except Exception as e:
            logger.error(f"Error calculating travel time from {origin} to {destination} using Google Maps: {e}")
            return None

    def process_super_areas(
            self,
            geography: Geography,
            isochrone_calc: bool
    ):
        """Process each super area, calculate isochrones and travel times, and store results."""
        data = []

        for origin_super_area in geography.super_areas:
            origin_coords = [round(coord, 6) for coord in origin_super_area.coordinates]
            origin_name = origin_super_area.name

            # Get isochrones for both car and public transport using ORS
            if isochrone_calc:
                car_isochrone = self.get_isochrone([origin_coords[1], origin_coords[0]], profile='driving-car', duration=3600) # ORS takes [longitude, latitude]
                # transit_isochrone = self.get_isochrone([origin_coords[1], origin_coords[0]], profile='driving-car',duration=7200) # ORS takes [longitude, latitude]

            else: car_isochrone = np.inf

            for destination_super_area in geography.super_areas:
                if origin_super_area == destination_super_area:
                    continue  # Skip if the origin and destination are the same

                dest_coords = [round(coord, 6) for coord in destination_super_area.coordinates]
                dest_name = destination_super_area.name

                # Calculate travel time using Google Maps Distance Matrix for car and public transport
                car_time, transit_time = None, None

                if car_isochrone == np.inf:
                    car_time = self.calculate_travel_time_google(origin_coords, dest_coords, mode='driving')
                    car_time = round(car_time, 1)

                    # if transit_isochrone and self.is_within_isochrone(dest_coords, transit_isochrone):
                    transit_time = self.calculate_travel_time_google(origin_coords, dest_coords, mode='transit')
                    transit_time = round(transit_time, 1)

                elif car_isochrone and self.is_within_isochrone(dest_coords, car_isochrone):
                    car_time = self.calculate_travel_time_google(origin_coords, dest_coords, mode='driving')
                    car_time = round(car_time, 1)

                # if transit_isochrone and self.is_within_isochrone(dest_coords, transit_isochrone):
                    transit_time = self.calculate_travel_time_google(origin_coords, dest_coords, mode='transit')
                    transit_time = round(transit_time, 1)

                # Only add rows for destinations reachable by at least one method
                if car_time is not None or transit_time is not None:
                    data.append({
                        "Origin": origin_name,
                        "Destination": dest_name,
                        "Car Travel Time (min)": car_time if car_time is not None else 'None',
                        "Public Transport Travel Time (min)": transit_time if transit_time is not None else 'None'
                    })

        # Save the results to a CSV file
        df = pd.DataFrame(data)
        df.to_csv("travel_times_no_isochrone.csv", index=False)
        logger.info("CSV file created: travel_times_no_isochrone.csv")

# Example usage
if __name__ == "__main__":
    # Load the geography object from file (assuming this is a valid Geography instance)
    geography = Geography.from_file({"super_area": london_areas})

    # Create an instance of TravelDistanceTimes and process the geography
    travel_distance_times_instance = TravelDistanceTimes()
    travel_distance_times_instance.process_super_areas(geography, isochrone_calc=False)


