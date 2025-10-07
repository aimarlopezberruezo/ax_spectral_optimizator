# modules/file_monitor.py
import logging
from threading import Event
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)

class TxtHandler(FileSystemEventHandler):
    """File system event handler for monitoring new .txt file creation.

    Inherits from FileSystemEventHandler to watch for file creation events.
    Signals when new .txt files are detected and stores their paths.

    Attributes:
        new_txt_event (Event): Threading event flag set when new file detected
        latest_txt_path (str): Path of most recently created .txt file

    Example:
        >>> handler = TxtHandler()
        >>> observer.schedule(handler, path='./data')
        >>> handler.new_txt_event.wait()  # Blocks until new .txt appears
        >>> print(handler.latest_txt_path)
    """
    def __init__(self):
        """Initializes the handler with clear event state."""
        self.new_txt_event = Event()
        self.latest_txt_path = None

    def on_created(self, event):
        """Handles file creation events, triggering for .txt files.

        Args:
            event: File system event object containing:
                - src_path (str): Path to created file
                - is_directory (bool): If the event is for a directory

        Sets new_txt_event and updates latest_txt_path when:
        - Event is for a file (not directory)
        - File has .txt extension

        Logs errors during event processing at ERROR level.
        """
        if not event.is_directory and event.src_path.endswith('.txt'):
            try:
                self.latest_txt_path = event.src_path
                self.new_txt_event.set()
                logger.debug(f'Signal aactivated for TXT: {event.src_path}')
            except Exception as e:
                logger.error(f'Error handling created event in TxtHandler: {e}')

class JSONHandler (FileSystemEventHandler):
    """Monitors for new .json file creation events.

    Provides thread-safe notification when new JSON configuration files
    are created in watched directories.

    Attributes:
        new_json_event (Event): Signal flag for new JSON detection
        latest_json_path (str): Path of most recent JSON file

    Note:
        Distinct from SpecHandler despite similar functionality -
        used for different monitoring contexts.
    """
    def __init__(self):
        """Initializes handler with empty path and reset event flag."""
        self.new_json_event = Event()
        self.latest_json_path = None
    
    def on_created(self, event):
        """Processes file creation events for JSON files.

        Args:
            event: File system event with creation details

        Triggers when:
        - Created object is a file
        - File extension is .json

        Updates latest_json_path before setting event flag.
        """
        if not event.is_directory and event.src_path.endswith('.json'):
            try:
                self.latest_json_path = event.src_path
                self.new_json_event.set()
                logger.debug(f'Signal activated for JSON: {event.src_path}')
            except Exception as e:
                logger.error(f'Error handling created event in JSONHandler: {e}')


class SpecHandler (FileSystemEventHandler):
    """Specialized handler for spectrometer JSON configuration files.

    While functionally similar to JSONHandler, this is maintained separately
    to handle spectrometer-specific files with different processing requirements.

    Attributes:
        new_json_event (Event): Notification flag for new files
        latest_json_path (str): Path to most recent spec config file

    Note:
        Intended for spectrometer configuration files only.
        May be extended with validation in future versions.
    """
    def __init__(self):
        """Initializes with default empty state."""
        self.new_json_event = Event()
        self.latest_json_path = None
    
    def on_created(self, event):
        """Handles creation of spectrometer config files.

        Args:
            event: File creation event details

        Only triggers for .json files, matching JSONHandler behavior
        but with separate logging context for spectrometer files.
        """
        if not event.is_directory and event.src_path.endswith('.json'):
            try:
                self.latest_json_path = event.src_path
                self.new_json_event.set()
                logger.debug(f'Signal activated for JSON: {event.src_path}')
            except Exception as e:
                logger.error(f'Error handling created event in SpecHandler: {e}')

class TempHandler(FileSystemEventHandler):
    """Monitors temperature data file creation events.

    Specifically watches for new .txt files containing temperature
    measurements, with identical functionality to TxtHandler but
    maintained separately for semantic clarity.

    Attributes:
        new_txt_event (Event): Notification signal flag
        latest_txt_path (str): Path to newest temperature file

    Note:
        Currently duplicates TxtHandler functionality - consider
        merging if use cases remain identical.
    """
    def __init__(self):
        """Initializes handler with default state."""
        self.new_txt_event = Event()
        self.latest_txt_path = None

    def on_created(self, event):
        """Processes temperature file creation events.

        Args:
            event: File system event details

        Mirrors TxtHandler behavior for temperature-specific files.
        Maintains separate instance for potential future specialization.
        """
        if not event.is_directory and event.src_path.endswith('.txt'):
            try:
                self.latest_txt_path = event.src_path
                self.new_txt_event.set()
                logger.debug(f'Signal activated for TXT: {event.src_path}')
            except Exception as e:
                logger.error(f'Error handling created event in TxtHandler: {e}')