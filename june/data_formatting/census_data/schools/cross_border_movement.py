import pandas as pd
from june import paths

# Load the CSV file
file_path = f'{paths.data_path}/raw_data/schools/spc_cbm_220815.csv'
data = pd.read_csv(file_path, low_memory=False)

# Step 2: Drop specified columns
columns_to_drop = [
    'time_period', 'time_identifier', 'geographic_level',
    'country_code', 'country_name', 'region_code', 'region_name', 'old_la_code'
]
data.drop(columns=columns_to_drop, inplace=True)

# Step 3: Rename 'new_la_code' to 'la_code'
data.rename(columns={'new_la_code': 'la_code'}, inplace=True)

# Step 4: Get unique values for 'la_name' and 'la_code' to match with column headers
la_name_code_mapping = data[['la_name', 'la_code']].drop_duplicates()

# Replace spaces and dashes in `la_name` with underscores to match column names
la_name_code_mapping['la_name'] = (
    la_name_code_mapping['la_name']
    .str.replace(r'[\s\-\.,]', '_', regex=True)  # Replace spaces, dashes, periods, commas with underscores
    .str.replace(r'_+', '_', regex=True)  # Replace multiple underscores with a single underscore
    .str.strip('_')  # Remove leading or trailing underscores
)

# Step 5: Replace county names in column names with county codes
data.rename(columns=lambda col: la_name_code_mapping.set_index('la_name')['la_code'].get(col, col), inplace=True)

# Step 6: Separate data with 'Special School' in 'phase_type_grouping'
special_school_data = data[data['phase-type_grouping'] == 'Special School'].drop(columns=['phase-type_grouping']).reset_index(drop=True)
remaining_data = data[data['phase-type_grouping'] != 'Special School'].drop(columns=['phase-type_grouping']).reset_index(drop=True)

# Step 7: Split the data based on the 'boarder' column and merge rows with the same 'ncyear'
# For Special Schools
special_day_data = special_school_data[special_school_data['boarder'] == 'Not a boarder'].drop(columns=['boarder']).reset_index(drop=True)
special_boarder_data = special_school_data[special_school_data['boarder'] == 'Boarder'].drop(columns=['boarder']).reset_index(drop=True)
special_total_data = special_school_data[special_school_data['boarder'] == 'Total'].drop(columns=['boarder']).reset_index(drop=True)

# For Remaining Schools
day_data = remaining_data[remaining_data['boarder'] == 'Not a boarder'].drop(columns=['boarder']).reset_index(drop=True)
boarder_data = remaining_data[remaining_data['boarder'] == 'Boarder'].drop(columns=['boarder']).reset_index(drop=True)
total_data = remaining_data[remaining_data['boarder'] == 'Total'].drop(columns=['boarder']).reset_index(drop=True)

# Merge rows with the same 'ncyear' within each Local Authority
special_day_data = special_day_data.groupby(['la_code', 'ncyear'], as_index=False).sum()
special_boarder_data = special_boarder_data.groupby(['la_code', 'ncyear'], as_index=False).sum()
special_total_data = special_total_data.groupby(['la_code', 'ncyear'], as_index=False).sum()

day_data = day_data.groupby(['la_code', 'ncyear'], as_index=False).sum()
boarder_data = boarder_data.groupby(['la_code', 'ncyear'], as_index=False).sum()
total_data = total_data.groupby(['la_code', 'ncyear'], as_index=False).sum()

# Step 8: Sort data within each la_code by 'ncyear'
ncyear_order = ['Reception'] + [str(i) for i in range(1, 13)] + ['X', 'Total']

for df in [special_day_data, special_boarder_data, special_total_data, day_data, boarder_data, total_data]:
    df['ncyear'] = pd.Categorical(df['ncyear'], categories=ncyear_order, ordered=True)
    df.sort_values(by=['la_code', 'ncyear'], inplace=True)
    df.set_index(['la_code', 'ncyear'], inplace=True)

# Step 9: Prepare the county columns (excluding the indices)
county_columns = sorted([code for code in la_name_code_mapping['la_code'].unique() if pd.notna(code) and code != 'z'])
non_county_columns = [col for col in data.columns if col not in county_columns]

# Step 10: Reorder columns so specific non-county columns come first
priority_columns = ['la_name', 'phase_type', 'resident_headcount', 'school_in_la', 'school_outside_la']
remaining_non_county_columns = [col for col in non_county_columns if col not in priority_columns]

# Reorder columns for each DataFrame
for df in [special_day_data, special_boarder_data, special_total_data, day_data, boarder_data, total_data]:
    df = df[[col for col in priority_columns if col in df.columns] + [col for col in remaining_non_county_columns if col in df.columns] + [col for col in county_columns if col in df.columns]]

# Step 11: Save each modified DataFrame as a new CSV file without adding any extra rows
output_file_path_special_day = f'{paths.data_path}/input/schools/cross_border_movement/special_day.csv'
output_file_path_special_boarder = f'{paths.data_path}/input/schools/cross_border_movement/special_boarder.csv'
output_file_path_special_total = f'{paths.data_path}/input/schools/cross_border_movement/special_total.csv'

output_file_path_day = f'{paths.data_path}/input/schools/cross_border_movement/day.csv'
output_file_path_boarder = f'{paths.data_path}/input/schools/cross_border_movement/boarder.csv'
output_file_path_total = f'{paths.data_path}/input/schools/cross_border_movement/total.csv'

special_day_data.to_csv(output_file_path_special_day)
special_boarder_data.to_csv(output_file_path_special_boarder)
special_total_data.to_csv(output_file_path_special_total)

day_data.to_csv(output_file_path_day)
boarder_data.to_csv(output_file_path_boarder)
total_data.to_csv(output_file_path_total)

print("Processed CSVs saved at:")
print("Special Day data:", output_file_path_special_day)
print("Special Boarder data:", output_file_path_special_boarder)
print("Special Total data:", output_file_path_special_total)
print("Day data:", output_file_path_day)
print("Boarder data:", output_file_path_boarder)
print("Total data:", output_file_path_total)