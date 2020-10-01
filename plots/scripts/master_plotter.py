import numpy as np
import pandas as pd
import time
from pathlib import Path
from datetime import datetime, timedelta
import argparse
import os
import matplotlib.pyplot as plt

from june.hdf5_savers import generate_world_from_hdf5
from policy import PolicyPlots
from leisure import LeisurePlots
from companies import CompanyPlots
from households import HouseholdPlots

plt.style.use(['science'])
plt.style.reload_library()

default_world_filename = 'world.hdf5'

class Plotter:
    """
    Master plotting script for paper and validation plots
    Parameters
    ----------
    world
        Preloaded world which can also be passed from the master plotting script
    """

    def __init__(self, world):
        self.world = world

    @classmethod
    def from_file(
            cls,
            world_filename: str = default_world_filename,
    ):
        world = generate_world_from_hdf5(world_filename)

        return Plotter(world)

    def plot_households(self, save_dir: Path = Path("../plots/households")):
        save_dir.mkdir(exist_ok=True, parents=True)
        print("Setting up household plots")
        household_plots = HouseholdPlots(self.world)

        print ("Loading household data")
        household_plots.load_household_data()

        print ("Plotting household sizes")
        household_sizes_plot = household_plots.plot_household_sizes()
        household_sizes_plot.plot()
        plt.savefig(save_dir / 'household_sizes.png', dpi=150, bbox_inches='tight')

        print ("Plotting household probability matrix")
        household_probability_matrix = household_plots.plot_household_probability_matrix()
        household_probability_matrix.plot()
        plt.savefig(save_dir / 'household_prob_matrix.png', dpi=150, bbox_inches='tight')

        print ("Plotting household age differences")
        f, ax = household_plots.plot_household_age_differences()
        plt.plot()
        plt.savefig(save_dir / 'household_age_differences.png', dpi=150, bbox_inches='tight')


    def plot_companies(
            self,
            save_dir: str = '../plots/companies/'
    ):
        "Make all company plots"

        if not os.path.exists(save_dir):
            os.mkdir(save_dir)

        print ("Setting up company plots")

        company_plots = CompanyPlots(self.world)

        print ("Loading company data")
        company_plots.load_company_data()

        print ("Plotting company sizes")
        company_sizes_plot = company_plots.plot_company_sizes()
        company_sizes_plot.plot()
        plt.savefig(save_dir + 'company_sizes.png', dpi=150, bbox_inches='tight')

        print ("Plotting company workers")
        company_workers_plot = company_plots.plot_company_workers()
        company_workers_plot.plot()
        plt.savefig(save_dir + 'company_workers.png', dpi=150, bbox_inches='tight')

        print ("Plotting company sectors")
        company_sectors_plot = company_plots.plot_company_sectors()
        company_sectors_plot.plot()
        plt.savefig(save_dir + 'company_sectors.png', dpi=150, bbox_inches='tight')

        print ("Plotting work distance travel")
        work_distance_travel_plot = company_plots.plot_work_distance_travel()
        work_distance_travel_plot.plot()
        plt.savefig(save_dir + 'work_distance_travel.png', dpi=150, bbox_inches='tight')
        
    
    def plot_leisure(
            self,
            save_dir: str = '../plots/leisure/'
    ):
        "Make all leisure plots"

        if not os.path.exists(save_dir):
            os.mkdir(save_dir)

        print ("Setting up leisure plots")

        leisure_plots = LeisurePlots(self.world)

        print ("Running poisson process")
        leisure_plots.run_poisson_process()

        print ("Plotting week probabilities")
        week_probabilities_plot = leisure_plots.plot_week_probabilities()
        week_probabilities_plot.plot()
        plt.savefig(save_dir + 'week_probabilities.png', dpi=150, bbox_inches='tight')
        
        plt.clf()
        print ("Plotting leisure time spent")
        leisure_time_spent_plot = leisure_plots.plot_leisure_time_spent()
        leisure_time_spent_plot.plot()
        plt.savefig(save_dir + 'leisure_time_spent.png', dpi=150, bbox_inches='tight')
        
    def plot_policies(
            self,
            save_dir: str = '../plots/policy/'
    ):
        "Make all policy plots"

        if not os.path.exists(save_dir):
            os.mkdir(save_dir)

        print ("Setting up policy plots")

        policy_plots = PolicyPlots(self.world)

        print ("Plotting restaurant reopening")
        restaurant_reopening_plot = policy_plots.plot_restaurant_reopening()
        restaurant_reopening_plot.plot()
        plt.savefig(save_dir + 'restaurant_reopening.png', dpi=150, bbox_inches='tight')

        print ("Plotting school reopening")
        school_reopening_plot = policy_plots.plot_school_reopening()
        school_reopening_plot.plot()
        plt.savefig(save_dir + 'school_reopening.png', dpi=150, bbox_inches='tight')

        print ("Plotting beta fraction")
        beta_fraction_plot = policy_plots.plot_beta_fraction()
        beta_fraction_plot.plot()
        plt.savefig(save_dir + 'beta_fraction.png', dpi=150, bbox_inches='tight')

        print ("All policy plots finished")
    
    def plot_all(self):

        print ("Plotting the world")

        self.plot_companies()
        self.plot_leisure()
        self.plot_policies()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Plotter for JUNE's world.")

    parser.add_argument(
        "-w",
        "--world_filename",
        help="Relative directory to world file",
        required=False,
        default = default_world_filename
    )
    parser.add_argument(
        "-q",
        "--households",
        help="Plot only households",
        required=False,
        default = False,
        action="store_true"
    )
    args = parser.parse_args()
    plotter = Plotter.from_file(args.world_filename)
    if args.households:
        plotter.plot_households()
    else:
        plotter.plot_all()
