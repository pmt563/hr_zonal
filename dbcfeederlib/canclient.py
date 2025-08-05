from ctypes import *

import time
import os
import logging
from typing import Optional
import can  # type: ignore
import sys
import struct
import typing

cur_path = os.path.abspath(os.path.join(os.path.dirname(__file__)))
print(f"canclient current dir: {cur_path}")
import sys
sys.path.append(cur_path)
from dbcfeederlib import canmessage

log = logging.getLogger(__name__)
log.info(f"Systems path of {__name__}: {cur_path}")

# Lấy đường dẫn tuyệt đối tới file .so
#so_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'libcontrolcanfd.so'))
def get_library_path():
    if getattr(sys, 'frozen', False):  # Running in PyInstaller
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(__file__)
    return os.path.abspath(os.path.join(base_path, 'dbcfeederlib', 'libcontrolcanfd.so'))
so_path = get_library_path()

# try:
#     lib = ctypes.CDLL(so_path)
#     log.info("Load libcontrolcanfd successfully")
# except OSError as e:
#     print(f"Failed to load libcontrolcanfd.so: {e}")
#     raise

VCI_USBCAN2 = 41
STATUS_OK = 1
INVALID_DEVICE_HANDLE  = 0
INVALID_CHANNEL_HANDLE = 0
TYPE_CAN = 0
TYPE_CANFD = 1


    
class VCI_INIT_CONFIG(Structure):  
    _fields_ = [("AccCode", c_uint),
                ("AccMask", c_uint),
                ("Reserved", c_uint),
                ("Filter", c_ubyte),
                ("Timing0", c_ubyte),
                ("Timing1", c_ubyte),
                ("Mode", c_ubyte)
                ]  

class VCI_CAN_OBJ(Structure):  
    _fields_ = [("ID", c_uint),
                ("TimeStamp", c_uint),
                ("TimeFlag", c_ubyte),
                ("SendType", c_ubyte),
                ("RemoteFlag", c_ubyte),
                ("ExternFlag", c_ubyte),
                ("DataLen", c_ubyte),
                ("Data", c_ubyte*8),
                ("Reserved", c_ubyte*3)
                ] 

class _ZCAN_CHANNEL_CAN_INIT_CONFIG(Structure):
    _fields_ = [("acc_code", c_uint),
                ("acc_mask", c_uint),
                ("reserved", c_uint),
                ("filter",   c_ubyte),
                ("timing0",  c_ubyte),
                ("timing1",  c_ubyte),
                ("mode",     c_ubyte)]

class _ZCAN_CHANNEL_CANFD_INIT_CONFIG(Structure):
    _fields_ = [("acc_code",     c_uint),
                ("acc_mask",     c_uint),
                ("abit_timing",  c_uint),
                ("dbit_timing",  c_uint),
                ("brp",          c_uint),
                ("filter",       c_ubyte),
                ("mode",         c_ubyte),
                ("pad",          c_ushort),
                ("reserved",     c_uint)]

class _ZCAN_CHANNEL_INIT_CONFIG(Union):
    _fields_ = [("can", _ZCAN_CHANNEL_CAN_INIT_CONFIG), ("canfd", _ZCAN_CHANNEL_CANFD_INIT_CONFIG)]

class ZCAN_CHANNEL_INIT_CONFIG(Structure):
    _fields_ = [("can_type", c_uint),
                ("config", _ZCAN_CHANNEL_INIT_CONFIG)]

class ZCAN_CAN_FRAME(Structure):
    _fields_ = [("can_id",  c_uint, 29),
                ("err",     c_uint, 1),
                ("rtr",     c_uint, 1),
                ("eff",     c_uint, 1), 
                ("can_dlc", c_ubyte),
                ("__pad",   c_ubyte),
                ("__res0",  c_ubyte),
                ("__res1",  c_ubyte),
                ("data",    c_ubyte * 8)]

