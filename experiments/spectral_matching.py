import os
from config.experiment_settings import *
from modules.utils import *
from modules.ax_integration import AxIntegration
from modules.file_monitor import TxtHandler, JSONHandler, SpecHandler
if REAL_EXP:
    from hardware.G2VPico.G2VPico import G2VPicoController
    from hardware.MayaPro2000.MayaPro2000 import MayaPro2000Controller
from watchdog.observers import Observer

def real_match(seed, config, target_file_name, sobol):
        
    observer_txt=None
    observer_json=None
    observer_spec=None
    wrong_limits=False
    pico_init=False

    try:
        # Step 1: Load Tester experiment configuration
        print("----------Step 1: Loading configuration...----------")
        print(f'REAL_EXP: {REAL_EXP}, SPECTRAL_MATCHING: {SPECTRAL_MATCHING}, MINIMIZE_ERROR: {MINIMIZE_ERROR}')

        # Step 2: Load necessary paths
        print("----------Step 2: Loading necessary paths...----------")
        required_paths = [config.CHANNEL_LIMITS_FILE, config.EXP_LIMITS_PATH] #TARGET_SPECTRA_FILE, 
        required_folders = [config.INDI_RESULTS, config.TRIAL_TXT, config.TRIAL_JSON, config.TRIAL_SPECTRA_JSON, 
                            config.EXP_RESULTS_PATH, config.DATA_EXP, config.ERROR_EXP, config.LOG_PATH,
                            config.EXP_PLOT_PATH, config.SPECTRA_PLOTS, config.ERROR_PLOTS, config.FIG_PATH, config.GLOBAL_DATAS]
        if not os.path.exists(config.CHANNEL_LIMITS_FILE):
            print(f'WARNING¡{config.CHANNEL_LIMITS_FILE} not found! Creating with write_channel_limits()...')
            print('Initializing pico to get the limits...')
            pico_init=True
            pico=G2VPicoController()
            pico.turn_off()
            pico.clear_channels()
            pico.set_global_intensity(pico.global_intensity)
            pico.write_channel_limits(config.CHANNEL_LIMITS_FILE)
        print("The folders and paths required for this experiment are as follows:")
        print(f'Required_paths:\n {required_paths}')
        print(f'Required_folders:\n {required_folders}')

        # Step 3: Creation of necessary folders
        print("----------Step 3: Creating necessary folders...----------")
        create_folders(required_folders)
        csv_path=os.path.join(config.GLOBAL_DATAS, 'Experiment_results.csv')

        # Step 4: Check channel_limits
        print("----------Step 4: Checking if the edited limits are valid----------")
        
        if not validate_experiment_limits(config.CHANNEL_LIMITS_FILE, config.EXP_LIMITS_PATH):
            print("ERROR: Experiment limits are invalid. Check experiment_limits.json")
            wrong_limits=True
            raise ValueError("Invalid experiment limits")
        else:
            params=load_ax_params(config.EXP_LIMITS_PATH)
            wrong_limits=False

        # Step 5: Inicialize G2VPico y MayaPro2000
        print("----------Step 5: Initializing G2VPico y MayaPro2000----------")
        if not pico_init:
            pico=G2VPicoController()
            pico.turn_off()
            pico.clear_channels()
            pico.set_global_intensity(pico.global_intensity)
            print("G2VPico initializing correctly")
        maya=MayaPro2000Controller()
        maya.set_integration_time()
        print("MayaPro2000 initializing correctly")

        #Step 6: Initialize Ax and monitors
        print("----------Step 6: Initializing Ax and monitors----------")
        target_spec=search_and_load_target_spectra(target_file_name, TV_JSONs, TV_CSVs)
        ax = AxIntegration(
            params=params,
            num_trials_sobol=sobol,
            seed=seed
            )
        # Set up observer for TxtHandler
        txt_handler=TxtHandler()
        observer_txt = Observer()
        observer_txt.schedule(
            txt_handler,
            path=config.TRIAL_TXT, 
            recursive=False
        )
        observer_txt.start()
        print("Observer started (monitoring TXTs folder)")

        # Set up observer for JSONHandler
        json_handler=JSONHandler()
        observer_json=Observer()
        observer_json.schedule(
            json_handler,
            path=config.TRIAL_JSON,
            recursive=False
        )
        observer_json.start()
        print("Observer started (monitoring JSONs folder)")

        # Set up observer for SpecHandler
        spec_handler=SpecHandler()
        observer_spec=Observer()
        observer_spec.schedule(
            spec_handler,
            path=config.TRIAL_SPECTRA_JSON,
            recursive=False
        )
        observer_spec.start()
        print("Observer started (monitoring Spectra_JSONs folder)")

        # Main loop
        trials = []
        ax_objs=[]
        print("Starting experiment cycle...")
        print("Turning on G2VPico...")
        pico.turn_on()
        try:
            for trial in range(sobol + NUM_TRIALS_FB):
                print(f'--- Trial {trial+1} ---')

                # Step 7: Ax proposes parameters
                parameters, trial_idx=ax.get_next_trial()
                print(f'Parameters generated by Ax: {parameters}')

                # Step 8: Save parameters in Txt
                txt_indi = os.path.join(config.TRIAL_TXT, f'Result_trial_{trial_idx}.txt')
                save_indi_trials(trial_idx, txt_indi, parameters, None)
                print(f'DEBUG: Trial {trial_idx} saved in TXT: {txt_indi}')

                # Actively wait for the handler to detect the file
                txt_handler.new_txt_event.wait()
                txt_handler.new_txt_event.clear()
            
                # Step 9: Convert TXT to JSON
                print(f'DEBUG: Converting Txt to JSON')
                json_data, trial_num = txt_to_json(txt_handler.latest_txt_path)
                if json_data:
                    json_path = os.path.join(config.TRIAL_JSON, f'Result_trial_{trial_idx}.json')
                    with open (json_path, 'w') as f:
                        f.write(json_data)
                    print(f'JSON generated: {json_path}')
                else:
                    print("ERROR: Error in TXT to JSON conversion")
            
                # Actively wait for the handler to detect the file
                json_handler.new_json_event.wait()
                json_handler.new_json_event.clear()

                # Step 10: Load JSON and configure G2VPico
                json_pico_data, trial_num = pico.configure_from_txt(txt_handler.latest_txt_path)
                if json_pico_data:
                    pico.set_spectrum(json_pico_data)
                    print(f'Spectrum configured in G2VPico ({trial_num})')
                else:
                    print(f'ERROR: Error in G2VPico configuration')
                    continue

                # Step 11: Acquire spectrum and save JSON
                wavelengths, intensities=maya.acquire_spectrum()
                if wavelengths is None or intensities is None:
                    raise ValueError("Error in spectrum acquisition")

                spectra_path=os.path.join(config.TRIAL_SPECTRA_JSON, f'Spectrum_trial_{trial_idx+1}.json')
                maya.save_spectrum_to_json(wavelengths, intensities, spectra_path)
                print(f'Spectrum saved in {spectra_path}')

                # Actively wait for the handler to detect the file
                spec_handler.new_json_event.wait()
                spec_handler.new_json_event.clear()

                # Step 12: Calculate error
                trial_spec=load_event_spectra(spec_handler.latest_json_path)
                error=calculate_error_spec(trial_spec, target_spec)
                ax_obj=float(error["Variable_error"][0])
                print(f"Error calculated for Trial {trial_num}: {error}")

                # Step 13: Save datas
                ax_objs.append(ax_obj)
                trials.append(trial_idx)

                txt_total=os.path.join(config.DATA_EXP, f'DB_Experiment_{config.DATA_UTC}.txt')
                error_file=os.path.join(config.ERROR_EXP, f'Error_Experiment_{config.DATA_UTC}.txt')

                save_indi_trials(trial_idx, txt_indi, parameters, ax_obj)
                save_total_trials(trial_idx, txt_total, parameters, ax_objs[-1] if ax_objs else 0)
                save_error(trial_idx, error_file, ax_objs[-1] if ax_objs else 0)

                write_csv(file_path=csv_path, config=config, trial=trial_idx, channels=parameters, loss=ax_obj, shape=target_file_name)

                # Step 14: Pass the error to Ax
                ax.complete_trial({"error": (ax_obj, 0.0)})
        except Exception as e:
            print(f'ERROR: Error in Trial {trial_idx+1}: {str(e)}')
            pico.turn_off()
    except KeyboardInterrupt:
        print('WARNING: Stopping the experiment...')

    finally:
        pico.turn_off()
        if wrong_limits==False:
            best_parameters, _ = ax.get_best_parameters()
            print(f'Best founded parameters: {best_parameters}')
            lw_error_file=os.path.join(config.GLOBAL_DATAS, f'Lowest_errors.txt')
            lowest_error_file(lw_error_file, target_file_name, seed, error_file)

            if observer_txt:
                observer_txt.stop()
                observer_txt.join()
            if observer_json:
                observer_json.stop()
                observer_json.join()
            
            save_path=os.path.join(config.ERROR_PLOTS, f'Error_plot_{config.DATA_UTC}.png')
            plot_errors_FB(trials=trials, error=ax_objs, sobol_trials=sobol,best_parameters=best_parameters, save_path=save_path, fecha_utc=config.DATA_UTC, num_trials=NUM_TRIALS_FB, error_file=error_file, config=config)
            plot_spectra_files_json(config.TRIAL_SPECTRA_JSON, config.TARGET_SPECTRA_FILE, config.SPECTRA_PLOTS)

            print("Visualizations successfully generated")
        else:
            print("No experiment until limits changed")