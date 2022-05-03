import sys
import copy
import time
import requests
import asyncio
import json
import RPi.GPIO as GPIO
from SX127x.constants import *
from lora import LoRa
from board import BaseBoard
from util import Log,TimeStamp,StrToAscii,getTime,dumpData,tempLog
from config_m import *
from structdata import *

DEBUG = False

c_tempLog = copy.deepcopy(tempLog)

json_datas = {

    'timestamp':'',
    'log_data':c_tempLog

}

if len(sys.argv) < 2 or  len(sys.argv) > 3:
    print(f"Usage: {sys.argv[0]} <log> <Debug>")
    exit(1)
LOG_FILE = open(sys.argv[1],'a')

if len(sys.argv) == 3 and sys.argv[2] == "Debug":
    DEBUG = True

# Setup

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
loop = asyncio.get_event_loop()

class Board0(BaseBoard):
    # Note that the BCM numbering for the GPIOs is used.
    DIO0    = 24
    DIO1    = 6
    RST     = 17
    LED     = 4
    SPI_BUS = 0
    SPI_CS  = 8


class Board1(BaseBoard):
    # Note that the BCM numbering for the GPIOs is used.
    DIO0    = 12
    DIO1    = 19
    RST     = 27
    LED     = None
    SPI_BUS = 0
    SPI_CS  = 20

class Board2(BaseBoard):
    # Note that the BCM numbering for the GPIOs is used.
    DIO0    = 25
    DIO1    = 13
    RST     = 23
    LED     = 18
    SPI_BUS = 0
    SPI_CS  = 7

class Board3(BaseBoard):
    # Note that the BCM numbering for the GPIOs is used.
    DIO0    = 5
    DIO1    = 26
    RST     = 22
    LED     = None
    SPI_BUS = 0
    SPI_CS  = 21

# Setup Channel

configs = [
        {'name':"CH0",'id':0,'board':Board0, 'bw':BW.BW125, 'freq':CH0_FREQ, 'cr':CODING_RATE.CR4_8, 'sf':SF},
        {'name':"CH1",'id':1,'board':Board1, 'bw':BW.BW125, 'freq':CH1_FREQ, 'cr':CODING_RATE.CR4_8, 'sf':SF},
        {'name':"CH2",'id':2,'board':Board2, 'bw':BW.BW125, 'freq':CH2_FREQ, 'cr':CODING_RATE.CR4_8, 'sf':SF},
        {'name':"CH3",'id':3,'board':Board3, 'bw':BW.BW125, 'freq':CH3_FREQ, 'cr':CODING_RATE.CR4_8, 'sf':SF}
        ]

for config in configs:
    board = config['board']
    GPIO.setup(board.SPI_CS, GPIO.OUT)
    GPIO.output(board.SPI_CS, GPIO.HIGH)
    board.setup()
    board.reset()

# Define MyLoRa

