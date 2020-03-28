import pandas as pd


def read_population_df(DATA_DIR: str) -> pd.DataFrame:
    """
        

    """
    population = "usual_resident_population.csv"
    population_column_names = [
        "postcode_sector",
        "n_residents",
        "males",
        "females",
    ]
    population_usecols = [2, 4, 5, 6]
    population_df = pd.read_csv(
        DATA_DIR + population,
        names=population_column_names,
        usecols=population_usecols,
        header=0,
    )

    pd.testing.assert_series_equal(
        population_df["n_residents"],
        population_df["males"] + population_df["females"],
        check_names=False,
    )
    # Convert to ratios
    population_df["males"] /= population_df["n_residents"]
    population_df["females"] /= population_df["n_residents"]
    population_df.set_index("postcode_sector", inplace=True)
    return population_df


def df2dict(population_df: pd.DataFrame) -> dict:
    total_residents = population_df["n_residents"].sum()
    population_dict = {"n_residents": total_residents, "postcode_sector": {}}
    population_dict["postcode_sector"] = population_df[["n_residents"]].to_dict("index")
    for postcode in population_dict["postcode_sector"].keys():
        population_dict["postcode_sector"][postcode]["census_freq"] = {
            0: population_df.loc[postcode]["males"],
            1: population_df.loc[postcode]["females"],
        }
    return population_dict


def create_input_dictionary(
    DATA_DIR: str = "../data/census_data/postcode_sector/",
) -> dict:

    population_df = read_population_df(DATA_DIR)
    population_dict = df2dict(population_df)

    return population_dict


if __name__ == "__main__":

    print(create_input_dictionary())