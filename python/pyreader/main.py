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

# ---------------------------------------------------------------------------
# Package resource helpers
# ---------------------------------------------------------------------------
_PACKAGE_DIR = Path(__file__).resolve().parent


def _resource(filename: str) -> Path:
    """Return the absolute path to a file bundled with this package."""
    return _PACKAGE_DIR / filename

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtWidgets import (QApplication, QComboBox, QFileDialog, QFormLayout,
                                QGroupBox, QHBoxLayout, QHeaderView, QLabel,
                                QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit,
                                QProgressBar, QPushButton, QSpinBox, QTableWidget,
                                QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget)

try:
    from . import cp2112
except Exception:
    import importlib
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    cp2112 = importlib.import_module('pyreader.cp2112')

log_file = Path(__file__).resolve().parent / 'cp2112.log'
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
    if isinstance(value, (bytes, bytearray)):
        return ' '.join(f'{byte:02X}' for byte in value)
    if isinstance(value, (list, tuple)):
        return ' '.join(f'{byte:02X}' for byte in value)
    return str(value)


UNSEAL_PRESETS = {
    'TI BQ20Zxx / BQ30xx (0x0414, 0x3672)': (0x0414, 0x3672),
    'Generic / Standard (0x8000, 0x8000)': (0x8000, 0x8000),
    'TI BQ40xx / BQ2084 (0x3672, 0x0414)': (0x3672, 0x0414),
    'Sony / Sanyo (0x1122, 0x3344)': (0x1122, 0x3344),
    'Full Unseal (0xFFFF, 0xFFFF)': (0xFFFF, 0xFFFF),
    'Zero Keys (0x0000, 0x0000)': (0x0000, 0x0000),
}


