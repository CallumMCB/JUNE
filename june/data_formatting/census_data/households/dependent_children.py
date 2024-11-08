import pandas as pd
from june import paths

# Load the Excel file and inspect its structure
file_path = f'{paths.data_path}/raw_data/households/household_dependent_children.xlsx'
sheet_name = '1b'
output_file_path = f'{paths.data_path}/input/households/dependent_children_ratios.csv'

# Load the Excel file starting from row 7, considering 0-indexing (hence skiprows=6)
df = pd.read_excel(file_path, sheet_name=sheet_name, skiprows=6)

# Display the first few rows to understand the structure of the data
df.head()

# Remove the unnecessary "Single family household: Lone step-parent" and "Total number of households" columns
df_cleaned = df.drop(columns=["Single family household: Lone step-parent", "Other household types", "Total number of households"])

# Replace the value 'c' with NaN, then fill NaN values with 0 to handle any calculation issues
df_cleaned.replace('c', 0, inplace=True)
df_cleaned.fillna(0, inplace=True)

# Convert numerical columns to numeric types for ratio calculation
numerical_columns = df_cleaned.columns[3:]  # Columns from index 3 onward are numerical
df_cleaned[numerical_columns] = df_cleaned[numerical_columns].apply(pd.to_numeric)

# Group by 'Local authority code (2022)' to maintain MSOA specific rows
grouped = df_cleaned.groupby("Local authority code (2022)")

# Calculate ratios for each MSOA such that each 2D array sums to 1
ratio_df_list = []
for _, group in grouped:
    group_sum = group[numerical_columns].sum().sum()  # Calculate the total sum for the entire group, excluding "Total number of households"
    group_ratios = group.copy()
    group_ratios[numerical_columns] = group[numerical_columns] / group_sum  # Divide each cell by the total sum
    ratio_df_list.append(group_ratios)

# Concatenate all the ratio dataframes to maintain the original structure
ratio_df = pd.concat(ratio_df_list)

# Add a column that contains the sum of the ratios for each row
ratio_df['Sum'] = ratio_df[numerical_columns].sum(axis=1)

# Save the output to a CSV
ratio_df.to_csv(output_file_path, index=False)

print("Saved to {}".format(output_file_path))