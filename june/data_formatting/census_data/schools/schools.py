import pandas as pd
from june import paths

input_file = f'{paths.data_path}/raw_data/schools/schools_30-06-2021.csv'
output_file = f'{paths.data_path}/input/schools/schools_30-06-2021.csv'

def filter_and_save_csv(input_file, output_file):
    # Load the CSV into a DataFrame
    df = pd.read_csv(input_file, encoding='ISO-8859-1', on_bad_lines='skip', low_memory=False)
    df_filtered = df[df['EstablishmentStatus (name)'] == 'Open']

    # Select the desired columns and rename them
    columns_to_keep = [
        'EstablishmentName',
        'EstablishmentTypeGroup (name)',
        'PhaseOfEducation (name)',
        'StatutoryLowAge',
        'StatutoryHighAge',
        'Boarders (name)',
        'Gender (name)',
        'SchoolCapacity',
        'NumberOfPupils',
        'NumberOfBoys',
        'NumberOfGirls',
        'MSOA (code)',
        'Postcode',
        'Easting',
        'Northing'
    ]
    df_filtered = df_filtered[columns_to_keep]

    # Rename the columns
    new_column_names = [
        'name',
        'type',
        'level',
        'min age',
        'max age',
        'boarding',
        'gender',
        'capacity',
        'pupils',
        'boys',
        'girls',
        'super_area',
        'postcode',
        'easting',
        'northing'
    ]
    df_filtered.columns = new_column_names

    # Simplify the 'type' column
    type_mapping = {
        'Local authority maintained schools': 'State',
        'Welsh schools': 'State',
        'Academies': 'Academy',
        'Free Schools': 'Academy',
        'Special schools': 'Special',
        'Independent schools': 'Independent',
        'Colleges': 'Independent',
        'Universities': 'Independent',
        'Other types': 'Independent'
    }
    df_filtered['type'] = df_filtered['type'].map(type_mapping)

    # Filter rows where super_area starts with 'E0'
    df_filtered = df_filtered[df_filtered['super_area'].str.startswith('E0')]

    print("Unique values in 'Type':", df_filtered['type'].unique())
    print("Unique values in 'Level':", df_filtered['level'].unique())
    print("Unique values in 'Bording':", df_filtered['boarding'].unique())
    print("Unique values in 'Gender':", df_filtered['gender'].unique())

    # Save the filtered DataFrame to a new CSV file
    df_filtered.to_csv(output_file, index=False)

filter_and_save_csv(input_file, output_file)
