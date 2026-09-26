"""
Main Entry Point for Google Drive AutoPush.
ไฟล์เริ่มต้นหลักของโปรแกรม Google Drive AutoPush
ทำหน้าที่กำหนดค่าระบบ, โหลดธีม Dark Mode, เริ่มต้น Services และเปิดหน้าต่าง Desktop GUI (PySide6)
"""
# นำเข้าโมดูลระบบสำหรับการจัดการ path และการออกจากโปรแกรม
import sys
# นำเข้า Path สำหรับจัดการเส้นทางไฟล์และไดเรกทอรีแบบ Object-Oriented
from pathlib import Path

# เพิ่มไดเรกทอรีหลักของโปรเจกต์เข้าไปใน sys.path เพื่อให้สามารถ import โมดูลภายในโปรเจกต์ได้อย่างถูกต้อง
sys.path.insert(0, str(Path(__file__).resolve().parent))

# นำเข้าโมดูลหลักของ PySide6 (Qt) สำหรับการควบคุมคุณสมบัติระบบ
from PySide6.QtCore import Qt
# นำเข้า QApplication เพื่อใช้สร้างและควบคุม Application Event Loop ของ GUI
from PySide6.QtWidgets import QApplication

# นำเข้าค่าคงที่ของระบบ เช่น ชื่อโปรแกรม, ชื่อองค์กร และเวอร์ชัน
from config.constants import APP_NAME, APP_ORG, APP_VERSION
# นำเข้าคลาสจัดการการตั้งค่าโปรแกรม (Settings) ที่เชื่อมกับฐานข้อมูล
from config.settings import AppSettings
# นำเข้า SignalBus ซึ่งเป็นศูนย์กลางรับ-ส่งสัญญาณ (Qt Signals) ระหว่าง Thread
from app.core.signals import signal_bus
# นำเข้าคลาสจัดการฐานข้อมูล SQLite (DatabaseManager)
from app.database.db_manager import DatabaseManager
# นำเข้า Data Models สำหรับเก็บโครงสร้างข้อมูลของงาน Sync และประวัติการอัปโหลด
from app.database.models import SyncJobConfig, UploadHistoryItem
# นำเข้า Service สำหรับจัดการระบบยืนยันตัวตน Google OAuth 2.0
from app.services.auth_service import AuthService
# นำเข้า Service สำหรับเรียกใช้งาน Google Drive API v3 (สร้างโฟลเดอร์, อัปโหลดไฟล์)
from app.services.drive_service import DriveService
# นำเข้า Service สำหรับสแกนและจัดการไฟล์ในเครื่องคอมพิวเตอร์
from app.services.file_service import FileService
# นำเข้า Service สำหรับระบบ Auto Sync ที่ตรวจจับไฟล์ด้วย Watchdog
from app.services.sync_service import SyncService
# นำเข้าหน้าต่างหลักของโปรแกรม (MainWindow)
from app.ui.main_window import MainWindow
# นำเข้ารูปแบบสไตล์ชีทธีมมืด (Modern Dark Mode QSS)
from app.ui.styles import DARK_THEME_QSS
# นำเข้าระบบ Logger สำหรับบันทึกเหตุการณ์การทำงานลงไฟล์และคอนโซล
from app.utils.logger import logger


