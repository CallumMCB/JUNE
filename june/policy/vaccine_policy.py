import operator
from random import random
import numpy as np
import datetime
from june.demography.person import Person
from .policy import Policy, PolicyCollection, Policies, read_date
from june import paths

# TODO: put in daily probability of being vaccinated
# TODO: modify parameters
# TODO: add option for second dose compliance (no second dose date needs testing)
# TODO: add type of vaccine that just makes people asymptomatic instead of non susceptible


class VaccinePlan:
    def __init__(
        self,
        first_dose_date,
        second_dose_date,
        first_dose_effective_days,
        second_dose_effective_days,
        first_dose_susceptibility,
        second_dose_susceptibility,
        original_susceptibility,
    ):
        self.first_dose_date = first_dose_date
        self.first_dose_effective_days = first_dose_effective_days
        self.first_dose_susceptibility = first_dose_susceptibility
        if second_dose_date is None:
            self.second_dose_date = first_dose_date + datetime.timedelta(
                days=self.first_dose_effective_days
            )
        else:
            self.second_dose_date = second_dose_date
        if second_dose_effective_days is None:
            self.second_dose_effective_days = 0
        else:
            self.second_dose_effective_days = second_dose_effective_days
        if second_dose_susceptibility is None:
            self.second_dose_susceptibility = first_dose_susceptibility
        else:
            self.second_dose_susceptibility = second_dose_susceptibility
        self.first_dose_effective_date = self.first_dose_date + datetime.timedelta(
            days=self.first_dose_effective_days
        )
        if second_dose_date is not None:
            self.second_dose_effective_date = (
                self.second_dose_date
                + datetime.timedelta(days=self.second_dose_effective_days)
            )
        else:
            self.second_dose_effective_date = first_dose_effective_date
        self.original_susceptibility = original_susceptibility

    @property
    def minimal_susceptibility(self):
        if self.second_dose_date is None:
            return self.first_dose_susceptibility
        else:
            return self.second_dose_susceptibility

    def straight_line(self, n_days, p0, p1):
        m = (p1[1] - p0[1]) / (p1[0] - p0[0])
        c = p1[1] - (m * p1[0])
        return m * n_days + c

    def susceptibility(self, date):
        if date < self.first_dose_effective_date:
            n_days = (date - self.first_dose_date).days
            return self.straight_line(
                n_days,
                p0=(0, self.original_susceptibility),
                p1=(self.first_dose_effective_days, self.first_dose_susceptibility),
            )
        elif self.first_dose_effective_date <= date < self.second_dose_date:
            return self.first_dose_susceptibility
        elif date < self.second_dose_effective_date:
            n_days = (date - self.second_dose_date).days
            return self.straight_line(
                n_days,
                p0=(0, self.first_dose_susceptibility),
                p1=(self.second_dose_effective_days, self.second_dose_susceptibility),
            )
        else:
            return self.second_dose_susceptibility


