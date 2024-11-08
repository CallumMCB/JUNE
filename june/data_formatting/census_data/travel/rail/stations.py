import pandas as pd
from june import paths
from scipy.spatial import KDTree
import numpy as np
from math import radians, sin, cos, sqrt, atan2
from pyproj import Transformer

# File paths
train_stations_fp = f'{paths.data_path}/input/travel/rail/train_stations.csv'
underground_metro_stations_fp = f'{paths.data_path}/input/travel/rail/underground_metro_stations.csv'
postcode_coords_fp = f'{paths.data_path}/input/geography/postcode_coordinates.csv'
super_area_centroids_fp = f'{paths.data_path}/input/geography/super_area_centroids.csv'
train_output_fp = f'{paths.data_path}/input/travel/rail/train_stations_processed.csv'
um_output_fp = f'{paths.data_path}/input/travel/rail/underground_metro_stations_processed.csv'

# Load CSV in chunks to prevent memory overload
chunk_size = 100000  # Customize this depending on your memory capacity
train_stations = []
underground_metro_stations = []

print("Loading data in chunks...")
for chunk in pd.read_csv(train_stations_fp, encoding='ISO-8859-1', low_memory=False, chunksize=chunk_size):
    train_stations.append(chunk)
for chunk in pd.read_csv(underground_metro_stations_fp, encoding='ISO-8859-1', low_memory=False, chunksize=chunk_size):
    underground_metro_stations.append(chunk)

print("Concatenating chunks...")
df_filtered_train_stations = pd.concat(train_stations, ignore_index=True)
df_filtered_um_stations = pd.concat(underground_metro_stations, ignore_index=True)

# Load postcode coordinates
print("Loading postcode coordinates...")
df_postcodes = pd.read_csv(postcode_coords_fp, encoding='ISO-8859-1', low_memory=False)

# Drop rows with None (NaN) values in Latitude or Longitude
df_postcodes = df_postcodes.dropna(subset=['latitude', 'longitude'])

# Create a KDTree for postcode coordinates for fast lookup
postcode_coords = df_postcodes[['latitude', 'longitude']].to_numpy()
postcode_tree = KDTree(np.radians(postcode_coords))

# Set up transformer to convert BNG (British National Grid) to WGS84 (longitude, latitude)
transformer = Transformer.from_crs('epsg:27700', 'epsg:4326', always_xy=True)

# Function to convert station coordinates and find closest postcodes
def convert_find_postcode(df):
    closest_postcodes = []  # Reset list for each dataframe
    for _, station_row in df.iterrows():
        # Convert Easting/Northing to Latitude/Longitude for postcode lookup
        lon, lat = transformer.transform(station_row['Easting'], station_row['Northing'])
        station_coords = [lat, lon]
        distance, index = postcode_tree.query(np.radians(station_coords))
        closest_postcode_row = df_postcodes.iloc[index]

        closest_postcodes.append({
            'Station': station_row['Station'],
            'Location': station_row['Location'],
            'Easting': station_row['Easting'],
            'Northing': station_row['Northing'],
            'postcode': closest_postcode_row['postcode'],
            'distance': distance
        })

    # Create dataframe with closest postcodes
    df_closest_postcodes = pd.DataFrame(closest_postcodes)
    return df_closest_postcodes

# Find the closest postcodes for each train and underground station
print("Finding closest postcodes for train and underground stations...")
df_train_closest_pc = convert_find_postcode(df_filtered_train_stations)
df_um_closest_pc = convert_find_postcode(df_filtered_um_stations)

# Load MSOA centroid coordinates
print("Loading MSOA centroid coordinates...")
df_centroids = pd.read_csv(super_area_centroids_fp, low_memory=False)

# Ensure correct column names
df_centroids = df_centroids.rename(columns={'X': 'easting', 'Y': 'northing'})

# Create a KDTree for train station coordinates for fast lookup
train_station_coords = df_filtered_train_stations[['Easting', 'Northing']].to_numpy()
um_station_coords = df_filtered_um_stations[['Easting', 'Northing']].to_numpy()
train_station_tree = KDTree(train_station_coords)
um_station_tree = KDTree(um_station_coords)

# Function to calculate Haversine distance
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # Radius of Earth in kilometers
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

# Find the nearest n train stations for each MSOA centroid

def find_nearest_stations(df, tree, n, max_distance):
    nearest_stations_info = []
    for _, centroid_row in df_centroids.iterrows():
        centroid_coords = [centroid_row['easting'], centroid_row['northing']]
        distances, indices = tree.query(centroid_coords, k=n)

        # Ensure indices are iterable if KDTree returns a single value
        if np.isscalar(indices):
            indices = [indices]

        for index in indices:
            if index >= len(df):
                # Skip if index is out of bounds
                continue

            nearest_station_row = df.iloc[index]
            # Convert centroid Easting/Northing to Latitude/Longitude
            lon_centroid, lat_centroid = transformer.transform(centroid_row['easting'], centroid_row['northing'])
            # Convert station Easting/Northing to Latitude/Longitude
            lon_station, lat_station = transformer.transform(nearest_station_row['Easting'], nearest_station_row['Northing'])
            # Calculate Haversine distance
            haversine_distance = haversine(lat_centroid, lon_centroid, lat_station, lon_station)
            if haversine_distance <= max_distance:
                # Find the closest postcode for the nearest train station
                station_coords = [lat_station, lon_station]
                postcode_distance, postcode_index = postcode_tree.query(np.radians(station_coords))
                closest_postcode_row = df_postcodes.iloc[postcode_index]

                nearest_stations_info.append({
                    'msoa': centroid_row['super_area'],
                    'centroid_easting': centroid_row['easting'],
                    'centroid_northing': centroid_row['northing'],
                    'station': nearest_station_row['Station'],
                    'station_easting': nearest_station_row['Easting'],
                    'station_northing': nearest_station_row['Northing'],
                    'postcode': closest_postcode_row['postcode'],
                    'station_postcode_distance': postcode_distance,
                    'distance_to_msoa_centroid': haversine_distance
                })

    return pd.DataFrame(nearest_stations_info)

# Create dataframe with nearest train stations for each MSOA
print("Finding nearest train stations for each MSOA...")
df_nearest_train_stations = find_nearest_stations(df_filtered_train_stations, train_station_tree, n=2, max_distance=4)
df_nearest_um_stations = find_nearest_stations(df_filtered_um_stations, um_station_tree, n=1, max_distance =3)

# Save the result to a CSV file
df_nearest_train_stations.to_csv(train_output_fp, index=False)
df_nearest_um_stations.to_csv(um_output_fp, index=False)

print("Nearest train stations for each MSOA saved to:", train_output_fp)
print("Nearest underground & metro stations for each MSOA saved to:", um_output_fp)
