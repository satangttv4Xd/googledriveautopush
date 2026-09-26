"""
Build script for packaging Google Drive AutoPush into a standalone Windows EXE using PyInstaller.
สคริปต์สำหรับคอมไพล์โปรแกรม Google Drive AutoPush เป็นไฟล์ EXE ที่สามารถรันบน Windows ได้โดยไม่ต้องติดตั้ง Python
"""
# นำเข้าโมดูล os สำหรับการทำงานกับระบบปฏิบัติการ
import os
# นำเข้า subprocess เพื่อใช้สั่งรันคำสั่งภายนอก (PyInstaller CLI)
import subprocess
# นำเข้า sys เพื่อเข้าถึง executable ของ Python ที่กำลังใช้งาน
import sys
# นำเข้า Path สำหรับจัดการเส้นทางไฟล์
from pathlib import Path


def build():
    """ฟังก์ชันสำหรับสร้างไฟล์ Windows Standalone Executable (.exe)"""
    # ระบุไดเรกทอรีรากของโปรเจกต์
    root_dir = Path(__file__).resolve().parent
    # ระบุไฟล์ entry point หลักของโปรแกรม
    main_py = root_dir / "main.py"
    # ระบุโฟลเดอร์ปลายทางสำหรับเก็บไฟล์ EXE ที่สร้างเสร็จแล้ว
    dist_dir = root_dir / "dist"
    # ระบุโฟลเดอร์สำหรับเก็บไฟล์ temporary build cache
    build_dir = root_dir / "build"

    print("==================================================")
    print("Building Google Drive AutoPush for Windows (EXE)...")
    print("==================================================")

    # กำหนดรายการพารามิเตอร์และตัวเลือกทั้งหมดสำหรับคำสั่ง PyInstaller
    cmd = [
        # ใช้ Python interpreter ตัวปัจจุบันในการเรียกใช้โมดูล
        sys.executable,
        # ระบุว่าต้องการรันโมดูล PyInstaller
        "-m", "PyInstaller",
        # กำหนดชื่อไฟล์ EXE ที่ได้ผลลัพธ์
        "--name=GoogleDriveAutoPush",
        # รวมทุกไฟล์และ Dependencies เป็นไฟล์ .exe ตัวเดียวจบ (One-file executable)
        "--onefile",
        # ซ่อนหน้าต่างคอนโซลดำ (ให้เปิดเฉพาะหน้าจอ GUI ของ PySide6)
        "--noconsole",
        # ล้างแคชการ build เก่าก่อนเริ่มสร้างใหม่เพื่อความสดใหม่
        "--clean",
        # กำหนดโฟลเดอร์ผลลัพธ์ของไฟล์ .exe
        f"--distpath={dist_dir}",
        # กำหนดโฟลเดอร์ชั่วคราวระหว่างการ build
        f"--workpath={build_dir}",
        # ระบุ Hidden Imports ที่ PyInstaller อาจหาไม่พบโดยอัตโนมัติ เพื่อป้องกัน error ตอนรัน
        "--hidden-import=PySide6.QtCore",
        "--hidden-import=PySide6.QtGui",
        "--hidden-import=PySide6.QtWidgets",
        "--hidden-import=googleapiclient.discovery",
        "--hidden-import=googleapiclient.http",
        "--hidden-import=google_auth_oauthlib.flow",
        "--hidden-import=google.auth.transport.requests",
        "--hidden-import=watchdog.observers.winapi",
        "--hidden-import=sqlite3",
        # แนบไฟล์ข้อมูลตัวอย่าง credentials.json.example เข้าไปใน package
        f"--add-data={root_dir / 'credentials.json.example'};.",
        # ระบุไฟล์สคริปต์หลักที่เป็นจุดเริ่มต้นของโปรแกรม
        str(main_py)
    ]

    # แสดงคำสั่งเต็มที่กำลังจะสั่งรัน
    print(f"Running command:\n{' '.join(cmd)}\n")
    # เรียกสั่งรันคำสั่ง PyInstaller ผ่าน subprocess
    result = subprocess.run(cmd, cwd=str(root_dir))

    # ตรวจสอบรหัสสถานะผลการทำงาน (0 = สำเร็จ)
    if result.returncode == 0:
        print("\n==================================================")
        print("BUILD SUCCESSFUL!")
        print(f"Standalone executable is located at:\n{dist_dir / 'GoogleDriveAutoPush.exe'}")
        print("==================================================")
    else:
        # หากเกิดข้อผิดพลาด ให้แจ้งเตือนและจบการทำงานด้วยรหัส error
        print(f"\nBUILD FAILED with exit code {result.returncode}")
        sys.exit(result.returncode)


# ตรวจสอบว่าไฟล์นี้ถูกรันโดยตรงหรือไม่
if __name__ == "__main__":
    # เรียกฟังก์ชัน build
    build()