class ZCAN_CANFD_FRAME(Structure):
    _fields_ = [("can_id", c_uint, 29), 
                ("err",    c_uint, 1),
                ("rtr",    c_uint, 1),
                ("eff",    c_uint, 1), 
                ("len",    c_ubyte),
                ("brs",    c_ubyte, 1),
                ("esi",    c_ubyte, 1),
                ("__res",  c_ubyte, 6),
                ("__res0", c_ubyte),
                ("__res1", c_ubyte),
                ("data",   c_ubyte * 64)]

class ZCAN_Transmit_Data(Structure):
    _fields_ = [("frame", ZCAN_CAN_FRAME), ("transmit_type", c_uint)]

class ZCAN_Receive_Data(Structure):
    _fields_  = [("frame", ZCAN_CAN_FRAME), ("timestamp", c_ulonglong)]

class ZCAN_TransmitFD_Data(Structure):
    _fields_ = [("frame", ZCAN_CANFD_FRAME), ("transmit_type", c_uint)]

class ZCAN_ReceiveFD_Data(Structure):
    _fields_ = [("frame", ZCAN_CANFD_FRAME), ("timestamp", c_ulonglong)]

# CanDLLName = 'libcontrolcanfd.so'
canDLL = cdll.LoadLibrary(so_path)

# Define function argument and return types
canDLL.ZCAN_OpenDevice.restype = c_void_p
canDLL.ZCAN_SetAbitBaud.argtypes = (c_void_p, c_ulong, c_ulong)
canDLL.ZCAN_SetDbitBaud.argtypes = (c_void_p, c_ulong, c_ulong)
canDLL.ZCAN_SetCANFDStandard.argtypes = (c_void_p, c_ulong, c_ulong)
canDLL.ZCAN_InitCAN.argtypes = (c_void_p, c_ulong, c_void_p)
canDLL.ZCAN_InitCAN.restype = c_void_p
canDLL.ZCAN_StartCAN.argtypes = (c_void_p,)
canDLL.ZCAN_Transmit.argtypes = (c_void_p, c_void_p, c_ulong)
canDLL.ZCAN_TransmitFD.argtypes = (c_void_p, c_void_p, c_ulong)
canDLL.ZCAN_GetReceiveNum.argtypes = (c_void_p, c_ulong)
canDLL.ZCAN_Receive.argtypes = (c_void_p, c_void_p, c_ulong, c_long)
canDLL.ZCAN_ReceiveFD.argtypes = (c_void_p, c_void_p, c_ulong, c_long)
canDLL.ZCAN_ResetCAN.argtypes = (c_void_p,)
canDLL.ZCAN_CloseDevice.argtypes = (c_void_p,)

canDLL.ZCAN_ClearFilter.argtypes = (c_void_p,)
canDLL.ZCAN_AckFilter.argtypes = (c_void_p,)
canDLL.ZCAN_SetFilterMode.argtypes = (c_void_p, c_ulong)
canDLL.ZCAN_SetFilterStartID.argtypes = (c_void_p, c_ulong)
canDLL.ZCAN_SetFilterEndID.argtypes = (c_void_p, c_ulong)

def open_device():
    m_dev = canDLL.ZCAN_OpenDevice(VCI_USBCAN2, 0, 0)
    if m_dev == INVALID_DEVICE_HANDLE:
        print("Open Device failed!")
        exit(0)
    # print("Open Device OK, device handle:0x%x." % m_dev)
    return m_dev

def set_baud_rate(device_handle):
    # channel   -     instance
    #  1        -          1
    #  0        -          2
    # Set baud rate for CAN2 instance
    channel = 0
    baud_rate_a = 500000
    baud_rate_d = 500000
    ret = canDLL.ZCAN_SetAbitBaud(device_handle, channel, baud_rate_a)
    if ret != STATUS_OK:
        print(f"Set CAN{channel} abit:{baud_rate_a} failed!")
        sys.exit(0)
    print(f"Set CAN{channel} abit:{baud_rate_a} OK!")
    ret = canDLL.ZCAN_SetDbitBaud(device_handle, channel, baud_rate_d)
    if ret != STATUS_OK:
        print(f"Set CAN{channel} dbit:{baud_rate_d} failed!")
        sys.exit(0)
    print(f"Set CAN{channel} dbit:{baud_rate_d} OK!")

