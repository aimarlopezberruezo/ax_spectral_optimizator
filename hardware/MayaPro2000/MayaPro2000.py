#hardware/mayapro2000/mayapro2000.py
import json
from .spec_config import *
from .data_processor import *


class MayaPro2000Controller:

    def __init__(self):

        try:
            self.spec = spec
            self.time_micros = time_micros
            print("MayaPro2000 initialized successfully.")
        except Exception as e:
            print(f'ERROR: Error initializing the spectrometer: {e}')
            raise

    def set_integration_time(self):

        try:
            self.spec.integration_time_micros(self.time_micros)
            print(f'Integration time set to {self.time_micros} microseconds.')
        except AttributeError:
            print("ERROR: The method 'integration_time_micros' is not available in the 'spec' object.")
        except Exception as e:
            print(f'ERROR: Error setting the integration time: {e}')

    def acquire_spectrum(self):
        return acquire_spectrum(self.spec)
    
    def save_spectrum_to_json(self, wavelengths, intensities, filepath):
        save_spectrum_to_json(wavelengths, intensities, filepath)