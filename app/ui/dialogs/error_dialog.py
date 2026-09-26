"""
Detailed Error Inspection Dialog.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)


class ErrorDetailDialog(QDialog):
    """Displays full error messages with copy-to-clipboard functionality."""

    def __init__(self, filename: str, error_message: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Error Details")
        self.setMinimumSize(480, 320)
        self.setModal(True)

        self.filename = filename
        self.error_message = error_message
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel(f"⚠️ Upload Error: {self.filename}")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #ef4444;")
        layout.addWidget(title)

        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setPlainText(self.error_message or "No additional error details recorded.")
        self.text_area.setStyleSheet("""
            background-color: #0b0f19;
            color: #fca5a5;
            font-family: Consolas, monospace;
            font-size: 12px;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 8px;
        """)
        layout.addWidget(self.text_area)

        # Buttons
        btn_layout = QHBoxLayout()
        
        self.copy_btn = QPushButton("📋 Copy Error")
        self.copy_btn.clicked.connect(self._copy_error)
        btn_layout.addWidget(self.copy_btn)

        btn_layout.addStretch()

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_btn)

        layout.addLayout(btn_layout)

    def _copy_error(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.error_message)
        self.copy_btn.setText("Copied!")
