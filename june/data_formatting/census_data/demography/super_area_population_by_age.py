import pandas as pd
from june import paths

# Load the necessary libraries and the area-super area mapping file
area_super_area_path = f'{paths.data_path}/input/geography/area_super_area_regions.csv'
area_super_area_df = pd.read_csv(area_super_area_path)

# Load the merged dataframes for total and female populations
output_total_filepath = f'{paths.data_path}/input/demography/1_year_ages_total_oa.csv'
output_female_filepath = f'{paths.data_path}/input/demography/1_year_ages_female_oa.csv'

total_population_df = pd.read_csv(output_total_filepath)
female_population_df = pd.read_csv(output_female_filepath)

# Merge the total population dataframe with the area-super area mapping
merged_total_df = total_population_df.merge(area_super_area_df, left_on='area', right_on='area', how='left')

# Calculate the total population for each super area
super_area_total_population = merged_total_df.groupby('super_area').sum()

# Similarly, merge the female population dataframe with the area-super area mapping
merged_female_df = female_population_df.merge(area_super_area_df, left_on='area', right_on='area', how='left')

# Calculate the female population for each super area
super_area_female_population = merged_female_df.groupby('super_area').sum()

# Save the output to CSV files
super_area_total_population_filepath = f'{paths.data_path}/input/demography/super_area_total_population.csv'
super_area_female_population_filepath = f'{paths.data_path}/input/demography/super_area_female_population.csv'

super_area_total_population.to_csv(super_area_total_population_filepath)
super_area_female_population.to_csv(super_area_female_population_filepath)

print(f"Super area total population saved to {super_area_total_population_filepath}")
print(f"Super area female population saved to {super_area_female_population_filepath}")
