import pandas as pd
from june import paths

# File paths
csv_fp = f'{paths.data_path}/raw_data/geography/PCD_OA21_LSOA21_MSOA21_LAD_AUG24_UK_LU.csv'
area_msoa_coord_output_fp = f'{paths.data_path}/input/geography/oa_msoa_lad_coordinates.csv'
area_msoa_region_output_fp = f'{paths.data_path}/input/geography/oa_msoa_lad_regions.csv'

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
df_area_msoa = df_filtered.loc[:, ['oa21cd', 'msoa21cd', 'ladcd', 'ladnm']].rename(columns={'oa21cd': 'area', 'msoa21cd': 'super_area', 'ladnm': 'LAD name', 'ladcd': 'LAD code'})

df_area_msoa.sort_values(by='area', inplace=True)
df_area_msoa = df_area_msoa.drop_duplicates(subset='area')

# Manually add missing LAD names for specific LAD codes
missing_lad_names = {
    'E06000063': 'Isles of Scilly',
    'E06000064': 'Buckinghamshire',
    'E06000065': 'West Northamptonshire',
    'E06000066': 'Somerset'
}

df_area_msoa['LAD name'] = df_area_msoa.apply(
    lambda row: missing_lad_names[row['LAD code']] if pd.isna(row['LAD name']) and row['LAD code'] in missing_lad_names else row['LAD name'],
    axis=1
)

# Print any still missing LAD names
missing_lads = df_area_msoa[df_area_msoa['LAD name'].isna()]['LAD code'].unique()
if len(missing_lads) > 0:
    print(f"The following LAD codes are still missing names: {missing_lads}")
else:
    print("No missing LAD names.")

print("Merging with other files...")
areas_coordinates_fp = f'{paths.data_path}/input/geography/oa_coordinates.csv'
areas_coordinates_df = pd.read_csv(areas_coordinates_fp)
df_area_msoa_coordinates = pd.merge(df_area_msoa, areas_coordinates_df, on='area', how='left')

areas_region_fp = f'{paths.data_path}/raw_data/geography/OA21_RGN22_LU.csv'
areas_region_df = pd.read_csv(areas_region_fp, low_memory=False)
df_area_msoa_region = pd.merge(df_area_msoa, areas_region_df, left_on='area', right_on='oa21cd', how='left')
df_area_msoa_region.drop(columns=['oa21cd', 'rgn22nmw'], inplace=True)
df_area_msoa_region = df_area_msoa_region.rename(columns={'rgn22cd': 'region code', 'rgn22nm': 'region name'})

# Save the modified DataFrame to a new CSV file
print("Saving the modified CSVs...")
df_area_msoa_coordinates.to_csv(area_msoa_coord_output_fp, index=False)
df_area_msoa_region.to_csv(area_msoa_region_output_fp, index=False)

print(f'Modified CSV file saved to: {area_msoa_coord_output_fp}')
print(f'Modified CSV file saved to: {area_msoa_region_output_fp}')
