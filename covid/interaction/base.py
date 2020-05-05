from covid.interaction.parameters import ParameterInitializer
import numpy as np
import sys
import random


class Interaction(ParameterInitializer):
    def __init__(self, user_parameters, required_parameters, world):
        super().__init__("interaction", user_parameters, required_parameters)
        self.groups = []
        self.world = world
        self.intensities = {}

    def time_step(self):
        delta_time = self.world.timer.now - self.world.timer.previous
        # TODO think how we treat the double update_status_lists and make it consistent
        # with delta_time
        # print ("-----------------------------------------------------")
        for grouptype in self.groups:
            for group in grouptype.members:
                if group.size != 0:
                    group.update_status_lists(time=self.world.timer.now, delta_time=0)
        # print ("-----------------------------------------------------")
        for grouptype in self.groups:
            for group in grouptype.members:
                if group.size != 0:
                    self.single_time_step_for_group(group, self.world.timer.now)
        # print ("-----------------------------------------------------")
        for grouptype in self.groups:
            for group in grouptype.members:
                if group.size != 0:
                    group.update_status_lists(
                        time=self.world.timer.now, delta_time=delta_time
                    )
        # print ("-----------------------------------------------------")

    def single_time_step_for_group(self, group, time):
        pass

    def get_intensity(self, grouptype):
        if grouptype in self.intensities:
            return self.intensities[grouptype]
        return 1

    def set_intensities(self, intensities):
        self.intensities = intensities

    def set_intensity(self, grouptype, intensity):
        self.intensities[grouptype] = intensity