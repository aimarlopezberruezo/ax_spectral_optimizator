#config/experiment_settings.py
tv_name=[]
target_spec_name=[]
PARAM_MATCHING=False
SPECTRAL_MATCHING=False
MINIMIZE_ERROR=False

'''  
Select whether you want it to be a real experiment or a test one (Right now, it can only be a real experiment.)
'''
REAL_EXP=False
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
    SPECTRAL_MATCHING = True #Only option for the moment

#------------------------------------------------------------------------------------------------------------------------
#-------------------------------------------- SPECTRAL_MATCHING CONFIGURATION--------------------------------------------
#------------------------------------------------------------------------------------------------------------------------
if SPECTRAL_MATCHING:
    MINIMIZE_ERROR=True
    #target_spec_name=['cubes', 'decahedra', 'rods', 'spheres']
    target_spec_name=['210525a-uv-vis']
    
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