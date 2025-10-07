#hardware/TSP01/TSP01.py
import os
import logging
from .tsp01_config import tsp01
from .data_processor import *
from config.experiment_settings import wait_time

logger= logging.getLogger(__name__)

class TSP01Controller:
    def __init__(self, config):
        try:
            self.tsp01 = tsp01
            self.general_file = config.TEMP_FILE_TXT
            self.stab_temp_dir = config.STAB_TEMP
            self.general_stab_file = config.STAB_TEMP_TXT
            self.stabilized_temperatures = []
            self.current_trial = None
            self.wait_time = wait_time

            os.makedirs(self.stab_temp_dir, exist_ok=True)
            logger.info('TSP01 initialized successfully')
        except Exception as e:
            logger.error('Error initializing TSP01: %s', e)
            raise


    def write_header(self, file):
        write_header(self.tsp01, file)
    
    def save_stabilized_temp_indi(self, temp):
        save_stabilized_temp_indi(self.stab_temp_dir, self.current_trial, temp)
        self.stabilized_temperatures.append(temp)

    def save_stabilized_temp_general(self, temp):
        save_stabilized_temp_general(self.general_stab_file, self.current_trial, temp)

    def monitor_and_save_stabilized_temp(self, trial_number):
        try:            
            logger.info('Monitoring temperature')
            stabilized_temp = monitor_temp_for_wait_time(
                self.tsp01,
                self.general_file,
                self.wait_time
            )
            stabilized_temp=float(stabilized_temp)
            
            if stabilized_temp:
                save_stabilized_temp_indi(self.stab_temp_dir, trial_number, stabilized_temp)
                save_stabilized_temp_general(self.general_stab_file, trial_number, stabilized_temp)
                logger.info(f"Stabilized temperature saved: {stabilized_temp}°C")
            
            logger.info('Stopped monitoring')
            return stabilized_temp
            
        except Exception as e:
            logger.error(f"Error while monitoring and saving temperature: {str(e)}")
            return None
