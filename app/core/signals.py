"""
Central Signal Bus for decoupled Qt communication between worker threads, services, and UI.
"""
from PySide6.QtCore import QObject, Signal


class SignalBus(QObject):
    """Singleton signal hub."""

    # Auth signals
    # is_authenticated, user_display_name, email, quota_dict
    auth_status_changed = Signal(bool, str, str, object)
    auth_error_occurred = Signal(str)

    # Destination & Folder signals
    # folder_id, folder_name, folder_path
    destination_selected = Signal(str, str, str)
    # folder_id, folder_name, parent_id
    folder_created = Signal(str, str, str)
    folder_tree_refreshed = Signal()

    # Upload Signals
    # total_files, total_bytes
    upload_batch_started = Signal(int, int)
    # item_id/filename, bytes_sent, file_size, speed_bps, eta_seconds
    upload_file_progress = Signal(str, int, int, float, float)
    # completed_files, total_files, bytes_sent, total_bytes, overall_speed, overall_eta
    upload_overall_progress = Signal(int, int, int, int, float, float)
    # item_id/filename, drive_file_id, status_str
    upload_file_completed = Signal(str, str, str)
    # item_id/filename, error_str
    upload_file_failed = Signal(str, str)
    # completed_count, failed_count, skipped_count
    upload_batch_finished = Signal(int, int, int)
    upload_paused = Signal()
    upload_resumed = Signal()
    upload_cancelled = Signal()

    # Sync signals
    # event_type (created/modified), file_path, job_name
    sync_file_detected = Signal(str, str, str)
    # job_id, is_active
    sync_job_status_changed = Signal(int, bool)
    sync_jobs_updated = Signal()

    # History & UI signals
    history_updated = Signal()
    # title, message, level ('info', 'success', 'warning', 'error')
    show_notification = Signal(str, str, str)


# Global singleton signal bus instance
signal_bus = SignalBus()