class VaccineDistribution(Policy):
    policy_type = "vaccine_distribuion"

    def __init__(
        self,
        start_time: str = "2100-01-01",
        end_time: str = "2100-01-02",
        group_description: dict = {"by": "residence", "group": "care_home"},
        group_coverage: float = 1.0,
        group_prevalence: float = 0.0,
        efficacy: float = 1.0,
        second_dose_compliance: float = 1.0,
        mean_time_delay: int = 1,
        std_time_delay: int = 1,
        effective_after_first_dose: int = 7,
        effective_after_second_dose: int = 7,
    ):
        """
        Policy to apply a vaccinated tag to people based on certain attributes with a given probability

        Parameters
        ----------
        start_time: start time of vaccine rollout
        end_time: end time of vaccine rollout
        group_description: type of people to get the vaccine, currently support:
            by: either residence, primary activity or age
            group: group type e.g. care_home for residence or XX-YY for age range
        group_coverage: % of group to be left as having target susceptibility after vaccination
        group_prevalence: the prevalence level in the group at time of vaccination rollout
        efficacy: % of people vaccinated who get the vaccinated tag
        second_dose_compliance: % of people getting their second vaccine dose if required
        mean_time_delay: mean time delay of the second dose being administered
        std_time_delay: std time delat of the second dose being administered
        effective_after_first_dose: number of days for the first dose to become effective
        effective_after_second_dose: number of days for second dose to become effective

        Assumptions
        -----------
        - The chance of getting your first dose in the first first_rollout_days days is uniform
        - The probability of when you get your second dose is chosen from a Gaussian distribution
          with mean mean_time_delay and std std_time_delay
        - The progression over time after vaccination (first and/or second dose) to reach the target
          susceptibilty is linear
        - The target susceptiblity after the first dose is half that of after the second dose
        - The target susceptibility after the second dose is 1-efficacy of the vaccine
        """

        super().__init__(start_time=start_time, end_time=end_time)
        self.group_attribute, self.group_value = self.process_group_description(
            group_description
        )
        self.total_days = (self.end_time - self.start_time).days
        self.group_coverage = group_coverage
        self.group_prevalence = group_prevalence
        self.second_dose_compliance = second_dose_compliance
        self.mean_time_delay = mean_time_delay
        self.std_time_delay = std_time_delay
        self.effective_after_first_dose = effective_after_first_dose
        self.effective_after_second_dose = effective_after_second_dose
        self.final_susceptibility = 1.0 - efficacy
        self.vaccinated_ids = set()

    def process_group_description(self, group_description):
        if group_description["by"] in ("residence", "primary_activity"):
            return f'{group_description["by"]}.group.spec', group_description["group"]
        elif group_description["by"] == "age":
            return f'{group_description["by"]}', group_description["group"]

    def is_target_group(self, person):
        if self.group_attribute is not "age":
            try:
                if (
                    operator.attrgetter(self.group_attribute)(person)
                    == self.group_value
                ):
                    return True
            except:
                return False
        else:
            if (
                int(self.group_value.split("-")[0])
                <= getattr(person, self.group_attribute)
                <= int(self.group_value.split("-")[1])
            ):
                return True
        return False

    def vaccinate(self, person, date):
        first_dose_effective_date = date + datetime.timedelta(
            days=self.effective_after_first_dose
        )
        # second dose
        if random() < self.second_dose_compliance:
            second_dose_lag = np.random.lognormal(
                mean=self.mean_time_delay, sigma=self.std_time_delay
            )
            second_dose_date = first_dose_effective_date + datetime.timedelta(
                days=int(second_dose_lag)
            )
            second_dose_effective_days = self.effective_after_second_dose
        else:
            second_dose_date = None
            second_dose_effective_days = None
        person.vaccine_plan = VaccinePlan(
            first_dose_date=date,
            first_dose_effective_days=self.effective_after_first_dose,
            first_dose_susceptibility=0.5
            * (person.susceptibility - self.final_susceptibility),
            second_dose_date=second_dose_date,
            second_dose_effective_days=second_dose_effective_days,
            second_dose_susceptibility=self.final_susceptibility,
            original_susceptibility=person.susceptibility,
        )
        self.vaccinated_ids.add(person.id)

    def daily_vaccine_probability(self, days_passed):
        return (self.group_coverage - self.group_prevalence) * (
            1 / (self.total_days - days_passed)
        )

    def apply(self, date: datetime, person: Person):
        if person.susceptibility == 1.0 and self.is_target_group(person):
            days_passed = (date - self.start_time).days
            if random() < self.daily_vaccine_probability(days_passed=days_passed):
                self.vaccinate(person=person, date=date)

    def update_susceptibility(self, person, date):
        person.susceptibility = person.vaccine_plan.susceptibility(date=date)

    def update_susceptibility_of_vaccinated(self, people, date):
        ids_to_remove = set()
        if self.vaccinated_ids:
            for pid in self.vaccinated_ids:
                person = people.get_from_id(pid)
                if person.susceptibility == person.vaccine_plan.minimal_susceptibility:
                    ids_to_remove.add(person.id)
                    person.vaccine_plan = None
                else:
                    self.update_susceptibility(person=person, date=date)
        self.vaccinated_ids -= ids_to_remove


class VaccineDistributions(PolicyCollection):
    policy_type = "vaccine_distribution"

    def apply(self, date: datetime, person: Person):
        if self.policies:
            for policy in self.policies:
                policy.apply(date=date, person=person)
