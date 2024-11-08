from june import paths
import pandas as pd
from tqdm import tqdm

# Load the CSV file to process the data
file_path = f'{paths.data_path}/raw_data/demography/ethnicity_sex_age_msoa.csv'
data = pd.read_csv(file_path)

# Filtering out rows where the Ethnic group is "Does not apply"
filtered_data = data[data["Ethnic group (6 categories)"] != "Does not apply"]

# Splitting the data by Sex (before removing the "Sex (2 categories)" column)
male_data = filtered_data[filtered_data["Sex (2 categories)"] == "Male"]
female_data = filtered_data[filtered_data["Sex (2 categories)"] == "Female"]

# Dropping unnecessary columns from both male and female datasets
columns_to_drop = [
    "Ethnic group (6 categories) Code",
    "Sex (2 categories) Code",
    "Age (13 categories) Code",
    "Middle layer Super Output Areas",
    "Sex (2 categories)"
]

male_data = male_data.drop(columns=columns_to_drop)
female_data = female_data.drop(columns=columns_to_drop)

# Renaming columns to make them more readable
def renaming(df):
    columns_renaming = {
        "Middle layer Super Output Areas Code": "super_area",
        "Ethnic group (6 categories)": "Ethnicity",
    }
    age_columns = [column for column in df.columns if "Aged" in column]

    for i, column in enumerate(age_columns):
        new_name = column.replace("Aged ", "").replace(' to ', '-').replace(" years", "")
        if "and under" in column:
            new_name = "0-" + new_name.split(' ')[0]
        elif "and over" in column:
            new_name = new_name.split(' ')[0] + "-99"
        columns_renaming[column] = new_name
    return df.rename(columns=columns_renaming)

# Renaming values in the Ethnic group column to make them more readable
def rename_ethnic_groups(df):
    ethnic_group_renaming = {
        "Asian, Asian British or Asian Welsh": "Asian",
        "Black, Black British, Black Welsh, Caribbean or African": "Black",
        "Mixed or Multiple ethnic groups": "Mixed",
        "Other ethnic group": "Other",
    }
    df = df.rename(columns={"Middle layer Super Output Areas Code": "super_area", "Ethnic group (6 categories)": "Ethnicity"})
    df["Ethnicity"] = df["Ethnicity"].replace(ethnic_group_renaming)
    return df

# Adding tqdm progress bar
tqdm.pandas()

# Pivoting the datasets so that Age Categories become columns
male_pivoted = male_data.pivot_table(
    index=["Middle layer Super Output Areas Code", "Ethnic group (6 categories)"],
    columns="Age (13 categories)",
    values="Observation",
    fill_value=0
)

female_pivoted = female_data.pivot_table(
    index=["Middle layer Super Output Areas Code", "Ethnic group (6 categories)"],
    columns="Age (13 categories)",
    values="Observation",
    fill_value=0
)

# Flattening the column index after pivot (if it exists)
male_pivoted.columns = [str(col) for col in male_pivoted.columns]
female_pivoted.columns = [str(col) for col in female_pivoted.columns]

male_pivoted.reset_index(inplace=True)
female_pivoted.reset_index(inplace=True)

male_data = renaming(male_pivoted)
male_data = rename_ethnic_groups(male_data)
female_data = renaming(female_pivoted)
female_data = rename_ethnic_groups(female_data)

# Adding a column for the total of each row after Ethnicity and before age categories
male_data.insert(2, 'Total', male_data.iloc[:, 2:].sum(axis=1))
female_data.insert(2, 'Total', female_data.iloc[:, 2:].sum(axis=1))

# Normalizing each row so that the values in each super area sum to 1
male_ratios = male_data.copy()
female_ratios = female_data.copy()

# Groupby normalization for each super_area excluding the 'Total' column
numeric_columns = male_ratios.columns[3:]

def normalize_group(df):
    df_sum = df[numeric_columns].sum().sum()
    return df[numeric_columns] / df_sum if df_sum != 0 else df[numeric_columns]

# Adding tracker for normalization progress
male_ratios[numeric_columns] = male_ratios.groupby('super_area')[numeric_columns].progress_apply(normalize_group).reset_index(drop=True)
female_ratios[numeric_columns] = female_ratios.groupby('super_area')[numeric_columns].progress_apply(normalize_group).reset_index(drop=True)

# Recalculating the total column after normalization
male_ratios['Total'] = male_ratios[numeric_columns].sum(axis=1)
female_ratios['Total'] = female_ratios[numeric_columns].sum(axis=1)

# Adding a row to each super_area group to sum the columns within each group
def add_super_area_total(df):
    grouped = df.groupby('super_area')
    total_rows = []
    for super_area, group in tqdm(grouped, desc="Adding super area totals"):
        total_row = group.sum(numeric_only=True)
        total_row['super_area'] = super_area
        total_row['Ethnicity'] = 'TOTAL:'
        total_rows.append(total_row)
    total_df = pd.DataFrame(total_rows)
    return pd.concat([df, total_df], ignore_index=True)

# Removing duplicate total rows
male_ratios = add_super_area_total(male_ratios)
male_ratios = male_ratios[~((male_ratios['Ethnicity'] == 'TOTAL:') & male_ratios.duplicated(subset=['super_area', 'Ethnicity'], keep='last'))]

female_ratios = add_super_area_total(female_ratios)
female_ratios = female_ratios[~((female_ratios['Ethnicity'] == 'TOTAL:') & female_ratios.duplicated(subset=['super_area', 'Ethnicity'], keep='last'))]

# Rounding values to 6 significant figures
male_ratios = male_ratios.round({col: 6 for col in numeric_columns})
male_ratios['Total'] = male_ratios['Total'].round(6)
female_ratios = female_ratios.round({col: 6 for col in numeric_columns})
female_ratios['Total'] = female_ratios['Total'].round(6)

# Setting the index to 'super_area' and sorting
male_ratios.set_index(['super_area', 'Ethnicity'], inplace=True)
male_ratios.sort_index(inplace=True)
female_ratios.set_index(['super_area', 'Ethnicity'], inplace=True)
female_ratios.sort_index(inplace=True)

# Setting columns for ages as a sub-index
male_ratios.columns = pd.MultiIndex.from_product([['Age Group'], male_ratios.columns])
female_ratios.columns = pd.MultiIndex.from_product([['Age Group'], female_ratios.columns])

# Saving the processed datasets as new CSV files
output_base_path = f'{paths.data_path}/input/demography/'
male_output_path = f'{output_base_path}ethnicity_male_age.csv'
female_output_path = f'{output_base_path}ethnicity_female_age.csv'
male_ratios_output_path = f'{output_base_path}ethnicity_male_age_ratios.csv'
female_ratios_output_path = f'{output_base_path}ethnicity_female_age_ratios.csv'

male_data.to_csv(male_output_path, index=False)
female_data.to_csv(female_output_path, index=False)
male_ratios.to_csv(male_ratios_output_path)
female_ratios.to_csv(female_ratios_output_path)