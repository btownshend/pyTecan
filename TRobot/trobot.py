# Module to interface to TRobot
import serial
import logging
import sys
import time

class BlockStatus:
    def __init__(self,x):
        self.status=x

    def __str__(self):
        s=""
        if self.status&0x1:
            s+=" running"
        if self.status&0x2:
            s+=" error"
        if self.status&0x4:
            s+=" plateau"
        if self.status&0x8:
            s+=" ramp"
        if self.status&0x10:
            s+=" autorestart"
        if self.status&0x20:
            s+=" cooling"
        if self.status&0x40:
            s+=" preheating"
        if self.status&0x80:
            s+=" pause"
        if self.status&0x100:
            s+=" hlerror"
        if self.status&0x200:
            s+=" coolerror"
        if len(s)>=1:
            s=s[1:]
        return s
            
class LidStatus:
    def __init__(self,x):
        self.status=x

    def __str__(self):
        s=""
        if self.status&0x1:
            s+=" heated"
        if self.status&0x2:
            s+=" too_hot"
        if self.status&0x4:
            s+=" too_often_on"
        if self.status&0x8:
            s+=" fast_heated"
        if self.status&0x100:
            s+=" open"
        if self.status&0x200:
            s+=" closed"
        if self.status&0x400:
            s+=" HW_error_1"
        if self.status&0x800:
            s+=" HW_error_2"
        if self.status&0x1000:
            s+=" time_out"
        if self.status&0x2000:
            s+=" safety_switch"
        if len(s)>=1:
            s=s[1:]
        return s

    def isopen(self):
        return (self.status&0x100)!=0

    def isclosed(self):
        return (self.status&0x200)!=0

class RunStatus:
    # Construct status from TRobot- reply to RUNS stored in 'm' as a sequence
    
    def __init__(self,m):
        # print "m=",m
        self.dirnr=int(m[0],16)
        self.prognr=int(m[1],16)
        self.progname=m[2].strip("'").strip()
        self.lidtemp=int(m[3],16)
        self.preheating=int(m[4])
        self.stepnr=int(m[5],16)
        self.bltemp=int(m[6],16)/100.0
        self.htime=int(m[7],16)
        if self.htime>=32768:
            self.htime=(self.htime-32768)*60
        self.loop=int(m[8],16)
        self.numloop=int(m[9],16)
        self.tempinc=int(m[11],16)/100.0
        self.timeinc=int(m[12],16)
        self.slope=int(m[13],16)/100.0

    def __str__(self):
        return (
                 "pgm:"+self.progname+
                 ", lid:"+str(self.lidtemp)+
                 ", blocktemp:"+str(self.bltemp)+
                 ", step:"+str(self.stepnr)
                 )
    
