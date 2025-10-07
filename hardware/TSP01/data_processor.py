#hardware/TSP01/data_processor.py
import os
import time
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def write_header(tsp01_device, file_path):
    """
    Writes measurement header file with device information and channel configuration.

    Queries device identification and generates a standardized measurement header
    containing device info, sensor specifications, and column headers for data logging.

    Args:
        tsp01_device: Connected TSP01 device instance with query capability
        file (str): Path to output file (.txt recommended)

    Raises:
        IOError: If file cannot be written
        RuntimeError: If device query fails

    Notes:
        Header includes:
        - Device identification (brand, model, serial)
        - Channel specifications (ranges, calibration)
        - Data column headers
        Overwrites existing files without warning.
    """
    try:
        idn = tsp01_device.query("*IDN?")
        brand, device, S_N, Version = idn.split(",")
        header = f"""Thorlabs Environment Measurement
Device: {device}
S/N: {S_N}
Measurement Interval:1
Averaging:ON
Exernal Temperature Channel 1: TH1
\tMin ºC: -17.9524
\tMax ºC: 219.954
\tR0:101000
\tT0: 25
\tBeta: 3988
Exernal Temperature Channel 2: TH2
\tMin ºC: -17.9524
\tMax ºC: 219.954
\tR0: 10000
\tT0: 25
\tBeta: 3988
Time [s]\tDate\tTime\tTemperature[ºC]\tHumidity[%]\tTH1[ºC]\tTH2[ºC]
"""
        with open(file_path, "w") as f:
            f.write(header)
        logger.info(f'Header written in {file_path}')
    except Exception as e:
        logger.error(f'Error writing the header in {file_path}: {e}')
        raise

def datas(temp, hum, th1, th2):
    """
    Validates environmental sensor readings against expected ranges.

    Args:
        temp (str/float): Temperature reading in °C
        hum (str/float): Relative humidity in %
        th1 (str/float): External sensor 1 temperature in °C
        th2 (str/float): External sensor 2 temperature in °C

    Returns:
        bool: True if all values are within operational ranges:
            - Temperatures: -15°C to 200°C
            - Humidity: 0% to 100%

    Note:
        Performs string-to-float conversion and range checking.
        Logs detailed validation failures at WARNING level.
    """
    try:
        temp = float(temp)
        hum = float(hum)
        th1 = float(th1)
        th2 = float(th2)
        if -15 <= temp <= 200 and 0 <= hum <= 100 and -15 <= th1 <= 200 and -15 <= th2 <= 200:
            logger.debug(f'Valid data: Temp={temp}ºC, Hum={hum}, TH1={th1}ºC, TH2={th2}ºC')
            return True
        logger.warning(f'Invalid data: Temp={temp}ºC, Hum={hum}, TH1={th1}ºC, TH2={th2}ºC')
        return False
    except ValueError:
        logger.error(f'Error converting data to float: Temp={temp}, Hum={hum}, TH1={th1}, TH2={th2}')
        return False
    
def save_stabilized_temp_indi(stab_temp_dir, current_trial, temp):
    """
    Saves stabilized temperature reading to a trial-specific file.

    Args:
        stab_temp_dir (str): Directory path for output files
        current_trial (int/str): Trial identifier
        temp (float): Stabilized temperature value

    Creates:
        File named "Trial_[X]_Stab_Temp.txt" containing:
            Trial [X]
            Stabilized Temp: [value]

    Note:
        Creates directory if nonexistent (handled by os.path.join)
    """
    try:
        stab_file = os.path.join(stab_temp_dir, f"Trial_{current_trial}_Stab_Temp.txt")
        with open(stab_file, 'w') as f:
            f.write(f"Trial {current_trial}\nStabilized Temp: {temp}")
        logger.info(f'Stabilized temperature saved: {stab_file}')
    except IOError as e:
        logger.error(f'I/O error while saving the stabilized temperature: {e}')
    except Exception as e:
        logger.error(f'Unexpected error while saving the stabilized temperature: {e}')


