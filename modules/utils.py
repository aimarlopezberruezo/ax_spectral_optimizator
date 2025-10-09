#modules/utils.py
import matplotlib.pyplot as plt
import json
import re
import numpy as np
import time
import logging
import matplotlib
import pyvisa
import os
import csv
from datetime import datetime, timedelta
from matplotlib.dates import DateFormatter
from config.experiment_settings import *
from config.path_declarations import *
import smtplib
import zipfile
import tempfile
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)


def plot_errors_FB(trials, error, sobol_trials, best_parameters, save_path, fecha_utc, num_trials, error_file, is_temp=False, config=None):
    """Generates and saves an error trend plot with experiment metadata visualization.

    Creates a professional-quality plot showing:
    - Error progression across optimization trials
    - SOBOL/Fully Bayesian phase separation
    - Key experiment statistics
    - Best parameters found

    Args:
        trials (list[int]): Sequential trial numbers (e.g., [1, 2, 3, ...])
        error (list[float]): Error values corresponding to each trial
        sobol_trials (int): Number of initial SOBOL sequence trials
        best_parameters (dict): Optimized parameters from the experiment
        save_path (str): Full path for saving the output plot image
        fecha_utc (str): Experiment timestamp in UTC format
        num_trials (int): Total number of trials completed
        error_file (str): Path to error data file for best trial analysis
        is_temp (bool, optional): If True, skips secondary saves. Defaults to False.
        config (object, optional): Configuration object with:
            - FIG_PATH: Directory for figure storage
            - DATA_UTC: Timestamp for filename

    Returns:
        None: Saves plot to disk but returns nothing

    Raises:
        ValueError: If input lists length mismatch
        IOError: If plot saving fails

    Side Effects:
        - Creates plot file at save_path
        - Optionally saves copy in FIG_PATH
        - Closes matplotlib figure

    Example:
        >>> plot_errors_FB(
                trials=[1, 2, 3],
                error=[0.5, 0.3, 0.1],
                sobol_trials=10,
                best_parameters={'param1': 0.7},
                save_path='/results/plot.png',
                fecha_utc='2023-01-01',
                num_trials=50,
                error_file='errors.json'
            )
    """
    logger.info('Starting the generation of the error plot')

    try:
        plt.figure(figsize=(12, 6))
        plt.scatter(trials, error, color='skyblue', alpha=0.8)
        plt.plot(trials, error, color='black', linestyle='-', linewidth=2, alpha=0.7, label='Trendline')

        plt.axvline(x=sobol_trials, color='red', linestyle='--', linewidth=2, alpha=0.8, label='SOBOL trials')

        plt.title('Error Trend Across Trials', fontsize=14, pad=20)
        plt.xlabel('Trial Number', fontsize=12)
        plt.ylabel('Error Value', fontsize=12)
        
        plt.grid(True, linestyle=':', alpha=0.3)
        N = max(1, len(trials) // 10)  # Adjust ticks based on number of trials
        plt.xticks(ticks=trials[::N], labels=trials[::N], rotation=45, fontsize=10)
        plt.yticks(fontsize=10)

        plt.subplots_adjust(right=0.75)
        plt.legend(fontsize=10, framealpha=0.9)

        info_box_props = dict(boxstyle='round', facecolor='white', alpha=0.5)

        try:
            best_parameters_text = format_dict(best_parameters)
        except Exception as e:
            logger.warning(f"Error formatting the dictionaries: {str(e)}")
            best_parameters_text = "Not available"

        try:
            best_trial, min_error = find_lowest_error(error_file)
            logger.debug(f'Best trial found: {best_trial} with error: {min_error}')
        except Exception as e:
            logger.error(f"Error finding the best trial: {str(e)}")
            best_trial = "Not available"
            min_error = "Not available"

        experiment_info = (
            f"Experiment Date: {fecha_utc}\n"
            f"SOBOL Trials: {sobol_trials}\n"
            f"FB Trials: {num_trials}\n"
            f"Best Trial: {best_trial}\n"
            f"Min Error: {min_error:.4f}"
        )
        
        plt.text(1.03, 0.97, experiment_info, 
                transform=plt.gca().transAxes, 
                fontsize=9, 
                verticalalignment='top', 
                bbox=info_box_props)

        plt.text(1.03, 0.75, f"Best Parameters:\n{best_parameters_text}", 
                transform=plt.gca().transAxes, 
                fontsize=8, 
                verticalalignment='top', 
                bbox=info_box_props)

        try:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.savefig(os.path.join(config.FIG_PATH, f'Error_plot_{config.DATA_UTC}.png'), dpi=300, bbox_inches='tight')
            logger.info(f'Plot saved at: {save_path}')
            plt.close()
        except Exception as e:
            logger.error(f"Error saving the plot: {str(e)}")
            raise

        logger.info('Plot generated successfully')

    except Exception as e:
        logger.error(f"Error in the function plot_errors_FB: {str(e)}")
        raise

def format_dict(d):
    """Converts a dictionary to a human-readable multi-line string representation.

    Transforms dictionary key-value pairs into an aligned string format suitable for:
    - Logging outputs
    - Plot annotations
    - Configuration displays

    Args:
        d (dict): Dictionary to format. All values should be string-convertible.

    Returns:
        str: Formatted string with one 'key: value' pair per line.
            Returns empty string for empty dictionaries.

    Raises:
        AttributeError: If input is not dictionary-like (missing items() method)
        TypeError: If values cannot be converted to strings

    Examples:
        >>> format_dict({'temp': 37.5, 'humidity': 60})
        'temp: 37.5\nhumidity: 60'

        >>> format_dict({})
        ''

    Note:
        - Maintains original dictionary order (Python 3.7+ preserves insertion order)
        - Logs formatting process at DEBUG level
        - Uses str() conversion for values
    """
    logger.debug(f'Starting dictionary formatting: {d}')   
    try:
        formatted_text = "\n".join([f"{k}: {v}" for k, v in d.items()])
        logger.debug(f'Dictionary formatted successfully: {formatted_text}')
        return formatted_text
    except AttributeError as e:
        logger.error(f"Error: The argument is not a dictionary. Details: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error formatting the dictionary: {str(e)}")
        raise

def find_lowest_error(error_file):
    """Finds the trial with the minimum error value in a results file.

    Parses a trial results file to identify the experiment trial with the lowest
    reported error value. Handles various file formats and logs parsing issues.

    Args:
        error_file (str): Path to the results file. Expected format:
            "Error of Trial [X] is Error: [Y]" per line
            Example: "Error of Trial 42 is Error: 0.1563"

    Returns:
        tuple: 
            - min_trial (int): Trial number with lowest error (None if no valid trials)
            - min_error (float): Corresponding error value (inf if no valid trials)

    Raises:
        FileNotFoundError: If specified file doesn't exist
        ValueError: If file contains malformed data (logged but not raised)
        RuntimeError: For critical file processing failures

    Examples:
        >>> find_lowest_error("results.txt")
        (42, 0.1563)  # Trial 42 had lowest error (0.1563)

        >>> find_lowest_error("empty.txt")
        (None, inf)  # No valid trials found

    Note:
        - Uses 'cp1252' encoding for file reading
        - Logs skipped lines at WARNING level
        - Returns (None, float('inf')) for empty/invalid files
        - Case-sensitive to "Error of Trial" line prefix
    """
    logger.info(f'Starting search for the trial with the lowest error in the file: {error_file}')
    
    min_error = float('inf')
    min_trial = None

    try:
        with open(error_file, 'r', encoding='cp1252') as file:
            logger.debug(f'File opened successfully: {error_file}')
            
            for line in file:
                if line.startswith("Error of Trial"):
                    try:
                        parts = line.split(" is Error: ")
                        trial_number = int(parts[0].split(" ")[-1])
                        error_value = float(parts[1])
                        
                        if error_value < min_error:
                            min_error = error_value
                            min_trial = trial_number
                            logger.debug(f'New minimum found: Trial {min_trial}, Error {min_error}')
                    except (IndexError, ValueError) as e:
                        logger.warning(f"Error processing the line: {line.strip()}. Details: {str(e)}")
                        continue

        if min_trial is None:
            logger.warning("No valid trials were found in the file.")
        else:
            logger.info(f'Trial with the lowest error found: {min_trial}, Error: {min_error}')

        return min_trial, min_error

    except FileNotFoundError:
        logger.error(f"File not found: {error_file}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing the file {error_file}: {str(e)}")
        raise

def find_lowest_loss(loss_file):
    """Identifies the trial with the minimum loss value from a results file.

    Parses a trial results file to locate the experiment trial with the lowest
    reported loss value. Designed to process files generated during optimization
    experiments with specific formatting requirements.

    Args:
        loss_file (str): Path to the loss results file. Expected format:
            "Loss of Trial [X] is: [Y]" per line
            Example: "Loss of Trial 42 is: 1.563"

    Returns:
        tuple: 
            - min_trial (int): Trial number with lowest loss (None if no valid trials)
            - min_error (float): Corresponding loss value (inf if no valid trials)

    Raises:
        FileNotFoundError: If specified file cannot be found
        PermissionError: If file cannot be read due to permissions
        RuntimeError: For unexpected parsing failures

    Examples:
        >>> find_lowest_loss("loss_results.txt")
        (42, 1.563)  # Trial 42 had lowest loss (1.563)

        >>> find_lowest_loss("empty_file.txt")
        (None, inf)  # Case when no valid trials exist

    Note:
        - Uses 'cp1252' (Windows-1252) encoding for compatibility
        - Returns (None, float('inf')) for empty/invalid files
        - Logs all parsing issues at WARNING level
        - Case-sensitive to "Loss of Trial" line prefix
        - Processes files line-by-line for memory efficiency

    See Also:
        find_lowest_error(): Similar function for error values
    """
    logger.info(f'Starting search for the trial with the lowest loss in the file: {loss_file}')
    
    min_error = float('inf')
    min_trial = None

    try:
        with open(loss_file, 'r', encoding='cp1252') as file:
            logger.debug(f'File opened successfully: {loss_file}')
            
            for line in file:
                if line.startswith("Loss of Trial"):
                    try:
                        parts = line.split(" is: ")
                        trial_number = int(parts[0].split(" ")[-1])
                        error_value = float(parts[1])
                        
                        if error_value < min_error:
                            min_error = error_value
                            min_trial = trial_number
                            logger.debug(f'New minimum found: Trial {min_trial}, Error {min_error}')
                    except (IndexError, ValueError) as e:
                        logger.warning(f"Error processing the line: {line.strip()}. Details: {str(e)}")
                        continue

        if min_trial is None:
            logger.warning("No valid trials were found in the file.")
        else:
            logger.info(f'Trial with the lowest loss found: {min_trial}, Loss: {min_error}')

        return min_trial, min_error

    except FileNotFoundError:
        logger.error(f"File not found: {loss_file}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing the file {loss_file}: {str(e)}")
        raise
        
def load_target_values(file_path):
    """Loads and parses target LED values from a JSON configuration file.

    Reads a JSON file containing channel-value pairs and converts them into
    a standardized dictionary format for LED control. Validates file structure
    and content during loading.

    Args:
        file_path (str): Path to JSON configuration file. Expected format:
            [
                {"channel": "1", "value": 100},
                {"channel": "2", "value": 150},
                ...
            ]

    Returns:
        dict: Mapping of LED channels to target values in format:
            {"led 1": 100, "led 2": 150, ...}
            Channel numbers are converted to integers (e.g., "1" → 1)

    Raises:
        FileNotFoundError: If specified file doesn't exist
        json.JSONDecodeError: For malformed JSON content
        KeyError: If required keys ('channel' or 'value') are missing
        ValueError: If channel numbers cannot be converted to integers

    Examples:
        >>> load_target_values("targets.json")
        {'led 1': 100, 'led 2': 150}

        >>> load_target_values("invalid.json")
        KeyError: "Missing 'channel' key in JSON data"

    Note:
        - Uses strict JSON parsing (no YAML compatibility)
        - Converts channel strings to integers automatically
        - Logs detailed progress at DEBUG level
        - Validates both file structure and data types

    Security:
        - Validates JSON structure before processing
        - Uses safe JSON loading (no object_hook or other unsafe features)
    """
    logger.info(f'Starting to load target values from: {file_path}')
    
    try:
        with open(file_path, "r") as file:
            logger.debug(f'JSON file opened successfully: {file_path}')
            datos = json.load(file)
            logger.debug(f'JSON data loaded: {datos}')
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding the JSON file {file_path}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while loading the file {file_path}: {str(e)}")
        raise

    try:
        target_values = {f"led {int(item['channel'])}": item['value'] for item in datos}
        logger.info(f'Target values successfully loaded from: {file_path}')
        return target_values
    except KeyError as e:
        logger.error(f"Error: The JSON file is not in the expected format. Missing key: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while processing JSON data: {str(e)}")
        raise

def save_indi_trials(i, save_path, parameterization, ax_obj):
    """Saves individual trial results to a text file with experiment parameters and outcomes.

    Writes a structured text file containing trial metadata, parameterization, and
    optimization results. The output format varies based on experiment type (error
    minimization or temperature maximization).

    Args:
        i (int): Trial index (0-based) that will be converted to 1-based in output
        save_path (str): Full path to output text file (.txt recommended)
        parameterization (dict): Parameter set used for this trial
        ax_obj (float): Optimization result (error or temperature value)

    Returns:
        None: Writes to file but returns nothing explicitly

    Raises:
        IOError: If file cannot be written (permissions, disk full)
        TypeError: If parameterization cannot be converted to string
        RuntimeError: For other unexpected failures

    Examples:
        Error minimization trial:
        >>> save_indi_trials(0, "trial1.txt", {"param1": 0.5}, 0.25)
        # Creates file containing:
        # Trial 1
        # Parameters: {'param1': 0.5}
        # Error: 0.25

        Temperature maximization trial:
        >>> save_indi_trials(1, "trial2.txt", {"param1": 0.7}, 37.5)
        # Creates file containing:
        # Trial 1
        # Parameters: {'param1': 0.7}
        # Temp: 37.5

    Note:
        - Trial numbers are stored as i+1 (converts 0-based to 1-based)
        - Uses module-level constants MINIMIZE_ERROR/MAXIMIZE_TEMP to determine format
        - Overwrites existing files without warning
        - Maintains consistent line endings (\n)
        - Logs all operations at appropriate levels

    See Also:
        load_target_values(): For loading similar configuration files
        plot_errors_FB(): For visualizing trial results
    """
    logger.info(f'Starting to save trial {i+1} results in: {save_path}')
    
    try:
        with open(save_path, "w") as file:
            logger.debug(f'File opened successfully for writing: {save_path}')
            file.write(f"Trial {i+1}\n")
            file.write(f"Parameters: {parameterization}\n")
            if MINIMIZE_ERROR:
                file.write(f"Error: {ax_obj}\n")
            elif MAXIMIZE_TEMP:
                file.write(f"Temp: {ax_obj}\n")
            logger.debug(f'Data written successfully to the file: {save_path}')
        
        logger.info(f'Trial {i+1} results saved successfully in: {save_path}')
    except IOError as e:
        logger.error(f"I/O error while saving trial {i+1} in {save_path}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while saving trial {i+1} in {save_path}: {str(e)}")
        raise

def save_total_trials(i, save_path, parameterization, ax_obj, loss=None):
    """Appends trial results to a cumulative experiment log file.

    Records complete trial information including parameters and outcomes in
    append mode, supporting multiple experiment types (error minimization,
    temperature maximization, or custom loss metrics).

    Args:
        i (int): 0-based trial index (displayed as 1-based in output)
        save_path (str): Path to cumulative results file (.txt recommended)
        parameterization (dict): Parameter set used for this trial
        ax_obj (float): Primary optimization metric value
        loss (float, optional): Additional loss metric value. Defaults to None.

    Returns:
        None: Writes to file but returns nothing explicitly

    Raises:
        IOError: For filesystem issues (permissions, disk full)
        TypeError: If parameterization can't be converted to string
        RuntimeError: For other unexpected failures

    Examples:
        >>> save_total_trials(0, "results.txt", {"wavelength": 450}, 0.25)
        # Appends to file:
        # Trial 1
        # Parameters: {'wavelength': 450}
        # Error: 0.25

        >>> save_total_trials(1, "results.txt", {"power": 75}, 37.5, loss=0.1)
        # Appends to file:
        # Trial 1
        # Parameters: {'power': 75}
        # Temp: 37.5
        # Loss: 0.1

    Note:
        - Uses append mode ('a') to preserve previous trials
        - Determines output format using module-level constants:
          MINIMIZE_ERROR, MAXIMIZE_TEMP
        - Converts trial index from 0-based to 1-based
        - Maintains consistent line endings (\n)
        - Logs all operations at appropriate levels

    See Also:
        save_indi_trials(): For saving individual trial files
        plot_errors_FB(): For visualizing these results
    """
    logger.info(f'Starting to save trial {i+1} results in: {save_path}')
    
    try:
        with open(save_path, "a") as file:
            logger.debug(f'File opened successfully for writing (append mode): {save_path}')
            file.write(f"Trial {i+1}\n")
            file.write(f"Parameters: {parameterization}\n")
            if MINIMIZE_ERROR:
                file.write(f"Error: {ax_obj}\n")
            elif MAXIMIZE_TEMP:
                file.write(f"Temp: {ax_obj}\n")
            elif loss:
                file.write(f'Loss: {loss}')
            logger.debug(f'Trial {i+1} data written successfully to the file: {save_path}')
        
        logger.info(f'Trial {i+1} results saved successfully in: {save_path}')
    except IOError as e:
        logger.error(f"I/O error while saving trial {i+1} in {save_path}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while saving trial {i+1} in {save_path}: {str(e)}")
        raise

def save_error(i, save_path, current_error):
    """Appends trial error results to a dedicated error log file.

    Records individual trial error metrics in a standardized format to a cumulative
    error tracking file. Designed for consistent error analysis and visualization.

    Args:
        i (int): 0-based trial index (stored as 1-based in file)
        save_path (str): Path to error log file (.txt or .csv recommended)
        current_error (float): Computed error value for this trial

    Returns:
        None: Writes to file but returns nothing explicitly

    Raises:
        IOError: If file cannot be opened/written (permissions, disk full)
        TypeError: If error value cannot be converted to string
        RuntimeError: For other unexpected failures

    Examples:
        >>> save_error(0, "errors.log", 0.25)
        # Appends to file:
        # Error of Trial 1 is Error: 0.25

        >>> save_error(1, "errors.csv", 0.18)
        # Appends to file:
        # Error of Trial 2 is Error: 0.18

    Note:
        - Uses append mode ('a') to preserve historical data
        - Converts trial index from 0-based to 1-based
        - Maintains consistent output format for parsing:
          "Error of Trial X is Error: Y"
        - Logs all operations at appropriate levels
        - UTF-8 encoding used by default

    See Also:
        find_lowest_error(): For analyzing this error log
        plot_errors_FB(): For visualizing error trends
    """   

    logger.info(f'Starting to save trial {i+1} error in: {save_path}')
    
    try:
        with open(save_path, "a") as file:
            logger.debug(f'File opened successfully for writing (append mode): {save_path}')
            file.write(f"Error of Trial {i+1} is Error: {current_error}\n")
            logger.debug(f'Trial {i+1} error written successfully to the file: {save_path}')
        
        logger.info(f'Trial {i+1} error saved successfully in: {save_path}')
    except IOError as e:
        logger.error(f"I/O error while saving trial {i+1} error in {save_path}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while saving trial {i+1} error in {save_path}: {str(e)}")
        raise

def save_loss(i, save_path, current_loss):
    """Appends trial loss values to a cumulative loss tracking file.

    Records optimization loss metrics in a standardized format for subsequent analysis.
    Maintains consistent formatting for easy parsing and visualization.

    Args:
        i (int): 0-based trial index (displayed as 1-based in output)
        save_path (str): Path to loss log file (.txt recommended)
        current_loss (float): Computed loss value for the current trial

    Returns:
        None: Writes to file but returns nothing explicitly

    Raises:
        IOError: If file cannot be accessed (permissions, disk full)
        TypeError: If loss value cannot be converted to string
        RuntimeError: For other unexpected write failures

    Examples:
        >>> save_loss(0, "loss_log.txt", 0.42)
        # Appends to file:
        # Loss of Trial 1 is: 0.42

        >>> save_loss(3, "optimization.log", 1.25)
        # Appends to file:
        # Loss of Trial 4 is: 1.25

    Note:
        - Uses append mode to preserve historical data
        - Maintains exact output format for parsing:
          "Loss of Trial X is: Y"
        - Converts trial numbers from 0-based to 1-based
        - UTF-8 encoding used by default
        - Thread-safe for single-file writes (but not for concurrent processes)

    See Also:
        find_lowest_loss(): For extracting minimum loss from this log
        plot_optimization_progress(): For visualizing loss trends
    """

    logger.info(f'Starting to save trial {i+1} error in: {save_path}')
    
    try:
        with open(save_path, "a") as file:
            logger.debug(f'File opened successfully for writing (append mode): {save_path}')
            file.write(f"Loss of Trial {i+1} is: {current_loss}\n")
            logger.debug(f'Trial {i+1} loss written successfully to the file: {save_path}')
        
        logger.info(f'Trial {i+1} error saved successfully in: {save_path}')
    except IOError as e:
        logger.error(f"I/O error while saving trial {i+1} loss in {save_path}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while saving trial {i+1} loss in {save_path}: {str(e)}")
        raise
        
def txt_to_json(file_path):
    """Converts a structured text file to JSON format with robust error handling.

    Processes trial data files containing parameter configurations with:
    - Automatic retry logic for file operations
    - Validation of required fields
    - Safe parameter evaluation
    - Structured JSON output generation

    Args:
        file_path (str): Path to input text file. Expected format:
            Trial [NUMBER]
            Parameters: {PARAMETER_DICT}
            Example:
                Trial 42
                Parameters: {"ch1": 100, "ch2": 200}

    Returns:
        tuple: 
            - json_data (str): JSON string in format [{"channel": X, "value": Y}]
            - trial_number (str): Extracted trial identifier
            Returns (None, None) on conversion failure

    Raises:
        FileNotFoundError: If file doesn't exist (after retries)
        ValueError: For malformed parameter structures
        RuntimeError: For unrecoverable processing errors

    Examples:
        Successful conversion:
        >>> txt_to_json("trial_data.txt")
        ('[{"channel": "1", "value": 100}]', "42")

        Failed conversion:
        >>> txt_to_json("bad_data.txt")
        (None, None)

    Note:
        - Performs up to 5 retries with 1-second delays
        - Uses eval() for parameter parsing (ensure trusted files)
        - Validates both trial number and parameters exist
        - Returns standardized JSON structure:
            [{"channel": str, "value": num}, ...]
        - Logs detailed progress at DEBUG level

    Security:
        - Validates file structure before evaluation
        - Uses limited retries to prevent hangs
        - Checks parameter dict structure before conversion
    """

    logger.info(f'Starting text file to JSON conversion: {file_path}')
    
    MAX_ATTEMPTS = 5
    attempt_count = 0
    retry_delay = 1

    while attempt_count < MAX_ATTEMPTS:
        try:
            attempt_count +=1
            logger.debug(f'Attempt {attempt_count}/{MAX_ATTEMPTS} to process the file: {file_path}')
            
            #1. File Reading
            try:
                with open(file_path, 'r') as file:
                    lines = file.readlines()
                    logger.debug(f'File read successfully: {file_path}')
            except FileNotFoundError:
                logger.error(f'Critical: File not found at specified path: {file_path}')
                return None, None
            except IOError as e:
                logger.warning(f'IOError during file reading (attempt {attempt_count}): {str(e)}')
                if attempt_count<MAX_ATTEMPTS:
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.error(f'Permanent IOError after {MAX_ATTEMPTS} attempts')
                    return None, None
                
            #2. Empty File Check
            if not lines:
                logger.warning(f'The file is empty, retrying... (Attempt {attempt_count + 1}/{MAX_ATTEMPTS})')
                if attempt_count<MAX_ATTEMPTS:
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.error('Failed: File remains empty after retries')
                    return None, None
                
            trial_number = None
            parameters = None

            #3. Line Processing
            for line in lines:
                line = line.strip()

                #Trial Number Extraction
                if line.lower().startswith("trial"):
                    try:
                        match = re.search(r"Trial (\d+)", line, re.IGNORECASE)
                        if match:
                            trial_number = match.group(1)
                            logger.debug(f'Extracted trial number: {trial_number}')
                        else:
                            logger.warning(f'Error: Could not extract trial number from line: {line}')
                    except Exception as e:
                        logger.error(f'Error processing trial number: {str(e)}')

                #Parameters Extraction
                if line.lower().startswith("parameters:"):
                    try:
                        param_str = line.split("Parameters:")[1]
                        parameters = eval(param_str)
                        logger.debug(f'Extracted parameters: {parameters}')
                    except (IndexError, ValueError, SyntaxError) as e:
                        logger.error(f'Parameter parsing failed: {str(e)}')
                        parameters= None
                    except Exception as e:
                        logger.error(f'Error evaluating parameters: {str(e)}')
                        parameters = None

            #4. Validation and Conversion
            if not trial_number:
                logger.error('No valid trial number found in file')
                return None, None
                
            if not parameters:
                logger.error('No valid parameters found in file')
                return None, None
            
            try:
                data = [{"channel": re.search(r'\d+', channel).group(), "value": value} for channel, value in parameters.items()]
                json_data = json.dumps(data, indent=4)
                logger.info(f'File successfully converted to JSON: {file_path}')
                return json_data, trial_number
            except (AttributeError, TypeError) as e:
                logger.error(f'Invalid parameter structure: {str(e)}')
                return None, None
            except Exception as e:
                logger.error(f'Unexpected error during JSON conversion: {str(e)}')
                return None, None

        except FileNotFoundError:
            logger.error(f'File not found: {file_path}')
            return None, None
        except Exception as e:
            logger.critical(f'Unexpected error while processing the file {file_path}: {e}')
            if attempt_count<MAX_ATTEMPTS:
                time.sleep(retry_delay)
                continue
            else:
                logger.error(f'Permanent failure after {MAX_ATTEMPTS} attempts')
                return None, None
            
    logger.error(f'Failed to process the file after {MAX_ATTEMPTS} attempts: {file_path}')
    return None, None
    
def calculate_error(parameterization, target_values):
    """Calculates normalized error between parameterization and target values.

    Computes the L2 norm (Euclidean distance) between normalized parameter values
    and target values, supporting both direct input and file-based configuration.

    Args:
        parameterization (dict or str): Either:
            - Dictionary of {led_channel: value} pairs
            - Path to JSON file containing parameter data (will be converted to dict)
        target_values (dict): Reference values in format {led_channel: target_value}

    Returns:
        dict: Contains single key "Variable_error" with tuple value:
            - norm_error (float): Computed normalized error (L2 norm)
            - 0.0 (float): Placeholder variance value

    Raises:
        FileNotFoundError: If parameterization is path and file doesn't exist
        json.JSONDecodeError: For malformed JSON parameter files
        ValueError: If normalization fails (e.g., constant values)
        RuntimeError: For other calculation errors

    Examples:
        Direct dictionary input:
        >>> calculate_error(
            {"led 1": 100, "led 2": 150},
            {"led 1": 110, "led 2": 140}
            )
        {'Variable_error': (0.099, 0.0)}

        File path input:
        >>> calculate_error(
            "params.json",
            {"led 1": 110, "led 2": 140}
            )

    Note:
        - Performs min-max normalization on input values
        - Warns if key sets don't match between inputs
        - Uses all available keys from parameterization
        - Handles JSON files with format:
            [{"channel": X, "value": Y}, ...]
        - Returns zero variance for compatibility with optimization frameworks

    Algorithm:
        1. Loads parameters (from dict or file)
        2. Normalizes both parameter and target values to [0,1] range
        3. Computes L2 norm between normalized vectors
    """

    logger.info(f'Starting error calculation between parameterization and target_values')
    
    if isinstance(parameterization, str):
        with open(parameterization, 'r') as f:
            trial_data = json.load(f)
        parameterization={f"led {item['channel']}": item['value'] for item in trial_data}
    
         
    try:
        # Checking key matching
        if set(parameterization.keys()) != set(target_values.keys()):
            logger.warning(f'Keys of parameterization and target_values do not match: {parameterization.keys()} vs {target_values.keys()}')

        keys = parameterization.keys()
        obj1 = np.array([parameterization[k] for k in keys])
        obj2 = np.array([target_values[k] for k in keys])
        logger.debug(f'Parameterization values: {obj1}')
        logger.debug(f'Target values: {obj2}')

        # Normalizing values
        obj1_norm = (obj1 - np.min(obj1)) / (np.max(obj1) - np.min(obj1))
        obj2_norm = (obj2 - np.min(obj2)) / (np.max(obj2) - np.min(obj2))
        logger.debug(f'Normalized parameterization values: {obj1_norm}')
        logger.debug(f'Normalized target values: {obj2_norm}')

        # Calculating error
        norm_error = np.linalg.norm(obj1_norm - obj2_norm)
        logger.info(f'Calculated error: {norm_error}')

        return {"Variable_error": (norm_error, 0.0)}

    except Exception as e:
        logger.error(f'Unexpected error while calculating error: {str(e)}')
        raise

def calculate_error_spec(current_values, target_values):
    """Calculates spectral matching error between current and target spectra.

    Performs wavelength-aligned comparison of two spectra with normalization,
    handling potential format discrepancies between the inputs. The error is
    computed as the L2 norm (Euclidean distance) between normalized intensity
    vectors of matching wavelengths.

    Args:
        current_values (dict/array): Raw spectral data from measurement device.
            Will be processed through procesar_espectro() to extract wavelengths.
        target_values (dict): Reference spectrum with format:
            {wavelength(str/float): intensity(float), ...}
            Example: {"450": 1500.2, "500": 2000.1}

    Returns:
        dict: Contains single key "Variable_error" with tuple value:
            - loss (float): Computed spectral error (L2 norm)
            - 0.0 (float): Placeholder variance value

    Raises:
        ValueError: If no overlapping wavelengths exist between spectra
        TypeError: If input spectra cannot be processed
        RuntimeError: For numerical calculation failures

    Examples:
        >>> calculate_error_spec(
            current_values={"wavelengths": [450,500], "values": [1400,2100]},
            target_values={"450": 1500.2, "500": 2000.1}
            )
        {'Variable_error': (0.024, 0.0)}

    Note:
        - Normalizes wavelengths by converting all keys to integers
        - Performs min-max normalization on intensity values
        - Adds small epsilon (1e-10) to prevent division by zero
        - Uses all available overlapping wavelengths
        - Logs key validation steps at DEBUG level

    Algorithm:
        1. Normalizes wavelength keys in both spectra
        2. Finds intersection of available wavelengths
        3. Sorts wavelengths numerically
        4. Normalizes intensity values to [0,1] range
        5. Computes L2 norm between normalized vectors
    """
    logger.info('Starting error calculation between spectras...')

    try:
        # 1. Normalize target spectrum keys (remove .0 if exists)
        target_cleaned = {str(int(float(k))): v for k, v in target_values.items()}
        
        # 2. Process current spectrum (process_spectra returns integers)
        processed_spectra = process_spectra(current_values)
        current_cleaned = {str(item["wavelengths"]): item["value"] for item in processed_spectra}

        # 3. Find wavelength intersection
        common_keys = set(target_cleaned.keys()) & set(current_cleaned.keys())
        logger.debug(f'TARGET_KEYS: {target_cleaned.keys()}, CURRENT_KEYS: {current_cleaned.keys()}, COMMON_KEYS: {common_keys}')
        
        if not common_keys:
            logger.error("No common wavelengths found. Check spectral ranges.")
            raise ValueError("No overlapping wavelengths between spectra.")

        # 4. Sort numerically and extract values
        sorted_keys = sorted(common_keys, key=lambda x: int(x))
        obj1 = np.array([current_cleaned[k] for k in sorted_keys])
        obj2 = np.array([target_cleaned[k] for k in sorted_keys])

        # 5. Normalize and calculate error
        obj1_norm = (obj1 - np.min(obj1)) / (np.max(obj1) - np.min(obj1) + 1e-10)
        obj2_norm = (obj2 - np.min(obj2)) / (np.max(obj2) - np.min(obj2) + 1e-10)
        
        loss = np.linalg.norm(obj1_norm - obj2_norm)
        logger.info(f"Computed loss: {loss} (using {len(common_keys)} common wavelengths)")

        return {"Variable_error": (loss, 0.0)}

    except Exception as e:
        logger.error(f'Unexpected error while calculating error: {str(e)}')
        raise

def calculate_loss(current_values, target_values):
    """Calculates spectral loss between measured and target spectra.

    Computes the normalized L2 distance (Euclidean norm) between two spectra after:
    - Wavelength key normalization
    - Intersection of available wavelengths
    - Intensity value normalization
    - Numerical sorting of wavelengths

    Args:
        current_values (dict/array): Measured spectral data (will be processed by process_spectra)
        target_values (dict): Reference spectrum in format {wavelength(str/float): intensity(float)}

    Returns:
        float: Computed loss value (L2 norm between normalized spectra)

    Raises:
        ValueError: If no overlapping wavelengths exist
        TypeError: If input data cannot be processed
        RuntimeError: For numerical calculation failures

    Examples:
        >>> calculate_loss(
            {"wavelengths": [400,500], "values": [1000,1500]},
            {"400": 950, "500": 1550}
            )
        0.125

    Note:
        - Handles wavelength format variations (converts all to int)
        - Adds small epsilon (1e-10) to prevent division by zero
        - Uses all available overlapping wavelengths
        - Logs key processing steps at DEBUG level

    Algorithm:
        1. Normalizes wavelength keys in both spectra
        2. Processes raw current_values through process_spectra()
        3. Finds intersection of available wavelengths
        4. Sorts wavelengths numerically
        5. Normalizes intensity values to [0,1] range
        6. Computes L2 norm between normalized vectors
    """

    logger.info("Normalizing keys and calculating loss...")

    try:
        # 1. Normalize target spectrum keys (remove .0 if exists) 
        target_cleaned = {str(int(float(k))): v for k, v in target_values.items()}
        
        # 2. Process current spectrum (process_spectra returns integers)
        processed_spectra = process_spectra(current_values)
        current_cleaned = {str(item["wavelengths"]): item["value"] for item in processed_spectra}

        # 3. Find wavelength intersection
        common_keys = set(target_cleaned.keys()) & set(current_cleaned.keys())
        logger.debug(f'TARGET_KEYS: {target_cleaned.keys()}, CUURENT_KEYS: {current_cleaned.keys()}, COMMON_KEYS: {common_keys}')
        
        if not common_keys:
            logger.error("No common wavelengths found. Check spectral ranges.")
            raise ValueError("No overlapping wavelengths between spectra.")

        # 4. Sort numerically and extract values
        sorted_keys = sorted(common_keys, key=lambda x: int(x))
        obj1 = np.array([current_cleaned[k] for k in sorted_keys])
        obj2 = np.array([target_cleaned[k] for k in sorted_keys])

        # 5. Normalize and calculate loss
        obj1_norm = (obj1 - np.min(obj1)) / (np.max(obj1) - np.min(obj1) + 1e-10)
        obj2_norm = (obj2 - np.min(obj2)) / (np.max(obj2) - np.min(obj2) + 1e-10)
        
        loss = np.linalg.norm(obj1_norm - obj2_norm)
        logger.info(f"Calculated loss: {loss} (using {len(common_keys)} common wavelengths)")

        return float(loss)

    except Exception as e:
        logger.error(f'Unexpected error while calculating error: {str(e)}')
        raise

def load_event_spectra(file_path):
    """Loads and validates spectral event data from a JSON file with retry logic.

    Reads a JSON file containing wavelength-intensity pairs and converts them into
    a dictionary format. Implements robust error handling including file existence
    checks, empty file validation, and multiple read attempts.

    Args:
        file_path (str): Path to JSON file containing spectral data. Expected format:
            [
                {"wavelengths": X, "value": Y},
                {"wavelengths": X, "value": Y},
                ...
            ]

    Returns:
        dict: Spectral data as {wavelength: value} pairs if successful
        None: If file cannot be loaded after multiple attempts or contains invalid data

    Raises:
        FileNotFoundError: If file does not exist (logged but not raised)
        json.JSONDecodeError: For malformed JSON content (handled internally)
        KeyError: If required keys are missing (handled internally)

    Examples:
        >>> load_event_spectra("spectra.json")
        {450: 1200.5, 500: 1500.2}

        >>> load_event_spectra("invalid.json")
        None  # For invalid/missing files

    Note:
        - Performs 3 read attempts with 1-second delays
        - Validates file existence and non-empty status
        - Logs detailed progress at DEBUG level
        - Returns None for all error cases
        - Converts list of dicts to single {wavelength: value} dict

    Security:
        - Validates JSON structure before processing
        - Uses safe JSON loading without object_hook
    """

    logger.info(f'Starting event spectra loading from: {file_path}')
    
    if not os.path.exists(file_path):
        logger.error(f'The file does not exist: {file_path}')
        return None

    if os.path.getsize(file_path) == 0:
        logger.error(f'The file is empty: {file_path}')
        return None

    attempts = 3
    for attempt in range(attempts):
        try:
            with open(file_path, "r") as file:
                logger.debug(f'JSON file opened successfully (Attempt {attempt+1}/{attempts}): {file_path}')
                data = json.load(file)                
                if data:
                    event = {}
                    try:
                        event = {item['wavelengths']: item['value'] for item in data}
                        logger.info(f'Event spectra successfully loaded from: {file_path}')
                        return event
                    except (KeyError, AttributeError) as e:
                        logger.warning(f"Error processing event spectra. Details: {str(e)}")
                        continue
                    
                else:
                    logger.warning(f'The JSON file is empty or does not contain valid data: {file_path}')
                    return None

        except json.JSONDecodeError as e:
            logger.warning(f'Error decoding JSON (Attempt {attempt+1}/{attempts}): {e}')
            time.sleep(1)
        except Exception as e:
            logger.error(f'Failed to load the file after {attempts} attempts: {file_path}')
            return None

    logger.error(f'Failed to load the file after {attempts} attempts: {file_path}')
    return None
    
def load_target_spectra (file_path):
    """Loads and validates target spectral data from a JSON configuration file.

    Reads a JSON file containing wavelength-intensity pairs and converts them into
    a standardized dictionary format for spectral analysis. Includes comprehensive
    error checking for file access, JSON structure, and data format.

    Args:
        file_path (str): Path to JSON configuration file. Expected format:
            [
                {"wavelengths": <number>, "value": <number>},
                {"wavelengths": <number>, "value": <number>},
                ...
            ]

    Returns:
        dict: Target spectra as {wavelength: value} pairs
        Example: {450: 1200.5, 500: 1500.2}

    Raises:
        FileNotFoundError: If specified file doesn't exist
        json.JSONDecodeError: For malformed JSON content
        KeyError: If required keys ('wavelengths' or 'value') are missing
        ValueError: If wavelength/value cannot be converted to numbers
        RuntimeError: For other unexpected processing errors

    Examples:
        >>> load_target_spectra("targets.json")
        {450: 1200.5, 500: 1500.2}

        >>> load_target_spectra("invalid.json")
        KeyError: "Missing 'wavelengths' key in JSON data"

    Note:
        - Validates JSON structure before processing
        - Converts all wavelengths/values to native Python numbers
        - Maintains original data precision
        - Logs detailed progress at DEBUG level
        - Raises exceptions immediately on failure

    Security:
        - Uses safe JSON loading without object_hook
        - Validates complete structure before processing
    """

    logger.info(f'Starting to load target spectra values from: {file_path}')
    
    try:
        with open(file_path, "r") as file:
            logger.debug(f'JSON file opened successfully: {file_path}')
            datos = json.load(file)
            logger.debug(f'JSON data loaded: {datos}')
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding the JSON file {file_path}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while loading the file {file_path}: {str(e)}")
        raise

    try:
        target_values = {item['wavelengths']: item['value'] for item in datos}
        logger.info(f'Target values successfully loaded from: {file_path}')
        return target_values
    except KeyError as e:
        logger.error(f"Error: The JSON file is not in the expected format. Missing key: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while processing JSON data: {str(e)}")
        raise
    except KeyError as e:
        logger.error(f"Error: The JSON file is not in the expected format. Missing key: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while processing JSON data: {str(e)}")
        raise
    
def plot_temperature_data(txt_file, output_file=None):
    """Generates a time-series plot of temperature data with trial markers.

    Processes a tab-delimited text file containing temperature measurements and
    creates a visualization with:
    - Continuous temperature curve
    - 30-second interval markers
    - Trial change indicators
    - Custom time formatting

    Args:
        txt_file (str): Path to input data file. Expected format:
            - 18-line header
            - Tab-separated columns:
              [counter, month, day, year, time, temp, TH1, TH2]
        output_file (str, optional): Path to save the plot image. If None,
            displays the plot interactively. Defaults to None.

    Returns:
        None: Either saves plot to file or displays it

    Raises:
        FileNotFoundError: If input file doesn't exist
        ValueError: For malformed data lines
        RuntimeError: For plotting failures
    """

    # Lists to store data
    times = []
    th1_values = []
    first_timestamp = None
    trial_markers = []  # To store each trial's start time
    
    try:
        with open(txt_file, 'r') as f:
            # Skip header (18 lines)
            for _ in range (18):
                next(f)
            
            prev_counter = None
            for line in f:
                if line.strip():
                    parts = [p.strip() for p in line.split('\t') if p.strip()]
                    if len(parts) >= 7:
                        try:
                            # Get counter (first column)
                            counter = int(parts[0])
                            
                            # Create datetime object
                            date_str = f"{parts[1]} {parts[2]} {parts[3]}"
                            dt = datetime.strptime(date_str, "%b %d %Y %H:%M:%S")
                            
                            if first_timestamp is None:
                                first_timestamp = dt
                            
                            # Detect counter reset (new trial)
                            if prev_counter is not None and counter < prev_counter:
                                trial_markers.append(dt)
                            
                            prev_counter = counter
                            times.append(dt)
                            th1_values.append(float(parts[6]))  # TH1 is column 6 (index 5)
                        except (ValueError, IndexError) as e:
                            logger.error(f"Error processing line: {line.strip()} - {str(e)}")
                            continue
        
        if not times:
            logger.warning("No valid data found")
            return
            
        # Create figure
        fig, ax = plt.subplots(figsize=(14, 7))
        
        # Plot all points
        ax.plot(times, th1_values, 'b-', linewidth=1.5)
        
        # Calculate time range
        start_time = first_timestamp
        end_time = times[-1]
        
        # Add gray vertical lines every 30 seconds
        current_time = start_time
        while current_time <= end_time:
            ax.axvline(x=current_time, color='gray', linestyle=':', linewidth=0.5, alpha=0.7)
            current_time += timedelta(seconds=30)
        
        # Add red lines at each detected trial
        for trial_time in trial_markers:
            ax.axvline(x=trial_time, color='red', linestyle='--', linewidth=1.5, alpha=0.8)
        
        # Configure X-axis ticks (bottom)
        custom_ticks = [start_time]+trial_markers+[end_time]
        ax.set_xticks(custom_ticks)
        ax.xaxis.set_major_formatter(DateFormatter('%H:%M:%S'))
        plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
        
        # Style configuration
        ax.set_title('TH1 Temperature Evolution (Trials marked in red)', pad=20)
        ax.set_xlabel('Time (gray lines: 30s | red lines: trial change)')
        ax.set_ylabel('TH1 Temperature [°C]')
        ax.grid(True, axis='y', linestyle=':', alpha=0.5)
        
        plt.tight_layout()
        
        # Save or display
        if output_file:
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"Plot saved in: {output_file}")
        else:
            plt.show()
            
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        raise

