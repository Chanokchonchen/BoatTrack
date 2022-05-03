import ctypes

PKT_TYPE_ADVERTISE = 0x01
PKT_TYPE_REPORT    = 0x02
PKT_TYPE_ACK       = 0x03
PKT_TYPE_BOOT      = 0x04


class BaseStruct(ctypes.Structure):

    _pack_ = 1

    @classmethod
    def size(cls):
        return ctypes.sizeof(cls)

    def unpack(self, blob):
        if not isinstance(blob,bytes):
            raise Exception('Byte array expected for blob')
        if ctypes.sizeof(self) != len(blob):
            raise Exception('Size mismatched')
        ctypes.memmove(ctypes.addressof(self), blob, ctypes.sizeof(self))

class StructConfig(BaseStruct):
    _fields_ = [
        ('radio_device_address', ctypes.c_ubyte),
        ('radio_gateway_address', ctypes.c_ubyte),
        ('radio_freq', ctypes.c_float),
        ('radio_tx_power', ctypes.c_ubyte),
        ('collect_interval_day', ctypes.c_ushort),
        ('collect_interval_night', ctypes.c_ushort),
        ('day_start_hour', ctypes.c_ubyte),
        ('day_end_hour', ctypes.c_ubyte),
        ('time_zone', ctypes.c_byte),
        ('advertise_interval', ctypes.c_ushort),
        ('use_ack', ctypes.c_byte),
        ('ack_timeout', ctypes.c_ushort),
        ('long_range', ctypes.c_ubyte),
        ('tx_repeat', ctypes.c_ubyte),
        ('gps_max_wait_for_fix', ctypes.c_ushort),
        ('next_collect_no_fix', ctypes.c_ushort),
        ('total_slots', ctypes.c_ushort),
        ('slot_interval', ctypes.c_ushort),
        ('prog_file_name', ctypes.c_char*10),
    ]

class StructDate(BaseStruct):
    _fields_ = [
        ('year',ctypes.c_uint,6),
        ('month',ctypes.c_uint,4),
        ('day',ctypes.c_uint,5),
        ('hour',ctypes.c_uint,5),
        ('minute',ctypes.c_uint,6),
        ('second',ctypes.c_uint,6),
    ]    


class StructReport(BaseStruct):
    _fields_ = [
        ('date', StructDate),
        ('vbat', ctypes.c_ushort),    # unit of mV
        ('latitude', ctypes.c_long),
        ('longitude', ctypes.c_long), # unit of 1/100000 degrees
        ('quality', ctypes.c_ubyte),
        ('satellites', ctypes.c_ubyte),
        ('temperature', ctypes.c_ushort),
        ('time_to_fix', ctypes.c_ushort),
    ]
    
class StructPktBoot(BaseStruct):
    _fields_ = [
        ('type', ctypes.c_ubyte),
        ('firmware', ctypes.c_ushort),
        ('device_model', ctypes.c_ubyte),
        ('reset_flags', ctypes.c_ubyte),
        ('config', StructConfig),
    ]



class StructPktReport(BaseStruct):
    _fields_ = [
        ('type', ctypes.c_ubyte),
        ('seq', ctypes.c_ubyte),
        ('report', StructReport),
    ]

