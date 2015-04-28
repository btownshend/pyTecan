# Module to interface to BioShake
import serial
import string
import sys
import time
import logging
import debughook

class BioShake:
    debug=True
    PORT=3
    
    def __init__(self,to=1):
        fname=time.strftime("BioShake-%Y%m%d.log");
        logging.basicConfig(filename=fname, level=logging.DEBUG,format='%(asctime)s %(levelname)s:\t %(message)s')
        logging.captureWarnings(True)
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        formatter=logging.Formatter('%(message)s')
        console.setFormatter(formatter)
        logging.getLogger('').addHandler(console)
        
        logging.info("Running: %s"," ".join(sys.argv))
        if self.debug:
            logging.debug( "About to open serial port  %d",self.PORT)
        try:
            self.ser = serial.Serial(self.PORT,baudrate=9600,timeout=to)
        except serial.SerialException as e:
            logging.error("Failed to initialize serial port: %s",e)
            sys.exit(1)
        if self.debug:
            logging.debug(self.ser.portstr)

    def __del__(self):
        self.close()
        
    def open(self):
        self.ser = serial.Serial(self.PORT,baudrate=9600,timeout=1)
        if self.debug:
            logging.debug("Opened %s",self.ser.portstr)

    def setdebug(self):
        self.debug=True
        
    def close(self):
        self.ser.close()

    def execute(self,cmd):
        if self.debug:
            logging.debug("Sending command: %s",cmd)
        self.ser.write(cmd+"\r")
        line=self.ser.readline()
        line= string.strip(line)
        if line=="e":
            logging.error( "Error from BioShake while executing '%s'",cmd)
            if cmd!="getErrorList":
                errors=self.getErrorList()
                logging.error(" Errors: %s",errors)
        elif len(line)==0:
            logging.error("No response from BioShake while executing '%s'",cmd)
        elif self.debug:
            logging.debug("response: %s",line)
        return line

    def executeAndCheck(self,cmd):
        res=self.execute(cmd)
        if res!="ok":
            logging.error( "BioShake: Unexpected response to cmd '%s': %s",cmd, res)

    def getErrorList(self):
        res=self.execute("getErrorList")
        
    def version(self):
        res=self.execute("getVersion")
        return res
    
    def info(self):
        res=self.execute("info")
        return res
    
    def reset(self):
        self.executeAndCheck("resetDevice")

    def shake(self,onOff):
        if onOff:
            res=self.executeAndCheck("shakeOn")
        else:
            res=self.executeAndCheck("shakeOff")
        return res

    def getShakeState(self):
        res=self.execute("getShakeState")
        return res

    def home(self):
        self.executeAndCheck("shakeGoHome")
        
    def lock(self):
        self.executeAndCheck("setElmLockPos")

    def unlock(self):
        self.executeAndCheck("setElmUnlockPos")
        
    def isLocked(self):
        res=self.execute("getElmState")
        if res=="1":
            return True
        elif res=="3":
            return False
        else:
            logging.error("BioShake: Bad lock status: %s",res)

    def setSpeed(self,speed):
        if speed<0 or speed>3000:
            logging.error( "BioShake: Bad speed: %d",speed)
            return
        executeAndCheck("setShakeTargetSpeed"+speed)

    def setAcceleration(self,acceleration):
        if acceleration<0 or acceleration>10:
            logging.error("BioShake: Bad acceleration: %d seconds",acceleration)
            return
        executeAndCheck("setShakeAcceleration"+acceleration)
