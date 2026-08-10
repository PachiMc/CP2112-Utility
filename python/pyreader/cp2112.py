from ctypes import WinDLL, c_uint32, c_uint16, c_int, c_void_p, POINTER, byref, c_ubyte, c_bool
from ctypes import c_char_p, create_string_buffer
import os
import re
import time
from pathlib import Path
import logging

# Load the SLAB HID->SMBus DLL. Ensure the DLL is in PATH or next to the executable.
_dll_path = 'SLABHIDtoSMBus.dll'
_dll = None
_dll_error = None
if os.name == 'nt':
    candidates = [
        Path(__file__).resolve().parent / _dll_path,
        Path(__file__).resolve().parents[1] / _dll_path,
        Path(__file__).resolve().parents[2] / _dll_path,
        Path.cwd() / _dll_path,
    ]
    last_exc = None
    for cand in candidates:
        try:
            if cand.exists():
                _dll = WinDLL(str(cand))
                _dll_error = None
                break
        except Exception as exc:
            last_exc = exc
    if _dll is None:
        try:
            _dll = WinDLL(_dll_path)
        except Exception as exc:
            _dll = None
            _dll_error = exc if last_exc is None else last_exc
else:
    _dll_error = OSError('CP2112 wrapper currently supports Windows only')

# Typedefs
DWORD = c_uint32
WORD = c_uint16
BYTE = c_ubyte
HID_SMBUS_DEVICE = c_void_p

if _dll is None and _dll_error is None:
    _dll_error = RuntimeError('SLABHIDtoSMBus DLL not loaded')

if _dll is not None:
    _dll.HidSmbus_GetNumDevices.argtypes = [POINTER(DWORD), WORD, WORD]
    _dll.HidSmbus_GetNumDevices.restype = c_int

    _dll.HidSmbus_Open.argtypes = [POINTER(HID_SMBUS_DEVICE), DWORD, WORD, WORD]
    _dll.HidSmbus_Open.restype = c_int

    _dll.HidSmbus_IsOpened.argtypes = [HID_SMBUS_DEVICE, POINTER(c_bool)]
    _dll.HidSmbus_IsOpened.restype = c_int

    _dll.HidSmbus_SetSmbusConfig.argtypes = [HID_SMBUS_DEVICE, DWORD, BYTE, c_bool, WORD, WORD, c_bool, WORD]
    _dll.HidSmbus_SetSmbusConfig.restype = c_int

    _dll.HidSmbus_SetTimeouts.argtypes = [HID_SMBUS_DEVICE, DWORD]
    _dll.HidSmbus_SetTimeouts.restype = c_int

    _dll.HidSmbus_GetGpioConfig.argtypes = [HID_SMBUS_DEVICE, POINTER(BYTE), POINTER(BYTE), POINTER(BYTE), POINTER(BYTE)]
    _dll.HidSmbus_GetGpioConfig.restype = c_int

    _dll.HidSmbus_SetGpioConfig.argtypes = [HID_SMBUS_DEVICE, BYTE, BYTE, BYTE, BYTE]
    _dll.HidSmbus_SetGpioConfig.restype = c_int

    _dll.HidSmbus_GetOpenedString.argtypes = [HID_SMBUS_DEVICE, c_char_p, DWORD]
    _dll.HidSmbus_GetOpenedString.restype = c_int

    _dll.HidSmbus_GetSmbusConfig.argtypes = [HID_SMBUS_DEVICE, POINTER(DWORD), POINTER(BYTE), POINTER(c_bool), POINTER(WORD), POINTER(WORD), POINTER(c_bool), POINTER(WORD)]
    _dll.HidSmbus_GetSmbusConfig.restype = c_int

    _dll.HidSmbus_AddressReadRequest.argtypes = [HID_SMBUS_DEVICE, BYTE, WORD, BYTE, POINTER(BYTE)]
    _dll.HidSmbus_AddressReadRequest.restype = c_int

    _dll.HidSmbus_ReadRequest.argtypes = [HID_SMBUS_DEVICE, BYTE, WORD]
    _dll.HidSmbus_ReadRequest.restype = c_int

    _dll.HidSmbus_WriteRequest.argtypes = [HID_SMBUS_DEVICE, BYTE, POINTER(BYTE), BYTE]
    _dll.HidSmbus_WriteRequest.restype = c_int

    _dll.HidSmbus_TransferStatusRequest.argtypes = [HID_SMBUS_DEVICE]
    _dll.HidSmbus_TransferStatusRequest.restype = c_int

    _dll.HidSmbus_GetTransferStatusResponse.argtypes = [HID_SMBUS_DEVICE, POINTER(BYTE), POINTER(BYTE), POINTER(WORD), POINTER(WORD)]
    _dll.HidSmbus_GetTransferStatusResponse.restype = c_int

    _dll.HidSmbus_ForceReadResponse.argtypes = [HID_SMBUS_DEVICE, WORD]
    _dll.HidSmbus_ForceReadResponse.restype = c_int

    _dll.HidSmbus_GetReadResponse.argtypes = [HID_SMBUS_DEVICE, POINTER(BYTE), POINTER(BYTE), BYTE, POINTER(BYTE)]
    _dll.HidSmbus_GetReadResponse.restype = c_int

    _dll.HidSmbus_Close.argtypes = [HID_SMBUS_DEVICE]
    _dll.HidSmbus_Close.restype = c_int

    _dll.HidSmbus_Reset.argtypes = [HID_SMBUS_DEVICE]
    _dll.HidSmbus_Reset.restype = c_int

    _dll.HidSmbus_GetTimeouts.argtypes = [HID_SMBUS_DEVICE, POINTER(DWORD)]
    _dll.HidSmbus_GetTimeouts.restype = c_int

    _dll.HidSmbus_ReadLatch.argtypes = [HID_SMBUS_DEVICE, POINTER(BYTE)]
    _dll.HidSmbus_ReadLatch.restype = c_int

    _dll.HidSmbus_WriteLatch.argtypes = [HID_SMBUS_DEVICE, BYTE, BYTE]
    _dll.HidSmbus_WriteLatch.restype = c_int

    _dll.HidSmbus_GetPartNumber.argtypes = [HID_SMBUS_DEVICE, POINTER(BYTE), POINTER(BYTE)]
    _dll.HidSmbus_GetPartNumber.restype = c_int

    _dll.HidSmbus_CancelTransfer.argtypes = [HID_SMBUS_DEVICE]
    _dll.HidSmbus_CancelTransfer.restype = c_int

    _dll.HidSmbus_CancelIo.argtypes = [HID_SMBUS_DEVICE]
    _dll.HidSmbus_CancelIo.restype = c_int

    try:
        _dll.HidSmbus_GetLibraryVersion.argtypes = [POINTER(BYTE), POINTER(BYTE), POINTER(c_bool)]
        _dll.HidSmbus_GetLibraryVersion.restype = c_int
    except AttributeError:
        pass

