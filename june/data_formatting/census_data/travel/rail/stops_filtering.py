import pandas as pd
from scipy.spatial.distance import cdist
from june import paths
import numpy as np

# File paths
csv_fp = f'{paths.data_path}/input/travel/raw_unprocessed/Stops.csv'
train_stations_output_fp = f'{paths.data_path}/input/travel/rail/train_stations.csv'

# Load CSV in chunks to prevent memory overload
chunk_size = 100000  # Customize this depending on your memory capacity
stations = []

print("Loading data in chunks...")

phrases_to_remove = [" Rail", " Railway", " Station", " Stations", " (Main Entrance)"]

# Step 1: Load the data in chunks and clean it
for chunk in pd.read_csv(csv_fp, encoding='ISO-8859-1', low_memory=False, chunksize=chunk_size):
    # Filter for active train stations
    chunk_active_RSE_filtered = chunk[(chunk['Status'] == 'active') & (chunk['StopType'].isin(['RSE', 'RLY']))].copy()

    # Remove unwanted phrases from CommonName
    for phrase in phrases_to_remove:
        chunk_active_RSE_filtered['CommonName'] = chunk_active_RSE_filtered['CommonName'].str.replace(phrase, "",
                                                                                                      regex=False)

    stations.append(chunk_active_RSE_filtered)

print("Concatenating chunks...")
df_filtered_stations = pd.concat(stations, ignore_index=True)

# Select specific columns and rename them
df_filtered_stations = df_filtered_stations[['CommonName', 'LocalityName', 'Easting', 'Northing']]
df_filtered_stations = df_filtered_stations.rename(columns={
    'CommonName': 'Station',
    'LocalityName': 'Location',
    'Easting': 'Easting',
    'Northing': 'Northing'
})

# Average Easting and Northing for stations with the same name
df_filtered_stations = df_filtered_stations.groupby('Station').agg({
    'Location': 'first',
    'Easting': 'mean',
    'Northing': 'mean'
}).reset_index()


# Step 2: Merge stations that are within 200m of each other and share the same first 4 letters
def merge_nearby_stations(df, distance_threshold=60):
    """
    Merge train stations that are within a certain distance threshold and share the same first 4 letters.

    Parameters:
        df (pd.DataFrame): DataFrame containing station data with Easting and Northing coordinates.
        distance_threshold (float): Distance in meters to consider stations as duplicates.

    Returns:
        pd.DataFrame: DataFrame with merged stations, averaging the coordinates where appropriate.
    """
    coords = df[['Easting', 'Northing']].to_numpy()
    distances = cdist(coords, coords, metric='euclidean')
    to_merge = []

    # Track which stations have been merged
    merged = np.zeros(len(df), dtype=bool)

    for i in range(len(df)):
        if merged[i]:
            continue

        # Find indices of stations within the distance threshold
        nearby_indices = np.where((distances[i] <= distance_threshold) & (distances[i] > 0))[0]

        # Filter nearby stations based on matching first four letters
        nearby_indices = [idx for idx in nearby_indices if
                          df.iloc[idx]['Station'][:4].lower() == df.iloc[i]['Station'][:4].lower()]

        if len(nearby_indices) > 0:
            # Include the current station
            group_indices = [i] + nearby_indices

            # Mark these stations as merged
            merged[group_indices] = True

            # Extract rows for the group
            group = df.iloc[group_indices]

            # Find the station with the shortest name
            shortest_station_name = group['Station'].str.len().idxmin()
            merged_station = group.loc[shortest_station_name]

            # Create a dictionary for the merged station
            merged_station_data = {
                'Station': merged_station['Station'],
                'Location': merged_station['Location'],
                'Easting': group['Easting'].mean(),
                'Northing': group['Northing'].mean()
            }

            # Append merged station details
            to_merge.append(merged_station_data)
        else:
            # If no nearby stations, append the current station as a dictionary
            to_merge.append(df.iloc[i].to_dict())

    # Return merged stations as a DataFrame
    return pd.DataFrame(to_merge)


print("Merging nearby stations...")
df_merged_stations = merge_nearby_stations(df_filtered_stations)

# Step 3: Save the result to a CSV file
df_merged_stations.to_csv(train_stations_output_fp, index=False)

print("Saved Train Station Stops to:", train_stations_output_fp)
