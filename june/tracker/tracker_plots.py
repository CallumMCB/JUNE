from configparser import Interpolation
import numpy as np
import yaml
import pandas as pd

from pathlib import Path
from june import paths

from june.world import World

import matplotlib.pyplot as plt
import matplotlib.colors as colors
from matplotlib.dates import DateFormatter
import matplotlib.dates as mdates
import datetime

from june.tracker.tracker import Tracker

from june.mpi_setup import mpi_comm, mpi_size, mpi_rank
import logging
logger = logging.getLogger("tracker plotter")
mpi_logger = logging.getLogger("mpi")

if mpi_rank > 0:
    logger.propagate = False

from june.paths import data_path, configs_path
default_BBC_Pandemic_loc = data_path / "BBC_Pandemic"

DaysOfWeek_Names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

try:
    plt.style.use(['science','no-latex', "bright"])
    if mpi_rank == 0:
        print("Using 'science' matplotlib style")
except:
    plt.style.use('default')
    if mpi_rank == 0:
        print("Using default matplotlib style")
    pass

cmap_A = 'RdYlBu_r'
cmap_B = 'seismic'


#####################################################################################################################################################################
                            ################################### Plotting functions ##################################
#####################################################################################################################################################################

class PlotClass:
    """
    Class to plot everything tracker related

    Parameters
    ----------
    record_path:
        path for results directory

    Tracker_Contact_Type:
        list, list of tracker contact types to be loaded ["1D", "All"]

    Following parameters can be preloaded data from another plot class. If None data automatically loaded.
        Params,
        IM,
        CM_T,
        NCM,
        NCM_R,
        average_contacts,
        location_counters,
        location_counters_day,
        location_cum_pop,
        age_profiles,
        travel_distance

    Returns
    -------
        The tracker plotting class

    """
    def __init__(
        self,        
        record_path=Path(""),
        Tracker_Contact_Type="1D",

        Params=None,

        IM=None,
        CM_T=None,
        NCM=None,
        NCM_R=None,

        average_contacts=None,
        location_counters=None,
        location_counters_day=None,

        location_cum_pop = None,
        age_profiles = None,

        travel_distance = None,
    ):
        self.record_path = record_path
        self.Tracker_Contact_Type = Tracker_Contact_Type

        #Only plot fully merged data (Only applies to MPI runs, auto saved to merge if single core)
        folder_name = "merged_data_output"

        logger.info(f"Rank {mpi_rank} -- Begin loading")

        if Params is None:
            with open(self.record_path / folder_name / "tracker_Simulation_Params.yaml") as f:
                self.Params = yaml.load(f, Loader=yaml.FullLoader)
        else:
            self.Params = Params

        if IM is None:
            with open(self.record_path / folder_name / "CM_yamls" / "tracker_IM.yaml") as f:
                self.IM = yaml.load(f, Loader=yaml.FullLoader)
        else:
            self.IM = IM

        if CM_T is None:
            with open(self.record_path / folder_name / "CM_yamls" / f"tracker_{self.Tracker_Contact_Type}_Total_CM.yaml") as f:
                self.CM_T = yaml.load(f, Loader=yaml.FullLoader)
        else:
            self.CM_T = CM_T

        if NCM is None:
            with open(self.record_path / folder_name / "CM_yamls" / f"tracker_{self.Tracker_Contact_Type}_NCM.yaml") as f:
                self.NCM = yaml.load(f, Loader=yaml.FullLoader)
        else:
            self.NCM = NCM

        if NCM_R is None:
            with open(self.record_path / folder_name / "CM_yamls" / f"tracker_{self.Tracker_Contact_Type}_NCM_R.yaml") as f:
                self.NCM_R = yaml.load(f, Loader=yaml.FullLoader)
        else:
            self.NCM_R = NCM_R

        #Get Parameters of simulation
        self.total_days = self.Params["total_days"]
        self.day_types = {"weekend":self.Params["Weekend_Names"],"weekday":self.Params["Weekday_Names"]}
        self.NVenues = self.Params["NVenues"]
        #Get all the bin types
        self.relevant_bin_types = list(self.CM_T.keys())
        #Get all location names
        self.group_type_names = list(self.CM_T["syoa"].keys())
        #Get all CM options
        self.CM_Keys = list(self.CM_T["syoa"][self.group_type_names[0]].keys())
        #Get all contact sexes
        self.contact_sexes = list(self.CM_T["syoa"][self.group_type_names[0]]["sex"].keys())
    
        self.age_bins = {}
        for rbt in self.relevant_bin_types:
            if rbt == "Interaction":
                continue
            self.age_bins[rbt] = np.array(self.CM_T[rbt][self.group_type_names[0]]["bins"])

        if average_contacts is None:
            self.average_contacts = {}
            for rbt in self.relevant_bin_types:
                if rbt == "Interaction":
                    continue
                self.average_contacts[rbt] = pd.read_excel(
                    self.record_path / folder_name / "Venue_AvContacts" / "Average_contacts.xlsx",
                    sheet_name=rbt,
                    index_col=0,
                )
        else:
            self.average_contacts = average_contacts  


        if location_counters is None:
            self.location_counters = {"loc": {}}
            for loc in self.group_type_names:
                if loc in ["global", "shelter_inter", "shelter_intra"]:
                    continue
                self.location_counters["loc"][loc] = {}
                self.location_counters["Timestamp"] = None
                self.location_counters["dt"] = None


                for sex in self.contact_sexes:
                    filename = f"Venues_{sex}_Counts_BydT.xlsx"
                    sheet_name = Tracker.pluralise(self, loc)
                    df = pd.read_excel(
                    self.record_path / folder_name / "Venue_UniquePops" / filename,
                    sheet_name=sheet_name,
                    index_col=0,
                )
                    self.location_counters["loc"][loc][sex] = df.iloc[:,2:]
                    if self.location_counters["Timestamp"] is None:
                        self.location_counters["Timestamp"] = df["t"]
                        self.location_counters["delta_t"] = df["dt"]
        else:
            self.location_counters = location_counters

        if location_counters_day is None:
            self.location_counters_day = {"loc": {}}
            for loc in self.group_type_names:
                if loc in ["global", "shelter_inter", "shelter_intra"]:
                    continue
                self.location_counters_day["loc"][loc] = {}
                self.location_counters_day["Timestamp"] = None


                for sex in self.contact_sexes:
                    filename = f"Venues_{sex}_Counts_ByDate.xlsx"
                    sheet_name = Tracker.pluralise(self, loc)
                    df = pd.read_excel(
                    self.record_path / folder_name / "Venue_UniquePops" / filename,
                    sheet_name=sheet_name,
                    index_col=0,
                )
                    self.location_counters_day["loc"][loc][sex] = df.iloc[:,0:]
                    if self.location_counters_day["Timestamp"] is None:
                        self.location_counters_day["Timestamp"] = df["t"]
        else:
            self.location_counters_day = location_counters_day

        if location_cum_pop is None:
            self.location_cum_pop = {}
            for rbt in self.relevant_bin_types:
                self.location_cum_pop[rbt] = {}
                filename = self.record_path / folder_name / "Venue_TotalDemographics" / f"CumPersonCounts_{rbt}.xlsx"
                for loc in self.group_type_names:
                    self.location_cum_pop[rbt][loc] = {}
                    if rbt == "Interaction" and loc in ["global", "shelter_inter", "shelter_intra"]:
                            continue
                    df = pd.read_excel(
                        filename,
                        sheet_name=loc,
                        index_col=0,
                    )
                    self.location_cum_pop[rbt][loc] = df
        else:
            self.location_cum_pop = location_cum_pop

        if age_profiles is None:
            self.age_profiles = {}
            for rbt in self.relevant_bin_types:
                if rbt == "Interaction":
                    continue
                self.age_profiles[rbt] = {}
                filename = self.record_path / folder_name / "Venue_Demographics" / f"PersonCounts_{rbt}.xlsx"
                for loc in self.group_type_names:
                    self.age_profiles[rbt][loc] = {}

                    df = pd.read_excel(
                        filename,
                        sheet_name=loc,
                        index_col=0,
                    )
                    self.age_profiles[rbt][loc] = df.iloc[:-1,:]

        else:
            self.age_profiles = age_profiles

        if travel_distance is None:
            filename = self.record_path / folder_name / "Venue_TravelDist" / "Distance_traveled.xlsx"
            self.travel_distance= {}
            for loc in self.group_type_names:
                if loc in ["global", "shelter_inter", "shelter_intra"]:
                    continue
                sheet_name = Tracker.pluralise(self, loc)
                df = pd.read_excel(
                    filename,
                    sheet_name=sheet_name,
                    index_col=0,
                )
                self.travel_distance[loc] = df
        else:
            self.travel_distance = travel_distance

        logger.info(f"Rank {mpi_rank} -- Data loaded")

