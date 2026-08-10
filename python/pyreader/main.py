"""CP2112 Battery Analyzer — main GUI entry point.

This module implements the full PySide6 desktop application for reading,
diagnosing, and repairing laptop battery packs via the Silicon Laboratories
CP2112 HID-to-SMBus bridge and the Smart Battery System (SBS v1.1) protocol.
"""
import csv
import json
import logging
import sys
from pathlib import Path

from .paths import resource_path, user_data_dir
from . import sbs
from .theme import (
    action_button_style,
    badge_style,
    badge_style_compact,
    group_box_style,
    health_alert_style,
    muted_label_style,
    pin_card_style,
    progress_bar_style,
    semantic_color,
    soc_label_style,
    status_label_style,
    step_card_style,
    stylesheet,
    value_label_style,
)


def _resource(filename: str) -> Path:
    """Return the absolute path to a file bundled with this package."""
    return resource_path(filename)

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QComboBox, QFileDialog, QFormLayout,
                                QGroupBox, QHBoxLayout, QHeaderView, QLabel,
                                QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit,
                                QProgressBar, QPushButton, QSpinBox,
                                QTableWidget, QTableWidgetItem, QTabWidget,
                                QVBoxLayout, QWidget)

try:
    from . import cp2112
except Exception:
    import importlib
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    cp2112 = importlib.import_module('pyreader.cp2112')

log_file = user_data_dir() / 'cp2112.log'
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s',
                    handlers=[logging.FileHandler(str(log_file), encoding='utf-8'), logging.StreamHandler()])
logger = logging.getLogger('cp2112')


def parse_int(text, default=0):
    text = (text or '').strip()
    if text == '':
        return default
    if text.lower().startswith('0x'):
        return int(text, 16)
    return int(text, 0)


def parse_bytes(text):
    text = (text or '').strip()
    if text == '':
        return b''
    if ',' in text:
        return bytes(int(part.strip(), 0) for part in text.split(',') if part.strip())
    hex_text = ''.join(ch for ch in text if ch.isalnum())
    if len(hex_text) % 2 != 0:
        raise ValueError('Hex string length must be even')
    return bytes.fromhex(hex_text)


def format_bytes(value):
    return sbs.format_bytes(value)


UNSEAL_PRESETS = {
    'TI BQ20Zxx / BQ30xx (0x0414, 0x3672)': (0x0414, 0x3672),
    'Generic / Standard (0x8000, 0x8000)': (0x8000, 0x8000),
    'TI BQ40xx / BQ2084 (0x3672, 0x0414)': (0x3672, 0x0414),
    'Sony / Sanyo (0x1122, 0x3344)': (0x1122, 0x3344),
    'Full Unseal (0xFFFF, 0xFFFF)': (0xFFFF, 0xFFFF),
    'Zero Keys (0x0000, 0x0000)': (0x0000, 0x0000),
}

APP_NAME = 'CP2112 Battery Analyzer'
APP_VERSION = '1.2.0'


