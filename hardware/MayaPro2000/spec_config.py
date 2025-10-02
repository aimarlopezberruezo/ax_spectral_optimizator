#hardware/mayapro2000/spec_config.py
import seabreeze.spectrometers as sb


# List avaiable Devices
devices = sb.list_devices()

if not devices:
    print("ERROR: No connected devices found.")
    raise RuntimeError("No connected devices found.")

try:
    #Initialize the spectrometer (we take the first device from the list)
    spec = sb.Spectrometer(devices[0])
    time_micros=10000
    print(f"Spectrometer initialized successfully. Integration time in micros: {time_micros}")
except Exception as e:
    print(f"ERROR: Error initializing the spectrometer: {e}")
    raise