def configure_canfd_mode(device_handle):
    channel = 1
    ret = canDLL.ZCAN_SetCANFDStandard(device_handle, channel, 0)
    if ret != STATUS_OK:
        print(f"Set CAN{channel} ISO mode failed!")
        exit(0)
    print(f"Set CAN{channel} ISO mode OK!")

def init_channel(device_handle, channel):
    init_config = ZCAN_CHANNEL_INIT_CONFIG()
    init_config.can_type = TYPE_CANFD
    init_config.config.canfd.mode = 0
    dev_ch = canDLL.ZCAN_InitCAN(device_handle, channel, byref(init_config))
    if dev_ch == INVALID_CHANNEL_HANDLE:
        print(f"Init CAN{channel} failed!")
        exit(0)
    print(f"Init CAN{channel} OK!")
    return dev_ch

def start_channel(dev_ch):
    ret = canDLL.ZCAN_StartCAN(dev_ch)
    if ret != STATUS_OK:
        print(f"Start CAN channel failed!")
        exit(0)
    print("Start CAN channel OK!")

def configure_filter(dev_ch2):
    canDLL.ZCAN_ClearFilter(dev_ch2)
    canDLL.ZCAN_SetFilterMode(dev_ch2, 1)
    # canDLL.ZCAN_SetFilterStartID(dev_ch2, 0x2B6)
    # canDLL.ZCAN_SetFilterEndID(dev_ch2, 0x2B6)
    canDLL.ZCAN_AckFilter(dev_ch2)

def send_canfd_data(dev_ch2, can_id, can_data):
    transmit_canfd_num = 1
    canfd_msgs = (ZCAN_TransmitFD_Data * transmit_canfd_num)()
    canfd_msgs[0].transmit_type = 0
    canfd_msgs[0].frame.eff     = 1  # Extended frame
    canfd_msgs[0].frame.rtr     = 0  # Not a remote frame
    canfd_msgs[0].frame.brs     = 1  # Bit rate switch enabled
    canfd_msgs[0].frame.can_id  = can_id  # CAN ID
    canfd_msgs[0].frame.len     = 8  # Data length
    # Data: 0600000000000000 (hex) = [6, 0, 0, 0, 0, 0, 0, 0]
    canfd_msgs[0].frame.data = can_data
    ret = canDLL.ZCAN_TransmitFD(dev_ch2, canfd_msgs, transmit_canfd_num)
    print(f"\nCAN2 Transmit CANFD Num: {ret}.")

def receive_canfd_data(dev_ch2):
    ret = canDLL.ZCAN_GetReceiveNum(dev_ch2, TYPE_CANFD)
    while ret <= 0:
        time.sleep(0.01)  # Add a small delay to avoid busy-waiting
        ret = canDLL.ZCAN_GetReceiveNum(dev_ch2, TYPE_CANFD)
    if ret > 0:
        rcv_canfd_msgs = (ZCAN_ReceiveFD_Data * ret)()
        num = canDLL.ZCAN_ReceiveFD(dev_ch2, byref(rcv_canfd_msgs), ret, -1)
        print(f"CAN2 Received CANFD NUM: {num}.")
        for i in range(num):
            print(f"[{i}]:ts:{rcv_canfd_msgs[i].timestamp}, id:{hex(rcv_canfd_msgs[i].frame.can_id)}, len:{rcv_canfd_msgs[i].frame.len}, "
                  f"eff:{rcv_canfd_msgs[i].frame.eff}, rtr:{rcv_canfd_msgs[i].frame.rtr}, esi:{rcv_canfd_msgs[i].frame.esi}, "
                  f"brs:{rcv_canfd_msgs[i].frame.brs}, data:{' '.join(hex(rcv_canfd_msgs[i].frame.data[j]) for j in range(rcv_canfd_msgs[i].frame.len))}")

