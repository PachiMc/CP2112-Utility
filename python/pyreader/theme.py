"""Application light/dark theme stylesheets."""

LIGHT_STYLE = """
QMainWindow, QWidget {
    background-color: #f8f9fa;
    color: #212529;
}
QGroupBox {
    font-weight: bold;
    border: 1px solid #ced4da;
    border-radius: 6px;
    margin-top: 8px;
    padding-top: 10px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
}
QTabWidget::pane {
    border: 1px solid #ced4da;
    border-radius: 4px;
    background: #ffffff;
}
QTabBar::tab {
    padding: 8px 14px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    background: #e9ecef;
}
QTabBar::tab:selected {
    background: #ffffff;
    font-weight: bold;
}
QPlainTextEdit, QLineEdit, QTableWidget {
    background: #ffffff;
    border: 1px solid #ced4da;
    border-radius: 4px;
}
QHeaderView::section {
    background: #e9ecef;
    padding: 4px;
    border: none;
    font-weight: bold;
}
QStatusBar {
    background: #e9ecef;
}
"""

DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #1e1e2e;
    color: #e0e0e0;
}
QGroupBox {
    font-weight: bold;
    border: 1px solid #3d3d5c;
    border-radius: 6px;
    margin-top: 8px;
    padding-top: 10px;
    color: #e0e0e0;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
}
QTabWidget::pane {
    border: 1px solid #3d3d5c;
    border-radius: 4px;
    background: #2a2a3d;
}
QTabBar::tab {
    padding: 8px 14px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    background: #2a2a3d;
    color: #b0b0b0;
}
QTabBar::tab:selected {
    background: #3d3d5c;
    color: #ffffff;
    font-weight: bold;
}
QPlainTextEdit, QLineEdit, QSpinBox, QComboBox {
    background: #2a2a3d;
    color: #e0e0e0;
    border: 1px solid #3d3d5c;
    border-radius: 4px;
    selection-background-color: #4a6fa5;
}
QTableWidget {
    background: #2a2a3d;
    color: #e0e0e0;
    gridline-color: #3d3d5c;
    border: 1px solid #3d3d5c;
    alternate-background-color: #252535;
}
QHeaderView::section {
    background: #3d3d5c;
    color: #e0e0e0;
    padding: 4px;
    border: none;
    font-weight: bold;
}
QPushButton {
    background: #3d3d5c;
    color: #e0e0e0;
    border: 1px solid #4d4d6c;
    border-radius: 4px;
    padding: 5px 10px;
}
QPushButton:hover {
    background: #4d4d6c;
}
QPushButton:pressed {
    background: #2d2d4c;
}
QStatusBar {
    background: #2a2a3d;
    color: #b0b0b0;
}
QLabel {
    color: #e0e0e0;
}
QMenuBar {
    background: #2a2a3d;
    color: #e0e0e0;
}
QMenuBar::item:selected {
    background: #3d3d5c;
}
QMenu {
    background: #2a2a3d;
    color: #e0e0e0;
    border: 1px solid #3d3d5c;
}
QMenu::item:selected {
    background: #4a6fa5;
}
"""


def stylesheet(dark: bool) -> str:
    return DARK_STYLE if dark else LIGHT_STYLE