# Default values
VID = 0x10C4
PID = 0xEA90
BITRATE_HZ = 70000
ACK_ADDRESS = 0x02
WRITE_TIMEOUT_MS = 1000
READ_TIMEOUT_MS = 1000
TRANSFER_RETRIES = 0
SCL_LOW_TIMEOUT = True
RESPONSE_TIMEOUT_MS = 1000

# Status values
HID_SMBUS_SUCCESS = 0x00
HID_SMBUS_DEVICE_NOT_FOUND = 0x01
HID_SMBUS_INVALID_HANDLE = 0x02
HID_SMBUS_INVALID_DEVICE_OBJECT = 0x03
HID_SMBUS_INVALID_PARAMETER = 0x04
HID_SMBUS_INVALID_REQUEST_LENGTH = 0x05
HID_SMBUS_READ_ERROR = 0x10
HID_SMBUS_WRITE_ERROR = 0x11
HID_SMBUS_READ_TIMED_OUT = 0x12
HID_SMBUS_WRITE_TIMED_OUT = 0x13
HID_SMBUS_DEVICE_IO_FAILED = 0x14
HID_SMBUS_DEVICE_ACCESS_ERROR = 0x15
HID_SMBUS_DEVICE_NOT_SUPPORTED = 0x16
HID_SMBUS_UNKNOWN_ERROR = 0xFF

HID_SMBUS_S0_IDLE = 0x00
HID_SMBUS_S0_BUSY = 0x01
HID_SMBUS_S0_COMPLETE = 0x02
HID_SMBUS_S0_ERROR = 0x03

HID_SMBUS_S1_BUSY_ADDRESS_ACKED = 0x00
HID_SMBUS_S1_BUSY_ADDRESS_NACKED = 0x01
HID_SMBUS_S1_BUSY_READING = 0x02
HID_SMBUS_S1_BUSY_WRITING = 0x03

