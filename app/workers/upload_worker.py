"""
Background Upload Worker Thread.
Executes batch and queue uploads asynchronously using PySide6 QThread.
Maintains directory structures, calculates speed/ETA, and allows Pause/Resume/Cancel.
"""
import os
import time
from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import QThread

from config.constants import ConflictPolicy, UploadStatus
from app.core.signals import signal_bus
from app.database.db_manager import DatabaseManager
from app.database.models import UploadHistoryItem
from app.services.drive_service import DriveService
from app.services.file_service import FileTask
from app.utils.logger import logger


class UploadWorker(QThread):
    """Worker thread running chunked resumable uploads with pause/resume/cancel."""

    def __init__(
        self,
        drive_service: DriveService,
        db_manager: DatabaseManager,
        tasks: List[FileTask],
        destination_folder_id: str = "root",
        destination_path: str = "My Drive",
        conflict_policy: str = ConflictPolicy.KEEP_BOTH,
        parent=None
    ):
        super().__init__(parent)
        self.drive_service = drive_service
        self.db_manager = db_manager
        self.tasks = tasks
        self.destination_folder_id = destination_folder_id
        self.destination_path = destination_path
        self.conflict_policy = conflict_policy

        self._is_paused = False
        self._is_cancelled = False
        self._folder_hierarchy_cache: Dict[str, str] = {}  # {relative_dir: drive_folder_id}

    def pause(self):
        """Pauses upload loop."""
        self._is_paused = True
        logger.info("Upload paused by user.")
        signal_bus.upload_paused.emit()

    def resume(self):
        """Resumes upload loop."""
        self._is_paused = False
        logger.info("Upload resumed by user.")
        signal_bus.upload_resumed.emit()

    def cancel(self):
        """Cancels upload loop."""
        self._is_cancelled = True
        self._is_paused = False
        logger.info("Upload cancelled by user.")
        signal_bus.upload_cancelled.emit()

    def run(self):
        """Thread entrypoint."""
        total_files = len(self.tasks)
        total_bytes = sum(t.file_size for t in self.tasks)
        
        signal_bus.upload_batch_started.emit(total_files, total_bytes)

        completed_count = 0
        failed_count = 0
        skipped_count = 0
        total_bytes_sent = 0
        batch_start_time = time.time()

        for idx, task in enumerate(self.tasks):
            if self._is_cancelled:
                logger.info("Batch cancelled before processing next file.")
                break

            # Handle pause
            while self._is_paused:
                if self._is_cancelled:
                    break
                time.sleep(0.5)

            if self._is_cancelled:
                break

            filename = task.filename
            file_size = task.file_size
            local_path = task.local_path

            # Determine target parent folder on Drive (preserving directory hierarchy)
            target_parent_id = self._resolve_target_folder(task.relative_path)

            file_start_time = time.time()
            current_file_bytes = 0

            def on_progress(bytes_uploaded: int, file_total: int):
                nonlocal current_file_bytes, total_bytes_sent
                delta = bytes_uploaded - current_file_bytes
                current_file_bytes = bytes_uploaded
                total_bytes_sent += delta

                elapsed_file = max(time.time() - file_start_time, 0.001)
                speed = bytes_uploaded / elapsed_file
                eta = (file_total - bytes_uploaded) / speed if speed > 0 else 0

                elapsed_overall = max(time.time() - batch_start_time, 0.001)
                overall_speed = total_bytes_sent / elapsed_overall
                overall_eta = (total_bytes - total_bytes_sent) / overall_speed if overall_speed > 0 else 0

                signal_bus.upload_file_progress.emit(filename, bytes_uploaded, file_total, speed, eta)
                signal_bus.upload_overall_progress.emit(
                    completed_count, total_files, total_bytes_sent, total_bytes, overall_speed, overall_eta
                )

            try:
                status, drive_file_id, final_name = self.drive_service.upload_file_resumable(
                    local_path=local_path,
                    parent_id=target_parent_id,
                    target_name=filename,
                    conflict_policy=self.conflict_policy,
                    progress_callback=on_progress,
                    is_cancelled=lambda: self._is_cancelled,
                    is_paused=lambda: self._is_paused
                )

                duration = time.time() - file_start_time
                avg_speed = file_size / duration if duration > 0 else 0

                if status == UploadStatus.COMPLETED:
                    completed_count += 1
                    signal_bus.upload_file_completed.emit(filename, drive_file_id, status)
                elif status == UploadStatus.SKIPPED:
                    skipped_count += 1
                    signal_bus.upload_file_completed.emit(filename, drive_file_id, status)
                elif status == UploadStatus.CANCELLED:
                    break

                # Save record to history
                self.db_manager.add_history_record(UploadHistoryItem(
                    filename=final_name or filename,
                    local_path=local_path,
                    drive_file_id=drive_file_id,
                    drive_folder_id=target_parent_id,
                    drive_folder_path=self.destination_path,
                    file_size=file_size,
                    status=status,
                    upload_speed=avg_speed,
                    duration_seconds=duration,
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
                ))

            except Exception as e:
                failed_count += 1
                err_msg = str(e)
                logger.error(f"Failed to upload {filename}: {err_msg}")
                signal_bus.upload_file_failed.emit(filename, err_msg)

                # Save failed record to history
                self.db_manager.add_history_record(UploadHistoryItem(
                    filename=filename,
                    local_path=local_path,
                    drive_file_id=None,
                    drive_folder_id=target_parent_id,
                    drive_folder_path=self.destination_path,
                    file_size=file_size,
                    status=UploadStatus.FAILED,
                    error_message=err_msg,
                    duration_seconds=time.time() - file_start_time,
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
                ))

        # Finalize batch
        signal_bus.upload_batch_finished.emit(completed_count, failed_count, skipped_count)
        signal_bus.history_updated.emit()
        logger.info(f"Batch upload finished. Completed: {completed_count}, Failed: {failed_count}, Skipped: {skipped_count}")

    def _resolve_target_folder(self, relative_path: str) -> str:
        """
        If file is inside nested folders (e.g. 'sub1/sub2/file.txt'),
        creates or retrieves Drive folder hierarchy under destination_folder_id.
        """
        parts = Path(relative_path).parent.parts
        if not parts or parts == (".",):
            return self.destination_folder_id

        rel_dir_key = "/".join(parts)
        if rel_dir_key in self._folder_hierarchy_cache:
            return self._folder_hierarchy_cache[rel_dir_key]

        # Create or resolve folder hierarchy on Google Drive
        target_folder = self.drive_service.create_folder_hierarchy(
            rel_dir_key,
            parent_id=self.destination_folder_id
        )
        target_id = target_folder["id"]
        self._folder_hierarchy_cache[rel_dir_key] = target_id
        return target_id
