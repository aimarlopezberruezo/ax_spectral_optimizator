#main.py
import logging
from config.path_declarations import PROYECT_BASE_PATHS#, FIG_PATH
from config.experiment_settings import TESTER_EXP, SEED, NUM_TRIALS_SOBOL, tv_name
from modules.utils import create_base_folders
from experiments.test_experiment import tester
from config.path_declarations import paths
from modules.utils import parse_error_data, plot_all_targets_errors

def main(seed, config, target_val, sobol):
    # Check if the proyect base folders are created
    print(f'Checking if the proyect base paths: {PROYECT_BASE_PATHS} exists')

    #Creating necesary proyect base folders
    print('Creating necesary proyect base folders')
    create_base_folders(PROYECT_BASE_PATHS)

    if TESTER_EXP:
        tester(seed, config, target_val, sobol)

if __name__ == '__main__':
    if TESTER_EXP:
        target_files=tv_name
    for target_val in target_files:
        for sobol in NUM_TRIALS_SOBOL:
            for seed in SEED:
                for _ in range(1):
                    config=paths(target_val)
                    main(seed, config, target_val, sobol)
    data=parse_error_data(config)
    plot_all_targets_errors(data, config)