HID_SMBUS_S1_ERROR_TIMEOUT_NACK = 0x00
HID_SMBUS_S1_ERROR_TIMEOUT_BUS_NOT_FREE = 0x01
HID_SMBUS_S1_ERROR_ARB_LOST = 0x02
HID_SMBUS_S1_ERROR_READ_INCOMPLETE = 0x03
HID_SMBUS_S1_ERROR_WRITE_INCOMPLETE = 0x04
HID_SMBUS_S1_ERROR_SUCCESS_AFTER_RETRY = 0x05

HID_SMBUS_DIRECTION_INPUT = 0
HID_SMBUS_DIRECTION_OUTPUT = 1
HID_SMBUS_MODE_OPEN_DRAIN = 0
HID_SMBUS_MODE_PUSH_PULL = 1

HID_SMBUS_MASK_FUNCTION_GPIO_7_CLK = 0x01
HID_SMBUS_MASK_FUNCTION_GPIO_0_TXT = 0x02
HID_SMBUS_MASK_FUNCTION_GPIO_1_RXT = 0x04
HID_SMBUS_GPIO_FUNCTION = 0
HID_SMBUS_SPECIAL_FUNCTION = 1

HID_SMBUS_MASK_GPIO_0 = 0x01
HID_SMBUS_MASK_GPIO_1 = 0x02
HID_SMBUS_MASK_GPIO_2 = 0x04
HID_SMBUS_MASK_GPIO_3 = 0x08
HID_SMBUS_MASK_GPIO_4 = 0x10
HID_SMBUS_MASK_GPIO_5 = 0x20
HID_SMBUS_MASK_GPIO_6 = 0x40
HID_SMBUS_MASK_GPIO_7 = 0x80

HID_SMBUS_MIN_BIT_RATE = 1
HID_SMBUS_MIN_TIMEOUT = 0
HID_SMBUS_MAX_TIMEOUT = 1000
HID_SMBUS_MAX_RETRIES = 1000
HID_SMBUS_MIN_ADDRESS = 0x02
HID_SMBUS_MAX_ADDRESS = 0xFE
HID_SMBUS_MIN_READ_REQUEST_SIZE = 1
HID_SMBUS_MAX_READ_REQUEST_SIZE = 512
HID_SMBUS_MIN_TARGET_ADDRESS_SIZE = 1
HID_SMBUS_MAX_TARGET_ADDRESS_SIZE = 16
HID_SMBUS_MAX_READ_RESPONSE_SIZE = 61
HID_SMBUS_MIN_WRITE_REQUEST_SIZE = 1
HID_SMBUS_MAX_WRITE_REQUEST_SIZE = 61

HID_SMBUS_GET_VID_STR = 0x01
HID_SMBUS_GET_PID_STR = 0x02
HID_SMBUS_GET_PATH_STR = 0x03
HID_SMBUS_GET_SERIAL_STR = 0x04
HID_SMBUS_GET_MANUFACTURER_STR = 0x05
HID_SMBUS_GET_PRODUCT_STR = 0x06

_STATUS_STR = {
    HID_SMBUS_SUCCESS: 'SUCCESS',
    HID_SMBUS_DEVICE_NOT_FOUND: 'DEVICE_NOT_FOUND',
    HID_SMBUS_INVALID_HANDLE: 'INVALID_HANDLE',
    HID_SMBUS_INVALID_DEVICE_OBJECT: 'INVALID_DEVICE_OBJECT',
    HID_SMBUS_INVALID_PARAMETER: 'INVALID_PARAMETER',
    HID_SMBUS_INVALID_REQUEST_LENGTH: 'INVALID_REQUEST_LENGTH',
    HID_SMBUS_READ_ERROR: 'READ_ERROR',
    HID_SMBUS_WRITE_ERROR: 'WRITE_ERROR',
    HID_SMBUS_READ_TIMED_OUT: 'READ_TIMED_OUT',
    HID_SMBUS_WRITE_TIMED_OUT: 'WRITE_TIMED_OUT',
    HID_SMBUS_DEVICE_IO_FAILED: 'DEVICE_IO_FAILED',
    HID_SMBUS_DEVICE_ACCESS_ERROR: 'DEVICE_ACCESS_ERROR',
    HID_SMBUS_DEVICE_NOT_SUPPORTED: 'DEVICE_NOT_SUPPORTED',
    HID_SMBUS_UNKNOWN_ERROR: 'UNKNOWN_ERROR',
}

logger = logging.getLogger('cp2112')
if not logger.handlers:
    logger.addHandler(logging.NullHandler())


