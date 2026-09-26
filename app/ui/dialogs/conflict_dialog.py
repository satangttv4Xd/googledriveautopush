"""
Conflict Policy Selection Dialog.
หน้าต่าง Dialog สำหรับให้ผู้ใช้เลือกนโยบายจัดการกรณีชื่อไฟล์ซ้ำกับที่มีอยู่แล้วบน Google Drive
รองรับ 3 ตัวเลือก: ข้ามไฟล์ (Skip), เขียนทับไฟล์เดิม (Replace), หรือเก็บไว้ทั้งคู่โดยตั้งชื่อใหม่ (Keep Both)
"""
# นำเข้า Qt Core สำหรับคุณสมบัติพื้นฐาน
from PySide6.QtCore import Qt
# นำเข้า Widgets สำหรับสร้างหน้าต่าง UI
from PySide6.QtWidgets import (
    QButtonGroup,   # กลุ่มสำหรับจัดการ Radio Button ให้เลือกได้อันเดียว
    QDialog,        # คลาสแม่ของหน้าต่าง Modal Dialog
    QHBoxLayout,    # เลย์เอาต์แนวนอน
    QLabel,         # ป้ายข้อความ
    QPushButton,    # ปุ่มกด
    QRadioButton,   # ปุ่มเลือกแบบตัวเลือกเดียว
    QVBoxLayout,    # เลย์เอาต์แนวตั้ง
)
# นำเข้าคลาส ConflictPolicy ที่เก็บค่าคงที่ของนโยบาย
from config.constants import ConflictPolicy


