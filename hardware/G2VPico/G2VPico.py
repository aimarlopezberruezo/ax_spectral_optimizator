#hardware/G2VPico/GVPico.py
from g2vpico import G2VPico
from .pico_config import *
from .data_processor import *
import logging
import json

logger = logging.getLogger(__name__)

class G2VPicoController:

    def __init__(self):

        logger.info('Initializing G2VPico controller...')
        try:
            self.pico = G2VPico(PICO_IP_ADDRESS, PICO_ID)
            logger.info(f'Connected to G2VPico (ID: {PICO_ID}, IP: {PICO_IP_ADDRESS})')
        except ConnectionError as e:
            logger.critical(f'Connection failed: {str(e)}')
            raise
        except Exception as e:
            logger.error(f'Unexpected initialization error: {str(e)}')
            raise
        self.global_intensity = global_intensity

    def clear_channels(self):

        logger.debug('Initiating channel clearance...')
        try:
            self.pico.clear_channels()
            logger.info('All channels cleared successfully')
        except Exception as e:
            logger.error(f'Channel clearance failed: {str(e)}')
            raise

    def turn_off(self):

        logger.debug('Turning off ...')
        try:
            self.pico.turn_off()
            logger.info('G2VPico successfully turned off.')
        except Exception as e:
            logger.error(f'Error turning off G2VPico: {str(e)}.')
            raise

    def turn_on(self):

        logger.info('Turning on G2VPico...')
        try:
            self.pico.turn_on()
            logger.info("G2VPico successfully turned on.")
        except Exception as e:
            logger.error(f'Error turning on G2VPico: {str(e)}.')
            raise

    def set_global_intensity(self, intensity):

        logger.debug(f'Requested intensity change: {intensity}%')
        
        if not 0 <= intensity <= 100:
            logger.error(f'Invalid intensity {intensity}% (0-100 allowed)')
            raise ValueError("Intensity out of bounds")
        try:
            self.pico.set_global_intensity(intensity)
            logger.info(f'Intensity set to {intensity}%')
        except ValueError as e:
            logger.warning(f'Value rejected: {str(e)}')
            raise

    def set_spectrum(self, spectrum_data):

        logger.info('Spectrum configuration requested')
        
        try:
            self.pico.set_spectrum(spectrum_data)
            logger.info(f'Spectrum configured: {len(spectrum_data)} channels')
        except Exception as e:
            logger.error(f'Configuration error: {str(e)}')
            raise

    def configure_from_txt(self, file_path):

        logger.info(f'Loading configuration from: {file_path}')

        try:
            json_data, trial_number = txt_to_json(file_path)
            if not all([json_data, trial_number]):
                logger.warning(f'Incomplete processing of {file_path}')
                return None, None
            logger.debug(f'Trial #{trial_number} config loaded')
            self.set_spectrum(json_data)
            return json_data, trial_number
        except Exception as e:
            logger.error(f'Configuration failed: {str(e)}')
            raise
    
    def channel_list(self):

        logger.info('Getting channel list...')
        return self.pico.channel_list
    
    def set_channel_limit(self, channel):

        logger.info('Getting each channel limits...')
        try:
            lim=self.pico.get_channel_limit(channel)
            logger.info(f'Channel limit correctly founded: {lim}')
            return lim
        except Exception as e:
            logger.error(f'Error getting the limits: {str(e)}')

    def write_channel_limits(self, file_path):

        try:
            channel_list=self.channel_list()
            logger.info(f"Retrieved channel list: {channel_list}")

            for channel in channel_list:
                try:
                    limit = self.set_channel_limit(channel)
                    logger.info(f"Set limit for channel {channel}: {limit}")
                    limit_json(channel, limit, file_path)
                    logger.info(f"Saved limit in JSON format for channel {channel}")
                except Exception as e:
                    logging.error(f"Error setting limit or saving JSON for channel {channel}: {e}")
        except Exception as e:
            logging.error("Error retrieving channel list: %s", e)