def handle_sync_file_ready(
    job_config: SyncJobConfig,       # ข้อมูลการตั้งค่าของงาน Sync (เช่น โฟลเดอร์ต้นทาง, ปลายทางบน Drive)
    file_path: str,                 # เส้นทางไฟล์ในคอมพิวเตอร์ที่ตรวจพบ
    event_type: str,                # ประเภทเหตุการณ์ เช่น 'created' (สร้างใหม่) หรือ 'modified' (แก้ไข)
    drive_service: DriveService,    # อ็อบเจกต์บริการ Google Drive API
    db_manager: DatabaseManager,    # อ็อบเจกต์จัดการฐานข้อมูล SQLite
    app_settings: AppSettings       # อ็อบเจกต์จัดการการตั้งค่าของโปรแกรม
):
    """
    ฟังก์ชัน Callback ที่จะถูกเรียกทำงานอัตโนมัติจาก SyncService
    เมื่อมีไฟล์ในโฟลเดอร์ที่เฝ้าติดตามถูกเขียนหรือคัดลอกลงดิสก์เสร็จสมบูรณ์แล้ว
    """
    # บันทึก Log แจ้งเตือนว่ากำลังเริ่มประมวลผลไฟล์ที่ตรวจพบ
    logger.info(f"[AutoSync Worker] กำลังประมวลผลไฟล์ ({event_type}): {file_path} สำหรับงาน '{job_config.name}'")

    # ตรวจสอบว่าผู้ใช้ล็อกอินเชื่อมต่อ Google Drive ไว้หรือไม่
    if not drive_service.auth_service.is_authenticated():
        # หากยังไม่ได้ล็อกอิน ให้ข้ามการอัปโหลดและแจ้งเตือนใน Log
        logger.warning("[AutoSync Worker] Google Drive ยังไม่ได้เชื่อมต่อ ข้ามการอัปโหลดอัตโนมัติ")
        return

    try:
        # สแกนและดึงข้อมูล metadata ของไฟล์ เช่น ขนาด และชื่อไฟล์
        task = FileService.get_file_task(file_path)
        # หากอ่านไฟล์ไม่ได้ (เช่น ไฟล์ถูกลบไปแล้ว) ให้หยุดการทำงาน
        if not task:
            return

        # ดึงค่านโยบายจัดการกรณีชื่อไฟล์ซ้ำจาก Settings (ค่าเริ่มต้น: 'keep_both' เก็บไว้ทั้งคู่)
        conflict_policy = app_settings.get("conflict_policy", "keep_both")

        # สั่งอัปโหลดไฟล์ขึ้น Google Drive แบบ Resumable Chunked Upload
        status, file_id, final_name = drive_service.upload_file_resumable(
            local_path=task.local_path,               # เส้นทางไฟล์ในเครื่อง
            parent_id=job_config.drive_folder_id,     # ID โฟลเดอร์ปลายทางบน Google Drive
            target_name=task.filename,                # ชื่อไฟล์
            conflict_policy=conflict_policy           # นโยบายจัดการไฟล์ซ้ำ
        )

        # นำเข้าโมดูลเวลาเพื่อดึงเวลาปัจจุบันในรูปแบบตัวอักษร
        import time
        # จัดรูปแบบเวลาปัจจุบันเป็น 'YYYY-MM-DD HH:MM:SS'
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        # บันทึกประวัติการอัปโหลดลงในฐานข้อมูล SQLite
        db_manager.add_history_record(UploadHistoryItem(
            filename=final_name or task.filename,     # ชื่อไฟล์ที่อัปโหลดสำเร็จ (อาจมีการเปลี่ยนชื่อตามนโยบาย)
            local_path=task.local_path,               # ที่อยู่ไฟล์เดิมในเครื่อง
            drive_file_id=file_id,                    # Google Drive File ID ที่ได้หลังอัปโหลด
            drive_folder_id=job_config.drive_folder_id,   # ID โฟลเดอร์ปลายทางบน Drive
            drive_folder_path=job_config.drive_folder_path, # Path โฟลเดอร์ปลายทางบน Drive
            file_size=task.file_size,                 # ขนาดไฟล์ (ไบต์)
            status=status,                            # สถานะ (completed, skipped ฯลฯ)
            timestamp=now_str                         # เวลาที่บันทึก
        ))

        # อัปเดตเวลาการซิงค์ล่าสุดของงานนี้ในฐานข้อมูล
        db_manager.update_sync_last_run(job_config.id, now_str)

        # ส่งสัญญาณ Qt Signal เพื่อให้หน้าต่าง History บน UI รีเฟรชตารางประวัติใหม่ทันที
        signal_bus.history_updated.emit()
        # ส่งสัญญาณแจ้งเตือน Notification ไปยัง Status Bar ของหน้าต่างโปรแกรม
        signal_bus.show_notification.emit(
            "Auto-Sync Upload",
            f"ซิงค์ไฟล์ '{task.filename}' ไปยัง {job_config.drive_folder_path} สำเร็จ",
            "success"
        )
    except Exception as e:
        # บันทึกข้อผิดพลาดลง Log กรณีเกิด Error ระหว่างอัปโหลดไฟล์อัตโนมัติ
        logger.error(f"[AutoSync Worker] เกิดข้อผิดพลาดในการอัปโหลด {file_path}: {e}")


