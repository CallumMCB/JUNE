from typing import Dict, Union
from random import random, shuffle, randint
import datetime

from .event import Event
from june.utils import parse_age_probabilities


class DomesticCare(Event):
    """
    This event models people taking care of their elderly who live
    alone or in couples. The logic is that at the beginning of each
    leisure time-step, people who have caring responsibilites go
    to their relatives household for the duration of their time-step.

    Parameters
    ----------
    start_time
        time from when the event is active (default is always)
    end_time
        time when the event ends (default is always)
    needs_care_probabilities
        dictionary mapping the probability of needing care per age.
        Example:
        needs_care_probabilities = {"0-65" : 0.0, "65-100" : 0.5}
    relative_frequency
        relative factor to scale the overall probabilities in needs_care_probabilities
        useful for when we want to change the caring frequency with lockdowns, etc.
    """

    def __init__(
        self,
        start_time: Union[str, datetime.datetime],
        end_time: Union[str, datetime.datetime],
        needs_care_probabilities: Dict[str, float],
        daily_going_probability=1.0,
    ):
        super().__init__(start_time=start_time, end_time=end_time)
        self.needs_care_probabilities = parse_age_probabilities(
            needs_care_probabilities
        )
        self.daily_going_probability = daily_going_probability

    def initialise(self, world):
        self._link_carers_to_households(world=world)

    def apply(self, world, activities, is_weekend):
        """
        When a household is reponsible for caring of another housheold,
        a random person is sent during leisure to take care of that household.
        We checked that the person is not at hospital when we send them.
        """
        if "leisure" not in activities or is_weekend:
            return
        for household in world.households:
            if household.household_to_care:
                people_household = list(household.residents)
                shuffle(people_household)
                for person in people_household:
                    if person.medical_facility is None and not person.busy:
                        person.subgroups.leisure = household.household_to_care[
                            household.get_leisure_subgroup_type(person)
                        ]
                        break

    def _link_carers_to_households(self, world):
        """
        Links old people households to other households that provide them with care aid.
        All linking is restricted to the super area level.
        """
        for super_area in world.super_areas:
            # get households that need care
            need_care = []
            can_provide_care = []
            for area in super_area.areas:
                for household in area.households:
                    if self._check_household_needs_care(household):
                        need_care.append(household)
                    if self._check_household_can_provide_care(household):
                        can_provide_care.append(household)
            shuffle(need_care)
            shuffle(can_provide_care)
            for needer, provider in zip(need_care, can_provide_care):
                provider.household_to_care = needer

    def _check_household_needs_care(self, household):
        """
        Check if a household needs care. We take the oldest
        person in the household to be representative of the risk
        for needing care.
        """
        oldest_person = None
        oldest_age = 0
        if household.type == "old":
            for person in household.residents:
                if person.age > oldest_age:
                    oldest_person = person
                    oldest_age = person.age
            care_probability = self.needs_care_probabilities[oldest_age]
            if random() < care_probability:
                return True
        return False

    def _check_household_can_provide_care(self, household):
        """
        We limit care providers to non-student households.
        """
        if household.type in ["student", "old"]:
            return False
        return True
