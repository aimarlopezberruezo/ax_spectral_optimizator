#config/experiment_settings.py
tv_name=[]
target_spec_name=[]
sol_spec_name=[]
PARAM_MATCHING=False
SPECTRAL_MATCHING=False
MINIMIZE_ERROR=False
MAXIMIZE_TEMP=False

'''  
Select whether you want it to be a real experiment or a test one  
'''
REAL_EXP = False
# TRUE: You want to do a real experiment using hardwares
# FALSE: You can't use any hardware but you want to do some experiments as test.
TESTER_EXP = not REAL_EXP


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
#-------------------------------------------------REAL EXP CONFIGURATION-------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------
'''
If it's a real experiment, what do you want to do during the experiment?
'''
if REAL_EXP:
    SPECTRAL_MATCHING = False 
    # TRUE: Experiment where Ax tries to minimize the error between the target and the current trial
    # FALSE: Experiment where Ax tries to maximize the temperature of the TSP01
    MAXIMIZE_TEMP = not SPECTRAL_MATCHING


#------------------------------------------------------------------------------------------------------------------------
#-------------------------------------------- SPECTRAL_MATCHING CONFIGURATION--------------------------------------------
#------------------------------------------------------------------------------------------------------------------------
if SPECTRAL_MATCHING:
    MINIMIZE_ERROR=True
    #target_spec_name=['cubes', 'decahedra', 'rods', 'spheres']
    target_spec_name=['210525a-uv-vis']

#------------------------------------------------------------------------------------------------------------------------
#-------------------------------------------MAXIMIZE_TEMPERATURE CONFIGURATION-------------------------------------------
#------------------------------------------------------------------------------------------------------------------------

if MAXIMIZE_TEMP:
    SOLUTION = False
    # TRUE: During the experiment, there will be solution in the cuvette.
    # FALSE: There will be no solution in the cuvette
    NO_SOLUTION = not SOLUTION
    if SOLUTION:
        wait_time = 400 # Waiting time for temperature stabilization
    elif NO_SOLUTION:
        wait_time = 20

    #sol_spec_name=['Export Data MG_20250410_AuNRs231120A2']
    sol_spec_name=['210525a-uv-vis']

#------------------------------------------------------------------------------------------------------------------------
#----------------------------------------------------AX CONFIGURATION----------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------

'''
How many trials do you want the experiment to have?
'''
# Experiment Duration and Ax information
NUM_TRIALS_SOBOL = [20,15,10,5]
NUM_TRIALS_FB = 5
#SEED = [123, 456, 7890, 349]
SEED = [123,456]

#------------------------------------------------------------------------------------------------------------------------
#---------------------------------------------------LOGS CONFIGURATION---------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------

'''
What level of logs do you want to store?
'''
# Write in uppercase (Matplotlib_LOG_LEVEL in lowercase) the desired log level, choose from:    
    # DEBUG: Technical details (e.g., "Value of X=5", "Iteration 3/10"). Useful only for developers.
    # INFO: Normal events (e.g., "Loading file X", "Process Y completed").
    # WARNING: Unusual but manageable situations (e.g., "File does not exist, a new one will be created").
    # ERROR: Issues that affect operation but do not crash the system (e.g., "Could not read X, using default value").
    # CRITICAL: Severe errors that halt execution (e.g., "Out of memory", "API key not configured").
    
EXP_LOG_LEVEL = "DEBUG"
Matplotlib_LOG_LEVEL = "WARNING"
Pyvisa_LOG_LEVEL = "WARNING"
PIL_LOG_LEVEL = "WARNING"

#------------------------------------------------------------------------------------------------------------------------
#----------------------------------------------- MAIL-SENDER CONFIGURATION-----------------------------------------------
#------------------------------------------------------------------------------------------------------------------------

recipients = ["aimarlopezberruezo@gmail.com", "alopez419@ikasle.ehu.eus"]
#recipients.append("grzelczak.marek@gmail.com")
mail_sender= "aimarlopezberruezo@gmail.com" #Your mail
mail_password= "kuzp aizo lnmu nuuf" #Application password
extra_message='Estoy probando el mensaje extra' # Write relevant information about the experiment, otherwise comment this line