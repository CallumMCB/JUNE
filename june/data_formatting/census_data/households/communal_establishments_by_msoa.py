import pandas as pd
from june import paths

# Load the CSV file
resident_fp = f'{paths.data_path}/raw_data/households/communal_resident_type_msoa.csv'
establishment_fp = f'{paths.data_path}/raw_data/households/communal_establishment_type_msoa.xlsx'

output_resident_fp = f'{paths.data_path}/input/households/communal_establishments/resident_type_msoa.csv'
output_establishment_fp = f'{paths.data_path}/input/households/communal_establishments/establishment_type_msoa.csv'

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

import pandas as pd
from june import paths

# Load the CSV file
resident_fp = f'{paths.data_path}/raw_data/households/communal_resident_type_msoa.csv'
establishment_fp = f'{paths.data_path}/raw_data/households/communal_establishment_type_msoa.xlsx'

output_resident_fp = f'{paths.data_path}/input/households/communal_establishments/resident_type_msoa.csv'
output_establishment_fp = f'{paths.data_path}/input/households/communal_establishments/establishment_type_msoa.csv'

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

def processing_file(fp, output_fp):
    # Determine the file type and read accordingly
    if fp.endswith('.csv'):
        df = pd.read_csv(fp)
    elif fp.endswith('.xlsx'):
        df = pd.read_excel(fp)
    else:
        raise ValueError(f"Unsupported file type for {fp}. Must be .csv or .xlsx")

    # Drop unnecessary columns
    df_cleaned = df.drop(
        columns=['Middle layer Super Output Areas', 'Communal establishment management and type (26 categories) Code'])

    # Pivot the DataFrame
    df_pivoted = df_cleaned.pivot(index='Middle layer Super Output Areas Code',
                                  columns='Communal establishment management and type (26 categories)',
                                  values='Observation')

    # Drop the "Does not apply" column if it exists
    df_pivoted.drop(columns=['Establishment not stated'], inplace=True, errors='ignore')

    # Calculate the total of all categories for each MSOA
    df_pivoted['total'] = df_pivoted.sum(axis=1)

    # Rename the columns in the DataFrame
    df_pivoted.rename(columns=generalized_renaming, inplace=True)

    # Combine columns that now have the same names by summing them
    df_pivoted = df_pivoted.groupby(level=0, axis=1).sum()

    # Save the cleaned DataFrame to CSV with MSOA as the index
    df_pivoted.to_csv(output_fp, index=True)

    print(f"Adapted CSV file saved to: {output_fp}")

# Process both files
processing_file(resident_fp, output_resident_fp)
processing_file(establishment_fp, output_establishment_fp)