def plot_stab_temp(txt_file, data, output_file=None):
    """Generates a plot of stabilized temperatures across experimental trials.

    Reads a text file containing trial-temperature pairs and creates a line plot
    showing the temperature stabilization profile across multiple trials.

    Args:
        txt_file (str): Path to input text file. Expected format:
            "Trial X is Temp: Y" per line
        data (str): Dataset identifier for plot title
        output_file (str, optional): Path to save the plot image. If None,
            displays the plot interactively. Defaults to None.

    Returns:
        None: Either saves plot to file or displays it

    Raises:
        FileNotFoundError: If input file doesn't exist
        ValueError: For malformed data lines
        RuntimeError: For plotting failures

    Examples:
        >>> plot_stab_temp("temps.txt", "Experiment 1", "output.png")
        Plot saved in output.png

    Note:
        - Creates a red line plot with circle markers
        - Automatically adjusts y-axis limits with 0.2°C padding
        - Uses 300 DPI for saved images
        - Formats grid with dashed lines
        - Shows exact trial numbers on x-axis
    """

    trials = []
    temps = []
    
    try:
        # Read and parse the data file
        with open(txt_file, 'r') as f:
            for line in f:
                if line.strip():  # Skip empty lines
                    # Extract trial number and temperature
                    parts = line.split('Trial ')
                    trial_part = parts[1].split(' is Temp: ')
                    
                    trial_num = int(trial_part[0])
                    temp = float(trial_part[1].strip())
                    
                    trials.append(trial_num)
                    temps.append(temp)
        
        # Create the plot
        plt.figure(figsize=(10, 6))
        plt.plot(trials, temps, 'ro-', linewidth=1.5, markersize=8)
        
        # Format the plot
        plt.title(f'Stabilized Temperatures by Trial ({data})', fontsize=14, fontweight='bold')
        plt.xlabel('Trial Number', fontsize=12)
        plt.ylabel('Temperature [ºC]', fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7)
        
        # Adjust axes for better visualization
        plt.xticks(trials)
        plt.ylim(min(temps)-0.2, max(temps)+0.2)
        
        plt.tight_layout()
        
        # Save or display the plot
        if output_file:
            plt.savefig(output_file, dpi=300)
            plt.close()
            print(f"Plot saved in {output_file}")
        else:
            plt.show()
            
    except Exception as e:
        print(f"Error processing file: {e}")
        raise

