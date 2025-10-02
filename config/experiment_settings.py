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
EXP_LOG_LEVEL = "DEBUG"