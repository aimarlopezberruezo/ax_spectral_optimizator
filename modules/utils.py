#modules/utils.py
import matplotlib.pyplot as plt
import json
import re
import numpy as np
import time
import logging
import matplotlib
import os
import csv
from datetime import datetime, timedelta
from matplotlib.dates import DateFormatter
from config.experiment_settings import *
from config.path_declarations import *


def plot_errors_FB(trials, error, sobol_trials, best_parameters, save_path, fecha_utc, num_trials, error_file, is_temp=False, config=None):

    print('Starting the generation of the error plot')

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
            print(f"WARNING: Error formatting the dictionaries: {str(e)}")
            best_parameters_text = "Not available"

        try:
            best_trial, min_error = find_lowest_error(error_file)
            print(f'Best trial found: {best_trial} with error: {min_error}')
        except Exception as e:
            print(f"ERROR: Error finding the best trial: {str(e)}")
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
            print(f'Plot saved at: {save_path}')
            plt.close()
        except Exception as e:
            print(f"ERROR: Error saving the plot: {str(e)}")
            raise

        print('Plot generated successfully')

    except Exception as e:
        print(f"ERROR: Error in the function plot_errors_FB: {str(e)}")
        raise

def format_dict(d):

    print(f'Starting dictionary formatting: {d}')   
    try:
        formatted_text = "\n".join([f"{k}: {v}" for k, v in d.items()])
        print(f'Dictionary formatted successfully: {formatted_text}')
        return formatted_text
    except AttributeError as e:
        print(f"ERROR: Error: The argument is not a dictionary. Details: {str(e)}")
        raise
    except Exception as e:
        print(f"ERROR: Unexpected error formatting the dictionary: {str(e)}")
        raise

def find_lowest_error(error_file):
    
    print(f'Starting search for the trial with the lowest error in the file: {error_file}')
    
    min_error = float('inf')
    min_trial = None

    try:
        with open(error_file, 'r', encoding='cp1252') as file:
            print(f'File opened successfully: {error_file}')
            
            for line in file:
                if line.startswith("Error of Trial"):
                    try:
                        parts = line.split(" is Error: ")
                        trial_number = int(parts[0].split(" ")[-1])
                        error_value = float(parts[1])
                        
                        if error_value < min_error:
                            min_error = error_value
                            min_trial = trial_number
                            print(f'New minimum found: Trial {min_trial}, Error {min_error}')
                    except (IndexError, ValueError) as e:
                        print(f"WARNING: Error processing the line: {line.strip()}. Details: {str(e)}")
                        continue

        if min_trial is None:
            print("WARNING: No valid trials were found in the file.")
        else:
            print(f'Trial with the lowest error found: {min_trial}, Error: {min_error}')

        return min_trial, min_error

    except FileNotFoundError:
        print(f"ERROR: File not found: {error_file}")
        raise
    except Exception as e:
        print(f"ERROR: Unexpected error processing the file {error_file}: {str(e)}")
        raise

def find_lowest_loss(loss_file):

    print(f'Starting search for the trial with the lowest loss in the file: {loss_file}')
    
    min_error = float('inf')
    min_trial = None

    try:
        with open(loss_file, 'r', encoding='cp1252') as file:
            print(f'File opened successfully: {loss_file}')
            
            for line in file:
                if line.startswith("Loss of Trial"):
                    try:
                        parts = line.split(" is: ")
                        trial_number = int(parts[0].split(" ")[-1])
                        error_value = float(parts[1])
                        
                        if error_value < min_error:
                            min_error = error_value
                            min_trial = trial_number
                            print(f'New minimum found: Trial {min_trial}, Error {min_error}')
                    except (IndexError, ValueError) as e:
                        print(f"WARNING: Error processing the line: {line.strip()}. Details: {str(e)}")
                        continue

        if min_trial is None:
            print("WARNING: No valid trials were found in the file.")
        else:
            print(f'Trial with the lowest loss found: {min_trial}, Loss: {min_error}')

        return min_trial, min_error

    except FileNotFoundError:
        print(f"ERROR: File not found: {loss_file}")
        raise
    except Exception as e:
        print(f"ERROR: Unexpected error processing the file {loss_file}: {str(e)}")
        raise
        