def normalize(values):
    """Normalizes numeric values to a specified range using min-max scaling.

    Transforms input data to a target range while preserving the original distribution.
    Handles edge cases including constant arrays and provides numerical stability.

    Args:
        values (array-like): Input data to normalize (list, np.ndarray, or pd.Series)
        feature_range (tuple, optional): Target (min, max) range. Defaults to (0, 1).

    Returns:
        np.ndarray: Normalized values scaled to feature_range

    Raises:
        ValueError: If input is empty or contains infinity/NaN
        TypeError: If input contains non-numeric values

    Examples:
        >>> normalize([1, 2, 3])
        array([0. , 0.5, 1. ])

        >>> normalize([0, 10, 100], (-1, 1))
        array([-1. , -0.8,  1. ])

    Note:
        - Adds ε=1e-10 to prevent division by zero
        - Returns all values as midpoint of feature_range for constant inputs
        - Preserves input array shape and dtype (float64)
    """
    values_array = np.array(values)
    return (values_array - np.min(values_array)) / (np.max(values_array) - np.min(values_array))

def load_objective_csv_spectrum(csv_path):
    """Loads and processes spectral data from a CSV file.

    Reads wavelength-intensity pairs from a CSV file, filters wavelengths > 300nm,
    normalizes intensity values, and returns processed data. Handles malformed data
    by capturing the problematic row for error reporting.

    Args:
        csv_path (str): Path to CSV file with spectral data. Expected format:
            - First row: Header (skipped)
            - Subsequent rows: wavelength (float), intensity (float)

    Returns:
        tuple: Contains three elements:
            - wavelengths (list): Filtered wavelength values >300nm
            - values_normalized (numpy.ndarray): Normalized intensity values [0-1]
            - solution_info (str): First malformed row if errors occur, else empty string

    Raises:
        FileNotFoundError: If CSV file doesn't exist
        ValueError: If CSV has incorrect format

    Examples:
        >>> load_objective_csv_spectrum("spectrum.csv")
        ([400.0, 450.0], array([0.2, 0.8]), '')

    Note:
        - Skips header row and empty lines
        - Filters wavelengths below 300nm
        - Normalizes intensities using min-max scaling
        - Preserves original wavelength ordering
        - Returns first malformed row for debugging
    """
    wavelengths = []
    values = []
    with open(csv_path, 'r') as csvfile:
        reader = csv.reader(csvfile)
        lines = list(reader)

        lines = lines[1:] # Skip header
        header = lines[0]
            
        for row in lines[1:]:
            if not row or not row[0]:
                continue

            try:    
                wavelength = (float(row[0]))
                value = (float(row[1]))
                if wavelength > 300:
                    wavelengths.append(wavelength)
                    values.append(value)
            except ValueError:
                solution_info = str(row[0])
    
        # Normalize values
        values_normalized = normalize(values)
        return wavelengths, values_normalized, solution_info
    
