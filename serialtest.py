import serial
import serial.tools.list_ports
allports=serial.tools.list_ports.comports()
for p in allports:
    print p
ser = serial.Serial(1,baudrate=9600,timeout=1)
print ser.portstr
ser.write("s")
line=ser.readline()
print "Got: %s"%line
ser.close()

