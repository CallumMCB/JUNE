import pandas as pd
from june import paths

msoa_csv = f'{paths.data_path}/raw_data/demography/population_density_msoa.csv'
oa_csv = f'{paths.data_path}/raw_data/demography/population_density_oa.csv'

def process_csv(fp, output_fp):
    area_type = fp.rsplit('_', 1)[-1].rsplit('.', 1)[0]
    print(f"Processing {area_type}'s")
    df = pd.read_csv(fp)
    df.drop(columns=['date', 'geography'], inplace=True)
    df.rename(columns={
        'geography code': f'{area_type}',
        'Population Density: Persons per square kilometre; measures: Value': 'people per square kilometre',
    }, inplace=True)
    df.set_index([f'{area_type}'], inplace=True)
    df.to_csv(output_fp, index=True)

process_csv(msoa_csv, f'{paths.data_path}/input/demography/population_density_msoa.csv')
process_csv(oa_csv, f'{paths.data_path}/input/demography/population_density_oa.csv')