"""
Modern Dark Mode Theme Stylesheet and Palette for PySide6.
"""

DARK_THEME_QSS = """
/* Global Window and Base Styles */
QWidget {
    background-color: #0f172a;
    color: #f8fafc;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, "Helvetica Neue", sans-serif;
    font-size: 13px;
    selection-background-color: #3b82f6;
    selection-color: #ffffff;
}

QMainWindow, QDialog {
    background-color: #0f172a;
}

/* Sidebar */
#sidebar {
    background-color: #1e293b;
    border-right: 1px solid #334155;
    min-width: 230px;
    max-width: 250px;
}

#sidebarHeader {
    padding: 16px 12px;
    border-bottom: 1px solid #334155;
}

#appLogoTitle {
    font-size: 16px;
    font-weight: 700;
    color: #38bdf8;
}

#appVersionLabel {
    font-size: 11px;
    color: #94a3b8;
}

/* Sidebar Nav Buttons */
QPushButton.nav-btn {
    text-align: left;
    padding: 10px 16px;
    border-radius: 8px;
    font-weight: 600;
    font-size: 13px;
    color: #94a3b8;
    background-color: transparent;
    border: none;
    margin: 2px 8px;
}

QPushButton.nav-btn:hover {
    background-color: #334155;
    color: #ffffff;
}

QPushButton.nav-btn:checked {
    background-color: #2563eb;
    color: #ffffff;
}

/* Content Area */
#contentArea {
    background-color: #0f172a;
    padding: 20px;
}

/* Cards */
QFrame.card {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 16px;
}

QFrame.card:hover {
    border-color: #475569;
}

/* Buttons */
QPushButton {
    background-color: #334155;
    color: #f8fafc;
    border: 1px solid #475569;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #475569;
    border-color: #64748b;
}

QPushButton:pressed {
    background-color: #1e293b;
}

QPushButton:disabled {
    background-color: #1e293b;
    color: #64748b;
    border-color: #334155;
}

QPushButton.primary-btn {
    background-color: #2563eb;
    color: #ffffff;
    border: 1px solid #3b82f6;
}

QPushButton.primary-btn:hover {
    background-color: #1d4ed8;
    border-color: #60a5fa;
}

QPushButton.success-btn {
    background-color: #059669;
    color: #ffffff;
    border: 1px solid #10b981;
}

QPushButton.success-btn:hover {
    background-color: #047857;
    border-color: #34d399;
}

QPushButton.danger-btn {
    background-color: #dc2626;
    color: #ffffff;
    border: 1px solid #ef4444;
}

QPushButton.danger-btn:hover {
    background-color: #b91c1c;
    border-color: #f87171;
}

QPushButton.icon-btn {
    padding: 6px 10px;
    border-radius: 6px;
}

/* Form Controls */
QLineEdit, QComboBox, QSpinBox {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 8px 12px;
    color: #f8fafc;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #3b82f6;
    background-color: #111827;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

QComboBox QAbstractItemView {
    background-color: #1e293b;
    border: 1px solid #334155;
    selection-background-color: #2563eb;
    color: #f8fafc;
}

/* Progress Bar */
QProgressBar {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 6px;
    text-align: center;
    color: #f8fafc;
    font-weight: 600;
    height: 18px;
}

QProgressBar::chunk {
    background-color: #3b82f6;
    border-radius: 5px;
}

QProgressBar.success::chunk {
    background-color: #10b981;
}

/* Tables */
QTableWidget, QTableView {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    gridline-color: #242f44;
    color: #f8fafc;
    alternate-background-color: #182234;
}

QTableWidget::item {
    padding: 8px;
    border-bottom: 1px solid #242f44;
}

QTableWidget::item:selected {
    background-color: #1e3a8a;
    color: #ffffff;
}

QHeaderView::section {
    background-color: #0f172a;
    color: #94a3b8;
    padding: 10px 8px;
    font-weight: 700;
    border: none;
    border-bottom: 1px solid #334155;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #0f172a;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #334155;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #475569;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Breadcrumb Bar */
#breadcrumbBar {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 6px 12px;
}

QPushButton.crumb-btn {
    background-color: transparent;
    border: none;
    color: #38bdf8;
    font-weight: 600;
    padding: 4px 6px;
    border-radius: 4px;
}

QPushButton.crumb-btn:hover {
    background-color: #334155;
    text-decoration: underline;
}

/* Badges */
QLabel.badge {
    border-radius: 4px;
    padding: 2px 8px;
    font-weight: 700;
    font-size: 11px;
}

QLabel.badge-success {
    background-color: #064e3b;
    color: #34d399;
}

QLabel.badge-warning {
    background-color: #78350f;
    color: #fbbf24;
}

QLabel.badge-danger {
    background-color: #7f1d1d;
    color: #f87171;
}

QLabel.badge-info {
    background-color: #1e3a8a;
    color: #60a5fa;
}

/* Drop Area */
#dropArea {
    border: 2px dashed #475569;
    border-radius: 12px;
    background-color: #141f32;
    padding: 24px;
}

#dropArea:hover {
    border-color: #3b82f6;
    background-color: #182844;
}
"""
