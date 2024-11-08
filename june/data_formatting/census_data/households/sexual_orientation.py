import pandas as pd
from june import paths

# Load the CSV file
csv_file_path = f'{paths.data_path}/raw_data/households/communal_establishment_management_and_type_msoa.csv'
df = pd.read_csv(csv_file_path)

# Drop unnecessary columns
df_cleaned = df.drop(columns=['Middle layer Super Output Areas', 'Communal establishment management and type (26 categories) Code'])

output_file_path = f'{paths.data_path}/input/households/communal_establishments/type_by_msoa.csv'

# Pivot the DataFrame to make household composition types the columns, with 'Middle layer Super Output Areas Code' as the index
# The data for each cell is in the 'Observation' column
df_pivoted = df_cleaned.pivot(index='Middle layer Super Output Areas Code',
                              columns='Communal establishment management and type (26 categories)',
                              values='Observation')

# Drop the "Does not apply" column if it exists
df_pivoted.drop(columns=['Establishment not stated'], inplace=True, errors='ignore')

# Calculate the total of all categories for each MSOA
df_pivoted['total'] = df_pivoted.sum(axis=1)

# Rename columns based on generalized categories
generalized_renaming = {
    # Merging all general hospitals under 'MC: General hospital'
    'Medical and care establishment: NHS: General hospital': 'MC: General hospital',

    # Merging all mental health hospitals under 'MC: Mental health hospital or unit'
    'Medical and care establishment: NHS: Mental health hospital or unit (including secure units)': 'MC: Mental health hospital or unit',
    'Medical and care establishment: Other: Mental health hospital or unit (including secure units)': 'MC: Mental health hospital or unit',

    # Merging all other hospitals under 'MC: Other hospital'
    'Medical and care establishment: NHS: Other hospital': 'MC: Other hospital',
    'Medical and care establishment: Other: Other hospital': 'MC: Other hospital',

    # Merging all children's homes under 'MC: Children\'s home'
    "Medical and care establishment: Local Authority: Children's home (including secure units)": 'MC: Children\'s home',
    "Medical and care establishment: Other: Children's home (including secure units)": 'MC: Children\'s home',

    # Merging all care homes with nursing under 'MC: Care home with nursing'
    'Medical and care establishment: Local Authority: Care home with nursing': 'MC: Care home with nursing',
    'Medical and care establishment: Other: Care home with nursing': 'MC: Care home with nursing',

    # Merging all care homes without nursing under 'MC: Care home without nursing'
    "Medical and care establishment: Local Authority: Care home without nursing": 'MC: Care home without nursing',
    "Medical and care establishment: Other: Care home without nursing": 'MC: Care home without nursing',

    # Merging other homes under 'MC: Other home'
    "Medical and care establishment: Local Authority: Other home": 'MC: Other home',
    "Medical and care establishment: Other: Other establishment": 'MC: Other home',

    # Merging home or hostel under 'MC: Home or hostel'
    "Medical and care establishment: Registered Social Landlord or Housing Association: Home or hostel": 'MC: Home or hostel',

    # Merging other establishments (Defence, Prison service, etc.)
    "Other establishment: Defence": "Other: Defence",
    "Other establishment: Prison service": "Other: Prison service",
    "Other establishment: Approved premises (probation or bail hostel)": "Other: Approved premises",
    "Other establishment: Detention centres and other detention": "Other: Detention centres",
    "Other establishment: Education": "Other: Education",
    "Other establishment: Hotel, guest house, B&B or youth hostel": "Other: Temporary accommodation",
    "Other establishment: Hostel or temporary shelter for the homeless": "Other: Temporary accommodation",
    "Other establishment: Holiday accommodation": "Other: Temporary accommodation",
    "Other establishment: Other travel or temporary accommodation": "Other: Temporary accommodation",
    "Other establishment: Religious": "Other: Religious",
    "Other establishment: Staff or worker accommodation or Other": "Other: Staff/Worker accommodation"
}

# Rename the columns in the DataFrame
df_pivoted.rename(columns=generalized_renaming, inplace=True)

# Combine columns that now have the same names by summing them
df_pivoted = df_pivoted.groupby(level=0, axis=1).sum()

# Reorder columns based on the generalized renaming dictionary
desired_order = list(generalized_renaming.values())
desired_order = list(dict.fromkeys(desired_order))  # Remove any duplicate values
desired_order.append('total')  # Ensure 'total' is at the end

# Reorder the columns to match the desired order
df_pivoted = df_pivoted.reindex(columns=desired_order)

# Save the cleaned DataFrame to CSV with MSOA as the index
df_pivoted.to_csv(output_file_path, index=True)

print(f"Adapted CSV file saved to: {output_file_path}")