# def send_can_data(dev_ch1, can_id, can_data):
#     transmit_can_num = 1
#     can_msgs = (ZCAN_Transmit_Data * transmit_can_num)()
#     for i in range(transmit_can_num):
#         can_msgs[i].transmit_type = 0
#         can_msgs[i].frame.eff     = 0
#         can_msgs[i].frame.rtr     = 0
#         can_msgs[i].frame.can_id  = can_id
#         can_msgs[i].frame.can_dlc = 8
#         can_msgs[i].frame.data = can_data
#     ret = canDLL.ZCAN_Transmit(dev_ch1, can_msgs, transmit_can_num)
#     log.info(f"\nCAN1 Transmit CAN Num: {ret} {transmit_can_num}")

def send_can_data(dev_ch1, can_id, can_data):
    transmit_can_num = 1
    can_msgs = (ZCAN_Transmit_Data * transmit_can_num)()
    
    for i in range(transmit_can_num):
        can_msgs[i].transmit_type = 0
        can_msgs[i].frame.eff     = 0
        can_msgs[i].frame.rtr     = 0
        can_msgs[i].frame.can_id  = can_id
        can_msgs[i].frame.can_dlc = 8
        
        # Handle different types of can_data
        if isinstance(can_data, (bytes, bytearray)):
            for j in range(min(len(can_data), 8)):
                can_msgs[i].frame.data[j] = can_data[j]
        elif isinstance(can_data, int):
            # Convert integer to bytes using big-endian
            bits = struct.unpack('!Q', struct.pack('!Q', can_data))[0]
            for j in range(8):
                can_msgs[i].frame.data[j] = (bits >> (8 * (7 - j))) & 0xFF
        elif isinstance(can_data, typing.Iterable):
            # Handle iterable of integers
            data_list = list(can_data)[:8]  # Limit to 8 bytes
            for j in range(min(len(data_list), 8)):
                can_msgs[i].frame.data[j] = data_list[j]
        else:
            raise ValueError("Unsupported can_data type")
            
    ret = canDLL.ZCAN_Transmit(dev_ch1, can_msgs, transmit_can_num)
    log.info(f"\nCAN1 Transmit CAN Num: {ret} {transmit_can_num}")


def receive_can_data(dev_ch2):
    ret = canDLL.ZCAN_GetReceiveNum(dev_ch2, TYPE_CAN)
    while ret <= 0:
        time.sleep(0.01)  # Add a small delay to avoid busy-waiting
        ret = canDLL.ZCAN_GetReceiveNum(dev_ch2, TYPE_CAN)
    if ret > 0:
        rcv_can_msgs = (ZCAN_Receive_Data * ret)()
        num = canDLL.ZCAN_Receive(dev_ch2, byref(rcv_can_msgs), ret, -1)
        print(f"CAN2 Received CAN NUM: {num}.")
        for i in range(num):
            print(f"[{i}]:ts:{rcv_can_msgs[i].timestamp}, id:{hex(rcv_can_msgs[i].frame.can_id)}, len:{rcv_can_msgs[i].frame.can_dlc}, "
                  f"eff:{rcv_can_msgs[i].frame.eff}, rtr:{rcv_can_msgs[i].frame.rtr}, "
                  f"data:{' '.join(hex(rcv_can_msgs[i].frame.data[j]) for j in range(rcv_can_msgs[i].frame.can_dlc))}")
        return rcv_can_msgs

def close_device(dev_ch1, dev_ch2, device_handle):
    ret = canDLL.ZCAN_ResetCAN(dev_ch1)
    if ret != STATUS_OK:
        print("Close CAN1 failed!")
        exit(0)
    print("Close CAN1 OK!")    
    ret = canDLL.ZCAN_ResetCAN(dev_ch2)
    if ret != STATUS_OK:
        print("Close CAN2 failed!")
        exit(0)
    print("Close CAN2 OK!")    
    ret = canDLL.ZCAN_CloseDevice(device_handle)
    if ret != STATUS_OK:
        print("Close Device failed!")
        exit(0)
    print("Close Device OK!")