class CP2112Error(Exception):
    pass


def status_str(code):
    try:
        return _STATUS_STR[int(code)]
    except Exception:
        return f'CODE_{int(code)}'


def _check_dll():
    if _dll is None:
        raise CP2112Error('SLABHIDtoSMBus DLL not available')


def _check_device(device):
    if device is None or not bool(device):
        raise CP2112Error('Invalid CP2112 device handle')


def _validate_address(address):
    if not isinstance(address, int) or address < HID_SMBUS_MIN_ADDRESS or address > HID_SMBUS_MAX_ADDRESS:
        raise CP2112Error(f'Invalid SMBus address: {address}')


def _validate_length(length, min_val, max_val, name):
    if not isinstance(length, int) or length < min_val or length > max_val:
        raise CP2112Error(f'{name} must be between {min_val} and {max_val}, got {length}')


def _to_byte_array(data, min_len=1, max_len=HID_SMBUS_MAX_WRITE_REQUEST_SIZE, name='data'):
    if isinstance(data, str):
        text = re.sub(r'[^0-9A-Fa-f]', '', data)
        if len(text) % 2 != 0:
            raise CP2112Error(f'{name} hex string must have an even number of characters')
        data = bytes.fromhex(text)
    elif isinstance(data, list):
        data = bytes(data)
    elif isinstance(data, bytearray):
        data = bytes(data)
    elif isinstance(data, bytes):
        pass
    else:
        raise CP2112Error(f'{name} must be bytes, bytearray, list[int], or hex string')

    _validate_length(len(data), min_len, max_len, f'{name} length')
    return data


def _hex_to_bytes(text, min_len=1, max_len=HID_SMBUS_MAX_TARGET_ADDRESS_SIZE, name='value'):
    if text is None:
        return b''
    text = re.sub(r'[^0-9A-Fa-f]', '', str(text))
    if text == '':
        return b''
    if len(text) % 2 != 0:
        raise CP2112Error(f'{name} hex string must contain an even number of digits')
    data = bytes.fromhex(text)
    _validate_length(len(data), min_len, max_len, f'{name} length')
    return data


def _build_byte_buffer(data):
    return (BYTE * len(data))(*data)


def _decode_string(buffer):
    try:
        return buffer.value.decode(errors='ignore')
    except Exception:
        return ''


def find_devices():
    _check_dll()
    num = DWORD(0)
    status = _dll.HidSmbus_GetNumDevices(byref(num), WORD(VID), WORD(PID))
    if status != HID_SMBUS_SUCCESS:
        raise CP2112Error(f'HidSmbus_GetNumDevices failed: {status} ({status_str(status)})')
    return int(num.value)


def open_device(dev_number):
    _check_dll()
    if not isinstance(dev_number, int) or dev_number < 0:
        raise CP2112Error('Device number must be a non-negative integer')
    device = HID_SMBUS_DEVICE()
    status = _dll.HidSmbus_Open(byref(device), DWORD(dev_number), WORD(VID), WORD(PID))
    if status != HID_SMBUS_SUCCESS:
        raise CP2112Error(f'HidSmbus_Open failed: {status} ({status_str(status)})')
    return device


def is_opened(device):
    _check_dll()
    _check_device(device)
    opened = c_bool()
    status = _dll.HidSmbus_IsOpened(device, byref(opened))
    if status != HID_SMBUS_SUCCESS:
        raise CP2112Error(f'HidSmbus_IsOpened failed: {status} ({status_str(status)})')
    return bool(opened.value)


def set_smbus_config(device, bitrate=BITRATE_HZ, address=ACK_ADDRESS, auto_respond=False,
                      write_timeout=WRITE_TIMEOUT_MS, read_timeout=READ_TIMEOUT_MS,
                      scl_low=SCL_LOW_TIMEOUT, retries=TRANSFER_RETRIES):
    _check_dll()
    _check_device(device)
    _validate_address(address)
    status = _dll.HidSmbus_SetSmbusConfig(device, DWORD(bitrate), BYTE(address), c_bool(auto_respond),
                                         WORD(write_timeout), WORD(read_timeout), c_bool(scl_low), WORD(retries))
    if status != HID_SMBUS_SUCCESS:
        raise CP2112Error(f'HidSmbus_SetSmbusConfig failed: {status} ({status_str(status)})')
    return True