def load_target_values(file_path):

    print(f'Starting to load target values from: {file_path}')
    
    try:
        with open(file_path, "r") as file:
            print(f'JSON file opened successfully: {file_path}')
            datos = json.load(file)
            print(f'JSON data loaded: {datos}')
    except FileNotFoundError:
        print(f"ERROR: File not found: {file_path}")
        raise
    except json.JSONDecodeError as e:
        print(f"ERROR: Error decoding the JSON file {file_path}: {str(e)}")
        raise
    except Exception as e:
        print(f"ERROR: Unexpected error while loading the file {file_path}: {str(e)}")
        raise

    try:
        target_values = {f"led {int(item['channel'])}": item['value'] for item in datos}
        print(f'Target values successfully loaded from: {file_path}')
        return target_values
    except KeyError as e:
        print(f"ERROR: Error: The JSON file is not in the expected format. Missing key: {str(e)}")
        raise
    except Exception as e:
        print(f"ERROR: Unexpected error while processing JSON data: {str(e)}")
        raise

def save_indi_trials(i, save_path, parameterization, ax_obj):

    print(f'Starting to save trial {i+1} results in: {save_path}')
    
    try:
        with open(save_path, "w") as file:
            print(f'File opened successfully for writing: {save_path}')
            file.write(f"Trial {i+1}\n")
            file.write(f"Parameters: {parameterization}\n")
            if MINIMIZE_ERROR:
                file.write(f"Error: {ax_obj}\n")
            print(f'Data written successfully to the file: {save_path}')
        
        print(f'Trial {i+1} results saved successfully in: {save_path}')
    except IOError as e:
        print(f"ERROR: I/O error while saving trial {i+1} in {save_path}: {str(e)}")
        raise
    except Exception as e:
        print(f"ERROR: Unexpected error while saving trial {i+1} in {save_path}: {str(e)}")
        raise

def save_total_trials(i, save_path, parameterization, ax_obj, loss=None):

    print(f'Starting to save trial {i+1} results in: {save_path}')
    
    try:
        with open(save_path, "a") as file:
            print(f'File opened successfully for writing (append mode): {save_path}')
            file.write(f"Trial {i+1}\n")
            file.write(f"Parameters: {parameterization}\n")
            if MINIMIZE_ERROR:
                file.write(f"Error: {ax_obj}\n")
            elif loss:
                file.write(f'Loss: {loss}')
            print(f'Trial {i+1} data written successfully to the file: {save_path}')
        
        print(f'Trial {i+1} results saved successfully in: {save_path}')
    except IOError as e:
        print(f"ERROR: I/O error while saving trial {i+1} in {save_path}: {str(e)}")
        raise
    except Exception as e:
        print(f"ERROR: Unexpected error while saving trial {i+1} in {save_path}: {str(e)}")
        raise

def save_error(i, save_path, current_error): 

    print(f'Starting to save trial {i+1} error in: {save_path}')
    
    try:
        with open(save_path, "a") as file:
            print(f'File opened successfully for writing (append mode): {save_path}')
            file.write(f"Error of Trial {i+1} is Error: {current_error}\n")
            print(f'Trial {i+1} error written successfully to the file: {save_path}')
        
        print(f'Trial {i+1} error saved successfully in: {save_path}')
    except IOError as e:
        print(f"ERROR: I/O error while saving trial {i+1} error in {save_path}: {str(e)}")
        raise
    except Exception as e:
        print(f"ERROR: Unexpected error while saving trial {i+1} error in {save_path}: {str(e)}")
        raise
        