#####################################################################################################################################################################
                                ################################### General Plotting ##################################
#####################################################################################################################################################################

    def Get_SAMECMAP_Norm(self, dim, override=None):
        """
        If same colour map required this produces standarised colourmaps for different size matrices.

        Parameters
        ----------
            dim:
                int, the dimension (length) of square matrix
            override:
                string, Log, Lin, SymLog or SymLin. Override if SAMECMAP was False. (Applies to certain plots)

        Returns
        -------
            Norm:
                matplotlib.colors.Norm object

        """
        SAMElinvmin = {"small_dim" : 0, "large_dim" : 0}
        SAMElogvmin = {"small_dim" : 1e-1, "large_dim" : 1e-2}
        
        SAMElinvmax = {"small_dim" : 2.5e1, "large_dim" : 4e0}
        SAMElogvmax = {"small_dim" : 2.5e1, "large_dim" : 4e0}


        SAMEsymlogvmax = {"small_dim" : 3e0, "large_dim" : 3e0}
        SAMEsymlinvmax = {"small_dim" : 1e0, "large_dim" : .5e0}


        if dim < 5:
            kind = "small_dim"
        else:
            kind = "large_dim"

        if override is None:
            if self.SameCMAP == "Log":
                return colors.LogNorm(vmin=SAMElogvmin[kind], vmax=SAMElogvmax[kind])
            elif self.SameCMAP == "Lin":
                return colors.Normalize(vmin=SAMElinvmin[kind], vmax=SAMElinvmax[kind])
        elif override == "SymLog":
            return colors.SymLogNorm(linthresh = 1e-1, vmin=-SAMEsymlogvmax[kind], vmax=SAMEsymlogvmax[kind])
        elif override == "SymLin":
            return colors.Normalize(vmin=-SAMEsymlinvmax[kind], vmax=SAMEsymlinvmax[kind])
        elif override == "Log":
                return colors.LogNorm(vmin=SAMElogvmin[kind], vmax=SAMElogvmax[kind])
        elif override == "Lin":
            return colors.Normalize(vmin=SAMElinvmin[kind], vmax=SAMElinvmax[kind])
        return None
    
    def AnnotateCM(self, cm, cm_err, ax, thresh=1e10):
        """
        Function to annotate the CM with text. Including error catching for Nonetype errors.

        Parameters
        ----------
            cm:
                np.array contact matrix
            cm_err:
                np.array contact matrix errors
            ax:
                matplotlib axes
            thresh:
                threshhold value for CM text change colour

            
        Returns
        -------
            ax
        """
        size=15
        if cm.shape[0] == 3:
            size=12
        if cm.shape[0] > 3:
            size=10

        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                fmt = ".2f"
                if cm[i,j] == 1e-16:
                    cm[i,j] = 0
                if cm[i,j] > 1e8:
                    cm[i,j] = np.inf
                
                if cm_err is not None:
                    if np.isnan(cm_err[i,j]):
                        cm_err[i,j]=0

                    if cm_err[i,j] + cm[i,j] == 0:
                        fmt = ".0f"

                    text =  r"$ %s \pm %s$" % (format(cm[i, j], fmt), format(cm_err[i, j], fmt))
                else: 
                    text =  r"$ %s $" % (format(cm[i, j], fmt))

                if thresh == 1e8:
                    ax.text(j, i,text,
                        ha="center", va="center",
                        color="black",size=size)
                else:
                    ax.text(j, i,text,
                        ha="center", va="center",
                        color="white" if abs(cm[i, j] - 1) > thresh else "black",size=size)
        return ax

    def PlotCM(self, cm, cm_err, labels, ax, thresh=1e10, thumb=False, **plt_kwargs):
        """
        Function to imshow plot the CM.

        Parameters
        ----------
            cm:
                np.array contact matrix
            cm_err:
                np.array contact matrix errors
            labels:
                list of string bins labels (or none type)
            ax:
                matplotlib axes
            thresh:
                threshhold value for CM text change colour
            thumb:
                bool, make thumbnail style plots. e.g. no axis labels 
            **plt_kwargs:
                plot keyword arguements

        Returns
        -------
            im:
                referance to plot object
        """
        if cm is None:
            pass
        else:
            cm = cm.T

        if cm_err is None:
            pass
        else:
            cm_err = cm_err.T

        #im = ax.matshow(cm, **plt_kwargs)
        Interpolation = "None"
        im = ax.imshow(cm, **plt_kwargs, interpolation = Interpolation)
        ax.xaxis.tick_bottom()
        if labels is not None:
            if len(labels) < 25:
                ax.set_xticks(np.arange(len(cm)))
                ax.set_xticklabels(labels,rotation=45)
                ax.set_yticks(np.arange(len(cm)))
                ax.set_yticklabels(labels)

        # Loop over data dimensions and create text annotations.
        if cm.shape[0]*cm.shape[1] < 26:
            self.AnnotateCM(cm, cm_err, ax, thresh=thresh)
        if thumb == False:
            ax.set_xlabel("age group")
            ax.set_ylabel("contact age group")
        else:
            ax.axes.xaxis.set_visible(False)
            ax.axes.yaxis.set_visible(False)
            ax.set_xlabel("")
            ax.set_ylabel("")
        return im

    def CMPlots_GetLabels(self, bins):
        """
        Create list of labels for the bins in the CM plots

        Parameters
        ----------
            bins:
                np.array bin edges

        Returns
        -------
            labels:
                list of strings for bin labels or none type
        """
        if len(bins) < 25:
            return [
                f"{low}-{high-1}" for low,high in zip(bins[:-1], bins[1:])
            ]
        else:
            return None

    def MaxAgeBinIndex(self, bins, MaxAgeBin=60):
        """
        Get index for truncation of bins upto max age MaxAgeBin
            self.group_type_names

        Parameters
        ----------
            bins:
                Age bins
            MaxAgeBin:
                The maximum age at which to truncate the bins

        Returns
        -------
            Index
        """
        Array = [index for index in range(len(bins)) if bins[index] >= MaxAgeBin]
        if len(Array) != 0:
            return min(Array)
        else:
            return None

    def CMPlots_UsefulCM(self, bin_type, cm, cm_err=None, labels=None):
        """
        Truncate the CM for the plots to drop age bins of the data with no people.

        Parameters
        ----------
            binType:
                Name of bin type syoa, AC etc
            cm:
                np.array contact matrix
            cm_err:
                np.array contact matrix errors
            labels:
                list of strings for bin labels or none type
            
        Returns
        -------
            Truncated values of;
            cm:
                np.array contact matrix
            cm_err:
                np.array contact matrix errors
            labels:
                list of strings for bin labels or none type
        """
        MaxAgeBin = 60
        if bin_type == "Paper":
            MaxAgeBin = np.inf

        index = self.MaxAgeBinIndex(self.age_bins[bin_type], MaxAgeBin=MaxAgeBin)
        cm = cm[:index, :index]
        if cm_err is not None:
            cm_err=cm_err[:index,:index]
        if labels is not None:
            labels=labels[:index]
        return cm, cm_err, labels

    def IMPlots_GetLabels(self, contact_type):
        """
        Create list of labels for the bins in the input IM plots. More nuisanced as subgroups not always age bins.

        Parameters
        ----------
            contact_type:
                Location of contacts


        Returns
        -------
            labels:
                list of strings for bin labels or none type
        """

        bintype = self.IM[contact_type]["type"]
        bins = np.array(self.IM[contact_type]["bins"])

        if len(bins) < 25 and bintype == "Age":
            labels = [
                f"{int(low)}-{int(high-1)}" for low,high in zip(bins[:-1], bins[1:])
            ]
        elif len(bins) < 25 and bintype == "Discrete":
            labels = bins
        else:
            labels = None
        return labels

    def IMPlots_UsefulCM(self, contact_type, cm, cm_err=None, labels=None):
        """
        Truncate the CM for the plots to drop age bins of the data with no people.

        Parameters
        ----------
            contact_type:
                Location of contacts
            cm:
                np.array contact matrix
            cm_err:
                np.array contact matrix errors
            labels:
                list of strings for bin labels or none type
            
        Returns
        -------
            Truncated values of;
            cm:
                np.array contact matrix
            cm_err:
                np.array contact matrix errors
            labels:
                list of strings for bin labels or none type
        """
        bintype = self.IM[contact_type]["type"]
        bins = np.array(self.IM[contact_type]["bins"])

        if bintype == "Discrete":
            return cm, cm_err, labels
        
        index = self.MaxAgeBinIndex(np.array(bins))
        cm = cm[:index, :index]
        if cm_err is not None:
            cm_err=cm_err[:index,:index]
        if labels is not None:
            labels=labels[:index]
        return cm, cm_err, labels

