import time
import json
from datetime import datetime , timedelta

tempLog = {
    'CH0':[],
    'CH1':[],
    'CH2':[],
    'CH3':[]
}

def StrToAscii(n):
    assert(type(n) == str)
    return [ord(c) for c in n]
def TimeStamp():
    return f"T:{datetime.now()}"
def Log(text,logfile):
    #print(f"T:{datetime.now()} {text}")
    if logfile:
        logfile.write(f"{text}\n")
        logfile.flush()
def getTime():
    return int(time.time()) 
def dumpData(report,src,rssi,eid):
    
    try:
        rxtime = datetime.now()
        logtime = datetime(2000+report.date.year,
                                report.date.month,
                                report.date.day,
                                report.date.hour,
                                report.date.minute,
                                report.date.second)
        logtime += timedelta(hours=7)
    except ValueError:
        return
    data = {
            "eid" : eid,
            "timeStamp"      : logtime.strftime("%Y-%m-%d %H:%M:%S"),
            "received_time"      : rxtime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "nodeId"             : src,
            "nodeLAT"                : report.latitude/1e5,
            "nodeLong"            : report.longitude/1e5,
            "vbat"               : report.vbat/1e3,
            "quality"            : report.quality,
            "satellites"         : report.satellites,
            "temperature"        : report.temperature,
            "time_to_fix" : report.time_to_fix,
            "rssi"               : rssi,
    }
    return data



