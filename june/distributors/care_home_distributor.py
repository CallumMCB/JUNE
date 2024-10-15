import logging
import yaml
from random import shuffle, choice
from collections import OrderedDict, defaultdict

import numpy as np
import pandas as pd

from june import paths
from june.geography import Area, SuperAreas


logger = logging.getLogger("care_home_distributor")

care_homes_per_area_filename = paths.data_path / "input/care_homes/care_homes_ew.csv"

default_config_filename = paths.configs_path / "defaults/groups/care_home.yaml"
default_communal_men_by_super_area = (
    paths.data_path / "input/care_homes/communal_male_residents_by_super_area.csv"
)
default_communal_women_by_super_area = (
    paths.data_path / "input/care_homes/communal_female_residents_by_super_area.csv"
)


class CareHomeError(BaseException):
    pass


class CareHomeDistributor:
    def __init__(
        self,
        communal_men_by_super_area: dict,
        communal_women_by_super_area: dict,
        n_residents_per_worker: int = 10,
        workers_sector="Q",
    ):
        """
        Tool to distribute people from a certain area into a care home, if there is one.

        Parameters
        ----------
        min_age_in_care_home
            minimum age to put people in care home.
        """
        self.communal_men_by_super_area = communal_men_by_super_area
        self.communal_women_by_super_area = communal_women_by_super_area
        self.n_residents_per_worker = n_residents_per_worker
        self.workers_sector = workers_sector

    @classmethod
    def from_file(
        cls,
        communal_men_by_super_area_filename: str = default_communal_men_by_super_area,
        communal_women_by_super_area_filename: str = default_communal_women_by_super_area,
        config_filename: str = default_config_filename,
    ):
        with open(config_filename) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        communal_men_df = pd.read_csv(communal_men_by_super_area_filename, index_col=0)
        communal_women_df = pd.read_csv(
            communal_women_by_super_area_filename, index_col=0
        )
        return cls(
            communal_men_by_super_area=communal_men_df.T.to_dict(),
            communal_women_by_super_area=communal_women_df.T.to_dict(),
            n_residents_per_worker=config["n_residents_per_worker"],
            workers_sector=config["workers_sector"],
        )

    def _create_people_dicts(self, area: Area):
        """
        Creates dictionaries with the men and women per age key living in the area.
        """
        people_by_sex = {"m": defaultdict(list), "f": defaultdict(list)}

        for person in area.people:
            people_by_sex[person.sex][person.age].append(person)

        return people_by_sex["m"], people_by_sex["f"]

    def _find_person_in_age_range(self, people_by_age: dict, age_1, age_2):
        available_people = [person for age in range(age_1, age_2 + 1) for person in people_by_age.get(age, [])]

        if not available_people:
            return None

        chosen_person = choice(available_people)

        # Remove the chosen person from the dictionary
        people_by_age[chosen_person.age].remove(chosen_person)

        # Delete the age group if it's now empty
        if not people_by_age[chosen_person.age]:
            del people_by_age[chosen_person.age]

        return chosen_person

    def _sort_dictionary_by_age_range_key(self, d: dict):
        """
        Sorts a dictionary by decreasing order of the age range in the keys.
        """
        ages = [age_range[0] for age_range in d.keys()]
        men_age_ranges_sorted = np.array(list(d.keys()))[np.argsort(ages)[::-1]]

        return OrderedDict((key, d[key]) for key in men_age_ranges_sorted)

    def populate_care_homes_in_super_areas(self, super_areas: SuperAreas):
        """
        Populates care homes in the super areas. For each super area, we look into the
        population that lives in communal establishments, from there we pick the oldest ones
        to live in care homes.
        """
        logger.info("Populating care homes")
        total_care_home_residents = 0

        for super_area in super_areas:
            communal_men_sorted, communal_women_sorted = self._get_sorted_communal_residents(super_area)
            areas_with_care_homes = self._areas_with_care_homes(super_area)
            areas_dicts = [self._create_people_dicts(area) for area in areas_with_care_homes]

            total_care_home_residents += self._allocate_residents_to_care_homes(
                areas_with_care_homes, areas_dicts, communal_men_sorted, communal_women_sorted
            )

        logger.info(f"This world has {total_care_home_residents} people living in care homes.")

    def _get_sorted_communal_residents(self, super_area):
        """Fetches and sorts communal residents for a given msoa"""
        men_communal_residents = self.communal_men_by_super_area[super_area.name]
        women_communal_residents = self.communal_women_by_super_area[super_area.name]

        communal_men_sorted = self._sort_dictionary_by_age_range_key(men_communal_residents)
        communal_women_sorted = self._sort_dictionary_by_age_range_key(women_communal_residents)

        assert communal_men_sorted.keys() == communal_women_sorted.keys()
        return communal_men_sorted, communal_women_sorted

    def _areas_with_care_homes(self, super_area):
        """Allocates residents from commmunal establishments to care homes."""
        areas_with_care_homes = [area for area in super_area.areas if area.care_home is not None]
        shuffle(areas_with_care_homes)
        return areas_with_care_homes

    def _allocate_residents_to_care_homes(self, areas_with_care_homes, areas_dicts, communal_men_sorted, communal_women_sorted):
        total_care_home_residents = 0
        found_person = True

        while found_person:
            found_person = False

            for i, area in enumerate(areas_with_care_homes):
                care_home = area.care_home
                if len(care_home.residents) < care_home.n_residents:
                    for age_range in communal_men_sorted:
                        if communal_men_sorted[age_range] <= 0 and communal_women_sorted[age_range] <= 0:
                            continue

                        person = self._find_person_for_care_home(areas_dicts[i], age_range, communal_men_sorted, communal_women_sorted)

                        if person:
                            care_home.add(person, care_home.SubgroupType.residents)
                            total_care_home_residents += 1
                            found_person = True
                            break

        return total_care_home_residents

    def _find_person_for_care_home(self, area_dict, age_range, communal_men_sorted, communal_women_sorted):
        """Finds a person from the communal residents to add to the care home."""
        men_dict, women_dict = area_dict
        age1, age2 = list(map(int, age_range.split("-")))

        if communal_men_sorted[age_range] > 0:
            person = self._find_person_in_age_range(men_dict, age1, age2)
            if person:
                communal_men_sorted[age_range] -= 1
                return person

        person = self._find_person_in_age_range(women_dict, age1, age2)
        if person:
            communal_women_sorted[age_range] -= 1
            return person

    def distribute_workers_to_care_homes(self, super_areas: SuperAreas):
        for super_area in super_areas:
            care_homes = [
                area.care_home
                for area in super_area.areas
                if area.care_home is not None
            ]
            if not care_homes:
                continue
            carers = [
                person
                for person in super_area.workers
                if (
                    person.sector == "Q"
                    and person.primary_activity is None
                    and person.sub_sector is None
                )
            ]
            shuffle(carers)
            for care_home in care_homes:
                while len(care_home.workers) < care_home.n_workers:
                    try:
                        carer = carers.pop()
                    except Exception:
                        logger.info(
                            f"Care home in area {care_home.area.name} has not enough workers!"
                        )
                        break
                    care_home.add(
                        person=carer,
                        subgroup_type=care_home.SubgroupType.workers,
                        activity="primary_activity",
                    )
                    carer.lockdown_status = "key_worker"