def set_timeouts(device, response_timeout_ms):
    _check_dll()
    _check_device(device)
    if not isinstance(response_timeout_ms, int) or response_timeout_ms < HID_SMBUS_MIN_TIMEOUT or response_timeout_ms > HID_SMBUS_MAX_TIMEOUT:
        raise CP2112Error(f'Response timeout must be between {HID_SMBUS_MIN_TIMEOUT} and {HID_SMBUS_MAX_TIMEOUT}')
    status = _dll.HidSmbus_SetTimeouts(device, DWORD(response_timeout_ms))
    if status != HID_SMBUS_SUCCESS:
        raise CP2112Error(f'HidSmbus_SetTimeouts failed: {status} ({status_str(status)})')
    return True


def get_timeouts(device):
    _check_dll()
    _check_device(device)
    timeout = DWORD()
    status = _dll.HidSmbus_GetTimeouts(device, byref(timeout))
    if status != HID_SMBUS_SUCCESS:
        raise CP2112Error(f'HidSmbus_GetTimeouts failed: {status} ({status_str(status)})')
    return int(timeout.value)


def get_gpio_config(device):
    _check_dll()
    _check_device(device)
    direction = BYTE()
    mode = BYTE()
    function = BYTE()
    clkDiv = BYTE()
    status = _dll.HidSmbus_GetGpioConfig(device, byref(direction), byref(mode), byref(function), byref(clkDiv))
    if status != HID_SMBUS_SUCCESS:
        raise CP2112Error(f'HidSmbus_GetGpioConfig failed: {status} ({status_str(status)})')
    return {
        'direction': int(direction.value),
        'mode': int(mode.value),
        'function': int(function.value),
        'clkDiv': int(clkDiv.value),
    }


def set_gpio_config(device, direction, mode, function, clkDiv=0):
    _check_dll()
    _check_device(device)
    status = _dll.HidSmbus_SetGpioConfig(device, BYTE(direction), BYTE(mode), BYTE(function), BYTE(clkDiv))
    if status != HID_SMBUS_SUCCESS:
        raise CP2112Error(f'HidSmbus_SetGpioConfig failed: {status} ({status_str(status)})')
    return True


def get_opened_string(device, option):
    _check_dll()
    _check_device(device)
    buf = create_string_buffer(260)
    status = _dll.HidSmbus_GetOpenedString(device, buf, DWORD(option))
    if status != HID_SMBUS_SUCCESS:
        raise CP2112Error(f'HidSmbus_GetOpenedString failed: {status} ({status_str(status)})')
    return _decode_string(buf)


def get_smbus_config(device):
    _check_dll()
    _check_device(device)
    bitRate = DWORD()
    address = BYTE()
    autoReadRespond = c_bool()
    writeTimeout = WORD()
    readTimeout = WORD()
    sclLow = c_bool()
    transferRetries = WORD()
    status = _dll.HidSmbus_GetSmbusConfig(device, byref(bitRate), byref(address), byref(autoReadRespond), byref(writeTimeout), byref(readTimeout), byref(sclLow), byref(transferRetries))
    if status != HID_SMBUS_SUCCESS:
        raise CP2112Error(f'HidSmbus_GetSmbusConfig failed: {status} ({status_str(status)})')
    return {
        'bitRate': int(bitRate.value),
        'address': int(address.value),
        'autoReadRespond': bool(autoReadRespond.value),
        'writeTimeout': int(writeTimeout.value),
        'readTimeout': int(readTimeout.value),
        'sclLowTimeout': bool(sclLow.value),
        'transferRetries': int(transferRetries.value),
    }


def address_read_request(device, slave_address, num_bytes_to_read, target_address_size, target_address):
    _check_dll()
    _check_device(device)
    _validate_address(slave_address)
    _validate_length(num_bytes_to_read, HID_SMBUS_MIN_READ_REQUEST_SIZE, HID_SMBUS_MAX_READ_REQUEST_SIZE, 'num_bytes_to_read')
    _validate_length(target_address_size, HID_SMBUS_MIN_TARGET_ADDRESS_SIZE, HID_SMBUS_MAX_TARGET_ADDRESS_SIZE, 'target_address_size')
    if not isinstance(target_address, (bytes, bytearray, list)):
        raise CP2112Error('target_address must be bytes, bytearray, or list[int]')
    target_address = bytes(target_address)
    if len(target_address) != target_address_size:
        raise CP2112Error('target_address length does not match target_address_size')
    status = _dll.HidSmbus_AddressReadRequest(device, BYTE(slave_address), WORD(num_bytes_to_read), BYTE(target_address_size), _build_byte_buffer(target_address))
    if status != HID_SMBUS_SUCCESS:
        raise CP2112Error(f'HidSmbus_AddressReadRequest failed: {status} ({status_str(status)})')
    return True


