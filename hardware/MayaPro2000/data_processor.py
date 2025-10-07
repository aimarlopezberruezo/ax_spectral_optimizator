#hardware/MayaPro2000/data_processor.py
import logging
import json

logger = logging.getLogger(__name__)


def acquire_spectrum(spec):
    """
    Acquires spectral data (wavelengths and intensities) from a spectrometer device.

    Retrieves synchronized wavelength-intensity pairs from the connected spectrometer.
    Handles common device communication errors and logs detailed failure reasons.

    Args:
        spec: Spectrometer device object with required methods:
            - wavelengths(): Returns array of wavelength values (nm)
            - intensities(): Returns array of corresponding intensity values

    Returns:
        tuple: 
            - wavelengths (array): Array of wavelength values in nanometers.
            - intensities (array): Array of corresponding intensity measurements.
        Returns (None, None) on failure.

    Raises:
        AttributeError: If spectrometer lacks required methods (logged as error).
        RuntimeError: For device communication failures (logged as error).

    Example:
        >>> wavelengths, intensities = acquire_spectrum(spectrometer)
        >>> print(wavelengths[:5])
        [400.0, 400.5, 401.0, 401.5, 402.0]
    """
    try:
        wavelengths = spec.wavelengths()
        intensities = spec.intensities()
        logger.info('Spectrum acquired successfully.')
        return wavelengths, intensities
    except AttributeError:
        logger.error("The methods 'wavelengths' or 'intensities' are not available in the 'spec' object.")
        return None, None
    except Exception as e:
        logger.error(f'Error acquiring the spectrum: {e}')
        return None, None

def save_spectrum_to_json(wavelengths, intensities, filepath):
    """
    Saves spectral data to a JSON file in standardized format.

    Converts wavelength-intensity pairs to JSON-compatible format and writes to disk.
    Performs data validation and handles filesystem errors gracefully.

    Args:
        wavelengths (array-like): Sequence of wavelength values (nm).
        intensities (array-like): Sequence of corresponding intensity values.
        filepath (str): Destination path for JSON file (.json extension recommended).

    Raises:
        TypeError: If input data cannot be converted to float (logged as error).
        IOError: For filesystem access problems (logged as error).
        ValueError: If wavelength/intensity arrays have mismatched lengths.

    Notes:
        - Output JSON structure:
            [{"wavelengths": 400.0, "value": 1500.2}, ...]
        - Overwrites existing files without warning.
        - Uses 4-space JSON indentation for human readability.

    Example:
        >>> save_spectrum_to_json(wl_array, int_array, "spectrum.json")
        Spectrum saved at spectrum.json
    """
    try:
        # Transforming the spectrum into JSON
        spec_json = [
            {"wavelengths": float(wl), "value": float(intensity)}
            for wl,intensity in zip(wavelengths, intensities)
        ]

        # Saving the JSON
        with open (filepath, "w") as archivo_json:
            json.dump(spec_json, archivo_json, indent=4)
        logger.info(f'Spectrum saved at {filepath}')
    except TypeError as e:
        logger.error(f'Type error in spectrum data: {e}')
    except IOError as e:
        logger.error(f'I/O error while saving the JSON file: {e}')
    except Exception as e:
        logger.error(f'Error saving the spectrum in JSON: {e}')