#####################################################################################################################################################################
                                ################################### Grab CM  ##################################
#####################################################################################################################################################################
        
    def CMPlots_GetCM(self, bin_type, contact_type, sex="unisex", which="NCM"):
        """
        Get cm out of dictionary. 

        Parameters
        ----------
            binType:
                Name of bin type syoa, AC etc
            contact_type:
                Location of contacts
            sex:
                Sex contact matrix
            which:
                str, which matrix type to collect "NCM", "NCM_R", "CM_T"
            
        Returns
        -------
            cm:
                np.array contact matrix
            cm_err:
                np.array contact matrix errors
        """
        if bin_type != "Interaction":
            if which == "CM_T":
                cm = self.CM_T[bin_type][contact_type]["sex"][sex]["contacts"]
                cm_err = self.CM_T[bin_type][contact_type]["sex"][sex]["contacts_err"]
            elif which == "NCM":
                cm = self.NCM[bin_type][contact_type]["sex"][sex]["contacts"]
                cm_err = self.NCM[bin_type][contact_type]["sex"][sex]["contacts_err"]
            elif which == "NCM_R":
                cm = self.NCM_R[bin_type][contact_type]["sex"][sex]["contacts"]
                cm_err = self.NCM_R[bin_type][contact_type]["sex"][sex]["contacts_err"]
        else:
            if which == "CM_T":
                cm = self.CM_T[bin_type][contact_type]["contacts"]
                cm_err = self.CM_T[bin_type][contact_type]["contacts_err"]
            elif which == "NCM":
                cm = self.NCM[bin_type][contact_type]["contacts"]
                cm_err = self.NCM[bin_type][contact_type]["contacts_err"]
            elif which == "NCM_R":
                cm = self.NCM_R[bin_type][contact_type]["contacts"]
                cm_err = self.NCM_R[bin_type][contact_type]["contacts_err"]
        return np.array(cm), np.array(cm_err)

    def IMPlots_GetIM(self, contact_type):
        """
        Get IM out of dictionary. 

        Parameters
        ----------
            contact_type:
                Location of contacts

        Returns
        -------
            cm:
                np.array interactiojn matrix
            cm_err:
                np.array interaction matrix errors (could be none)
        """
        im = np.array(self.IM[contact_type]["contacts"], dtype=float)
        if "contacts_err" not in self.IM[contact_type].keys():
            im_err = None
        else:
            im_err = np.array(self.IM[contact_type]["contacts_err"], dtype=float)
        return im, im_err


    #####################################################################################################################################################################
                                ################################### Plotting ##################################
    #####################################################################################################################################################################

    
    def plot_contact_matrix_INOUT(self, bin_type, contact_type, sex="unisex", which="NCM_R", plot_BBC_Sheet=False):
        """
        Function to plot input contact matrix vs output for bin_type, contact_type and sex.

        Parameters
        ----------
            binType:
                Name of bin type syoa, AC etc
            contact_type:
                Location of contacts
            sex:
                Sex contact matrix
            which:
                str, which matrix type to collect "NCM", "NCM_R", "CM_T"
            
        Returns
        -------
            (ax1,ax2):
                matplotlib axes objects (Linear and Log)
        """
  
        IM, IM_err = self.IMPlots_GetIM(contact_type)
        labels_IM = self.IMPlots_GetLabels(contact_type)
        IM, IM_err, labels_IM = self.IMPlots_UsefulCM(contact_type, IM, cm_err=IM_err, labels=labels_IM)

        if len(np.nonzero(IM)[0]) != 0 and len(np.nonzero(IM)[1]) != 0:
            IM_Min = np.nanmin(IM[np.nonzero(IM)])
        else:
            IM_Min = 1e-1
        if np.isfinite(IM).sum() != 0:
            IM_Max = IM[np.isfinite(IM)].max()
        else:
            IM_Max = 1

        if np.isnan(IM_Min):
            IM_Min = 1e-1
        if np.isnan(IM_Max) or IM_Max == 0:
            IM_Max = 1

        IM = np.nan_to_num(IM, posinf=IM_Max, neginf=0, nan=0)

        labels = self.CMPlots_GetLabels(self.age_bins[bin_type])
        cm, cm_err = self.CMPlots_GetCM(bin_type, contact_type, sex=sex, which=which)
        cm, cm_err, labels = self.CMPlots_UsefulCM(bin_type, cm, cm_err, labels)

        if len(np.nonzero(cm)[0]) != 0 and len(np.nonzero(cm)[1]) != 0:
            cm_Min = np.nanmin(cm[np.nonzero(cm)])
        else:
            cm_Min = 1e-1
        if np.isfinite(cm).sum() != 0:
            cm_Max = cm[np.isfinite(cm)].max()
        else:
            cm_Max = 1

        if np.isnan(cm_Min):
            cm_Min = 1e-1
        if np.isnan(cm_Max) or cm_Max == 0:
            cm_Max = 1

        cm = np.nan_to_num(cm, posinf=cm_Max, neginf=0, nan=0)

        if self.SameCMAP == False:
            norm1 = colors.Normalize(vmin=0,vmax=IM_Max)
            norm2 = colors.Normalize(vmin=0,vmax=cm_Max)
        else:
            norm1 = self.Get_SAMECMAP_Norm(IM.shape[0])
            norm2 = self.Get_SAMECMAP_Norm(cm.shape[0])

        if plot_BBC_Sheet == False:
            plt.rcParams["figure.figsize"] = (15,5)
            f, (ax1,ax2) = plt.subplots(1,2)
            f.patch.set_facecolor('white')

            
            
            im1 = self.PlotCM(IM+1e-16, IM_err, labels_IM, ax1, origin='lower',cmap=cmap_A,norm=norm1)
            im2 = self.PlotCM(cm+1e-16, cm_err, labels, ax2, origin='lower',cmap=cmap_A,norm=norm2)

            f.colorbar(im1, ax=ax1, extend="both")
            f.colorbar(im2, ax=ax2, extend="both")

            ax1.set_title(f"Interaction Matrix (IM)")
            ax2.set_title(f"Output Contact Matrix ({which})")
            #f.suptitle(f"{bin_type} binned contacts in {contact_type}")
            plt.tight_layout()
            return (ax1,ax2)
        else:
            df = pd.read_excel(default_BBC_Pandemic_loc / "BBC reciprocal matrices by type and context.xls", sheet_name =plot_BBC_Sheet)
            bbc_cm = df.iloc[:,1:].values.T
            bbc_labels = df.iloc[:,0].values

            bbc_Max = np.nanmax(bbc_cm)
            bbc_Min = np.nanmin(bbc_cm)

            cm_Max = max(bbc_Max, cm_Max)

            plt.rcParams["figure.figsize"] = (15,5)
            f, (ax1,ax2, ax3) = plt.subplots(1,3)
            f.patch.set_facecolor('white')


            im1 = self.PlotCM(IM+1e-16, IM_err, labels_IM, ax1, origin='lower',cmap=cmap_A,norm=norm1)
            im2 = self.PlotCM(cm+1e-16, cm_err, labels, ax2, origin='lower',cmap=cmap_A,norm=norm2)
            im3 = self.PlotCM(bbc_cm, None, bbc_labels, ax3, origin='lower',cmap=cmap_A,norm=norm2)

            f.colorbar(im1, ax=ax1, extend="both")
            f.colorbar(im2, ax=ax2, extend="both")
            f.colorbar(im3, ax=ax3, extend="both")

            ax1.set_title(f"Interaction Matrix (IM)")
            ax2.set_title(f"Output Contact Matrix ({which})")
            ax3.set_title(f"BBC Pandemic Matrix ({plot_BBC_Sheet})")
            #f.suptitle(f"{bin_type} binned contacts in {contact_type}")
            plt.tight_layout()
            return (ax1,ax2, ax3)

    
    def plot_interaction_matrix(self, contact_type):
        """
        Function to plot interaction matrix for contact_type

        Parameters
        ----------
            contact_type:
                Location of contacts
            
        Returns
        -------
            ax1:
                matplotlib axes object
        """
        IM, IM_err = self.IMPlots_GetIM(contact_type)
        labels_IM = self.IMPlots_GetLabels(contact_type)
        IM, IM_err, labels_IM = self.IMPlots_UsefulCM(contact_type, IM, cm_err=IM_err, labels=labels_IM)

        if len(np.nonzero(IM)[0]) != 0 and len(np.nonzero(IM)[1]) != 0:
            IM_Min = np.nanmin(IM[np.nonzero(IM)])
        else:
            IM_Min = 1e-1
        if np.isfinite(IM).sum() != 0:
            IM_Max = IM[np.isfinite(IM)].max()
        else:
            IM_Max = 1


        if np.isnan(IM_Min):
            IM_Min = 1e-1
        if np.isnan(IM_Max) or IM_Max == 0:
            IM_Max = 1

        IM = np.nan_to_num(IM, posinf=IM_Max, neginf=0, nan=0)


        labels_CM = labels_IM
        if contact_type in self.CM_T["Interaction"].keys():
            cm, cm_err = self.CMPlots_GetCM("Interaction", contact_type, which="NCM")
            cm, cm_err, _ = self.IMPlots_UsefulCM(contact_type, cm, cm_err=cm_err, labels=labels_CM)
        else: #The venue wasn't tracked
            cm = np.zeros_like(IM)
            cm_err = np.zeros_like(cm)

        if len(np.nonzero(cm)[0]) != 0 and len(np.nonzero(cm)[1]) != 0:
            cm_Min = np.nanmin(cm[np.nonzero(cm)])
        else:
            cm_Min = 1e-1
        if np.isfinite(cm).sum() != 0:
            cm_Max = cm[np.isfinite(cm)].max()
        else:
            cm_Max = 1

        if np.isnan(cm_Min):
            cm_Min = 1e-1
        if np.isnan(cm_Max) or cm_Max == 0:
            cm_Max = 1
        cm = np.nan_to_num(cm, posinf=cm_Max, neginf=0, nan=0)

        vMax = max(cm_Max, IM_Max)
        vMin = 1e-2
        
        plt.rcParams["figure.figsize"] = (15,5)
        f, (ax1,ax2, ax3) = plt.subplots(1,3)
        f.patch.set_facecolor('white')


        if self.SameCMAP == False:
            norm1=colors.Normalize(vmin=vMin, vmax=vMax)
            norm2=colors.Normalize(vmin=vMin, vmax=vMax)
        else:
            
            norm1 = self.Get_SAMECMAP_Norm(IM.shape[0])
            norm2 = self.Get_SAMECMAP_Norm(cm.shape[0])

        im1 = self.PlotCM(IM+1e-16, IM_err, labels_IM, ax1, origin='lower',cmap=cmap_A, norm=norm1)
        im2 = self.PlotCM(cm+1e-16, cm_err, labels_CM, ax2, origin='lower',cmap=cmap_A,norm=norm2)

        ratio = cm/IM
        ratio = np.nan_to_num(ratio)
        ratio_values = ratio[np.nonzero(ratio) and ratio<1e3]
        if len(ratio_values) != 0:
            ratio_max = np.nanmax(ratio_values)
            ratio_min = np.nanmin(ratio_values)
            diff_max = np.max([abs(ratio_max-1),abs(ratio_min-1)])
            if diff_max < 0.5:
                diff_max = 0.5
        else:
            diff_max = 0.5
        if IM_err is None:
            IM_err = np.zeros_like(IM)
        ratio_errors = ratio * np.sqrt((cm_err/cm)**2+(IM_err/IM)**2)

        norm=colors.Normalize(vmin=1-diff_max,vmax=1+diff_max)
        norm=colors.Normalize(vmin=1-1,vmax=1+1)
        im3 = self.PlotCM(ratio, ratio_errors, labels_CM, ax3, thresh=diff_max/3, origin='lower',cmap=cmap_B, norm=norm)
        f.colorbar(im1, ax=ax1, extend="both")
        f.colorbar(im2, ax=ax2, extend="both")
        f.colorbar(im3, ax=ax3, extend="both")
        ax1.set_title("Interaction Matrix (IM)")
        ax2.set_title("Normalised Contact Matrix (NCM)")
        ax3.set_title("NCM / IM")

        #f.suptitle(f"Survey interaction binned contacts in {contact_type}")
        plt.tight_layout()
        return ax1
        
    def plot_contact_matrix(self, bin_type, contact_type, sex="unisex", which="NCM"):
        """
        Function to plot contact matrix for bin_type, contact_type and sex.

        Parameters
        ----------
            binType:
                Name of bin type syoa, AC etc
            contact_type:
                Location of contacts
            sex:
                Sex contact matrix
            which:
                str, which matrix type to collect "NCM", "NCM_R", "CM_T"
            
        Returns
        -------
            (ax1,ax2):
                matplotlib axes objects (Linear and Log)
        """
        cm, cm_err = self.CMPlots_GetCM(bin_type, contact_type, sex=sex, which=which)
        if bin_type == "Interaction":
            labels = self.IMPlots_GetLabels(contact_type)
        else:
            labels = self.CMPlots_GetLabels(self.age_bins[bin_type])
            cm, cm_err, labels = self.CMPlots_UsefulCM(bin_type, cm, cm_err, labels)

        if len(np.nonzero(cm)[0]) != 0 and len(np.nonzero(cm)[1]) != 0:
            cm_Min = np.nanmin(cm[np.nonzero(cm)])
        else:
            cm_Min = 1e-1
        if np.isfinite(cm).sum() != 0:
            cm_Max = cm[np.isfinite(cm)].max()
        else:
            cm_Max = 1

        if np.isnan(cm_Min):
            cm_Min = 1e-1
        if np.isnan(cm_Max) or cm_Max == 0:
            cm_Max = 1

        cm = np.nan_to_num(cm, posinf=cm_Max, neginf=0, nan=0)

        if self.SameCMAP == False or which=="CM_T":
            normlin= colors.Normalize(vmin=0,vmax=cm_Max)
            normlog = colors.LogNorm(vmin=cm_Min, vmax=cm_Max)
        else:
            normlin = self.Get_SAMECMAP_Norm(cm.shape[0], override="Lin")
            normlog = self.Get_SAMECMAP_Norm(cm.shape[0], override="Log")


        plt.rcParams["figure.figsize"] = (15,5)
        f, (ax1,ax2) = plt.subplots(1,2)
        f.patch.set_facecolor('white')

        
        im1 = self.PlotCM(cm+1e-16, cm_err, labels, ax1, origin='lower',cmap=cmap_A,norm=normlin)
        im2 = self.PlotCM(cm+1e-16, cm_err, labels, ax2, origin='lower',cmap=cmap_A, norm=normlog)

        f.colorbar(im1, ax=ax1, extend="both")
        f.colorbar(im2, ax=ax2, extend="both")

        ax1.set_title("Linear Scale")
        ax2.set_title("Log Scale")
        #f.suptitle(f"{bin_type} binned contacts in {contact_type} for {sex}")
        plt.tight_layout()
        return (ax1,ax2)

    def plot_contact_matrix_thumb(self, log, bin_type, contact_type, sex="unisex", which="NCM"):
        """
        Function to plot contact matrix for bin_type, contact_type and sex.

        Parameters
        ----------
            log:
                bool, shold be log plot?
            binType:
                Name of bin type syoa, AC etc
            contact_type:
                Location of contacts
            sex:
                Sex contact matrix
            which:
                str, which matrix type to collect "NCM", "NCM_R", "CM_T"
            
        Returns
        -------
            (ax1,ax2):
                matplotlib axes objects (Linear and Log)
        """
        
        cm, cm_err = self.CMPlots_GetCM(bin_type, contact_type, sex=sex, which=which)
        if bin_type == "Interaction":
            labels = self.IMPlots_GetLabels(contact_type)
        else:
            labels = self.CMPlots_GetLabels(self.age_bins[bin_type])
            cm, cm_err, labels = self.CMPlots_UsefulCM(bin_type, cm, cm_err, labels)

        if len(np.nonzero(cm)[0]) != 0 and len(np.nonzero(cm)[1]) != 0:
            cm_Min = np.nanmin(cm[np.nonzero(cm)])
        else:
            cm_Min = 1e-1
        if np.isfinite(cm).sum() != 0:
            cm_Max = cm[np.isfinite(cm)].max()
        else:
            cm_Max = 1

        if np.isnan(cm_Min):
            cm_Min = 1e-1
        if np.isnan(cm_Max) or cm_Max == 0:
            cm_Max = 1

        cm = np.nan_to_num(cm, posinf=cm_Max, neginf=0, nan=0)

        plt.rcParams["figure.figsize"] = (5,5)
        f, ax1 = plt.subplots(1,1)
        f.patch.set_facecolor('white')

        if self.SameCMAP == False or which=="CM_T":
            normlin = colors.Normalize(vmin=0,vmax=cm_Max)
            normlog = colors.LogNorm(vmin=cm_Min, vmax=cm_Max)
        else:
            normlin = self.Get_SAMECMAP_Norm(cm.shape[0], override="Lin")
            normlog = self.Get_SAMECMAP_Norm(cm.shape[0], override="Log")
            
        if log == False:
            im1 = self.PlotCM(cm+1e-16, cm_err, None, ax1, origin='lower',cmap=cmap_A,norm=normlin, thumb=True)
            f.colorbar(im1, ax=ax1, extend="both")
        else:
            im1 = self.PlotCM(cm+1e-16, cm_err, None, ax1, origin='lower',cmap=cmap_A, norm=normlog, thumb=True)
            f.colorbar(im1, ax=ax1, extend="both")

        #cax1 = f.add_axes([ax1.get_position().x1+0.01,ax1.get_position().y0,0.02,ax1.get_position().height])
        plt.tight_layout()
        return (ax1)

    def plot_comparesexes_contact_matrix(self, bin_type, contact_type, which="NCM"):
        """
        Function to plot difference in contact matrices between men and women for bin_type, contact_type.

        Parameters
        ----------
            binType:
                Name of bin type syoa, AC etc
            contact_type:
                Location of contacts
            which:
                str, which matrix type to collect "NCM", "NCM_R", "CM_T"
            
        Returns
        -------
            (ax1,ax2):
                matplotlib axes objects (Linear and Log)
        """
        plt.rcParams["figure.figsize"] = (15,5)
        f, (ax1,ax2) = plt.subplots(1,2)
        f.patch.set_facecolor('white')

        labels = self.CMPlots_GetLabels(self.age_bins[bin_type])

        cm_M, _ = self.CMPlots_GetCM(bin_type, contact_type, "male", which)
        cm_F, _ = self.CMPlots_GetCM(bin_type, contact_type, "female", which)
        cm = cm_M - cm_F    


        cm, cm_err, labels = self.CMPlots_UsefulCM(bin_type, cm, None, labels)

        cm_Min = -1e-1
        cm_Max = 1e-1

        if self.SameCMAP == False:
            normlin=colors.Normalize(vmin=cm_Max,vmax=cm_Max)
            normlog = colors.SymLogNorm(linthresh = 1, vmin=cm_Min, vmax=cm_Max)
        else:
            normlin = self.Get_SAMECMAP_Norm(cm.shape[0], override="SymLin")
            normlog = self.Get_SAMECMAP_Norm(cm.shape[0], override="SymLog")

        cm = np.nan_to_num(cm, posinf=cm_Max, neginf=0, nan=0)
        
        im1 = self.PlotCM(cm+1e-16, cm_err, labels, ax1, origin='lower',cmap=cmap_A,norm=normlin)
        im2 = self.PlotCM(cm+1e-16, cm_err, labels, ax2, origin='lower',cmap=cmap_B, norm=normlog)

        f.colorbar(im1, ax=ax1, extend="both", label="$M - F$")
        f.colorbar(im2, ax=ax2, extend="both", label="$M - F$")

        ax1.set_title("Linear Scale")
        ax2.set_title("Log Scale")
        #f.suptitle(f"Male - female {bin_type} binned contacts in {contact_type}")
        plt.tight_layout()
        return (ax1,ax2)

    def plot_stacked_contacts(self, bin_type, contact_types=None):
        """
        Plot average contacts per day in each location.

        Parameters
        ----------
            binType:
                Name of bin type syoa, AC etc
            contact_types:
                List of the contact_type locations (or none to grab all of them)
            
        Returns
        -------
            ax:
                matplotlib axes object

        """
        plt.rcParams["figure.figsize"] = (10,5)
        f, ax = plt.subplots()
        f.patch.set_facecolor('white')

        average_contacts = self.average_contacts[bin_type]
        bins = self.age_bins[bin_type]
        lower = np.zeros(len(bins)-1)

        mids = 0.5*(bins[:-1]+bins[1:])
        widths = (bins[1:]-bins[:-1])
        plotted = 0

        if contact_types is None:
            contact_types = self.contact_types

        for ii, contact_type in enumerate(contact_types):
            if contact_type in ["shelter_intra", "shelter_inter"]:
                continue
            if contact_type not in average_contacts.columns:
                print(f"No contact_type {contact_type}")
                continue
            if contact_type == "global":
                ax.plot(mids, average_contacts[contact_type] , linestyle="-", color="black", label="Total")
                continue


            if plotted > len(plt.rcParams['axes.prop_cycle'].by_key()["color"])-1:
                hatch='//'
            else:
                hatch=None
        
            heights = average_contacts[contact_type] 
            ax.bar(
                mids, heights, widths, bottom=lower, hatch=hatch, label=contact_type, edgecolor="black",linewidth=0
            )
            plotted += 1

            lower = lower + heights

        ax.set_xlim(bins[0], bins[-1])

        ax.legend(bbox_to_anchor = (0.5,1.02),loc='lower center',ncol=3)
        ax.set_xlabel('Age')
        ax.set_ylabel('average contacts per day')
        f.subplots_adjust(top=0.70)
        plt.tight_layout()
        return ax 

    def plot_population_at_locs(self, locations, max_days=7):
        """
        Plot total population of each location for each timestep.

        Parameters
        ----------
            locations:
                list of locations to plot for
            max_days:
                The maximum number of days to plot over

        Returns
        -------
            ax:
                matplotlib axes object

        """
        df = pd.DataFrame()
        df = self.location_counters_day["loc"][locations]["unisex"]
        NVenues = df.shape[1]
        df["t"] = np.array(self.location_counters_day["Timestamp"])
        df["day"] = [day.day_name() for day in df["t"]]
        Weekday_Names = self.day_types["weekday"]

        df = df[df["day"] == Weekday_Names[0]]
        Cols = df.columns[~df.columns.isin(["t", "day"])]
        df = df[Cols].iloc[0]

        
        df_weekeday_att = np.array(df.values)
       

        NVenues_Per = sum(df_weekeday_att > 0)/NVenues
        NVenues = sum(df_weekeday_att > 0)

        
            
        Interval = datetime.timedelta(days=max_days)

        xs = self.location_counters["Timestamp"]
        max_index = None
        if xs.iloc[-1] - xs.iloc[0] > Interval:
            max_index = np.sum(xs < xs.iloc[0]+Interval)
        xs = xs[:max_index]

        widths = [datetime.timedelta(hours=w) for w in self.location_counters["delta_t"][:max_index]]

        plt.rcParams["figure.figsize"] = (10,5)
        f, (ax1,ax2) = plt.subplots(1,2)
        f.patch.set_facecolor('white')

        plural_locations = Tracker.pluralise(self, locations)
        Nlocals = self.NVenues[plural_locations]

        ymax = -1
        i_counts = 0

        #ax1.set_title("%s locations (frac:%.2f)" % (NVenues, NVenues_Per))
        for i in self.location_counters["loc"][locations]["unisex"][Cols].keys():
            if Nlocals > 100:
                Nlocals = 100

            if np.sum(self.location_counters["loc"][locations]["unisex"][Cols][i].values) == 0:
                continue


            ys = self.location_counters["loc"][locations]["unisex"][Cols][i].iloc[:max_index]
            if np.nanmax(ys) > ymax:
                ymax = np.nanmax(ys)

            
            ax1.bar(xs, ys, width=widths, align="edge", color="b", alpha=1/Nlocals)

            if i_counts == 0:
                Total = np.array(ys)
            else:
                Total += np.array(ys)

            i_counts += 1
            if i_counts >= Nlocals:
                break
                    
            
        # Define the date format
        ax1.xaxis.set_major_locator(mdates.HourLocator(byhour=[0]))
        ax1.xaxis.set_minor_locator(mdates.HourLocator(byhour=None, interval=1))
        ax1.xaxis.set_major_formatter(DateFormatter("%d/%m"))
        ax1.set_ylabel("Number of people at venue")
        ax1.set_xlabel("time")
        ax1.set_yscale("log")
        ax1.set_ylim([1, ymax])
        


        df = pd.DataFrame()
        df = self.location_counters_day["loc"][locations]["unisex"]
        df["t"] = np.array(self.location_counters_day["Timestamp"])
        Cols = df.columns[~df.columns.isin(["t", "day"])]

        if df[Cols].shape[1] == 0:
            Max_attendance = 20
        else:    
            Max_attendance = max(df[Cols].max())

        Steps = 1
        if Max_attendance < 20:
            Steps = 1
        elif Max_attendance < 100:
            Steps = 5
        elif Max_attendance < 1000:
            Steps = 10
        else:
            Steps = 50
        bins = np.concatenate([np.zeros(1)-0.5, np.arange(0.5,Max_attendance+Steps,Steps)])

        for day_i in range(df.shape[0]):
            hist, bin_edges = np.histogram(df[Cols].iloc[day_i].values, bins=bins, density=False)
            ax2.bar(x=(bin_edges[1:]+bin_edges[:-1])/2, height=(100*hist)/len(self.location_counters["loc"][locations]), width=(bin_edges[:-1]-bin_edges[1:]),alpha=1/df.shape[0], color="b")

        ax2.set_ylim([0, None])
        ax2.set_ylabel(r"% of venue type")
        ax2.set_xlabel(r"People per day")

        plt.tight_layout()
        return (ax1,ax2)

    def plot_population_at_locs_variations(self, locations):
        """
        Plot variations of median values of attendence across all venues of each type

        Parameters
        ----------
            locations:
                list of locations to plot for
        Returns
        -------
            ax:
                matplotlib axes object

        """
        #Get variations between days
        Weekday_Names = self.day_types["weekday"]
        Weekend_Names = self.day_types["weekend"]

        #
        
        df = pd.DataFrame()
        df = self.location_counters_day["loc"][locations]["unisex"]
        df["t"] = pd.to_datetime(self.location_counters_day["Timestamp"].values)
        df["day"] = [day.day_name() for day in df["t"]]
         
        means = np.zeros(len(DaysOfWeek_Names))
        stds = np.zeros(len(DaysOfWeek_Names))
        medians = np.zeros(len(DaysOfWeek_Names))
        for day_i in range(len(DaysOfWeek_Names)):
            day = DaysOfWeek_Names[day_i]
            
            data = df[df["day"] == day][df.columns[~df.columns.isin(["t", "day"])]].values.flatten()
            data = data[data>1]

            if len(data) == 0:
                continue
            means[day_i] = np.nanmean(data)
            stds[day_i] = np.nanstd(data, ddof=1)
            medians[day_i] = np.nanmedian(data)
        
        plt.rcParams["figure.figsize"] = (15,5)
        f, (ax1,ax2) = plt.subplots(1,2)
        f.patch.set_facecolor('white')
        ax1.bar(np.arange(len(DaysOfWeek_Names)), means, alpha=0.4, color="b", label="mean")
        ax1.bar(np.arange(len(DaysOfWeek_Names)),medians, alpha=0.4, color="g", label="median")
        ax1.errorbar(np.arange(len(DaysOfWeek_Names)),means, [stds, stds], color="black", label="std errorbar")
        ax1.set_xticklabels([""]+DaysOfWeek_Names)
        ax1.set_ylabel("Unique Attendees per day")
        ax1.set_xlabel("Day of week")
        ax1.set_ylim([0, None])
        ax1.legend()

        #Get variations between days and time of day
        df = pd.DataFrame()
        df = self.location_counters["loc"][locations]["unisex"]
        df["t"] = pd.to_datetime(self.location_counters["Timestamp"].values, format='%d/%m/%y %H:%M:%S')
        df["dt"] = np.array(self.location_counters["delta_t"],dtype=float)
        df["day"] = [day.day_name() for day in df["t"]]

        available_days = np.unique(df["day"].values)
        dts = {}
        times = {}
        timesmid = {}

        for day_i in range(len(DaysOfWeek_Names)):
            day = DaysOfWeek_Names[day_i]
            data = df[df["day"] == day]

            dts[day] = []
            times[day] = [df["t"].iloc[0]]
            timesmid[day] = []

            for i in range(len(data["dt"].values)):

                dts[day].append(df["dt"].values[i])
                timesmid[day].append(times[day][-1]+datetime.timedelta(hours=dts[day][-1])/2)
                times[day].append(times[day][-1]+datetime.timedelta(hours=dts[day][-1]))
                if sum(dts[day]) >=24:
                    break

            dts[day] = np.array(dts[day])
            times[day] = np.array(times[day])
            timesmid[day] = np.array(timesmid[day])

        medians_days = {}
        means_days = {}
        stds_days = {}

        

        ymax = -1e3
        ymin = 1e3
        for day_i in range(len(DaysOfWeek_Names)):
            day = DaysOfWeek_Names[day_i]
            if day not in available_days:
                continue
            data = df[df["day"] == day][df.columns[~df.columns.isin(["day"])]]
            total_persons = data[data.columns[~data.columns.isin(["dt", "t"])]].sum(axis=0).values
            total_persons = total_persons[total_persons>0]

            

            medians_days[day] = []
            means_days[day] = []
            stds_days[day] = []
            for time_i in range(len(dts[day])):
                data_dt = data[data.columns[~data.columns.isin(["dt", "t"])]].values[time_i]
                data_dt = data_dt[data_dt>1]
                if len(data_dt) == 0:
                    medians_days[day].append(0)
                    means_days[day].append(0)
                    stds_days[day].append(0)
                else:
                    medians_days[day].append(np.nanmedian(data_dt))
                    means_days[day].append(np.nanmean(data_dt))
                    stds_days[day].append(np.nanstd(data_dt, ddof=1))


            if ymax < np.nanmax(means_days[day]):
                ymax = np.nanmax(means_days[day])     
            if ymin > np.nanmin(means_days[day]):
                ymin = np.nanmin(means_days[day])


        xlim = [times[Weekday_Names[0]][0], times[Weekday_Names[0]][-1]]
        for day_i in range(len(DaysOfWeek_Names)):
            day = DaysOfWeek_Names[day_i]
            if day not in available_days:
                continue
            timesmid[day] = np.insert(timesmid[day], 0, timesmid[day][-1]-datetime.timedelta(days=1), axis=0)
            timesmid[day] = np.insert(timesmid[day], len(timesmid[day]), timesmid[day][1]+datetime.timedelta(days=1), axis=0)
            medians_days[day] = np.insert(medians_days[day], 0, medians_days[day][-1], axis=0) 
            medians_days[day] = np.insert(medians_days[day], len(medians_days[day]), medians_days[day][1], axis=0) 
            means_days[day] = np.insert(means_days[day], 0, means_days[day][-1], axis=0) 
            means_days[day] = np.insert(means_days[day], len(means_days[day]), means_days[day][1], axis=0) 

        for day_i in range(len(DaysOfWeek_Names)):
            day = DaysOfWeek_Names[day_i]
            if day not in available_days:
                continue
            if day in Weekend_Names:
                linestyle="--"
            else:
                linestyle="-"
            #ax2.plot(timesmid[day], medians_days[day], label=DaysOfWeek_Names[day_i], linestyle=linestyle)
            ax2.plot(timesmid[day], means_days[day], label=DaysOfWeek_Names[day_i], linestyle=linestyle)
            
            
        alphas = [0.1,0.2]
        ylim = [-abs(ymin*1.1),abs(ymax*1.1)]
        for time_i in range(len(dts[Weekday_Names[0]])): 
            ax2.fill_between([times[Weekday_Names[0]][time_i], times[Weekday_Names[0]][time_i+1]],ylim[0], ylim[1], color ='g', alpha=alphas[time_i % 2])
        ax2.axhline(0, color="grey", linestyle="--")
                            
        ax2.set_ylabel("Mean Unique Attendees per timeslot")
        ax2.set_xlabel("Time of day [hour]")
        # Define the date format
        ax2.xaxis.set_major_locator(mdates.HourLocator(byhour=None, interval=1))
        ax2.xaxis.set_major_formatter(DateFormatter("%H"))
        ax2.set_xlim(xlim)
        ax2.set_ylim(ylim)
        ax2.legend()
        plt.tight_layout()
        return (ax1, ax2)


    def plot_AgeProfileRatios(self, contact_type="global", bin_type="syoa", sex="unisex"):
        """
        Plot demographic counts for each location and ratio of counts in age bins.

        Parameters
        ----------
            contact_types:
                List of the contact_type locations (or none to grab all of them)
            binType:
                Name of bin type syoa, AC etc
            sex:
                Which sex of population ["male", "female", "unisex"]


        Returns
        -------
            ax:
                matplotlib axes object

        """

        if bin_type != "Interaction":
            pop_tots = self.location_cum_pop[bin_type][contact_type][sex]
            global_age_profile = self.age_profiles[bin_type]["global"][sex]
            Bins = np.array(self.age_bins[bin_type])

            Labels = self.CMPlots_GetLabels(Bins)
            Bincenters = 0.5*(Bins[1:]+Bins[:-1])
            Bindiffs = np.abs(Bins[1:]-Bins[:-1])
        else:
            Bins = np.array(self.IM[contact_type]["bins"])
            AgeDiscrete = self.IM[contact_type]["type"]
            if AgeDiscrete == "Age":
                pop_tots = self.location_cum_pop[bin_type][contact_type][sex]
                

                contacts_loc = self.contacts_df[self.contacts_df[contact_type] != 0]
                AgesCount = contacts_loc.groupby([Bins], dropna = False).size()
                AgesCount = AgesCount.reindex(len(Bins), fill_value=0)
                global_age_profile = self.age_profiles[bin_type]["global"][sex]


                Labels = self.CMPlots_GetLabels(Bins)
                Bincenters = 0.5*(Bins[1:]+Bins[:-1])
                Bindiffs = np.abs(Bins[1:]-Bins[:-1])

            if AgeDiscrete == "Discrete":
                Labels = Bins
                pass
                
        Height_G = global_age_profile/Bindiffs
        Height_P = pop_tots/Bindiffs

        ws_G = np.zeros((Bins.shape[0]-1,Bins.shape[0]-1))
        ws_P = np.zeros((Bins.shape[0]-1,Bins.shape[0]-1))
        #Loop over elements
        for i in range(ws_G.shape[0]):
            for j in range(ws_G.shape[1]):
                #Population rescaling
                ws_G[i,j] = Height_G[i] / Height_G[j]
                ws_P[i,j] = Height_P[i] / Height_P[j]

        plt.rcParams["figure.figsize"] = (15,5)
        f, (ax1,ax2) = plt.subplots(1,2)
        
        f.patch.set_facecolor('white')

        vmax_G = np.nan
        vmax_P = np.nan
        if np.isfinite(ws_G).sum() != 0:
            vmax_G = ws_G[np.isfinite(ws_G)].max()*2
        if np.isfinite(ws_P).sum() != 0:
            vmax_P = ws_P[np.isfinite(ws_P)].max()*2

        vmax = np.nanmax([vmax_G, vmax_P])
        if np.isnan(vmax) or vmax == None:
            vmax= 1e-1

        vmin = 10**(-1*np.log10(vmax))
        ax1_ins = ax1.inset_axes([0.8,1.0,0.2,0.2])


        norm = colors.LogNorm(vmin=vmin, vmax=vmax)
        im_P = self.PlotCM(ws_P, None, Labels, ax1, origin='lower',cmap=cmap_B,norm=norm)
        im_G = self.PlotCM(ws_G, None, Labels, ax1_ins, origin='lower',cmap=cmap_B,norm=norm)
            
        f.colorbar(im_P, ax=ax1, label=r"$\dfrac{Age_{y}}{Age_{x}}$", extend="both")
        plt.bar(x=Bincenters, height=Height_G/sum(Height_G), width=Bindiffs, tick_label=Labels, alpha=0.5, color="blue", label="Ground truth")
        plt.bar(x=Bincenters, height=Height_P/sum(Height_P), width=Bindiffs, tick_label=Labels, alpha=0.5, color="red", label=contact_type+" tracker")
        ax2.set_xlabel("Age")
        ax2.set_ylabel("Normed Population size")
        ax2.set_xlim([Bins[0], Bins[-1]])
        ax2.set_yscale("log")
        plt.xticks(rotation=90)
        #f.suptitle(f"Age profile of {contact_type}")
        plt.legend()
        return (ax1,ax2)

    def plot_DistanceTraveled(self, location, day):
        """
        Plot histogram of commuting distances from home

        Parameters
        ----------
            location:
                The venue to look at
            day:
                The day of the week

        Returns
        -------
            ax:
                matplotlib axes object

        """
        plural_locations = Tracker.pluralise(self, location)
        Nlocals = self.NVenues[plural_locations]
        dat = self.travel_distance[location]
        Total = dat.iloc[:,1].sum()

        #Truncate plot on relvent bins.
        CumSum = np.cumsum(dat.iloc[:,1].values)
        indexlast = len(CumSum) - np.sum(CumSum == CumSum[-1])
        maxkm = dat.iloc[indexlast,0]+3.5*(dat.iloc[1,0]-dat.iloc[0,0])

        plt.rcParams["figure.figsize"] = (10,5)
        f, ax = plt.subplots(1,1)
        f.patch.set_facecolor('white')
        ax.bar(x=dat["bins"], height=(100*dat.iloc[:,1])/Total, width=(dat["bins"].iloc[1]-dat["bins"].iloc[0]), color="b", alpha=0.4)
        #ax.set_title(f"{Nlocals} available {location}")
        ax.set_ylabel(r"Frequency [%]")
        ax.set_xlabel(r"Travel distance from shelter [km]")
        ax.set_xlim([0, maxkm])
        return ax

