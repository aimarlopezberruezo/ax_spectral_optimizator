#hardware/TSP01/TSP01.py
import os
import logging
from .tsp01_config import tsp01
from .data_processor import *
from config.experiment_settings import wait_time

logger= logging.getLogger(__name__)

class TSP01Controller:
    """
    Controller class for Thorlabs TSP01 environmental monitoring device.

    Provides high-level interface for:
    - Device initialization and configuration
    - Continuous temperature/humidity monitoring
    - Data logging with precise timing
    - Stabilized temperature detection and recording

    Args:
        config (object): Configuration object with required attributes:
            - TEMP_FILE_TXT: Main data log file path
            - STAB_TEMP: Directory for trial-specific stabilized temps
            - STAB_TEMP_TXT: Master stabilized temperatures log file

    Attributes:
        tsp01: Hardware device instance
        general_file (str): Path to primary data log
        stab_temp_dir (str): Directory for trial-specific stabilized temps  
        general_stab_file (str): Master stabilized temp log path
        stabilized_temperatures (list): Historical stabilized readings
        current_trial (int/str): Active trial identifier
        wait_time (int): Stabilization monitoring duration (seconds)

    Raises:
        RuntimeError: If device initialization fails
        FileNotFoundError: For invalid log file paths
    """
    def __init__(self, config):
        """Initializes TSP01 controller and verifies file structure.

        Creates required directories and validates device communication.
        Sets up data logging infrastructure based on configuration.

        Args:
            config: See class docstring for required attributes

        Note:
            Automatically creates STAB_TEMP directory if nonexistent
            Uses module-level wait_time from experiment_settings
        """
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
        """Writes standardized measurement header to specified file.

        Delegates to data_processor.write_header() with controller's device instance.

        Args:
            file (str): Target file path for header

        See Also:
            data_processor.write_header() for implementation details
        """
        write_header(self.tsp01, file)
    
    def save_stabilized_temp_indi(self, temp):
        """Records stabilized temperature to trial-specific file.

        Args:
            temp (float): Validated stabilized temperature

        Creates:
            File named 'Trial_[X]_Stab_Temp.txt' in STAB_TEMP directory

        Note:
            Also appends to internal stabilized_temperatures list
        """
        save_stabilized_temp_indi(self.stab_temp_dir, self.current_trial, temp)
        self.stabilized_temperatures.append(temp)

    def save_stabilized_temp_general(self, temp):
        """Appends stabilized temperature to master log file.

        Args:
            temp (float): Validated stabilized temperature

        Appends line in format:
            'Stabilized Temperature of Trial [X] is Temp: [value]'
        """
        save_stabilized_temp_general(self.general_stab_file, self.current_trial, temp)

    def monitor_and_save_stabilized_temp(self, trial_number):
        """Executes full stabilization monitoring cycle.

        Args:
            trial_number (int/str): Identifier for current experiment trial

        Returns:
            float: Stabilized temperature in °C, or None if monitoring failed

        Workflow:
            1. Monitors for wait_time seconds (10s sampling interval)
            2. Validates final reading
            3. Records to both individual and master logs
            4. Updates internal state

        Note:
            Sets self.current_trial during execution
        """
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