def read_request(device, slave_address, num_bytes_to_read):
    _check_dll()
    _check_device(device)
    _validate_address(slave_address)
    _validate_length(num_bytes_to_read, HID_SMBUS_MIN_READ_REQUEST_SIZE, HID_SMBUS_MAX_READ_REQUEST_SIZE, 'num_bytes_to_read')
    status = _dll.HidSmbus_ReadRequest(device, BYTE(slave_address), WORD(num_bytes_to_read))
    if status != HID_SMBUS_SUCCESS:
        raise CP2112Error(f'HidSmbus_ReadRequest failed: {status} ({status_str(status)})')
    return True


def write_request(device, slave_address, data):
    _check_dll()
    _check_device(device)
    _validate_address(slave_address)
    data_bytes = _to_byte_array(data, min_len=HID_SMBUS_MIN_WRITE_REQUEST_SIZE, max_len=HID_SMBUS_MAX_WRITE_REQUEST_SIZE)
    status = _dll.HidSmbus_WriteRequest(device, BYTE(slave_address), _build_byte_buffer(data_bytes), BYTE(len(data_bytes)))
    if status != HID_SMBUS_SUCCESS:
        raise CP2112Error(f'HidSmbus_WriteRequest failed: {status} ({status_str(status)})')
    return True


def transfer_status_request(device):
    _check_dll()
    _check_device(device)
    status = _dll.HidSmbus_TransferStatusRequest(device)
    if status != HID_SMBUS_SUCCESS:
        raise CP2112Error(f'HidSmbus_TransferStatusRequest failed: {status} ({status_str(status)})')
    return True


def get_transfer_status_response(device):
    _check_dll()
    _check_device(device)
    status0 = BYTE()
    status1 = BYTE()
    num_retries = WORD()
    bytes_read = WORD()
    status = _dll.HidSmbus_GetTransferStatusResponse(device, byref(status0), byref(status1), byref(num_retries), byref(bytes_read))
    if status != HID_SMBUS_SUCCESS:
        raise CP2112Error(f'HidSmbus_GetTransferStatusResponse failed: {status} ({status_str(status)})')
    return {
        'status': int(status0.value),
        'detailed_status': int(status1.value),
        'num_retries': int(num_retries.value),
        'bytes_read': int(bytes_read.value),
    }


def force_read_response(device, num_bytes_to_read):
    _check_dll()
    _check_device(device)
    _validate_length(num_bytes_to_read, HID_SMBUS_MIN_READ_REQUEST_SIZE, HID_SMBUS_MAX_READ_REQUEST_SIZE, 'num_bytes_to_read')
    status = _dll.HidSmbus_ForceReadResponse(device, WORD(num_bytes_to_read))
    if status != HID_SMBUS_SUCCESS:
        raise CP2112Error(f'HidSmbus_ForceReadResponse failed: {status} ({status_str(status)})')
    return True


def get_read_response(device, buffer_size=HID_SMBUS_MAX_READ_RESPONSE_SIZE):
    _check_dll()
    _check_device(device)
    _validate_length(buffer_size, 1, HID_SMBUS_MAX_READ_RESPONSE_SIZE, 'buffer_size')
    status0 = BYTE()
    buffer = (BYTE * buffer_size)()
    num_bytes_read = BYTE()
    status = _dll.HidSmbus_GetReadResponse(device, byref(status0), buffer, BYTE(buffer_size), byref(num_bytes_read))
    if status != HID_SMBUS_SUCCESS:
        raise CP2112Error(f'HidSmbus_GetReadResponse failed: {status} ({status_str(status)})')
    return {
        'status': int(status0.value),
        'data': bytes(buffer[:num_bytes_read.value]),
        'num_bytes_read': int(num_bytes_read.value),
    }


def close_device(device):
    _check_dll()
    _check_device(device)
    status = _dll.HidSmbus_Close(device)
    if status != HID_SMBUS_SUCCESS:
        raise CP2112Error(f'HidSmbus_Close failed: {status} ({status_str(status)})')
    return True


def reset_device(device):
    _check_dll()
    _check_device(device)
    status = _dll.HidSmbus_Reset(device)
    if status != HID_SMBUS_SUCCESS:
        raise CP2112Error(f'HidSmbus_Reset failed: {status} ({status_str(status)})')
    return True


