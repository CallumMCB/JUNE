import pandas as pd
import numpy as np
from june import paths
import re

# Load the Excel file, skipping the first 10 rows
excel_file_path = f'{paths.data_path}/raw_data/households/age_difference_by_female_age.xlsx'
df = pd.read_excel(excel_file_path, skiprows=11)

# Keep only the desired columns
columns_rename = {
    'Age Disparity': 'male relative age',
    'Female aged 16 to 24 (percent of couples)': '16-24',
    'Female aged 25 to 34 (percent of couples)': '25-34',
    'Female aged 35 to 54 (percent of couples)': '35-54',
    'Female aged 55 to 64 (percent of couples)': '54-65',
    'Female aged 65 to 74 (percent of couples)': '65-74',
    'Female aged 75+ (percent of couples)': '75-99'
}

df.rename(columns=columns_rename, inplace=True)
df.replace(to_replace=[None, np.nan, 'c'], value=0, inplace=True)

# Set 'male relative age' as the index
df.set_index('male relative age', inplace=True)

# Create a dictionary for renaming index values
index_rename = {
    r'Female older: ': '-',
    r'Male older: ': '+',
    r' years': '',
    r' year': '',
    r' or more': '<',
    r'Same age': '0'
}

# Efficiently rename index values using the dictionary
df.index = df.index.map(lambda x: re.sub('|'.join(index_rename.keys()), lambda m: index_rename[m.group(0)], str(x)))

# Save the final DataFrame as a CSV file, including the index
output_csv_path = f'{paths.data_path}/input/households/age_difference_by_female_age.csv'
df.to_csv(output_csv_path, index=True)

print(f"Filtered CSV file saved to: {output_csv_path}")