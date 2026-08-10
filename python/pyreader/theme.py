"""Application light/dark theme stylesheets and widget style helpers."""

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
    color: #212529;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
    color: #212529;
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
    color: #495057;
}
QTabBar::tab:selected {
    background: #ffffff;
    color: #212529;
    font-weight: bold;
}
QPlainTextEdit, QLineEdit, QSpinBox, QComboBox {
    background: #ffffff;
    color: #212529;
    border: 1px solid #ced4da;
    border-radius: 4px;
    selection-background-color: #b8daff;
    selection-color: #212529;
}
QTableWidget {
    background: #ffffff;
    color: #212529;
    gridline-color: #dee2e6;
    border: 1px solid #ced4da;
    alternate-background-color: #f1f3f5;
}
QHeaderView::section {
    background: #e9ecef;
    color: #212529;
    padding: 4px;
    border: none;
    font-weight: bold;
}
QPushButton {
    background: #ffffff;
    color: #212529;
    border: 1px solid #ced4da;
    border-radius: 4px;
    padding: 5px 10px;
}
QPushButton:hover {
    background: #e9ecef;
}
QPushButton:pressed {
    background: #dee2e6;
}
QProgressBar {
    background: #e9ecef;
    color: #212529;
    border: 1px solid #ced4da;
    border-radius: 5px;
    text-align: center;
}
QProgressBar::chunk {
    border-radius: 4px;
}
QLabel {
    color: #212529;
}
QMenuBar {
    background: #f8f9fa;
    color: #212529;
}
QMenuBar::item:selected {
    background: #dee2e6;
}
QMenu {
    background: #ffffff;
    color: #212529;
    border: 1px solid #ced4da;
}
QMenu::item:selected {
    background: #0d6efd;
    color: #ffffff;
}
QStatusBar {
    background: #e9ecef;
    color: #495057;
}
QScrollBar:vertical {
    background: #f1f3f5;
    width: 12px;
}
QScrollBar::handle:vertical {
    background: #ced4da;
    border-radius: 4px;
    min-height: 24px;
}
"""

DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #1e1e2e;
    color: #e8eaed;
}
QGroupBox {
    font-weight: bold;
    border: 1px solid #3d3d5c;
    border-radius: 6px;
    margin-top: 8px;
    padding-top: 10px;
    color: #e8eaed;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
    color: #e8eaed;
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
    color: #e8eaed;
    border: 1px solid #3d3d5c;
    border-radius: 4px;
    selection-background-color: #4a6fa5;
    selection-color: #ffffff;
}
QTableWidget {
    background: #2a2a3d;
    color: #e8eaed;
    gridline-color: #3d3d5c;
    border: 1px solid #3d3d5c;
    alternate-background-color: #252535;
}
QHeaderView::section {
    background: #3d3d5c;
    color: #e8eaed;
    padding: 4px;
    border: none;
    font-weight: bold;
}
QPushButton {
    background: #3d3d5c;
    color: #e8eaed;
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
QProgressBar {
    background: #252535;
    color: #e8eaed;
    border: 1px solid #3d3d5c;
    border-radius: 5px;
    text-align: center;
}
QProgressBar::chunk {
    border-radius: 4px;
}
QLabel {
    color: #e8eaed;
}
QMenuBar {
    background: #2a2a3d;
    color: #e8eaed;
}
QMenuBar::item:selected {
    background: #3d3d5c;
}
QMenu {
    background: #2a2a3d;
    color: #e8eaed;
    border: 1px solid #3d3d5c;
}
QMenu::item:selected {
    background: #4a6fa5;
}
QStatusBar {
    background: #2a2a3d;
    color: #b0b0b0;
}
QScrollBar:vertical {
    background: #252535;
    width: 12px;
}
QScrollBar::handle:vertical {
    background: #4d4d6c;
    border-radius: 4px;
    min-height: 24px;
}
"""

# Accent colors — title tints are lightened in dark mode for readability.
ACCENT = {
    'green': ('#28a745', '#5dd879'),
    'teal': ('#17a2b8', '#5bc0de'),
    'purple': ('#6f42c1', '#a98eda'),
    'neutral': ('#495057', '#ced4da'),
    'orange': ('#fd7e14', '#ffb366'),
    'blue': ('#007bff', '#6ea8fe'),
}

SEMANTIC = {
    'success': ('#28a745', '#5dd879'),
    'warning': ('#d39e00', '#ffc107'),
    'danger': ('#dc3545', '#f07178'),
    'info': ('#17a2b8', '#5bc0de'),
    'muted': ('#6c757d', '#adb5bd'),
}


def stylesheet(dark: bool) -> str:
    return DARK_STYLE if dark else LIGHT_STYLE


def _pick(pair: tuple[str, str], dark: bool) -> str:
    return pair[1] if dark else pair[0]


def accent_color(name: str, dark: bool) -> str:
    return _pick(ACCENT[name], dark)


def semantic_color(name: str, dark: bool) -> str:
    return _pick(SEMANTIC[name], dark)


