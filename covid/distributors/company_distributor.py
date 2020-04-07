import numpy as np
from random import uniform
from scipy import stats
import warnings
from covid.school import SchoolError

"""
This file contains routines to attribute people with different characteristics
according to census data.
"""


class CompanyDistributor:
    """
    Distributes students to different schools
    """

    def __init__(self, msoarea):
        self.area = msoarea
        self.MAX_COMPANIES = msoarea.world.config["schools"]["neighbour_schools"]

    def distribute_adults_to_companies(self):
        for person in self.msoarea.people.values():
            if (
                person.age <= self.SCHOOL_AGE_RANGE[1]
                and person.age >= self.SCHOOL_AGE_RANGE[0]
            ):  # person age from 5 up to 19 yo
                agegroup = self.area.world.decoder_age[person.age]
                agemean = self.compute_age_group_mean(agegroup)
                if self.is_agemean_full[
                    agegroup
                ]:  # if all schools at that age are full, assign one randomly
                    if person.age == 6:  # if it is 18-19 yo, then do not fill
                        continue
                    random_number = np.random.randint(0, self.MAX_SCHOOLS, size=1)[0]
                    school = self.closest_schools_by_age[agegroup][random_number]
                else:
                    schools_full = 0
                    for i in range(0, self.MAX_SCHOOLS):  # look for non full school
                        school = self.closest_schools_by_age[agegroup][i]
                        if school.n_pupils >= school.n_pupils_max:
                            schools_full += 1
                        else:
                            break
                    if schools_full == self.MAX_SCHOOLS:  # all schools are full
                        self.is_agemean_full[agegroup] = True
                        random_number = np.random.randint(0, self.MAX_SCHOOLS, size=1)[
                            0
                        ]
                        school = self.closest_schools_by_age[agegroup][random_number]
                    else:  # just keep the school saved in the previous for loop
                        pass
                school.pupils[school.n_pupils] = person
                person.school = school
                school.n_pupils += 1