import pandas as pd
from june import paths

# Load the Excel file, skipping the first 10 rows
excel_file_path = f'{paths.data_path}/raw_data/households/age_disparity_by_relationship_type.xlsx'
df = pd.read_excel(excel_file_path, skiprows=10)

# Keep only the desired columns
columns_to_keep = [
    'Age disparity',
    'Same-sex married couples: female',
    'Same-sex married couples: male',
    'Same-sex civil partnership couples: female',
    'Same-sex civil partnership couples: male'
]
df_filtered = df[columns_to_keep]

# Calculate the average for married and civil partnership couples by gender
df_filtered['female'] = df_filtered[['Same-sex married couples: female', 'Same-sex civil partnership couples: female']].mean(axis=1)
df_filtered['male'] = df_filtered[['Same-sex married couples: male', 'Same-sex civil partnership couples: male']].mean(axis=1)

# Check that the total sum of 'female' and 'male' columns is 100
total_female_sum = df_filtered['female'].sum()
total_male_sum = df_filtered['male'].sum()

if not (abs(total_female_sum - 100) < 1e-6 and abs(total_male_sum - 100) < 1e-6):
    print("Warning: The sum of 'female' or 'male' column does not add up to 100.")

# Keep only the 'Age disparity', 'female', and 'male' columns
df_final = df_filtered[['Age disparity', 'female', 'male']]

# Save the final DataFrame as a CSV file
output_csv_path = f'{paths.data_path}/input/households/same_sex_age_disparity.csv'
df_final.to_csv(output_csv_path, index=False)

print(f"Filtered CSV file saved to: {output_csv_path}")
