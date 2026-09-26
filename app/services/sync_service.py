"""
Auto-Sync File System Monitoring Service using Watchdog.
Detects created/modified files, debounces rapid writes, checks file stability,
and dispatches upload tasks safely without UI freezing or premature uploads.
"""
import os
import threading
import time
from pathlib import Path
from typing import Callable, Dict, Optional, Set

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from app.database.models import SyncJobConfig
from app.utils.file_checker import is_file_stable
from app.utils.logger import logger


class SyncEventHandler(FileSystemEventHandler):
    """Handles directory change events with debounce and write-completion checks."""

    def __init__(
        self,
        job_config: SyncJobConfig,
        on_file_ready: Callable[[SyncJobConfig, str, str], None],
        debounce_seconds: float = 3.0,
        stability_interval: float = 0.5,
        poll_interval: float = 0.2
    ):
        super().__init__()
        self.job_config = job_config
        self.on_file_ready = on_file_ready
        self.debounce_seconds = debounce_seconds
        self.stability_interval = stability_interval
        self.poll_interval = poll_interval
        
        # Debounce tracking: {file_path: (last_event_time, event_type)}
        self._pending_events: Dict[str, Tuple[float, str]] = {}
        self._lock = threading.Lock()
        self._running = True

        # Background worker thread for processing debounced events
        self._worker_thread = threading.Thread(target=self._process_debounced_queue, daemon=True)
        self._worker_thread.start()

    def stop(self):
        """Stops the event handler thread."""
        self._running = False

    def on_created(self, event: FileSystemEvent):
        if event.is_directory:
            return
        self._enqueue_event(event.src_path, "created")

    def on_modified(self, event: FileSystemEvent):
        if event.is_directory or not self.job_config.sync_modified:
            return
        self._enqueue_event(event.src_path, "modified")

    def _enqueue_event(self, path: str, event_type: str):
        with self._lock:
            self._pending_events[path] = (time.time(), event_type)
            logger.debug(f"[Sync: {self.job_config.name}] Detected {event_type} on {path}")

    def _process_debounced_queue(self):
        """Periodically checks pending events after debounce duration."""
        while self._running:
            time.sleep(self.poll_interval)
            now = time.time()
            to_process = []

            with self._lock:
                for path, (event_time, event_type) in list(self._pending_events.items()):
                    if now - event_time >= self.debounce_seconds:
                        to_process.append((path, event_type))
                        del self._pending_events[path]

            for path, event_type in to_process:
                # Verify file exists and is stable (finished copying/writing)
                if not os.path.exists(path):
                    continue

                if is_file_stable(path, check_interval=self.stability_interval, timeout=5.0):
                    logger.info(f"[Sync: {self.job_config.name}] File stable and ready: {path}")
                    try:
                        self.on_file_ready(self.job_config, path, event_type)
                    except Exception as e:
                        logger.error(f"Error handling sync file {path}: {e}")
                else:
                    logger.warning(f"[Sync: {self.job_config.name}] File {path} was not stable within timeout. Re-queuing.")
                    with self._lock:
                        self._pending_events[path] = (time.time(), event_type)


class SyncService:
    """Manages active Watchdog directory observers."""

    def __init__(self, on_file_ready_callback: Callable[[SyncJobConfig, str, str], None]):
        self.on_file_ready_callback = on_file_ready_callback
        self._observers: Dict[int, Observer] = {}
        self._handlers: Dict[int, SyncEventHandler] = {}
        self._lock = threading.Lock()

    def start_job(self, config: SyncJobConfig, debounce_seconds: float = 3.0) -> bool:
        """Starts monitoring a directory for a sync job."""
        with self._lock:
            job_id = config.id
            if job_id in self._observers:
                logger.info(f"Sync job {config.name} (ID: {job_id}) is already active.")
                return True

            local_path = Path(config.local_dir)
            if not local_path.is_dir():
                logger.warning(f"Cannot start sync job {config.name}: Directory does not exist ({local_path})")
                return False

            try:
                handler = SyncEventHandler(
                    job_config=config,
                    on_file_ready=self.on_file_ready_callback,
                    debounce_seconds=debounce_seconds
                )
                observer = Observer()
                observer.schedule(handler, str(local_path), recursive=True)
                observer.start()

                self._observers[job_id] = observer
                self._handlers[job_id] = handler
                logger.info(f"Started monitoring for sync job: {config.name} -> {local_path}")
                return True
            except Exception as e:
                logger.error(f"Failed to start sync observer for job {config.name}: {e}")
                return False

    def stop_job(self, job_id: int):
        """Stops monitoring for a specific job."""
        with self._lock:
            if job_id in self._observers:
                try:
                    self._handlers[job_id].stop()
                    self._observers[job_id].stop()
                    self._observers[job_id].join(timeout=2.0)
                    del self._observers[job_id]
                    del self._handlers[job_id]
                    logger.info(f"Stopped sync job ID {job_id}")
                except Exception as e:
                    logger.error(f"Error stopping sync observer {job_id}: {e}")

    def stop_all(self):
        """Stops all active observers."""
        with self._lock:
            for job_id, observer in list(self._observers.items()):
                try:
                    self._handlers[job_id].stop()
                    observer.stop()
                    observer.join(timeout=2.0)
                except Exception as e:
                    logger.error(f"Error stopping observer {job_id}: {e}")
            self._observers.clear()
            self._handlers.clear()
            logger.info("All sync observers stopped.")

    def is_job_running(self, job_id: int) -> bool:
        """Checks if a job is currently monitored."""
        with self._lock:
            return job_id in self._observers
