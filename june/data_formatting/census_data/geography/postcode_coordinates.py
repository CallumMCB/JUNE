import pandas as pd
from june import paths

# File paths
csv_fp = f'{paths.data_path}/raw_data/geography/ONS_postcodes_2022.csv'
postcode_coord_opfp = f'{paths.data_path}/input/geography/postcode_coordinates.csv'

# Load CSV in chunks to prevent memory overload
chunk_size = 100000  # Customize this depending on your memory capacity
chunks = []

print("Loading data in chunks...")

for chunk in pd.read_csv(csv_fp, encoding='ISO-8859-1', low_memory=False, chunksize=chunk_size):
    chunk = chunk.loc[:, ['pcd', 'lat', 'long']].rename(columns={'pcd':'postcode', 'lat': 'latitude', 'long': 'longitude'})
    chunks.append(chunk)

print("Concatenating chunks...")
postcode_coords_df = pd.concat(chunks, ignore_index=True)

postcode_coords_df.sort_values(by='postcode', inplace=True)

print("Saving the modified CSVs...")
postcode_coords_df.to_csv(postcode_coord_opfp, index=False)
