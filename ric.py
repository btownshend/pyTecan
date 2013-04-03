# Module to interface to RIC
import serial
import string

class RIC:
    debug=False
    PORT=1
    
    def open(self):
        self.ser = serial.Serial(self.PORT,baudrate=9600,timeout=1)
        if self.debug:
            print self.ser.portstr

    def setdebug(self):
        self.debug=True
        
    def close(self):
        self.ser.close()

    def execute(self,cmd):
        if self.debug:
            print "Sending command: ",cmd,
        self.ser.write(cmd+"\r")
        line=self.ser.readline()
        if self.debug:
            print ", response:",line
        return string.strip(line)

    def gettemp(self):
        res=self.execute("p")
	print "temp=",res
        temp=float(res)
	return temp

    def settemp(self,temp):
        res=self.execute("n%.1f"%temp)
        if res!="ok":
            print "RIC: Failed to set temperature to %.1f: %s" % (temp, res)

    def idle(self):
        res=self.execute("i")
        if res!="ok":
            print "RIC: Failed to go to idle: %s" % (res)

    def version(self):
        res=self.execute("v")
        return res
    
    def status(self):
        res=self.execute("S")
        return res
    
