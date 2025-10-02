#hardware/MayaPro2000/data_processor.py
import json



def acquire_spectrum(spec):
    try:
        wavelengths = spec.wavelengths()
        intensities = spec.intensities()
        print('Spectrum acquired successfully.')
        return wavelengths, intensities
    except AttributeError:
        print("ERROR: The methods 'wavelengths' or 'intensities' are not available in the 'spec' object.")
        return None, None
    except Exception as e:
        print(f'ERROR: Error acquiring the spectrum: {e}')
        return None, None

def save_spectrum_to_json(wavelengths, intensities, filepath):
    try:
        # Transforming the spectrum into JSON
        spec_json = [
            {"wavelengths": float(wl), "value": float(intensity)}
            for wl,intensity in zip(wavelengths, intensities)
        ]

        # Saving the JSON
        with open (filepath, "w") as archivo_json:
            json.dump(spec_json, archivo_json, indent=4)
        print(f'Spectrum saved at {filepath}')
    except TypeError as e:
        print(f'ERROR: Type error in spectrum data: {e}')
    except IOError as e:
        print(f'ERROR: I/O error while saving the JSON file: {e}')
    except Exception as e:
        print(f'ERROR: Error saving the spectrum in JSON: {e}')