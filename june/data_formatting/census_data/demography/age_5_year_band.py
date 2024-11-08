import pandas as pd
import os
from june import paths

# Define the directory containing the files
data_dir = f'{paths.data_path}/raw_data/demography/5_year_ages_oa/'
output_file_path = f'{paths.data_path}/input/demography/5_year_ages_oa.csv'

# Define chunk size to handle large data
chunk_size = 10000

# Create an empty list to store DataFrames
dataframes = []

# Iterate over all CSV files in the directory
for file_name in os.listdir(data_dir):
    if file_name.endswith('.csv'):
        file_path = os.path.join(data_dir, file_name)
        # Read the file in chunks to handle large files
        for chunk in pd.read_csv(file_path, chunksize=chunk_size):
            # Keep only relevant columns and rename them
            chunk = chunk[['Output Areas Label', 'Age (B) (18 categories) Label', 'Count']]
            chunk.rename(columns={'Output Areas Label': 'areas',
                                 'Age (B) (18 categories) Label': 'age_bands',
                                 'Count': 'data'}, inplace=True)
            # Append the chunk to the list of DataFrames
            dataframes.append(chunk)

# Concatenate all DataFrames into one
combined_df = pd.concat(dataframes, ignore_index=True)

# Pivot the DataFrame to make age bands the columns, with 'areas' as the index
combined_pivoted = combined_df.pivot(index='areas', columns='age_bands', values='data')

# Rename the age bands to simplify them using a more efficient approach
def rename_age_band(age_label):
    if 'and under' in age_label:
        return '<4'
    elif 'and over' in age_label:
        return '85>'
    else:
        return age_label.replace('Aged ', '').replace(' years', '').replace(' to ', '-')

combined_pivoted.rename(columns=rename_age_band, inplace=True)

# Sort columns by extracting the first number in each age range and sorting numerically
combined_pivoted = combined_pivoted.reindex(columns=sorted(combined_pivoted.columns, key=lambda x: int(x.split('-')[0].replace('<', '').replace('>', ''))))

# Sort rows by 'areas' index for consistency
combined_pivoted.sort_index(inplace=True)

# Save the combined and pivoted DataFrame to CSV
combined_pivoted.to_csv(output_file_path, index=True)

print(f"Combined CSV file saved successfully to: {output_file_path}")
