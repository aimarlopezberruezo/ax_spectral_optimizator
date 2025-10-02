#hardware/G2VPico/data_processor.py
import logging
import re
import time
import json
import os

logger = logging.getLogger(__name__)

def txt_to_json(file_path):

    logger.info(f'Starting text file to JSON conversion: {file_path}')
    
    MAX_ATTEMPTS = 5                # Maximum number of retries
    attempt_count = 0               # Current attempt counter
    retry_delay = 1                 # Wait time between retries (seconds)

    while attempt_count < MAX_ATTEMPTS:
        try:
            attempt_count +=1
            logger.debug(f'Attempt {attempt_count}/{MAX_ATTEMPTS} to process the file: {file_path}')

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

            for line in lines:
                line = line.strip()

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

def limit_json (channel, limit, file_name):

    logger.info(f"Updating channel limits in {file_name} - Channel: {channel}, Limit: {limit}")
    data=[]

    if os.path.exists(file_name):
        try:
            with open(file_name, "r") as json_file:
                data = json.load(json_file)
                logger.debug(f"Successfully loaded existing data from {file_name}")
        except json.JSONDecodeError:
            logger.warning(f"Corrupted JSON file {file_name}, creating new file. Error: {str(e)}")
            data = []   # Reset data if file is corrupted
        except IOError as e:
            logger.error(f"Failed to read {file_name}: {str(e)}")
            return False

    existing_index = next(
        (i for i, item in enumerate(data) 
         if str(item.get("channel")) == str(channel)),
        None
    )

    if existing_index is not None:
        logger.debug(f"Updating existing entry for channel {channel}")
        data[existing_index]["limit"] = limit
    else:
        logger.debug(f"Creating new entry for channel {channel}")
        data.append({
            "channel": channel,
            "Limit": limit
        })

    try:
        with open(file_name, "w") as json_file:
            json.dump(data, json_file, indent=4)
            logger.info(f"Successfully updated {file_name}")
        return True
        
    except IOError as e:
        logger.error(f"Failed to write to {file_name}: {str(e)}")
        return False
    except Exception as e:
        logger.critical(f"Unexpected error while saving {file_name}: {str(e)}")
        return False