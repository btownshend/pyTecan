# Module to interface to system liquid level monitor
import serial
import string
import sys
import time
import struct

class LiquidLevel:
    debug=True
    PORT=7 # "/dev/cu.usbmodem144101"

    def open(self):
        self.ser = serial.Serial(self.PORT,baudrate=9600,timeout=1)
        if self.debug:
            print(self.ser.portstr)
        time.sleep(2)  # Give arduino time to reset
        line=self.ser.readline().decode('utf-8').strip()
        if line != "LiquidLevel":
            print("Unexpected response from serial port while looking for 'LiquidLevel': ",line)
            sys.exit(-1)
	if self.debug:
	    print("Connected to arduino.")

    def setdebug(self):
        self.debug=True

    def close(self):
        self.ser.close()

    def execute(self,cmd):
        if self.debug:
            print("Sending command: ",cmd,)
        self.ser.write(cmd)
        res=self.ser.read(2)
        if self.debug:
            print(", response:",res)
	val=struct.unpack('>H',res)
	if self.debug:
	    print("val:",val)
	return val[0]

    def getlevel(self):
        res=self.execute(b"L")
        temp=float(res)
        return temp