#####################################################################################################################################################################
                                ################################### Master plotter ##################################
#####################################################################################################################################################################
    
    def make_plots(self, 
        plot_BBC = False,
        plot_thumbprints = False,
        SameCMAP=False,

        plot_INPUTOUTPUT=True,
        plot_AvContactsLocation=True, 
        plot_dTLocationPopulation=True, 
        plot_InteractionMatrices=True,
        plot_ContactMatrices=True, 
        plot_CompareSexMatrices=True,
        plot_AgeBinning=True,
        plot_Distances=True):
        """
        Make plots.

        Parameters
        ----------
            plot_BBC:
                bool, if we want to compare to BBC Pandemic data.
            plot_thumbprints:
                bool, To plot thumbnail style plots for plot_ContactMatrices and plot_CompareSexMatrices
            SameCMAP:
                bool, To plot same colour map accross all similar dimension contact matrices
            plot_INPUTOUTPUT:
                bool,
            plot_AvContactsLocation:
                bool, To plot average contacts per location plots
            plot_dTLocationPopulation:
                bool, To plot average people per location at timestamp
            plot_InteractionMatrices:
                bool, To plot interaction matrices
            plot_ContactMatrices:
                bool, To plot contact matrices
            plot_CompareSexMatrices:
                bool, To plot comparison of sexes matrices
            plot_AgeBinning:
                bool, To plot w weight matrix to compare demographics
            plot_Distances:
                bool, To plot the distance traveled from shelter to locations
        Returns
        -------
            None
        """

        logger.info(f"Rank {mpi_rank} -- Begin plotting")
        if self.group_type_names == []:
            return 1
    
        self.SameCMAP = SameCMAP


        relevant_bin_types = self.CM_T.keys()
        relevant_bin_types_short = ["syoa", "AC"]
        relevant_contact_types = self.CM_T["syoa"].keys()
        IM_contact_types = self.CM_T["Interaction"].keys()
        CMTypes = ["NCM", "NCM_R", "CM_T"]
        #CMTypes = ["CM_T"]

        if plot_INPUTOUTPUT:
            plot_dir_1 = self.record_path / "Graphs" / f"Contact_Matrices_INOUT_{self.Tracker_Contact_Type}"
            plot_dir_1.mkdir(exist_ok=True, parents=True)
            if "Paper" in relevant_bin_types:
                rbt = "Paper"
            else:
                rbt = "syoa"
            for rct in self.IM.keys():
                if rct not in relevant_contact_types:
                    continue

                plot_BBC_Sheet = False
                if plot_BBC == True and rct in ["household", "school", "company"] and rbt == "Paper":
                    if rct == "household":
                        plot_BBC_Sheet = "all_home"
                    if rct == "school":
                        plot_BBC_Sheet = "all_school"
                    if rct == "company":
                        plot_BBC_Sheet = "all_work"



                self.plot_contact_matrix_INOUT(
                    bin_type=rbt, contact_type=rct, sex="unisex", which="NCM_R",
                    plot_BBC_Sheet=plot_BBC_Sheet,
                )
                plt.savefig(plot_dir_1 / f"{rct}.pdf", dpi=150, bbox_inches='tight')
                plt.close() 
        logger.info(f"Rank {mpi_rank} -- Input vs output done")


        if plot_AvContactsLocation:
            plot_dir = self.record_path / "Graphs" / "Average_Contacts" 
            plot_dir.mkdir(exist_ok=True, parents=True)
            for rbt in relevant_bin_types_short:  
                stacked_contacts_plot = self.plot_stacked_contacts(
                    bin_type=rbt, contact_types=relevant_contact_types
                )
                stacked_contacts_plot.plot()
                plt.savefig(plot_dir / f"{rbt}_contacts.pdf", dpi=150, bbox_inches='tight')
                plt.close()
        logger.info(f"Rank {mpi_rank} -- Av contacts done")
            
            
        if plot_dTLocationPopulation:
            plot_dir = self.record_path / "Graphs" / "Location_Pops" 
            plot_dir.mkdir(exist_ok=True, parents=True)
            for locations in self.location_counters["loc"].keys():
                self.plot_population_at_locs_variations(locations)
                plt.savefig(plot_dir / f"{locations}_Variations.pdf", dpi=150, bbox_inches='tight')
                plt.close()

                self.plot_population_at_locs(locations)
                plt.savefig(plot_dir / f"{locations}.pdf", dpi=150, bbox_inches='tight')
                plt.close()
        logger.info(f"Rank {mpi_rank} -- Pop at locations done")

        if plot_InteractionMatrices:
            plot_dir = self.record_path / "Graphs" / f"IM_{self.Tracker_Contact_Type}" 
            plot_dir.mkdir(exist_ok=True, parents=True)
            for rct in self.IM.keys():
                self.plot_interaction_matrix(
                    contact_type=rct
                )
                plt.savefig(plot_dir / f"{rct}.pdf", dpi=150, bbox_inches='tight')
                plt.close()
        logger.info(f"Rank {mpi_rank} -- Interaction matrix plots done")

        if plot_ContactMatrices:
            for CMType in CMTypes:
                plot_dir_1 = self.record_path / "Graphs" / "Contact_Matrices" / self.Tracker_Contact_Type / CMType
                plot_dir_1.mkdir(exist_ok=True, parents=True)

                for rbt in relevant_bin_types:
                    

                    plot_dir_2 = plot_dir_1 / f"{rbt}"
                    plot_dir_2.mkdir(exist_ok=True, parents=True)

                    if rbt != "Interaction":
                        for sex in self.contact_sexes:
                            plot_dir_3 = plot_dir_2 / f"{sex}"
                            plot_dir_3.mkdir(exist_ok=True, parents=True)

                            for rct in relevant_contact_types:
                                self.plot_contact_matrix(
                                    bin_type=rbt, contact_type=rct, sex=sex, which=CMType
                                )
                                plt.savefig(plot_dir_3 / f"{rct}.pdf", dpi=150, bbox_inches='tight')
                                plt.close()

                                if plot_thumbprints:
                                    self.plot_contact_matrix_thumb(
                                        log=False, bin_type=rbt, contact_type=rct, sex=sex, which=CMType
                                    )
                                    plt.savefig(plot_dir_3 / f"{rct}_thumbnail.pdf", dpi=100, bbox_inches='tight')
                                    plt.close()

                                    self.plot_contact_matrix_thumb(
                                        log=True, bin_type=rbt, contact_type=rct, sex=sex, which=CMType
                                    )
                                    plt.savefig(plot_dir_3 / f"{rct}_thumbnail_log.pdf", dpi=100, bbox_inches='tight')
                                    plt.close()
                    else:
                        for rct in IM_contact_types:
                            self.plot_contact_matrix(
                                bin_type=rbt, contact_type=rct, sex=sex, which=CMType
                            )
                            plt.savefig(plot_dir_2 / f"{rct}.pdf", dpi=150, bbox_inches='tight')
                            plt.close()

                            if plot_thumbprints:
                                self.plot_contact_matrix_thumb(
                                    log=False, bin_type=rbt, contact_type=rct, sex=sex, which=CMType
                                )
                                plt.savefig(plot_dir_2 / f"{rct}_thumbnail.pdf", dpi=100, bbox_inches='tight')
                                plt.close()

                                self.plot_contact_matrix_thumb(
                                    log=True, bin_type=rbt, contact_type=rct, sex=sex, which=CMType
                                )
                                plt.savefig(plot_dir_2 / f"{rct}_thumbnail_log.pdf", dpi=100, bbox_inches='tight')
                                plt.close()
        logger.info(f"Rank {mpi_rank} -- CM plots done")


        if plot_CompareSexMatrices:
            for CMType in CMTypes:
                plot_dir_1 = self.record_path / "Graphs" / "Contact_Matrices" / self.Tracker_Contact_Type /  CMType
                plot_dir_1.mkdir(exist_ok=True, parents=True)

                for rbt in relevant_bin_types:
                    if rbt == "Interaction":
                        continue

                    plot_dir_2 = plot_dir_1 / f"{rbt}"
                    plot_dir_2.mkdir(exist_ok=True, parents=True)

                    for rct in relevant_contact_types:
                        if "male" in self.contact_sexes and "female" in self.contact_sexes:
                            plot_dir_3 = plot_dir_2 / "CompareSexes"
                            plot_dir_3.mkdir(exist_ok=True, parents=True)

                            self.plot_comparesexes_contact_matrix(
                                bin_type=rbt, contact_type=rct, which=CMType
                                )
                            plt.savefig(plot_dir_3 / f"{rct}.pdf", dpi=150, bbox_inches='tight')
                            plt.close() 
        logger.info(f"Rank {mpi_rank} -- CM between sexes done")

        if plot_AgeBinning:
            plot_dir = self.record_path / "Graphs" / "Age_Binning"
            plot_dir.mkdir(exist_ok=True, parents=True)
            for rbt in ["syoa", "Paper"]:
                if rbt not in self.age_bins.keys():
                    continue
                for rct in relevant_contact_types:
                    self.plot_AgeProfileRatios(
                        contact_type = rct, bin_type=rbt, sex="unisex"
                    )
                    plt.savefig(plot_dir / f"{rbt}_{rct}.pdf", dpi=150, bbox_inches='tight')
                    plt.close() 
        logger.info(f"Rank {mpi_rank} -- Age bin matrix done")

        if plot_Distances:
            plot_dir = self.record_path / "Graphs" / "Distance_Traveled" 
            plot_dir.mkdir(exist_ok=True, parents=True)
            for locations in self.location_counters["loc"].keys():
                for day in self.travel_distance.keys():
                    self.plot_DistanceTraveled(locations, day)
                    plt.savefig(plot_dir / f"{locations}.pdf", dpi=150, bbox_inches='tight')
                    plt.close()
                    break
        logger.info(f"Rank {mpi_rank} -- Distance plots done")
        return 1