class MainWindow(QMainWindow):
    BATTERY_REGISTERS = sbs.BATTERY_REGISTERS

    def __init__(self):
        super().__init__()
        self._settings = QtCore.QSettings('CP2112-Battery-Analyzer', APP_NAME)
        self._dark_mode = self._settings.value('dark_mode', True, type=bool)
        self.setWindowTitle(f'{APP_NAME} v{APP_VERSION}')
        self.resize(1200, 900)
        self.device = None
        self._log_messages = []
        self._last_battery_snapshot = ''
        self._conn_badge_kind = 'danger'
        self._dash_state_kind = 'idle'
        self._soc_tier = 'success'
        self._soh_bar_color = '#17a2b8'
        self._delta_tier = 'success'
        self._health_worst = 'info'

        # Application icon (bundled icon.ico / icon.png)
        icon_path = _resource('icon.ico')
        if not icon_path.exists():
            icon_path = _resource('icon.png')
        if icon_path.exists():
            self.setWindowIcon(QtGui.QIcon(str(icon_path)))

        # Auto-refresh timer (Live Monitoring)
        self.auto_refresh_timer = QtCore.QTimer(self)
        self.auto_refresh_timer.timeout.connect(self._auto_refresh_tick)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        self._build_top_header(main_layout)

        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget, stretch=1)

        self._build_dashboard_tab()
        self._build_full_table_tab()
        self._build_advanced_battery_tab()
        self._build_cp2112_gpio_tab()
        self._build_pinout_guide_tab()
        self._build_logs_tab()

        self._build_menu_bar()
        self._build_status_bar()
        self._apply_theme(self._dark_mode)
        self._load_settings()

        QShortcut(QKeySequence('F5'), self, self.on_refresh_basic_values)

        self._refresh_device_count()
        self._append_log('CP2112 Battery Analyzer ready')

    def _append_log(self, message, error=False):
        timestamp = QtCore.QDateTime.currentDateTime().toString('HH:mm:ss')
        line = f'[{timestamp}] {message}'
        self._log_messages.append(line)
        if hasattr(self, 'log_widget') and self.log_widget is not None:
            self.log_widget.appendPlainText(line)
        if error:
            logger.error(message)
        else:
            logger.info(message)

    def _build_menu_bar(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu('&File')
        file_menu.addAction('Export Battery Report…', self.on_export_battery_report)
        file_menu.addAction('Export Register CSV…', self.on_export_table_csv)
        file_menu.addAction('Export Log…', self.on_export_log)
        file_menu.addSeparator()
        file_menu.addAction('E&xit', self.close, QKeySequence('Ctrl+Q'))

        battery_menu = menu_bar.addMenu('&Battery')
        battery_menu.addAction('Read Battery (F5)', self.on_refresh_basic_values, QKeySequence('F5'))
        battery_menu.addAction('Read All Registers', self.on_read_all_registers_table)
        battery_menu.addAction('Generate Full Report', self.on_read_battery_summary)
        battery_menu.addSeparator()
        battery_menu.addAction('Copy Snapshot to Clipboard', self.on_copy_snapshot)

        view_menu = menu_bar.addMenu('&View')
        self.dark_mode_action = QAction('Dark Mode', self, checkable=True)
        self.dark_mode_action.setChecked(self._dark_mode)
        self.dark_mode_action.triggered.connect(self._toggle_dark_mode)
        view_menu.addAction(self.dark_mode_action)

        help_menu = menu_bar.addMenu('&Help')
        help_menu.addAction('Connection Guide', self._show_guide_tab)
        help_menu.addAction('Run Diagnostics', self.on_diagnostic)
        help_menu.addAction('&About', self._show_about)

    def _build_status_bar(self):
        self.statusBar().showMessage('Ready')

    def _apply_theme(self, dark: bool):
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(stylesheet(dark))
        self._dark_mode = dark
        if hasattr(self, 'dark_mode_action'):
            self.dark_mode_action.setChecked(dark)
        self._refresh_theme_styles()

    def _toggle_dark_mode(self, checked: bool):
        self._apply_theme(checked)
        self._settings.setValue('dark_mode', checked)

    def _show_guide_tab(self):
        for index in range(self.tab_widget.count()):
            if 'Connection Guide' in self.tab_widget.tabText(index):
                self.tab_widget.setCurrentIndex(index)
                return

    def _style_conn_badge(self, kind: str):
        self._conn_badge_kind = kind
        self.conn_status_badge.setStyleSheet(badge_style(kind, self._dark_mode))

    def _style_auto_refresh_btn(self, active: bool):
        color = '#dc3545' if active else '#6c757d'
        self.auto_refresh_btn.setStyleSheet(action_button_style(color))

    def _refresh_theme_styles(self):
        if not hasattr(self, 'tab_widget'):
            return

        dark = self._dark_mode

        self.header_group.setStyleSheet(group_box_style('blue', dark, border_width=1))
        self._style_conn_badge(self._conn_badge_kind)
        self.status_label.setStyleSheet(status_label_style(dark))

        self.soc_box.setStyleSheet(group_box_style('green', dark))
        self.vp_box.setStyleSheet(group_box_style('teal', dark))
        self.cell_box.setStyleSheet(group_box_style('purple', dark))
        self.cap_box.setStyleSheet(group_box_style('neutral', dark))
        self.chg_box.setStyleSheet(group_box_style('orange', dark))
        self.unseal_box.setStyleSheet(group_box_style('blue', dark))

        self.btn_read_info.setStyleSheet(action_button_style('#28a745', large=True))
        self.quick_unseal_btn.setStyleSheet(action_button_style('#007bff', large=True))
        self.quick_seal_btn.setStyleSheet(action_button_style('#dc3545', large=True))
        self._style_auto_refresh_btn(self.auto_refresh_timer.isActive())

        self.dash_state_badge.setStyleSheet(badge_style_compact(self._dash_state_kind, dark))
        self.dash_soc_label.setStyleSheet(soc_label_style(self._soc_tier, dark))
        self.dash_soc_bar.setStyleSheet(progress_bar_style(semantic_color(self._soc_tier, dark), dark))
        self.dash_soh_label.setStyleSheet(value_label_style(color=semantic_color('success', dark)))
        self.dash_soh_bar.setStyleSheet(progress_bar_style(self._soh_bar_color, dark, height=18))
        self.dash_last_update_label.setStyleSheet(muted_label_style(dark))

        for widget in (
            self.dash_voltage_label, self.dash_current_label, self.dash_power_label,
            self.dash_temp_label, self.dash_chg_voltage_label, self.dash_chg_current_label,
        ):
            widget.setStyleSheet(value_label_style(large=True))

        delta_colors = {
            'success': semantic_color('success', dark),
            'warning': semantic_color('warning', dark),
            'danger': semantic_color('danger', dark),
        }
        self.dash_delta_cell_label.setStyleSheet(
            value_label_style(color=delta_colors.get(self._delta_tier))
        )

        self.dash_unseal_btn.setStyleSheet(action_button_style('#007bff'))
        self.dash_seal_btn.setStyleSheet(action_button_style('#dc3545'))
        self.dash_reset_btn.setStyleSheet(action_button_style('#6c757d'))
        self.read_all_table_btn.setStyleSheet(action_button_style('#28a745'))

        if hasattr(self, 'dash_health_alerts'):
            self.dash_health_alerts.setStyleSheet(health_alert_style(self._health_worst, dark))

        if hasattr(self, '_guide_step_labels'):
            for label, accent in self._guide_step_labels:
                label.setStyleSheet(step_card_style(dark, accent))
        if hasattr(self, '_guide_pin_cards'):
            for card in self._guide_pin_cards:
                card.setStyleSheet(pin_card_style(dark))

    def _load_settings(self):
        geometry = self._settings.value('geometry')
        if geometry:
            self.restoreGeometry(geometry)
        address = self._settings.value('battery_address', '0x0B')
        if hasattr(self, 'battery_address_input'):
            self.battery_address_input.setText(str(address))
        interval = self._settings.value('refresh_interval', 2, type=int)
        if hasattr(self, 'refresh_interval_spin'):
            self.refresh_interval_spin.setValue(max(1, min(60, interval)))

    def _save_settings(self):
        self._settings.setValue('geometry', self.saveGeometry())
        if hasattr(self, 'battery_address_input'):
            self._settings.setValue('battery_address', self.battery_address_input.text().strip())
        if hasattr(self, 'refresh_interval_spin'):
            self._settings.setValue('refresh_interval', self.refresh_interval_spin.value())
        self._settings.setValue('dark_mode', self._dark_mode)

    def closeEvent(self, event):
        if self.auto_refresh_timer.isActive():
            self.auto_refresh_timer.stop()
        self._save_settings()
        super().closeEvent(event)

    def _show_about(self):
        QMessageBox.about(
            self,
            f'About {APP_NAME}',
            f'<h3>{APP_NAME}</h3>'
            f'<p>Version {APP_VERSION}</p>'
            f'<p>Smart Battery System (SBS v1.1) diagnostics via the '
            f'Silicon Labs CP2112 HID-to-SMBus adapter.</p>'
            f'<p>Log file: {log_file}</p>',
        )

    def _confirm_action(self, title: str, message: str) -> bool:
        reply = QMessageBox.warning(
            self, title, message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return reply == QMessageBox.Yes

    def _update_health_alerts(self, raw_data: dict):
        alerts = sbs.assess_battery_health(raw_data)
        lines = []
        worst = 'info'
        rank = {'info': 0, 'warning': 1, 'critical': 2}
        for severity, message in alerts:
            icon = {'info': 'ℹ️', 'warning': '⚠️', 'critical': '🚨'}.get(severity, '•')
            lines.append(f'{icon} {message}')
            if rank.get(severity, 0) > rank.get(worst, 0):
                worst = severity
        self.dash_health_alerts.setText('Health assessment:\n' + '\n'.join(lines))
        self._health_worst = worst
        self.dash_health_alerts.setStyleSheet(health_alert_style(worst, self._dark_mode))

    def on_copy_snapshot(self):
        if not self._last_battery_snapshot:
            QMessageBox.information(self, 'Copy Snapshot', 'No battery data yet. Press READ BATTERY first.')
            return
        QApplication.clipboard().setText(self._last_battery_snapshot)
        self._set_status('Battery snapshot copied to clipboard')

    def _set_status(self, message):
        self.status_label.setText(message)
        self.statusBar().showMessage(message)
        self._append_log(message)

    def _ensure_device_open(self, show_warning=True):
        if self.device is not None:
            try:
                if cp2112.is_opened(self.device.device):
                    return True
            except Exception:
                self.device = None

        try:
            count = cp2112.find_devices()
            if count > 0:
                index = self.device_index_input.value() if hasattr(self, 'device_index_input') else 0
                self.device = cp2112.CP2112Device(index=index)
                self.device.configure()
                self._update_device_info()
                self._set_status('Auto-connected to CP2112 adapter')
                return True
        except Exception as exc:
            self._append_log(f'Auto-connect failed: {exc}', error=True)

        if show_warning:
            QMessageBox.warning(
                self,
                'Adapter Not Connected',
                'No open CP2112 adapter was detected.\n\n'
                '1. Plug the CP2112 USB adapter into your PC.\n'
                '2. Connect the SMBus wires (SDA, SCL, GND) to the battery.\n'
                '3. Click "Open Device" or "Detect Devices".'
            )
        return False

    def _build_top_header(self, layout):
        self.header_group = QGroupBox('CP2112 Battery Analyzer — Adapter Control & Quick Commands')
        header = self.header_group
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 8, 10, 8)
        header_layout.setSpacing(8)

        self.conn_status_badge = QLabel('🔴 Disconnected')
        self._style_conn_badge('danger')
        header_layout.addWidget(self.conn_status_badge)

        header_layout.addWidget(QLabel('Index:'))
        self.device_index_input = QSpinBox()
        self.device_index_input.setMinimum(0)
        self.device_index_input.setMaximum(0)
        self.device_index_input.setFixedWidth(50)
        header_layout.addWidget(self.device_index_input)

        self.detect_button = QPushButton('🔍 Detect')
        self.detect_button.clicked.connect(self._refresh_device_count)
        header_layout.addWidget(self.detect_button)

        self.open_button = QPushButton('⚡ Open')
        self.open_button.clicked.connect(self.on_open_device)
        header_layout.addWidget(self.open_button)

        self.close_button = QPushButton('❌ Close')
        self.close_button.clicked.connect(self.on_close_device)
        header_layout.addWidget(self.close_button)

        header_layout.addStretch(1)

        # NLBA Main Action Buttons
        self.btn_read_info = QPushButton('⚡ READ BATTERY')
        self.btn_read_info.clicked.connect(self.on_refresh_basic_values)
        header_layout.addWidget(self.btn_read_info)

        self.quick_unseal_btn = QPushButton('🔓 UNSEAL (DEFAULT KEYS)')
        self.quick_unseal_btn.clicked.connect(self.on_unseal_default_keys)
        header_layout.addWidget(self.quick_unseal_btn)

        self.quick_seal_btn = QPushButton('🔒 SEAL BATTERY')
        self.quick_seal_btn.clicked.connect(self.on_seal_battery)
        header_layout.addWidget(self.quick_seal_btn)

        self.auto_refresh_btn = QPushButton('▶️ AUTO-MONITOR (OFF)')
        self.auto_refresh_btn.clicked.connect(self.on_toggle_auto_refresh)
        header_layout.addWidget(self.auto_refresh_btn)

        header_layout.addWidget(QLabel('Poll (s):'))
        self.refresh_interval_spin = QSpinBox()
        self.refresh_interval_spin.setRange(1, 60)
        self.refresh_interval_spin.setValue(2)
        self.refresh_interval_spin.setFixedWidth(50)
        self.refresh_interval_spin.setToolTip('Auto-monitor polling interval in seconds')
        header_layout.addWidget(self.refresh_interval_spin)

        layout.addWidget(header)

        self.status_label = QLabel('Ready to connect battery')
        layout.addWidget(self.status_label)

    def _build_dashboard_tab(self):
        dash_tab = QWidget()
        tab_layout = QVBoxLayout(dash_tab)
        tab_layout.setContentsMargins(8, 8, 8, 8)
        tab_layout.setSpacing(10)

        grid = QtWidgets.QGridLayout()
        grid.setSpacing(10)

        # Card 1: SOC & State
        self.soc_box = QGroupBox('🔋 State of Charge (SOC) & Health (SOH) — Live')
        soc_box = self.soc_box
        soc_layout = QVBoxLayout(soc_box)
        soc_layout.setContentsMargins(10, 10, 10, 10)
        soc_layout.setSpacing(6)

        self.dash_state_badge = QLabel('STATE: IDLE / STANDBY')
        self.dash_state_badge.setAlignment(QtCore.Qt.AlignCenter)
        soc_layout.addWidget(self.dash_state_badge)

        self.dash_soc_label = QLabel('0 %')
        self.dash_soc_label.setAlignment(QtCore.Qt.AlignCenter)
        soc_layout.addWidget(self.dash_soc_label)

        self.dash_soc_bar = QProgressBar()
        self.dash_soc_bar.setRange(0, 100)
        self.dash_soc_bar.setValue(0)
        self.dash_soc_bar.setTextVisible(True)
        soc_layout.addWidget(self.dash_soc_bar)

        soh_form = QFormLayout()
        self.dash_soh_label = QLabel('-')
        self.dash_max_error_label = QLabel('-')
        soh_form.addRow('Health (SOH %):', self.dash_soh_label)
        soh_form.addRow('Max Error:', self.dash_max_error_label)
        self.dash_soh_bar = QProgressBar()
        self.dash_soh_bar.setRange(0, 100)
        self.dash_soh_bar.setValue(0)
        self.dash_soh_bar.setTextVisible(True)
        soc_layout.addWidget(self.dash_soh_bar)
        soc_layout.addLayout(soh_form)

        self.dash_last_update_label = QLabel('Last update: —')
        soc_layout.addWidget(self.dash_last_update_label)

        grid.addWidget(soc_box, 0, 0)

        # Card 2: Live Telemetry
        self.vp_box = QGroupBox('⚡ Real-Time Telemetry')
        vp_box = self.vp_box
        vp_layout = QFormLayout(vp_box)
        vp_layout.setContentsMargins(10, 10, 10, 10)
        vp_layout.setSpacing(6)
        self.dash_voltage_label = QLabel('-')
        self.dash_current_label = QLabel('-')
        self.dash_avg_current_label = QLabel('-')
        self.dash_power_label = QLabel('-')
        self.dash_temp_label = QLabel('-')

        vp_layout.addRow('Pack Voltage:', self.dash_voltage_label)
        vp_layout.addRow('Actual Current:', self.dash_current_label)
        vp_layout.addRow('Average Current:', self.dash_avg_current_label)
        vp_layout.addRow('Estimated Power:', self.dash_power_label)
        vp_layout.addRow('Cell Temp:', self.dash_temp_label)
        grid.addWidget(vp_box, 0, 1)

        # Card 3: Cell Voltages & Imbalance
        self.cell_box = QGroupBox('🧪 Individual Cell Voltages & Imbalance')
        cell_box = self.cell_box
        cell_layout = QFormLayout(cell_box)
        cell_layout.setContentsMargins(10, 10, 10, 10)
        cell_layout.setSpacing(6)
        self.dash_cell1_label = QLabel('-')
        self.dash_cell2_label = QLabel('-')
        self.dash_cell3_label = QLabel('-')
        self.dash_cell4_label = QLabel('-')
        self.dash_delta_cell_label = QLabel('-')

        cell_layout.addRow('Cell 1:', self.dash_cell1_label)
        cell_layout.addRow('Cell 2:', self.dash_cell2_label)
        cell_layout.addRow('Cell 3:', self.dash_cell3_label)
        cell_layout.addRow('Cell 4:', self.dash_cell4_label)
        cell_layout.addRow('Imbalance (Delta):', self.dash_delta_cell_label)
        grid.addWidget(cell_box, 0, 2)

        # Card 4: Capacities & Runtime
        self.cap_box = QGroupBox('📦 Capacity & Runtime')
        cap_box = self.cap_box
        cap_layout = QFormLayout(cap_box)
        cap_layout.setContentsMargins(10, 10, 10, 10)
        cap_layout.setSpacing(6)
        self.dash_rem_cap_label = QLabel('-')
        self.dash_full_cap_label = QLabel('-')
        self.dash_design_cap_label = QLabel('-')
        self.dash_cycles_label = QLabel('-')
        self.dash_time_empty_label = QLabel('-')
        self.dash_time_full_label = QLabel('-')

        cap_layout.addRow('Remaining Capacity:', self.dash_rem_cap_label)
        cap_layout.addRow('Full Charge Cap (FCC):', self.dash_full_cap_label)
        cap_layout.addRow('Design Capacity:', self.dash_design_cap_label)
        cap_layout.addRow('Cycle Count:', self.dash_cycles_label)
        cap_layout.addRow('Time to Empty:', self.dash_time_empty_label)
        cap_layout.addRow('Time to Full:', self.dash_time_full_label)
        grid.addWidget(cap_box, 1, 0)

        # Card 5: BMS Charging Recommendations
        self.chg_box = QGroupBox('🔌 BMS Charging Recommendations')
        chg_box = self.chg_box
        chg_layout = QFormLayout(chg_box)
        chg_layout.setContentsMargins(10, 10, 10, 10)
        chg_layout.setSpacing(6)
        self.dash_chg_voltage_label = QLabel('-')
        self.dash_chg_current_label = QLabel('-')
        self.dash_design_voltage_label = QLabel('-')

        chg_layout.addRow('Rec. Charging Voltage:', self.dash_chg_voltage_label)
        chg_layout.addRow('Rec. Charging Current:', self.dash_chg_current_label)
        chg_layout.addRow('Design Nominal Voltage:', self.dash_design_voltage_label)
        grid.addWidget(chg_box, 1, 1)

        # Card 6: Chipset Info & Unseal Console
        self.unseal_box = QGroupBox('🔓 Gas Gauge Identification & Security Console')
        unseal_box = self.unseal_box
        unseal_layout = QVBoxLayout(unseal_box)
        unseal_layout.setContentsMargins(10, 10, 10, 10)
        unseal_layout.setSpacing(6)

        info_f = QFormLayout()
        self.dash_device_name_label = QLabel('-')
        self.dash_mfr_name_label = QLabel('-')
        self.dash_chem_label = QLabel('-')
        self.dash_serial_label = QLabel('-')
        self.dash_mfr_date_label = QLabel('-')
        info_f.addRow('Chipset / Device:', self.dash_device_name_label)
        info_f.addRow('Manufacturer:', self.dash_mfr_name_label)
        info_f.addRow('Cell Chemistry:', self.dash_chem_label)
        info_f.addRow('Serial Number:', self.dash_serial_label)
        info_f.addRow('Manufacture Date:', self.dash_mfr_date_label)
        unseal_layout.addLayout(info_f)

        unseal_layout.addWidget(QLabel('Unseal Key Presets:'))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(list(UNSEAL_PRESETS.keys()))
        self.preset_combo.currentIndexChanged.connect(self.on_preset_changed)
        unseal_layout.addWidget(self.preset_combo)

        btn_row = QHBoxLayout()
        self.dash_unseal_btn = QPushButton('🔓 UNSEAL')
        self.dash_unseal_btn.clicked.connect(self.on_unseal_default_keys)

        self.dash_seal_btn = QPushButton('🔒 SEAL')
        self.dash_seal_btn.clicked.connect(self.on_seal_battery)

        self.dash_reset_btn = QPushButton('🔄 RESET BMS')
        self.dash_reset_btn.clicked.connect(self.on_reset_battery)

        btn_row.addWidget(self.dash_unseal_btn)
        btn_row.addWidget(self.dash_seal_btn)
        btn_row.addWidget(self.dash_reset_btn)
        unseal_layout.addLayout(btn_row)

        self.dash_status_flags_label = QLabel('Flags: -')
        self.dash_status_flags_label.setWordWrap(True)
        unseal_layout.addWidget(self.dash_status_flags_label)

        grid.addWidget(unseal_box, 1, 2)

        self.dash_health_alerts = QLabel('Health: connect battery and press READ BATTERY')
        self.dash_health_alerts.setWordWrap(True)
        self._health_worst = 'info'
        tab_layout.addLayout(grid)
        tab_layout.addWidget(self.dash_health_alerts)
        tab_layout.addStretch(1)

        self.tab_widget.addTab(dash_tab, '⚡ Battery Dashboard')

    def _build_full_table_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        ctrl_bar = QWidget()
        ctrl_layout = QHBoxLayout(ctrl_bar)
        ctrl_layout.setContentsMargins(0, 0, 0, 0)

        self.read_all_table_btn = QPushButton('🔄 Read All SBS Registers')
        self.read_all_table_btn.clicked.connect(self.on_read_all_registers_table)

        self.export_csv_btn = QPushButton('💾 Export Table to CSV')
        self.export_csv_btn.clicked.connect(self.on_export_table_csv)

        ctrl_layout.addWidget(self.read_all_table_btn)
        ctrl_layout.addWidget(self.export_csv_btn)
        ctrl_layout.addStretch(1)

        layout.addWidget(ctrl_bar)

        self.reg_table = QTableWidget()
        self.reg_table.setColumnCount(5)
        self.reg_table.setHorizontalHeaderLabels(['Hex Address', 'Register Name', 'Raw Hex Bytes', 'Decoded Value', 'Description / Unit'])
        self.reg_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.reg_table.setAlternatingRowColors(True)

        self.reg_table.setRowCount(len(self.BATTERY_REGISTERS))
        for row, (name, addr) in enumerate(self.BATTERY_REGISTERS.items()):
            self.reg_table.setItem(row, 0, QTableWidgetItem(f'0x{addr:02X}'))
            self.reg_table.setItem(row, 1, QTableWidgetItem(name))
            self.reg_table.setItem(row, 2, QTableWidgetItem('-'))
            self.reg_table.setItem(row, 3, QTableWidgetItem('-'))
            desc = self._get_register_description(name)
            self.reg_table.setItem(row, 4, QTableWidgetItem(desc))

        layout.addWidget(self.reg_table, stretch=1)
        self.tab_widget.addTab(tab, '📋 SBS v1.1 Registers')

    def _get_register_description(self, name):
        return sbs.REGISTER_DESCRIPTIONS.get(name, 'Smart Battery Standard Register')

    def _build_advanced_battery_tab(self):
        adv_tab = QWidget()
        adv_layout = QVBoxLayout(adv_tab)
        adv_layout.setContentsMargins(8, 8, 8, 8)
        adv_layout.setSpacing(10)

        group = QGroupBox('Smart Battery (SMBus SBS v1.1)')
        group_layout = QVBoxLayout(group)
        form_layout = QFormLayout()

        self.battery_address_input = QLineEdit('0x0B')
        self.battery_register_combo = QComboBox()
        self.battery_register_combo.setEditable(True)
        self.battery_register_combo.addItems(list(self.BATTERY_REGISTERS.keys()))
        self.battery_register_combo.setCurrentText('BatteryMode')
        self.battery_read_length_input = QLineEdit('2')

        self.battery_read_button = QPushButton('Read Register')
        self.battery_read_button.clicked.connect(self.on_read_battery_register)
        self.battery_summary_button = QPushButton('Generate Full Battery Report')
        self.battery_summary_button.clicked.connect(self.on_read_battery_summary)
        self.battery_export_button = QPushButton('Export Report (.txt)')
        self.battery_export_button.clicked.connect(self.on_export_battery_report)

        self.battery_unseal_key1_input = QLineEdit('0x0414')
        self.battery_unseal_key2_input = QLineEdit('0x3672')
        self.battery_unseal_button = QPushButton('Custom Manual Unseal')
        self.battery_unseal_button.clicked.connect(self.on_unseal_battery)

        form_layout.addRow('Battery I2C Address:', self.battery_address_input)
        form_layout.addRow('SMBus Register:', self.battery_register_combo)
        form_layout.addRow('Read Length:', self.battery_read_length_input)

        row1 = QWidget()
        r1_lay = QHBoxLayout(row1)
        r1_lay.setContentsMargins(0, 0, 0, 0)
        r1_lay.addWidget(self.battery_read_button)
        r1_lay.addWidget(self.battery_summary_button)
        r1_lay.addWidget(self.battery_export_button)
        form_layout.addRow(row1)

        form_layout.addRow('Unseal Key 1 (Hex):', self.battery_unseal_key1_input)
        form_layout.addRow('Unseal Key 2 (Hex):', self.battery_unseal_key2_input)
        form_layout.addRow(self.battery_unseal_button)

        self.battery_last_value_label = QLabel('-')
        form_layout.addRow('Last Read Value:', self.battery_last_value_label)

        group_layout.addLayout(form_layout)
        group_layout.addWidget(QLabel('Battery Report Preview:'))
        self.battery_report_widget = QPlainTextEdit()
        self.battery_report_widget.setReadOnly(True)
        self.battery_report_widget.setPlaceholderText('Battery report will appear here after reading...')
        group_layout.addWidget(self.battery_report_widget, stretch=1)

        adv_layout.addWidget(group)
        self.tab_widget.addTab(adv_tab, '🔋 Advanced Battery')

    def _build_cp2112_gpio_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        dev_group = QGroupBox('CP2112 Hardware Info')
        dev_layout = QFormLayout(dev_group)
        self.serial_label = QLabel('-')
        self.product_label = QLabel('-')
        self.manufacturer_label = QLabel('-')
        self.path_label = QLabel('-')

        dev_layout.addRow('Serial Number:', self.serial_label)
        dev_layout.addRow('Product:', self.product_label)
        dev_layout.addRow('Manufacturer:', self.manufacturer_label)
        dev_layout.addRow('Device Path:', self.path_label)

        dev_row = QWidget()
        dev_row_lay = QHBoxLayout(dev_row)
        dev_row_lay.setContentsMargins(0, 0, 0, 0)
        self.refresh_info_button = QPushButton('Refresh Info')
        self.refresh_info_button.clicked.connect(self.on_refresh_info)
        self.reset_button = QPushButton('Reset Device')
        self.reset_button.clicked.connect(self.on_reset_device)
        dev_row_lay.addWidget(self.refresh_info_button)
        dev_row_lay.addWidget(self.reset_button)
        dev_layout.addRow(dev_row)
        layout.addWidget(dev_group)

        smbus_group = QGroupBox('Raw SMBus Transfers')
        smbus_layout = QFormLayout(smbus_group)

        self.slave_address_input = QLineEdit('0x16')
        self.read_length_input = QLineEdit('16')
        self.target_address_input = QLineEdit('')
        self.read_button = QPushButton('Read Transfer')
        self.read_button.clicked.connect(self.on_read)
        self.read_result = QLineEdit('')
        self.read_result.setReadOnly(True)

        self.write_data_input = QLineEdit('')
        self.write_button = QPushButton('Write Transfer')
        self.write_button.clicked.connect(self.on_write)
        self.write_result = QLineEdit('')
        self.write_result.setReadOnly(True)

        smbus_layout.addRow('Slave Address:', self.slave_address_input)
        smbus_layout.addRow('Read Length:', self.read_length_input)
        smbus_layout.addRow('Target Address (hex):', self.target_address_input)
        smbus_layout.addRow(self.read_button, self.read_result)
        smbus_layout.addRow('Write Data (hex / bytes):', self.write_data_input)
        smbus_layout.addRow(self.write_button, self.write_result)
        layout.addWidget(smbus_group)

        gpio_group = QGroupBox('GPIO / Latch Control')
        gpio_layout = QFormLayout(gpio_group)
        self.latch_value_label = QLabel('-')
        self.read_latch_button = QPushButton('Read Latch')
        self.read_latch_button.clicked.connect(self.on_read_latch)
        self.write_latch_value_input = QLineEdit('0x00')
        self.write_latch_mask_input = QLineEdit('0xFF')
        self.write_latch_button = QPushButton('Write Latch')
        self.write_latch_button.clicked.connect(self.on_write_latch)
        self.cancel_transfer_button = QPushButton('Cancel Transfer')
        self.cancel_transfer_button.clicked.connect(self.on_cancel_transfer)
        self.cancel_io_button = QPushButton('Cancel I/O')
        self.cancel_io_button.clicked.connect(self.on_cancel_io)

        gpio_layout.addRow(self.read_latch_button, self.latch_value_label)
        gpio_layout.addRow('Latch Value:', self.write_latch_value_input)
        gpio_layout.addRow('Latch Mask:', self.write_latch_mask_input)
        gpio_layout.addRow(self.write_latch_button)
        gpio_layout.addRow(self.cancel_transfer_button, self.cancel_io_button)
        layout.addWidget(gpio_group)

        self.tab_widget.addTab(tab, '🔌 CP2112 & GPIO')

    def _build_pinout_guide_tab(self):
        tab = QWidget()
        outer = QVBoxLayout(tab)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(10)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(12)

        self._guide_pin_cards = []
        self._guide_step_labels = []

        # Pinout diagram
        pinout_group = QGroupBox('🔌 CP2112 to Battery Wiring')
        pinout_layout = QVBoxLayout(pinout_group)

        pin_row = QHBoxLayout()
        adapter_card = QLabel(
            '<b>CP2112 Adapter</b><br><br>'
            '<span style="color:#007bff;">SDA</span> — Data<br>'
            '<span style="color:#17a2b8;">SCL</span> — Clock<br>'
            '<span style="color:#6c757d;">GND</span> — Ground'
        )
        adapter_card.setWordWrap(True)
        battery_card = QLabel(
            '<b>Laptop Battery</b><br><br>'
            'SMBus Data (SDA)<br>'
            'SMBus Clock (SCL)<br>'
            'Ground (− / GND)'
        )
        battery_card.setWordWrap(True)
        arrow_card = QLabel('──────────────►')
        arrow_card.setAlignment(QtCore.Qt.AlignCenter)
        for card in (adapter_card, arrow_card, battery_card):
            card.setStyleSheet(pin_card_style(self._dark_mode))
            self._guide_pin_cards.append(card)
            pin_row.addWidget(card, stretch=1 if card is not arrow_card else 0)
        pinout_layout.addLayout(pin_row)

        tips = QLabel(
            'Use short wires (&lt; 30 cm). Add 4.7 kΩ pull-ups on SDA and SCL if transfers time out. '
            'Default SMBus address: <b>0x0B</b> (7-bit).'
        )
        tips.setWordWrap(True)
        tips.setStyleSheet(muted_label_style(self._dark_mode))
        pinout_layout.addWidget(tips)
        layout.addWidget(pinout_group)

        # Wake-up steps
        wake_group = QGroupBox('💤 Wake Up Sleeping Batteries')
        wake_layout = QVBoxLayout(wake_group)
        wake_steps = [
            ('1', 'blue', 'Deep-sleep batteries show 0 V on output pins and ignore SMBus.'),
            ('2', 'teal', 'Connect the System Present pin (often pin 4 — SysPres / SMBC) to GND for ~2 seconds.'),
            ('3', 'orange', 'Alternative: apply a brief 5 V pulse between B+ and B− for ~1 second.'),
        ]
        for number, accent, text in wake_steps:
            step = QLabel(f'<b>Step {number}.</b> {text}')
            step.setWordWrap(True)
            step.setStyleSheet(step_card_style(self._dark_mode, accent))
            self._guide_step_labels.append((step, accent))
            wake_layout.addWidget(step)
        layout.addWidget(wake_group)

        # Unseal keys table
        keys_group = QGroupBox('🔑 Unseal Key Reference')
        keys_layout = QVBoxLayout(keys_group)
        keys_table = QTableWidget()
        keys_table.setColumnCount(3)
        keys_table.setHorizontalHeaderLabels(['Gas Gauge / Firmware', 'Key 1', 'Key 2'])
        keys_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        keys_table.setEditTriggers(QTableWidget.NoEditTriggers)
        keys_table.setAlternatingRowColors(True)
        key_rows = [
            ('TI BQ20Zxx / BQ30xx (default)', '0x0414', '0x3672'),
            ('TI BQ40xx / BQ2084', '0x3672', '0x0414'),
            ('Generic / Standard firmware', '0x8000', '0x8000'),
            ('Sony / Sanyo OEM', '0x1122', '0x3344'),
            ('Full access (if permitted)', '0xFFFF', '0xFFFF'),
        ]
        keys_table.setRowCount(len(key_rows))
        for row, (name, k1, k2) in enumerate(key_rows):
            keys_table.setItem(row, 0, QTableWidgetItem(name))
            keys_table.setItem(row, 1, QTableWidgetItem(k1))
            keys_table.setItem(row, 2, QTableWidgetItem(k2))
        keys_table.setMaximumHeight(180)
        keys_layout.addWidget(keys_table)
        seal_note = QLabel('Re-seal: write word <b>0x0020</b> to ManufacturerAccess (0x00).')
        seal_note.setWordWrap(True)
        keys_layout.addWidget(seal_note)
        layout.addWidget(keys_group)

        # Troubleshooting
        trouble_group = QGroupBox('🛠️ Troubleshooting')
        trouble_layout = QVBoxLayout(trouble_group)
        trouble_items = [
            ('DEVICE_NOT_FOUND', 'Plug in the CP2112 USB dongle and install the Silicon Labs driver.'),
            ('Transfer timeout', 'Check SDA/SCL wiring; add 4.7 kΩ pull-up resistors.'),
            ('All registers return 0', 'Battery may still be sleeping — see wake-up steps above.'),
            ('Unseal has no effect', 'Try the alternate TI key order (BQ40xx row in the table).'),
        ]
        for title, detail in trouble_items:
            item = QLabel(f'<b>{title}</b> — {detail}')
            item.setWordWrap(True)
            item.setStyleSheet(step_card_style(self._dark_mode, 'neutral'))
            self._guide_step_labels.append((item, 'neutral'))
            trouble_layout.addWidget(item)
        layout.addWidget(trouble_group)

        layout.addStretch(1)
        scroll.setWidget(content)
        outer.addWidget(scroll)
        self.tab_widget.addTab(tab, '📌 Connection Guide')

    def _build_logs_tab(self):
        log_tab = QWidget()
        log_layout = QVBoxLayout(log_tab)
        log_layout.setContentsMargins(8, 8, 8, 8)

        group = QGroupBox('System Logs & CP2112 Diagnostics')
        group_layout = QVBoxLayout(group)

        controls = QWidget()
        ctrl_layout = QHBoxLayout(controls)
        ctrl_layout.setContentsMargins(0, 0, 0, 0)
        self.diagnostic_button = QPushButton('🛠️ Run Diagnostics')
        self.diagnostic_button.clicked.connect(self.on_diagnostic)
        self.clear_log_button = QPushButton('🗑️ Clear Log')
        self.clear_log_button.clicked.connect(self.on_clear_log)
        self.export_log_button = QPushButton('💾 Export Log')
        self.export_log_button.clicked.connect(self.on_export_log)
        ctrl_layout.addWidget(self.diagnostic_button)
        ctrl_layout.addWidget(self.clear_log_button)
        ctrl_layout.addWidget(self.export_log_button)
        ctrl_layout.addStretch(1)

        group_layout.addWidget(controls)

        self.log_widget = QPlainTextEdit()
        self.log_widget.setReadOnly(True)
        self.log_widget.setPlaceholderText('Activity log stream...')
        group_layout.addWidget(self.log_widget, stretch=1)

        log_layout.addWidget(group)
        self.tab_widget.addTab(log_tab, '📜 Diagnostics & Log')

    def _refresh_device_count(self):
        try:
            count = cp2112.find_devices()
            self.device_index_input.setMaximum(max(count - 1, 0))
            if count > 0:
                self.conn_status_badge.setText(f'🟢 {count} CP2112 Device(s) Found')
                self._style_conn_badge('success')
            else:
                self.conn_status_badge.setText('🔴 Disconnected (0 Devices)')
                self._style_conn_badge('danger')
            self._set_status(f'Detected {count} CP2112 device(s)')
        except Exception as exc:
            self._append_log(f'Device detection failed: {exc}', error=True)
            self.conn_status_badge.setText('🔴 DLL / Driver Error')
            self._style_conn_badge('danger')
            self.device_index_input.setMaximum(0)

    def _update_device_info(self):
        if self.device is None:
            self.serial_label.setText('-')
            self.product_label.setText('-')
            self.manufacturer_label.setText('-')
            self.path_label.setText('-')
            self.conn_status_badge.setText('🔴 Disconnected')
            self._style_conn_badge('danger')
            return
        info = self.device.get_info()
        strings = info.get('device_strings', {})
        self.serial_label.setText(strings.get('serial_number', '-'))
        self.product_label.setText(strings.get('product', '-'))
        self.manufacturer_label.setText(strings.get('manufacturer', '-'))
        self.path_label.setText(strings.get('path', '-'))
        self.conn_status_badge.setText(f'🟢 Open ({strings.get("product", "CP2112")})')
        self._style_conn_badge('success')
        self._set_status('CP2112 device ready')

    def _get_report_text(self):
        return '\n'.join(self._log_messages)

    def _write_text_file(self, label, content):
        path, _ = QFileDialog.getSaveFileName(self, f'Save {label}', str(Path.cwd() / f'{label.lower()}.txt'))
        if not path:
            return None
        Path(path).write_text(content, encoding='utf-8')
        return path

    def _resolve_battery_address(self):
        return parse_int(self.battery_address_input.text(), default=0x0B)

    def _resolve_battery_register(self):
        selected = self.battery_register_combo.currentText().strip()
        if selected in self.BATTERY_REGISTERS:
            return self.BATTERY_REGISTERS[selected], selected
        try:
            return parse_int(selected, default=0x00), selected
        except ValueError as exc:
            raise ValueError(f'Invalid register: {selected}') from exc

    def _format_battery_value(self, register_name, data):
        return sbs.format_register_value(register_name, data)

    def on_preset_changed(self):
        preset_name = self.preset_combo.currentText()
        if preset_name in UNSEAL_PRESETS:
            k1, k2 = UNSEAL_PRESETS[preset_name]
            self.battery_unseal_key1_input.setText(f'0x{k1:04X}')
            self.battery_unseal_key2_input.setText(f'0x{k2:04X}')

    def on_toggle_auto_refresh(self):
        if self.auto_refresh_timer.isActive():
            self.auto_refresh_timer.stop()
            self.auto_refresh_btn.setText('▶️ AUTO-MONITOR (OFF)')
            self._style_auto_refresh_btn(False)
            self._set_status('Live monitoring stopped')
        else:
            if not self._ensure_device_open():
                return
            interval_ms = self.refresh_interval_spin.value() * 1000
            self.auto_refresh_timer.start(interval_ms)
            self.auto_refresh_btn.setText('⏹️ STOP MONITORING')
            self._style_auto_refresh_btn(True)
            self._set_status(f'Live monitoring active — polling every {self.refresh_interval_spin.value()} s')

    def _auto_refresh_tick(self):
        try:
            self._refresh_basic_values()
        except Exception as exc:
            self._append_log(f'Auto-refresh tick error: {exc}', error=True)
            self.auto_refresh_timer.stop()
            self.auto_refresh_btn.setText('▶️ AUTO-MONITOR (OFF)')
            self._style_auto_refresh_btn(False)

    def on_open_device(self):
        try:
            if self.device is not None:
                try:
                    already_open = cp2112.is_opened(self.device.device)
                except Exception:
                    already_open = False
                    self.device = None

                if already_open:
                    # Device is already open — just refresh the badge so it
                    # always shows the correct name/state after repeated clicks.
                    self._update_device_info()
                    self._set_status('Device already open — connection info refreshed')
                    return

            index = self.device_index_input.value()
            self.device = cp2112.CP2112Device(index=index)
            self.device.configure()
            self._update_device_info()
        except Exception as exc:
            self._append_log(f'Open device failed: {exc}', error=True)
            self.device = None
            QMessageBox.critical(
                self,
                'Open Device Failure',
                f'Could not open CP2112 device (Index {self.device_index_input.value()}).\n\n'
                f'Detail: {exc}\n\n'
                'Tip: Ensure no other application is using the adapter and re-plug the USB cable.'
            )

    def on_close_device(self):
        try:
            if self.auto_refresh_timer.isActive():
                self.auto_refresh_timer.stop()
                self.auto_refresh_btn.setText('▶️ AUTO-MONITOR (OFF)')

            if self.device is None:
                self._set_status('No open device')
                return
            self.device.close()
            self.device = None
            self._set_status('Device closed')
            self._update_device_info()
        except Exception as exc:
            self._append_log(f'Close device failed: {exc}', error=True)

    def on_refresh_info(self):
        try:
            if not self._ensure_device_open():
                return
            self._update_device_info()
        except Exception as exc:
            self._append_log(f'Refresh device info failed: {exc}', error=True)

    def on_reset_device(self):
        try:
            if not self._ensure_device_open():
                return
            if not self._confirm_action(
                'Reset CP2112 Adapter',
                'Reset the CP2112 USB adapter?\n\nThis does not reset the battery BMS.',
            ):
                return
            self.device.reset()
            self._set_status('CP2112 adapter reset command sent')
        except Exception as exc:
            self._append_log(f'Reset device failed: {exc}', error=True)

    def on_reset_battery(self):
        try:
            if not self._ensure_device_open():
                return
            if not self._confirm_action(
                'Reset Battery BMS',
                'Send BMS reset command (ManufacturerAccess 0x0041)?\n\n'
                'The battery must be unsealed. This may affect gas gauge state.',
            ):
                return
            address = self._resolve_battery_address()
            self.device.reset_battery(address)
            self._set_status('BMS reset command sent (0x0041)')
            self._append_log(f'BMS reset sent to 0x{address:02X}')
        except Exception as exc:
            self._append_log(f'BMS reset failed: {exc}', error=True)

    def on_diagnostic(self):
        try:
            result = cp2112.diagnose(verbose=False)
            self._append_log(f'Diagnostic result: {result}')
            msg = (f"CP2112 Diagnostics Completed:\n"
                   f"• DLL Loaded: {result.get('dll_found')}\n"
                   f"• Library Version: {result.get('library_version', 'N/A')}\n"
                   f"• Devices Found: {result.get('num_devices', 0)}\n"
                   f"• Open State: {result.get('opened', False)}")
            if 'open_error' in result:
                msg += f"\n• Open Error: {result['open_error']}"
            QMessageBox.information(self, 'CP2112 Diagnostics', msg)
            self._set_status('Diagnostics completed')
        except Exception as exc:
            self._append_log(f'Diagnostics failed: {exc}', error=True)

    def on_read(self):
        try:
            if not self._ensure_device_open():
                return
            address = parse_int(self.slave_address_input.text())
            length = parse_int(self.read_length_input.text())
            target = self.target_address_input.text().strip() or None
            data = self.device.read(address, length, target_address=target)
            self.read_result.setText(format_bytes(data))
            self._set_status(f'Read successful: {len(data)} bytes')
        except Exception as exc:
            self._append_log(f'Read failed: {exc}', error=True)

    def on_write(self):
        try:
            if not self._ensure_device_open():
                return
            address = parse_int(self.slave_address_input.text())
            data = parse_bytes(self.write_data_input.text())
            status = self.device.write(address, data)
            self.write_result.setText(str(status))
            self._set_status('Write completed')
        except Exception as exc:
            self._append_log(f'Write failed: {exc}', error=True)

    def on_read_latch(self):
        try:
            if not self._ensure_device_open():
                return
            value = self.device.read_latch()
            self.latch_value_label.setText(f'0x{value:02X}')
            self._set_status(f'Read latch: 0x{value:02X}')
        except Exception as exc:
            self._append_log(f'Read latch failed: {exc}', error=True)

    def on_write_latch(self):
        try:
            if not self._ensure_device_open():
                return
            value = parse_int(self.write_latch_value_input.text())
            mask = parse_int(self.write_latch_mask_input.text())
            self.device.write_latch(value, mask)
            self._set_status(f'Write latch: value=0x{value:02X}, mask=0x{mask:02X}')
        except Exception as exc:
            self._append_log(f'Write latch failed: {exc}', error=True)

    def on_cancel_transfer(self):
        try:
            if not self._ensure_device_open():
                return
            self.device.cancel_transfer()
            self._set_status('Transfer canceled')
        except Exception as exc:
            self._append_log(f'Cancel transfer failed: {exc}', error=True)

    def on_cancel_io(self):
        try:
            if not self._ensure_device_open():
                return
            self.device.cancel_io()
            self._set_status('I/O canceled')
        except Exception as exc:
            self._append_log(f'Cancel I/O failed: {exc}', error=True)

    def on_read_battery_register(self):
        try:
            if not self._ensure_device_open():
                return
            address = self._resolve_battery_address()
            register_address, register_name = self._resolve_battery_register()
            length = parse_int(self.battery_read_length_input.text(), default=2)
            if register_name in {'ManufacturerName', 'DeviceName', 'DeviceChemistry'}:
                length = max(length, 16)
            data = self.device.read_register(address, register_address, length=length)
            display = self._format_battery_value(register_name, data)
            self.battery_last_value_label.setText(display)
            self._set_status(f'Read battery register {register_name} (0x{address:02X})')
            self._append_log(f'Register {register_name} ({register_address:#x}): {display}')
        except Exception as exc:
            self._append_log(f'Read battery register failed: {exc}', error=True)

    def _refresh_basic_values(self):
        if not self._ensure_device_open():
            raise RuntimeError('No open device')

        address = self._resolve_battery_address()
        regs_to_read = list(sbs.DASHBOARD_REGISTERS)

        raw_data = {}
        formatted_data = {}

        for reg_name in regs_to_read:
            try:
                reg_addr = self.BATTERY_REGISTERS[reg_name]
                length = 16 if reg_name in sbs.STRING_REGISTERS else 2
                data = self.device.read_register(address, reg_addr, length=length)
                raw_data[reg_name] = data
                formatted_data[reg_name] = self._format_battery_value(reg_name, data)
            except Exception:
                formatted_data[reg_name] = 'N/A'

        # SOC
        soc_raw = raw_data.get('RelativeStateOfCharge')
        if soc_raw and len(soc_raw) >= 2:
            soc_val = sbs.word_value(soc_raw) or 0
            self.dash_soc_label.setText(f'{soc_val} %')
            self.dash_soc_bar.setValue(min(max(soc_val, 0), 100))
            if soc_val > 50:
                self._soc_tier = 'success'
            elif soc_val >= 20:
                self._soc_tier = 'warning'
            else:
                self._soc_tier = 'danger'
            self.dash_soc_label.setStyleSheet(soc_label_style(self._soc_tier, self._dark_mode))
            self.dash_soc_bar.setStyleSheet(
                progress_bar_style(semantic_color(self._soc_tier, self._dark_mode), self._dark_mode)
            )
        else:
            self.dash_soc_label.setText('- %')
            self.dash_soc_bar.setValue(0)

        # Current & Power
        curr_val = sbs.signed_word_value(raw_data.get('Current')) or 0
        volt_val = sbs.word_value(raw_data.get('Voltage')) or 0

        if curr_val > 0:
            self.dash_state_badge.setText('⚡ CHARGING')
            self._dash_state_kind = 'success'
        elif curr_val < 0:
            self.dash_state_badge.setText('🔋 DISCHARGING')
            self._dash_state_kind = 'warning'
        else:
            self.dash_state_badge.setText('💤 IDLE / STANDBY')
            self._dash_state_kind = 'idle'
        self.dash_state_badge.setStyleSheet(badge_style_compact(self._dash_state_kind, self._dark_mode))

        power_w = abs(volt_val * curr_val) / 1000000.0
        self.dash_voltage_label.setText(formatted_data.get('Voltage', '-'))
        self.dash_current_label.setText(formatted_data.get('Current', '-'))
        self.dash_avg_current_label.setText(formatted_data.get('AverageCurrent', '-'))
        self.dash_power_label.setText(f'{power_w:.2f} W')

        # Cell Voltages & Imbalance Delta
        cell_vals = []
        for i, reg_c in enumerate(['CellVoltage1', 'CellVoltage2', 'CellVoltage3', 'CellVoltage4']):
            c_lbl = getattr(self, f'dash_cell{i+1}_label')
            if reg_c in raw_data and len(raw_data[reg_c]) >= 2:
                v_cell = int.from_bytes(raw_data[reg_c][:2], 'little', signed=False)
                c_lbl.setText(formatted_data.get(reg_c, '-'))
                if v_cell > 0:
                    cell_vals.append(v_cell)
            else:
                c_lbl.setText('-')

        if cell_vals:
            delta_mv = max(cell_vals) - min(cell_vals)
            if delta_mv <= 30:
                self.dash_delta_cell_label.setText(f'{delta_mv} mV (✅ EXCELLENT BALANCE)')
                self._delta_tier = 'success'
            elif delta_mv <= 60:
                self.dash_delta_cell_label.setText(f'{delta_mv} mV (⚠️ MODERATE)')
                self._delta_tier = 'warning'
            else:
                self.dash_delta_cell_label.setText(f'{delta_mv} mV (🚨 HIGH IMBALANCE)')
                self._delta_tier = 'danger'
            self.dash_delta_cell_label.setStyleSheet(
                value_label_style(color=semantic_color(self._delta_tier, self._dark_mode))
            )
        else:
            self.dash_delta_cell_label.setText('-')
            self._delta_tier = 'success'
            self.dash_delta_cell_label.setStyleSheet(value_label_style())

        # Temperature & Capacities
        self.dash_temp_label.setText(formatted_data.get('Temperature', '-'))
        self.dash_max_error_label.setText(formatted_data.get('MaxError', '-'))
        self.dash_rem_cap_label.setText(formatted_data.get('RemainingCapacity', '-'))
        self.dash_full_cap_label.setText(formatted_data.get('FullChargeCapacity', '-'))
        self.dash_design_cap_label.setText(formatted_data.get('DesignCapacity', '-'))
        self.dash_cycles_label.setText(formatted_data.get('CycleCount', '-'))
        self.dash_time_empty_label.setText(formatted_data.get('RunTimeToEmpty', '-'))
        self.dash_time_full_label.setText(formatted_data.get('AverageTimeToFull', '-'))

        # BMS Recommendations
        self.dash_chg_voltage_label.setText(formatted_data.get('ChargingVoltage', '-'))
        self.dash_chg_current_label.setText(formatted_data.get('ChargingCurrent', '-'))
        self.dash_design_voltage_label.setText(formatted_data.get('DesignVoltage', '-'))

        # Info & Serial
        self.dash_mfr_name_label.setText(formatted_data.get('ManufacturerName', '-'))
        self.dash_device_name_label.setText(formatted_data.get('DeviceName', '-'))
        self.dash_chem_label.setText(formatted_data.get('DeviceChemistry', '-'))
        self.dash_serial_label.setText(formatted_data.get('SerialNumber', '-'))
        self.dash_mfr_date_label.setText(formatted_data.get('ManufacturerDate', '-'))
        self.dash_status_flags_label.setText('Flags: ' + formatted_data.get('BatteryStatus', '-'))
        if 'BatteryMode' in formatted_data:
            self.dash_status_flags_label.setText(
                self.dash_status_flags_label.text()
                + ' | Mode: ' + formatted_data.get('BatteryMode', '-')
            )

        soh, soh_str = sbs.calculate_soh(raw_data)
        self.dash_soh_label.setText(soh_str)
        if soh is not None:
            soh_int = min(max(int(soh), 0), 100)
            self.dash_soh_bar.setValue(soh_int)
            if soh_int >= 70:
                self._soh_bar_color = semantic_color('info', self._dark_mode)
            elif soh_int >= 50:
                self._soh_bar_color = semantic_color('warning', self._dark_mode)
            else:
                self._soh_bar_color = semantic_color('danger', self._dark_mode)
            self.dash_soh_bar.setStyleSheet(
                progress_bar_style(self._soh_bar_color, self._dark_mode, height=18)
            )
        else:
            self.dash_soh_bar.setValue(0)

        self._update_health_alerts(raw_data)
        now = QtCore.QDateTime.currentDateTime().toString('yyyy-MM-dd HH:mm:ss')
        self.dash_last_update_label.setText(f'Last update: {now}')

        lines = [f'CP2112 Battery Snapshot — {now}', f'Address: 0x{address:02X}', '']
        for key in sbs.DASHBOARD_REGISTERS:
            if key in formatted_data:
                lines.append(f'{key}: {formatted_data[key]}')
        self._last_battery_snapshot = '\n'.join(lines)

        return formatted_data

    def on_refresh_basic_values(self):
        try:
            values = self._refresh_basic_values()
            self._set_status('Battery data read successfully')
            self._append_log('Battery read OK')
        except Exception as exc:
            self._append_log(f'Read battery info failed: {exc}', error=True)

    def on_read_all_registers_table(self):
        try:
            if not self._ensure_device_open():
                return
            address = self._resolve_battery_address()
            self._set_status('Reading all SBS v1.1 registers — please wait...')

            for row, (name, reg_addr) in enumerate(self.BATTERY_REGISTERS.items()):
                try:
                    length = 16 if name in {'ManufacturerName', 'DeviceName', 'DeviceChemistry'} else 2
                    data = self.device.read_register(address, reg_addr, length=length)
                    raw_str = format_bytes(data)
                    dec_str = self._format_battery_value(name, data)
                    self.reg_table.setItem(row, 2, QTableWidgetItem(raw_str))
                    self.reg_table.setItem(row, 3, QTableWidgetItem(dec_str))
                except Exception as exc:
                    self.reg_table.setItem(row, 2, QTableWidgetItem('Err'))
                    self.reg_table.setItem(row, 3, QTableWidgetItem(f'Error: {exc}'))

            self._set_status('All SBS registers read successfully')
            self._append_log('Full SBS v1.1 register table read completed')
        except Exception as exc:
            self._append_log(f'Read register table failed: {exc}', error=True)

    def on_export_table_csv(self):
        try:
            path, _ = QFileDialog.getSaveFileName(self, 'Save Register Table to CSV', str(Path.cwd() / 'cp2112_battery_registers.csv'), 'CSV Files (*.csv)')
            if not path:
                return
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Hex_Address', 'Register_Name', 'Raw_Hex_Bytes', 'Decoded_Value', 'Description'])
                for row in range(self.reg_table.rowCount()):
                    r_addr = self.reg_table.item(row, 0).text() if self.reg_table.item(row, 0) else ''
                    r_name = self.reg_table.item(row, 1).text() if self.reg_table.item(row, 1) else ''
                    r_raw = self.reg_table.item(row, 2).text() if self.reg_table.item(row, 2) else ''
                    r_dec = self.reg_table.item(row, 3).text() if self.reg_table.item(row, 3) else ''
                    r_desc = self.reg_table.item(row, 4).text() if self.reg_table.item(row, 4) else ''
                    writer.writerow([r_addr, r_name, r_raw, r_dec, r_desc])
            self._set_status(f'Table exported successfully to: {path}')
            QMessageBox.information(self, 'CSV Export', f'Table successfully exported to:\n{path}')
        except Exception as exc:
            self._append_log(f'Export CSV failed: {exc}', error=True)

    def on_unseal_battery(self):
        try:
            if not self._ensure_device_open():
                return
            if not self._confirm_action(
                'Unseal Battery',
                'Send unseal sequence to the battery BMS?\n\n'
                'Only proceed if you understand the risks of modifying BMS settings.',
            ):
                return
            address = self._resolve_battery_address()
            key1 = parse_int(self.battery_unseal_key1_input.text(), default=0x0414)
            key2 = parse_int(self.battery_unseal_key2_input.text(), default=0x3672)
            self.device.unseal(address, key1=key1, key2=key2)
            self._set_status('Unseal sequence sent')
            self._append_log(f'Unseal sequence sent with keys 0x{key1:04X}, 0x{key2:04X}')
            QMessageBox.information(
                self,
                'Unseal Sent',
                f'Unseal sequence sent to battery (0x{address:02X}) using keys:\n'
                f'• Key 1: 0x{key1:04X}\n'
                f'• Key 2: 0x{key2:04X}'
            )
        except Exception as exc:
            self._append_log(f'Unseal failed: {exc}', error=True)

    def on_unseal_default_keys(self):
        try:
            if not self._ensure_device_open():
                return
            if not self._confirm_action(
                'Unseal Battery',
                'Send unseal sequence with the selected preset keys?',
            ):
                return
            address = self._resolve_battery_address()
            preset_name = self.preset_combo.currentText()
            key1, key2 = UNSEAL_PRESETS.get(preset_name, (0x0414, 0x3672))

            self.device.unseal(address, key1=key1, key2=key2)
            self._set_status(f'Unseal sequence sent — preset: {preset_name}')
            self._append_log(f'Default Unseal executed: key1=0x{key1:04X}, key2=0x{key2:04X}')
            QMessageBox.information(
                self,
                'Unseal with Default Keys',
                f'Unseal sequence sent to 0x{address:02X} using preset:\n'
                f'"{preset_name}"\n\n'
                f'Keys: 0x{key1:04X}, 0x{key2:04X}'
            )
        except Exception as exc:
            self._append_log(f'Default Unseal failed: {exc}', error=True)

    def on_seal_battery(self):
        try:
            if not self._ensure_device_open():
                return
            if not self._confirm_action('Seal Battery', 'Re-seal (lock) the battery BMS?'):
                return
            address = self._resolve_battery_address()
            self.device.seal(address)
            self._set_status('SEAL command sent to battery BMS')
            self._append_log('SEAL command sent to battery BMS')
            QMessageBox.information(self, 'SEAL Battery', f'Security lock command (SEAL) sent to battery at 0x{address:02X}.')
        except Exception as exc:
            self._append_log(f'SEAL command failed: {exc}', error=True)

    def on_read_battery_summary(self):
        try:
            if not self._ensure_device_open():
                return
            address = self._resolve_battery_address()
            lines = [
                f'================================================================',
                f'  CP2112 Battery Analyzer — Full Battery Diagnostics Report',
                f'  Smart Battery System (SBS) v1.1 Register Dump',
                f'================================================================',
                f'Date      : {QtCore.QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")}',
                f'I2C Addr  : 0x{address:02X}',
                f'Software  : {APP_NAME} v{APP_VERSION}',
                f'----------------------------------------------------------------'
            ]
            summary_regs = [
                'ManufacturerName', 'DeviceName', 'DeviceChemistry', 'SerialNumber', 'ManufacturerDate',
                'RelativeStateOfCharge', 'AbsoluteStateOfCharge',
                'Voltage', 'Current', 'AverageCurrent', 'Temperature',
                'RemainingCapacity', 'FullChargeCapacity', 'DesignCapacity', 'DesignVoltage',
                'ChargingVoltage', 'ChargingCurrent',
                'CycleCount', 'MaxError', 'RunTimeToEmpty', 'AverageTimeToEmpty',
                'CellVoltage1', 'CellVoltage2', 'CellVoltage3', 'CellVoltage4',
                'BatteryStatus', 'BatteryMode'
            ]

            for reg_name in summary_regs:
                reg_addr = self.BATTERY_REGISTERS[reg_name]
                try:
                    length = 16 if reg_name in {'ManufacturerName', 'DeviceName', 'DeviceChemistry'} else 2
                    data = self.device.read_register(address, reg_addr, length=length)
                    display = self._format_battery_value(reg_name, data)
                    lines.append(f'{reg_name:<24}: {display}')
                except Exception as exc:
                    lines.append(f'{reg_name:<24}: N/A ({exc})')

            report = '\n'.join(lines)
            self.battery_report_widget.setPlainText(report)
            self._set_status('Battery diagnostics report generated')
            self._append_log('Full battery report generated')
            self.on_refresh_basic_values()
        except Exception as exc:
            self._append_log(f'Generate report failed: {exc}', error=True)

    def on_export_battery_report(self):
        try:
            text = self.battery_report_widget.toPlainText().strip()
            if not text:
                QMessageBox.warning(self, 'Export Report', 'No report has been generated yet. Click "Generate Full Battery Report" first.')
                return
            path = self._write_text_file('cp2112_battery_report', text)
            if path:
                self._set_status(f'Report exported to: {path}')
        except Exception as exc:
            self._append_log(f'Export report failed: {exc}', error=True)

    def on_clear_log(self):
        self.log_widget.clear()
        self._log_messages.clear()
        self._append_log('Log cleared')

    def on_export_log(self):
        try:
            path = self._write_text_file('cp2112-log', self._get_report_text())
            if path:
                self._set_status(f'Log exported to: {path}')
        except Exception as exc:
            self._append_log(f'Export log failed: {exc}', error=True)


def main():
    """Entry point for the CP2112 Battery Analyzer standalone application."""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName('CP2112 Battery Analyzer')
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