class Mylora(LoRa):

    def __init__(self, board, name,cid, verbose=False):

        super(Mylora, self).__init__(board,verbose=verbose)
        self.board = board
        self.set_mode(MODE.SLEEP)
        self.set_dio_mapping([1,0,0,0,0,0])
        self.tx_avail = True
        self.rx_avail = False
        self.name = name
        self.cid = cid
        self.send_ack = False
        self.send_ack_mode = False
        self.n_pkt = 0
        self.eid = 0

    def on_rx_done(self):

        self.board.led_on()
        #self.printT(f"Recieve Done Process ...")
        pkt_rssi,rssi = self.get_pkt_rssi_value(), self.get_rssi_value()
        self.clear_irq_flags(RxDone=1)
        payload = self.read_payload(nocheck=True) 
        src = payload[1]
        dst = payload[0]
        pkt = bytes(bytearray(payload[4:]))
        self.board.led_off()
        if pkt[0] == PKT_TYPE_BOOT and len(pkt) == 40:
            self.printT("Recieve Boot Pkt")
            self.onPktBoot(src,pkt)
        elif pkt[0] == PKT_TYPE_REPORT and len(pkt) == 22 and self.eid == src:      
            #self.printT(self.eid)
            #self.printT((SLOT_INT * self.cid) + src)
            #self.printT("Recieve Report Pkt")
            self.onPktReport(src,pkt)

    def on_tx_done(self):

        #self.printT(f"Transmit Done")
        self.clear_irq_flags(TxDone=1)
        self.toRxMode()
        self.tx_avail = True

    def printT(self,text):
        if DEBUG:
            print(f"{TimeStamp()} [{self.name}] {text}")
        else:
            Log(f"{TimeStamp()} [{self.name}] {text}",LOG_FILE)

    def onPktReport(self,src,pkt):

        report_pkt = StructPktReport()
        report_pkt.unpack(pkt)
        report = report_pkt.report
        date = report.date
        self.n_pkt = report_pkt.seq
        rssi = self.get_pkt_rssi_value()
        self.printT('LOG: {} {} 20{:02}-{:02}-{:02} {:02}:{:02}:{:02} {} {} {} {} {} {} {} {}'.format(
            self.n_pkt,
            self.eid,
            date.year,
            date.month,
            date.day,
            date.hour,
            date.minute,
            date.second,
            report.latitude,
            report.longitude,
            report.vbat,
            report.quality,
            report.satellites,
            report.temperature,
            report.time_to_fix,
            rssi,
        ))
        json_data = dumpData(report,src,rssi,self.eid)
        if json_data:
            json_datas['log_data'][self.name].append(json_data)
        self.rx_avail = True
        self.send_ack_mode = True      
        self.send_ack = True

    def onPktBoot(self,src,pkt):

        boot = StructPktBoot()
        boot.unpack(pkt)
        rssi = self.get_pkt_rssi_value()
        my_addr = boot.config.radio_device_address
        gw_addr = boot.config.radio_gateway_address
        print(f'Device booting reported from {src}, RSSI={rssi}, with parameters:')
        print(f'Firmware version: {boot.firmware}')
        print(f'Device model: 0x{boot.device_model:02x}')
        print(f'Reset flags: 0x{boot.reset_flags:02x}')
        print(f'radio_freq = {boot.config.radio_freq:.2f} MHz')
        print(f'radio_tx_power = {boot.config.radio_tx_power} dBm')
        print(f'radio_device_address = {my_addr} (0x{my_addr:02X})')
        print(f'radio_gateway_address = {gw_addr} (0x{gw_addr:02X})')
        print(f'collect_interval_day = {boot.config.collect_interval_day} sec')
        print(f'collect_interval_night = {boot.config.collect_interval_night} sec')
        print(f'day_start_hour = {boot.config.day_start_hour}')
        print(f'day_end_hour = {boot.config.day_end_hour}')
        print(f'time_zone = {boot.config.time_zone} hours')
        print(f'use_ack = {boot.config.use_ack}')
        print(f'ack_timeout = {boot.config.ack_timeout} sec')
        print(f'long_range = {boot.config.long_range}')
        print(f'tx_repeat = {boot.config.tx_repeat}')
        print(f'gps_max_wait_for_fix = {boot.config.gps_max_wait_for_fix} sec')
        print(f'next_collect_no_fix = {boot.config.next_collect_no_fix} sec')
        print(f'total_slots = {boot.config.total_slots}')
        print(f'slot_interval = {boot.config.slot_interval} sec')
        self.rx_avail = True

    def toRxMode(self):

        self.set_dio_mapping([0] * 6)
        self.reset_ptr_rx()
        self.set_mode(MODE.RXCONT)

    async def sendADV(self):

        self.set_dio_mapping([1,0,0,0,0,0])
        self.tx_avail = False
        self.write_payload([0xff,self.cid,0x00,0x00,0x01])
        #self.printT("Transmiting ADV Pkt ")
        self.set_mode(MODE.TX)
        while not self.tx_avail:
            await asyncio.sleep(0.001)
        #self.printT("Wait for Report Pkt")
        try:
            await asyncio.wait_for(self.changeMode(),RX_TIMEOUT)
        except asyncio.TimeoutError:
            await asyncio.sleep(0.001)
        #while not self.send_ack_mode:
        #    await asyncio.sleep(0.001)
    
    async def changeMode(self):
        while not self.send_ack_mode:
            await asyncio.sleep(0.001)
        await asyncio.sleep(0.001)

    async def sendACK(self):
        
        self.set_dio_mapping([1,0,0,0,0,0])
        self.tx_avail = False
        #self.printT(f"Transmiting ACK Pkt for Report {self.n_pkt}")
        self.write_payload([0xff,self.cid,0x00,0x00,0x03,self.n_pkt])
        self.set_mode(MODE.TX)
        while not self.tx_avail:
            await asyncio.sleep(0.001)
        #self.printT(f"Wait for Report Pkt seq {self.n_pkt + 1}")


    async def mainTask(self):

        await asyncio.sleep(1)
        while not self.send_ack_mode: 
            await self.sendADV()
        while self.send_ack_mode:
            if self.send_ack:
                self.send_ack = False
                await self.sendACK()
                #self.printT(f"Test Test {self.n_pkt}")
            await asyncio.sleep(0.1) # Important line            

    async def start(self):
        #self.printT(f"START f = {self.get_freq()} MHz")
        #await asyncio.sleep(0.001)
        while True:
            try:
                timeout = ((getTime() // SLOT_INT) + 1)*SLOT_INT  - getTime()
                slot = (((getTime() // SLOT_INT) + 1) % TOTAL_SLOT) + 1 + (self.cid*TOTAL_SLOT)
                self.eid = slot
                self.printT(f'F {self.get_freq()} Timout {timeout} Slot {slot}')
                #await asyncio.sleep(0.00001)
                await asyncio.wait_for(self.mainTask(), timeout=timeout)
            except asyncio.TimeoutError:
                self.set_mode(MODE.SLEEP)
                self.send_ack_mode = False
                self.send_ack = False
                self.set_dio_mapping([1,0,0,0,0,0])
                self.tx_avail = True
                self.rx_avail = False
                self.n_pkt = 0

class Uploader():

    def __init__(self,url):

        self.url = url
        self.name = "Uploader"

    def printT(self,text):
        if DEBUG:
            print(f"{TimeStamp()} [{self.name}] {text}")
        else:
            Log(f"{TimeStamp()} [{self.name}] {text}",LOG_FILE)

    async def start(self):
        #self.printT(f"Start Task Uploader Period {UPLOAD_INT}")
        while True:
            await asyncio.sleep(UPLOAD_INT)
            #self.printT("Start Upload")
            json_datas['timestamp'] = TimeStamp()[2:]
            #self.printT(f"Send Request {json_datas}")
            result = requests.post(API_LOCATION,json.dumps(json_datas),headers={'content-type': 'application/json'})
            if result.status_code == 200:
                #self.printT(f"Send Success")
                c_tempLog = copy.deepcopy(tempLog)
                json_datas['log_data'] = c_tempLog
            else:
                self.printT(f"Send Failure")



loras = []

for config in configs:

    lora = Mylora(config['board'],config['name'],config['id'])
    lora.set_pa_config(pa_select=1, max_power=21, output_power=15)
    lora.set_bw(config['bw'])
    lora.set_freq(config['freq'])
    lora.set_coding_rate(config['cr'])
    lora.set_spreading_factor(config['sf'])
    lora.set_rx_crc(True)
    lora.set_low_data_rate_optim(True)
    assert(lora.get_agc_auto_on() == 1)
    loras.append(lora)

for lora in loras:

    loop.create_task(lora.start())

uploader = Uploader(API_LOCATION)

#loop.create_task(uploader.start())

try:
    loop.run_forever()
except KeyboardInterrupt:
    sys.stdout.flush()
    print("Exit")
    sys.stderr.write("KeyboardInterrupt\n")
