import pandas as pd
import os
import geopandas as gpd
from shapely.geometry import Point
from june import paths
from tqdm import tqdm
import re
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

def load_data(trust_sites_csv, unique_trust_locations_csv):
    print("Loading trust sites data...")
    trust_sites_df = pd.read_csv(trust_sites_csv)

    print("Loading unique trust locations data...")
    unique_trust_locations_df = pd.read_csv(unique_trust_locations_csv)

    return trust_sites_df, unique_trust_locations_df

def clean_postcodes(df, postcode_column):
    print("Removing spaces from postcodes...")
    df[postcode_column] = df[postcode_column].str.replace(' ', '', regex=False)
    return df

def filter_trust_sites(trust_sites_df, unique_trust_locations_df, location_type):
    print(f"Filtering trust sites based on operation codes for {location_type}...")
    filtered_df = trust_sites_df[trust_sites_df['Is Operated By - Code'].isin(unique_trust_locations_df['org_code'])]

    print(f"Filtering {location_type} sites...")
    filtered_df['Name'] = filtered_df['Name'].apply(lambda x: filter_location_name(x, location_type))
    filtered_df = filtered_df[filtered_df['Name'].str.contains(location_type.upper(), case=False, na=False)]

    return filtered_df

def add_postcode_coordinates(filtered_df, postcode_coords_csv):
    print("Loading postcode coordinates...")
    postcode_coords_df = pd.read_csv(postcode_coords_csv)

    if 'postcode' not in postcode_coords_df.columns:
        raise KeyError("The 'postcode' column is missing from postcode_coords_df")

    postcode_coords_df['postcode'] = postcode_coords_df['postcode'].str.replace(' ', '', regex=False)

    print("Adding postcode coordinates to filtered dataset...")
    filtered_df = pd.merge(filtered_df, postcode_coords_df[['postcode', 'latitude', 'longitude']],
                           left_on='Postcode', right_on='postcode', how='left').drop(columns=['postcode'])
    filtered_df = filtered_df.drop_duplicates(subset=['Postcode'])

    return filtered_df, postcode_coords_df

def handle_missing_coordinates(filtered_df, postcode_coords_df):
    print("Handling missing coordinates by finding the closest postcode alphabetically...")
    sorted_postcodes = postcode_coords_df['postcode'].sort_values()

    missing_coords = filtered_df[filtered_df['latitude'].isna()]
    removed_postcodes = []
    updated_coords = []

    for idx in tqdm(missing_coords.index, desc="Processing missing coordinates"):
        missing_postcode = filtered_df.loc[idx, 'Postcode']
        pos = sorted_postcodes.searchsorted(missing_postcode)
        closest_postcode = None
        if pos < len(sorted_postcodes):
            closest_postcode = sorted_postcodes.iloc[pos]

        if closest_postcode and closest_postcode[:3] == missing_postcode[:3]:
            nearest_coords = postcode_coords_df[postcode_coords_df['postcode'] == closest_postcode]
            updated_coords.append({
                'index': idx,
                'latitude': nearest_coords['latitude'].values[0],
                'longitude': nearest_coords['longitude'].values[0]
            })
        else:
            removed_postcodes.append(missing_postcode)

    additional_postcodes_to_remove = ['GY46UU', 'JE23QP', 'IM44RJ', 'JE13UH', 'BT126BE', 'BT126BA', 'EH105HF']
    filtered_df = filtered_df[~filtered_df['Postcode'].isin(additional_postcodes_to_remove)]

    for item in updated_coords:
        filtered_df.at[item['index'], 'latitude'] = item['latitude']
        filtered_df.at[item['index'], 'longitude'] = item['longitude']

    print(f"Removed postcodes: {(', '.join(removed_postcodes + additional_postcodes_to_remove))}")
    return filtered_df

def add_msoa_information(filtered_df, geography_dir):
    print("Loading MSOA boundaries...")
    msoa_boundaries_path = os.path.join(geography_dir, 'msoa_boundaries.geojson')
    msoa_gdf = gpd.read_file(msoa_boundaries_path)

    print("Creating GeoDataFrame to find MSOA...")
    filtered_gdf = gpd.GeoDataFrame(filtered_df.dropna(subset=['latitude', 'longitude']),
                                    geometry=[Point(xy) for xy in zip(filtered_df['longitude'], filtered_df['latitude'])],
                                    crs='EPSG:4326')
    filtered_gdf = gpd.sjoin(filtered_gdf, msoa_gdf[['MSOA21CD', 'geometry']], how='left', predicate='within')

    filtered_df['msoa'] = filtered_gdf['MSOA21CD']
    return filtered_df

def drop_duplicate_entries(filtered_df, location_type):
    print(f"Dropping duplicate {location_type} entries based on name and postcode prefix...")
    filtered_df['PostcodePrefix'] = filtered_df['Postcode'].str[:2]
    filtered_df = filtered_df.sort_values(by=['Name', 'PostcodePrefix', 'Is Operated By - Code'], ascending=[True, True, False])
    filtered_df = filtered_df.drop_duplicates(subset=['Name', 'PostcodePrefix'], keep='first').drop(columns=['PostcodePrefix'])
    return filtered_df

def filter_location_name(name, location_type):
    name = name.replace("'", "")
    name = name.upper()

    match = re.search(rf'\(([^)]+{location_type.upper()})\)', name)
    if match:
        name = match.group(1)
    else:
        possible_parts = re.split(r'[-()]', name)
        possible_parts = [part.strip() for part in possible_parts if part.strip()]
        if possible_parts:
            name = process.extractOne(location_type.upper(), possible_parts, scorer=fuzz.partial_ratio)[0]

    name = re.sub(r'\bSt\b', 'St.', name.title())
    return name

def filter_and_enrich_data(trust_sites_csv, unique_trust_locations_csv, geography_dir, location_type):
    trust_sites_df, unique_trust_locations_df = load_data(trust_sites_csv, unique_trust_locations_csv)
    trust_sites_df = clean_postcodes(trust_sites_df, 'Postcode')
    unique_trust_locations_df = clean_postcodes(unique_trust_locations_df, 'postcode')

    filtered_df = filter_trust_sites(trust_sites_df, unique_trust_locations_df, location_type)
    filtered_df, postcode_coords_df = add_postcode_coordinates(filtered_df, os.path.join(geography_dir, 'postcode_coordinates.csv'))
    filtered_df = handle_missing_coordinates(filtered_df, postcode_coords_df)
    filtered_df = add_msoa_information(filtered_df, geography_dir)
    filtered_df = drop_duplicate_entries(filtered_df, location_type)

    output_file = os.path.join(paths.data_path, f'input/NHS_trusts/unique_{location_type.lower()}_locations.csv')
    print(f"Saving filtered and enriched data to {output_file}...")
    filtered_df.to_csv(output_file, index=False)

    print("Data filtering and enrichment completed.")

# File paths
trust_sites_csv = f'{paths.data_path}/raw_data/NHS_trusts/trust_sites.csv'
unique_trust_locations_csv = f'{paths.data_path}/input/NHS_trusts/unique_trust_locations.csv'
geography_dir = f'{paths.data_path}/input/geography/'

location_types = ['hospital', 'hospice']
for location in location_types:
    filter_and_enrich_data(trust_sites_csv, unique_trust_locations_csv, geography_dir, location)

print("Data processing completed and saved.")
