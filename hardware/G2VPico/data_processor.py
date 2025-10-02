#hardware/G2VPico/data_processor.py
import re
import time
import json
import os


def txt_to_json(file_path):

    print(f'Starting text file to JSON conversion: {file_path}')
    
    MAX_ATTEMPTS = 5                # Maximum number of retries
    attempt_count = 0               # Current attempt counter
    retry_delay = 1                 # Wait time between retries (seconds)

    while attempt_count < MAX_ATTEMPTS:
        try:
            attempt_count +=1
            print(f'DEBUG: Attempt {attempt_count}/{MAX_ATTEMPTS} to process the file: {file_path}')

            try:
                with open(file_path, 'r') as file:
                    lines = file.readlines()
                    print(f'DEBUG: File read successfully: {file_path}')
            except FileNotFoundError:
                print(f'ERROR: Critical: File not found at specified path: {file_path}')
                return None, None
            except IOError as e:
                print(f'WARNING: IOError during file reading (attempt {attempt_count}): {str(e)}')
                if attempt_count<MAX_ATTEMPTS:
                    time.sleep(retry_delay)
                    continue
                else:
                    print(f'ERROR: Permanent IOError after {MAX_ATTEMPTS} attempts')
                    return None, None

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

            for line in lines:
                line = line.strip()

                if line.lower().startswith("trial"):
                    try:
                        match = re.search(r"Trial (\d+)", line, re.IGNORECASE)
                        if match:
                            trial_number = match.group(1)
                            print(f'DEBUG: Extracted trial number: {trial_number}')
                        else:
                            print(f'WARNING: Error: Could not extract trial number from line: {line}')
                    except Exception as e:
                        print(f'ERROR: Error processing trial number: {str(e)}')

                if line.lower().startswith("parameters:"):
                    try:
                        param_str = line.split("Parameters:")[1]
                        parameters = eval(param_str)
                        print(f'DEBUG: Extracted parameters: {parameters}')
                    except (IndexError, ValueError, SyntaxError) as e:
                        print(f'ERROR: Parameter parsing failed: {str(e)}')
                        parameters= None
                    except Exception as e:
                        print(f'ERROR: Error evaluating parameters: {str(e)}')
                        parameters = None

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
                print(f'Invalid parameter structure: {str(e)}')
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

def limit_json (channel, limit, file_name):

    print(f"Updating channel limits in {file_name} - Channel: {channel}, Limit: {limit}")
    data=[]

    if os.path.exists(file_name):
        try:
            with open(file_name, "r") as json_file:
                data = json.load(json_file)
                print(f"DEBUG: Successfully loaded existing data from {file_name}")
        except json.JSONDecodeError:
            print(f"WARNING: Corrupted JSON file {file_name}, creating new file. Error: {str(e)}")
            data = []   # Reset data if file is corrupted
        except IOError as e:
            print(f"ERROR: Failed to read {file_name}: {str(e)}")
            return False

    existing_index = next(
        (i for i, item in enumerate(data) 
         if str(item.get("channel")) == str(channel)),
        None
    )

    if existing_index is not None:
        print(f"DEBUG: Updating existing entry for channel {channel}")
        data[existing_index]["limit"] = limit
    else:
        print(f"DEBUG: Creating new entry for channel {channel}")
        data.append({
            "channel": channel,
            "Limit": limit
        })

    try:
        with open(file_name, "w") as json_file:
            json.dump(data, json_file, indent=4)
            print(f"Successfully updated {file_name}")
        return True
        
    except IOError as e:
        print(f"ERROR: Failed to write to {file_name}: {str(e)}")
        return False
    except Exception as e:
        print(f"CRITICAL: Unexpected error while saving {file_name}: {str(e)}")
        return False