import logging
import pickle
from june.groups import Group
from june.box.box_mode import Boxes, Box
from june.demography import Demography, Population
from june.distributors import (
    SchoolDistributor,
    HospitalDistributor,
    HouseholdDistributor,
    CareHomeDistributor,
    WorkerDistributor,
    CompanyDistributor,
)
from june.geography import Geography
from june.groups import Hospitals

logger = logging.getLogger(__name__)

allowed_super_groups = ["hospitals", "companies", "cemeteries", "schools", "households"]


def _populate_areas(geography, demography):
    people = Population()
    for area in geography.areas:
        area.populate(demography)
        people.extend(area.people)
    return people


class World(object):
    """
    This Class creates the world that will later be simulated.
    The world will be stored in pickle, but a better option needs to be found.
    
    Note: BoxMode = Demography +- Sociology - Geography
    """

    def __init__(
        self,
        geography: Geography,
        demography: Demography,
        include_households: bool = True,
        box_mode=False,
    ):
        """
        Initializes a world given a geography and a demography. For now, households are
        a special group because they require a mix of both groups (we need to fix
        this later). 

        Parameters
        ----------
        geography
            an instance of the Geography class specifying the "board"
        demography
            an instance of the Demography class with generators to generate people with 
            certain demographic attributes
        include_households
            whether to include households in the world or not (defualt = True)
        """
        self.box_mode = box_mode
        if self.box_mode:
            self.hospitals = Hospitals.for_box_mode()
            self.people = _populate_areas(geography, demography)
            self.boxes = Boxes([Box()])
            self.boxes.members[0].set_population(self.people)
            return
        self.areas = geography.areas
        self.super_areas = geography.super_areas
        print("populating the world's geography with the specified demography...")
        self.people = _populate_areas(geography, demography)

        if hasattr(geography, "carehomes"):
            self.carehomes = geography.carehomes
            CareHomeDistributor().populate_carehome_in_areas(self.areas)

        if include_households:
            household_distributor = HouseholdDistributor.from_file()
            self.households = household_distributor.distribute_people_and_households_to_areas(
                self.areas
            )
        if (
            hasattr(geography, "companies")
            or hasattr(geography, "hospitals")
            or hasattr(geography, "schools")
        ):
            worker_distr = WorkerDistributor.for_geography(
                geography
            )  # atm only for_geography()
            worker_distr.distribute(geography, self.people)

        if hasattr(geography, "schools"):
            self.schools = geography.schools
            school_distributor = SchoolDistributor(geography.schools)
            school_distributor.distribute_kids_to_school(self.areas)
            school_distributor.distribute_teachers_to_schools_in_super_areas(
                self.super_areas
            )

        if hasattr(geography, "companies"):
            self.companies = geography.companies
            company_distributor = CompanyDistributor()
            company_distributor.distribute_adults_to_companies_in_super_areas(
                geography.super_areas
            )

        if hasattr(geography, "hospitals"):
            self.hospitals = geography.hospitals
            hospital_distributor = HospitalDistributor(geography.hospitals)
            hospital_distributor.distribute_medics_to_super_areas(self.super_areas)

        if hasattr(geography, "cemeteries"):
            self.cemeteries = geography.cemeteries

    @classmethod
    def from_geography(cls, geography: Geography, box_mode=False):
        """
        Initializes the world given a geometry. The demography is calculated
        with the default settings for that geography.
        """
        demography = Demography.for_geography(geography)
        return cls(geography, demography, box_mode=box_mode)

    def __getstate__(self):
        """ I am being pickled! Removes links from group to people
        to avoid circular references and to make the world pickleable.
        The state of the world is then restored, however, some temporary
        information store by distributors to area or group objects
        might be deleted (they shouldn't be there anyway..)
        """
        #original_state = self.__dict__.copy()
        for supergroup_name in allowed_super_groups:
            if hasattr(self, supergroup_name):
                supergroup = getattr(self, supergroup_name)
                supergroup.erase_people_from_groups_and_subgroups()

        for geo_superunit in ["super_areas", "areas"]:
            supergeo = getattr(self, geo_superunit)
            supergeo.erase_people_from_geographical_unit()
            for geo in supergeo:
                geo.erase_people_from_geographical_unit()
        state_dict = self.__dict__.copy()  # state to pickle
        return state_dict

    def restore_world(self):
        for person in self.people:
            for subgroup in person.subgroups:
                subgroup.append(person)
            if person.area is not None:
                person.area.add(person)

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.restore_world()

    @classmethod
    def from_pickle(self, pickle_path):
        with open(pickle_path, "rb") as f:
            world = pickle.load(f)
        return world

    def to_pickle(self, save_path):
        with open(save_path, "wb") as f:
            pickle.dump(self, f)
        self.restore_world()