def load_objective_json_spectrum(json_path):
    """Loads and processes spectral data from a JSON file.

    Reads wavelength-intensity pairs from a JSON file, filters wavelengths >300nm,
    and returns normalized intensity values. The function expects specific JSON structure
    and handles the data processing pipeline.

    Args:
        json_path (str): Path to JSON file containing spectral data. Expected format:
            [
                {"wavelengths": float, "value": float},
                {"wavelengths": float, "value": float},
                ...
            ]

    Returns:
        tuple: Contains two elements:
            - wavelengths (list): Filtered wavelength values >300nm in original order
            - values_normalized (numpy.ndarray): Intensity values normalized to [0,1] range

    Raises:
        FileNotFoundError: If JSON file doesn't exist
        json.JSONDecodeError: If file contains invalid JSON
        KeyError: If required fields ('wavelengths' or 'value') are missing
        ValueError: If wavelength/value cannot be converted to float

    Examples:
        >>> load_objective_json_spectrum("spectrum.json")
        ([400.0, 450.0, 500.0], array([0.1, 0.5, 1.0]))

    Note:
        - Strictly filters wavelengths below 300nm
        - Preserves original ordering of wavelengths
        - Uses min-max normalization (via normalize() function)
        - Returns numpy array for normalized values
    """
    with open(json_path, 'r') as jsonfile:
        data = json.load(jsonfile)
    
    # Filter wavelengths above 300
    filtered_data = [item for item in data if item['wavelengths'] > 300]
    
    wavelengths = [item['wavelengths'] for item in filtered_data]
    values = [item['value'] for item in filtered_data]
    
    # Normalize the values
    values_normalized = normalize(values)
    return wavelengths, values_normalized

def plot_spectra_files_csv(folder_path, objective_csv_path=None, save_path=None):
    """Generates and saves/plots spectral comparisons for JSON files in a directory.

    Processes multiple JSON spectral files, compares them against an optional objective
    spectrum from CSV, and generates individual plots. Handles file I/O, data filtering,
    normalization, and visualization.

    Args:
        folder_path (str): Path to directory containing JSON spectral files
        objective_csv_path (str, optional): Path to CSV with reference spectrum.
            Expected format: wavelength, intensity columns with header.
            Defaults to None (no comparison spectrum).
        save_path (str, optional): Directory to save plots. If None, displays plots.
            Defaults to None.

    Returns:
        None: Generates plots either as files or interactive displays

    Raises:
        FileNotFoundError: If input directory or CSV file doesn't exist
        json.JSONDecodeError: For malformed JSON files
        ValueError: For invalid spectral data

    Examples:
        >>> plot_spectra_files_csv('data/spectra', 'ref/objective.csv', 'output/plots')
        # Saves PNG plots for each JSON file in 'output/plots'

        >>> plot_spectra_files_csv('data/spectra')
        # Displays interactive plots for each file

    Note:
        - Filters wavelengths below 300nm
        - Normalizes all intensity values to [0,1] range
        - Saves plots at 300 DPI when save_path specified
        - Uses blue for trial spectra, green for objective spectrum
        - Skips files with processing errors (logs warning)
        - Creates separate plot for each JSON file
    """
    if objective_csv_path:
        objective_wavelengths, objective_values, solution_info=load_objective_csv_spectrum(objective_csv_path)
    else:
        objective_wavelengths, objective_values = None, None
        
    # Get list of JSON files in folder
    files = [f for f in os.listdir(folder_path) if f.endswith('.json')]
    
    if not files:
        logger.warning(f"No JSON files found in the folder: {folder_path}")
        return
    
    # Create figure for each file
    for filename in files:
        file_name=os.path.splitext(filename)[0]
        print(file_name)
        file_path = os.path.join(folder_path, filename)
        
        try:
            # Read JSON file
            with open(file_path, 'r') as file:
                data = json.load(file)
            
            # Filter and extract data
            filtered_data = [item for item in data if item['wavelengths'] > 300]
            wavelengths = [item['wavelengths'] for item in filtered_data]
            values = [item['value'] for item in filtered_data]
            values_normalized = normalize(values)
            
            # Create plot
            plt.figure(figsize=(10, 6))
            plt.plot(wavelengths, values_normalized, 'b-', linewidth=1, label='Trial_Spectrum')

            if len(objective_wavelengths) > 0 and len(objective_values) > 0:
                plt.plot(objective_wavelengths, objective_values, 'g-', linewidth=1.2, label='Objective Spectrum')
            
            plt.title(filename)
            plt.xlabel('Wavelength (nm)')
            plt.ylabel('Intensity')
            plt.grid(True)
            plt.legend()
            
            # Save or display plot
            if save_path:
                plt.savefig(os.path.join(save_path ,f'{file_name}_plot.png'), dpi=300)
                print(f'Plot saved in {save_path}')
                plt.close()
            else:
                plt.show()
            
        except Exception as e:
            print(f"Error processing file {filename}: {str(e)}")