class MainWindow(QMainWindow):
    BATTERY_REGISTERS = {
        'ManufacturerAccess': 0x00,
        'RemainingCapacityAlarm': 0x01,
        'RemainingTimeAlarm': 0x02,
        'BatteryMode': 0x03,
        'AtRate': 0x04,
        'AtRateTimeToEmpty': 0x05,
        'AtRateTimeToFull': 0x06,
        'Temperature': 0x08,
        'Voltage': 0x09,
        'Current': 0x0A,
        'AverageCurrent': 0x0B,
        'MaxError': 0x0C,
        'RelativeStateOfCharge': 0x0D,
        'AbsoluteStateOfCharge': 0x0E,
        'RemainingCapacity': 0x0F,
        'FullChargeCapacity': 0x10,
        'RunTimeToEmpty': 0x11,
        'AverageTimeToEmpty': 0x12,
        'AverageTimeToFull': 0x13,
        'ChargingCurrent': 0x14,
        'ChargingVoltage': 0x15,
        'BatteryStatus': 0x16,
        'CycleCount': 0x17,
        'DesignCapacity': 0x18,
        'DesignVoltage': 0x19,
        'SpecificationInfo': 0x1A,
        'ManufacturerDate': 0x1B,
        'SerialNumber': 0x1C,
        'ManufacturerName': 0x20,
        'DeviceName': 0x21,
        'DeviceChemistry': 0x22,
        'ManufacturerData': 0x23,
        'CellVoltage4': 0x3C,
        'CellVoltage3': 0x3D,
        'CellVoltage2': 0x3E,
        'CellVoltage1': 0x3F,
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle('CP2112 Battery Analyzer — Smart Battery SMBus Tool v1.0')
        self.resize(1200, 900)
        self.device = None
        self._log_messages = []

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

    def _set_status(self, message):
        self.status_label.setText(message)
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
        header = QGroupBox('CP2112 Battery Analyzer — Adapter Control & Quick Commands')
        header.setStyleSheet('QGroupBox { font-weight: bold; border: 1px solid #007bff; border-radius: 6px; padding-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #007bff; }')
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 8, 10, 8)
        header_layout.setSpacing(8)

        self.conn_status_badge = QLabel('🔴 Disconnected')
        self.conn_status_badge.setStyleSheet('font-weight: bold; font-size: 13px; color: #721c24; background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 4px; padding: 5px 12px;')
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
        self.btn_read_info.setStyleSheet('font-weight: bold; padding: 7px 14px; background-color: #28a745; color: white; border-radius: 4px; font-size: 13px;')
        self.btn_read_info.clicked.connect(self.on_refresh_basic_values)
        header_layout.addWidget(self.btn_read_info)

        self.quick_unseal_btn = QPushButton('🔓 UNSEAL (DEFAULT KEYS)')
        self.quick_unseal_btn.setStyleSheet('font-weight: bold; padding: 7px 14px; background-color: #007bff; color: white; border-radius: 4px; font-size: 13px;')
        self.quick_unseal_btn.clicked.connect(self.on_unseal_default_keys)
        header_layout.addWidget(self.quick_unseal_btn)

        self.quick_seal_btn = QPushButton('🔒 SEAL BATTERY')
        self.quick_seal_btn.setStyleSheet('font-weight: bold; padding: 7px 14px; background-color: #dc3545; color: white; border-radius: 4px; font-size: 13px;')
        self.quick_seal_btn.clicked.connect(self.on_seal_battery)
        header_layout.addWidget(self.quick_seal_btn)

        self.auto_refresh_btn = QPushButton('▶️ AUTO-MONITOR (OFF)')
        self.auto_refresh_btn.setStyleSheet('font-weight: bold; padding: 7px 12px; background-color: #6c757d; color: white; border-radius: 4px;')
        self.auto_refresh_btn.clicked.connect(self.on_toggle_auto_refresh)
        header_layout.addWidget(self.auto_refresh_btn)

        layout.addWidget(header)

        self.status_label = QLabel('Ready to connect battery')
        self.status_label.setStyleSheet('font-style: italic; color: #444; padding-left: 4px;')
        layout.addWidget(self.status_label)

    def _build_dashboard_tab(self):
        dash_tab = QWidget()
        tab_layout = QVBoxLayout(dash_tab)
        tab_layout.setContentsMargins(8, 8, 8, 8)
        tab_layout.setSpacing(10)

        grid = QtWidgets.QGridLayout()
        grid.setSpacing(10)

        # Card 1: SOC & State
        soc_box = QGroupBox('🔋 State of Charge (SOC) & Health (SOH) — Live')
        soc_box.setStyleSheet('QGroupBox { font-weight: bold; border: 2px solid #28a745; border-radius: 6px; margin-top: 6px; padding-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #28a745; }')
        soc_layout = QVBoxLayout(soc_box)
        soc_layout.setContentsMargins(10, 10, 10, 10)
        soc_layout.setSpacing(6)

        self.dash_state_badge = QLabel('STATE: IDLE / STANDBY')
        self.dash_state_badge.setAlignment(QtCore.Qt.AlignCenter)
        self.dash_state_badge.setStyleSheet('font-weight: bold; font-size: 13px; padding: 5px; background: #e9ecef; border-radius: 4px; color: #333;')
        soc_layout.addWidget(self.dash_state_badge)

        self.dash_soc_label = QLabel('0 %')
        self.dash_soc_label.setAlignment(QtCore.Qt.AlignCenter)
        self.dash_soc_label.setStyleSheet('font-size: 38px; font-weight: bold; color: #28a745;')
        soc_layout.addWidget(self.dash_soc_label)

        self.dash_soc_bar = QProgressBar()
        self.dash_soc_bar.setRange(0, 100)
        self.dash_soc_bar.setValue(0)
        self.dash_soc_bar.setTextVisible(True)
        self.dash_soc_bar.setStyleSheet('QProgressBar { text-align: center; height: 22px; border-radius: 5px; } QProgressBar::chunk { background-color: #28a745; }')
        soc_layout.addWidget(self.dash_soc_bar)

        soh_form = QFormLayout()
        self.dash_soh_label = QLabel('-')
        self.dash_soh_label.setStyleSheet('font-size: 14px; font-weight: bold; color: #28a745;')
        self.dash_max_error_label = QLabel('-')
        soh_form.addRow('Health (SOH %):', self.dash_soh_label)
        soh_form.addRow('Max Error:', self.dash_max_error_label)
        soc_layout.addLayout(soh_form)

        grid.addWidget(soc_box, 0, 0)

        # Card 2: Live Telemetry
        vp_box = QGroupBox('⚡ Real-Time Telemetry')
        vp_box.setStyleSheet('QGroupBox { font-weight: bold; border: 2px solid #17a2b8; border-radius: 6px; margin-top: 6px; padding-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #17a2b8; }')
        vp_layout = QFormLayout(vp_box)
        vp_layout.setContentsMargins(10, 10, 10, 10)
        vp_layout.setSpacing(6)
        self.dash_voltage_label = QLabel('-')
        self.dash_voltage_label.setStyleSheet('font-size: 15px; font-weight: bold;')
        self.dash_current_label = QLabel('-')
        self.dash_current_label.setStyleSheet('font-size: 15px; font-weight: bold;')
        self.dash_avg_current_label = QLabel('-')
        self.dash_power_label = QLabel('-')
        self.dash_power_label.setStyleSheet('font-size: 15px; font-weight: bold;')
        self.dash_temp_label = QLabel('-')
        self.dash_temp_label.setStyleSheet('font-size: 15px; font-weight: bold;')

        vp_layout.addRow('Pack Voltage:', self.dash_voltage_label)
        vp_layout.addRow('Actual Current:', self.dash_current_label)
        vp_layout.addRow('Average Current:', self.dash_avg_current_label)
        vp_layout.addRow('Estimated Power:', self.dash_power_label)
        vp_layout.addRow('Cell Temp:', self.dash_temp_label)
        grid.addWidget(vp_box, 0, 1)

        # Card 3: Cell Voltages & Imbalance
        cell_box = QGroupBox('🧪 Individual Cell Voltages & Imbalance')
        cell_box.setStyleSheet('QGroupBox { font-weight: bold; border: 2px solid #6f42c1; border-radius: 6px; margin-top: 6px; padding-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #6f42c1; }')
        cell_layout = QFormLayout(cell_box)
        cell_layout.setContentsMargins(10, 10, 10, 10)
        cell_layout.setSpacing(6)
        self.dash_cell1_label = QLabel('-')
        self.dash_cell2_label = QLabel('-')
        self.dash_cell3_label = QLabel('-')
        self.dash_cell4_label = QLabel('-')
        self.dash_delta_cell_label = QLabel('-')
        self.dash_delta_cell_label.setStyleSheet('font-weight: bold; color: #28a745;')

        cell_layout.addRow('Cell 1:', self.dash_cell1_label)
        cell_layout.addRow('Cell 2:', self.dash_cell2_label)
        cell_layout.addRow('Cell 3:', self.dash_cell3_label)
        cell_layout.addRow('Cell 4:', self.dash_cell4_label)
        cell_layout.addRow('Imbalance (Delta):', self.dash_delta_cell_label)
        grid.addWidget(cell_box, 0, 2)

        # Card 4: Capacities & Runtime
        cap_box = QGroupBox('📦 Capacity & Runtime')
        cap_box.setStyleSheet('QGroupBox { font-weight: bold; border: 2px solid #343a40; border-radius: 6px; margin-top: 6px; padding-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #343a40; }')
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
        chg_box = QGroupBox('🔌 BMS Charging Recommendations')
        chg_box.setStyleSheet('QGroupBox { font-weight: bold; border: 2px solid #fd7e14; border-radius: 6px; margin-top: 6px; padding-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #fd7e14; }')
        chg_layout = QFormLayout(chg_box)
        chg_layout.setContentsMargins(10, 10, 10, 10)
        chg_layout.setSpacing(6)
        self.dash_chg_voltage_label = QLabel('-')
        self.dash_chg_voltage_label.setStyleSheet('font-weight: bold;')
        self.dash_chg_current_label = QLabel('-')
        self.dash_chg_current_label.setStyleSheet('font-weight: bold;')
        self.dash_design_voltage_label = QLabel('-')

        chg_layout.addRow('Rec. Charging Voltage:', self.dash_chg_voltage_label)
        chg_layout.addRow('Rec. Charging Current:', self.dash_chg_current_label)
        chg_layout.addRow('Design Nominal Voltage:', self.dash_design_voltage_label)
        grid.addWidget(chg_box, 1, 1)

        # Card 6: Chipset Info & Unseal Console
        unseal_box = QGroupBox('🔓 Gas Gauge Identification & Security Console')
        unseal_box.setStyleSheet('QGroupBox { font-weight: bold; border: 2px solid #007bff; border-radius: 6px; margin-top: 6px; padding-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #007bff; }')
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
        self.dash_unseal_btn.setStyleSheet('font-weight: bold; padding: 7px; background-color: #007bff; color: white; border-radius: 4px;')
        self.dash_unseal_btn.clicked.connect(self.on_unseal_default_keys)

        self.dash_seal_btn = QPushButton('🔒 SEAL')
        self.dash_seal_btn.setStyleSheet('font-weight: bold; padding: 7px; background-color: #dc3545; color: white; border-radius: 4px;')
        self.dash_seal_btn.clicked.connect(self.on_seal_battery)

        self.dash_reset_btn = QPushButton('🔄 RESET BMS')
        self.dash_reset_btn.setStyleSheet('font-weight: bold; padding: 7px; background-color: #6c757d; color: white; border-radius: 4px;')
        self.dash_reset_btn.clicked.connect(self.on_reset_device)

        btn_row.addWidget(self.dash_unseal_btn)
        btn_row.addWidget(self.dash_seal_btn)
        btn_row.addWidget(self.dash_reset_btn)
        unseal_layout.addLayout(btn_row)

        self.dash_status_flags_label = QLabel('Flags: -')
        self.dash_status_flags_label.setWordWrap(True)
        unseal_layout.addWidget(self.dash_status_flags_label)

        grid.addWidget(unseal_box, 1, 2)

        tab_layout.addLayout(grid)
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
        self.read_all_table_btn.setStyleSheet('font-weight: bold; padding: 6px 12px; background-color: #28a745; color: white; border-radius: 4px;')
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
        descriptions = {
            'ManufacturerAccess': 'Manufacturer access commands and Unseal/Seal sequences',
            'RemainingCapacityAlarm': 'Remaining capacity alarm threshold',
            'RemainingTimeAlarm': 'Remaining time alarm threshold (minutes)',
            'BatteryMode': 'Battery operational mode configuration',
            'AtRate': 'Test current rate (mA)',
            'AtRateTimeToEmpty': 'Estimated time to empty at AtRate current',
            'AtRateTimeToFull': 'Estimated time to full at AtRate current',
            'Temperature': 'Internal cell pack temperature (0.1K / °C)',
            'Voltage': 'Total cell pack voltage (mV)',
            'Current': 'Instantaneous current (+Charge / -Discharge in mA)',
            'AverageCurrent': 'Time-averaged current (mA)',
            'MaxError': 'Maximum gas gauge accuracy error (%)',
            'RelativeStateOfCharge': 'Relative State of Charge (% of FCC)',
            'AbsoluteStateOfCharge': 'Absolute State of Charge (% of Design Cap)',
            'RemainingCapacity': 'Current usable remaining capacity (mAh)',
            'FullChargeCapacity': 'Full Charge Capacity at full health (mAh)',
            'RunTimeToEmpty': 'Remaining continuous run time (minutes)',
            'AverageTimeToEmpty': 'Average remaining time before empty (min)',
            'AverageTimeToFull': 'Average estimated time to full charge (min)',
            'ChargingCurrent': 'Recommended charging current from BMS (mA)',
            'ChargingVoltage': 'Recommended charging voltage from BMS (mV)',
            'BatteryStatus': 'Status flags, protection alarms, and error codes',
            'CycleCount': 'Total complete charge/discharge cycle count',
            'DesignCapacity': 'Nominal factory design capacity (mAh)',
            'DesignVoltage': 'Nominal factory pack voltage (mV)',
            'SpecificationInfo': 'Supported SBS specification version',
            'ManufacturerDate': 'Assembly manufacture date (YYYY.MM.DD)',
            'SerialNumber': 'Unique battery serial number',
            'ManufacturerName': 'Cell / BMS manufacturer name',
            'DeviceName': 'Device model or part number',
            'DeviceChemistry': 'Internal cell chemistry (LION, NiMH, etc.)',
            'ManufacturerData': 'Proprietary manufacturer binary data',
            'CellVoltage4': 'Individual Cell 4 voltage (mV)',
            'CellVoltage3': 'Individual Cell 3 voltage (mV)',
            'CellVoltage2': 'Individual Cell 2 voltage (mV)',
            'CellVoltage1': 'Individual Cell 1 voltage (mV)',
        }
        return descriptions.get(name, 'Smart Battery Standard Register')

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
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)

        guide_box = QGroupBox('📌 CP2112 Connection Guide & Battery Repair Cheat Sheet')
        guide_layout = QVBoxLayout(guide_box)

        guide_text = QPlainTextEdit()
        guide_text.setReadOnly(True)
        guide_text.setPlainText(
            "========================================================================\n"
            "  CP2112 Battery Analyzer — Connection Guide & Repair Cheat Sheet\n"
            "========================================================================\n\n"
            "1. HARDWARE PINOUT — CP2112 Adapter to Laptop Battery:\n"
            "   • CP2112 SDA (Data)   ──►  Battery SMBus Data  (SDA) Pin\n"
            "   • CP2112 SCL (Clock)  ──►  Battery SMBus Clock (SCL) Pin\n"
            "   • CP2112 GND (Ground) ──►  Battery Ground (GND / Negative) Pin\n\n"
            "   NOTE: Use short wires (< 30 cm) and add 4.7 kΩ pull-up resistors on\n"
            "         SDA and SCL if you get communication errors.\n\n"
            "2. WAKING UP DORMANT / SLEEPING BATTERIES:\n"
            "   • Many laptop batteries enter deep-sleep if disconnected for a long time.\n"
            "     In this state the output pins carry no voltage and SMBus is unresponsive.\n"
            "   • WAKE-UP METHOD: Briefly connect the 'System Present' pin (usually Pin 4,\n"
            "     labelled SysPres, SMBC, or similar) to GND for ~2 seconds.\n"
            "   • Alternatively, apply a short pulse of 5 V between B+ and B− for ~1 s.\n\n"
            "3. COMMON SMBUS ADDRESSES & GAS GAUGE CHIPS:\n"
            "   • Standard Laptop Battery Address : 0x0B  (7-bit) / 0x16 (8-bit write)\n"
            "   • Texas Instruments BQ Series    : BQ20Z45, BQ20Z70, BQ20Z90, BQ30Z55,\n"
            "                                      BQ40Z50, BQ40Z80\n"
            "   • Maxim / Analog Devices          : MAX1781, MAX17055, DS2786\n"
            "   • Renesas / Seiko                 : SN8030, R2J240, S-8530\n\n"
            "4. UNSEAL KEY REFERENCE (write both Key1 then Key2 to ManufacturerAccess 0x00):\n"
            "   • TI BQ20Zxx / BQ30xx (default) : Key1=0x0414  Key2=0x3672\n"
            "   • TI BQ40xx / BQ2084            : Key1=0x3672  Key2=0x0414\n"
            "   • Generic / Standard firmware   : Key1=0x8000  Key2=0x8000\n"
            "   • Sony / Sanyo OEM firmware     : Key1=0x1122  Key2=0x3344\n"
            "   • Full-access (if permitted)    : Key1=0xFFFF  Key2=0xFFFF\n\n"
            "5. SEAL / LOCK COMMAND:\n"
            "   • Write word 0x0020 to ManufacturerAccess (0x00) to re-seal the BMS.\n\n"
            "6. TROUBLESHOOTING:\n"
            "   • 'DEVICE_NOT_FOUND' error → Plug in the CP2112 USB dongle first.\n"
            "   • 'Transfer timeout'       → Check SDA/SCL wiring; try pull-up resistors.\n"
            "   • All registers return 0   → Battery may still be sleeping (see step 2).\n"
            "   • Unseal has no effect     → Try the alternate TI key order (BQ40xx preset).\n"
        )
        guide_layout.addWidget(guide_text)

        layout.addWidget(guide_box)
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
                self.conn_status_badge.setStyleSheet('font-weight: bold; font-size: 13px; color: #155724; background: #d4edda; border: 1px solid #c3e6cb; border-radius: 4px; padding: 5px 12px;')
            else:
                self.conn_status_badge.setText('🔴 Disconnected (0 Devices)')
                self.conn_status_badge.setStyleSheet('font-weight: bold; font-size: 13px; color: #721c24; background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 4px; padding: 5px 12px;')
            self._set_status(f'Detected {count} CP2112 device(s)')
        except Exception as exc:
            self._append_log(f'Device detection failed: {exc}', error=True)
            self.conn_status_badge.setText('🔴 DLL / Driver Error')
            self.conn_status_badge.setStyleSheet('font-weight: bold; font-size: 13px; color: #721c24; background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 4px; padding: 5px 12px;')
            self.device_index_input.setMaximum(0)

    def _update_device_info(self):
        if self.device is None:
            self.serial_label.setText('-')
            self.product_label.setText('-')
            self.manufacturer_label.setText('-')
            self.path_label.setText('-')
            self.conn_status_badge.setText('🔴 Disconnected')
            self.conn_status_badge.setStyleSheet('font-weight: bold; font-size: 13px; color: #721c24; background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 4px; padding: 5px 12px;')
            return
        info = self.device.get_info()
        strings = info.get('device_strings', {})
        self.serial_label.setText(strings.get('serial_number', '-'))
        self.product_label.setText(strings.get('product', '-'))
        self.manufacturer_label.setText(strings.get('manufacturer', '-'))
        self.path_label.setText(strings.get('path', '-'))
        self.conn_status_badge.setText(f'🟢 Open ({strings.get("product", "CP2112")})')
        self.conn_status_badge.setStyleSheet('font-weight: bold; font-size: 13px; color: #155724; background: #d4edda; border: 1px solid #c3e6cb; border-radius: 4px; padding: 5px 12px;')
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
        if not data:
            return 'No data'
        if register_name in {'ManufacturerName', 'DeviceName', 'DeviceChemistry'}:
            if len(data) > 1 and 0 < data[0] <= len(data) - 1:
                length = data[0]
                text = data[1:1 + length].decode('ascii', errors='ignore').strip()
            else:
                text = data.decode('ascii', errors='ignore').rstrip('\x00').strip()
            return text if text else 'N/A'
        if register_name == 'ManufacturerDate' and len(data) >= 2:
            val = int.from_bytes(data[:2], 'little', signed=False)
            day = val & 0x1F
            month = (val >> 5) & 0x0F
            year = 1980 + ((val >> 9) & 0x7F)
            return f'{year:04d}.{month:02d}.{day:02d}'
        if register_name == 'SerialNumber' and len(data) >= 2:
            val = int.from_bytes(data[:2], 'little', signed=False)
            return f'{val} (0x{val:04X})'
        if register_name in {'CellVoltage1', 'CellVoltage2', 'CellVoltage3', 'CellVoltage4'} and len(data) >= 2:
            val = int.from_bytes(data[:2], 'little', signed=False)
            if val == 0:
                return '0 mV (N/A)'
            return f'{val / 1000.0:.2f} V ({val} mV)'
        if register_name == 'MaxError' and len(data) >= 2:
            val = int.from_bytes(data[:2], 'little', signed=False)
            return f'{val} %'
        if register_name in {'RunTimeToEmpty', 'AverageTimeToEmpty', 'AverageTimeToFull', 'AtRateTimeToEmpty', 'AtRateTimeToFull'} and len(data) >= 2:
            val = int.from_bytes(data[:2], 'little', signed=False)
            if val == 65535:
                return 'N/A'
            return f'{val} min'
        if register_name == 'BatteryStatus' and len(data) >= 2:
            value = int.from_bytes(data[:2], 'little', signed=False)
            bits = []
            if value & 0x0001: bits.append('Overcharged')
            if value & 0x0002: bits.append('TerminateCharge')
            if value & 0x0004: bits.append('Overtemp')
            if value & 0x0008: bits.append('TerminateDischarge')
            if value & 0x0010: bits.append('RemainingCapacityAlarm')
            if value & 0x0020: bits.append('RemainingTimeAlarm')
            if value & 0x0040: bits.append('Initialized')
            if value & 0x0080: bits.append('Discharging')
            if value & 0x0100: bits.append('FullyCharged')
            if value & 0x0200: bits.append('FullyDischarged')
            return f'0x{value:04X} ({", ".join(bits) if bits else "OK / Normal"})'
        if register_name == 'Temperature' and len(data) >= 2:
            value = int.from_bytes(data[:2], 'little', signed=False)
            temp_k = value / 10.0
            temp_c = temp_k - 273.15
            temp_f = (temp_c * 9.0 / 5.0) + 32.0
            return f'{temp_c:.1f} °C ({temp_f:.1f} °F / {temp_k:.1f} K)'
        if register_name in {'Voltage', 'DesignVoltage', 'ChargingVoltage'} and len(data) >= 2:
            value = int.from_bytes(data[:2], 'little', signed=False)
            return f'{value / 1000.0:.2f} V ({value} mV)'
        if register_name in {'Current', 'AverageCurrent', 'ChargingCurrent', 'AtRate'} and len(data) >= 2:
            value = int.from_bytes(data[:2], 'little', signed=True)
            sign = '+' if value > 0 else ''
            state = ' (Charging)' if value > 0 else (' (Discharging)' if value < 0 else '')
            return f'{sign}{value} mA{state}'
        if register_name in {'RemainingCapacity', 'FullChargeCapacity', 'DesignCapacity'} and len(data) >= 2:
            value = int.from_bytes(data[:2], 'little', signed=False)
            return f'{value} mAh'
        if register_name in {'RelativeStateOfCharge', 'AbsoluteStateOfCharge'} and len(data) >= 2:
            value = int.from_bytes(data[:2], 'little', signed=False)
            return f'{value} %'
        if register_name == 'CycleCount' and len(data) >= 2:
            value = int.from_bytes(data[:2], 'little', signed=False)
            return f'{value} cycles'
        if len(data) == 1:
            return str(data[0])
        if len(data) == 2:
            return str(int.from_bytes(data[:2], 'little', signed=False))
        return format_bytes(data)

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
            self.auto_refresh_btn.setStyleSheet('font-weight: bold; padding: 7px 12px; background-color: #6c757d; color: white; border-radius: 4px;')
            self._set_status('Live monitoring stopped')
        else:
            if not self._ensure_device_open():
                return
            self.auto_refresh_timer.start(2000)
            self.auto_refresh_btn.setText('⏹️ STOP MONITORING')
            self.auto_refresh_btn.setStyleSheet('font-weight: bold; padding: 7px 12px; background-color: #dc3545; color: white; border-radius: 4px;')
            self._set_status('Live monitoring active — polling every 2.0 s')

    def _auto_refresh_tick(self):
        try:
            self._refresh_basic_values()
        except Exception as exc:
            self._append_log(f'Auto-refresh tick error: {exc}', error=True)
            self.auto_refresh_timer.stop()
            self.auto_refresh_btn.setText('▶️ AUTO-MONITOR (OFF)')
            self.auto_refresh_btn.setStyleSheet('font-weight: bold; padding: 7px 12px; background-color: #6c757d; color: white; border-radius: 4px;')

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
            self.device.reset()
            self._set_status('Device reset command sent')
        except Exception as exc:
            self._append_log(f'Reset device failed: {exc}', error=True)

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
        regs_to_read = [
            'RelativeStateOfCharge', 'Voltage', 'Current', 'AverageCurrent', 'Temperature',
            'RemainingCapacity', 'FullChargeCapacity', 'DesignCapacity', 'DesignVoltage',
            'ChargingVoltage', 'ChargingCurrent',
            'CycleCount', 'MaxError', 'RunTimeToEmpty', 'AverageTimeToFull',
            'ManufacturerDate', 'SerialNumber', 'ManufacturerName', 'DeviceName', 'DeviceChemistry',
            'BatteryStatus', 'CellVoltage1', 'CellVoltage2', 'CellVoltage3', 'CellVoltage4'
        ]

        raw_data = {}
        formatted_data = {}

        for reg_name in regs_to_read:
            try:
                reg_addr = self.BATTERY_REGISTERS[reg_name]
                length = 16 if reg_name in {'ManufacturerName', 'DeviceName', 'DeviceChemistry'} else 2
                data = self.device.read_register(address, reg_addr, length=length)
                raw_data[reg_name] = data
                formatted_data[reg_name] = self._format_battery_value(reg_name, data)
            except Exception as exc:
                formatted_data[reg_name] = f'N/A'

        # SOC
        soc_val = 0
        if 'RelativeStateOfCharge' in raw_data and len(raw_data['RelativeStateOfCharge']) >= 2:
            soc_val = int.from_bytes(raw_data['RelativeStateOfCharge'][:2], 'little', signed=False)
            self.dash_soc_label.setText(f'{soc_val} %')
            self.dash_soc_bar.setValue(min(max(soc_val, 0), 100))
            if soc_val > 50:
                self.dash_soc_bar.setStyleSheet('QProgressBar { text-align: center; height: 22px; border-radius: 5px; } QProgressBar::chunk { background-color: #28a745; }')
                self.dash_soc_label.setStyleSheet('font-size: 38px; font-weight: bold; color: #28a745;')
            elif soc_val >= 20:
                self.dash_soc_bar.setStyleSheet('QProgressBar { text-align: center; height: 22px; border-radius: 5px; } QProgressBar::chunk { background-color: #ffc107; }')
                self.dash_soc_label.setStyleSheet('font-size: 38px; font-weight: bold; color: #d39e00;')
            else:
                self.dash_soc_bar.setStyleSheet('QProgressBar { text-align: center; height: 22px; border-radius: 5px; } QProgressBar::chunk { background-color: #dc3545; }')
                self.dash_soc_label.setStyleSheet('font-size: 38px; font-weight: bold; color: #dc3545;')
        else:
            self.dash_soc_label.setText('- %')
            self.dash_soc_bar.setValue(0)

        # Current & Power
        curr_val = 0
        volt_val = 0
        if 'Current' in raw_data and len(raw_data['Current']) >= 2:
            curr_val = int.from_bytes(raw_data['Current'][:2], 'little', signed=True)
        if 'Voltage' in raw_data and len(raw_data['Voltage']) >= 2:
            volt_val = int.from_bytes(raw_data['Voltage'][:2], 'little', signed=False)

        if curr_val > 0:
            self.dash_state_badge.setText('⚡ CHARGING')
            self.dash_state_badge.setStyleSheet('font-weight: bold; font-size: 13px; color: #155724; background: #d4edda; border-radius: 4px; padding: 5px;')
        elif curr_val < 0:
            self.dash_state_badge.setText('🔋 DISCHARGING')
            self.dash_state_badge.setStyleSheet('font-weight: bold; font-size: 13px; color: #856404; background: #fff3cd; border-radius: 4px; padding: 5px;')
        else:
            self.dash_state_badge.setText('💤 IDLE / STANDBY')
            self.dash_state_badge.setStyleSheet('font-weight: bold; font-size: 13px; color: #383d41; background: #e2e3e5; border-radius: 4px; padding: 5px;')

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
                self.dash_delta_cell_label.setStyleSheet('font-weight: bold; color: #28a745;')
            elif delta_mv <= 60:
                self.dash_delta_cell_label.setText(f'{delta_mv} mV (⚠️ MODERATE)')
                self.dash_delta_cell_label.setStyleSheet('font-weight: bold; color: #d39e00;')
            else:
                self.dash_delta_cell_label.setText(f'{delta_mv} mV (🚨 HIGH IMBALANCE)')
                self.dash_delta_cell_label.setStyleSheet('font-weight: bold; color: #dc3545;')
        else:
            self.dash_delta_cell_label.setText('-')
            self.dash_delta_cell_label.setStyleSheet('font-weight: bold;')

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

        # SOH
        soh_str = '-'
        try:
            if 'FullChargeCapacity' in raw_data and 'DesignCapacity' in raw_data:
                fcc = int.from_bytes(raw_data['FullChargeCapacity'][:2], 'little', signed=False)
                dcap = int.from_bytes(raw_data['DesignCapacity'][:2], 'little', signed=False)
                if dcap > 0:
                    soh = (fcc / dcap) * 100.0
                    soh_str = f'{soh:.1f} % ({fcc}/{dcap} mAh)'
        except Exception:
            pass
        self.dash_soh_label.setText(soh_str)

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
                f'Software  : CP2112 Battery Analyzer v1.0',
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


APP_NAME = 'CP2112 Battery Analyzer'
APP_VERSION = '1.0.0'


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
