# PART 1: Filtering Care Homes

import pandas as pd
from tqdm import tqdm
from june import paths

# Define the file paths
input_file = f'{paths.data_path}/raw_data/care_facilities/01_March_21_HSCA_active_locations.xlsx'
output_file = f'{paths.data_path}/raw_data/care_facilities/beds_type_locations_filtered.csv'
sheet_name = 'HSCA Active Locations'

# Load data
with tqdm(total=1, desc="Reading Excel file") as pbar:
    df = pd.read_excel(input_file, sheet_name=sheet_name)
    pbar.update(1)

# Initialize progress tracker
total_rows = len(df)
tqdm.pandas(desc="Processing rows")

# Filter rows where the 'Care home?' column is 'Y' and coordinates are not empty
with tqdm(total=total_rows, desc="Filtering care homes") as pbar:
    df_filtered = df[(df['Care home?'] == 'Y') & df['Location Latitude'].notna() & df['Location Longitude'].notna()]
    pbar.update(len(df_filtered))

# Keep only the specified columns
columns_to_keep = [
    'Location Name',
    'Care homes beds',
    'Location Type/Sector',
    'Location Primary Inspection Category',
    'Location Region',
    'Location Local Authority',
    'Location Latitude',
    'Location Longitude',
    'Service type - Care home service with nursing'
]
with tqdm(total=len(df_filtered), desc="Keeping specified columns") as pbar:
    df_filtered = df_filtered[columns_to_keep]
    pbar.update(len(df_filtered))

# Save the filtered DataFrame to a CSV file
df_filtered.to_csv(output_file, index=False)
print(f"Filtered data saved to: {output_file}")