class TRobot:
    debug=False
    ser=None
    #PORT=3
    PORT="/dev/cu.KeySerial1"

    def __init__(self,to=5):
        fname=time.strftime("TRobot-%Y%m%d.log")
        logging.basicConfig(filename=fname, level=logging.DEBUG,format='%(asctime)s %(levelname)s:\t %(message)s')
        logging.captureWarnings(True)
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG if self.debug else logging.INFO)
        formatter=logging.Formatter('%(message)s')
        console.setFormatter(formatter)
        logging.getLogger('').addHandler(console)
        
        logging.info("Running: %s"," ".join(sys.argv))
        logging.debug( "About to open serial port "+self.PORT)
        try:
            self.ser = serial.Serial(self.PORT,baudrate=9600,timeout=to)
        except serial.SerialException as e:
            logging.error("Failed to initialize serial port: "+str(e))
            sys.exit(1)
        logging.debug(self.ser.portstr)

    def __del__(self):
        self.close()
        
    def setdebug(self):
        self.debug=True
        
    def close(self):
        if self.ser is not None and self.ser.isOpen():
            logging.debug( "Closing port")
            self.ser.close()

    def readline(self):
        res=""
        while True:
            b=self.ser.read(1)
            if len(b)==0:
                logging.error('Timeout on read')
                break
            if b=='\r':
                break
            res=res+b
        return res
    
    def execute(self,cmd):
        cmds=cmd.split(";")   # Split it
        if len(cmds)>1:
            res=None
            for c in cmds:
                res=self.execute(c)
            return res
        logging.debug( "Sending command: "+cmd)
        self.ser.write(cmd+"\r")
        self.ser.flush()
        res=self.readline()
        res=res.strip()
        logging.debug( "response: <"+res+">")
        if len(res)==0:
            logging.error("Empty response to %s: %s "%(cmd,self.errorstr(res[1:])))
            raise ValueError("Empty response")
        if res[0]=='!':
            logging.error("Got error %s in response to %s: %s "%(res[1:],cmd,self.errorstr(res[1:])))
            raise ValueError(res[1:])
        shortcmd=cmd[0]
        if shortcmd==":":
            shortcmd=cmd[1]
        if shortcmd.upper()!=res[0].upper():
            logging.error("Sent cmd <%s>, but response was <%s>"%(cmd,res))
            raise ValueError("Mismatched response")
        elif len(res)>2:
            res=res[2:]
            if res[0]=='!':
                logging.error("Got error %s in response to %s: %s "%(res[1:],cmd,self.errorstr(res[1:])))
                raise ValueError(res[1:])
        else:
            res=None        

        return res

    def gettemp(self):
        res=self.execute(":b;l") # TEMP
        temp=int(res,16)/100.0
        return temp

    def getlidtemp(self):
        res=self.execute(":b;o") # HTMP
        temp=int(res,16)/100.0
        return temp

    def cancel(self): 
        res=self.execute(":b;i")   # STOP

    def version(self):
        res=self.execute(":d;c")
        return res
    
    def getstatus(self):
        res=self.execute(":b;a")   # BSTT
        return BlockStatus(int(res,16))

    def getrunstatus(self):
        p=self.execute(":b;q")   # RUNS
        s=p.split(",")
        res=RunStatus(s)
        return res
    
    def getremainingtime(self):
        remt=self.execute(":b;r") # REMT
        remt=int(remt,16)
        return remt
    
    def run(self,prognr=0):  
        self.execute(":b;h 0,%d"%(prognr))
        
    def getlidstatus(self):
        response=self.execute(":b;d") # HSTT
        #logging.debug("getlidstatus: got <%s>"%response)
        return LidStatus(int(response,16))

    def getloopcounters(self):
        resp=self.execute(":b;p") # LOOP
        return resp
        
    def lidopen(self):
        res=self.execute(":b;f") # OPEN

    def lidclose(self):
        res=self.execute(":b;g") #CLOS

    def folders(self):
        dirnames=[]
        for i in range(10):
            dirnames.append(self.execute(":c;e %d"%i).strip("'"))
        return dirnames
    
    def programs(self,dirnr):  
        p=[]
        while True:
            if len(p)==0:
                s=self.execute(":c;d %04x"%dirnr)
            else:
                s=self.execute(":c;d")
            if s is None:
                break
            p.append(s)
        return p

    def erase(self, prognr):  
        dirnr=0
        try:
            res = self.execute(':c;b %04x,%04x'%(dirnr,prognr))
        except ValueError as err:
            print "err=<",err,">,args=",err.args[0]
            if err.args[0]=='105':
                print "Ignoring error from erase"
            else:
                raise

    def program(self,name,lidtemp,steps):
        # Always use 0,0 slot
        # steps is a list of LIBR/EDIT commands as strings (typically  'c [bltemp,htime [,loop,#loops[,0[,tempinc[,timeinc[,slope]]]]]]' )
        prognr=0
        dirnr=0
        self.erase(prognr)
        self.execute(':c;a %04x,%04x'%(dirnr,prognr))     # EDIT
        self.execute("a %04x,1,'%-8.8s'"%(lidtemp,name))
        for step in steps:
            self.execute(step)
        runtime=self.execute('h')    # RUNT
        runtime=int(runtime,16)
        self.execute('g')   # EEND
        logging.info( "Programmed %s: runtime = %d minutes"%(name,runtime))
        return runtime

    def showpgm(self,dirnr,prognr):
        # Dump a program
        self.execute(':c;a %04x,%04x'%(dirnr,prognr))     # EDIT
        hdr=self.execute("a")
        print "header=",hdr
        nstep=self.execute("d")
        nstep=int(nstep,16)
        steps=[]
        for i in range(nstep):
            steps.append(self.execute("c"))
        print "steps=",steps
        return [hdr,steps]
    
    def errorstr(self,ecode):
        'Parse 3 hex digits in ecode string'
        estr=''
        if ecode[0]=='0':
            estr="System Error: "
            if ecode=='001':
                estr+="remote control off!"
            elif ecode=='002':
                estr+="software error"
            elif ecode=='003':
                estr+="wait: too cold!"
            elif ecode=='004':
                estr+="wait: too hot!"
            elif ecode=='005':
                estr+="no printer!"
            elif ecode=='006':
                estr+="no heated lid!"
            elif ecode=='007':
                estr+="printer active!"
            elif ecode=='008':
                estr+="paper feed"
            elif ecode=='009':
                estr+="display contrast"
            elif ecode=='010':
                estr+="handshake not possible"
            else:
                estr+=ecode
        elif ecode[0]=='1':
            estr='Edit Error:'
            if ecode=='101':
                estr+="max %1d!"
            elif ecode=='102':
                estr+="max %2d!"
            elif ecode=='103':
                estr+="edit not possible!"
            elif ecode=='104':
                estr+="pgm full: %2d steps!"
            elif ecode=='105':
                estr+="pgm is empty!"
            elif ecode=='106':
                estr+="pgm is active!"
            elif ecode=='107':
                estr+="pgm is edited!"
            elif ecode=='108':
                estr+="RAM full! , memory full"
            elif ecode=='109':
                estr+="only %3d programs possible!"
            elif ecode=='110':
                estr+="max %2d!"
            elif ecode=='111':
                estr+="min = 1!"
            elif ecode=='112':
                estr+="max = %2d!"
            elif ecode=='113':
                estr+="min %4f1 max %5f1!"
            elif ecode=='114':
                estr+="min %5f1C, max %5f1C!"
            elif ecode=='115':
                estr+="max %2h%2m%2s!"
            elif ecode=='116':
                estr+="max %2d!"
            elif ecode=='117':
                estr+="too many nested cycles!"
            elif ecode=='118':
                estr+="back cycles only: max = %2d!"
            elif ecode=='119':
                estr+="cycle into cycle!"
            elif ecode=='120':
                estr+="cycle out of cycle!"
            elif ecode=='121':
                estr+="gradient out of temperature range!"
            elif ecode=='122':
                estr+="%5f1C - %5f1C!"
            elif ecode=='123':
                estr+="max +-%2d C!"
            elif ecode=='124':
                estr+="max. %3d s!"
            elif ecode=='125':
                estr+="value?!"
            elif ecode=='126':
                estr+="cycle value?!"
            else:
                estr+=ecode
        elif ecode[0]=='2':
            estr='Block Error:'
            if ecode=='200':
                estr+="no block error!"
            elif ecode=='201':
                estr+="unidentified error!"
            elif ecode=='202':
                estr+="emergency off!"
            elif ecode=='203':
                estr+="peltier contact??!"
            elif ecode=='204':
                estr+="temp fault!"
            elif ecode=='205':
                estr+="cooling current low!"
            elif ecode=='206':
                estr+="heating current low!"
            elif ecode=='207':
                estr+="lid too hot!"
            elif ecode=='208':
                estr+="cooler fault!"
            elif ecode=='209':
                estr+="opening not possible!"
            elif ecode=='210':
                estr+="closing not possible!"
            elif ecode=='211':
                estr+="motor disconnected??!"
            else:
                estr+=ecode
        elif ecode[0]=='3':
            estr='Block Using Error:'
            if ecode=='300':
                estr+="pgm finished or paused!"
            elif ecode=='301':
                estr+="start not possible!"
            elif ecode=='302':
                estr+="block off!"
            elif ecode=='303':
                estr+="blocks 1 .. %1d!"
            elif ecode=='304':
                estr+="lid is open!"
            elif ecode=='305':
                estr+="lid is closed!"
            elif ecode=='306':
                estr+="lid is not in endposition!"
            elif ecode=='307':
                estr+="block is active!"
            elif ecode=='308':
                estr+="wrong block type!"
            elif ecode=='309':
                estr+="no in tube sensor!"
            elif ecode=='310':
                estr+="pgm not paused!"
            else:
                estr+=ecode
        elif ecode[0]=='4':
            estr='Memory Error:'
            if ecode=='401':
                estr+="name deleted!"
            elif ecode=='402':
                estr+="pg %1d/%2d and the following empty!"
            elif ecode=='403':
                estr+="%3d pgm's empty!"
            elif ecode=='404':
                estr+="no steps!"
            elif ecode=='405':
                estr+="data error: block %1d stopped!"
            elif ecode=='406':
                estr+="checksum error!"
            else:
                estr+=ecode
        elif ecode[0]=='5':
            estr='Input Syntax Error:'
            if ecode=='501':
                estr+="invalid command!"
            elif ecode=='502':
                estr+="missing command!"
            elif ecode=='503':
                estr+="missing separator!"
            elif ecode=='504':
                estr+="separator error!"
            elif ecode=='505':
                estr+="missing apostrophe!"
            elif ecode=='506':
                estr+="convert error!"
            elif ecode=='507':
                estr+="missing parameter!"
            elif ecode=='508':
                estr+="wrong parameter!"
            else:
                estr+=ecode
        elif ecode[0]=='6':
            estr='Buffer Error:'
            if ecode=='601':
                estr+="rx write denied!"
            elif ecode=='602':
                estr+="rx read denied!"
            elif ecode=='603':
                estr+="overflow rx!"
            elif ecode=='604':
                estr+="rx time-out"
            elif ecode=='611':
                estr+="tx write denied!"
            elif ecode=='612':
                estr+="tx read denied!"
            elif ecode=='613':
                estr+="overflow tx!"
            elif ecode=='621':
                estr+="sy0 write denied!"
            elif ecode=='622':
                estr+="sy0 read denied!"
            elif ecode=='623':
                estr+="overflow sy0!"
            elif ecode=='631':
                estr+="sy1 write denied!"
            elif ecode=='632':
                estr+="sy1 read denied!"
            elif ecode=='633':
                estr+="overflow sy1!"
            elif ecode=='641':
                estr+="sync data fault!"
            else:
                estr+=ecode
        logging.debug("Error %s -> %s"%(ecode, estr))
        return estr
