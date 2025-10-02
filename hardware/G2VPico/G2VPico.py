#hardware/G2VPico/GVPico.py
from g2vpico import G2VPico
from .pico_config import *
from .data_processor import *
import json


class G2VPicoController:
    
    def __init__(self):

        print('Initializing G2VPico controller...')
        try:
            self.pico = G2VPico(PICO_IP_ADDRESS, PICO_ID)
            print(f'Connected to G2VPico (ID: {PICO_ID}, IP: {PICO_IP_ADDRESS})')
        except ConnectionError as e:
            print(f'CRITICAL: Connection failed: {str(e)}')
            raise
        except Exception as e:
            print(f'ERROR: Unexpected initialization error: {str(e)}')
            raise
        self.global_intensity = global_intensity

    def clear_channels(self):

        print('DEBUG: Initiating channel clearance...')
        try:
            self.pico.clear_channels()
            print('All channels cleared successfully')
        except Exception as e:
            print(f'ERROR: Channel clearance failed: {str(e)}')
            raise

    def turn_off(self):

        print('DEBUG: Turning off ...')
        try:
            self.pico.turn_off()
            print('G2VPico successfully turned off.')
        except Exception as e:
            print(f'ERROR: Error turning off G2VPico: {str(e)}.')
            raise

    def turn_on(self):

        print('Turning on G2VPico...')
        try:
            self.pico.turn_on()
            print("G2VPico successfully turned on.")
        except Exception as e:
            print(f'ERROR: Error turning on G2VPico: {str(e)}.')
            raise

    def set_global_intensity(self, intensity):
        
        print(f'DEBUG: Requested intensity change: {intensity}%')
        
        if not 0 <= intensity <= 100:
            print(f'ERROR: Invalid intensity {intensity}% (0-100 allowed)')
            raise ValueError("Intensity out of bounds")
        try:
            self.pico.set_global_intensity(intensity)
            print(f'Intensity set to {intensity}%')
        except ValueError as e:
            print(f'WARNING: Value rejected: {str(e)}')
            raise

    def set_spectrum(self, spectrum_data):
        
        print('Spectrum configuration requested')
        
        try:
            self.pico.set_spectrum(spectrum_data)
            print(f'Spectrum configured: {len(spectrum_data)} channels')
        except Exception as e:
            print(f'ERROR: Configuration error: {str(e)}')
            raise

    def configure_from_txt(self, file_path):

        print(f'Loading configuration from: {file_path}')

        try:
            json_data, trial_number = txt_to_json(file_path)
            if not all([json_data, trial_number]):
                print(f'WARNING: Incomplete processing of {file_path}')
                return None, None
            print(f'DEBUG: Trial #{trial_number} config loaded')
            self.set_spectrum(json_data)
            return json_data, trial_number
        except Exception as e:
            print(f'ERROR: Configuration failed: {str(e)}')
            raise
    
    def channel_list(self):
        print('Getting channel list...')
        return self.pico.channel_list
    
    def set_channel_limit(self, channel):
        print('Getting each channel limits...')
        try:
            lim=self.pico.get_channel_limit(channel)
            print(f'Channel limit correctly founded: {lim}')
            return lim
        except Exception as e:
            print(f'ERROR: Error getting the limits: {str(e)}')

    def write_channel_limits(self, file_path):

        try:
            channel_list=self.channel_list()
            print(f"Retrieved channel list: {channel_list}")

            for channel in channel_list:
                try:
                    limit = self.set_channel_limit(channel)
                    print(f"Set limit for channel {channel}: {limit}")
                    limit_json(channel, limit, file_path)
                    print(f"Saved limit in JSON format for channel {channel}")
                except Exception as e:
                    print(f"ERROR: Error setting limit or saving JSON for channel {channel}: {e}")
        except Exception as e:
            print("ERROR: Error retrieving channel list: %s", e)