class ConflictPolicyDialog(QDialog):
    """หน้าต่างสำหรับตั้งค่านโยบายเมื่อตรวจพบไฟล์ซ้ำบน Google Drive"""

    def __init__(self, current_policy: str = ConflictPolicy.KEEP_BOTH, parent=None):
        # เรียกคอนสตรักเตอร์ของ QDialog
        super().__init__(parent)
        # กำหนดชื่อ Title ของหน้าต่าง Dialog
        self.setWindowTitle("Duplicate File Policy - นโยบายจัดการไฟล์ซ้ำ")
        # กำหนดความกว้างขั้นต่ำของหน้าต่าง
        self.setMinimumWidth(440)
        # กำหนดให้เป็น Modal (ผู้ใช้ต้องจัดการหน้าต่างนี้ก่อนกลับไปหน้าต่างหลัก)
        self.setModal(True)

        # เก็บนโยบายปัจจุบันที่เลือกไว้
        self.selected_policy = current_policy
        # เริ่มต้นสร้างและจัดวางวิดเจ็ต UI
        self._init_ui()

    def _init_ui(self):
        """กำหนดการจัดวางองค์ประกอบบนหน้าต่าง"""
        # สร้างเลย์เอาต์แนวตั้งหลัก
        layout = QVBoxLayout(self)
        # กำหนดระยะห่างระหว่างแต่ละวิดเจ็ต
        layout.setSpacing(18)
        # กำหนดระยะขอบ (Margin) ของหน้าต่าง
        layout.setContentsMargins(24, 24, 24, 24)

        # ป้ายหัวข้อของหน้าต่าง
        title_label = QLabel("⚠️ Existing File Resolution Policy (นโยบายจัดการไฟล์ซ้ำ)")
        # ตกแต่งสีและขนาดฟอนต์หัวข้อ
        title_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #fbbf24;")
        # เพิ่มหัวข้อลงเลย์เอาต์
        layout.addWidget(title_label)

        # ป้ายข้อความอธิบายการทำงาน
        desc_label = QLabel(
            "เลือกวิธีการทำงานเมื่อตรวจพบว่ามีไฟล์ชื่อเดียวกันอยู่แล้วในโฟลเดอร์ปลายทางบน Google Drive:"
        )
        # อนุญาตให้ตัดคำขึ้นบรรทัดใหม่อัตโนมัติ
        desc_label.setWordWrap(True)
        # กำหนดสีและขนาดฟอนต์คำอธิบาย
        desc_label.setStyleSheet("color: #94a3b8; font-size: 12px;")
        # เพิ่มคำอธิบายลงเลย์เอาต์
        layout.addWidget(desc_label)

        # สร้างกลุ่มสำหรับ Radio Buttons
        self.btn_group = QButtonGroup(self)

        # ตัวเลือกที่ 1: Skip ข้ามการอัปโหลดไฟล์ซ้ำ
        self.radio_skip = QRadioButton("1. Skip (ข้ามไฟล์)")
        self.radio_skip.setToolTip("ไม่อัปโหลดหากพบว่ามีไฟล์ชื่อเดียวกันอยู่แล้วบน Google Drive")
        
        # ตัวเลือกที่ 2: Replace เขียนทับเนื้อหาไฟล์เดิม
        self.radio_replace = QRadioButton("2. Replace (เขียนทับไฟล์เดิม)")
        self.radio_replace.setToolTip("อัปเดตข้อมูลไฟล์เดิมบน Google Drive ด้วยเนื้อหาใหม่")

        # ตัวเลือกที่ 3: Keep Both บันทึกเป็นไฟล์ใหม่พร้อมตั้งชื่อต่อท้าย
        self.radio_keep_both = QRadioButton("3. Keep Both (เก็บไว้ทั้งคู่ - ตั้งชื่อใหม่)")
        self.radio_keep_both.setToolTip("อัปโหลดเป็นไฟล์ใหม่โดยต่อท้ายชื่อด้วยตัวเลข เช่น filename (1).ext")

        # เพิ่มปุ่ม Radio ลงใน ButtonGroup เพื่อให้เลือกได้เพียงตัวเลือกเดียวในเวลาเดียวกัน
        self.btn_group.addButton(self.radio_skip)
        self.btn_group.addButton(self.radio_replace)
        self.btn_group.addButton(self.radio_keep_both)

        # ตรวจสอบเพื่อตั้งค่าเลือกปุ่มเริ่มต้นตามนโยบายปัจจุบัน
        if self.selected_policy == ConflictPolicy.SKIP:
            self.radio_skip.setChecked(True)
        elif self.selected_policy == ConflictPolicy.REPLACE:
            self.radio_replace.setChecked(True)
        else:
            self.radio_keep_both.setChecked(True)

        # เพิ่มปุ่มตัวเลือกลงในเลย์เอาต์หลักตามลำดับ
        layout.addWidget(self.radio_keep_both)
        layout.addWidget(self.radio_skip)
        layout.addWidget(self.radio_replace)

        # สร้างเลย์เอาต์แนวนอนสำหรับปุ่มกดยืนยัน/ยกเลิก
        btn_layout = QHBoxLayout()
        # ดันปุ่มไปทางขวาสุด
        btn_layout.addStretch()

        # ปุ่มยกเลิก (Cancel)
        self.cancel_btn = QPushButton("Cancel (ยกเลิก)")
        # เชื่อมปุ่มยกเลิกเข้ากับเมธอด reject ของ QDialog
        self.cancel_btn.clicked.connect(self.reject)
        # เพิ่มปุ่มยกเลิกลงเลย์เอาต์
        btn_layout.addWidget(self.cancel_btn)

        # ปุ่มยืนยัน (Confirm)
        self.confirm_btn = QPushButton("Confirm (ยืนยัน)")
        # ตกแต่งปุ่มยืนยันด้วยสีน้ำเงินโดดเด่น
        self.confirm_btn.setStyleSheet("background-color: #2563eb; color: white; font-weight: bold;")
        # เชื่อมปุ่มยืนยันเข้ากับเมธอด _save_and_accept
        self.confirm_btn.clicked.connect(self._save_and_accept)
        # เพิ่มปุ่มยืนยันลงเลย์เอาต์
        btn_layout.addWidget(self.confirm_btn)

        # เพิ่มแถวปุ่มกดลงในเลย์เอาต์หลัก
        layout.addLayout(btn_layout)

    def _save_and_accept(self):
        """บันทึกนโยบายที่เลือกและปิดหน้าต่างแบบยอมรับ (Accepted)"""
        # ตรวจสอบว่าผู้ใช้เลือกตัวเลือกใด
        if self.radio_skip.isChecked():
            self.selected_policy = ConflictPolicy.SKIP
        elif self.radio_replace.isChecked():
            self.selected_policy = ConflictPolicy.REPLACE
        else:
            self.selected_policy = ConflictPolicy.KEEP_BOTH
        # ส่งผลลัพธ์ Accepted และปิด Dialog
        self.accept()

    def get_policy(self) -> str:
        """ส่งคืนค่า String ของนโยบายที่ผู้ใช้เลือก"""
        return self.selected_policy
