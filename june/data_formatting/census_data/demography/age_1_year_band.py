# Load the necessary libraries
import pandas as pd
import os
from june import paths

year = '2022'

# Define the directory containing the CSV files
total_path = f'{paths.data_path}/raw_data/demography/1_year_age_total_oa_{year}/'
female_path = f'{paths.data_path}/raw_data/demography/1_year_age_female_oa_{year}/'

output_total_filepath = f'{paths.data_path}/input/demography/age_dist_{year}/1_year_ages_total_oa.csv'
output_female_filepath = f'{paths.data_path}/input/demography/age_dist_{year}/1_year_ages_female_oa.csv'


# Function to clean up the dataframe
def clean_dataframe(df):
    # Set '2021 output area' as the index
    if 'All Ages' in df.columns: has_all_ages = True
    else: has_all_ages = False

    df.rename(columns={'2021 output area': 'area'}, inplace=True)
    df.set_index('area', inplace=True)

    # Handle the 'All Ages' column if it exists
    if has_all_ages:
        # Drop the 'All Ages' column, while keeping it separately
        all_ages_col = df['All Ages']
        df.drop(columns=['All Ages'], inplace=True)
    else:
        # If 'All Ages' does not exist, initialize a placeholder for summation
        all_ages_col = None

    # Rename columns to remove the 'Age ' prefix and handle the 'Aged 90+' case
    df.columns = df.columns.str.replace('Age ', '', regex=True).str.replace('Aged ', '', regex=True)
    df.columns = df.columns.str.replace('90\+', '90', regex=True).astype(int)

    # Ensure all values are integers (not floats)
    df = df.apply(pd.to_numeric, downcast='integer')

    # Return cleaned dataframe and the 'All Ages' or placeholder column separately
    return df, all_ages_col, has_all_ages


def process_directory(directory_path, output_filepath):
    # Initialize an empty list to hold individual dataframes
    all_dataframes = []
    all_ages_column = None

    # Loop through all CSV files in the directory
    for filename in os.listdir(directory_path):
        if filename.endswith('.csv'):
            # Load each file, skipping the appropriate rows to correctly read the headers
            filepath = os.path.join(directory_path, filename)
            df = pd.read_csv(filepath, skiprows=5)

            # Clean up the dataframe
            cleaned_df, all_ages_col, has_all_ages = clean_dataframe(df)
            all_dataframes.append(cleaned_df)

            # If processing total data, store the 'All Ages' column from the first file only
            if has_all_ages and all_ages_column is None:
                all_ages_column = all_ages_col

            # If processing female data, sum the 'All Females' across all files
            if not has_all_ages:
                if all_ages_column is None:
                    all_ages_column = all_ages_col
                else:
                    all_ages_column += all_ages_col

    # Concatenate all dataframes along columns (to merge data from multiple files into a single dataframe)
    merged_df = pd.concat(all_dataframes, axis=1)

    # Add the 'All Ages' or 'All Females' column as the first column
    column_name = 'all_ages'
    merged_df.insert(0, column_name, all_ages_column)

    # If processing female data, calculate the sum for each row to create 'all_female'
    if not has_all_ages:
        merged_df[column_name] = merged_df.iloc[:, 1:].sum(axis=1)

    # Sort only the age columns by numerical order, excluding the 'all_ages' or 'all_female' column
    age_columns = [col for col in merged_df.columns if col != column_name]
    age_columns_sorted = sorted(age_columns)
    merged_df = merged_df[[column_name] + age_columns_sorted]

    # Ensure all values are integers (not floats)
    merged_df = merged_df.apply(pd.to_numeric, downcast='integer')

    # Save the cleaned and merged dataframe to an output CSV file
    merged_df.to_csv(output_filepath, index=True)

    # Indicate that the process has completed successfully
    print(f"Merged dataframe saved to {output_filepath}")


# Process the total and female directories
process_directory(total_path, output_total_filepath)
process_directory(female_path, output_female_filepath)
