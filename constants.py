from pathlib import Path

# --- Configuration ---
APP_NAME = "BackItUp"
CONFIG_DIR = Path("BackItUp/Config")
DATA_DIR = Path("BackItUp/Data") # Currently unused, but good practice

# --- Dark Theme Stylesheet ---
DARK_STYLESHEET = """
QWidget {
    background-color: #1e1e1e;
    color: #ffffff;
    font-size: 12pt;
    padding: 5px;
}
QMainWindow {
    background-color: #1e1e1e;
}
QTabWidget::pane {
    border-top: 2px solid #333333;
}
QTabBar::tab {
    background: #333333;
    color: #b0b0b0;
    border: 1px solid #1e1e1e;
    border-bottom-color: #333333; /* Same as pane border color */
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    min-width: 8ex;
    padding: 5px;
}
QTabBar::tab:selected, QTabBar::tab:hover {
    background: #4f4f4f;
    color: #ffffff;
}
QTabBar::tab:selected {
    border-color: #4f4f4f;
    border-bottom-color: #4f4f4f; /* Same as selected tab background */
}
QTabBar::tab:!selected {
    margin-top: 2px; /* make non-selected tabs look smaller */
}
QPushButton {
    background-color: #383838;
    border: 1px solid #444444;
    padding: 8px;
    min-width: 80px;
    border-radius: 4px;
}
QPushButton:hover {
    background-color: #505050;
    border: 1px solid #666666;
}
QPushButton:pressed {
    background-color: #2a2a2a;
}
QPushButton:disabled {
    background-color: #3f3f3f;
    color: #777777;
    border-color: #4f4f4f;
}
QListWidget, QTreeView, QTextEdit, QLineEdit {
    background-color: #2d2d2d;
    border: 1px solid #444444;
    border-radius: 4px;
    padding: 2px;
}
QListWidget::item:selected, QTreeView::item:selected {
    background-color: #0d47a1; /* Darker blue accent for selection */
    color: #ffffff;
}
QListWidget::item:hover, QTreeView::item:hover {
    background-color: #4f4f4f;
}
/* Removed custom QTreeView::branch styling to test default indicators */
QScrollBar:vertical {
    border: 1px solid #4f4f4f;
    background: #3c3c3c;
    width: 10px;
    margin: 0px 0px 0px 0px;
}
QScrollBar::handle:vertical {
    background: #5a5a5a;
    min-height: 20px;
    border-radius: 5px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
    background: none;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}
QScrollBar:horizontal {
    border: 1px solid #4f4f4f;
    background: #3c3c3c;
    height: 10px;
    margin: 0px 0px 0px 0px;
}
QScrollBar::handle:horizontal {
    background: #5a5a5a;
    min-width: 20px;
    border-radius: 5px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
    background: none;
}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
}
QSplitter::handle {
    background-color: #4f4f4f;
    border: 1px solid #5a5a5a;
    height: 5px; /* Horizontal splitter */
    width: 5px;  /* Vertical splitter */
}
QSplitter::handle:horizontal {
    height: 5px;
}
QSplitter::handle:vertical {
    width: 5px;
}
QSplitter::handle:hover {
    background-color: #5a5a5a;
}
QProgressBar {
    border: 1px solid #444444;
    border-radius: 5px;
    text-align: center;
    background-color: #2d2d2d;
    color: #ffffff; /* Ensure text is visible */
    padding: 1px;
    height: 18px;
}
QProgressBar::chunk {
    background-color: #0d6efd; /* Modern blue accent */
    border-radius: 4px; /* Match progress bar radius */
    margin: 1px; /* Small margin for better look */
}
QProgressBar::chunk:disabled { /* Style for completed/failed states */
    background-color: #5a5a5a;
}
/* Specific styles for progress bar states */
QProgressBar[state="success"]::chunk {
    background-color: #198754; /* Darker green */
}
QProgressBar[state="warning"]::chunk {
    background-color: #ffc107; /* Yellow/amber for warnings */
}
QProgressBar[state="failed"]::chunk {
    background-color: #dc3545; /* Modern red */
}
QProgressBar[state="cancelled"]::chunk {
    background-color: #6c757d; /* Modern grey */
}
QComboBox {
    border: 1px solid #4f4f4f;
    border-radius: 4px;
    padding: 1px 18px 1px 3px;
    min-width: 6em;
    background-color: #3c3c3c;
}
QComboBox:editable {
    background: #3c3c3c;
}
QComboBox:!editable, QComboBox::drop-down:editable {
     background: #4a4a4a;
}
/* QComboBox gets the "on" state when the popup is open */
QComboBox:!editable:on, QComboBox::drop-down:editable:on {
    background: #5a5a5a;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 15px;
    border-left-width: 1px;
    border-left-color: #4f4f4f;
    border-left-style: solid;
    border-top-right-radius: 3px;
    border-bottom-right-radius: 3px;
}
QComboBox::down-arrow {
    image: url(:/qt-project.org/styles/commonstyle/images/arrow-down-16.png); /* Use a standard down arrow */
}
QComboBox::down-arrow:on { /* shift the arrow when popup is open */
    top: 1px;
    left: 1px;
}
QComboBox QAbstractItemView { /* Style the dropdown list */
    border: 1px solid #4f4f4f;
    background-color: #3c3c3c;
    selection-background-color: #3399ff;
    color: #ffffff;
}
QLabel#StatusBar { /* Specific style for the status bar */
    padding: 3px;
    border-top: 1px solid #4f4f4f;
    background-color: #353535; /* Slightly different background */
    font-weight: bold;
}
QListWidget#SchemaList QLabel {
    font-size: 14pt; /* Increase font size from 12pt to 14pt */
    margin: 0; /* No margin */
    padding: 0; /* No padding */
    font-weight: 500; /* Slightly bolder for better readability */
}

QListWidget#SchemaList::item QLabel#InvalidPathIndicator {
    color: #cc3333; /* Red for invalid path 'X' */
    font-weight: bold;
    padding-right: 5px;
}

/* Ensure item text is visible */
QListWidget::item {
    border: 1px solid transparent; /* Transparent border that becomes visible on hover/selection */
    border-radius: 3px;
    margin: 2px;
}
"""
