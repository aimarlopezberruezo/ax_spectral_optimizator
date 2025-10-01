# modules/file_monitor.py
from threading import Event
from watchdog.events import FileSystemEventHandler


class TxtHandler(FileSystemEventHandler):

    def __init__(self):
        self.new_txt_event = Event()
        self.latest_txt_path = None

    def on_created(self, event):

        if not event.is_directory and event.src_path.endswith('.txt'):
            try:
                self.latest_txt_path = event.src_path
                self.new_txt_event.set()
                print(f'Signal aactivated for TXT: {event.src_path}')
            except Exception as e:
                print(f'ERROR: Error handling created event in TxtHandler: {e}')

class JSONHandler (FileSystemEventHandler):

    def __init__(self):
        self.new_json_event = Event()
        self.latest_json_path = None
    
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.json'):
            try:
                self.latest_json_path = event.src_path
                self.new_json_event.set()
                print(f'Signal activated for JSON: {event.src_path}')
            except Exception as e:
                print(f'ERROR: Error handling created event in JSONHandler: {e}')