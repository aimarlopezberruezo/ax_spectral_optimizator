# modules/ax_integration.py
from ax.service.ax_client import AxClient, ObjectiveProperties
from ax.modelbridge.generation_strategy import GenerationStrategy, GenerationStep
from ax.modelbridge.factory import Models
from watchdog.observers import Observer
from config.experiment_settings import PARAM_MATCHING

class AxIntegration:

    def __init__(self, params, num_trials_sobol, seed=None):

        try:
            self.current_trial_index = None
            self.running = False
            self.seed=seed

            print('Initializing AxIntegration.')

            self.gs = GenerationStrategy(steps=[
                GenerationStep(model=Models.SOBOL, num_trials=num_trials_sobol, min_trials_observed=3, max_parallelism=1, model_kwargs={"seed": self.seed}),
                GenerationStep(model=Models.FULLYBAYESIAN, num_trials=-1, max_parallelism=1, model_kwargs={})
            ])
            self.ax_client = AxClient(generation_strategy=self.gs)
            
            self.trial_data = {}
            self.observer = Observer()

            if PARAM_MATCHING:
                print("Creating parameter optimization experiment")
                self.ax_client.create_experiment(
                    name="Param_Matching",
                    parameters=params,
                    objectives={"error": ObjectiveProperties(minimize=True)}
                )

            print("AxIntegration initialized successfully")
        except Exception as e:
            print(f'CRITICAL: Error initializing AxIntegration: {str(e)}')
            raise

    def get_next_trial(self):

        try:
            print("Requesting next trial parameters")
            parameterization, trial_index = self.ax_client.get_next_trial()
            self.current_trial_index = trial_index
            print(f'Next trial: {parameterization}, Index: {trial_index}')
            return parameterization, trial_index
        except Exception as e:
            print(f'ERROR: Error getting the next trial: {str(e)}')
            raise

    def complete_trial(self, raw_data):

        try:
            if self.current_trial_index is not None:
                print(f'Completing trial #{self.current_trial_index + 1}')
                self.ax_client.complete_trial(
                    trial_index=self.current_trial_index,
                    raw_data=raw_data
                )
                key = list(raw_data.keys())[0]
                self.trial_data[self.current_trial_index] = raw_data[key][0]
                print(f'Trial #{self.current_trial_index +1} completed successfully')
                self.current_trial_index = None
        except Exception as e:
            print(f"ERRROR: Error completing trial {self.current_trial_index}: {str(e)}")
            raise

    def get_best_parameters(self):

        try:
            best_parameters, values = self.ax_client.get_best_parameters()
            print(f'Best parameters found: {best_parameters}')
            return best_parameters, values
        except Exception as e:
            print(f'ERROR: Error retrieving the best parameters: {str(e)}')
            raise
