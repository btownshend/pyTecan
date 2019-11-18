# Module to interface to system liquid level monitor
import serial
import string
import sys
import time

class LiquidLevel:
    debug=False
    PORT="/dev/cu.usbmodem144101"

    def open(self):
        self.ser = serial.Serial(self.PORT,baudrate=9600,timeout=1)
        if self.debug:
            print(self.ser.portstr)
        time.sleep(2)  # Give arduino time to reset
        line=self.ser.readline().decode('utf-8').strip()
        if line != "LiquidLevel":
            print("Unexpected response from serial port while looking for 'LiquidLevel': ",line)
            sys.exit(-1)

    def setdebug(self):
        self.debug=True

    def close(self):
        self.ser.close()

    def execute(self,cmd):
        if self.debug:
            print("Sending command: ",cmd,end="")
        self.ser.write(cmd)
        res=self.ser.read(2)
        if self.debug:
            print(", response:",res)
        return int.from_bytes(res,byteorder="big")

    def getlevel(self):
        res=self.execute(b"L:")
        temp=float(res)
        return temp
