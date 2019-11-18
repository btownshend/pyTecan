# Module to interface to RIC
import serial
import sys
import time
import os

epath = os.path.join(os.path.dirname(__file__), '..')
sys.path.append(epath)
from Experiment.config import Config
from Experiment import logging
from Experiment.db import LogDB, DB

debug=True
if True:
    PORT="/dev/cu.usbmodem144101"
    ser = serial.Serial(PORT,baudrate=9600,timeout=1,bytesize=serial.EIGHTBITS)
else:
    PORT="loop://"
    ser = serial.serial_for_url(PORT)

if debug:
    print(ser.portstr)

time.sleep(2)  # Give arduino time to reset

# Flush old data
if ser.inWaiting()>0:
    if debug:
        print("Input buffer had %d bytes"%ser.inWaiting())
    ser.reset_input_buffer()

# Request new data
ser.write(b'A')
ser.flush()
by=ser.read(2)
if len(by)==0:
    print('No response from Arduino')
    sys.exit(-1)
    
print(by)
val=int.from_bytes(by,byteorder="big")
if debug:
    print("got:%d"%val)

db=DB()
db.connect()

with db.cursor() as cursor:
    cursor.execute("select run,endtime from runs order by run desc limit 1")
    res=cursor.fetchone()
    print(res)
    
