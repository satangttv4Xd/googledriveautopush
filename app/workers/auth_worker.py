"""
Background OAuth Authentication Worker Thread.
เธรดการทำงานเบื้องหลังสำหรับการยืนยันตัวตน Google OAuth
ช่วยให้ขั้นตอนการเปิดเว็บเบราว์เซอร์เพื่อล็อกอินทำงานแบบ Asynchronous โดยไม่ทำให้หน้าจอ PySide6 UI ค้าง
"""
# นำเข้า Path สำหรับจัดการเส้นทางไฟล์ credentials.json
from pathlib import Path
# นำเข้า Optional สำหรับการระบุ Type hint ที่อาจเป็นค่าว่าง (None) ได้
from typing import Optional
# นำเข้า QThread สำหรับแยกเธรดการทำงาน และ Signal สำหรับส่งสัญญาณกลับไปยัง UI
from PySide6.QtCore import QThread, Signal

# นำเข้า AuthService สำหรับจัดการขั้นตอน OAuth
from app.services.auth_service import AuthService
# นำเข้าระบบ Logger เพื่อบันทึกข้อความการทำงาน
from app.utils.logger import logger


class AuthWorker(QThread):
    """คลาส Worker สำหรับประมวลผลการล็อกอิน OAuth ในเบื้องหลัง"""

    # สัญญาณเมื่อการล็อกอินสำเร็จ ส่งข้อความผลลัพธ์ (string) กลับไป
    login_success = Signal(str)
    # สัญญาณเมื่อการล็อกอินล้มเหลว ส่งข้อความข้อผิดพลาด (string) กลับไป
    login_failed = Signal(str)

    def __init__(self, auth_service: AuthService, credentials_file: Optional[Path] = None, parent=None):
        # เรียกคอนสตรักเตอร์ของ QThread ดั้งเดิม
        super().__init__(parent)
        # เก็บอ็อบเจกต์ AuthService สำหรับใช้งาน
        self.auth_service = auth_service
        # เก็บเส้นทางไฟล์ credentials.json (ถ้ามี)
        self.credentials_file = credentials_file

    def run(self):
        """เมธอดหลักที่จะถูกรันในเธรดแยกต่างหากเมื่อสั่ง start()"""
        # บันทึก Log แจ้งเตือนว่ากำลังเริ่มขั้นตอนยืนยันตัวตนในเบื้องหลัง
        logger.info("กำลังเริ่มต้น Worker ล็อกอิน Google OAuth ในเบื้องหลัง...")

        # เรียกใช้ฟังก์ชัน login() ซึ่งจะเปิดเว็บเบราว์เซอร์ให้ผู้ใช้กดยืนยันตัวตน
        success, message = self.auth_service.login(self.credentials_file)

        # ตรวจสอบผลการล็อกอิน
        if success:
            # หากสำเร็จ ให้ส่งสัญญาณ login_success พร้อมข้อความกลับไปยัง UI Thread
            self.login_success.emit(message)
        else:
            # หากล้มเหลว ให้ส่งสัญญาณ login_failed พร้อมข้อความ Error กลับไปยัง UI Thread
            self.login_failed.emit(message)
