import pandas as pd
from june import paths

# Load the CSV file
csv_file_path = f'{paths.data_path}/raw_data/households/communal_residents_by_age_sex_msoa.csv'
df = pd.read_csv(csv_file_path)

# Drop unnecessary columns
df.rename(columns={
    "Middle layer Super Output Areas Code": "super_area"
}, inplace=True)
df_cleaned = df.drop(columns=['Middle layer Super Output Areas', 'Position in communal establishment and sex and age (19 categories) Code'])

# Separate data based on type
df_male = df_cleaned[df_cleaned['Position in communal establishment and sex and age (19 categories)'].str.contains('Male')]
df_female = df_cleaned[df_cleaned['Position in communal establishment and sex and age (19 categories)'].str.contains('Female')]
df_staff_owner_temporary = df_cleaned[df_cleaned['Position in communal establishment and sex and age (19 categories)'].str.contains('staff|owner|temporarily')]

# Function to pivot and rename columns for male and female dataframes
def process_gender_dataframe(df, gender):
    # Pivot the DataFrame to make resident age groups the columns, with 'MSOA' as the index
    df_pivoted = df.pivot(index='super_area',
                          columns='Position in communal establishment and sex and age (19 categories)',
                          values='Observation')

    # Rename the columns to simplify age groups
    age_renaming = {
        col: col.split(":")[-1].strip()  # Extract the age range part only
        for col in df_pivoted.columns if gender in col
    }
    df_pivoted.rename(columns=age_renaming, inplace=True)

    # Remove the gender prefix from column names to only keep the age range
    df_pivoted.columns = df_pivoted.columns.str.replace(f'{gender}: ', '', regex=False)
    df_pivoted.columns = df_pivoted.columns.str.replace(' years', '', regex=False)

    # Sort columns for easier readability
    df_pivoted = df_pivoted.reindex(sorted(df_pivoted.columns), axis=1)

    return df_pivoted

# Process male and female dataframes
df_male_pivoted = process_gender_dataframe(df_male, 'Male')
df_female_pivoted = process_gender_dataframe(df_female, 'Female')

# Pivot and process staff/owner or temporary dataframe
df_staff_owner_pivoted = df_staff_owner_temporary.pivot(index='super_area',
                                                        columns='Position in communal establishment and sex and age (19 categories)',
                                                        values='Observation')

# Rename columns for staff/owner or temporary to be more readable
staff_owner_renaming = {
    "Staff or owner": "staff/owner",
    "Family member or partner of staff or owner": "staff/owner's relative",
    "Staying temporarily (no usual UK address)": "temporary/visiting"
}
df_staff_owner_pivoted.rename(columns=staff_owner_renaming, inplace=True)

# Reorder the columns alphabetically for consistency
df_staff_owner_pivoted = df_staff_owner_pivoted.reindex(sorted(df_staff_owner_pivoted.columns), axis=1)

# Save the cleaned DataFrames to CSV files
output_path = f'{paths.data_path}/input/households/communal_establishments/'
df_male_pivoted.to_csv(f'{output_path}male_residents.csv', index=True)
df_female_pivoted.to_csv(f'{output_path}female_residents.csv', index=True)
df_staff_owner_pivoted.to_csv(f'{output_path}staff_or_temporary.csv', index=True)

print("CSV files saved successfully:")
print("1. Male residents: male_residents.csv")
print("2. Female residents: female_residents.csv")
print("3. Staff/owner or temporary residents: staff_or_temporary.csv")