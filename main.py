#main.py
import logging
from config.path_declarations import PROYECT_BASE_PATHS#, FIG_PATH
from config.experiment_settings import TESTER_EXP, REAL_EXP, SPECTRAL_MATCHING, MAXIMIZE_TEMP, SEED, NUM_TRIALS_SOBOL, target_spec_name, tv_name, sol_spec_name
from modules.utils import create_base_folders, send_files_gmail, send_experiment_completion_notification, send_error_notification
from experiments.test_experiment import tester
from experiments.spectral_matching import real_match
from experiments.maximize_temperature import real_temp
from hardware.G2VPico.G2VPico import G2VPicoController
from figs_creator import create_figs
from config.path_declarations import paths
from modules.utils import parse_error_data, plot_all_targets_errors
import traceback
import sys

def _apagar_g2vpico():
    pico=G2VPicoController()
    pico.turn_off()

def global_exception_handler(exc_type, exc_value, exc_traceback):
    """Catches any unhandled exception in the program."""
    # Logs the error
    tb_formatted="".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logging.critical("Unhandled error", exc_info=(exc_type, exc_value, exc_traceback))
    traceback.print_exception(exc_type, exc_value, exc_traceback)
    
    # Executes emergency sequence
    _apagar_g2vpico()
    
    # Sends email notification
    try:
        error_sum =str(exc_value)
        error_det=f'''Critical error in Experiment:
        Error Summary: {error_sum}

        Error Details: {tb_formatted}'''
        send_error_notification(error_det)
    except Exception as mail_error:
        logging.error(f"Fallo al enviar correo: {str(mail_error)}")
    
    sys.exit(1)  # Termitates the program with an error code

# Sets up the global handler
sys.excepthook = global_exception_handler

def main(seed, config, target_val, sobol):
    # Check if the proyect base folders are created
    print(f'Checking if the proyect base paths: {PROYECT_BASE_PATHS} exists')

    #Creating necesary proyect base folders
    print('Creating necesary proyect base folders')
    create_base_folders(PROYECT_BASE_PATHS)

    if TESTER_EXP:
        tester(seed, config, target_val, sobol)
    elif REAL_EXP:
        if SPECTRAL_MATCHING:
            real_match(seed, config, target_val, sobol)
        elif MAXIMIZE_TEMP:
            real_temp(seed, config, target_val, sobol)
        else:
            print('There is no such experiment')
            
if __name__ == '__main__':
    if TESTER_EXP:
        target_files=tv_name
    elif SPECTRAL_MATCHING:
        target_files=target_spec_name
    elif MAXIMIZE_TEMP:
        target_files=sol_spec_name
    for target_val in target_files:
        for sobol in NUM_TRIALS_SOBOL:
            for seed in SEED:
                for _ in range(1):
                    config=paths(target_val)
                    try:
                        main(seed, config, target_val, sobol)
                        create_figs(config)
                    finally:
                        send_files_gmail(seed, config, target_val, sobol)
    data=parse_error_data(config)
    plot_all_targets_errors(data, config)
    send_experiment_completion_notification(config,sobol)