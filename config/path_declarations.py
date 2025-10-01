#config/path_declarations.py
import os
from datetime import datetime

BASE_DIR_PATH=os.path.abspath(os.path.join(os.getcwd(), '..'))
#print(BASE_DIR_PATH)
SRC_DIR_PATH = os.path.join(BASE_DIR_PATH, 'src')
DOC_DIR_PATH = os.path.join(BASE_DIR_PATH, 'doc')
RESULTS_DIR_PATH = os.path.join(BASE_DIR_PATH, 'results')
DATA_DIR_PATH = os.path.join(BASE_DIR_PATH, 'data')
DATA_RAW_PATH = os.path.join(DATA_DIR_PATH, 'raw_data')
DATA_TV_PATH = os.path.join(DATA_DIR_PATH, 'Target_values')
TV_JSONs = os.path.join(DATA_TV_PATH, 'JSONs')
TV_CSVs = os.path.join(DATA_TV_PATH, 'CSVs')

DOC_DRAFT_PATH = os.path.join(DOC_DIR_PATH, 'draft')
DOC_REPORTS_PATH = os.path.join(DOC_DIR_PATH, 'reports')

RESULTS_DB_PATH = os.path.join(RESULTS_DIR_PATH, 'DB')
RESULTS_FIGS_PATH = os.path.join(RESULTS_DIR_PATH, 'figs')
RESULTS_PLOT_PATH = os.path.join(RESULTS_DIR_PATH, 'plots')
GLOBAL_DATA_UTC = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

PROYECT_BASE_PATHS = [SRC_DIR_PATH, 
                      DATA_DIR_PATH, DATA_RAW_PATH, DATA_TV_PATH, TV_JSONs, TV_CSVs,
                      DOC_DIR_PATH, DOC_DRAFT_PATH, DOC_REPORTS_PATH, 
                      RESULTS_DIR_PATH, RESULTS_DB_PATH, RESULTS_FIGS_PATH, RESULTS_PLOT_PATH]

class paths:
    def __init__(self, target_file_name):

        self.target_file_name=target_file_name
        # Current data and time in UTC format
        self.DATA_UTC = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        # Individual results paths
        self.INDI_RESULTS = os.path.join(RESULTS_DB_PATH, 'Individual', f"Experiment_{self.DATA_UTC}")
        self.TRIAL_TXT = os.path.join(self.INDI_RESULTS, 'Trial_TXTs')
        self.TRIAL_JSON = os.path.join(self.INDI_RESULTS, 'Trial_JSONs')
        self.TRIAL_SPECTRA_JSON = os.path.join (self.INDI_RESULTS, 'Trial_Spectra_JSONs')
        self.STAB_TEMP = os.path.join(self.INDI_RESULTS, 'Stab_Temps')

        # Experimets paths
        self.EXP_RESULTS_PATH= os.path.join(RESULTS_DB_PATH, 'Experiments', f'Experiment_{self.DATA_UTC}')
        self.DATA_EXP = os.path.join(self.EXP_RESULTS_PATH, 'Datas')
        self.ERROR_EXP = os.path.join(self.EXP_RESULTS_PATH, 'Error')
        self.LOSS_EXP = os.path.join(self.EXP_RESULTS_PATH, 'Loss')
        self.TEMP_FILE = os.path.join(self.EXP_RESULTS_PATH, 'Temp')
        self.LOG_PATH = os.path.join(self.EXP_RESULTS_PATH, 'Logs', f'Experiment_{self.DATA_UTC}.log')
        self.EXP_LIMITS_PATH = os.path.join(SRC_DIR_PATH, 'config', 'experiment_limits.json')

        # Path for graphics
        self.EXP_PLOT_PATH = os.path.join(RESULTS_PLOT_PATH, 'Experiment_plots', f'Exp_plots_{self.DATA_UTC}')
        self.TEMP_PLOTS = os.path.join(self.EXP_PLOT_PATH, 'Temp_plots')
        self.SPECTRA_PLOTS = os.path.join(self.EXP_PLOT_PATH, 'Spectra_plots')
        self.ERROR_PLOTS = os.path.join(self.EXP_PLOT_PATH, 'Error_plots')

        # Data path
        self.TARGET_VALUES_FILE = os.path.join(DATA_TV_PATH, f'{self.target_file_name}.json')
        self.TARGET_SPECTRA_FILE = os.path.join(DATA_TV_PATH, 'JSONs', f'{self.target_file_name}.json')
        self.CHANNEL_SIM_LIMITS_FILE = os.path.join(DATA_DIR_PATH, 'channel_limits.json')
        self.CHANNEL_LIMITS_FILE = os.path.join(DATA_DIR_PATH, 'real_channel_limits.json')
        self.TARGET_CSV_FILE = os.path.join(DATA_TV_PATH, 'CSVs', f'{self.target_file_name}.csv')
        self.TARGET_JSON_FILE = os.path.join(DATA_TV_PATH, 'JSONs', f'{self.target_file_name}.json')
        self.GLOBAL_DATAS = os.path.join(DATA_DIR_PATH, 'Global_Exps', f'Global_Exp_{GLOBAL_DATA_UTC}')

        #Temps path
        self.TEMP_FILE_TXT = os.path.join(self.TEMP_FILE, f'Temp_Experiment_{self.DATA_UTC}.txt')
        self.STAB_TEMP_TXT = os.path.join(self.TEMP_FILE, 'Stabilized_Temps.txt')

        # Logging configuration
        self.LOG_PATH = os.path.join(self.EXP_RESULTS_PATH, 'Logs')
        self.LOG_FILE = os.path.join(self.LOG_PATH, f'Experiment_{self.DATA_UTC}.log')

        self.FIG_PATH = os.path.join(RESULTS_FIGS_PATH, f'EXP_{self.DATA_UTC}')

