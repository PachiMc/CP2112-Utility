import logging
import sys
from pathlib import Path

from PySide6 import QtCore, QtWidgets
from PySide6.QtWidgets import (QApplication, QComboBox, QFileDialog, QFormLayout,
                                QGroupBox, QLabel, QLineEdit, QMainWindow,
                                QMessageBox, QPlainTextEdit, QPushButton,
                                QSpinBox, QVBoxLayout, QWidget)

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


class MainWindow(QMainWindow):
    BATTERY_REGISTERS = {
        'BatteryMode': 0x00,
        'Temperature': 0x01,
        'Voltage': 0x02,
        'Current': 0x03,
        'AverageCurrent': 0x04,
        'RelativeStateOfCharge': 0x06,
        'AbsoluteStateOfCharge': 0x07,
        'RemainingCapacity': 0x08,
        'FullChargeCapacity': 0x09,
        'RunTimeToEmpty': 0x0A,
        'AverageTimeToEmpty': 0x0B,
        'AverageTimeToFull': 0x0C,
        'ChargingCurrent': 0x0D,
        'ChargingVoltage': 0x0E,
        'BatteryStatus': 0x0F,
        'CycleCount': 0x10,
        'DesignCapacity': 0x11,
        'DesignVoltage': 0x12,
        'ManufacturerDate': 0x14,
        'ManufacturerName': 0x16,
        'DeviceName': 0x17,
        'DeviceChemistry': 0x18,
        'ManufacturerData': 0x19,
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle('CP2112 SMBus Utility')
        self.resize(1040, 780)
        self.device = None
        self._log_messages = []

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(12)

        self.status_label = QLabel('Ready')
        main_layout.addWidget(self.status_label)

        self._build_device_section(main_layout)
        self._build_smbus_section(main_layout)
        self._build_gpio_section(main_layout)
        self._build_battery_section(main_layout)
        self._build_log_section(main_layout)

        self._refresh_device_count()
        self._append_log('Application started')

    def _append_log(self, message, error=False):
        timestamp = QtCore.QDateTime.currentDateTime().toString('HH:mm:ss')
        line = f'[{timestamp}] {message}'
        self._log_messages.append(line)
        self.log_widget.appendPlainText(line)
        if error:
            logger.error(message)
        else:
            logger.info(message)

    def _set_status(self, message):
        self.status_label.setText(message)
        self._append_log(message)

    def _add_button_row(self, layout, buttons):
        row = QWidget(self)
        row_layout = QVBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        button_row = QWidget(self)
        button_row_layout = QtWidgets.QHBoxLayout(button_row)
        button_row_layout.setContentsMargins(0, 0, 0, 0)
        button_row_layout.setSpacing(8)
        for button in buttons:
            button_row_layout.addWidget(button)
        row_layout.addWidget(button_row)
        layout.addRow(row)

    def _build_device_section(self, layout):
        group = QGroupBox('Device')
        group_layout = QFormLayout(group)
        group.setLayout(group_layout)

        self.device_count_label = QLabel('0')
        self.device_index_input = QSpinBox()
        self.device_index_input.setMinimum(0)
        self.open_button = QPushButton('Open Device')
        self.open_button.clicked.connect(self.on_open_device)
        self.close_button = QPushButton('Close Device')
        self.close_button.clicked.connect(self.on_close_device)
        self.detect_button = QPushButton('Detect Devices')
        self.detect_button.clicked.connect(self._refresh_device_count)
        self.refresh_info_button = QPushButton('Refresh Info')
        self.refresh_info_button.clicked.connect(self.on_refresh_info)
        self.reset_button = QPushButton('Reset Device')
        self.reset_button.clicked.connect(self.on_reset_device)
        self.diagnostic_button = QPushButton('Run Diagnostic')
        self.diagnostic_button.clicked.connect(self.on_diagnostic)
        self.serial_label = QLabel('-')
        self.product_label = QLabel('-')
        self.manufacturer_label = QLabel('-')
        self.path_label = QLabel('-')

        group_layout.addRow('Devices found:', self.device_count_label)
        group_layout.addRow('Device index:', self.device_index_input)
        group_layout.addRow('Serial number:', self.serial_label)
        group_layout.addRow('Product:', self.product_label)
        group_layout.addRow('Manufacturer:', self.manufacturer_label)
        group_layout.addRow('Device path:', self.path_label)
        self._add_button_row(group_layout, [self.detect_button, self.open_button, self.close_button])
        self._add_button_row(group_layout, [self.refresh_info_button, self.reset_button, self.diagnostic_button])

        layout.addWidget(group)

    def _build_smbus_section(self, layout):
        group = QGroupBox('SMBus Transfer')
        group_layout = QFormLayout(group)
        group.setLayout(group_layout)

        self.slave_address_input = QLineEdit('0x50')
        self.read_length_input = QLineEdit('16')
        self.target_address_input = QLineEdit('')
        self.read_button = QPushButton('Read')
        self.read_button.clicked.connect(self.on_read)
        self.read_result = QLineEdit('')
        self.read_result.setReadOnly(True)

        self.write_data_input = QLineEdit('')
        self.write_button = QPushButton('Write')
        self.write_button.clicked.connect(self.on_write)
        self.write_result = QLineEdit('')
        self.write_result.setReadOnly(True)

        group_layout.addRow('Slave address:', self.slave_address_input)
        group_layout.addRow('Read length:', self.read_length_input)
        group_layout.addRow('Target address (hex):', self.target_address_input)
        self._add_button_row(group_layout, [self.read_button, self.write_button])
        group_layout.addRow('Read result:', self.read_result)
        group_layout.addRow('Write data (hex or comma separated):', self.write_data_input)
        group_layout.addRow('Write result:', self.write_result)

        layout.addWidget(group)

    def _build_gpio_section(self, layout):
        group = QGroupBox('GPIO / Latch')
        group_layout = QFormLayout(group)
        group.setLayout(group_layout)

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

        group_layout.addRow(self.read_latch_button, self.latch_value_label)
        group_layout.addRow('Latch value:', self.write_latch_value_input)
        group_layout.addRow('Latch mask:', self.write_latch_mask_input)
        group_layout.addRow(self.write_latch_button)
        group_layout.addRow(self.cancel_transfer_button, self.cancel_io_button)

        layout.addWidget(group)

    def _build_battery_section(self, layout):
        group = QGroupBox('Battery / Smart Battery')
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
        self.battery_summary_button = QPushButton('Read Summary')
        self.battery_summary_button.clicked.connect(self.on_read_battery_summary)
        self.battery_export_button = QPushButton('Export Report')
        self.battery_export_button.clicked.connect(self.on_export_battery_report)
        self.battery_last_value_label = QLabel('-')
        self.battery_report_widget = QPlainTextEdit()
        self.battery_report_widget.setReadOnly(True)
        self.battery_report_widget.setPlaceholderText('Battery report preview...')

        form_layout.addRow('Battery address:', self.battery_address_input)
        form_layout.addRow('Register:', self.battery_register_combo)
        form_layout.addRow('Read length:', self.battery_read_length_input)
        self._add_button_row(form_layout, [self.battery_read_button, self.battery_summary_button, self.battery_export_button])
        form_layout.addRow('Last value:', self.battery_last_value_label)
        group_layout.addLayout(form_layout)
        group_layout.addWidget(QLabel('Battery report preview'))
        group_layout.addWidget(self.battery_report_widget, stretch=1)

        layout.addWidget(group)

    def _build_log_section(self, layout):
        group = QGroupBox('Logs & Reports')
        group_layout = QVBoxLayout(group)
        self.log_widget = QPlainTextEdit()
        self.log_widget.setReadOnly(True)
        self.log_widget.setPlaceholderText('Log output...')
        controls = QWidget(self)
        controls_layout = QtWidgets.QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        self.clear_log_button = QPushButton('Clear Log')
        self.clear_log_button.clicked.connect(self.on_clear_log)
        self.export_log_button = QPushButton('Export Log')
        self.export_log_button.clicked.connect(self.on_export_log)
        controls_layout.addWidget(self.clear_log_button)
        controls_layout.addWidget(self.export_log_button)
        group_layout.addWidget(controls)
        group_layout.addWidget(self.log_widget, stretch=1)

        layout.addWidget(group)

    def _refresh_device_count(self):
        try:
            count = cp2112.find_devices()
            self.device_count_label.setText(str(count))
            self.device_index_input.setMaximum(max(count - 1, 0))
            self._set_status(f'Detected {count} device(s)')
        except Exception as exc:
            self._append_log(f'Device detection failed: {exc}', error=True)
            self.device_count_label.setText('0')
            self.device_index_input.setMaximum(0)

    def _update_device_info(self):
        if self.device is None:
            self.serial_label.setText('-')
            self.product_label.setText('-')
            self.manufacturer_label.setText('-')
            self.path_label.setText('-')
            return
        info = self.device.get_info()
        strings = info.get('device_strings', {})
        self.serial_label.setText(strings.get('serial_number', '-'))
        self.product_label.setText(strings.get('product', '-'))
        self.manufacturer_label.setText(strings.get('manufacturer', '-'))
        self.path_label.setText(strings.get('path', '-'))
        self._set_status('Device is open and ready')

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
            text = data.decode('ascii', errors='ignore').rstrip('\x00').strip()
            if text:
                return text
        if register_name == 'BatteryStatus' and len(data) >= 2:
            value = int.from_bytes(data[:2], 'little', signed=False)
            bits = []
            if value & 0x0001:
                bits.append('Overcharged')
            if value & 0x0002:
                bits.append('TerminateCharge')
            if value & 0x0004:
                bits.append('Overtemp')
            if value & 0x0008:
                bits.append('TerminateDischarge')
            if value & 0x0010:
                bits.append('RemainingCapacityAlarm')
            if value & 0x0020:
                bits.append('RemainingTimeAlarm')
            if value & 0x0040:
                bits.append('Initialized')
            if value & 0x0080:
                bits.append('Discharging')
            return f'0x{value:04X} ({", ".join(bits) if bits else "no flags"})'
        if register_name == 'Temperature' and len(data) >= 2:
            value = int.from_bytes(data[:2], 'little', signed=False)
            temp_k = value / 10.0
            return f'{temp_k:.1f} K ({temp_k - 273.15:.1f} C)'
        if register_name in {'Voltage', 'DesignVoltage', 'ChargingVoltage'} and len(data) >= 2:
            value = int.from_bytes(data[:2], 'little', signed=False)
            return f'{value} mV'
        if register_name in {'Current', 'AverageCurrent', 'ChargingCurrent'} and len(data) >= 2:
            value = int.from_bytes(data[:2], 'little', signed=False)
            return f'{value} mA'
        if register_name in {'RemainingCapacity', 'FullChargeCapacity', 'DesignCapacity'} and len(data) >= 2:
            value = int.from_bytes(data[:2], 'little', signed=False)
            return f'{value} mAh'
        if register_name in {'RelativeStateOfCharge', 'AbsoluteStateOfCharge'} and len(data) >= 2:
            value = int.from_bytes(data[:2], 'little', signed=False)
            return f'{value} %'
        if len(data) == 1:
            return str(data[0])
        if len(data) == 2:
            return str(int.from_bytes(data[:2], 'little', signed=False))
        return format_bytes(data)

    def on_open_device(self):
        try:
            if self.device is not None:
                self._set_status('Device already open')
                return
            index = self.device_index_input.value()
            self.device = cp2112.CP2112Device(index=index)
            self.device.configure()
            self._update_device_info()
        except Exception as exc:
            self._append_log(f'Open device failed: {exc}', error=True)
            self.device = None

    def on_close_device(self):
        try:
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
            if self.device is None:
                raise RuntimeError('No open device')
            self._update_device_info()
        except Exception as exc:
            self._append_log(f'Refresh device info failed: {exc}', error=True)

    def on_reset_device(self):
        try:
            if self.device is None:
                raise RuntimeError('No open device')
            self.device.reset()
            self._set_status('Device reset')
        except Exception as exc:
            self._append_log(f'Reset device failed: {exc}', error=True)

    def on_diagnostic(self):
        try:
            result = cp2112.diagnose(verbose=False)
            self._append_log(f'Diagnostic result: {result}')
            self._set_status('Diagnostic completed')
        except Exception as exc:
            self._append_log(f'Diagnostic failed: {exc}', error=True)

    def on_read(self):
        try:
            if self.device is None:
                raise RuntimeError('No open device')
            address = parse_int(self.slave_address_input.text())
            length = parse_int(self.read_length_input.text())
            target = self.target_address_input.text().strip() or None
            data = self.device.read(address, length, target_address=target)
            self.read_result.setText(format_bytes(data))
            self._set_status(f'Read {len(data)} bytes')
        except Exception as exc:
            self._append_log(f'Read failed: {exc}', error=True)

    def on_write(self):
        try:
            if self.device is None:
                raise RuntimeError('No open device')
            address = parse_int(self.slave_address_input.text())
            data = parse_bytes(self.write_data_input.text())
            status = self.device.write(address, data)
            self.write_result.setText(str(status))
            self._set_status('Write completed')
        except Exception as exc:
            self._append_log(f'Write failed: {exc}', error=True)

    def on_read_latch(self):
        try:
            if self.device is None:
                raise RuntimeError('No open device')
            value = self.device.read_latch()
            self.latch_value_label.setText(f'0x{value:02X}')
            self._set_status(f'Read latch: 0x{value:02X}')
        except Exception as exc:
            self._append_log(f'Read latch failed: {exc}', error=True)

    def on_write_latch(self):
        try:
            if self.device is None:
                raise RuntimeError('No open device')
            value = parse_int(self.write_latch_value_input.text())
            mask = parse_int(self.write_latch_mask_input.text())
            self.device.write_latch(value, mask)
            self._set_status(f'Write latch: value=0x{value:02X}, mask=0x{mask:02X}')
        except Exception as exc:
            self._append_log(f'Write latch failed: {exc}', error=True)

    def on_cancel_transfer(self):
        try:
            if self.device is None:
                raise RuntimeError('No open device')
            self.device.cancel_transfer()
            self._set_status('Transfer canceled')
        except Exception as exc:
            self._append_log(f'Cancel transfer failed: {exc}', error=True)

    def on_cancel_io(self):
        try:
            if self.device is None:
                raise RuntimeError('No open device')
            self.device.cancel_io()
            self._set_status('I/O canceled')
        except Exception as exc:
            self._append_log(f'Cancel I/O failed: {exc}', error=True)

    def on_read_battery_register(self):
        try:
            if self.device is None:
                raise RuntimeError('No open device')
            address = self._resolve_battery_address()
            register_address, register_name = self._resolve_battery_register()
            length = parse_int(self.battery_read_length_input.text(), default=2)
            data = self.device.read_register(address, register_address, length=length)
            display = self._format_battery_value(register_name, data)
            self.battery_last_value_label.setText(display)
            self._set_status(f'Read battery register {register_name} from 0x{address:02X}')
            self._append_log(f'Battery register {register_name} ({register_address:#x}): {display}')
        except Exception as exc:
            self._append_log(f'Battery register read failed: {exc}', error=True)

    def on_read_battery_summary(self):
        try:
            if self.device is None:
                raise RuntimeError('No open device')
            address = self._resolve_battery_address()
            lines = [f'Battery summary @ {QtCore.QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")}', f'Slave address: 0x{address:02X}']
            for register_name in ['BatteryMode', 'Temperature', 'Voltage', 'Current', 'AverageCurrent', 'RelativeStateOfCharge', 'AbsoluteStateOfCharge', 'RemainingCapacity', 'FullChargeCapacity', 'RunTimeToEmpty', 'BatteryStatus', 'CycleCount', 'DesignCapacity', 'ManufacturerName', 'DeviceName', 'DeviceChemistry']:
                register_address = self.BATTERY_REGISTERS[register_name]
                try:
                    length = 16 if register_name in {'ManufacturerName', 'DeviceName', 'DeviceChemistry'} else 2
                    data = self.device.read_register(address, register_address, length=length)
                    display = self._format_battery_value(register_name, data)
                    lines.append(f'{register_name}: {display}')
                except Exception as exc:
                    lines.append(f'{register_name}: unavailable ({exc})')
                    self._append_log(f'Battery summary register {register_name} failed: {exc}', error=True)
            report = '\n'.join(lines)
            self.battery_report_widget.setPlainText(report)
            self._set_status('Battery summary generated')
            self._append_log('Battery summary generated')
        except Exception as exc:
            self._append_log(f'Battery summary failed: {exc}', error=True)

    def on_export_battery_report(self):
        try:
            if not self.battery_report_widget.toPlainText().strip():
                self._append_log('No battery report to export', error=True)
                return
            path = self._write_text_file('battery-report', self.battery_report_widget.toPlainText())
            if path:
                self._set_status(f'Battery report exported to {path}')
        except Exception as exc:
            self._append_log(f'Export battery report failed: {exc}', error=True)

    def on_clear_log(self):
        self.log_widget.clear()
        self._log_messages.clear()
        self._append_log('Log cleared')

    def on_export_log(self):
        try:
            path = self._write_text_file('cp2112-log', self._get_report_text())
            if path:
                self._set_status(f'Log exported to {path}')
        except Exception as exc:
            self._append_log(f'Export log failed: {exc}', error=True)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
