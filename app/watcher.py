import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from app.processor import process_file


class GeminiKPIHandler(FileSystemEventHandler):
    def __init__(self, settings, ui):
        self.settings = settings
        self.ui       = ui

    def on_created(self, event):
        if not event.is_directory:
            threading.Thread(
                target=process_file,
                args=(event.src_path, self.settings, self.ui),
                daemon=True,
            ).start()


class WatcherDaemon:
    def __init__(self, ui):
        self.ui       = ui
        self.observer = None
        self.running  = False

    def start(self, settings) -> None:
        if self.running:
            return
        self.observer = Observer()
        self.observer.schedule(
            GeminiKPIHandler(settings, self.ui),
            settings.get('WATCH_FOLDER'),
            recursive=False,
        )
        self.observer.start()
        self.running = True
        self.ui.log("📡 File watcher daemon started.", "info")

    def stop(self) -> None:
        if not self.running:
            return
        self.observer.stop()
        self.observer.join()
        self.running = False
        self.ui.log("🛑 File watcher daemon stopped.", "warn")