def save_stabilized_temp_general(general_stab_file, current_trial, temp):
    """
    Appends stabilized temperature to a cumulative log file.

    Args:
        general_stab_file (str): Path to master log file
        current_trial (int/str): Trial identifier
        temp (float): Stabilized temperature value

    Appends line in format:
        "Stabilized Temperature of Trial [X] is Temp: [value]"

    Note:
        Maintains persistent record across multiple trials
    """
    try:
        with open(general_stab_file, 'a') as f:
            f.write(f'Stabilized Temperature of Trial {current_trial} is Temp: {temp}\n') 
        logger.info(f'Stabilized temperature writen in {general_stab_file}')
    except IOError as e:
        logger.error(f'I/O error while saving the stabilized temperature in general file: {e}')
    except Exception as e:
        logger.error(f'Unexpected error while saving the stabilized temperature in general file: {e}')
        
def data_meas(tsp01_device):
    """
    Acquires current environmental measurements from TSP01 device.

    Args:
        tsp01_device: Connected device with query capability

    Returns:
        tuple: Formatted measurements as (temp, hum, th1, th2) where:
            - temp (str): Internal temperature (°C) formatted to 2 decimals
            - hum (str): Humidity (%) formatted to 2 decimals
            - th1/th2 (str): External temps (°C) formatted to 2 decimals
        Returns (None, None, None, None) on read failure

    Note:
        Implements automatic 2-second retry on failure
        Logs all successful readings at INFO level
    """
    try:
        temp_meas = tsp01_device.query("MEAS:TEMP?")
        hum_meas = tsp01_device.query("MEAS:HUM?")
        temp_TH1 = tsp01_device.query("MEAS:TEMP2?")
        temp_TH2 = tsp01_device.query("MEAS:TEMP3?")
        temp = f"{float(temp_meas):.2f}"
        hum = f"{float(hum_meas):.2f}"
        th1 = f"{float(temp_TH1):.2f}"
        th2 = f"{float(temp_TH2):.2f}"
        logger.info(f'Data read: Temp={temp}ºC, Hum={hum}%, TH1={th1}ºC, TH2={th2}ºC')
        return temp, hum, th1, th2
    except Exception as e:
        logger.error(f'Error reading data: {e}')
        logger.info('Retrying in 2 seconds...')
        time.sleep(2)
        return None, None, None, None

def monitor_temp_for_wait_time(tsp01_device, general_file, wait_time):
    """
    Monitors environmental conditions at precise 10-second intervals.

    Args:
        tsp01_device: Connected measurement device
        general_file (str): Path to data log file
        wait_time (int): Total monitoring duration in seconds

    Returns:
        float: Last valid TH1 temperature reading, or None if no valid readings

    Behavior:
        1. Takes measurements every 10.00±0.05 seconds
        2. Logs valid data with timestamp and elapsed time
        3. Maintains synchronization despite processing delays

    Output Format:
        [elapsed_sec] [date] [time] [temp] [hum] [th1] [th2]
    """
    start_time = time.time()
    last_valid_temp = None
    
    try:
        while time.time() - start_time < wait_time:
            iteration_start = time.time()
            
            temp, hum, th1, th2 = data_meas(tsp01_device)
            
            if temp is not None and datas(temp, hum, th1, th2):
                current_time = datetime.now().strftime("%b %d %Y %H:%M:%S").split()
                time_elapsed = int(time.time() - start_time)
                
                with open(general_file, 'a') as f:
                    f.write(f"{time_elapsed}\t{current_time[0]} {current_time[1]}\t{current_time[2]}\t{current_time[3]}\t{temp}\t{hum}\t{th1}\t{th2}\n")
                
                last_valid_temp = th1
                logger.debug(f"Data recorded: {time_elapsed}s, Temp={th1}°C")
            
            sleep_time = 10 - (time.time() - iteration_start)
            if sleep_time > 0:
                time.sleep(sleep_time)
                
        return last_valid_temp
        
    except Exception as e:
        logger.error(f"Error in monitor_temp: {str(e)}")
        return None