def txt_to_json(file_path):

    print(f'Starting text file to JSON conversion: {file_path}')
    
    MAX_ATTEMPTS = 5
    attempt_count = 0
    retry_delay = 1

    while attempt_count < MAX_ATTEMPTS:
        try:
            attempt_count +=1
            print(f'Attempt {attempt_count}/{MAX_ATTEMPTS} to process the file: {file_path}')
            
            #1. File Reading
            try:
                with open(file_path, 'r') as file:
                    lines = file.readlines()
                    print(f'File read successfully: {file_path}')
            except FileNotFoundError:
                print(f'ERROR: Critical: File not found at specified path: {file_path}')
                return None, None
            except IOError as e:
                print(f'WARNING: IOError during file reading (attempt {attempt_count}): {str(e)}')
                if attempt_count<MAX_ATTEMPTS:
                    time.sleep(retry_delay)
                    continue
                else:
                    print(f'ERRORPermanent IOError after {MAX_ATTEMPTS} attempts')
                    return None, None
                
            #2. Empty File Check
            if not lines:
                print(f'WARNING: The file is empty, retrying... (Attempt {attempt_count + 1}/{MAX_ATTEMPTS})')
                if attempt_count<MAX_ATTEMPTS:
                    time.sleep(retry_delay)
                    continue
                else:
                    print('ERROR: Failed: File remains empty after retries')
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
                            print(f'Extracted trial number: {trial_number}')
                        else:
                            print(f'WARNING: Error: Could not extract trial number from line: {line}')
                    except Exception as e:
                        print(f'ERROR: Error processing trial number: {str(e)}')

                #Parameters Extraction
                if line.lower().startswith("parameters:"):
                    try:
                        param_str = line.split("Parameters:")[1]
                        parameters = eval(param_str)
                        print(f'Extracted parameters: {parameters}')
                    except (IndexError, ValueError, SyntaxError) as e:
                        print(f'ERROR: Parameter parsing failed: {str(e)}')
                        parameters= None
                    except Exception as e:
                        print(f'ERROR: Error evaluating parameters: {str(e)}')
                        parameters = None

            #4. Validation and Conversion
            if not trial_number:
                print('ERROR: No valid trial number found in file')
                return None, None
                
            if not parameters:
                print('ERROR: No valid parameters found in file')
                return None, None
            
            try:
                data = [{"channel": re.search(r'\d+', channel).group(), "value": value} for channel, value in parameters.items()]
                json_data = json.dumps(data, indent=4)
                print(f'File successfully converted to JSON: {file_path}')
                return json_data, trial_number
            except (AttributeError, TypeError) as e:
                print(f'ERROR: Invalid parameter structure: {str(e)}')
                return None, None
            except Exception as e:
                print(f'ERROR: Unexpected error during JSON conversion: {str(e)}')
                return None, None

        except FileNotFoundError:
            print(f'ERROR: File not found: {file_path}')
            return None, None
        except Exception as e:
            print(f'CRITICAL: Unexpected error while processing the file {file_path}: {e}')
            if attempt_count<MAX_ATTEMPTS:
                time.sleep(retry_delay)
                continue
            else:
                print(f'ERROR: Permanent failure after {MAX_ATTEMPTS} attempts')
                return None, None
            
    print(f'ERROR: Failed to process the file after {MAX_ATTEMPTS} attempts: {file_path}')
    return None, None
    
def calculate_error(parameterization, target_values):

    print(f'Starting error calculation between parameterization and target_values')
    
    if isinstance(parameterization, str):
        with open(parameterization, 'r') as f:
            trial_data = json.load(f)
        parameterization={f"led {item['channel']}": item['value'] for item in trial_data}
    
         
    try:
        # Checking key matching
        if set(parameterization.keys()) != set(target_values.keys()):
            print(f'WARNING: Keys of parameterization and target_values do not match: {parameterization.keys()} vs {target_values.keys()}')

        keys = parameterization.keys()
        obj1 = np.array([parameterization[k] for k in keys])
        obj2 = np.array([target_values[k] for k in keys])
        print(f'Parameterization values: {obj1}')
        print(f'Target values: {obj2}')

        # Normalizing values
        obj1_norm = (obj1 - np.min(obj1)) / (np.max(obj1) - np.min(obj1))
        obj2_norm = (obj2 - np.min(obj2)) / (np.max(obj2) - np.min(obj2))
        print(f'Normalized parameterization values: {obj1_norm}')
        print(f'Normalized target values: {obj2_norm}')

        # Calculating error
        norm_error = np.linalg.norm(obj1_norm - obj2_norm)
        print(f'Calculated error: {norm_error}')

        return {"Variable_error": (norm_error, 0.0)}

    except Exception as e:
        print(f'ERROR: Unexpected error while calculating error: {str(e)}')
        raise