def group_box_style(accent: str, dark: bool, border_width: int = 2) -> str:
    color = accent_color(accent, dark)
    return (
        f'QGroupBox {{ font-weight: bold; border: {border_width}px solid {color}; '
        f'border-radius: 6px; margin-top: 6px; padding-top: 10px; }} '
        f'QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 5px; color: {color}; }}'
    )


def badge_style(kind: str, dark: bool) -> str:
    """Status badge: success, danger, warning, idle, neutral."""
    palettes = {
        'success': {
            False: ('#155724', '#d4edda', '#c3e6cb'),
            True: ('#b7f0c6', '#1e3d2b', '#2d5a3d'),
        },
        'danger': {
            False: ('#721c24', '#f8d7da', '#f5c6cb'),
            True: ('#ffb3b8', '#3d1f24', '#5c2d33'),
        },
        'warning': {
            False: ('#856404', '#fff3cd', '#ffeeba'),
            True: ('#ffe08a', '#3d3520', '#5c5030'),
        },
        'idle': {
            False: ('#383d41', '#e2e3e5', '#d6d8db'),
            True: ('#c8ccd0', '#2e3033', '#45484c'),
        },
        'neutral': {
            False: ('#333333', '#e9ecef', '#ced4da'),
            True: ('#e8eaed', '#3d3d5c', '#4d4d6c'),
        },
    }
    fg, bg, border = palettes.get(kind, palettes['neutral'])[dark]
    return (
        f'font-weight: bold; font-size: 13px; color: {fg}; background: {bg}; '
        f'border: 1px solid {border}; border-radius: 4px; padding: 5px 12px;'
    )


def badge_style_compact(kind: str, dark: bool) -> str:
    base = badge_style(kind, dark)
    return base.replace('padding: 5px 12px;', 'padding: 5px;').replace('font-size: 13px;', 'font-size: 13px;')


def action_button_style(color: str, *, large: bool = False) -> str:
    size = 'font-size: 13px;' if large else ''
    padding = '7px 14px;' if large else '7px 12px;'
    return f'font-weight: bold; padding: {padding} background-color: {color}; color: #ffffff; border-radius: 4px; {size}'


def progress_bar_style(chunk_color: str, dark: bool, height: int = 22) -> str:
    return (
        f'QProgressBar {{ text-align: center; height: {height}px; border-radius: 5px; '
        f'background: {"#252535" if dark else "#e9ecef"}; '
        f'color: {"#e8eaed" if dark else "#212529"}; '
        f'border: 1px solid {"#3d3d5c" if dark else "#ced4da"}; }} '
        f'QProgressBar::chunk {{ background-color: {chunk_color}; border-radius: 4px; }}'
    )


def health_alert_style(severity: str, dark: bool) -> str:
    palettes = {
        'info': {
            False: ('#0c5460', '#d1ecf1', '#bee5eb'),
            True: ('#a8e6f0', '#1a3a40', '#2a5560'),
        },
        'warning': {
            False: ('#856404', '#fff3cd', '#ffeeba'),
            True: ('#ffe08a', '#3d3520', '#5c5030'),
        },
        'critical': {
            False: ('#721c24', '#f8d7da', '#f5c6cb'),
            True: ('#ffb3b8', '#3d1f24', '#5c2d33'),
        },
    }
    fg, bg, border = palettes.get(severity, palettes['info'])[dark]
    return f'padding: 10px; border-radius: 6px; background: {bg}; border: 1px solid {border}; color: {fg};'


def muted_label_style(dark: bool) -> str:
    return f'font-size: 11px; color: {semantic_color("muted", dark)};'


def status_label_style(dark: bool) -> str:
    color = semantic_color('muted', dark)
    return f'font-style: italic; color: {color}; padding-left: 4px;'


def value_label_style(*, large: bool = False, color: str | None = None, dark: bool = False) -> str:
    parts = ['font-weight: bold;']
    if large:
        parts.append('font-size: 15px;')
    if color:
        parts.append(f'color: {color};')
    return ' '.join(parts)


def soc_label_style(tier: str, dark: bool) -> str:
    colors = {
        'success': semantic_color('success', dark),
        'warning': semantic_color('warning', dark),
        'danger': semantic_color('danger', dark),
    }
    return f'font-size: 38px; font-weight: bold; color: {colors.get(tier, colors["success"])};'


def pin_card_style(dark: bool) -> str:
    if dark:
        return (
            'background: #2a2a3d; border: 1px solid #3d3d5c; border-radius: 8px; '
            'padding: 12px; color: #e8eaed;'
        )
    return (
        'background: #ffffff; border: 1px solid #dee2e6; border-radius: 8px; '
        'padding: 12px; color: #212529;'
    )


def step_card_style(dark: bool, accent: str = 'blue') -> str:
    color = accent_color(accent, dark)
    bg = '#252535' if dark else '#f8f9fa'
    border = '#3d3d5c' if dark else '#dee2e6'
    return (
        f'background: {bg}; border-left: 4px solid {color}; border-top: 1px solid {border}; '
        f'border-right: 1px solid {border}; border-bottom: 1px solid {border}; '
        f'border-radius: 4px; padding: 10px 12px; color: {"#e8eaed" if dark else "#212529"};'
    )
