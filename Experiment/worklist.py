"Module for generating a worklist from a set of commands"
import string
from plate import Plate
import shutil

_WorkList__DITI200=0
_WorkList__DITI10=2

class WorkList(object):
    "A Gemini worklist created programmatically"
    OPEN=0
    CLOSE=1
    DONOTMOVE=2
    SAFETOEND=0
    ENDTOSAFE=1
    
    def __init__(self):
        self.debug=False
        self.list=[]
        self.volumes={}
        self.diticnt=[0,0,0,0]   # Indexed by DiTi Type
        self.elapsed=0   # Self.Elapsed time in seconds

    def bin(s):
        return str(s) if s<=1 else bin(s>>1) + str(s&1)

    @staticmethod
    def wellSelection(nx,ny,pos):
        'Build a well selection string'
        s="%02x%02x"%(nx,ny)
        vals=[ 0 for x in range(7*((nx*ny+6)/7)) ]
        for i in pos:
            vals[i]=1
        bitCounter=0
        bitMask=0
        for i in range(len(vals)):
            if vals[i]:
                bitMask=bitMask | (1<<bitCounter)
            bitCounter=bitCounter+1
            if bitCounter>6:
                s=s+chr(0x30+bitMask)
                bitCounter=0
                bitMask=0
        if bitCounter>0:
            s=s+chr(0x30+bitMask)
        return s

    #def aspirate(tipMask, liquidClass, volume, loc, spacing, ws):
    def aspirate(self,tipMask,wells, liquidClass, volume, loc):
        self.aspirateDispense('Aspirate',tipMask,wells, liquidClass, volume, loc)

    def dispense(self,tipMask,wells, liquidClass, volume, loc):
        self.aspirateDispense('Dispense',tipMask,wells, liquidClass, volume, loc)

    def mix(self,tipMask,wells, liquidClass, volume, loc, cycles=3):
        self.aspirateDispense('Mix',tipMask,wells, liquidClass, volume, loc, cycles)
        
    def aspirateDispense(self,op,tipMask,wells, liquidClass, volume, loc, cycles=None):
        assert(isinstance(loc,Plate))

        print "%s %d %s.%s %.2f"%(op,tipMask,str(loc),str(wells),volume)
        # Update volumes
        if op=='Aspirate':
            vincr=-volume
        elif op=='Dispense':
            vincr=volume
        else:
            vincr=0
            
        if vincr != 0:
            if loc not in self.volumes:
                self.volumes[loc]={}
            for well in wells:
                if well not in self.volumes[loc]:
                    self.volumes[loc][well]=vincr
                else:
                    self.volumes[loc][well]=self.volumes[loc][well]+vincr
                    
        spacing=1
        pos=[0 for x in range(len(wells))]
        for i in range(len(wells)):
            well=wells[i]
            if isinstance(well,(long,int)):
                ival=int(well)
                (col,row)=divmod(ival,loc.ny)
                col=col+1
                row=row+1
            else:
                col=int(well[1:])
                row=ord(well[0])-ord('A')+1
            assert(row>=1 and row<=loc.ny and col>=1 and col<=loc.nx)
            pos[i]=(row-1)+loc.ny*(col-1)
            if i>0:
                assert(col==prevcol)
            prevcol=col

        span=pos[len(pos)-1]-pos[0]
        if span<4:
            spacing=1
        else:
            spacing=2
        allvols=[0 for x in range(12)]
        tip=0
        tipTmp=tipMask;
        for i in range(len(wells)):
            while tipTmp&1 == 0:
                tipTmp=tipTmp>>1
                tip=tip+1
            if type(volume)==type([]):
                allvols[tip]=volume[i]
            else:
                allvols[tip]=volume
            tipTmp = tipTmp>>1
            tip+=1

        if tipTmp!=0:
            print "Number of tips (mask=%d) != number of wells (%d)"%tipMask, len(wells)
            assert(0)
            
        if self.debug:
            print "allvols=",allvols
            print "pos[0]=",pos[0]
            print "spacing=",spacing

        ws=WorkList.wellSelection(loc.nx,loc.ny,pos)
        volstr="%.2f"%allvols[0]
        for i in range(1,12):
            volstr="%s,%.2f"%(volstr,allvols[i]);
        if op=="Mix":
            self.list.append( '%s(%d,"%s",%s,%d,%d,%d,"%s",%d,0)'%(op,tipMask,liquidClass,volstr,loc.grid,loc.pos-1,spacing,ws,cycles))
        else:
            self.list.append( '%s(%d,"%s",%s,%d,%d,%d,"%s",0)'%(op,tipMask,liquidClass,volstr,loc.grid,loc.pos-1,spacing,ws))
        self.elapsed+=4
        
    # Get DITI
    def getDITI(self, tipMask, volume, retry=True,multi=False):
        MAXVOL10=10
        MAXVOL200=200
        
        assert(tipMask>=1 and tipMask<=15)
        assert(volume>0 and volume<=MAXVOL200)
        if retry:
            options=1
        else:
            options=0
        if volume<=MAXVOL10:
            type=__DITI10
        else:
            type=__DITI200

        self.list.append('GetDITI(%d,%d,%d)'%(tipMask,type,options))
        self.elapsed+=2
        if tipMask&1:
            self.diticnt[type]+=1
        if tipMask&2:
            self.diticnt[type]+=1
        if tipMask&4:
            self.diticnt[type]+=1
        if tipMask&8:
            self.diticnt[type]+=1
        
    def getDITIcnt(self):
        return "10ul: %d, 200ul: %d"%(self.diticnt[__DITI10],self.diticnt[__DITI200])

    def dropDITI(self, tipMask, loc, airgap=10, airgapSpeed=70):
        'Drop DITI, airgap is in ul, speed in ul/sec'
        assert(tipMask>=1 and tipMask<=15)
        assert(airgap>=0 and airgap<=100)
        assert(airgapSpeed>=1 and airgapSpeed<1000)
        self.list.append('DropDITI(%d,%d,%d,%f,%d)'%(tipMask,loc.grid,loc.pos-1,airgap,airgapSpeed))
        self.elapsed+=2
        
    def wash(self, tipMask):
        wasteLoc=(1,1)
        cleanerLoc=(1,0)
        wasteVol=1  # in ml
        wasteDelay=500 # in msec
        cleanerVol=0.5 # in ml
        cleanerDelay=500 # in msec
        airgap=10  # ul
        airgapSpeed=70 # ul/sec
        retractSpeed=30 # mm/sec
        fastWash=1
        lowVolume=0
        atFreq=1000  # Hz, For Active tip
        self.list.append('Wash(%d,%d,%d,%d,%d,%.1f,%d,%.1f,%d,%.1f,%d,%d,%d,%d,%d)'%(tipMask,wasteLoc[0],wasteLoc[1],cleanerLoc[0],cleanerLoc[1],wasteVol,wasteDelay,cleanerVol,cleanerDelay,airgap, airgapSpeed, retractSpeed, fastWash, lowVolume, atFreq))
        print "Wash %d"%tipMask
        self.elapsed+=11
        
    def periodicWash(self,tipMask,period):
        wasteLoc=(1,1)
        cleanerLoc=(1,0)
        wasteVol=1  # in ml
        wasteDelay=500 # in msec
        cleanerVol=0.5 # in ml
        cleanerDelay=500 # in msec
        airgap=20  # ul
        airgapSpeed=20 # ul/sec
        retractSpeed=30 # mm/sec
        fastWash=0
        lowVolume=0
        atFreq=1000  # Hz, For Active tip
        self.list.append('Periodic_Wash(%d,%d,%d,%d,%d,%.1f,%d,%.1f,%d,%.1f,%d,%d,%d,%d,%d,%d)'%(tipMask,wasteLoc[0],wasteLoc[1],cleanerLoc[0],cleanerLoc[1],wasteVol,wasteDelay,cleanerVol,cleanerDelay,airgap, airgapSpeed, retractSpeed, fastWash, lowVolume, period, atFreq))
                         
    def vector(self, vector,loc, direction, andBack, safeAction, endAction, slow=True):
        'Move ROMA.  Gripper actions=0 (open), 1 (close), 2 (do not move).'
        if slow:
            speed=1
        else:
            speed=0
        if andBack:
            andBack=1
        else:
            andBack=0
        self.list.append('Vector("%s",%d,%d,%d,%d,%d,%d,%d,0)'%(vector,loc.grid,loc.pos,direction,andBack,safeAction, endAction, speed))
        self.elapsed+=12
        
    def romahome(self):
        self.list.append('ROMA(2,0,0,0,0,0,60,0,0)')
        self.elapsed+=5
        
    def userprompt(self, text, beeps=0, closetime=-1):
        'Prompt the user with text.  Beeps = 0 (no sound), 1 (once), 2 (three times), 3 (every 3 seconds).  Close after closetime seconds if > -1'
        self.list.append('UserPrompt("%s",%d,%d)'%(text,beeps,closetime))

    def comment(self, text,prepend=False):
        if prepend:
            self.list.insert(0,'Comment("%s")'%text)
        else:
            self.list.append('Comment("%s")'%text)

    def userprompt(self, text,timeout=-1,prepend=False):
        cmd='UserPrompt("%s",0,%d)'%(text,timeout)
        if prepend:
            self.list.insert(0,cmd)
        else:
            self.list.append(cmd)
        
    def execute(self, command, wait=True, resultvar=None):
        'Execute an external command'
        flags=0
        if wait:
            flags=flags | 2
        if resultvar!=None and resultvar!="":
            flags=flags | 4
        else:
            resultvar=""
        self.list.append('Execute("%s",%d,"%s")'%(command,flags,resultvar))
        self.elapsed+=5
        
    def pyrun(self, cmd):
        self.execute("C:\Python27\python.exe C:\cygwin\Home\Admin\%s"%cmd)
        
    def dump(self):
        'Dump current worklist'
        for i in range(len(self.list)):
            print self.list[i]

    def dumpvols(self):
        'Dump final volumes'
        for loc in self.volumes:
            for well in self.volumes[loc]:
                print "%-14s\t%s\t%6.1f"%(str(loc),str(well),self.volumes[loc][well])
        
    def saveworklist(self,filename):
        'Save worklist in a file in format that Gemini can load as a worklist'
        fd=open(filename,'w')
        for i in range(len(self.list)):
            print >>fd, "B;%s"%string.replace(str(self.list[i]),'\n','\f\a')
        fd.close()
        
    def savegem(self,headerfile,filename):
        'Save worklist in a file in format that Gemini can load as an experiment'
        shutil.copy(headerfile,filename)
        fd=open(filename,'a')
        for i in range(len(self.list)):
            print >>fd, "%s"%string.replace(str(self.list[i]),'\n','\f\a')
        fd.close()
        
