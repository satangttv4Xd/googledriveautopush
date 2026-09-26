# Google Drive AutoPush ☁️🚀
**Modern Desktop Application for Windows 10 / 11**

**Google Drive AutoPush** คือโปรแกรม Desktop สำหรับ Windows ที่พัฒนาด้วยภาษา **Python (PySide6)** ล้วน 100% ออกแบบตามหลักสถาปัตยกรรมซอฟต์แวร์ระดับมืออาชีพ หน้าตาโปรแกรมสไตล์ Modern Dark Mode สวยงาม ใช้งานง่าย และตอบโจทย์การทำงานจริง

หัวใจสำคัญของโปรแกรมคือ **ผู้ใช้สามารถสร้างโฟลเดอร์ใหม่บน Google Drive จากในโปรแกรมได้โดยตรง (Destination Manager)** ก่อนเริ่มต้นอัปโหลดหรือ Push ไฟล์เข้าโฟลเดอร์ โดยไม่ต้องเปิดหน้าเว็บ Google Drive เลยแม้แต่น้อย

---

## สารบัญ (Table of Contents)

1. [ฟีเจอร์หลัก (Key Features)](#1-ฟีเจอร์หลัก-key-features)
2. [สถาปัตยกรรมและโครงสร้างโปรเจกต์ (Architecture)](#2-สถาปัตยกรรมและโครงสร้างโปรเจกต์-architecture)
3. [เทคโนโลยีที่ใช้ (Tech Stack)](#3-เทคโนโลยีที่ใช้-tech-stack)
4. [ขั้นตอนการตั้งค่า Google Cloud Project และ OAuth (สำคัญมาก)](#4-ขั้นตอนการตั้งค่า-google-cloud-project-และ-oauth-สำคัญมาก)
5. [การติดตั้งและรันโปรแกรมบน Windows 10/11](#5-การติดตั้งและรันโปรแกรมบน-windows-1011)
6. [คู่มือการใช้งานฟีเจอร์หลัก](#6-คู่มือการใช้งานฟีเจอร์หลัก)
   - [6.1 การเชื่อมต่อ Google Drive](#61-การเชื่อมต่อ-google-drive)
   - [6.2 การสร้างโฟลเดอร์ปลายทางบน Drive ก่อน Push (Destination Manager)](#62-การสร้างโฟลเดอร์ปลายทางบน-drive-ก่อน-push-destination-manager)
   - [6.3 การเลือกไฟล์/โฟลเดอร์ และ Drag & Drop](#63-การเลือกไฟล์โฟลเดอร์-และ-drag--drop)
   - [6.4 ระบบ Push / Upload และระบบจัดการไฟล์ซ้ำ](#64-ระบบ-push--upload-และระบบจัดการไฟล์ซ้ำ)
   - [6.5 ระบบ Auto Sync ตรวจจับไฟล์อัตโนมัติ](#65-ระบบ-auto-sync-ตรวจจับไฟล์อัตโนมัติ)
   - [6.6 ประวัติและฐานข้อมูล SQLite](#66-ประวัติและฐานข้อมูล-sqlite)
7. [การรัน Unit Tests](#7-การรัน-unit-tests)
8. [การ Build เป็นไฟล์ Windows EXE ด้วย PyInstaller](#8-การ-build-เป็นไฟล์-windows-exe-ด้วย-pyinstaller)
9. [ความปลอดภัยและความเป็นส่วนตัว (Security)](#9-ความปลอดภัยและความเป็นส่วนตัว-security)

---

## 1. ฟีเจอร์หลัก (Key Features)

* **📁 Google Drive Destination Manager (ฟีเจอร์เด่น)**:
  * เรียกดูโครงสร้างโฟลเดอร์บน Google Drive ได้โดยตรง
  * แถบ Breadcrumbs นำทางหลายระดับ เช่น `My Drive / Projects / Python / Project A` (คลิกย้อนกลับไปชั้นใดก็ได้)
  * **ปุ่ม "+ New Folder"**: สร้างโฟลเดอร์ใหม่บน Google Drive ได้ทันทีจากในโปรแกรม รองรับการสร้างโฟลเดอร์ซ้อนหลายชั้น (เช่น `Projects/2026/Backup`)
  * **ปุ่ม "Select This Folder"**: บันทึก Google Drive Folder ID ที่เลือกไว้อย่างแม่นยำ ป้องกันปัญหาโฟลเดอร์ชื่อซ้ำ
* **🔑 Google OAuth 2.0 Desktop Flow**:
  * ล็อกอินผ่านเบราว์เซอร์อย่างปลอดภัยด้วยบัญชี Google ของผู้ใช้เอง
  * บันทึก Token อัตโนมัติ (`token.json`) พร้อมกลไก Auto Refresh Token เมื่อหมดอายุ
  * แสดงข้อมูลบัญชี (ชื่อ, อีเมล) และแถบโควตาพื้นที่ Google Drive Storage (Used / Total Quota)
  * มีปุ่ม Disconnect ปลอดภัย ไม่ส่งข้อมูลไปเซิร์ฟเวอร์ภายนอก
* **⬆️ Upload & Push Engine**:
  * รองรับการเลือกไฟล์เดี่ยว หลายไฟล์ และทั้งโฟลเดอร์
  * รองรับ **Drag & Drop** ลากไฟล์หรือโฟลเดอร์จาก Windows Explorer มาวางในโปรแกรมได้ทันที
  * มี 2 โหมดเมื่อเลือกโฟลเดอร์:
    1. *Upload Contents*: อัปโหลดไฟล์และโฟลเดอร์ย่อยข้างในไปยังโฟลเดอร์ปลายทาง
    2. *Upload As Folder*: สร้างโฟลเดอร์ตามชื่อต้นทางบน Drive แล้วอัปโหลดข้อมูลข้างใน รักษาโครงสร้างโฟลเดอร์ย่อยครบถ้วน
  * หน้าต่างสรุปข้อมูล (Pre-Push Summary) ก่อนเริ่มอัปโหลด
  * **Resumable Upload**: รองรับไฟล์ขนาดใหญ่แบบแบ่ง Chunk พร้อมคำนวณความเร็ว (Speed) และเวลาที่เหลือ (ETA) แบบเรียลไทม์
  * ควบคุมการทำงานได้: **Pause (หยุดชั่วคราว), Resume (ทำต่อ), Cancel (ยกเลิก)**
  * กลไก Exponential Backoff & Retry อัตโนมัติเมื่อเกิดปัญหาเน็ตหลุดหรือ Rate Limit
  * **UI ไม่ค้าง**: แยกการทำงานใน `QThread` พื้นหลัง
* **⚠️ ระบบป้องกันไฟล์ซ้ำ (Conflict Resolution)**:
  * ตรวจสอบไฟล์ชื่อเดียวกันในโฟลเดอร์ปลายทางก่อนอัปโหลด
  * 3 นโยบายให้เลือก:
    1. `Skip`: ข้ามไฟล์ที่มีอยู่แล้ว
    2. `Replace`: อัปเดตเนื้อหาไฟล์เดิมบน Google Drive
    3. `Keep Both`: สร้างเป็นไฟล์ใหม่พร้อมตั้งชื่อต่อท้าย เช่น `file (1).png`
* **🔄 ระบบ Auto Sync ตรวจจับอัตโนมัติ**:
  * ใช้ `watchdog` ดักจับไฟล์ที่สร้างใหม่หรือแก้ไขในคอมพิวเตอร์
  * **Write-Lock & Stability Checker**: มีระบบตรวจสอบความสมบูรณ์ของไฟล์ ป้องกันการอัปโหลดไฟล์ที่ยังคัดลอกหรือเขียนลงดิสก์ไม่เสร็จ
  * ปลอดภัย: การลบไฟล์ในคอมพิวเตอร์จะไม่ลบไฟล์บน Google Drive
* **📜 ประวัติและฐานข้อมูล SQLite**:
  * บันทึกประวัติการอัปโหลด, คิวงาน, การตั้งค่า และ Sync Jobs ลงฐานข้อมูล SQLite ในเครื่อง
  * ค้นหา กรองตามสถานะ (Completed, Failed, Skipped) และเปิดดูรายละเอียด Error ได้อย่างชัดเจน
  * ส่งออกประวัติเป็นไฟล์ CSV ได้

---

## 2. สถาปัตยกรรมและโครงสร้างโปรเจกต์ (Architecture)

โปรเจกต์ถูกออกแบบตามแนวคิด **Clean Architecture & Separation of Concerns** แยกชั้นการทำงานชัดเจน:

```
googledriveautopush/
├── main.py                     # Entry point หลักของโปรแกรม
├── requirements.txt            # รายการ Dependencies ทั้งหมด
├── credentials.json.example    # ตัวอย่างไฟล์ OAuth Client Secret จาก Google Cloud
├── build_exe.py                # สคริปต์สำหรับ Build เป็น Windows EXE
├── README.md                   # คู่มือภาษาไทยฉบับสมบูรณ์
├── config/
│   ├── constants.py            # ค่าคงที่, MIME Types, Policies, Default Paths
│   └── settings.py             # จัดการการตั้งค่าโปรแกรมผ่าน SQLite
├── app/
│   ├── core/
│   │   ├── exceptions.py       # Custom Exception Classes
│   │   └── signals.py          # Central Qt SignalBus สำหรับสื่อสารข้าม Thread
│   ├── database/
│   │   ├── models.py           # Data Models (Queue, History, SyncConfig, Bookmark)
│   │   └── db_manager.py       # SQLite Database Manager (WAL Mode, Thread-Safe)
│   ├── services/
│   │   ├── auth_service.py     # ระบบ Google OAuth 2.0 และจัดการ Token
│   │   ├── drive_service.py    # Google Drive API v3 (Folder CRUD, Resumable Upload)
│   │   ├── file_service.py     # ตรวจสอบและสแกนโครงสร้างโฟลเดอร์/ไฟล์ในเครื่อง
│   │   └── sync_service.py     # ตัวจัดการ Watchdog Observer และระบบ Debounce
│   ├── workers/
│   │   ├── upload_worker.py    # QThread อัปโหลดไฟล์พร้อมคำนวณ Speed, ETA, Pause/Resume
│   │   └── auth_worker.py      # QThread ดำเนินการ OAuth Browser Login แบบ Non-blocking
│   ├── ui/
│   │   ├── styles.py           # ธีม Modern Dark Mode (QSS)
│   │   ├── main_window.py      # หน้าต่างหลัก Sidebar + QStackedWidget
│   │   ├── pages/
│   │   │   ├── dashboard_page.py    # แดชบอร์ดสรุปสถานะและโควตา
│   │   │   ├── upload_page.py       # หน้าเลือกไฟล์ Drag & Drop และเริ่ม Push
│   │   │   ├── destination_page.py  # Destination Manager (สร้างโฟลเดอร์บน Drive)
│   │   │   ├── sync_page.py         # หน้าจัดการ Auto-Sync Jobs
│   │   │   ├── history_page.py      # หน้าประวัติการอัปโหลดและค้นหา
│   │   │   └── settings_page.py     # หน้าตั้งค่า Credentials และการเชื่อมต่อ
│   │   └── dialogs/
│   │       ├── new_folder_dialog.py # Dialog สร้างโฟลเดอร์ใหม่บน Drive
│   │       ├── conflict_dialog.py   # Dialog เลือกนโยบายไฟล์ซ้ำ
│   │       ├── summary_dialog.py    # Dialog สรุปข้อมูลก่อนเริ่ม Push
│   │       ├── error_dialog.py      # Dialog แสดงรายละเอียด Error
│   │       └── add_sync_dialog.py   # Dialog เพิ่มงาน Sync ใหม่
│   └── utils/
│       ├── logger.py           # Thread-safe Logger พร้อมระบบ Mask Token/Secret
│       ├── formatters.py       # แปลงหน่วยไบต์, ความเร็ว, เวลา ETA, วันที่
│       └── file_checker.py     # ตรวจสอบความนิ่งของไฟล์ (File Write Stability)
└── tests/
    ├── test_db.py              # ทดสอบฐานข้อมูล SQLite และ CRUD Operations
    ├── test_folder_manager.py  # ทดสอบการสร้างและจัดการโฟลเดอร์บน Google Drive
    ├── test_upload_engine.py   # ทดสอบระบบอัปโหลดและการจัดการไฟล์ซ้ำ
    └── test_sync_engine.py     # ทดสอบระบบสแกนไฟล์และ Watchdog Debounce
```

---

## 3. เทคโนโลยีที่ใช้ (Tech Stack)

* **Python**: 3.12+ (รองรับ Python 3.13)
* **GUI Framework**: `PySide6` (Qt 6 for Python) สำหรับหน้าต่าง Modern Dark UI และระบบ Multi-threading `QThread`
* **Google Drive API**: `google-api-python-client` (v3)
* **OAuth 2.0**: `google-auth-oauthlib`, `google-auth-httplib2`
* **Database**: `sqlite3` พร้อมเปิดใช้งาน Write-Ahead Logging (WAL) Mode
* **Filesystem Monitoring**: `watchdog`
* **Packaging**: `pyinstaller` สำหรับคอมไพล์เป็น Windows EXE
* **Testing**: `pytest`

---

## 4. ขั้นตอนการตั้งค่า Google Cloud Project และ OAuth (สำคัญมาก)

ในการใช้งาน Google Drive API กับบัญชีของคุณเอง Google กำหนดให้ต้องสร้าง **OAuth 2.0 Client ID** ผ่าน Google Cloud Console ทำตามขั้นตอนนี้เพียงครั้งเดียว:

### ขั้นที่ 1: สร้าง Google Cloud Project
1. ไปที่เว็บไซต์ **[Google Cloud Console](https://console.cloud.google.com/)** และล็อกอินด้วยบัญชี Google ของคุณ
2. ที่แถบด้านบน คลิกเลือกโปรเจกต์ แล้วกด **"New Project" (โปรเจกต์ใหม่)**
3. ตั้งชื่อโปรเจกต์ เช่น `GoogleDriveAutoPush` แล้วกด **"Create"**

### ขั้นที่ 2: เปิดใช้งาน Google Drive API
1. ไปที่เมนู **"APIs & Services" > "Library"** (คลัง API)
2. ค้นหาคำว่า **"Google Drive API"**
3. คลิกเข้าไปแล้วกดปุ่ม **"Enable" (เปิดใช้งาน)**

### ขั้นที่ 3: ตั้งค่า OAuth Consent Screen (หน้าจอยินยอม)
1. ไปที่ **"APIs & Services" > "OAuth consent screen"**
2. เลือก User Type เป็น **"External"** แล้วกด **"Create"**
3. กรอกข้อมูลเบื้องต้น:
   * **App name**: `Google Drive AutoPush`
   * **User support email**: เลือกอีเมลของคุณ
   * **Developer contact information**: กรอกอีเมลของคุณ
4. กด **"Save and Continue"**
5. ในขั้นตอน **Scopes**: สามารถกด Save and Continue ข้ามไปได้
6. ในขั้นตอน **Test users** (สำคัญมาก):
   * กด **"+ Add Users"**
   * ใส่อีเมล Google ที่คุณจะใช้ล็อกอินในโปรแกรม
   * กด **"Save and Continue"**

### ขั้นที่ 4: สร้าง OAuth 2.0 Client ID (ประเภท Desktop App)
1. ไปที่ **"APIs & Services" > "Credentials"** (ข้อมูลรับรอง)
2. คลิกปุ่ม **"+ Create Credentials"** ด้านบน แล้วเลือก **"OAuth client ID"**
3. ที่ช่อง **Application type** เลือกเป็น **"Desktop App"** (แอปพลิเคชันบนเดสก์ท็อป)
4. ตั้งชื่อ เช่น `AutoPush Desktop Client` แล้วกด **"Create"**
5. จะมีหน้าต่างขึ้นมา ให้คลิก **"Download JSON"** (ดาวน์โหลดไฟล์ JSON)
6. เปลี่ยนชื่อไฟล์ที่ดาวน์โหลดมาเป็น **`credentials.json`** แล้วนำมาวางไว้ที่โฟลเดอร์โปรเจกต์ หรือเลือกผ่านหน้า Settings ของโปรแกรม

> 💡 **หมายเหตุ**: ไฟล์ `credentials.json.example` ในโปรเจกต์แสดงตัวอย่างโครงสร้างไฟล์ที่ถูกต้อง

---

## 5. การติดตั้งและรันโปรแกรมบน Windows 10/11

### 1. โคลนหรือดาวน์โหลดโปรเจกต์
เปิด Command Prompt หรือ PowerShell ในโฟลเดอร์ที่ต้องการ:
```powershell
cd d:\Code\googledriveautopush
```

### 2. สร้าง Virtual Environment (แนะนำ)
```powershell
python -m venv venv
.\venv\Scripts\activate
```

### 3. ติดตั้ง Dependencies
```powershell
pip install -r requirements.txt
```

### 4. รันโปรแกรม
```powershell
python main.py
```

หน้าต่างโปรแกรม **Google Drive AutoPush** จะปรากฏขึ้นในธีม Modern Dark Mode ทันที!

---

## 6. คู่มือการใช้งานฟีเจอร์หลัก

### 6.1 การเชื่อมต่อ Google Drive
1. เปิดโปรแกรม ไปที่เมนู **Settings** (⚙️) ใน Sidebar ด้านซ้าย
2. ตรวจสอบว่าช่อง **Path to credentials.json** ชี้ไปยังไฟล์ของคุณ (สามารถกดปุ่ม **Browse...** เพื่อเลือกไฟล์ได้)
3. กดปุ่ม **"Connect Google Drive"**
4. โปรแกรมจะเปิดเว็บเบราว์เซอร์ขึ้นมาอัตโนมัติ ให้คุณล็อกอินและกดยินยอมให้สิทธิ์ (Allow)
5. เมื่อสำเร็จ หน้าต่างจะแสดงสถานะ **Connected (อีเมลของคุณ)**
6. โปรแกรมจะจำ Token ไว้ใน `data/token.json` ครั้งถัดไปที่เปิดโปรแกรมจะเชื่อมต่อให้อัตโนมัติโดยไม่ต้องล็อกอินซ้ำ

---

### 6.2 การสร้างโฟลเดอร์ปลายทางบน Drive ก่อน Push (Destination Manager)
**นี่คือฟีเจอร์หลักของโปรแกรมที่คุณไม่ต้องเปิดเว็บไซต์ Google Drive เลย:**

1. คลิกที่เมนู **Destinations & Folders** (📁)
2. คุณจะเห็นรายการโฟลเดอร์ทั้งหมดใน **My Drive**
3. สามารถ **ดับเบิ้ลคลิก** ที่แถวโฟลเดอร์ หรือกดปุ่ม **Open** เพื่อเข้าไปดูโฟลเดอร์ย่อยด้านใน
4. แถบ **Breadcrumbs** ด้านบนจะแสดงลำดับชั้นโฟลเดอร์ เช่น `My Drive / Projects / Python` (สามารถคลิกเพื่อย้อนกลับชั้นไหนก็ได้ หรือกดปุ่ม `⬅ Back / Up`)
5. **การสร้างโฟลเดอร์ใหม่**:
   * คลิกปุ่ม **"➕ New Folder"** สีน้ำเงินเด่นชัด
   * หน้าต่างสร้างโฟลเดอร์จะปรากฏขึ้น พร้อมบอกตำแหน่งว่ากำลังสร้างอยู่ใต้โฟลเดอร์ใด
   * พิมพ์ชื่อโฟลเดอร์ที่ต้องการ เช่น `Backup 2026` หรือพิมพ์แบบหลายชั้น เช่น `ProjectA/SourceCode`
   * กด **"Create Folder"**
   * โปรแกรมจะเรียก Google Drive API สร้างโฟลเดอร์จริงบน Drive ทันที และทำการรีเฟรชรายการให้อัตโนมัติ
6. **การกำหนดโฟลเดอร์ปลายทางสำหรับ Push**:
   * เมื่อคุณเปิดเข้าไปยังโฟลเดอร์ที่ต้องการใช้เป็นปลายทาง ให้กดปุ่ม **"🎯 Select Current Folder as Destination"**
   * โปรแกรมจะบันทึก Google Drive Folder ID และ Path ไว้อย่างถูกต้อง พร้อมแจ้งเตือนยืนยัน

---

### 6.3 การเลือกไฟล์/โฟลเดอร์ และ Drag & Drop
1. คลิกเมนู **Upload Files** (⬆️)
2. ด้านบนจะแสดงโฟลเดอร์ปลายทางบน Drive ที่คุณเลือกไว้ในขั้นตอนก่อนหน้า
3. วิธีการเพิ่มไฟล์:
   * **Drag & Drop**: ลากไฟล์หรือโฟลเดอร์จากหน้าต่าง Windows Explorer มาปล่อยในกรอบ **"Drag & Drop Files or Folders Here"**
   * **ปุ่ม "📄 Add Files..."**: เลือกไฟล์เดี่ยวหรือหลายไฟล์พร้อมกัน
   * **ปุ่ม "📁 Add Folder..."**: เลือกโฟลเดอร์จากเครื่องของคุณ ซึ่งโปรแกรมจะมีกล่องข้อความถาม:
     * *Upload As Folder*: สร้างโฟลเดอร์บน Drive ตามชื่อโฟลเดอร์เดิม แล้วอัปโหลดไฟล์และโฟลเดอร์ย่อยทั้งหมดไว้ด้านใน (รักษาโครงสร้างเดิม)
     * *Upload Contents*: อัปโหลดเฉพาะไฟล์และโฟลเดอร์ย่อยข้างในไปยังปลายทางโดยตรง
4. ตารางจะแสดงชื่อไฟล์, Relative Path, ขนาดไฟล์, และประเภทไฟล์ โดยคุณสามารถกดปุ่ม **✕** ลบไฟล์ที่ไม่ต้องการออกได้
5. ด้านล่างจะแสดงสรุปจำนวนไฟล์และขนาดรวมทั้งหมดแบบเรียลไทม์

---

### 6.4 ระบบ Push / Upload และระบบจัดการไฟล์ซ้ำ
1. ในหน้า **Upload Files** เลือกนโยบายไฟล์ซ้ำ (Policy) ได้จากดรอปดาวน์:
   * **Keep Both**: เก็บไว้ทั้งคู่ โดยไฟล์ใหม่จะตั้งชื่อต่อท้ายด้วย `(1)`, `(2)`
   * **Skip**: ข้ามการอัปโหลดหากไฟล์ชื่อซ้ำมีอยู่แล้ว
   * **Replace**: อัปเดตเนื้อหาไฟล์เดิมบน Google Drive
2. กดปุ่มใหญ่สีเขียว **"🚀 Push to Google Drive"**
3. โปรแกรมจะแสดงหน้าต่าง **Push Summary Dialog** สรุปข้อมูลทั้งหมด:
   * โฟลเดอร์ปลายทางบน Google Drive และ Folder ID
   * จำนวนไฟล์รวม และขนาดข้อมูลรวม
   * ตัวเลือกนโยบายไฟล์ซ้ำ
4. กด **"Start Upload (Push Now)"**
5. ระบบจะเริ่มอัปโหลดไฟล์แบบ Resumable ในพื้นหลัง:
   * แสดง Progress Bar รวม (Overall Progress) และของไฟล์ปัจจุบัน
   * แสดงความเร็วการถ่ายโอนข้อมูล (Speed เช่น `2.45 MB/s`) และเวลาที่เหลือ (ETA)
   * ปุ่มควบคุม: สามารถกด **"⏸ Pause"** เพื่อหยุดชั่วคราว, **"▶ Resume"** เพื่อทำงานต่อ, หรือ **"⏹ Cancel"** เพื่อยกเลิกได้ตลอดเวลา

---

### 6.5 ระบบ Auto Sync ตรวจจับไฟล์อัตโนมัติ
1. คลิกเมนู **Auto Sync** (🔄)
2. คลิกปุ่ม **"➕ Add Sync Job"**
3. ตั้งค่างาน Sync:
   * **Job Name**: ชื่อของงาน เช่น `Sync งานเอกสาร`
   * **Local Folder**: เลือกโฟลเดอร์ในเครื่องคอมพิวเตอร์ของคุณ
   * **Drive Target**: จะใช้โฟลเดอร์ปลายทางที่คุณเลือกไว้จาก Destination Manager
   * **Sync Modified Files**: ติ๊กถูกหากต้องการให้อัปโหลดเมื่อไฟล์ถูกแก้ไขด้วย (ถ้าไม่ติ๊กจะดักจับเฉพาะไฟล์ที่สร้างใหม่)
4. กด **"Create Sync Job"**
5. ระบบ Watchdog จะเริ่มเฝ้าตรวจจับการเปลี่ยนแปลงในโฟลเดอร์นั้นทันที
   * **ความปลอดภัยสูง**: โปรแกรมมีระบบ File Stability Checker รอจนกว่าไฟล์จะถูกเขียน/คัดลอกลงดิสก์เสร็จสมบูรณ์ จึงจะส่งขึ้น Drive เพื่อป้องกันไฟล์เสีย
   * การลบไฟล์ในเครื่อง **ไม่มีผล** ต่อไฟล์บน Google Drive

---

### 6.6 ประวัติและฐานข้อมูล SQLite
1. คลิกเมนู **Upload History** (📜)
2. ดูประวัติการอัปโหลดย้อนหลังทั้งหมด พร้อมข้อมูลวันที่, ชื่อไฟล์, โฟลเดอร์ปลายทาง, ขนาด, สถานะ, ความเร็ว และระยะเวลา
3. ช่องค้นหา (Search): ค้นหาตามชื่อไฟล์หรือชื่อโฟลเดอร์ปลายทางได้ทันที
4. ตัวกรองสถานะ: กรองเฉพาะ Completed, Failed หรือ Skipped
5. กรณีไฟล์มีข้อผิดพลาด สามารถกดปุ่ม **"View Error"** เพื่อดูสาเหตุและกด Copy รายละเอียดได้
6. สามารถกด **"💾 Export CSV"** เพื่อบันทึกประวัติออกมาเป็นไฟล์ Excel/CSV

---

## 7. การรัน Unit Tests

โปรเจกต์นี้มาพร้อมชุดการทดสอบอัตโนมัติ (Automated Unit Tests) ครอบคลุม:
* `test_db.py`: ทดสอบการทำงานของ SQLite Database, Transactions, Queue และ History
* `test_folder_manager.py`: ทดสอบการสร้างโฟลเดอร์, การสร้างโฟลเดอร์ซ้อนหลายระดับ และ Breadcrumbs
* `test_upload_engine.py`: ทดสอบระบบ Resumable Upload และนโยบายแก้ไขความขัดแย้งของไฟล์ (Skip, Replace, Keep Both)
* `test_sync_engine.py`: ทดสอบระบบสแกนโครงสร้างไดเรกทอรี และ Watchdog Debounce

รันคำสั่งทดสอบผ่าน Terminal:
```powershell
python -m pytest tests -v
```

ผลการทดสอบทั้งหมด 16 ชุดจะผ่าน (PASSED 100%):
```text
tests/test_db.py::test_init_db PASSED                                    [  6%]
tests/test_db.py::test_history_crud PASSED                               [ 12%]
tests/test_db.py::test_queue_crud PASSED                                 [ 18%]
tests/test_db.py::test_sync_configs_crud PASSED                          [ 25%]
tests/test_db.py::test_settings_storage PASSED                           [ 31%]
tests/test_folder_manager.py::test_create_folder_success PASSED          [ 37%]
tests/test_folder_manager.py::test_create_folder_empty_name PASSED       [ 43%]
tests/test_folder_manager.py::test_create_folder_hierarchy_nested PASSED [ 50%]
tests/test_folder_manager.py::test_list_folders PASSED                   [ 56%]
tests/test_folder_manager.py::test_get_folder_breadcrumbs PASSED         [ 62%]
tests/test_sync_engine.py::test_file_scanner_modes PASSED                [ 68%]
tests/test_sync_engine.py::test_file_stability_checker PASSED            [ 75%]
tests/test_sync_engine.py::test_sync_event_handler_debounce PASSED       [ 81%]
tests/test_upload_engine.py::test_conflict_skip PASSED                   [ 87%]
tests/test_upload_engine.py::test_conflict_replace PASSED                [ 93%]
tests/test_upload_engine.py::test_conflict_keep_both_renaming PASSED     [100%]
============================= 16 passed in 2.34s ==============================
```

---

## 8. การ Build เป็นไฟล์ Windows EXE ด้วย PyInstaller

โปรเจกต์มีสคริปต์ `build_exe.py` เตรียมไว้ให้เรียบร้อยแล้ว:

### คำสั่งคอมไพล์:
```powershell
python build_exe.py
```

หรือใช้คำสั่ง PyInstaller โดยตรง:
```powershell
pyinstaller --name="GoogleDriveAutoPush" --onefile --noconsole --clean `
  --hidden-import=PySide6.QtCore `
  --hidden-import=PySide6.QtGui `
  --hidden-import=PySide6.QtWidgets `
  --hidden-import=googleapiclient.discovery `
  --hidden-import=googleapiclient.http `
  --hidden-import=google_auth_oauthlib.flow `
  --hidden-import=google.auth.transport.requests `
  --hidden-import=watchdog.observers.winapi `
  --hidden-import=sqlite3 `
  main.py
```

เมื่อเสร็จสิ้น คุณจะได้ไฟล์ **`dist\GoogleDriveAutoPush.exe`** เป็นโปรแกรมแบบ Standalone สามารถดับเบิ้ลคลิกรันบนเครื่อง Windows 10/11 เครื่องใดก็ได้โดยไม่ต้องติดตั้ง Python!

---

## 9. ความปลอดภัยและความเป็นส่วนตัว (Security)

1. **OAuth 2.0 มาตรฐานสากล**:
   * การล็อกอินทำผ่านหน้าเว็บทางการของ Google เท่านั้น
   * โปรแกรม **ไม่เคยและไม่มีทางเก็บรหัสผ่าน Google** ของผู้ใช้
2. **การจัดเก็บข้อมูลส่วนตัว**:
   * ข้อมูล `token.json` และฐานข้อมูลประวัติจะถูกเก็บอยู่ในเครื่องคอมพิวเตอร์ของคุณในโฟลเดอร์ `data/` เท่านั้น ไม่มีการส่งข้อมูลใดๆ ไปยังเซิร์ฟเวอร์ภายนอก
3. **Sensitive Data Masking**:
   * ระบบ Logger มีตัวกรอง Mask ข้อมูลความลับ (เช่น Access Token, Refresh Token, Client Secret) อัตโนมัติ ป้องกันไม่ให้หลุดรั่วไปยัง Log File

---

## สรุปภาพรวม
**Google Drive AutoPush** พัฒนาขึ้นมาเพื่อแก้ปัญหาการต้องสลับไปมาระหว่างโปรแกรมจัดการไฟล์และหน้าเว็บ Google Drive ด้วยการรวมความสามารถในการ **สร้างโฟลเดอร์ใหม่บนคลาวด์ได้ทันท่วงที**, ระบบเลือกโฟลเดอร์ปลายทางที่แม่นยำ, การอัปโหลดที่เสถียรพร้อมแถบแสดงความคืบหน้าอย่างละเอียด และระบบซิงค์ไฟล์อัตโนมัติที่ปลอดภัยสำหรับผู้ใช้งาน Windows ทุกคน!
