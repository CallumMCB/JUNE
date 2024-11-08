import random
from datetime import datetime

import pytest
from june import paths
from june.activity import activity_hierarchy
from june.epidemiology.epidemiology import Epidemiology
from june.epidemiology.infection import Immunity, InfectionSelector, InfectionSelectors
from june.groups.leisure import leisure
from june.groups.travel import Travel
from june.interaction import Interaction
from june.policy import Hospitalisation, MedicalCarePolicies, Policies
from june.simulator import Simulator

constant_config = (
    paths.configs_path
    / "defaults/epidemiology/infection/transmission/TransmissionConstant.yaml"
)
interaction_config = paths.configs_path / "tests/interaction.yaml"
test_config = paths.configs_path / "tests/test_simulator.yaml"


@pytest.fixture(name="selectors", scope="module")
def make_selector(health_index_generator):
    selector = InfectionSelector(
        health_index_generator=health_index_generator,
        transmission_config_path=constant_config,
    )
    selector.recovery_rate = 0.05
    selector.transmission_probability = 0.7
    return InfectionSelectors([selector])
    return selector


@pytest.fixture(name="medical_policies")
def make_policies():
    policies = Policies([Hospitalisation()])
    return MedicalCarePolicies.get_active_policies(
        policies=policies, date=datetime(2020, 3, 1)
    )


@pytest.fixture(name="sim")
def setup_sim(dummy_world, selectors):
    world = dummy_world
    for person in world.people:
        person.immunity = Immunity()
        person.infection = None
        person.subgroups.medical_facility = None
        person.dead = False
    leisure_instance = leisure.generate_leisure_for_world(
        world=world,
        list_of_leisure_groups=["pubs", "cinemas", "groceries"],
        daytypes={
            "weekday": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            "weekend": ["Saturday", "Sunday"],
        },
    )
    leisure_instance.distribute_social_venues_to_areas(
        world.areas, super_areas=world.super_areas
    )
    interaction = Interaction.from_file(config_filename=interaction_config)
    policies = Policies.from_file()
    epidemiology = Epidemiology(infection_selectors=selectors)
    travel = Travel()
    sim = Simulator.from_file(
        world=world,
        epidemiology=epidemiology,
        interaction=interaction,
        config_filename=test_config,
        leisure=leisure_instance,
        travel=travel,
        policies=policies,
    )
    sim.activity_manager.leisure.generate_leisure_probabilities_for_timestep(
        delta_time=3,
        working_hours=False,
        date=datetime.strptime("2020-03-01", "%Y-%m-%d"),
    )
    sim.clear_world()
    return sim


@pytest.fixture(name="health_index")
def create_health_index():
    def dummy_health_index(age, sex):
        return [0.1, 0.3, 0.5, 0.7, 0.9]

    return dummy_health_index


def test__everyone_has_an_activity(sim: Simulator):
    for person in sim.world.people.members:
        assert person.subgroups.iter().count(None) != len(person.subgroups.iter())


def test__apply_activity_hierarchy(sim: Simulator):
    unordered_activities = random.sample(activity_hierarchy, len(activity_hierarchy))
    ordered_activities = sim.activity_manager.apply_activity_hierarchy(
        unordered_activities
    )
    assert ordered_activities == activity_hierarchy


def test__activities_to_super_groups(sim: Simulator):
    activities = [
        "medical_facility",
        "commute",
        "primary_activity",
        "leisure",
        "residence",
    ]
    groups = sim.activity_manager.activities_to_super_groups(activities)

    assert groups == [
        "hospitals",
        "city_transports",
        "inter_city_transports",
        "schools",
        "companies",
        "universities",
        "pubs",
        "cinemas",
        "groceries",
        "household_visits",
        "care_home_visits",
        "households",
        "care_homes",
    ]


def test__clear_world(sim: Simulator):
    sim.clear_world()
    for group_name in sim.activity_manager.activities_to_super_groups(
        sim.activity_manager.all_activities
    ):
        if group_name in ["household_visits", "care_home_visits"]:
            continue
        grouptype = getattr(sim.world, group_name)
        for group in grouptype.members:
            for subgroup in group.subgroups:
                assert len(subgroup.people) == 0

    for person in sim.world.people.members:
        assert person.busy is False


def test__move_to_active_subgroup(sim: Simulator):
    sim.activity_manager.move_to_active_subgroup(
        ["residence"], sim.world.people.members[0]
    )
    assert sim.world.people.members[0].residence.group.spec in ("carehome", "household")


def test__move_people_to_residence(sim: Simulator):
    sim.activity_manager.move_people_to_active_subgroups(["residence"])
    for person in sim.world.people.members:
        assert person in person.residence.people
    sim.clear_world()


def test__move_people_to_leisure(sim: Simulator):
    n_leisure = 0
    n_cinemas = 0
    n_pubs = 0
    n_groceries = 0
    repetitions = 500
    for _ in range(repetitions):
        sim.clear_world()
        sim.activity_manager.move_people_to_active_subgroups(["leisure", "residence"])
        for person in sim.world.people.members:
            if person.leisure is not None:
                n_leisure += 1
                if person.leisure.group.spec == "care_home":
                    assert person.leisure.subgroup_type == 2  # visitors
                elif person.leisure.group.spec == "cinema":
                    n_cinemas += 1
                elif person.leisure.group.spec == "pub":
                    n_pubs += 1
                elif person.leisure.group.spec == "grocery":
                    n_groceries += 1
                if person not in person.residence.people:
                    assert person in person.leisure.people
    assert n_leisure > 0
    assert n_cinemas > 0
    assert n_pubs > 0
    assert n_groceries > 0
    sim.clear_world()


def test__move_people_to_primary_activity(sim: Simulator):
    sim.activity_manager.move_people_to_active_subgroups(
        ["primary_activity", "residence"]
    )
    for person in sim.world.people.members:
        if person.primary_activity is not None:
            assert person in person.primary_activity.people
    sim.clear_world()


def test__move_people_to_commute(sim: Simulator):
    sim.activity_manager.move_people_to_active_subgroups(["commute", "residence"])
    n_commuters = 0
    for person in sim.world.people.members:
        if person.commute is not None:
            n_commuters += 1
            assert person in person.commute.people
    assert n_commuters > 0
    sim.clear_world()


def test__bury_the_dead(sim: Simulator):
    dummy_person = sim.world.people.members[0]
    sim.epidemiology.infection_selectors.infect_person_at_time(dummy_person, 0.0)
    sim.epidemiology.bury_the_dead(sim.world, dummy_person)
    assert dummy_person in sim.world.cemeteries.members[0].people
    assert dummy_person.dead
    assert dummy_person.infection is None
