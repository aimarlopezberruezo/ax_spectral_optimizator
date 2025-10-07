# modules/ax_integration.py
import logging
from ax.service.ax_client import AxClient, ObjectiveProperties
from ax.modelbridge.generation_strategy import GenerationStrategy, GenerationStep
from ax.modelbridge.factory import Models
from watchdog.observers import Observer
from config.experiment_settings import SPECTRAL_MATCHING, MAXIMIZE_TEMP, PARAM_MATCHING


logger = logging.getLogger(__name__)

class AxIntegration:
    """Facilitates Bayesian optimization experiments using Ax (Adaptive Experimentation).

    Manages the complete optimization lifecycle including:
    - Experiment initialization with different optimization strategies
    - Trial generation and parameter suggestion
    - Result collection and model updating
    - Best parameter extraction

    Args:
        params (list): List of parameter dictionaries defining the search space
        num_trials_sobol (int): Number of initial Sobol sequence trials
        num_trials_fb (int): Number of Fully Bayesian optimization trials (-1 for unlimited)
        trial_json (str, optional): Path to JSON file for trial data persistence
        target_values (dict, optional): Target values for objective matching
        temp_file_path (str, optional): Temporary file path for intermediate results
        seed (int, optional): Random seed for reproducibility
        weights (list, optional): Weights for multi-objective optimization
        target_irradiance (float): Target irradiance value (default: 150)
        tolerance (float): Acceptable error tolerance (default: 0.05)

    Attributes:
        gs (GenerationStrategy): Ax generation strategy combining Sobol and Bayesian steps
        ax_client (AxClient): Main Ax experiment client
        trial_data (dict): Storage for completed trial results
        observer (Observer): File system observer for monitoring changes
        current_trial_index (int): Active trial identifier

    Raises:
        RuntimeError: If experiment initialization fails
        ValueError: For invalid parameter configurations
    """
    def __init__(self, params, num_trials_sobol, seed=None):
        """Initializes the optimization experiment with specified configuration.

        Creates one of three experiment types based on experiment_settings:
        - SPECTRAL_MATCHING: Minimizes spectral error
        - MAXIMIZE_TEMP: Maximizes temperature
        - PARAM_MATCHING: Minimizes parameter error

        Note:
            Sets up a two-phase generation strategy:
            1. Initial Sobol sequence for space exploration
            2. Fully Bayesian optimization for refinement
        """
        try:
            self.current_trial_index = None
            self.running = False
            self.seed=seed

            logger.info('Initializing AxIntegration.')

            self.gs = GenerationStrategy(steps=[
                GenerationStep(model=Models.SOBOL, num_trials=num_trials_sobol, min_trials_observed=3, max_parallelism=1, model_kwargs={"seed": self.seed}),
                GenerationStep(model=Models.FULLYBAYESIAN, num_trials=-1, max_parallelism=1, model_kwargs={})
            ])
            self.ax_client = AxClient(generation_strategy=self.gs)
            
            self.trial_data = {}
            self.observer = Observer()

            if SPECTRAL_MATCHING:
                logger.info("Creating spectra optimization experiment")
                self.ax_client.create_experiment(
                    name="Spectral_Matching",
                    parameters=params,
                    objectives={"error": ObjectiveProperties(minimize=True)}
                )
            elif MAXIMIZE_TEMP:
                logger.info("Creating temperature optimization experiment")
                self.ax_client.create_experiment(
                    name="Temperature_Optimization",
                    parameters=params,
                    objectives={"temperature": ObjectiveProperties(minimize=False)}
                )
            elif PARAM_MATCHING:
                logger.info("Creating parameter optimization experiment")
                self.ax_client.create_experiment(
                    name="Param_Matching",
                    parameters=params,
                    objectives={"error": ObjectiveProperties(minimize=True)}
                )

            logger.debug("AxIntegration initialized successfully")
        except Exception as e:
            logger.critical(f'Error initializing AxIntegration: {str(e)}')
            raise

    def get_next_trial(self):
        """Generates parameters for the next experiment trial.

        Returns:
            tuple: 
                - parameterization (dict): Suggested parameter values
                - trial_index (int): Unique trial identifier

        Raises:
            RuntimeError: If trial generation fails
            StopIteration: When maximum trials reached

        Note:
            Updates current_trial_index for result tracking
        """
        try:
            logger.debug("Requesting next trial parameters")
            parameterization, trial_index = self.ax_client.get_next_trial()
            self.current_trial_index = trial_index
            logger.info(f'Next trial: {parameterization}, Index: {trial_index}')
            return parameterization, trial_index
        except Exception as e:
            logger.error(f'Error getting the next trial: {str(e)}')
            raise

    def complete_trial(self, raw_data):
        """Records trial results and updates the optimization model.

        Args:
            raw_data (dict): Measurement results in format {metric: (value, variance)}

        Raises:
            ValueError: For invalid/missing trial data
            RuntimeError: If model update fails

        Note:
            Clears current_trial_index upon completion
            Stores results in trial_data dictionary
        """
        try:
            if self.current_trial_index is not None:
                logger.info(f'Completing trial #{self.current_trial_index + 1}')
                self.ax_client.complete_trial(
                    trial_index=self.current_trial_index,
                    raw_data=raw_data
                )
                key = list(raw_data.keys())[0]
                self.trial_data[self.current_trial_index] = raw_data[key][0]
                logger.debug(f'Trial #{self.current_trial_index +1} completed successfully')
                self.current_trial_index = None
        except Exception as e:
            logger.error(f"Error completing trial {self.current_trial_index}: {str(e)}")
            raise

    def get_best_parameters(self):
        """Retrieves the best parameters found during optimization.

        Returns:
            tuple:
                - best_parameters (dict): Optimal parameter values
                - values (dict): Corresponding objective values

        Raises:
            RuntimeError: If no completed trials exist
            ValueError: If optimization hasn't converged
        """
        try:
            best_parameters, values = self.ax_client.get_best_parameters()
            logger.info(f'Best parameters found: {best_parameters}')
            return best_parameters, values
        except Exception as e:
            logger.error(f'Error retrieving the best parameters: {str(e)}')
            raise
