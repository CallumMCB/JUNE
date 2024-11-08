import pandas as pd
import yaml
from june import paths

# Load the CSV file
areas_csv_file_path = f'{paths.data_path}/raw_data/geography/output_areas_2021.csv'
areas_df = pd.read_csv(areas_csv_file_path)
areas_coordinates_output_file_path = f'{paths.data_path}/input/geography/oa_coordinates.csv'

super_areas_csv_file_path = f'{paths.data_path}/raw_data/geography/MSOAs_2021.csv'
super_areas_df = pd.read_csv(super_areas_csv_file_path)
super_areas_coordinates_output_file_path = f'{paths.data_path}/input/geography/msoa_coordinates.csv'


# Keep only the columns 'OA21CD', 'LAT', 'LONG'
areas_coordinates_df_filtered = areas_df[['OA21CD', 'LAT', 'LONG']]
super_areas_coordinates_df_filtered = super_areas_df[['MSOA21CD', 'LAT', 'LONG']]

# Rename the columns to 'area', 'latitude', 'longitude'
areas_coordinates_df_filtered.rename(columns={'OA21CD': 'area', 'LAT': 'latitude', 'LONG': 'longitude'}, inplace=True)
super_areas_coordinates_df_filtered.rename(columns={'MSOA21CD': 'super_area', 'LAT': 'latitude', 'LONG': 'longitude'}, inplace=True)


# Set the index to 'area'
areas_coordinates_df_filtered.set_index('area', inplace=True)
super_areas_coordinates_df_filtered.set_index('super_area', inplace=True)


# Save the modified DataFrame to a new CSV file
areas_coordinates_df_filtered.to_csv(areas_coordinates_output_file_path)
super_areas_coordinates_df_filtered.to_csv(super_areas_coordinates_output_file_path)

print(f"Adapted CSV file saved to: {areas_coordinates_output_file_path}")
print(f"Adapted CSV file saved to: {super_areas_coordinates_output_file_path}")

