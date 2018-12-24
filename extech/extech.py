# Module to interface to Extech thermometer
import serial
import string

class Extech:
	debug=True
	PORT="/dev/cu.SLAB_USBtoUART"

	def open(self):
		self.ser = serial.Serial(self.PORT,baudrate=9600,timeout=1)
		if self.debug:
			print(self.ser.portstr)

	def setdebug(self):
		self.debug=True

	def close(self):
		self.ser.close()

	def execute(self,cmd):
		if self.debug:
			print("Sending command: ",cmd)
		self.ser.write(cmd+b"\r")
		line=self.ser.readline()
		if self.debug:
			print(", response:",line)
		return line

	def status(self):
		res=self.execute(b"S")
		return res


e=Extech()
e.open()
print("Status = ",e.status())