def main():
    """
    ฟังก์ชันหลัก (Application Entry Point)
    ทำหน้าที่กำหนดค่าระบบและเปิดแสดงผลหน้าต่างโปรแกรม Desktop GUI
    """
    # บันทึก Log การเริ่มทำงานของโปรแกรม พร้อมชื่อและเวอร์ชัน
    logger.info(f"เริ่มต้นโปรแกรม {APP_NAME} v{APP_VERSION}...")

    # เปิดใช้งานฟีเจอร์ High-DPI Scaling สำหรับจอแสดงผลความละเอียดสูงบน Windows 10/11 เพื่อให้ฟอนต์และไอคอนคมชัด
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # สร้าง Application Object หลักของ Qt (ต้องสร้างก่อน Widget อื่นๆ เสมอ)
    app = QApplication(sys.argv)
    # กำหนดชื่อโปรแกรมในระดับ Application
    app.setApplicationName(APP_NAME)
    # กำหนดชื่อองค์กรผู้พัฒนา
    app.setOrganizationName(APP_ORG)
    # กำหนดเวอร์ชันของโปรแกรม
    app.setApplicationVersion(APP_VERSION)

    # นำสไตล์ชีทธีมมืด (Modern Dark Mode QSS) มาใช้งานทั่วทั้งโปรแกรม
    app.setStyleSheet(DARK_THEME_QSS)

    # สร้างและเตรียมความพร้อมฐานข้อมูล SQLite พร้อมโหลดตารางข้อมูลทั้งหมด
    db_manager = DatabaseManager()
    # สร้างตัวจัดการการตั้งค่าของโปรแกรม โดยเชื่อมโยงกับฐานข้อมูล SQLite
    app_settings = AppSettings(db_manager)

    # สร้าง Service สำหรับจัดการการล็อกอิน Google OAuth 2.0 (ระบุ path ของ credentials.json และ token.json)
    auth_service = AuthService(
        credentials_path=Path(app_settings.get("credentials_path")),
        token_path=Path(app_settings.get("token_path"))
    )
    # สร้าง Service สำหรับเรียกใช้งาน Google Drive API v3 โดยใช้ auth_service ในการยืนยันตัวตน
    drive_service = DriveService(auth_service)

    # สร้างฟังก์ชัน Callback สำหรับส่งต่องานให้อัปโหลดเมื่อ Watchdog ตรวจพบไฟล์ใหม่
    def on_sync_ready(cfg, fpath, etype):
        handle_sync_file_ready(cfg, fpath, etype, drive_service, db_manager, app_settings)

    # สร้าง Service สำหรับระบบ Auto Sync โฟลเดอร์อัตโนมัติ
    sync_service = SyncService(on_file_ready_callback=on_sync_ready)

    # สร้างหน้าต่างหลักของโปรแกรม (MainWindow) พร้อมส่งผ่าน Services ต่างๆ ให้พร้อมใช้งาน
    window = MainWindow(
        auth_service=auth_service,
        drive_service=drive_service,
        sync_service=sync_service,
        db_manager=db_manager,
        app_settings=app_settings
    )
    # แสดงหน้าต่างโปรแกรมขึ้นบนหน้าจอคอมพิวเตอร์
    window.show()

    # เริ่มต้นลูปการทำงานหลักของ GUI (Qt Event Loop) โดยโปรแกรมจะรอรับ Event จากผู้ใช้จนกว่าจะปิดหน้าต่าง
    exit_code = app.exec()
    # บันทึก Log เมื่อผู้ใช้ปิดโปรแกรม พร้อมรหัสการออก (Exit Code)
    logger.info(f"โปรแกรมปิดการทำงานด้วยรหัส {exit_code}")
    # จบการทำงานของสคริปต์ Python ด้วย exit_code ที่ได้รับ
    sys.exit(exit_code)


# ตรวจสอบว่าไฟล์นี้ถูกรันโดยตรงหรือไม่ (ไม่ใช่การ import)
if __name__ == "__main__":
    # เรียกฟังก์ชันหลักเพื่อเริ่มการทำงานของโปรแกรม
    main()
