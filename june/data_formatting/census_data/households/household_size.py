import pandas as pd
from june import paths

csv_file_path = f'{paths.data_path}/raw_data/households/household_size_per_area.csv'
df = pd.read_csv(csv_file_path)
df_cleaned = df.drop(columns=['Output Areas Code', 'Household size (9 categories)'])

output_file_path = f'{paths.data_path}/input/households/household_size_2021.csv'

df_pivoted = df_cleaned.pivot(index='area', columns='Household size (9 categories) Code', values='Observation').reset_index()
df_pivoted.drop(columns=[0], inplace=True, errors='ignore')
df_pivoted['Total'] = df_pivoted.iloc[:, 1:].sum(axis=1)

df.set_index('Output Areas Code', inplace=True)

df_pivoted.to_csv(output_file_path, index=False)

print(f'Adapted CSV file saved to: {output_file_path}')