def validate_experiment_limits(real_path, experiment_path):

    # Load JSON files
    with open(real_path, 'r') as f:
        real_limits = json.load(f)

    with open(experiment_path, 'r') as f:
        experiment_limits = json.load(f)

    # Create quick-access dictionary by channel
    real_dict = {entry['channel']: entry['Limit'] for entry in real_limits}

    print("---- LIMIT VALIDATION ----")
    errores = False

    for entry in experiment_limits:
        ch = entry['channel']
        lower = entry['Lower-limit']
        upper = entry['Upper-limit']
        real_limit = real_dict.get(ch)

        # Integer type validation
        if not isinstance(lower, int):
            print(f"WARNING: Channel {ch}: ERROR - Lower-limit = {lower} is not an integer. It must be an integer number.")
            errores = True

        if not isinstance(upper, int):
            print(f"WARNING: Channel {ch}: ERROR - Upper-limit = {upper} is not an integer. It must be an integer number.")
            errores = True

        # Range validation
        if lower < 0:
            print(f"WARNING: Channel {ch}: ERROR - Lower-limit = {lower} is less than 0. It must be ≥ 0.")
            errores = True

        if upper > real_limit:
            print(f"WARNING: Channel {ch}: ERROR - Upper-limit = {upper} exceeds the actual limit ({real_limit}). It must be ≤ {real_limit}.")
            errores = True

    if not errores:
        print("All limits are valid.")
        return True
    return False

def create_folders(paths):

    for path in paths:
        try:
            os.makedirs(path, exist_ok=True)
            print(f"Folder created: {path}")
        except Exception as e:
            print(f"ERROR: Error creating folder {path}: {str(e)}")
            raise

def create_base_folders(paths):

    for path in paths:
        try:
            os.makedirs(path, exist_ok=True)
        except Exception as e:
            print(f"ERROR: Error creating folder {path}: {str(e)}")

def load_ax_params(experiment_limits_path):

    print(f"Loading AX parameters from: {experiment_limits_path}")
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
        print(f"AX parameters generated: {parametros_ax[:2]}...")  # Log primeros 2 para ejemplo
        return parametros_ax
    except Exception as e:
        print(f"ERROR: Error loading AX parameters: {str(e)}")
        raise

def plot_parameter_comparison(trial_json_dir, target_values, save_path=None):

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
            print(f"Plot saved in {output_file}")
        else:
            plt.show()

def channel_test_limits(config):

    # Create channel list with limit 3300
    canales = [{"channel": i, "Limit": 3300} for i in range(1, 33)]

    # Save to JSON file
    with open(config.CHANNEL_SIM_LIMITS_FILE, 'w') as f:
        json.dump(canales, f, indent=4)

    print(f"File successfully generated: {config.CHANNEL_SIM_LIMITS_FILE}")

def search_and_load_target_values(file_name, json_dir, csv_dir):

    json_path = os.path.join(json_dir, f"{file_name}.json")
    csv_path = os.path.join(csv_dir, f"{file_name}.csv")

    if os.path.isfile(json_path):
        print(f"JSON file founded: {json_path}")
        return load_target_values(json_path)

    elif os.path.isfile(csv_path):
        print(f"CSV file founded: {csv_path}, converting to JSON...")
        data = csv_to_json_like_reference(csv_path, json_path)
        return load_target_values(json_path)

    else:
        print("ERROR: No target_values in .json o .csv format")
        raise FileNotFoundError("No target_values in json o csv.")
        
def csv_to_json_like_reference(csv_path, json_output_path):

    result = []

    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        rows = list(reader)

        if TESTER_EXP:
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

    if TESTER_EXP:
        _,min_error=find_lowest_error(error_file)
    else:
        _,min_error=find_lowest_loss(error_file)
    with open(lw_error_file, 'a') as file:
        print(f'File opened successfully for writing (append mode): {lw_error_file}')
        file.write(f'Target --> {target}\nSeed --> {seed}\nLowest_error --> {min_error}\n')
        print(f'Lowest error written successfully to the file: {lw_error_file}, {min_error}')

def parse_error_data(config):

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