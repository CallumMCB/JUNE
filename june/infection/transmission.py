import autofit as af
import yaml
import numpy as np
from scipy.stats import gamma
import sys
from typing import Optional

from june.infection.trajectory_maker import CompletionTime
from june.infection.symptom_tag import SymptomTag
from june import paths

default_config_path = (
    paths.configs_path / "defaults/transmission/TransmissionConstant.yaml"
)
default_gamma_config_path = paths.configs_path / "defaults/transmission/nature.yaml"


class Transmission:
    def __init__(self):
        self.probability = 0.0

    def update_probability_from_delta_time(self, time_from_infection):
        raise NotImplementedError()

    @classmethod
    def object_from_config(cls):
        """
        Loads the default Transmission class from the general.ini config file and 
        returns the class as object (not as an instance). This is used to set up the 
        epidemiology model in world.py via configs if an input is not provided.
        """
        classname_str = af.conf.instance.general.get(
            "epidemiology", "transmission_class", str
        )
        return getattr(sys.modules[__name__], classname_str)


class TransmissionConstant(Transmission):
    def __init__(self, probability=0.3):
        super().__init__()
        self.probability = probability

    @classmethod
    def from_file(
        cls, config_path: str = default_config_path
    ) -> "TransmissionConstant":
        with open(config_path) as f:
            config = yaml.safe_load(f)
        probability = CompletionTime.from_dict(config["probability"])()
        return TransmissionConstant(probability=probability)

    def update_probability_from_delta_time(self, time_from_infection):
        pass


class TransmissionGamma(Transmission):
    """
    Module to simulate the infectiousness profiles found in :
        - https://www.nature.com/articles/s41591-020-0869-5
        - https://arxiv.org/pdf/2007.06602.pdf
    """
    def __init__(
        self,
        max_infectiousness: float=1.0,
        shape: float =2.0,
        rate: float =3.0,
        shift: float =-2.0,
        max_symptoms: Optional["SymptomTag"] =None,
        asymptomatic_infectious_factor: Optional[float]=None,
        mild_infectious_factor: Optional[float] =None,
    ):
        '''
        Parameters
        ----------
        max_infectiousness:
            value of the infectiousness at its peak
        shape:
            shape parameter of the gamma distribution (a for scipy stats)
        rate:
            rate parameter of the gamma distribution (1/rate = scale for scipy stats)
        shift:
            location parameter of the gamma distribution
        max_symptoms:
            maximum symptoms the individual will develop, used to reduce the infectiousness
            of asymptomatic and mild individuals if wanted
        asymptomatic_infectious_factor:
            factor to reduce the infectiousness of asymptomatic individuals
        mild_infectious_factor:
            factor to reduce the infectiousness of mild individuals
        '''
        self.max_infectiousness = max_infectiousness
        self.shape = shape
        self.rate = rate
        self.shift = shift
        self.scale = 1.0 / self.rate
        time_at_max = (self.shape - 1) * self.scale + self.shift
        self.gamma = gamma(a=self.shape, scale=self.scale, loc=self.shift)
        self.norm = self.max_infectiousness / self.gamma.pdf(time_at_max)
        self.asymptomatic_infectious_factor = asymptomatic_infectious_factor
        self.mild_infectious_factor = mild_infectious_factor
        if (
            asymptomatic_infectious_factor is not None
            and mild_infectious_factor is not None
        ):
            self.modify_infectiousness_for_symptoms(max_symptoms=max_symptoms)
        self.probability = 0.0

    @classmethod
    def from_file(
        cls,
        max_symptoms: "SymptomTag" = None,
        config_path: str = default_gamma_config_path,
    ) -> "TransmissionGamma":
        """
        Generate transmission class reading parameters from config file

        Parameters
        ----------
        max_symptoms:
            maximum symptoms the individual will develop, used to reduce the infectiousness
            of asymptomatic and mild individuals if wanted
        config_path:
            path to config parameters

        Returns
        -------
            TransmissionGamma instance

        """
        with open(config_path) as f:
            config = yaml.safe_load(f)
        max_infectiousness = CompletionTime.from_dict(config["max_infectiousness"])()
        shape = CompletionTime.from_dict(config["shape"])()
        rate = CompletionTime.from_dict(config["rate"])()
        shift = CompletionTime.from_dict(config["shift"])()
        asymptomatic_infectious_factor = CompletionTime.from_dict(
            config["asymptomatic_infectious_factor"]
        )()
        mild_infectious_factor = CompletionTime.from_dict(
            config["mild_infectious_factor"]
        )()

        return cls(
            max_infectiousness=max_infectiousness,
            shape=shape,
            rate=rate,
            shift=shift,
            max_symptoms=max_symptoms,
            asymptomatic_infectious_factor=asymptomatic_infectious_factor,
            mild_infectious_factor=mild_infectious_factor,
        )

    @classmethod
    def from_file_linked_symptoms(
        cls,
        time_to_symptoms_onset: float,
        max_symptoms: "SymptomTag" = None,
        config_path: str = default_gamma_config_path,
    ) -> "TransmissionGamma":
        """
        Generate transmission class reading parameters from config file, linked to
        the time of symptoms onset

        Parameters
        ----------
        time_to_symptoms_onset:
            time (from infection) at which the person becomes symptomatic
        max_symptoms:
            maximum symptoms the individual will develop, used to reduce the infectiousness
            of asymptomatic and mild individuals if wanted
        config_path:
            path to config parameters

        Returns
        -------
            TransmissionGamma instance

        """

        with open(config_path) as f:
            config = yaml.safe_load(f)
        max_infectiousness = CompletionTime.from_dict(config["max_infectiousness"])()
        shape = CompletionTime.from_dict(config["shape"])()
        rate = CompletionTime.from_dict(config["rate"])()
        shift = CompletionTime.from_dict(config["shift"])() + time_to_symptoms_onset
        asymptomatic_infectious_factor = CompletionTime.from_dict(
            config["asymptomatic_infectious_factor"]
        )()
        mild_infectious_factor = CompletionTime.from_dict(
            config["mild_infectious_factor"]
        )()

        return cls(
            max_infectiousness=max_infectiousness,
            shape=shape,
            rate=rate,
            shift=shift,
            max_symptoms=max_symptoms,
            asymptomatic_infectious_factor=asymptomatic_infectious_factor,
            mild_infectious_factor=mild_infectious_factor,
        )

    def modify_infectiousness_for_symptoms(self, max_symptoms: "SymptomTag"):
        """
        Lowers the infectiousness of asymptomatic and mild cases, by modifying
        self.norm

        Parameters
        ----------
        max_symptoms:
            maximum symptom severity the person will ever have

        """
        if (
            self.asymptomatic_infectious_factor is not None
            and max_symptoms == SymptomTag.asymptomatic
        ):
            self.norm *= self.asymptomatic_infectious_factor
        elif (
            self.mild_infectious_factor is not None and max_symptoms == SymptomTag.mild
        ):
            self.norm *= self.mild_infectious_factor

    def update_probability_from_delta_time(self, time_from_infection: float):
        """
        Performs a probability update given time from infection

        Parameters
        ----------
        time_from_infection:
            time elapsed since person became infected
        """
        self.probability = self.norm * self.gamma.pdf(time_from_infection)