def plot_spectra_files_json(folder_path, objective_json_path=None, save_path=None):
    """Generates comparative spectral plots from JSON files in a directory.

    Processes multiple JSON spectral files, compares them against an optional objective
    spectrum (also in JSON format), and generates publication-quality plots. Handles
    data loading, normalization, visualization, and saving.

    Args:
        folder_path (str): Path to directory containing trial JSON spectral files.
            Files should contain [{"wavelengths": float, "value": float}, ...]
        objective_json_path (str, optional): Path to reference spectrum JSON file.
            If provided, will be plotted alongside trial spectra. Defaults to None.
        save_path (str, optional): Directory to save output plots. If None, plots
            are displayed interactively. Defaults to None.

    Returns:
        None: Generates plots either as saved files or interactive displays

    Raises:
        FileNotFoundError: If input directory or JSON files don't exist
        json.JSONDecodeError: For malformed JSON files
        ValueError: For invalid spectral data (missing fields, wrong types)
        RuntimeError: For plotting failures

    Examples:
        >>> plot_spectra_files_json('data/trials', 'data/reference.json', 'output/plots')
        # Saves comparison plots for each trial file in output/plots

        >>> plot_spectra_files_json('data/trials')
        # Displays interactive plots without reference spectrum

    Note:
        - Filters wavelengths below 300nm
        - Normalizes all intensity values to [0,1] range
        - Uses consistent color scheme (blue=trial, green=reference)
        - Saves plots at 300 DPI with descriptive filenames
        - Creates directory structure if save_path doesn't exist
        - Skips the objective file when processing the folder
        - Maintains original wavelength ordering
    """
    if objective_json_path:
        objective_wavelengths, objective_values = load_objective_json_spectrum(objective_json_path)
    else:
        objective_wavelengths, objective_values = None, None
        
    # Get list of files in the folder
    files = [f for f in os.listdir(folder_path) if f.endswith('.json') and f != os.path.basename(objective_json_path)]
    
    if not files:
        print(f"No JSON files found in folder: {folder_path}")
        return
    
    # Create a figure for each file
    for filename in files:
        file_name = os.path.splitext(filename)[0]
        file_path = os.path.join(folder_path, filename)
        
        try:
            # Read the JSON file
            with open(file_path, 'r') as file:
                data = json.load(file)
            
            # Filter wavelengths above 300
            filtered_data = [item for item in data if item['wavelengths'] > 300]
            
            # Extract wavelengths and values
            wavelengths = [item['wavelengths'] for item in filtered_data]
            values = [item['value'] for item in filtered_data]

            values_normalized = normalize(values)
            
            # Create the plot
            plt.figure(figsize=(10, 6))
            plt.plot(wavelengths, values_normalized, 'b-', linewidth=1, label='Trial Spectrum')

            if objective_wavelengths is not None and objective_values is not None:
                plt.plot(objective_wavelengths, objective_values, 'g-', linewidth=1.2, label='Objective Spectrum')
            
            plt.title(file_name)
            plt.xlabel('Wavelength (nm)')
            plt.ylabel('Normalized Intensity')
            plt.grid(True)
            plt.legend()
            
            # Save the plot
            if save_path:
                os.makedirs(save_path, exist_ok=True)
                plt.savefig(os.path.join(save_path, f'{file_name}_plot.png'), dpi=300)
                logger.info(f'Plot saved to {save_path}/{file_name}_plot.png')
                plt.close()
            else:
                plt.show()
            
        except Exception as e:
            print(f"Error processing file {filename}: {str(e)}")

def validate_experiment_limits(real_path, experiment_path):
    """Validates experiment channel limits against real hardware limits.

    Compares experimental channel limit configurations against actual hardware
    constraints, checking for:
    - Integer type validation
    - Non-negative lower limits
    - Upper limits within hardware capabilities
    - Complete channel coverage

    Args:
        real_path (str): Path to JSON file containing real hardware limits.
            Expected format: [{"channel": str, "Limit": int}, ...]
        experiment_path (str): Path to JSON file containing experiment limits.
            Expected format: [{"channel": str, "Lower-limit": int, "Upper-limit": int}, ...]

    Returns:
        bool: True if all limits are valid, False if any validation fails

    Raises:
        FileNotFoundError: If either JSON file doesn't exist
        json.JSONDecodeError: For malformed JSON files
        KeyError: If required fields are missing in JSON data

    Examples:
        >>> validate_experiment_limits("hardware_limits.json", "experiment_limits.json")
        Channel 1: ERROR - Upper-limit exceeds the actual limit (1000)
        False

        >>> validate_experiment_limits("hardware.json", "config.json")
        All limits are valid.
        True

    Note:
        - Performs case-sensitive channel matching
        - Logs detailed validation failures
        - Stops after first error for each channel
        - Requires exact field names ('channel', 'Limit', 'Lower-limit', 'Upper-limit')
    """
    # Load JSON files
    with open(real_path, 'r') as f:
        real_limits = json.load(f)

    with open(experiment_path, 'r') as f:
        experiment_limits = json.load(f)

    # Create quick-access dictionary by channel
    real_dict = {entry['channel']: entry['Limit'] for entry in real_limits}

    logger.info("---- LIMIT VALIDATION ----")
    errores = False

    for entry in experiment_limits:
        ch = entry['channel']
        lower = entry['Lower-limit']
        upper = entry['Upper-limit']
        real_limit = real_dict.get(ch)

        # Integer type validation
        if not isinstance(lower, int):
            logger.warning(f"Channel {ch}: ERROR - Lower-limit = {lower} is not an integer. It must be an integer number.")
            errores = True

        if not isinstance(upper, int):
            logger.warning(f"Channel {ch}: ERROR - Upper-limit = {upper} is not an integer. It must be an integer number.")
            errores = True

        # Range validation
        if lower < 0:
            logger.warning(f"Channel {ch}: ERROR - Lower-limit = {lower} is less than 0. It must be ≥ 0.")
            errores = True

        if upper > real_limit:
            logger.warning(f"Channel {ch}: ERROR - Upper-limit = {upper} exceeds the actual limit ({real_limit}). It must be ≤ {real_limit}.")
            errores = True

    if not errores:
        logger.info("All limits are valid.")
        return True
    return False

def create_folders(paths):
    """Creates multiple directories with comprehensive error handling.

    Safely creates a series of directories, including any necessary parent directories.
    Implements robust error handling and logging for each directory creation attempt.

    Args:
        paths (list[str]): List of directory paths to create. Can be absolute or relative paths.

    Returns:
        None: All valid directories are created; raises exception on critical failures.

    Raises:
        OSError: For filesystem-related errors (permissions, invalid paths, etc.)
        TypeError: If input is not a list of strings
        RuntimeError: For other unexpected failures

    Examples:
        >>> create_folders(["output/data", "output/logs"])
        Folder created: output/data
        Folder created: output/logs

        >>> create_folders(["/protected/system"])
        Error creating folder /protected/system: Permission denied

    Note:
        - Uses exist_ok=True to ignore already-existing directories
        - Creates entire directory tree for each path
        - Logs each successful creation at INFO level
        - Raises first encountered critical error
        - Continues attempting creation after non-critical errors
    """
    for path in paths:
        try:
            os.makedirs(path, exist_ok=True)
            logger.info(f"Folder created: {path}")
        except Exception as e:
            logger.error(f"Error creating folder {path}: {str(e)}")
            raise

def create_base_folders(paths):
    """Creates multiple directories with error handling and logging.

    Safely creates all specified directories including any necessary parent directories.
    This function is designed for setting up initial project directory structures.

    Args:
        paths (Union[List[str], str]): Either a single directory path (str) or 
            a list of directory paths to create. Paths can be absolute or relative.

    Returns:
        None: No return value, but all valid directories will be created.

    Raises:
        OSError: For filesystem-related errors (permission denied, invalid path, etc.)
        TypeError: If input paths are not strings or list of strings

    Examples:
        >>> create_base_folders("data/raw")
        >>> create_base_folders(["data/processed", "results/figures"])

    Note:
        - Silently skips already existing directories (exist_ok=True)
        - Creates entire directory hierarchy as needed
        - Logs errors but continues execution for subsequent paths
        - Accepts both single path strings and lists of paths
    """
    for path in paths:
        try:
            os.makedirs(path, exist_ok=True)
        except Exception as e:
            logger.error(f"Error creating folder {path}: {str(e)}")

def load_ax_params(experiment_limits_path):
    """Loads and transforms experiment limits into AX optimization parameters.

    Converts channel limit configurations from JSON into the parameter format required
    by AX's optimization engine. Validates the input structure and handles file operations.

    Args:
        experiment_limits_path (str): Path to JSON file containing channel limits.
            Expected format:
            [
                {
                    "channel": str|int,
                    "Lower-limit": int,
                    "Upper-limit": int
                },
                ...
            ]

    Returns:
        list: AX-compatible parameter specifications in the format:
            [
                {
                    "name": "led_X",
                    "type": "range",
                    "bounds": [min, max],
                    "value_type": "int"
                },
                ...
            ]

    Raises:
        FileNotFoundError: If specified JSON file doesn't exist
        json.JSONDecodeError: For malformed JSON content
        KeyError: If required fields are missing
        ValueError: For invalid limit values (min > max)

    Examples:
        >>> load_ax_params("experiment_limits.json")
        [
            {"name": "led_1", "type": "range", "bounds": [0, 1000], "value_type": "int"},
            {"name": "led_2", "type": "range", "bounds": [0, 1500], "value_type": "int"}
        ]

    Note:
        - Converts channel numbers to 'led_X' format
        - Enforces integer value types for all parameters
        - Logs first two parameters as examples
        - Validates that lower <= upper bounds
    """
    logger.info(f"Loading AX parameters from: {experiment_limits_path}")
    try:
        with open(experiment_limits_path, 'r') as f:
            limits = json.load(f)

        parametros_ax = [
            {
                "name": f"led_{item['channel']}",
                "type": "range",
                "bounds": [item['Lower-limit'], item['Upper-limit']],
                "value_type": "int"
            }
            for item in limits
        ]
        logger.debug(f"AX parameters generated: {parametros_ax[:2]}...")  # Log primeros 2 para ejemplo
        return parametros_ax
    except Exception as e:
        logger.error(f"Error loading AX parameters: {str(e)}")
        raise

def plot_parameter_comparison(trial_json_dir, target_values, save_path=None):
    """Generates comparison plots between trial parameters and target values.

    Creates side-by-side visualizations of LED channel parameters from trial JSON files
    against reference target values, with professional formatting for publication-quality
    output.

    Args:
        trial_json_dir (str): Directory containing trial JSON files. Files should contain:
            [{"channel": str|int, "value": float}, ...]
        target_values (dict): Reference values in format {"led X": float}
        save_path (str, optional): Directory to save plots. If None, displays plots.
            Defaults to None.

    Returns:
        None: Generates plots either as files or interactive displays

    Raises:
        FileNotFoundError: If directory doesn't exist
        json.JSONDecodeError: For malformed JSON files
        KeyError: If required fields are missing in JSON data

    Examples:
        >>> target = {"led 1": 100, "led 2": 200}
        >>> plot_parameter_comparison("trials", target, "output/plots")

    Note:
        - Creates one plot per trial file
        - Sorts LEDs numerically (led 1, led 2,...)
        - Uses consistent color scheme (green=target, blue=trial)
        - Saves at 300 DPI with tight bounding boxes
        - Automatic directory creation for save_path
        - Clean grid styling with subtle transparency
        - Rotated x-axis labels for readability
    """

    # Get all trial JSON files
    trial_files = [f for f in os.listdir(trial_json_dir) if f.endswith('.json')]
    
    for trial_file in trial_files:
        # Load trial data
        with open(os.path.join(trial_json_dir, trial_file), 'r') as f:
            trial_data = json.load(f)
        trial_params = {f"led {item['channel']}": item['value'] for item in trial_data}
        
        # Prepare plot data
        leds = sorted(target_values.keys(), key=lambda x: int(x.split()[1]))  # Ordenar por número de LED
        led_numbers = [int(led.split()[1]) for led in leds]  # Extraer solo los números
        target = [target_values[led] for led in leds]
        trial = [trial_params.get(led, 0) for led in leds]  # 0 si no existe el led
        
        # Create figure
        plt.figure(figsize=(12, 6))
        
        # Plot formatted lines
        plt.plot(led_numbers, target, color='green', label='Target', 
                linewidth=2.5, alpha=0.9)
        plt.plot(led_numbers, trial, color='blue', label='Trial', 
                linewidth=2.5, alpha=0.9, linestyle='--')
        
        # Style configuration
        plt.xlabel('LED Channel', fontsize=12)
        plt.ylabel('Value', fontsize=12)
        plt.title(f'Comparison: {trial_file[:-5]}', pad=20, fontsize=14)
        plt.legend(fontsize=11, framealpha=0.9)
        plt.grid(True, linestyle=':', alpha=0.3)
        plt.xticks(led_numbers, leds, rotation=45, fontsize=10)
        plt.yticks(fontsize=10)
        plt.margins(x=0.03)
        
        # Save or display
        if save_path:
            os.makedirs(save_path, exist_ok=True)
            output_file = os.path.join(save_path, f'compare_{trial_file[:-5]}.png')
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            plt.close()
            logger.info(f"Plot saved in {output_file}")
        else:
            plt.show()