def read_latch(device):
    _check_dll()
    _check_device(device)
    latch_value = BYTE()
    status = _dll.HidSmbus_ReadLatch(device, byref(latch_value))
    if status != HID_SMBUS_SUCCESS:
        raise CP2112Error(f'HidSmbus_ReadLatch failed: {status} ({status_str(status)})')
    return int(latch_value.value)


def write_latch(device, latch_value, latch_mask):
    _check_dll()
    _check_device(device)
    status = _dll.HidSmbus_WriteLatch(device, BYTE(latch_value), BYTE(latch_mask))
    if status != HID_SMBUS_SUCCESS:
        raise CP2112Error(f'HidSmbus_WriteLatch failed: {status} ({status_str(status)})')
    return True


def get_part_number(device):
    _check_dll()
    _check_device(device)
    part_number = BYTE()
    version = BYTE()
    status = _dll.HidSmbus_GetPartNumber(device, byref(part_number), byref(version))
    if status != HID_SMBUS_SUCCESS:
        raise CP2112Error(f'HidSmbus_GetPartNumber failed: {status} ({status_str(status)})')
    return {
        'part_number': int(part_number.value),
        'version': int(version.value),
    }


def cancel_transfer(device):
    _check_dll()
    _check_device(device)
    status = _dll.HidSmbus_CancelTransfer(device)
    if status != HID_SMBUS_SUCCESS:
        raise CP2112Error(f'HidSmbus_CancelTransfer failed: {status} ({status_str(status)})')
    return True


def cancel_io(device):
    _check_dll()
    _check_device(device)
    status = _dll.HidSmbus_CancelIo(device)
    if status != HID_SMBUS_SUCCESS:
        raise CP2112Error(f'HidSmbus_CancelIo failed: {status} ({status_str(status)})')
    return True


def get_library_version():
    _check_dll()
    major = BYTE()
    minor = BYTE()
    is_release = c_bool()
    try:
        status = _dll.HidSmbus_GetLibraryVersion(byref(major), byref(minor), byref(is_release))
    except AttributeError:
        raise CP2112Error('HidSmbus_GetLibraryVersion not available in this DLL')
    if status != HID_SMBUS_SUCCESS:
        raise CP2112Error(f'HidSmbus_GetLibraryVersion failed: {status} ({status_str(status)})')
    return {
        'status': int(status),
        'major': int(major.value),
        'minor': int(minor.value),
        'is_release': bool(is_release.value),
    }


def get_serial_number(device):
    return get_opened_string(device, HID_SMBUS_GET_SERIAL_STR)


def get_manufacturer_string(device):
    return get_opened_string(device, HID_SMBUS_GET_MANUFACTURER_STR)


def get_product_string(device):
    return get_opened_string(device, HID_SMBUS_GET_PRODUCT_STR)


def get_path_string(device):
    return get_opened_string(device, HID_SMBUS_GET_PATH_STR)


def get_device_strings(device):
    return {
        'serial_number': get_serial_number(device),
        'manufacturer': get_manufacturer_string(device),
        'product': get_product_string(device),
        'path': get_path_string(device),
    }


def open_first_device():
    count = find_devices()
    if count <= 0:
        raise CP2112Error('No CP2112 devices found')
    return open_device(0)


def wait_for_transfer(device, timeout_ms=2000, poll_interval_ms=50):
    _check_dll()
    _check_device(device)
    deadline = time.monotonic() + timeout_ms / 1000.0
    while time.monotonic() < deadline:
        transfer_status_request(device)
        status = get_transfer_status_response(device)
        if status['status'] in (HID_SMBUS_S0_COMPLETE, HID_SMBUS_S0_ERROR):
            return status
        time.sleep(poll_interval_ms / 1000.0)
    raise CP2112Error('Timeout waiting for SMBus transfer completion')


