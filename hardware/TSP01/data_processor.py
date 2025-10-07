#hardware/TSP01/data_processor.py
import os
import time
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def write_header(tsp01_device, file_path):
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
    try:
        with open(general_stab_file, 'a') as f:
            f.write(f'Stabilized Temperature of Trial {current_trial} is Temp: {temp}\n') 
        logger.info(f'Stabilized temperature writen in {general_stab_file}')
    except IOError as e:
        logger.error(f'I/O error while saving the stabilized temperature in general file: {e}')
    except Exception as e:
        logger.error(f'Unexpected error while saving the stabilized temperature in general file: {e}')
        
def data_meas(tsp01_device):
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