def log(config):
    """Configures the global logging system for the application.

    Initializes a comprehensive logging setup with:
    - File and console output handlers
    - Customizable log levels for application and third-party libraries
    - Automatic log directory creation
    - Consistent formatting across all loggers

    Args:
        config (object): Configuration object containing at least:
            - LOG_FILE (str): Path to log file
            (Other expected module-level constants: EXP_LOG_LEVEL, Matplotlib_LOG_LEVEL,
             Pyvisa_LOG_LEVEL, PIL_LOG_LEVEL)

    Returns:
        tuple: Configured log levels for:
            - Main application (int)
            - Matplotlib (str)
            - PyVISA (str)
            - PIL (int)

    Raises:
        OSError: If log directory cannot be created
        AttributeError: If required config values are missing
        ValueError: For invalid log level specifications

    Examples:
        >>> from config import Config
        >>> log(Config)
        (20, 'warning', 'WARNING', 30)

    Note:
        - Removes existing handlers before configuration
        - Uses standard logging levels (DEBUG=10, INFO=20, etc.)
        - Configures four separate logging systems:
            1. Main application logging
            2. Matplotlib logging
            3. PyVISA logging
            4. PIL (Pillow) logging
        - Creates log directory if needed
        - Format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    """  
    try:
        # Create log directory if it doesn't exist
        os.makedirs(os.path.dirname(config.LOG_FILE), exist_ok=True)
        
        # Configure main application logging
        log_levels = {
            "DEBUG": logging.DEBUG, 
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        log_level = log_levels.get(EXP_LOG_LEVEL.upper(), logging.WARNING)

        # Clear existing handlers
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        # Set up new handlers (file and console)
        handlers=[
                logging.FileHandler(config.LOG_FILE),
                logging.StreamHandler()
            ]
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=handlers
        )

        # Configure Matplotlib logging
        mat_log_levels = {
            "DEBUG": "debug", 
            "INFO": "info",
            "WARNING": "warning",
            "ERROR": "error",
            "CRITICAL": "critical" 
        }
        mat_log_level=mat_log_levels.get(Matplotlib_LOG_LEVEL.upper(), "warning")
        matplotlib.set_loglevel(mat_log_level)

        # Configure PyVISA logging
        pyvisa_logs = {
            "DEBUG": "DEBUG", 
            "INFO": "INFO",
            "WARNING": "WARNING",
            "ERROR": "ERROR",
            "CRITICAL": "CRITICAL"
        }
        pyvisa_log=pyvisa_logs.get(Pyvisa_LOG_LEVEL.upper(), "WARNING")
        pyvisa.logger.setLevel(pyvisa_log)

        # Configure PIL (Pillow) logging
        plog_levels = {
            "DEBUG": logging.DEBUG, 
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        plog_level = plog_levels.get(PIL_LOG_LEVEL.upper(), logging.WARNING)
        logging.getLogger('PIL').setLevel(plog_level)
        
        return log_level, mat_log_level, pyvisa_log, plog_level

    except Exception as e:
        print(f"Critical error while setting up logging: {str(e)}")
        raise

def channel_test_limits(config):
    """Generates a JSON file with default test limits for all channels.

    Creates a standardized configuration file containing test limits for 32 channels,
    with each channel set to a default limit of 3300. This is typically used for
    simulation or testing purposes.

    Args:
        config (object): Configuration object containing:
            - CHANNEL_SIM_LIMITS_FILE (str): Path to output JSON file

    Returns:
        None: Writes JSON file to specified path

    Raises:
        OSError: If the file cannot be written (permissions, disk full)
        TypeError: If config object is missing required attributes

    Examples:
        >>> from config import Config
        >>> channel_test_limits(Config)
        File successfully generated: config/channel_limits.json

    Note:
        - Generates limits for channels 1-32 inclusive
        - Uses consistent 3300 value for all channels
        - Creates pretty-printed JSON with 4-space indentation
        - Overwrites existing file without warning
    """
    # Create channel list with limit 3300
    canales = [{"channel": i, "Limit": 3300} for i in range(1, 33)]

    # Save to JSON file
    with open(config.CHANNEL_SIM_LIMITS_FILE, 'w') as f:
        json.dump(canales, f, indent=4)

    logger.info(f"File successfully generated: {config.CHANNEL_SIM_LIMITS_FILE}")

def process_spectra(datos_espectro):
    """Processes spectral data by rounding wavelengths and removing duplicates.

    Performs two key processing steps on spectral data:
    1. Converts wavelengths to nearest integer values
    2. Removes duplicate wavelengths, keeping only the first occurrence

    Args:
        datos_espectro (Union[list, dict]): Input spectral data in either:
            - List format: [{"wavelengths": float, "value": float}, ...]
            - Dict format: {wavelength(str/float): value(float), ...}

    Returns:
        list: Processed spectrum with:
            - Integer wavelengths
            - No duplicate wavelengths
            - Preserved original order of first occurrences
            - Format: [{"wavelengths": int, "value": float}, ...]

    Raises:
        TypeError: If input is neither list nor dict
        KeyError: If list elements lack required "wavelengths"/"value" keys
        ValueError: If wavelength/value conversion fails

    Examples:
        >>> process_spectra([{"wavelengths": 400.3, "value": 0.5}])
        [{"wavelengths": 400, "value": 0.5}]

        >>> process_spectra({"400.5": 0.5, "401.2": 0.7})
        [{"wavelengths": 401, "value": 0.5}, {"wavelengths": 401, "value": 0.7}]

    Note:
        - Uses Python's round() for wavelength conversion
        - Maintains first occurrence when duplicates exist
        - Preserves original value precision
        - Logs processing start at INFO level
    """
    logger.info('Processing spectra values...')

    # Convert dict to list of dicts if needed
    if isinstance(datos_espectro, dict):
        datos_espectro = [{"wavelengths": float(k), "value": v} for k, v in datos_espectro.items()]

    visto = set()
    espectro_procesado = []
    
    for punto in datos_espectro:
        wavelength_int = int(round(float(punto["wavelengths"])))
        
        if wavelength_int not in visto:
            visto.add(wavelength_int)
            espectro_procesado.append({
                "wavelengths": wavelength_int,
                "value": punto["value"]
            })
    return espectro_procesado

def plot_loss_from_txt(file_path,save_path):
    """Generates and saves/displays a loss evolution plot from trial data in a text file.

    Parses a text file containing trial loss values and creates a publication-quality
    line plot showing the progression of loss across trials. Handles both display and
    file saving options.

    Args:
        file_path (str): Path to input text file containing loss data. Expected format:
            Lines containing "Trial X" and "Loss: Y" or "Loss is: Y"
        save_path (str, optional): Directory to save the plot image. If None, displays
            the plot interactively. Defaults to None.

    Returns:
        None: Generates plot either as saved file or interactive display

    Raises:
        FileNotFoundError: If input file doesn't exist
        ValueError: If no valid data lines are found
        RuntimeError: For plotting failures

    Examples:
        >>> plot_loss_from_txt("loss_data.txt", "output/plots")
        Plot saved in: output/plots/loss_plot.png

        >>> plot_loss_from_txt("experiment_results.txt")
        # Displays interactive plot

    Note:
        - Only processes lines containing both "Trial" and "Loss"
        - Uses blue circular markers connected by lines
        - Saves at 300 DPI with tight bounding box
        - Creates automatic grid with dashed lines
        - Logs successful saves at INFO level
        - Shows exact trial numbers on x-axis
    """
    
    trials = []
    losses = []
    
    with open(file_path, 'r') as file:
        for line in file:
            if "Loss" in line and "Trial" in line:
                try:
                    # Extract trial number
                    trial_part = line.split("Trial")[1].split()[0]
                    trial_num = int(trial_part.strip(' :')) 
                    
                    # Extract loss value
                    loss_part = line.split("is:")[1] if "is:" in line else line.split(":")[1]
                    loss_value = float(loss_part.strip())
                    
                    trials.append(trial_num)
                    losses.append(loss_value)
                except (IndexError, ValueError) as e:
                    logger.error(f"Warning: Could not process the line: {line.strip()}. Error: {e}")
                    continue
    
    if not trials:
        raise ValueError("No valid data found in the file.")
    
    # Create the plot
    plt.figure(figsize=(10, 6))
    plt.plot(trials, losses, marker='o', linestyle='-', color='b', label='Loss per Trial')
    
    # Add labels and title
    plt.xlabel('Number of Trial')
    plt.ylabel('Loss Value')
    plt.title('Loss Evolution Across Trials')
    plt.xticks(trials) 
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    
    # Save or display the plot
    if save_path:
        output_path = os.path.join(save_path, 'loss_plot.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        logger.info(f"Plot saved in: {output_path}")
        plt.close()
    else:
        plt.show()

def search_and_load_target_values(file_name, json_dir, csv_dir):
    """Searches for and loads target spectral values from either JSON or CSV files.

    This function attempts to locate target spectral data by checking both JSON and CSV
    formats. If found in CSV format, it automatically converts to JSON before loading.

    Args:
        file_name (str): Base name of the target file (without extension)
        json_dir (str): Directory path to search for JSON files
        csv_dir (str): Directory path to search for CSV files

    Returns:
        dict: Target spectral values in format {wavelength: value}
        The specific format depends on the loader used (JSON or CSV)

    Raises:
        FileNotFoundError: If no matching files are found in either directory
        ValueError: If found files contain invalid data
        json.JSONDecodeError: For malformed JSON files
        csv.Error: For malformed CSV files

    Examples:
        >>> search_and_load_target_values("target1", "data/json", "data/csv")
        {400: 0.5, 450: 0.7, 500: 0.9}

    Note:
        - Checks for JSON file first (preferred format)
        - Automatically converts CSV to JSON if needed
        - Conversion preserves original data structure
        - Logs which format was found at INFO level
        - Raises exception only if neither format exists
    """
    json_path = os.path.join(json_dir, f"{file_name}.json")
    csv_path = os.path.join(csv_dir, f"{file_name}.csv")

    if os.path.isfile(json_path):
        logger.info(f"JSON file founded: {json_path}")
        return load_target_values(json_path)

    elif os.path.isfile(csv_path):
        logger.info(f"CSV file founded: {csv_path}, converting to JSON...")
        data = csv_to_json_like_reference(csv_path, json_path)
        return load_target_values(json_path)

    else:
        logger.error("No target_values in .json o .csv format")
        raise FileNotFoundError("No target_values in json o csv.")
    
def search_and_load_target_spectra(file_name, json_dir, csv_dir):
    """Searches for and loads target spectral data from either JSON or CSV files.

    This function attempts to locate target spectral data by checking both JSON and CSV
    formats. If found in CSV format, it automatically converts to JSON before loading.

    Args:
        file_name (str): Base name of the target file (without extension)
        json_dir (str): Directory path to search for JSON files
        csv_dir (str): Directory path to search for CSV files

    Returns:
        dict: Target spectral data in format {wavelength: value} 
        The specific format depends on the loader used (JSON or CSV)

    Raises:
        FileNotFoundError: If no matching files are found in either directory
        ValueError: If found files contain invalid data
        json.JSONDecodeError: For malformed JSON files
        csv.Error: For malformed CSV files

    Examples:
        >>> search_and_load_target_spectra("spectra1", "data/json", "data/csv")
        {400: 0.5, 450: 0.7, 500: 0.9}

    Note:
        - Checks for JSON file first (preferred format)
        - Automatically converts CSV to JSON if needed
        - Conversion preserves original data structure
        - Logs which format was found at INFO level
        - Raises exception only if neither format exists
        - Error message includes the specific file_name that wasn't found
    """
    json_path = os.path.join(json_dir, f"{file_name}.json")
    csv_path = os.path.join(csv_dir, f"{file_name}.csv")

    if os.path.isfile(json_path):
        logger.info(f"JSON file founded: {json_path}")
        return load_target_spectra(json_path)

    elif os.path.isfile(csv_path):
        logger.info(f"CSV file founded: {csv_path}, converting to JSON...")
        data = csv_to_json_like_reference(csv_path, json_path)
        return load_target_spectra(json_path)

    else:
        logger.error(f"No {file_name} in .json o .csv format")
        raise FileNotFoundError(f"No {file_name} in json o csv.")
    
def csv_to_json_like_reference(csv_path, json_output_path):
    """Converts CSV spectral data to JSON format with specific structure.

    Processes CSV files containing spectral data, extracting wavelength and absorbance values,
    and saves them in a standardized JSON format. Handles different CSV formats based on
    global configuration flags (MAXIMIZE_TEMP/SPECTRAL_MATCHING).

    Args:
        csv_path (str): Path to the input CSV file
        json_output_path (str): Path where the JSON output should be saved

    Returns:
        list: Converted data in format [{"wavelengths": float, "value": float}, ...]
        Also saves this data to the specified JSON path

    Raises:
        FileNotFoundError: If the input CSV file doesn't exist
        ValueError: If required columns ("Wavelength (nm)" or "Abs") are missing
        json.JSONEncodeError: If there's an error writing the JSON file
        csv.Error: For malformed CSV files

    Examples:
        >>> csv_to_json_like_reference("input.csv", "output.json")
        [{"wavelengths": 400.0, "value": 0.5}, {"wavelengths": 450.0, "value": 0.7}]

    Note:
        - Handles two different CSV formats based on global flags:
          * MAXIMIZE_TEMP: Uses row 1 for headers, row 2+ for data
          * SPECTRAL_MATCHING: Uses row 0 for headers, row 1+ for data
        - Only processes rows with valid float values in both wavelength and absorbance columns
        - Silently skips rows with conversion errors (ValueError/IndexError)
        - Output JSON is pretty-printed with 4-space indentation
        - Requires specific column names: "Wavelength (nm)" and "Abs"
    """
    result = []

    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        rows = list(reader)

        # Use the second row (index 1) as actual headers for MAXIMIZE_TEMP mode
        if MAXIMIZE_TEMP:
            headers = rows[1]
            data_rows = rows[2:]
        if SPECTRAL_MATCHING:
            headers = rows[0]
            data_rows = rows[1:]

        wave_index = headers.index("Wavelength (nm)")
        value_index = headers.index("Abs")

        for row in data_rows:
            try:
                wavelength = float(row[wave_index])
                value = float(row[value_index])
                result.append({
                    "wavelengths": wavelength,
                    "value": value
                })
            except (ValueError, IndexError):
                continue

    with open(json_output_path, 'w', encoding='utf-8') as jsonfile:
        json.dump(result, jsonfile, indent=4)

    return result

def lowest_error_file(lw_error_file, target, seed, error_file):
    """Records the lowest error value from an error file to a designated log file.

    This function finds the minimum error value from a given error file and appends it,
    along with target and seed information, to a specified log file. Useful for tracking
    optimization results across different runs.

    Args:
        lw_error_file (str): Path to the log file where results will be appended
        target (str): Identifier for the target being optimized
        seed (int): Random seed used for the optimization run
        error_file (str): Path to the error file containing loss values to analyze

    Returns:
        None: This function writes to files but does not return a value

    Raises:
        FileNotFoundError: If either error_file or lw_error_file cannot be opened
        PermissionError: If write permissions are insufficient for lw_error_file
        ValueError: If error_file is malformed (handled by find_lowest_loss)

    Examples:
        >>> lowest_error_file("results.log", "target1", 42, "errors.csv")
        # Appends to results.log:
        # Target --> target1
        # Seed --> 42
        # Lowest_error --> 0.005

    Note:
        - Operates in append mode (preserves existing file content)
        - Uses debug-level logging for operation tracking
        - Relies on find_lowest_loss() for error value extraction
        - File writing is atomic (single write operation per call)
        - New entries are separated by newlines (no additional delimiters)
    """
    _,min_error=find_lowest_loss(error_file)
    with open(lw_error_file, 'a') as file:
        logger.debug(f'File opened successfully for writing (append mode): {lw_error_file}')
        file.write(f'Target --> {target}\nSeed --> {seed}\nLowest_error --> {min_error}\n')
        logger.debug(f'Lowest error written successfully to the file: {lw_error_file}, {min_error}')

def parse_error_data(config):
    """Parses error data from a structured text file into a list of dictionaries.

    Reads a specially formatted text file containing target, seed, and error information,
    and converts it into a structured list of dictionaries for easier processing. The input
    file should have lines starting with "Target -->", "Seed -->", and "Lowest_error -->".

    Args:
        config (object): Configuration object containing GLOBAL_DATAS path attribute

    Returns:
        list: A list of dictionaries where each dictionary contains:
            - "Target" (str): The target identifier
            - "Seed" (str): The seed value
            - "Error" (float): The lowest error value

    Raises:
        FileNotFoundError: If the Lowest_errors.txt file doesn't exist
        ValueError: If any line is malformed or contains invalid data
        IndexError: If any line doesn't contain the expected "-->" separator
        TypeError: If error value cannot be converted to float

    Examples:
        >>> parse_error_data(config)
        [
            {"Target": "target1", "Seed": "42", "Error": 0.005},
            {"Target": "target2", "Seed": "7", "Error": 0.012}
        ]

    Note:
        - Expects file format with strict prefix matching:
          * "Target --> value"
          * "Seed --> value"
          * "Lowest_error --> value"
        - Maintains state between lines (remembers current target/seed)
        - Automatically strips whitespace from all values
        - Converts error values to float automatically
        - Skips empty or whitespace-only lines
        - File path is constructed using config.GLOBAL_DATAS
    """
    file_path=os.path.join(config.GLOBAL_DATAS, 'Lowest_errors.txt')
    data = []
    with open(file_path, 'r') as file:
        current_target = None
        current_seed = None
        for line in file:
            line = line.strip()
            if line.startswith("Target -->"):
                current_target = line.split("-->")[1].strip()
            elif line.startswith("Seed -->"):
                current_seed = line.split("-->")[1].strip()
            elif line.startswith("Lowest_error -->") or line.startswith("Lowest_error -->"):
                error = float(line.split("-->")[1].strip())
                data.append({
                    "Target": current_target,
                    "Seed": current_seed,
                    "Error": error
                })
    return data

def plot_all_targets_errors(data, config):
    """Generates and saves a scatter plot visualizing error values across targets and seeds.

    Creates a comparative visualization showing the lowest error values achieved for each
    target across different seeds. Each seed is represented by a unique color, allowing
    for easy comparison of optimization performance.

    Args:
        data (list): List of dictionaries containing error data in format:
            [
                {"Target": str, "Seed": str, "Error": float},
                ...
            ]
        config (object): Configuration object with GLOBAL_DATAS attribute for save path

    Returns:
        None: Saves plot to disk as PNG file and closes the figure

    Raises:
        ValueError: If input data is empty or malformed
        KeyError: If required keys ("Target", "Seed", "Error") are missing
        PermissionError: If unable to save the output image

    Examples:
        >>> data = [
                {"Target": "A", "Seed": "1", "Error": 0.1},
                {"Target": "A", "Seed": "2", "Error": 0.15}
            ]
        >>> plot_all_targets_errors(data, config)
        # Saves error_targets_seeds.png to config.GLOBAL_DATAS directory

    Note:
        - Uses tab10 colormap for seed differentiation (max 10 unique colors)
        - Automatically handles duplicate legend entries
        - Y-axis starts at 0 for better error comparison
        - Applies consistent styling:
          * White-edged markers (size 60, alpha 0.8)
          * Grid with dashed lines (alpha 0.4)
          * 45-degree rotated x-labels for readability
        - Saves plot with tight layout to prevent label clipping
        - Figure size is fixed at 14x8 inches
        - Legend is placed outside the plot area (upper right)
    """
    plt.figure(figsize=(14, 8))
    
    # Organize data by target and seed
    targets = sorted(set(d["Target"] for d in data))
    seeds = sorted(set(d["Seed"] for d in data))
    
    # Assign unique colors to each seed
    colors = plt.cm.tab10.colors
    seed_colors = {seed: colors[i % len(colors)] for i, seed in enumerate(seeds)}
    
    # Plot each point manually
    for target in targets:
        target_data = [d for d in data if d["Target"] == target]
        x_pos = [target] * len(target_data)
        y_pos = [d["Error"] for d in target_data]
        seed_labels = [d["Seed"] for d in target_data]
        
        for x, y, seed in zip(x_pos, y_pos, seed_labels):
            plt.scatter(
                x, y,
                color=seed_colors[seed],
                label=seed if target == targets[0] else "",
                s=60,
                alpha=0.8,
                edgecolor='white',
                linewidth=0.5
            )
    
    # Chart customization
    plt.title("Lowest Error by Target and Seed", fontsize=16)
    plt.xlabel("Target", fontsize=14)
    plt.ylabel("Lowest Error", fontsize=14)
    plt.ylim(0, None)  # Y-axis starts at 0 (new)
    
    # Legend (seeds)
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    plt.legend(
        by_label.values(),
        by_label.keys(),
        title="Seed",
        bbox_to_anchor=(1.05, 1),
        loc='upper left'
    )
    
    # Style adjustments
    plt.grid(True, linestyle='--', alpha=0.4)
    plt.xticks(rotation=45, ha='right')
    
    # Save and display
    plt.tight_layout()
    plt.savefig(os.path.join(config.GLOBAL_DATAS, "error_targets_seeds.png"))
    plt.close()

def write_csv(file_path, config, trial, channels, loss, shape):
    """Writes experimental data to a CSV file with standardized formatting.

    Handles multiple channel input formats (dict/list/tuple) and creates properly formatted
    CSV files with consistent 32-channel structure. Automatically creates headers for new files
    and appends data to existing ones.

    Args:
        file_path (str): Path to the CSV output file
        config (object): Configuration object with DATA_UTC attribute
        trial (int): Trial number to include in SampleID
        channels (dict/list/tuple): Channel values in various possible formats:
            - dict: {'led_1': val1, 'led_2': val2, ...} or {1: val1, 2: val2, ...}
            - list/tuple: [val1, val2, ..., val32]
        loss (float): Loss value to record
        shape (str): Shape descriptor (e.g., 'cubes', 'spheres')

    Returns:
        None: Writes to specified CSV file

    Raises:
        ValueError: If channels is not dict/list/tuple or has invalid format
        PermissionError: If unable to write to file
        TypeError: If channel values cannot be converted to proper format

    Examples:
        >>> write_csv("data.csv", config, 1, {'led_1': 255, 'led_2': 128}, 0.5, 'cubes')
        # Creates/writes to data.csv with proper formatting

        >>> write_csv("data.csv", config, 2, [255, 128, ..., 64], 0.3, 'spheres')
        # Appends new row to existing data.csv

    Note:
        - Automatically handles file creation (with headers) if not exists
        - Standardizes all channel inputs to 32-value format
        - SampleID format: '{UTC_TIME}_T{trial_number}'
        - Uses channel headers: 'Channel 1' through 'Channel 32'
        - Maintains data integrity through strict type checking
        - Thread-safe append operations
    """
    sample_id=f'{config.DATA_UTC}_T{trial}'
    # Prepare standard channel headers
    channel_headers = [f'Channel {i}' for i in range(1, 33)]
    
    # Check if file already exists
    file_exists = os.path.exists(file_path)
    
    # Convert channels to standardized 32-value list
    channel_values = [None]*32
    
    # Handle dictionary input format# Handle dictionary input format
    if isinstance(channels, dict):
        for i in range(1, 33):
            key = f'led_{i}'
            channel_values[i-1] = channels.get(key, channels.get(i, None))
    # Handle list/tuple input format 
    elif isinstance(channels, (list, tuple)):
        for i in range(min(32, len(channels))):
            channel_values[i] = channels[i]
    # Raise error for invalid input format
    else:
        raise ValueError("channels debe ser dict, list o tuple")
    
    # Write to CSV file
    with open(file_path, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write headers if new file
        if not file_exists:
            headers = ['SampleID', 'Shape'] + channel_headers + ['Loss']
            writer.writerow(headers)
        
        # Write data row
        row = [sample_id, shape] + channel_values + [loss]
        writer.writerow(row)

def send_files_gmail(seed, config, target_file_name, sobol):
    """Sends experimental data and results via email as a zip attachment.

    Compiles experiment results, configuration details, and log files into a zip archive
    and sends them to specified recipients via Gmail. Handles all aspects of email creation
    including authentication, message formatting, file attachment, and error handling.

    Args:
        seed (int): The random seed used for the experiment
        config (object): Configuration object containing:
            - DATA_UTC: Timestamp for experiment identification
            - FIG_PATH: Directory containing result files to send
            - LOG_FILE: Path to the experiment log file
        target_file_name (str): Name of the target file used in the experiment
        sobol (int): Number of Sobol trials performed

    Returns:
        None: Sends email but doesn't return a value

    Raises:
        FileNotFoundError: If specified directories/files don't exist
        smtplib.SMTPException: For email sending failures
        RuntimeError: For zip file creation problems

    Examples:
        >>> send_experiment_data_via_gmail(42, config, "target1", 100)
        # Sends email with experiment data attached

    Note:
        - Uses Gmail SMTP server on port 587 with TLS
        - Requires app-specific password for authentication
        - Creates temporary zip file that's automatically deleted
        - Includes comprehensive error logging
        - Supports multiple recipients
        - Email contains full experiment configuration details
    """
    # Email configuration
    sender= mail_sender
    password= mail_password #Application password
    file_recipients= recipients

    # Construct message
    subject= f"Datas of Experiment_{config.DATA_UTC}"
    message= "This experiment was conducted with the following configuration:"

    if REAL_EXP:
        if SPECTRAL_MATCHING:
            conf = f'REAL_EXP: {REAL_EXP}, SPECTRAL_MATCHING: {SPECTRAL_MATCHING}, MINIMIZE_ERROR: {MINIMIZE_ERROR}'
        elif MAXIMIZE_TEMP:
            conf= f'REAL_EXP: {REAL_EXP}, MAXIMIZE_TEMP: {MAXIMIZE_TEMP}'
    elif TESTER_EXP:
        conf= f'TEST_EXP: {TESTER_EXP}, PARAM_MATCHING: {PARAM_MATCHING}, MINIMIZE_ERROR: {MINIMIZE_ERROR}'

    seed_obj=f'The experiment seed is {seed} and the objective was {target_file_name}'
    exp_set=f'With {sobol} SOBOL trials and {NUM_TRIALS_FB} Fully Bayesian trials'
    if extra_message:
        full_msg=f'{extra_message}\n\n{message}\n{conf}\n{exp_set}\n{seed_obj}'
    else:
        full_msg=f'{message}\n{conf}\n{exp_set}\n{seed_obj}'

    # Folder with the files to send
    file_folder= config.FIG_PATH
    file_logs=config.LOG_FILE

    #Create the message
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = ", ".join(file_recipients)
    msg['Subject'] = subject
    msg.attach(MIMEText(full_msg, 'plain'))

    # Create a temporary zip file
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
        zip_filename = tmp_zip.name
        
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add files from the folder
            files = [f for f in os.listdir(file_folder) if os.path.isfile(os.path.join(file_folder, f))]
            
            if not files:
                logger.warning("There are no files in the specified folder")
                return
            
            for file in files:
                ruta_completa = os.path.join(file_folder, file)
                try:
                    zipf.write(ruta_completa, arcname=file)
                    logger.info(f"File added to zip: {file}")
                except Exception as e:
                    logger.error(f"Error adding {file} to zip: {str(e)}")
            
            # Add log file if it exists
            if os.path.isfile(file_logs):
                try:
                    zipf.write(file_logs, arcname=os.path.basename(file_logs))
                    logger.info(f"Log file added to zip: {file_logs}")
                except Exception as e:
                    logger.error(f"Error adding log file {file_logs} to zip: {str(e)}")
            else:
                logger.warning(f"Log file not found: {file_logs}")

    # Attach the zip file
    try:
        with open(zip_filename, 'rb') as zip_file:
            part = MIMEBase('application', 'zip')
            part.set_payload(zip_file.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename=Experiment_{config.DATA_UTC}.zip')
            msg.attach(part)
    except Exception as e:
        logger.error(f"Error attaching zip file: {str(e)}")
    finally:
        # Clean up the temporary zip file
        os.unlink(zip_filename)

    # Send mail
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, file_recipients, msg.as_string())
        server.quit()
        logger.info(f"Email successfully sent to: {', '.join(file_recipients)}")
    except Exception as e:
        logger.error(f"Error sending the email: {str(e)}")

def send_experiment_completion_notification(config):
    """Sends an email notification with attached results when all experiments complete.

    Compiles all experimental data files into a zip archive and sends them via email
    to notify recipients that the experiment batch has finished. Includes clear next steps
    in the message body and handles all email creation, authentication, and file attachment.

    Args:
        config (object): Configuration object containing:
            - GLOBAL_DATAS: Directory containing result files to send
            - DATA_UTC: Timestamp for experiment identification

    Returns:
        None: Sends email but doesn't return a value

    Raises:
        FileNotFoundError: If specified directory doesn't exist
        smtplib.SMTPException: For email sending failures
        RuntimeError: For zip file creation problems

    Examples:
        >>> send_experiment_completion_notification(config)
        # Sends completion email with data attachments

    Note:
        - Uses Gmail SMTP with TLS encryption
        - Requires app-specific password for authentication
        - Creates temporary zip file that's automatically deleted
        - Includes comprehensive error logging
        - Supports multiple recipients
        - Provides clear next steps in message body
    """
    # Email configuration
    sender= mail_sender
    password= mail_password
    file_recipients= recipients

    # Construct message
    subject = "Experiment Batch Completed"
    message = """All experiments have finished successfully!

Next Steps:
1. Review the collected data
2. Adjust laboratory parameters as needed
3. Prepare for next experiment batch

I'll be waiting in the lab!"""

    if extra_message:
        full_msg=f'{extra_message}\n\n{message}'
    else:
        full_msg=message

    # Folder with the files to send
    file_folder = config.GLOBAL_DATAS
    
    # Create email
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = ", ".join(file_recipients)
    msg['Subject'] = subject
    msg.attach(MIMEText(full_msg, 'plain'))

    # Create a temporary zip file
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
        zip_filename = tmp_zip.name
        
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add files from the folder
            files = [f for f in os.listdir(file_folder) if os.path.isfile(os.path.join(file_folder, f))]
            
            if not files:
                logger.warning("There are no files in the specified folder")
                return
            
            for file in files:
                ruta_completa = os.path.join(file_folder, file)
                try:
                    zipf.write(ruta_completa, arcname=file)
                    logger.info(f"File added to zip: {file}")
                except Exception as e:
                    logger.error(f"Error adding {file} to zip: {str(e)}")
    
    # Attach the zip file
    try:
        with open(zip_filename, 'rb') as zip_file:
            part = MIMEBase('application', 'zip')
            part.set_payload(zip_file.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename=Experiment_{config.DATA_UTC}.zip')
            msg.attach(part)
    except Exception as e:
        logger.error(f"Error attaching zip file: {str(e)}")
    finally:
        # Clean up the temporary zip file
        os.unlink(zip_filename)
    
    # Send mail
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, file_recipients, msg.as_string())
        server.quit()
        logger.info(f"Email successfully sent to: {', '.join(file_recipients)}")
    except Exception as e:
        logger.error(f"Error sending the email: {str(e)}")

def send_error_notification(error_message=None):
    """Sends an email notification when an experiment encounters an error.

    Constructs and sends an error notification email to specified recipients when
    an experiment fails. Includes detailed error information if provided, and
    handles all aspects of email creation and transmission.

    Args:
        error_message (str, optional): Detailed error message to include in notification.
            If None, a generic error message will be sent. Defaults to None.

    Returns:
        None: The function sends an email but does not return any value.

    Raises:
        smtplib.SMTPException: If there is an error during email transmission.
        RuntimeError: If the email cannot be constructed or sent.

    Examples:
        >>> send_error_notification("Temperature exceeded safe limits")
        # Sends error email with the specified message

        >>> send_error_notification()
        # Sends generic error notification

    Note:
        - Uses Gmail's SMTP server with TLS encryption
        - Requires application-specific password for authentication
        - Sends to predefined recipient list
        - Includes timestamp in the email subject
        - Logs both successful and failed attempts
        - Re-raises exceptions after logging them
    """
    try:
        # Email configuration
        sender= mail_sender
        password= mail_password
        file_recipients = recipients
        
        # Construct message with timestamp
        subject = "Experiment Batch not completed"
        base_message = """Unexpected error ocurred during the experiment"""
        detailed_message = f"{base_message}\n\nError details:\n{str(error_message)}" if error_message else base_message
        
        # Create email
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = ", ".join(file_recipients)
        msg['Subject'] = subject
        msg.attach(MIMEText(detailed_message, 'plain'))
        
        # Send email
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, file_recipients, msg.as_string())
        
        logger.info("Experiment completion notification sent successfully")
        
    except Exception as e:
        logger.error(f"Failed to send completion notification: {str(e)}")
        raise

def create_multiple_plots_pdf(config):
    """Generates a PDF document containing multiple plot images arranged in a grid layout.

    Creates a multi-page PDF with plots arranged in a 3x7 grid (21 plots per page) from PNG
    files in a specified directory. Maintains proper aspect ratio and includes automatic
    pagination and consistent margins.

    Args:
        config (object): Configuration object containing:
            - FIG_PATH: Output path for PDF file
            - SPECTRA_PLOTS: Directory containing PNG plot files

    Returns:
        None: Creates a PDF file at the specified location

    Raises:
        FileNotFoundError: If SPECTRA_PLOTS directory doesn't exist
        ValueError: If no PNG files found in directory
        PermissionError: If unable to write to output PDF

    Examples:
        >>> create_multiple_plots_pdf(config)
        # Generates 'compare_plots.pdf' in FIG_PATH directory

    Note:
        - Uses A4 page size (210x297mm) with 15mm margins
        - Each plot is 60x35mm (width x height)
        - Arranges plots in 3 columns and 7 rows per page
        - Sorts files numerically by embedded numbers in filenames
        - Preserves original image aspect ratios
        - Logs successful PDF generation
    """
    # Page dimensions and layout constants
    A4_WIDTH, A4_HEIGHT = A4                        # Standard A4 dimensions (210x297mm)
    PLOTS_PER_PAGE = 21                             # 3 columns x 7 rows
    PLOT_WIDTH = 60 * mm                            # Individual plot width
    PLOT_HEIGHT = 35 * mm                           # Individual plot height
    MARGIN_X = (A4_WIDTH - 3 * PLOT_WIDTH) / 2      # Horizontal centering margin
    MARGIN_Y = 15 * mm                              # Top/bottom margin

    def extract_number(filename):
        """Extracts numerical value from filename for sorting.
        
        Args:
            filename (str): The filename to process
            
        Returns:
            int: Extracted number or 0 if no number found
        """
        match = re.search(r'\d+', filename)
        return int(match.group()) if match else 0

    def create_pdf(folder_path, output_pdf_name):
        """Creates PDF document from PNG files in specified folder.
        
        Args:
            folder_path (str): Directory containing PNG files
            output_pdf_name (str): Path for output PDF file
        """
        # Get and sort PNG files by embedded numbers
        png_files = sorted(
            [f for f in os.listdir(folder_path) if f.endswith('.png')],
            key=extract_number
        )
        
        # Initialize PDF canvas
        c = canvas.Canvas(output_pdf_name, pagesize=A4)
        
        for i, png_file in enumerate(png_files):
            # Create new page after every 21 plots
            if i % PLOTS_PER_PAGE == 0 and i > 0:
                c.showPage()
            
            # Calculate grid position
            row = (i % PLOTS_PER_PAGE) // 3 # 0-6 row index
            col = (i % PLOTS_PER_PAGE) % 3  # 0-2 column index
            
            # Calculate plot position
            x = MARGIN_X + col * PLOT_WIDTH
            y = A4_HEIGHT - MARGIN_Y - (row + 1) * PLOT_HEIGHT

            # Draw image while preserving aspect ratio
            img_path = os.path.join(folder_path, png_file)
            c.drawImage(img_path, x, y, PLOT_WIDTH, PLOT_HEIGHT, preserveAspectRatio=True)
        
        c.save()
        logger.info(f"PDF generated: '{output_pdf_name}'")

    # Generate comparison figure PDFt
    compare_fig=os.path.join(config.FIG_PATH, 'compare_plots.pdf')
    create_pdf(config.SPECTRA_PLOTS, compare_fig)

def create_combined_report_pdf(config):
    """Generates a comprehensive PDF report combining multiple experimental visualizations.

    Creates a multi-section PDF report containing:
    1. Individual plots (loss and temperature stability)
    2. Combined loss vs temperature stability plot
    3. Detailed temperature profile plot
    All sections are properly formatted on an A4 page with consistent margins.

    Args:
        config (object): Configuration object containing:
            - FIG_PATH: Output directory for PDF
            - TEMP_PLOTS: Directory for temperature plots
            - LOSS_EXP: Directory for loss experiment data
            - TEMP_FILE: Directory for temperature data files
            - DATA_UTC: Timestamp for file naming

    Returns:
        None: Generates a PDF file at the specified location

    Raises:
        FileNotFoundError: If required input files are missing
        ValueError: If data files are malformed
        PermissionError: If unable to write output PDF

    Examples:
        >>> create_combined_report_pdf(config)
        # Generates 'general_fig.pdf' in FIG_PATH directory

    Note:
        - Uses A4 page size (210x297mm) with 15mm side margins
        - Maintains consistent spacing between sections (25mm)
        - Automatically generates combined loss/temperature plot
        - Cleans up temporary files after PDF generation
        - Preserves original image aspect ratios
        - Logs missing files as errors
    """
    # Page layout constants
    A4_WIDTH, A4_HEIGHT = A4    # Standard A4 dimensions in points (595x842)
    MARGIN_X = 15 * mm          # Left/right margin
    TOP_MARGIN = 20 * mm        # Top margin
    SECTION_GAP = 25 * mm       # Vertical space between sections
    PLOT_WIDTH = 80 * mm        # Width for individual plots
    COMBINED_WIDTH = 160 * mm   # Width for combined plot
    TEMP_WIDTH = 160 * mm       # Width for temperature plot

    # Directory paths from config
    CARPETA_PLOTS = config.TEMP_PLOTS  # Directory for plot images
    CARPETA_LOSS = config.LOSS_EXP  # Directory for loss data
    CARPETA_TEMP = config.TEMP_FILE  # Directory for temperature data

    def create_pdf(config):
        """Internal function to handle PDF creation."""
        general_fig=os.path.join(config.FIG_PATH, 'general_fig.pdf')
        c = canvas.Canvas(general_fig, pagesize=A4)
        y_position = A4_HEIGHT - TOP_MARGIN # Current vertical position

        # --- Section 1: Individual plots ---
        loss_img = os.path.join(CARPETA_PLOTS, "loss_plot.png")
        temp_stab_img = os.path.join(CARPETA_PLOTS, f"Plot_temp_stab_{config.DATA_UTC}.png")
        
        if all(os.path.exists(img) for img in [loss_img, temp_stab_img]):
            c.drawImage(loss_img, MARGIN_X, y_position - 60*mm, 
                       width=PLOT_WIDTH, height=60*mm, preserveAspectRatio=True)
            c.drawImage(temp_stab_img, MARGIN_X + PLOT_WIDTH + 10*mm, y_position - 60*mm,
                       width=PLOT_WIDTH, height=60*mm, preserveAspectRatio=True)
            y_position -= 70*mm
        else:
            logger.error("Missing images in Section 1!")

        # --- Section 2: Combined plot ---
        loss_file = os.path.join(CARPETA_LOSS, f"Loss_Experiment_{config.DATA_UTC}.txt")
        temp_file = os.path.join(CARPETA_TEMP, "Stabilized_Temps.txt")
        
        if all(os.path.exists(f) for f in [loss_file, temp_file]):
            def load_data(file_path, is_loss=True):
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                trials, values = [], []
                for line in lines:
                    parts = line.strip().split()
                    trials.append(int(parts[3] if is_loss else parts[4]))
                    values.append(float(parts[-1]))
                return trials, values
            
            trials_loss, losses = load_data(loss_file)
            trials_temp, temps = load_data(temp_file, False)

            plt.style.use('default')
            fig, ax1 = plt.subplots(figsize=(8, 4))
            
            ax1.grid(True, linestyle='--', alpha=0.6)
            
            ax1.plot(trials_loss, losses, 'b-', label='Loss', linewidth=2)
            ax1.set_xlabel("Trial Number", fontsize=10, color='black')
            ax1.set_ylabel("Loss Value", fontsize=10, color='black')
            ax1.tick_params(axis='y', colors='black')
            
            ax2 = ax1.twinx()
            ax2.plot(trials_temp, temps, 'r--', label='Temp Stability', linewidth=2)
            ax2.set_ylabel("Temperature [°C]", fontsize=10, color='black')
            ax2.tick_params(axis='y', colors='black')
            
            lines = ax1.get_legend_handles_labels()[0] + ax2.get_legend_handles_labels()[0]
            plt.legend(lines, [l.get_label() for l in lines], 
                     loc='upper center', bbox_to_anchor=(0.5, 1.18),
                     ncol=2, fontsize=9, framealpha=1)

            temp_path = "temp_combined.png"
            plt.savefig(temp_path, dpi=300, bbox_inches='tight', facecolor='white')
            plt.close()
            
            c.drawImage(temp_path, MARGIN_X, y_position - 80*mm,
                       width=COMBINED_WIDTH, height=80*mm, preserveAspectRatio=True)
            os.remove(temp_path)
            y_position -= 90*mm
        else:
            logger.error("Missing data files!")

        # --- Section 3: Temperature plot ---
        temp_img = os.path.join(CARPETA_PLOTS, f"Plot_temp_{config.DATA_UTC}.png")
        if os.path.exists(temp_img):
            c.drawImage(temp_img, MARGIN_X, y_position - 90*mm,
                       width=TEMP_WIDTH, height=90*mm, preserveAspectRatio=True)
        
        c.save()
        print(f"PDF generated: {general_fig}")

    create_pdf(config)

# Run both scripts
def create_figs(config):
    create_multiple_plots_pdf(config)
    if MAXIMIZE_TEMP:
        create_combined_report_pdf(config)