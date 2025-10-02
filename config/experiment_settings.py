#config/experiment_settings.py
tv_name=[]
PARAM_MATCHING=False
MINIMIZE_ERROR=False

'''  
Select whether you want it to be a real experiment or a test one (Right now, it can only be a real experiment.)
'''
TESTER_EXP = True


#------------------------------------------------------------------------------------------------------------------------
#-------------------------------------------------TEST EXP CONFIGURATION-------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------

'''
The only available testing experiment is to make the Ax parameters match some target parameters.
'''
if TESTER_EXP:
    PARAM_MATCHING = True
    MINIMIZE_ERROR = True
    tv_name=['target_values'] #Choose the name of the target_file

#------------------------------------------------------------------------------------------------------------------------
#----------------------------------------------------AX CONFIGURATION----------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------

'''
How many trials do you want the experiment to have?
'''
# Experiment Duration and Ax information
NUM_TRIALS_SOBOL = [20,15,10,5]
NUM_TRIALS_FB = 4
#SEED = [123, 456, 7890, 349]
SEED = [123, 456]

#------------------------------------------------------------------------------------------------------------------------
#---------------------------------------------------LOGS CONFIGURATION---------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------

'''
What level of logs do you want to store?
'''
# Write in uppercase the desired log level, choose from:    
    # DEBUG: Technical details (e.g., "Value of X=5", "Iteration 3/10"). Useful only for developers.
    # INFO: Normal events (e.g., "Loading file X", "Process Y completed").
    # WARNING: Unusual but manageable situations (e.g., "File does not exist, a new one will be created").
    # ERROR: Issues that affect operation but do not crash the system (e.g., "Could not read X, using default value").
    # CRITICAL: Severe errors that halt execution (e.g., "Out of memory", "API key not configured").

EXP_LOG_LEVEL = "DEBUG"
Matplotlib_LOG_LEVEL = "WARNING"
PIL_LOG_LEVEL = "WARNING"