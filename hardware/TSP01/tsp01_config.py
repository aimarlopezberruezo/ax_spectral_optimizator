#hardware/TSP01/tsp01_config.py
import pyvisa
import logging

logger= logging.getLogger(__name__)

try:
    logger.info("Initializing TSP01 connection...")
    try:
        rm=pyvisa.ResourceManager()
        resources = rm.list_resources()
        logger.debug(f'Avaiable VISA resources: {resources}')
    except pyvisa.VisaIOError as visa_err:
        logger.error(f'VISA Error initializing ResourceManager: {str(visa_err)}')
        raise
    except Exception as e:
        logger.critical(f'Unexpected error initializing VISA: {str(e)}')
        raise

    tsp01_resource=None
    try:
        for resource in resources:
            if "M00500554" in resource:
                tsp01_resource=resource
                logger.info(f'Device : {tsp01_resource}')
                break
        if tsp01_resource is None:
            logger.error("TSP01 device not found.")
            raise ConnectionError("TSP01 device not found.")
    except Exception as e:
        logger.error(f'Error searching for TSP01: {str(e)}')
        raise

    try:
        tsp01=rm.open_resource(tsp01_resource)
        tsp01.timeout=10000 
        logger.info("TSP01 connection established successfully")
        logger.debug(f'Connection details: {tsp01}')
    except pyvisa.VisaIOError as visa_err:
        logger.error(f'VISA Error opening TSP01 connection: {str(visa_err)}')
        raise
    except Exception as e:
        logger.critical(f'Unexpected error configuring TSP01: {str(e)}')
        raise

except KeyboardInterrupt:
    logger.warning("TSP01 initialization interrupted by user")
    raise
except Exception as e:
    logger.critical(f'Error establishing connection with TSP01: {e}')
    raise