class CANClient:
    """
    Wrapper class to hide dependency to CAN package.
    Reason is to make it simple to replace the CAN package dependency with something else if your KUKSA.val
    integration cannot interact directly with CAN, but rather interacts with some custom CAN solution/middleware.
    """

    def __init__(self, *args, **kwargs):
        # pylint: disable=abstract-class-instantiated
        # self._bus = can.interface.Bus(*args, **kwargs)
        log.info("Start init CAN USB Client")
        self._device_handle = open_device()

        
        set_baud_rate(self._device_handle)
        configure_canfd_mode(self._device_handle)

    # dev_ch1 = init_channel(device_handle, 0)
    # start_channel(dev_ch1)
    
    # dev_ch2 = init_channel(device_handle, 1)
    # configure_filter(dev_ch2)
    # start_channel(dev_ch2)
    
        self._dev_ch2 = init_channel(self._device_handle, 1)  # CAN2 for receiving
        self._dev_ch1 = init_channel(self._device_handle, 0)  # CAN1 for testing
        configure_filter(self._dev_ch2)
        start_channel(self._dev_ch2)
    
        

    def stop(self):
        """Shut down CAN bus."""
        # self._bus.shutdown()
        close_device(dev_ch1=self._dev_ch1, dev_ch2=self._dev_ch2, device_handle=self._device_handle)
        log.info("Close USB CAN !!!")


    def recv(self, timeout: int = 1) -> Optional[canmessage.CANMessage]:
        """Receive message from CAN bus."""
     
        try:
            rcv_can_msgs = receive_can_data(self._dev_ch2)
            i = 0
            log.info("DATA TYPE: ID datatypes: %s   -- Data: %s", type(rcv_can_msgs[i].frame.can_id), type(rcv_can_msgs[i].frame.data[0]))
            log.info("Receive CAN message from USB CAN: ID %s Data: %s", rcv_can_msgs[i].frame.can_id, rcv_can_msgs[i].frame.data[0])
        except can.CanError:
            rcv_can_msgs = None  
            if self._dev_ch2:
                log.error("Error while waiting for recv from CAN", exc_info=True)
            else:
                # This is expected if we are shutting down 
                log.debug("Exception received during shutdown")
                
        i = 0
        if rcv_can_msgs:
            canmsg_format = can.Message(timestamp=rcv_can_msgs[i].timestamp, arbitration_id=rcv_can_msgs[i].frame.can_id, data=rcv_can_msgs[i].frame.data)
            canmsg = canmessage.CANMessage(canmsg_format)
            log.info("Type ID: %s - Type Data: %s", type(canmsg.get_arbitration_id()), type(canmsg.get_data()))
            log.info("Convert to CAN msg STRUCT: [ID] %s - [data] %s", canmsg.get_arbitration_id(), canmsg.get_data())
            return canmsg
        return None
    
        # def __init__(  # pylint: disable=too-many-locals, too-many-arguments
        # self,
        # timestamp: float = 0.0,
        # arbitration_id: int = 0,
        # is_extended_id: bool = True,
        # is_remote_frame: bool = False,
        # is_error_frame: bool = False,
        # channel: Optional[typechecking.Channel] = None,
        # dlc: Optional[int] = None,
        # data: Optional[typechecking.CanData] = None,
        # is_fd: bool = False,
        # is_rx: bool = True,
        # bitrate_switch: bool = False,
        # error_state_indicator: bool = False,
        # check: bool = False,


    def send(self, arbitration_id, data):
        """Write message to CAN bus."""
        # Version with odler usb - sendcan
        msg = can.Message(arbitration_id=arbitration_id, data=data)
        data_len = min(len(msg.data), 8)
        c_data = ((c_ubyte * 8)(*[0] * 8))

        for i in range(data_len):
            c_data[i] = msg.data[i]
        
        try:
            # self._bus.send(msg)
            # send_canfd_data(dev_ch2=self._dev_ch2, can_id=msg.arbitration_id, can_data=msg.data)
            send_can_data(dev_ch1=self._dev_ch2, can_id=msg.arbitration_id, can_data=c_data)
            log.info("Send CAN msg: %s, %s", msg.arbitration_id, msg.data)
            # if log.isEnabledFor(logging.DEBUG):
            #     log.debug("Sent message [channel: %s]: %s", self._bus.channel_info, msg)
        except can.CanError:
            log.error("Failed to send message via CAN bus")
