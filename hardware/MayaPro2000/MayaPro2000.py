#hardware/mayapro2000/mayapro2000.py
import json
from .spec_config import *
from .data_processor import *
import logging

logger = logging.getLogger(__name__)

class MayaPro2000Controller:
    """
    Controller class for managing the MayaPro2000 spectrometer.

    Provides high-level interface for spectrometer configuration, data acquisition,
    and spectrum storage. Handles device initialization, integration time settings,
    and spectrum data persistence.

    Attributes:
        spec: Spectrometer hardware interface instance
        time_micros (int): Current integration time setting in microseconds

    Raises:
        RuntimeError: If spectrometer initialization fails
        AttributeError: For unsupported spectrometer operations

    Example:
        >>> controller = MayaPro2000Controller()
        >>> controller.set_integration_time()
        >>> wavelengths, intensities = controller.acquire_spectrum()
        >>> controller.save_spectrum_to_json(wavelengths, intensities, "spectrum.json")
    """
    def __init__(self):
        """
        Initializes the spectrometer connection and configuration.

        Loads device settings from module-level configuration (spec_config.py).
        Establishes communication with the spectrometer hardware.

        Raises:
            RuntimeError: If spectrometer initialization fails
            ConnectionError: If hardware communication cannot be established

        Note:
            Requires pre-configured 'spec' and 'time_micros' in spec_config.py
        """
        try:
            self.spec = spec
            self.time_micros = time_micros
            logger.info("MayaPro2000 initialized successfully.")
        except Exception as e:
            logger.error(f'Error initializing the spectrometer: {e}')
            raise

    def set_integration_time(self):
        """
        Configures the spectrometer's integration time.

        Applies the time_micros setting to the spectrometer hardware.
        Validates successful configuration through hardware feedback.

        Raises:
            AttributeError: If spectrometer lacks integration_time_micros method
            ValueError: If time_micros is outside valid hardware range
            RuntimeError: For device communication failures

        Note:
            Integration time must be set before spectrum acquisition
        """
        try:
            self.spec.integration_time_micros(self.time_micros)
            logger.info(f'Integration time set to {self.time_micros} microseconds.')
        except AttributeError:
            logger.error("The method 'integration_time_micros' is not available in the 'spec' object.")
        except Exception as e:
            logger.error(f'Error setting the integration time: {e}')

    def acquire_spectrum(self):
        """
        Captures a full spectrum measurement from the device.

        Returns:
            tuple: 
                - wavelengths (array): Array of wavelength values in nanometers
                - intensities (array): Corresponding intensity measurements
            Returns (None, None) on failure

        Raises:
            RuntimeError: For acquisition hardware failures
            AttributeError: If required spectrometer methods are missing

        Note:
            Requires prior integration time configuration for accurate results
        """
        return acquire_spectrum(self.spec)
    
    def save_spectrum_to_json(self, wavelengths, intensities, filepath):
        """
        Persists spectrum data to a JSON file.

        Args:
            wavelengths (array): Wavelength values in nanometers
            intensities (array): Corresponding intensity measurements
            filepath (str): Destination file path (.json extension recommended)

        Raises:
            IOError: For filesystem access problems
            TypeError: If data cannot be serialized to JSON
            ValueError: If input arrays have mismatched lengths

        Note:
            Overwrites existing files without warning
            Uses 4-space JSON indentation for readability
        """
        save_spectrum_to_json(wavelengths, intensities, filepath)