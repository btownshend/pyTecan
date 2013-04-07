# Module to interface to Mettler scale using MT-SICS interface
import serial
import string

class Scale:
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
        self.ser.write(cmd+"\r\n")
        line=self.ser.readline()
        if self.debug:
            print ", response:",line
        return string.strip(line).split(" ")

    def getweight(self):
        res=self.execute("S")
        if res[0]!='S':
            print "Unexpected response to S command: ",res
            return -1
        if res[1]=='S':
            return float(res[2])
        elif res[1]=='+':
            return float("inf")
        elif res[1]=='-':
            return float("-inf")
        else:
            print "Command not executed: ",res

	return -1

    def zero(self):
        res=self.execute("Z")
        if res[0]!='Z' or res[1]!='A':
            print "Unexpected response to Z command: ", res
            return -1

    def getversion(self):
        res=self.execute("I1")
        if res[0]!="I1" or res[1]!="A":
            print "Unexpected response to I1 command: ", res
            return -1
        return res[2:]
    
    def setpower(self,on):
        if on:
            res=self.execute("PWR 1")
        else:
            res=self.execute("PWR 1")
        if res[0]!="PWR" or res[1]!="A":
            print "Unexpected response to PWR command:",res
