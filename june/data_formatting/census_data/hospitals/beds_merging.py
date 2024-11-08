import pandas as pd
import os
import geopandas as gpd
from shapely.geometry import Point
from june import paths
from tqdm import tqdm

def merge_and_clean_data(occupied_csv, available_csv, locations_dir, output_dir, geography_dir):
    # Read the two CSV files with progress bars
    print("Reading occupied and available CSV files...")
    occupied_df = pd.read_csv(occupied_csv)
    available_df = pd.read_csv(available_csv)

    # Remove rows with Effective_Snapshot_Date before June 2020
    print("Filtering data from June 2020 onwards...")
    occupied_df['Effective_Snapshot_Date'] = pd.to_datetime(occupied_df['Effective_Snapshot_Date'], format='%d/%m/%Y')
    available_df['Effective_Snapshot_Date'] = pd.to_datetime(available_df['Effective_Snapshot_Date'], format='%d/%m/%Y')
    occupied_df = occupied_df[occupied_df['Effective_Snapshot_Date'] >= '2020-06-01']
    available_df = available_df[available_df['Effective_Snapshot_Date'] >= '2020-06-01']

    # Iterate through location CSV files in the locations directory in alphabetical order with progress bar
    print("Reading and merging location files...")
    location_files = sorted([os.path.join(locations_dir, f) for f in os.listdir(locations_dir) if f.endswith('.csv')])
    locations_df_list = []
    for location_file in tqdm(location_files, desc="Merging location files"):
        locations_df_list.append(pd.read_csv(location_file))
    locations_df = pd.concat(locations_df_list, ignore_index=True)

    # Remove spaces from postcodes in both datasets
    print("Removing spaces from postcodes...")

    # Add postcode to both occupied and available dataframes from location data with progress bar
    print("Adding postcodes to dataframes...")
    occupied_df = pd.merge(occupied_df, locations_df[['Code', 'Postcode']], left_on='Organisation_Code', right_on='Code', how='left').drop(columns=['Code'])
    available_df = pd.merge(available_df, locations_df[['Code', 'Postcode']], left_on='Organisation_Code', right_on='Code', how='left').drop(columns=['Code'])
    occupied_df['postcode'] = occupied_df['Postcode'].str.replace(' ', '', regex=False)
    available_df['postcode'] = available_df['Postcode'].str.replace(' ', '', regex=False)
    locations_df['postcode'] = locations_df['Postcode'].str.replace(' ', '', regex=False)

    # Merge occupied and available dataframes
    print("Merging occupied and available dataframes...")
    merged_df = pd.merge(occupied_df, available_df,
                         on=['Organisation_Code', 'Sector', 'Effective_Snapshot_Date', 'postcode'],
                         suffixes=('_Occupied', '_Available'))

    # Group by Organisation_Code and pick one postcode for each group
    print("Grouping by Organisation_Code to find unique postcodes...")
    org_postcode_df = merged_df.groupby('Organisation_Code').first().reset_index()[['Organisation_Code', 'postcode']]

    # Add postcode coordinates to the organisation level dataframe for unique postcodes
    print("Adding postcode coordinates...")
    postcode_coords_csv = os.path.join(geography_dir, 'postcode_coordinates.csv')
    postcode_coords_df = pd.read_csv(postcode_coords_csv)

    # Remove spaces from postcodes in postcode coordinates dataset
    postcode_coords_df['postcode'] = postcode_coords_df['postcode'].str.replace(' ', '', regex=False)

    org_postcode_df = pd.merge(org_postcode_df, postcode_coords_df[['postcode', 'latitude', 'longitude']],
                               left_on='postcode', right_on='postcode', how='left')

    # Handle missing coordinates by finding the closest postcode alphabetically
    print("Handling missing coordinates by finding the closest postcode alphabetically...")
    sorted_postcodes = postcode_coords_df['postcode'].sort_values()
    missing_coords = org_postcode_df[org_postcode_df['latitude'].isna()]
    for idx in tqdm(missing_coords.index, desc="Processing missing coordinates"):
        missing_postcode = org_postcode_df.loc[idx, 'postcode']
        # Find the closest postcode alphabetically
        pos = sorted_postcodes.searchsorted(missing_postcode)
        closest_postcode = None
        if pos < len(sorted_postcodes):
            closest_postcode = sorted_postcodes.iloc[pos]
        if closest_postcode:
            nearest_coords = postcode_coords_df[postcode_coords_df['postcode'] == closest_postcode]
            org_postcode_df.loc[idx, 'latitude'] = nearest_coords['latitude'].values[0]
            org_postcode_df.loc[idx, 'longitude'] = nearest_coords['longitude'].values[0]
        else:
            print(org_postcode_df.loc[idx, 'postcode'])

    # Load MSOA boundaries and determine which MSOA each unique postcode falls into
    print("Determining MSOA for each organisation...")
    msoa_boundaries_path = os.path.join(geography_dir, 'msoa_boundaries.geojson')
    msoa_gdf = gpd.read_file(msoa_boundaries_path)

    # Create GeoDataFrame from organisation-level dataframe to find MSOA
    org_postcode_gdf = gpd.GeoDataFrame(org_postcode_df, geometry=[Point(xy) for xy in zip(org_postcode_df['longitude'], org_postcode_df['latitude'])], crs='EPSG:4326')
    org_postcode_gdf = gpd.sjoin(org_postcode_gdf, msoa_gdf[['MSOA21CD', 'geometry']], how='left', predicate='within')

    # Add MSOA information to the organisation level dataframe
    org_postcode_df['MSOA21CD'] = org_postcode_gdf['MSOA21CD']

    # Add organisation name from locations_df
    org_postcode_df = pd.merge(org_postcode_df, locations_df[['Code', 'Name']], left_on='Organisation_Code', right_on='Code', how='left').drop(columns=['Code'])

    # Calculate first and last recorded snapshot dates for each organisation
    print("Calculating first and last snapshot dates for each organisation...")
    snapshot_dates = merged_df.groupby('Organisation_Code')['Effective_Snapshot_Date'].agg(['min', 'max']).reset_index()
    snapshot_dates = snapshot_dates.rename(columns={'min': 'first_snapshot_date', 'max': 'last_snapshot_date'})

    # Merge snapshot dates back to org_postcode_df
    org_postcode_df = pd.merge(org_postcode_df, snapshot_dates, on='Organisation_Code', how='left')

    # Save unique locations information
    unique_locations_file = os.path.join(output_dir, 'unique_trust_locations.csv')
    org_postcode_df = org_postcode_df.rename(columns={
        'MSOA21CD': 'msoa',
        'Organisation_Code': 'org_code',
        'Name': 'org_name',
        'Postcode': 'postcode'
    })
    org_postcode_df = org_postcode_df[['msoa', 'org_code', 'org_name', 'postcode', 'latitude', 'longitude', 'first_snapshot_date', 'last_snapshot_date']]
    org_postcode_df.to_csv(unique_locations_file, index=False)

    # Merge MSOA information back to the original merged dataframe
    merged_df = pd.merge(merged_df, org_postcode_df[['org_code', 'latitude', 'longitude', 'msoa']], left_on='Organisation_Code', right_on='org_code', how='left').drop(columns=['org_code'])

    # Remove rows where both available and occupied beds are zero for all records of an organisation code
    print("Removing rows with all zero beds...")
    org_codes_with_non_zero = merged_df[(merged_df['Number_Of_Beds_Occupied'] != 0) | (merged_df['Number_Of_Beds_Available'] != 0)]['Organisation_Code'].unique()
    merged_df = merged_df[merged_df['Organisation_Code'].isin(org_codes_with_non_zero)]

    # Calculate average number of beds for each organisation and sector, including postcode, latitude, longitude
    # temp_merged_df = merged_df.drop(columns=['Effective_Snapshot_Date'])
    # avg_beds = temp_merged_df.groupby(['Organisation_Code', 'Sector']).agg(
    #     {
    #         'Number_Of_Beds_Occupied': 'mean',
    #         'Number_Of_Beds_Available': 'mean',
    #         'latitude': 'first',
    #         'longitude': 'first',
    #         'postcode': 'first',
    #         'msoa': 'first'
    #     }
    # ).reset_index()
    # avg_beds = avg_beds.rename(columns={
    #     'Number_Of_Beds_Occupied': 'avg_occupied_beds',
    #     'Number_Of_Beds_Available': 'avg_available_beds'
    # })
    # avg_beds_file = os.path.join(output_dir, 'average_beds_per_organisation.csv')
    # avg_beds.to_csv(avg_beds_file, index=False)
    # merged_df = pd.merge(merged_df, avg_beds[['Organisation_Code', 'Sector', 'avg_occupied_beds', 'avg_available_beds']], on=['Organisation_Code', 'Sector'], how='left')

    # Organize columns as specified and rename them, setting msoa as index and org_code as sub-index
    print("Organizing columns and finalizing data...")
    merged_df = merged_df.rename(columns={
        'MSOA21CD': 'msoa',
        'Organisation_Code': 'org_code',
        'Sector': 'sector',
        'Number_Of_Beds_Occupied': 'occupied_beds',
        'Number_Of_Beds_Available': 'available_beds',
        'postcode': 'postcode'
    })
    merged_df = merged_df[['msoa', 'org_code', 'sector', 'occupied_beds', 'available_beds', 'postcode', 'latitude', 'longitude', 'Effective_Snapshot_Date']]
    merged_df = merged_df.set_index(['msoa', 'org_code']).sort_index()

    # Split data into year directories and quarter files, indexed by MSOA and sub-indexed by Organisation_Code
    print("Splitting data into year and quarter files...")
    for year, year_df in tqdm(merged_df.reset_index().groupby(merged_df.reset_index()['Effective_Snapshot_Date'].dt.year), desc="Processing years"):
        year_dir = os.path.join(output_dir, str(year))
        os.makedirs(year_dir, exist_ok=True)

        for quarter, quarter_df in year_df.groupby((year_df['Effective_Snapshot_Date'].dt.month - 1) // 3 + 1):
            quarter_df = quarter_df.sort_values(by=['msoa', 'org_code'])
            quarter_file = os.path.join(year_dir, f'Q{quarter}_beds.csv')
            quarter_df.drop(columns=['Effective_Snapshot_Date']).to_csv(quarter_file, index=False)

    print(f"Data processing completed and saved to {output_dir}")

# File names
data_file = f'{paths.data_path}/raw_data/NHS_trusts/'
output_dir = f'{paths.data_path}/input/NHS_trusts/'
geography_dir = f'{paths.data_path}/input/geography/'
occupied_csv = f'{data_file}KH03-Occupied-Overnight-only.csv'
available_csv = f'{data_file}KH03-Available-Overnight-only.csv'
locations_dir = f'{data_file}trust_locations_data/'

# Run the merge and clean operation
merge_and_clean_data(occupied_csv, available_csv, locations_dir, output_dir, geography_dir)

print(f'Data processing completed and saved to {output_dir}')
