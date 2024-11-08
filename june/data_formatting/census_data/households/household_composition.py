import pandas as pd
import yaml
from june import paths

# Load the CSV file
csv_file_path = f'{paths.data_path}/raw_data/households/household_composition_2021.csv'
df = pd.read_csv(csv_file_path)
df_cleaned = df.drop(columns = ['Output Areas Code', 'Household composition (15 categories) Code'])

# Load the YAML file
yaml_file_path = f'{paths.configs_path}/defaults/distributors/household_distributor_2021.yaml'
with open(yaml_file_path, 'r') as yaml_file:
    yaml_data = yaml.safe_load(yaml_file)

output_file_path = f'{paths.data_path}/input/households/household_composition_2021.csv'

# Extract the default household compositions dictionary from YAML
household_mapping = yaml_data.get('default_household_compositions', {})

# Create a mapping from original row names to new labels based on the YAML file
name_mapping = {}
for key, value in household_mapping.items():
    labels = value.get('labels', [])
    if isinstance(labels, list):
        for label in labels:
            name_mapping[label] = key
    elif isinstance(labels, str):
        name_mapping[labels] = key

# Rename the columns based on YAML mapping
df_cleaned.rename(columns=name_mapping, inplace=True)

# Pivot the DataFrame to make household composition types the columns, with 'Output Areas Code' as the index
# The data for each cell is in the 'Observation' column
df_pivoted = df_cleaned.pivot(index='Output Areas', columns='Household composition (15 categories)', values='Observation').reset_index()

# Drop the "Does not apply" column if it exists
df_pivoted.drop(columns=['Does not apply'], inplace=True, errors='ignore')

# Replace the final column names with the column labels from the YAML file
column_mapping = {col: name_mapping.get(col, col) for col in df_pivoted.columns}
df_pivoted.rename(columns=column_mapping, inplace=True)

# Merge columns with the same name by summing their values
df_pivoted = df_pivoted.groupby(df_pivoted.columns, axis=1).sum()
df_pivoted.set_index('Output Areas', inplace=True)
df_pivoted.reset_index(inplace=True)
df_pivoted['Total'] = df_pivoted.iloc[:, 1:].sum(axis=1)

df_pivoted.to_csv(output_file_path, index=False)

print(f"Adapted CSV file saved to: {output_file_path}")
