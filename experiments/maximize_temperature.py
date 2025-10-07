import os
import logging
from config.experiment_settings import *
from modules.utils import *
from modules.ax_integration import AxIntegration
from modules.file_monitor import TempHandler, TxtHandler, JSONHandler, SpecHandler
if REAL_EXP:
    from hardware.G2VPico.G2VPico import G2VPicoController
    from hardware.MayaPro2000.MayaPro2000 import MayaPro2000Controller
    if MAXIMIZE_TEMP:
        from hardware.TSP01.TSP01 import TSP01Controller
from watchdog.observers import Observer


def real_temp(seed, config, target_file_name, sobol):

    observer_txt=None
    observer_json=None
    observer_spec=None
    observer_temp=None
    wrong_limits=False
    pico_init=False

    try:
        # Step 0: Configure logging
        log_level, mat_log_level, pyvisa_log, plog_level= log(config=config)
        logger = logging.getLogger(__name__)
        logger.info("----------Step 0: Log configuration----------")
        logger.info(f'Log levels:\nLOG_LEVEL: {log_level}\nMATPLOTLIB_LOG_LEVEL: {mat_log_level}\nPYVISA_LOG_LEVEL: {pyvisa_log}\nPIL_LOG_LEVEL: {plog_level}')

        # Step 1: Load Tester experiment configuration
        logger.info("----------Step 1: Loading configuration...----------")
        logger.info(f'REAL_EXP: {REAL_EXP}, MAXIMIZE_TEMP: {MAXIMIZE_TEMP}, MINIMIZE_ERROR: {MINIMIZE_ERROR}')

        # Step 2: Load necessary paths
        logger.info("----------Step 2: Loading necessary paths...----------")
        required_paths = [config.TARGET_SPECTRA_FILE, config.CHANNEL_LIMITS_FILE, config.EXP_LIMITS_PATH]
        required_folders = [config.INDI_RESULTS, config.TRIAL_TXT, config.TRIAL_JSON, config.TRIAL_SPECTRA_JSON, 
                            config.EXP_RESULTS_PATH, config.DATA_EXP, config.LOSS_EXP, config.LOG_PATH, config.TEMP_FILE,
                            config.EXP_PLOT_PATH, config.SPECTRA_PLOTS, config.TEMP_PLOTS, config.FIG_PATH, config.GLOBAL_DATAS]
        if not os.path.exists(config.CHANNEL_LIMITS_FILE):
            logger.warning(f'¡{config.CHANNEL_LIMITS_FILE} not found! Creating with write_channel_limits()...')
            logger.info('Initializing pico to get the limits...')
            pico_init=True
            pico=G2VPicoController()
            pico.turn_off()
            pico.clear_channels()
            pico.set_global_intensity(pico.global_intensity)
            pico.write_channel_limits(config.CHANNEL_LIMITS_FILE)
        logger.info("The folders and paths required for this experiment are as follows:")
        logger.info(f'Required_paths:\n {required_paths}')
        logger.info(f'Required_folders:\n {required_folders}')

        # Step 3: Creation of necessary folders
        logger.info("----------Step 3: Creating necessary folders...----------")
        create_folders(required_folders)
        csv_path=os.path.join(config.GLOBAL_DATAS, 'Experiment_results.csv')

        # Step 4: Check channel_limits
        logger.info("----------Step 4: Checking if the edited limits are valid----------")
        
        if not validate_experiment_limits(config.CHANNEL_LIMITS_FILE, config.EXP_LIMITS_PATH):
            logger.error("Experiment limits are invalid. Check experiment_limits.json")
            wrong_limits=True
            raise ValueError("Invalid experiment limits")
        else:
            params=load_ax_params(config.EXP_LIMITS_PATH)
            wrong_limits=False

        # Step 5: Initialize G2VPico, MayaPro2000 and TSP01
        logger.info("----------Step 5: Initializing G2VPico, MayaPro2000 and TSP01----------")
        if not pico_init:
            pico=G2VPicoController()
            pico.turn_off()
            pico.clear_channels()
            pico.set_global_intensity(pico.global_intensity)
            logger.info("G2VPico initializing correctly")
        maya=MayaPro2000Controller()
        try:
            maya.set_integration_time()
            logger.info("MayaPro2000 initializing correctly")
        except Exception as e:
            logger.error(f'MayaPro2000 configuration failed: {str(e)}')
        tsp01=TSP01Controller(config)
        try:
            tsp01.write_header(config.TEMP_FILE_TXT)
            logger.info(f"TSP01 initializing correcty and header writed in {config.TEMP_FILE_TXT}")
        except Exception as e:
            logger.error(f'TSP01 configuration failed: {str(e)}')

        # Step 6: Initialize Ax y monitors
        logger.info("----------Step 6: Initializing Ax and monitors----------")
        target_spec=search_and_load_target_spectra(target_file_name, TV_JSONs, TV_CSVs)
        ax = AxIntegration(
            params=params,
            num_trials_sobol=sobol,
            seed=seed
        )
        # Step up observer for TxtHandler
        txt_handler=TxtHandler()
        observer_txt = Observer()
        observer_txt.schedule(
            txt_handler,
            path=config.TRIAL_TXT, 
            recursive=False
        )
        observer_txt.start()
        logger.info("Observer started (monitoring TxTs folder)")

        # Step up observer for JSONHandler
        json_handler=JSONHandler()
        observer_json=Observer()
        observer_json.schedule(
            json_handler,
            path=config.TRIAL_JSON,
            recursive=False
        )
        observer_json.start()
        logger.info("Observer started (monitoring JSONs folder)")

        # Step up observer for SpecHandler
        spec_handler=SpecHandler()
        observer_spec=Observer()
        observer_spec.schedule(
            spec_handler,
            path=config.TRIAL_SPECTRA_JSON,
            recursive=False
        )
        observer_spec.start()
        logger.info("Observer started (monitoring Spectra_JSONs folder)")

        # Step up observer for TempHandler
        temp_handler=TempHandler()
        observer_temp=Observer()
        observer_temp.schedule(
            temp_handler,
            path=config.STAB_TEMP,
            recursive=False
        )
        observer_temp.start()
        logger.info("Observer started (monitoring Stab_temp folder)")

        #Main loop
        trials = []
        ax_objs=[]
        losses = []
        logger.info("Starting experiment cycle...")
        logger.info("Turning on G2VPico...")
        pico.turn_on()
        try:
            for trial in range(sobol + NUM_TRIALS_FB):
                logger.info(f'--- Trial {trial+1} ---')

                # Step 7: Ax proposes parameters
                parameters, trial_idx=ax.get_next_trial()
                logger.info(f'Parameters generated by Ax: {parameters}')

                # Step 8: Save parameters in Txt
                txt_indi = os.path.join(config.TRIAL_TXT, f'Result_trial_{trial_idx}.txt')
                save_indi_trials(trial_idx, txt_indi, parameters, None)
                logger.debug(f'Trial {trial_idx} saved in TXT: {txt_indi}')

                # Actively wait for the handler to detect the file
                txt_handler.new_txt_event.wait()
                txt_handler.new_txt_event.clear()

                # Step 9: Convert TXT to JSON
                logger.debug(f'Converting Txt to JSON')
                json_data, trial_num = txt_to_json(txt_handler.latest_txt_path)
                if json_data:
                    json_path = os.path.join(config.TRIAL_JSON, f'Result_trial_{trial_idx}.json')
                    with open (json_path, 'w') as f:
                        f.write(json_data)
                    logger.info(f'JSON generated: {json_path}')
                else:
                    logger.error("Error in TXT to JSON conversion")

                # Actively wait for the handler to detect the file
                json_handler.new_json_event.wait()
                json_handler.new_json_event.clear()

                # Step 10: Load JSON and configure G2VPico
                json_pico_data, trial_num = pico.configure_from_txt(txt_handler.latest_txt_path)
                if json_pico_data:
                    pico.set_spectrum(json_pico_data)
                    logger.info(f'Spectrum configured in G2VPico ({trial_num})')
                else:
                    logger.error(f'Error in G2VPico configurationo')
                    continue

                # Step 11: Acquire spectrum and save JSON
                wavelengths, intensities=maya.acquire_spectrum()
                if wavelengths is None or intensities is None:
                    raise ValueError("Error in spectrum acquisition")

                spectra_path=os.path.join(config.TRIAL_SPECTRA_JSON, f'Spectrum_trial_{trial_idx+1}.json')
                maya.save_spectrum_to_json(wavelengths, intensities, spectra_path)
                logger.info(f'Spectrum saved in {spectra_path}')

                # Actively wait for the handler to detect the file
                spec_handler.new_json_event.wait()
                spec_handler.new_json_event.clear()

                # Step 12: For wait_time seconds, we will be collecting data
                logger.info(f'Reading temperature during {wait_time}s...')
                stabilized_temp=tsp01.monitor_and_save_stabilized_temp(trial_idx+1)
                ax_obj=float(stabilized_temp)
                if stabilized_temp is None:
                    logger.error('Error in temperature monitoring')
                
                # Actively wait for the handler to detect the file
                temp_handler.new_txt_event.wait()
                temp_handler.new_txt_event.clear()

                # Step 13: Calculate loss value
                trial_spec=load_event_spectra(spec_handler.latest_json_path)
                loss=calculate_loss(trial_spec, target_spec)
                loss=float(loss)

                # Step 14: Save datas
                ax_objs.append(ax_obj)
                trials.append(trial_idx)
                losses.append(loss)

                txt_total=os.path.join(config.DATA_EXP, f'DB_Experiment_{config.DATA_UTC}.txt')
                loss_file=os.path.join(config.LOSS_EXP, f'Loss_Experiment_{config.DATA_UTC}.txt')

                save_indi_trials(trial_idx, txt_indi, parameters, ax_obj)
                save_total_trials(trial_idx, txt_total, parameters, ax_objs[-1] if ax_objs else 0, loss)
                save_loss(trial_idx, loss_file, losses[-1] if losses else 0)
                write_csv(file_path=csv_path, config=config, trial=trial_idx, channels=parameters, loss=loss, shape=target_file_name)

                # Step 15: Pass the tempertarure to Ax
                ax.complete_trial({"temperature": (ax_obj, 0.0)})

        except Exception as e:
            logger.error(f'Temperatura en Trial {trial_idx+1}: {str(e)}')
            pico.turn_off()
    except KeyboardInterrupt:
        logger.warning('Stopping the experiment...')

    finally:
        pico.turn_off()

        logger.info("Starting final temperature monitoring")
        final_temp = tsp01.monitor_and_save_stabilized_temp (trial_idx+2)

        if final_temp is not None:
            logger.info(f'Final temperature recorded: {final_temp}ºC')
        if wrong_limits==False:
            best_parameters, _ = ax.get_best_parameters()
            logger.info(f'Best founded parameters: {best_parameters}')
            lw_error_file=os.path.join(config.GLOBAL_DATAS, f'Lowest_errors.txt')
            lowest_error_file(lw_error_file, target_file_name, seed, loss_file)
            
            if observer_txt:
                observer_txt.stop()
                observer_txt.join()
            if observer_json:
                observer_json.stop()
                observer_json.join()
            if observer_temp:
                observer_json.stop()
                observer_json.join()
            
            plot_temperature_data(config.TEMP_FILE_TXT, os.path.join(config.TEMP_PLOTS, f'Plot_temp_{config.DATA_UTC}.png'))
            plot_stab_temp(config.STAB_TEMP_TXT, config.DATA_UTC, os.path.join(config.TEMP_PLOTS, f'Plot_temp_stab_{config.DATA_UTC}'))
            plot_spectra_files_json(config.TRIAL_SPECTRA_JSON, config.TARGET_JSON_FILE, config.SPECTRA_PLOTS)
            plot_loss_from_txt(loss_file, config.TEMP_PLOTS)

            logger.info("Visualizations successfully generated")
        else:
            logger.info("No experiment until limits changed")