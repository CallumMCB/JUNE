import pandas as pd
from june import paths

# File paths
csv_fp = f'{paths.data_path}/input/geography/raw_unprocessed/PCD_OA21_LSOA21_MSOA21_LAD_AUG24_UK_LU.csv'  # Replace with your actual CSV file path
area_msoa_coord_output_fp = f'{paths.data_path}/input/geography/area_super_area_coordinates.csv'  # Replace with your desired output file path
area_msoa_region_output_fp = f'{paths.data_path}/input/geography/area_super_area_regions.csv'

# Load CSV in chunks to prevent memory overload
chunk_size = 100000  # Customize this depending on your memory capacity
chunks = []

print("Loading data in chunks...")

for chunk in pd.read_csv(csv_fp, encoding='ISO-8859-1', low_memory=False, chunksize=chunk_size):
    chunk['oa21cd'] = chunk['oa21cd'].astype(str)
    # Remove rows where 'oa21cd' starts with 'S0' or is 'nan'
    chunk_filtered = chunk[(chunk['oa21cd'] != 'nan') & (~chunk['oa21cd'].str.startswith('S0'))]
    chunks.append(chunk_filtered)

print("Concatenating chunks...")
df_filtered = pd.concat(chunks, ignore_index=True)

# Select specific columns and rename them
df_area_msoa = df_filtered.loc[:, ['oa21cd', 'msoa21cd']].rename(columns={'oa21cd': 'area', 'msoa21cd': 'super_area'})
df_area_msoa.sort_values(by='area', inplace=True)
df_area_msoa = df_area_msoa.drop_duplicates(subset='area')

print("Merging with other files...")
areas_coordinates_fp = f'{paths.data_path}/input/geography/area_coordinates.csv'
areas_coordinates_df = pd.read_csv(areas_coordinates_fp)
df_area_msoa_coordinates = pd.merge(df_area_msoa, areas_coordinates_df, on='area', how='left')

areas_region_fp = f'{paths.data_path}/input/geography/raw_unprocessed/OA21_RGN22_LU.csv'
areas_region_df = pd.read_csv(areas_region_fp, low_memory=False)
df_area_msoa_region = pd.merge(df_area_msoa, areas_region_df, left_on='area', right_on='oa21cd', how='left')
df_area_msoa_region.drop(columns=['oa21cd', 'rgn22nmw'], inplace=True)
df_area_msoa_region = df_area_msoa_region.rename(columns={'rgn22cd': 'region code', 'rgn22nm': 'region'})

# Save the modified DataFrame to a new CSV file
print("Saving the modified CSVs...")
df_area_msoa_coordinates.to_csv(area_msoa_coord_output_fp, index=False)
df_area_msoa_region.to_csv(area_msoa_region_output_fp, index=False)

print(f'Modified CSV file saved to: {area_msoa_coord_output_fp}')
print(f'Modified CSV file saved to: {area_msoa_region_output_fp}')
