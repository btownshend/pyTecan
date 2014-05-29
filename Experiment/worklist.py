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
    lnum=0
    
    def __init__(self):
        self.debug=False
        self.list=[]
        self.volumes={}
        self.diticnt=[0,0,0,0]   # Indexed by DiTi Type
        self.elapsed=0   # Self.Elapsed time in seconds
        self.delayEnabled=False
        self.opQueue=[]
        
    def bin(s):
        return str(s) if s<=1 else bin(s>>1) + str(s&1)

    def setOptimization(self,onoff):
        if onoff:
            self.comment("*Optimization on")
        else:
            self.flushQueue()
            self.comment("*Optimization off")
        self.delayEnabled=onoff
        
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

    def moveliha(self, loc):
        self.flushQueue()
        tipMask=15
        speed=10   # 0.1-400 (mm/s)
        self.comment('*MoveLiha to '+str(loc))
        self.list.append( 'MoveLiha(%d,%d,%d,1,"0104?",0,4,0,%.1f,0)'%(tipMask,loc.grid,loc.pos-1,speed))
        self.elapsed+=1.55
        
    def optimizeQueue(self):
        'Optimize operations in queue'
        # assert(False)    # Currently broken, manual mix with a chain of aspirateNC/dispense ends up doing all the aspirates first, then all the dispenses
        # for d in self.opQueue:
        #     print "PRE-OPT %s:\tTip %d, Loc (%d,%d) Wells %s"%(d[0],d[1],d[5].grid,d[5].pos,str(d[2]))
        # As much as possible, move together operations on a single plate
        newQueue=[]
        oldlen=len(self.opQueue)
        while len(self.opQueue)>0:
            d1=self.opQueue[0]
            newQueue.append(d1)
            self.opQueue.remove(d1)
            dirtyTips=0;
            for d in self.opQueue:
                if d[5].grid==d1[5].grid and d[5].pos==d1[5].pos and d[0]==d1[0]:
                    'Same grid,loc'
                    if d[1]&dirtyTips != 0:
                        'Tip used in intervening operations'
                        print 'Intervening tip use:',[str(item) for item in d]
                        break
                    newQueue.append(d)
                    #self.opQueue.remove(d)
                else:
                    dirtyTips|=d[1]
            self.opQueue=[d for d in self.opQueue if d not in newQueue]
        # for d in newQueue:
        #     print "POSTOPT %s:\tTip %d, Loc (%d,%d) Wells %s"%(d[0],d[1],d[5].grid,d[5].pos,str(d[2]))
        assert(len(newQueue)+len(self.opQueue)==oldlen)
        self.opQueue=newQueue

        # Try to combine multiple operations into one command
        todelete=[]
        for i in range(len(self.opQueue)-1):
            d1=self.opQueue[i];
            d2=self.opQueue[i+1];
            if False and d1[0]=='Dispense' and d2[0]=='Mix' and d1[1]==d2[1] and i+2<len(self.opQueue) and self.opQueue[i+2][1]!=d1[1]:
                # Special case of dispense/mix
                #print "DISPENSE/MIX"
                d2=self.opQueue[i+2]
                self.opQueue[i+2]=self.opQueue[i+1]
                self.opQueue[i+1]=d2
            if d1[0]==d2[0]  and d1[1]!=d2[1] and d1[5]==d2[5]:
                #print "COMBINE %s:\tTip %d, Loc (%d,%d) Wells %s"%(d1[0],d1[1],d1[5].grid,d1[5].pos,str(d1[2]))
                # print "   WITH %s:\tTip %d, Loc (%d,%d) Wells %s"%(d2[0],d2[1],d2[5].grid,d2[5].pos,str(d2[2]))
                if (d2[1]<d1[1]) or (((d2[1]>>1) &d1[1])==0):
                    pass # print "tipmasks out of order (%d,%d)"%(d2[1],d1[1])
                elif d2[2][0] != max(d1[2])+1:
                    pass # print "wells not adjacent"
                elif d1[2][0]/d1[5].ny != d2[2][0]/d2[5].ny:
                    pass # print "wells in different columns of %d-row plate"%d1[5].ny
                elif d1[3].name!=d2[3].name:
                    pass # print "liquid classes different",d1[3],d2[3]
                elif d1[6]!=d2[6]:
                    pass # print "mix cycles different"
                else:
                    merge=[d1[0],d1[1]|d2[1],d1[2]+d2[2],d1[3],d1[4]+d2[4],d1[5],d1[6]];
                    #print " MERGED %s:\tTip %d, Loc (%d,%d) Wells %s"%(merge[0],merge[1],merge[5].grid,merge[5].pos,str(merge[2]))
                    # self.comment("Merged operations")
                    self.opQueue[i+1]=merge
                    todelete.append(i)
                
        self.opQueue[:]=[self.opQueue[z] for z in range(len(self.opQueue)) if z not in todelete]
        
    def flushQueue(self):
        if not self.delayEnabled or len(self.opQueue)==0:
            return
        self.comment('*Flush queue')
        self.optimizeQueue()
        for d in self.opQueue:
            self.aspirateDispense(d[0],d[1],d[2],d[3],d[4],d[5],d[6],False)
        self.opQueue=[]
        
    #def aspirate(tipMask, liquidClass, volume, loc, spacing, ws):
    def aspirate(self,tipMask,wells, liquidClass, volume, loc):
        self.aspirateDispense('Aspirate',tipMask,wells, liquidClass, volume, loc)

    # aspirate without manual conditioning
    def aspirateNC(self,tipMask,wells, liquidClass, volume, loc):
        self.aspirateDispense('AspirateNC',tipMask,wells, liquidClass, volume, loc)

    def dispense(self,tipMask,wells, liquidClass, volume, loc):
        self.aspirateDispense('Dispense',tipMask,wells, liquidClass, volume, loc)

    def mix(self,tipMask,wells, liquidClass, volume, loc, cycles=3):
        self.aspirateDispense('Mix',tipMask,wells, liquidClass, volume, loc, cycles)
        
    def aspirateDispense(self,op,tipMask,wells, liquidClass, volume, loc, cycles=None,allowDelay=True):
        'Execute or queue liquid handling operation'
        assert(isinstance(loc,Plate))

        if type(volume)!=type([]):
            volume=[volume for w in wells]
            
        if self.delayEnabled and allowDelay:
            self.opQueue.append([op,tipMask,wells,liquidClass,volume,loc,cycles])
            self.comment("*Queued: %s tip=%d well=%s.%s vol=%s lc=%s"%(op,tipMask,str(loc),str(wells),str(volume),str(liquidClass)))
            return

        if op=='Mix':
            self.elapsed+=9.92
        elif op=='Dispense':
            self.elapsed+=3.12
        elif op=='Aspirate':
            self.elapsed+=3.50+3.12   # Extra for conditioning volume
        elif op=='AspirateNC':
            self.elapsed+=3.50
            
        self.comment("*%s tip=%d well=%s.%s vol=%s lc=%s"%(op,tipMask,str(loc),str(wells),str(volume),str(liquidClass)))
        # Update volumes
        for i in range(len(wells)):
            well=wells[i]
            v=volume[i]
            if op=='Aspirate' or op=='AspirateNC':
                vincr=-v
            elif op=='Dispense':
                vincr=v
            else:
                vincr=0
            
            if vincr != 0:
                if loc not in self.volumes:
                    self.volumes[loc]={}
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
        tipTmp=tipMask
        for i in range(len(wells)):
            while tipTmp&1 == 0:
                tipTmp=tipTmp>>1
                tip=tip+1
            allvols[tip]=volume[i]
            tipTmp = tipTmp>>1
            tip+=1

        if tipTmp!=0:
            print "Number of tips (mask=%d) != number of wells (%d)"%(tipMask, len(wells))
            assert(0)
            
        if self.debug:
            print "allvols=",allvols
            print "pos[0]=",pos[0]
            print "spacing=",spacing

        ws=WorkList.wellSelection(loc.nx,loc.ny,pos)
        if op=='Aspirate':
            if allvols[0]>0:
                volstr="%.2f"%(allvols[0]+2)
                condvol="2"
            else:
                volstr="%.2f"%(allvols[0])
                condvol="0"
            for i in range(1,12):
                if allvols[i]>0:
                    c=2
                else:
                    c=0
                volstr="%s,%.2f"%(volstr,allvols[i]+c)
                condvol="%s,%.2f"%(condvol,c)
        else:
            volstr="%.2f"%allvols[0]
            for i in range(1,12):
                volstr="%s,%.2f"%(volstr,allvols[i])
                
        if op=="Mix":
            self.list.append( '%s(%d,"%s",%s,%d,%d,%d,"%s",%d,0)'%(op,tipMask,liquidClass,volstr,loc.grid,loc.pos-1,spacing,ws,cycles))
        elif op=="AspirateNC":
            self.list.append( '%s(%d,"%s",%s,%d,%d,%d,"%s",0)'%("Aspirate",tipMask,liquidClass,volstr,loc.grid,loc.pos-1,spacing,ws))
        else:
            self.list.append( '%s(%d,"%s",%s,%d,%d,%d,"%s",0)'%(op,tipMask,liquidClass,volstr,loc.grid,loc.pos-1,spacing,ws))
        if op=="Aspirate":
            # Return conditioning volume
             self.list.append( '%s(%d,"%s",%s,%d,%d,%d,"%s",0)'%("Dispense",tipMask,liquidClass,condvol,loc.grid,loc.pos-1,spacing,ws))
        ptr=0
        for i in range(len(allvols)):
            if allvols[i]>0:
                self.SIM(i,op,allvols[i],loc,pos[ptr])
                ptr+=1

    def SIM(self,tip,op,vol,loc,pos):
        #print "SIM",tip,op,vol,loc,pos
        pass
        
    # Get DITI
    def getDITI(self, tipMask, volume, retry=True,multi=False):
        self.flushQueue()
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
        self.flushQueue()
        assert(tipMask>=1 and tipMask<=15)
        assert(airgap>=0 and airgap<=100)
        assert(airgapSpeed>=1 and airgapSpeed<1000)
        self.list.append('DropDITI(%d,%d,%d,%f,%d)'%(tipMask,loc.grid,loc.pos-1,airgap,airgapSpeed))
        self.elapsed+=2
        
    def wash(self, tipMask,wasteVol=1,cleanerVol=2,deepClean=False):
        self.flushQueue()
        self.comment("*Wash with tips=%d, wasteVol=%d, cleanerVol=%d, deep=%s"%(tipMask,wasteVol,cleanerVol,"Y" if deepClean else "N"))
        wasteLoc=(1,1)
        if deepClean:
            cleanerLoc=(1,2)
        else:
            cleanerLoc=(1,0)
        wasteDelay=500 # in msec
        cleanerDelay=500 # in msec
        airgap=10  # ul
        airgapSpeed=20 # ul/sec
        retractSpeed=30 # mm/sec
        fastWash=1
        lowVolume=0
        atFreq=1000  # Hz, For Active tip
        self.list.append('Wash(%d,%d,%d,%d,%d,%.1f,%d,%.1f,%d,%.1f,%d,%d,%d,%d,%d)'%(tipMask,wasteLoc[0],wasteLoc[1],cleanerLoc[0],cleanerLoc[1],wasteVol,wasteDelay,cleanerVol,cleanerDelay,airgap, airgapSpeed, retractSpeed, fastWash, lowVolume, atFreq))
        #print "Wash %d,%.1fml,%.1fml,deep="%(tipMask,wasteVol,cleanerVol),deepClean
        self.elapsed+=19.21
        
    def periodicWash(self,tipMask,period):
        wasteLoc=(1,1)
        cleanerLoc=(1,0)
        wasteVol=1  # in ml
        wasteDelay=500 # in msec
        cleanerVol=0.5 # in ml
        cleanerDelay=500 # in msec
        airgap=10  # ul
        airgapSpeed=20 # ul/sec
        retractSpeed=30 # mm/sec
        fastWash=1
        lowVolume=0
        atFreq=1000  # Hz, For Active tip
        self.list.append('Periodic_Wash(%d,%d,%d,%d,%d,%.1f,%d,%.1f,%d,%.1f,%d,%d,%d,%d,%d,%d)'%(tipMask,wasteLoc[0],wasteLoc[1],cleanerLoc[0],cleanerLoc[1],wasteVol,wasteDelay,cleanerVol,cleanerDelay,airgap, airgapSpeed, retractSpeed, fastWash, lowVolume, period, atFreq))
                         
    def vector(self, vector,loc, direction, andBack, initialAction, finalAction, slow=False):
        'Move ROMA.  Gripper actions=0 (open), 1 (close), 2 (do not move).'
        #self.comment("*ROMA Vector %s"%vector)
        if slow:
            speed=1
        else:
            speed=0
        if andBack:
            andBack=1
        else:
            andBack=0
        self.list.append('Vector("%s",%d,%d,%d,%d,%d,%d,%d,0)'%(vector,loc.grid,loc.pos,direction,andBack,initialAction, finalAction, speed))
        self.elapsed+=4.96
        
    def romahome(self):
        #self.comment("*ROMA Home")
        self.list.append('ROMA(2,0,0,0,0,0,60,0,0)')
        self.elapsed+=1.42

    def email(self,dest,subject,body='',profile='cdsrobot',onerror=0,attachscreen=1):
        self.list.append('Notification(%d,"%s","%s","%s","%s",%d)'%(attachscreen,profile,dest,subject,body,onerror))

    def condition(self,varname,cond,value,dest):
        'Conditional - jump to given label (comment) if (variable cond value) is true'
        if cond=='==':
            condval=0
        elif cond=='!=':
            condval=1
        elif cond=='>':
            condval=2
        elif cond=='<':
            condval=3
        else:
            print "Bad condition '%s' to condition()"%cond
            assert(0)
        self.list.append('If("%s",%d,"%s","%s")'%(varname,condval,value,dest))
                  
    def comment(self, text,prepend=False):
        if len(text) > 200:
            text=text[0:197]+"..."
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
        
    def variable(self,varname,default,userprompt=None,minval=None,maxval=None):
        if minval!=None or maxval!=None:
            limitrange=1
        else:
            limitrange=0
    
        if userprompt==None:
            self.list.append('Variable(%s,"%s",0," ",0,0.0,0.0)'%(varname,default))
        else:
            self.list.append('Variable(%s,"%s",1,"%s",%d,%f,%f)'%(varname,default,userprompt,limitrange,minval,maxval))
                         
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
        self.elapsed+=7.07   # Just overhead time, not actually time that command itself takes
        
    def pyrun(self, cmd):
        label='L%d'%self.lnum
        self.lnum=self.lnum+1
        self.execute("C:\Python27\python.exe C:\cygwin\Home\Admin\%s"%cmd,resultvar="ecode")
        self.condition("ecode","==","0",label)
        msg='Python command %s failed with ecode=~ecode~'%cmd
        self.email(dest='robot',subject=msg)
        self.userprompt(msg)
        self.comment(label)

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
        # Also save another copy with line numbers, indent in a readable form in filename.gemtxt
        fd=open(filename+'txt','w')
        for i in range(len(self.list)):
            s=str(self.list[i])
            if s.startswith('Comment'):
                s=s[9:-2]
                if s.startswith('*'):
                    s='    '+s[1:]
            else:
                s='        '+s
            print >>fd,"%s"%(s)
        fd.close()
        
