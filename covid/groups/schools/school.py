from sklearn.neighbors import BallTree
from scipy import stats
from covid.groups import Group
import numpy as np
import pandas as pd


class SchoolError(BaseException):
    """Class for throwing school related errors."""

    pass


class School(Group):
    """
    The School class represents a household and contains information about 
    its pupils (6 - 14 years old).
    """

    def __init__(self, school_id, coordinates, n_pupils, age_min, age_max):
        super().__init__("School_%05d" % school_id, "school")
        self.id = school_id
        self.coordinates = coordinates
        self.n_pupils_max = n_pupils
        self.n_pupils = 0
        self.age_min = age_min
        self.age_max = age_max


class Schools:
    def __init__(self, school_df, config):
        self.members = []
        self.init_schools(school_df)
        self.init_trees(school_df)
        self.config = config

    @classmethod
    def from_file(cls, filename: str, config_filename: str):
        school_df = pd.read_csv(filename, index_col=0)
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return Schools(school_df, config)

    def init_schools(self, school_df):
        """
        Initializes schools.
        """
        schools = []
        for i, (index, row) in enumerate(school_df.iterrows()):
            school = School(
                i,
                np.array(row[["latitude", "longitude"]].values, dtype=np.float64),
                row["NOR"],
                row["age_min"],
                row["age_max"],
            )
            schools.append(school)
        self.members = schools

    def init_trees(self, school_df):
        school_trees = {}
        school_agegroup_to_global_indices = {
            k: [] for k in range(self.SCHOOL_AGE_RANGE[0], self.SCHOOL_AGE_RANGE[1] + 1)
        }
        # have a tree per age
        school_df.reset_index(drop=True)
        for age in range(self.SCHOOL_AGE_RANGE[0], self.SCHOOL_AGE_RANGE[1] + 1):
            _school_df_agegroup = school_df[
                (school_df["age_min"] <= age) & (school_df["age_max"] >= age)
            ]
            school_trees[age] = self._create_school_tree(_school_df_agegroup)
            school_agegroup_to_global_indices[age] = _school_df_agegroup.index.values

        self.school_trees = school_trees
        self.school_agegroup_to_global_indices = school_agegroup_to_global_indices

    def get_closest_schools(self, age, coordinates, k):
        """
        Returns the k schools closest to the output area centroid.
        """
        school_tree = self.school_trees[age]
        coordinates_rad = np.deg2rad(coordinates).reshape(1, -1)
        distances, neighbours = school_tree.query(
            coordinates_rad, k=k, sort_results=True,
        )
        return neighbours[0]

    def _create_school_tree(self, school_df):
        """
        Reads school location and sizes, it initializes a KD tree on a sphere,
        to query the closest schools to a given location.
        """
        school_tree = BallTree(
            np.deg2rad(school_df[["latitude", "longitude"]].values), metric="haversine"
        )
        return school_tree
