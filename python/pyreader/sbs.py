"""Smart Battery System (SBS v1.1) register decoding and health assessment."""
from __future__ import annotations

BATTERY_REGISTERS: dict[str, int] = {
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

REGISTER_DESCRIPTIONS: dict[str, str] = {
    'ManufacturerAccess': 'Manufacturer access commands and Unseal/Seal sequences',
    'RemainingCapacityAlarm': 'Remaining capacity alarm threshold (mAh)',
    'RemainingTimeAlarm': 'Remaining time alarm threshold (minutes)',
    'BatteryMode': 'Battery operational mode and capability flags',
    'AtRate': 'Test current rate (mA)',
    'AtRateTimeToEmpty': 'Estimated time to empty at AtRate current',
    'AtRateTimeToFull': 'Estimated time to full at AtRate current',
    'Temperature': 'Internal cell pack temperature (0.1 K)',
    'Voltage': 'Total cell pack voltage (mV)',
    'Current': 'Instantaneous current (+ charge / − discharge, mA)',
    'AverageCurrent': 'Time-averaged current (mA)',
    'MaxError': 'Maximum gas gauge accuracy error (%)',
    'RelativeStateOfCharge': 'Relative State of Charge (% of FCC)',
    'AbsoluteStateOfCharge': 'Absolute State of Charge (% of design capacity)',
    'RemainingCapacity': 'Current usable remaining capacity (mAh)',
    'FullChargeCapacity': 'Full Charge Capacity at current health (mAh)',
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

DASHBOARD_REGISTERS = [
    'RelativeStateOfCharge', 'Voltage', 'Current', 'AverageCurrent', 'Temperature',
    'RemainingCapacity', 'FullChargeCapacity', 'DesignCapacity', 'DesignVoltage',
    'ChargingVoltage', 'ChargingCurrent',
    'CycleCount', 'MaxError', 'RunTimeToEmpty', 'AverageTimeToFull',
    'ManufacturerDate', 'SerialNumber', 'ManufacturerName', 'DeviceName', 'DeviceChemistry',
    'BatteryStatus', 'BatteryMode',
    'CellVoltage1', 'CellVoltage2', 'CellVoltage3', 'CellVoltage4',
]

STRING_REGISTERS = frozenset({'ManufacturerName', 'DeviceName', 'DeviceChemistry'})
TIME_REGISTERS = frozenset({
    'RunTimeToEmpty', 'AverageTimeToEmpty', 'AverageTimeToFull',
    'AtRateTimeToEmpty', 'AtRateTimeToFull',
})


def format_bytes(value: bytes | bytearray | list | tuple) -> str:
    if isinstance(value, (bytes, bytearray)):
        return ' '.join(f'{byte:02X}' for byte in value)
    if isinstance(value, (list, tuple)):
        return ' '.join(f'{byte:02X}' for byte in value)
    return str(value)


def _decode_battery_mode(value: int) -> str:
    flags = []
    if value & 0x8000:
        flags.append('InternalChargeController')
    if value & 0x4000:
        flags.append('PrimaryBatterySupport')
    if value & 0x2000:
        flags.append('PrimaryBattery')
    if value & 0x1000:
        flags.append('ChargerMode')
    if value & 0x0800:
        flags.append('AlarmMode')
    if value & 0x0400:
        flags.append('Initialised')
    if value & 0x0200:
        flags.append('PrimaryBatteryShutdown')
    if value & 0x0100:
        flags.append('ChargeControllerEnabled')
    cap_mode = '10mW/10mWh' if value & 0x0080 else 'mA/mAh'
    summary = ', '.join(flags) if flags else 'Default'
    return f'0x{value:04X} ({summary}; capacity units: {cap_mode})'


def _decode_battery_status(value: int) -> str:
    bits = []
    if value & 0x0001:
        bits.append('Overcharged')
    if value & 0x0002:
        bits.append('TerminateCharge')
    if value & 0x0004:
        bits.append('Overtemp')          # Flag, but we will not rely on it alone for alerts
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
    if value & 0x0100:
        bits.append('FullyCharged')
    if value & 0x0200:
        bits.append('FullyDischarged')
    return f'0x{value:04X} ({", ".join(bits) if bits else "OK / Normal"})'


def format_register_value(register_name: str, data: bytes | bytearray | None) -> str:
    if not data:
        return 'No data'
    if register_name in STRING_REGISTERS:
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
    if register_name.startswith('CellVoltage') and len(data) >= 2:
        val = int.from_bytes(data[:2], 'little', signed=False)
        if val == 0:
            return '0 mV (N/A)'
        return f'{val / 1000.0:.2f} V ({val} mV)'
    if register_name == 'MaxError' and len(data) >= 2:
        val = int.from_bytes(data[:2], 'little', signed=False)
        return f'{val} %'
    if register_name in TIME_REGISTERS and len(data) >= 2:
        val = int.from_bytes(data[:2], 'little', signed=False)
        if val == 65535:
            return 'N/A'
        return f'{val} min'
    if register_name == 'BatteryStatus' and len(data) >= 2:
        value = int.from_bytes(data[:2], 'little', signed=False)
        return _decode_battery_status(value)
    if register_name == 'BatteryMode' and len(data) >= 2:
        value = int.from_bytes(data[:2], 'little', signed=False)
        return _decode_battery_mode(value)
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


def word_value(data: bytes | bytearray | None) -> int | None:
    if data and len(data) >= 2:
        return int.from_bytes(data[:2], 'little', signed=False)
    return None


def signed_word_value(data: bytes | bytearray | None) -> int | None:
    if data and len(data) >= 2:
        return int.from_bytes(data[:2], 'little', signed=True)
    return None


def calculate_soh(raw_data: dict[str, bytes]) -> tuple[float | None, str]:
    fcc = word_value(raw_data.get('FullChargeCapacity'))
    design = word_value(raw_data.get('DesignCapacity'))
    if fcc is None or design is None or design <= 0:
        return None, '-'
    soh = (fcc / design) * 100.0
    return soh, f'{soh:.1f} % ({fcc}/{design} mAh)'


def cell_imbalance_mv(raw_data: dict[str, bytes]) -> int | None:
    values = []
    for name in ('CellVoltage1', 'CellVoltage2', 'CellVoltage3', 'CellVoltage4'):
        val = word_value(raw_data.get(name))
        if val and val > 0:
            values.append(val)
    if not values:
        return None
    return max(values) - min(values)


def assess_battery_health(raw_data: dict[str, bytes]) -> list[tuple[str, str]]:
    """
    Return list of (severity, message) where severity is info|warning|critical.
    Fixed to avoid false overtemperature from BatteryStatus flag.
    """
    alerts: list[tuple[str, str]] = []

    # ---- SOH ----
    soh, _ = calculate_soh(raw_data)
    if soh is not None:
        if soh < 50:
            alerts.append(('critical', f'Very low health (SOH {soh:.0f}%) — consider replacement'))
        elif soh < 70:
            alerts.append(('warning', f'Degraded capacity (SOH {soh:.0f}%)'))

    # ---- Cycle count ----
    cycles = word_value(raw_data.get('CycleCount'))
    if cycles is not None:
        if cycles >= 800:
            alerts.append(('critical', f'High cycle count ({cycles}) — end of life likely'))
        elif cycles >= 500:
            alerts.append(('warning', f'Elevated cycle count ({cycles})'))

    # ---- Max error ----
    max_error = word_value(raw_data.get('MaxError'))
    if max_error is not None and max_error > 10:
        alerts.append(('warning', f'Gas gauge max error is {max_error}%'))

    # ---- Cell imbalance ----
    delta = cell_imbalance_mv(raw_data)
    if delta is not None:
        if delta > 60:
            alerts.append(('critical', f'High cell imbalance ({delta} mV)'))
        elif delta > 30:
            alerts.append(('warning', f'Moderate cell imbalance ({delta} mV)'))

    # ---- BatteryStatus flags (excluding overtemperature flag, we rely on actual temperature) ----
    status = word_value(raw_data.get('BatteryStatus'))
    if status is not None:
        # Overcharged flag (0x0001) - can be false, but we'll report as warning
        if status & 0x0001:
            alerts.append(('warning', 'Battery status: Overcharged (flag set)'))
        # Terminate discharge (0x0008)
        if status & 0x0008:
            alerts.append(('warning', 'Battery status: Terminate discharge active'))
        # Fully discharged (0x0200)
        if status & 0x0200:
            alerts.append(('info', 'Battery status: Fully discharged'))
        # Terminate charge (0x0002)
        if status & 0x0002:
            alerts.append(('info', 'Battery status: Terminate charge'))
        # Overcurrent (0x0004?) Actually 0x0004 is Overtemp flag, we skip it.
        # Instead we check temperature below.

    # ---- Temperature based on actual reading ----
    temp_raw = word_value(raw_data.get('Temperature'))
    if temp_raw is not None:
        temp_c = (temp_raw / 10.0) - 273.15
        if temp_c > 55:
            alerts.append(('critical', f'High pack temperature ({temp_c:.1f} °C)'))
        elif temp_c > 45:
            alerts.append(('warning', f'Elevated pack temperature ({temp_c:.1f} °C)'))
        elif temp_c < -10:
            alerts.append(('warning', f'Low pack temperature ({temp_c:.1f} °C)'))

    # ---- SOC ----
    soc = word_value(raw_data.get('RelativeStateOfCharge'))
    if soc is not None and soc < 10:
        alerts.append(('info', f'Low state of charge ({soc}%)'))

    # ---- Voltage sanity ----
    voltage = word_value(raw_data.get('Voltage'))
    if voltage is not None:
        # Typically Li-ion nominal per cell ~3.7V, so assume 3 cells => ~11.1V, 4 cells => 14.8V
        # We'll just check if voltage is below 6V (may indicate connection issue or deep discharge)
        if voltage < 6000:
            alerts.append(('warning', f'Low pack voltage ({voltage/1000:.2f}V)'))

    if not alerts:
        alerts.append(('info', 'No health issues detected'))
    return alerts