class CP2112Device:
    """High-level CP2112 device helper."""

    def __init__(self, index=0):
        self.index = index
        self.device = open_device(index)
        self.configured = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def configure(self, bitrate=BITRATE_HZ, address=ACK_ADDRESS, auto_respond=False,
                  write_timeout=WRITE_TIMEOUT_MS, read_timeout=READ_TIMEOUT_MS,
                  scl_low=SCL_LOW_TIMEOUT, retries=TRANSFER_RETRIES, response_timeout=RESPONSE_TIMEOUT_MS):
        set_smbus_config(self.device, bitrate=bitrate, address=address, auto_respond=auto_respond,
                         write_timeout=write_timeout, read_timeout=read_timeout,
                         scl_low=scl_low, retries=retries)
        set_timeouts(self.device, response_timeout)
        self.configured = True
        return self

    def get_info(self):
        return {
            'device_strings': get_device_strings(self.device),
            'smbus_config': get_smbus_config(self.device),
            'gpio_config': get_gpio_config(self.device),
            'timeouts': get_timeouts(self.device),
            'part_number': get_part_number(self.device),
        }

    def read(self, slave_address, num_bytes, target_address=None):
        _validate_address(slave_address)
        _validate_length(num_bytes, HID_SMBUS_MIN_READ_REQUEST_SIZE, HID_SMBUS_MAX_READ_REQUEST_SIZE, 'num_bytes')
        if target_address is None or target_address == '':
            read_request(self.device, slave_address, num_bytes)
        else:
            if isinstance(target_address, str):
                target_bytes = _hex_to_bytes(target_address)
            elif isinstance(target_address, (bytes, bytearray, list)):
                target_bytes = bytes(target_address)
            else:
                raise CP2112Error('target_address must be bytes, list, or hex string')
            _validate_length(len(target_bytes), HID_SMBUS_MIN_TARGET_ADDRESS_SIZE, HID_SMBUS_MAX_TARGET_ADDRESS_SIZE, 'target_address')
            address_read_request(self.device, slave_address, num_bytes, len(target_bytes), target_bytes)
        wait_for_transfer(self.device)
        response = get_read_response(self.device, buffer_size=max(num_bytes, HID_SMBUS_MAX_READ_RESPONSE_SIZE))
        return response['data']

    def write(self, slave_address, data):
        _validate_address(slave_address)
        status = write_request(self.device, slave_address, data)
        if status is not True:
            return status
        transfer_status = wait_for_transfer(self.device)
        if transfer_status['status'] == HID_SMBUS_S0_ERROR:
            raise CP2112Error(f'Write failed: {transfer_status}')
        return transfer_status

    def read_register(self, slave_address, register_address, length=1):
        if isinstance(register_address, int):
            register_bytes = bytes([register_address])
        elif isinstance(register_address, str):
            register_bytes = _hex_to_bytes(register_address, min_len=1, max_len=HID_SMBUS_MAX_TARGET_ADDRESS_SIZE, name='register_address')
        elif isinstance(register_address, (bytes, bytearray, list)):
            register_bytes = bytes(register_address)
        else:
            raise CP2112Error('register_address must be an integer, hex string, bytes, or list[int]')
        _validate_length(len(register_bytes), HID_SMBUS_MIN_TARGET_ADDRESS_SIZE, HID_SMBUS_MAX_TARGET_ADDRESS_SIZE, 'register_address')
        return self.read(slave_address, length, target_address=register_bytes)

    def read_latch(self):
        return read_latch(self.device)

    def write_latch(self, latch_value, latch_mask):
        return write_latch(self.device, latch_value, latch_mask)

    def reset(self):
        return reset_device(self.device)

    def cancel_transfer(self):
        return cancel_transfer(self.device)

    def cancel_io(self):
        return cancel_io(self.device)

    def close(self):
        if self.device is not None:
            close_device(self.device)
            self.device = None
            self.configured = False


def diagnose(verbose=True):
    result = {
        'dll_found': _dll is not None,
        'dll_error': str(_dll_error) if _dll_error is not None else None,
    }
    if not result['dll_found']:
        if verbose:
            print('DLL not loaded:', result['dll_error'])
        return result

    try:
        result['library_version'] = get_library_version()
        if verbose:
            print('Library version:', result['library_version'])
    except Exception as exc:
        result['library_version_error'] = str(exc)
        if verbose:
            print('Library version failed:', exc)

    try:
        result['num_devices'] = find_devices()
        if verbose:
            print('Devices found:', result['num_devices'])
    except Exception as exc:
        result['num_devices_error'] = str(exc)
        if verbose:
            print('Device enumeration failed:', exc)

    if result.get('num_devices', 0) > 0:
        try:
            device = open_device(0)
            result['opened'] = is_opened(device)
            if verbose:
                print('Opened device 0, opened=', result['opened'])
            result['device_strings'] = get_device_strings(device)
            close_device(device)
        except Exception as exc:
            result['open_error'] = str(exc)
            if verbose:
                print('Open device failed:', exc)

    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='CP2112 wrapper diagnostics and utilities')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    args = parser.parse_args()
    diagnose(verbose=args.verbose)
