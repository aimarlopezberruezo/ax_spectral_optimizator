#hardware/TSP01/tsp01_config.py
import pyvisa


try:
    print("Initializing TSP01 connection...")
    try:
        rm=pyvisa.ResourceManager()
        resources = rm.list_resources()
        print(f'DEBUG: Avaiable VISA resources: {resources}')
    except pyvisa.VisaIOError as visa_err:
        print(f'ERROR: VISA Error initializing ResourceManager: {str(visa_err)}')
        raise
    except Exception as e:
        print(f'CRITICAL: Unexpected error initializing VISA: {str(e)}')
        raise

    tsp01_resource=None
    try:
        for resource in resources:
            if "M00500554" in resource:
                tsp01_resource=resource
                print(f'Device : {tsp01_resource}')
                break
        if tsp01_resource is None:
            print("ERROR: TSP01 device not found.")
            raise ConnectionError("TSP01 device not found.")
    except Exception as e:
        print(f'ERROR: Error searching for TSP01: {str(e)}')
        raise

    try:
        tsp01=rm.open_resource(tsp01_resource)
        tsp01.timeout=10000 
        print("TSP01 connection established successfully")
        print(f'DEBUG: Connection details: {tsp01}')
    except pyvisa.VisaIOError as visa_err:
        print(f'ERROR: VISA Error opening TSP01 connection: {str(visa_err)}')
        raise
    except Exception as e:
        print(f'CRITICAL: Unexpected error configuring TSP01: {str(e)}')
        raise

except KeyboardInterrupt:
    print("WARNING: TSP01 initialization interrupted by user")
    raise
except Exception as e:
    print(f'CRITICAL: Error establishing connection with TSP01: {e}')
    raise