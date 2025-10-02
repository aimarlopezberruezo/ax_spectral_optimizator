#hardware/mayapro2000/mayapro2000.py
import json
from .spec_config import *
from .data_processor import *
import logging

logger = logging.getLogger(__name__)

class MayaPro2000Controller:

    def __init__(self):

        try:
            self.spec = spec
            self.time_micros = time_micros
            logger.info("MayaPro2000 initialized successfully.")
        except Exception as e:
            logger.error(f'Error initializing the spectrometer: {e}')
            raise

    def set_integration_time(self):

        try:
            self.spec.integration_time_micros(self.time_micros)
            logger.info(f'Integration time set to {self.time_micros} microseconds.')
        except AttributeError:
            logger.error("The method 'integration_time_micros' is not available in the 'spec' object.")
        except Exception as e:
            logger.error(f'Error setting the integration time: {e}')

    def acquire_spectrum(self):
        return acquire_spectrum(self.spec)
    
    def save_spectrum_to_json(self, wavelengths, intensities, filepath):
        save_spectrum_to_json(wavelengths, intensities, filepath)