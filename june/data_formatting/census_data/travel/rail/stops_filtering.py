import pandas as pd
from scipy.spatial.distance import cdist
from june import paths
import numpy as np

# File paths
csv_fp = f'{paths.data_path}/raw_data/travel/Stops.csv'
train_stations_output_fp = f'{paths.data_path}/input/travel/rail/train_stations.csv'
underground_metro_stations_output_fp = f'{paths.data_path}/input/travel/rail/underground_metro_stations.csv'

# Load CSV in chunks to prevent memory overload
chunk_size = 100000  # Customize this depending on your memory capacity
train_stations = []
underground_metro_stations = []

print("Loading data in chunks...")

phrases_to_remove = [" Rail", " Railway", " Station", " Stations", "corner", "cnr", "DRT", "Stop", "Stance", "Stand", "Bay", "Platform", "entrance", "main entrance", "side entrance", "front entrance", "back entrance", "rear entrance", "north entrance", "east entrance", "south entrance", "west entrance", "north east entrance", "NE entrance", "north west entrance", "NW entrance", "south east entrance", "SE entrance", "south west entrance", "SW entrance", "N entrance", "E entrance", "S entrance", "W entrance", "arrivals", "departures", "Northbound", "N-bound", "Southbound", "Eastbound", "E-bound", "Westbound", "W bound", "NE bound", "NW bound", "SW bound", "N-bound", "E-bound", "S-bound", "W-bound", "NE-bound", "SE-bound", "SW-bound", "NW-bound", "Inner Circle", "Outer Circle", "Quay", "Berth", "Gate"]

# Step 1: Load the data in chunks and clean it
for chunk in pd.read_csv(csv_fp, encoding='ISO-8859-1', low_memory=False, chunksize=chunk_size):
    # Filter for active train and underground/metro stations
    chunk_active_filtered = chunk[(chunk['Status'] == 'active') & (chunk['StopType'].isin(['RSE', 'RLY', 'MET', 'TMU']))].copy()

    # Remove unwanted phrases from CommonName
    for phrase in phrases_to_remove:
        chunk_active_filtered['CommonName'] = chunk_active_filtered['CommonName'].str.replace(phrase, "", regex=False)
    chunk_active_filtered['CommonName'] = chunk_active_filtered['CommonName'].str.replace("()", "", regex=False)

    # Append filtered train and underground/metro stations
    train_stations.append(chunk_active_filtered[chunk_active_filtered['StopType'].isin(['RSE', 'RLY'])])
    underground_metro_stations.append(chunk_active_filtered[chunk_active_filtered['StopType'].isin(['MET', 'TMU'])])

print("Concatenating chunks...")
df_filtered_train_stations = pd.concat(train_stations, ignore_index=True)
df_filtered_um_stations = pd.concat(underground_metro_stations, ignore_index=True)

# Select specific columns and rename them
df_filtered_train_stations = df_filtered_train_stations[['CommonName', 'LocalityName', 'Easting', 'Northing']]
df_filtered_train_stations = df_filtered_train_stations.rename(columns={
    'CommonName': 'Station',
    'LocalityName': 'Location',
    'Easting': 'Easting',
    'Northing': 'Northing'
})
df_filtered_um_stations = df_filtered_um_stations[['CommonName', 'LocalityName', 'Easting', 'Northing']]
df_filtered_um_stations = df_filtered_um_stations.rename(columns={
    'CommonName': 'Station',
    'LocalityName': 'Location',
    'Easting': 'Easting',
    'Northing': 'Northing'
})

# Average Easting and Northing for stations with the same name
df_filtered_train_stations = df_filtered_train_stations.groupby('Station').agg({
    'Location': 'first',
    'Easting': 'mean',
    'Northing': 'mean'
}).reset_index()
df_filtered_um_stations = df_filtered_um_stations.groupby('Station').agg({
    'Location': 'first',
    'Easting': 'mean',
    'Northing': 'mean'
}).reset_index()


def word_overlap(name1, name2):
    """
    Calculate the word overlap ratio between two station names.

    Parameters:
    name1 (str): First station name.
    name2 (str): Second station name.

    Returns:
    float: Ratio of matching words to the total number of words in the shorter name.
    """
    words1 = set(name1.lower().split())
    words2 = set(name2.lower().split())
    common_words = words1.intersection(words2)
    return len(common_words) / min(len(words1), len(words2))

# Step 2: Merge stations that are within 200m of each other and share the same first 4 letters
def merge_nearby_stations(df, distance_threshold=200):
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
        nearby_indices = [
            idx for idx in nearby_indices
            if word_overlap(df.iloc[idx]['Station'], df.iloc[i]['Station']) >= 0.5
        ]

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
df_merged_train_stations = merge_nearby_stations(df_filtered_train_stations)
df_merged_ug_stations = merge_nearby_stations(df_filtered_um_stations)

# Step 3: Save the result to a CSV file
df_merged_train_stations.to_csv(train_stations_output_fp, index=False)
df_merged_ug_stations.to_csv(underground_metro_stations_output_fp, index=False)

print("Saved Train Station Stops to:", train_stations_output_fp)
print("Saved UG Station Stops to:", underground_metro_stations_output_fp)
