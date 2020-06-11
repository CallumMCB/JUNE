import numpy as np
import pandas as pd
from typing import List
from enum import IntEnum

from june.groups import Group, Subgroup, Supergroup
from june.demography.geography import SuperAreas, Areas
from june.paths import data_path

age_to_years = {19: 1, 20: 2, 21: 3, 22: 4}

default_universities_filename = data_path / "input/universities/uk_universities.csv"


class University(Group):
    def __init__(
        self,
        coordinates=None,
        n_students_max=None,
        super_area: str = None,
        number_of_years=4,
    ):
        self.coordinates = coordinates
        self.n_students_max = n_students_max
        self.super_area = super_area
        super().__init__()
        self.subgroups = [Subgroup(self, i) for i in range(number_of_years + 1)]

    @property
    def students(self):
        return [person for subgroup in self.subgroups for person in subgroup]

    @property
    def n_students(self):
        return sum([subgroup.size for subgroup in self.subgroups])

    @property
    def professors(self):
        return self.subgroups[0].people

    def add(self, person, subgroup="student"):
        if subgroup == "student":
            if person.age not in age_to_years:
                year = np.random.randint(0, len(self.subgroups))
            else:
                year = age_to_years[person.age]
            self.subgroups[year].append(person)
        elif subgroup == "professors":
            self.subgroups[0].append(person)

    @property
    def is_full(self):
        return self.n_students >= self.n_students_max


class Universities(Supergroup):
    def __init__(self, universities: List[University]):
        super().__init__()
        self.members = universities

    @classmethod
    def for_super_areas(
        cls,
        super_areas: SuperAreas,
        universities_filename: str = default_universities_filename,
        max_distance_to_super_area=20,
    ):
        """
        Initializes universities from super areas. By looking at the coordinates
        of each university in the filename, we initialize those universities who
        are close to any of the super areas.

        Parameters
        ----------
        super_areas:
            an instance of SuperAreas
        universities_filename:
            path to the university data
        """
        universities_df = pd.read_csv(universities_filename)
        longitudes = universities_df["longitude"].values
        latitudes = universities_df["latitude"].values
        coordinates = np.array(list(zip(latitudes, longitudes)))
        n_students = universities_df["n_students"].values
        super_areas, distances = super_areas.get_closest_super_areas(
            coordinates, k=1, return_distance=True
        )
        distances_close = distances < max_distance_to_super_area
        coordinates = coordinates[distances_close]
        n_students = n_students[distances_close]
        universities = list()
        for coord, n_stud, super_area in zip(coordinates, n_students, super_areas):
            university = University(
                coordinates=coord, n_students_max=n_stud, super_area=super_area
            )
            universities.append(university)
        return cls(universities)
