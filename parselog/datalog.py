#sys.path.append(os.path.join(os.path.dirname(__file__),'../Experiment'))
#print("path=",sys.path)
from Experiment.decklayout import TIPOFFSETS
from Experiment.experiment import Experiment
from Experiment.liquidclass import SURFACEREMOVE
from Experiment.plate import Plate
from Experiment.sample import Sample
from Experiment import sample

e=Experiment()		# This casuses all the plate definitions in Experiment to be loaded
sample.SHOWTIPS=True

def getSample(wellx,welly,rack,grid,pos):
        plate=Plate.lookup(grid,pos)
        if plate is None:
            plate=Plate(rack,grid,pos)
        wellname="%c%d"%(ord('A')+welly-1,wellx)
        well=plate.wellnumber(wellname)
        sample=Sample.lookupByWell(plate,well)
        if sample is None:
            sample=Sample("%s.%d.%d.%d"%(rack,grid,pos,well),plate,well)
            if grid==3:
                sample.volume=20000   # Troughs
            else:
                sample.volume=0
        return sample
    
class LogEntry(object):
    def __init__(self,op,tip,vol,wellx,welly,rack,grid,pos,lc,std,volset,isMulti):
        self.op=op
        self.tip=tip
        self.vol=vol
        self.lc=lc
        self.std=std
        self.volset=volset
        self.isMulti=isMulti
        self.sample=getSample(wellx,welly,rack,grid,pos)
        if lc=='Air' or lc[0:7]=='Blowout' or lc=='Dip':
            if op=='dispense':
                self.sample.addhistory(lc,vol,tip)
            elif op=='aspirate':
                self.sample.addhistory(lc,-vol,tip)
            else:
                print("LogEntry: bad op (%s) for LC %s"%(op,lc))
                assert(False)
            self.sample.lastadd=0
        elif op=='dispense':
            self.sample.addhistory("",vol,tip)
            self.sample.lastadd=vol
        elif op=='detect':
            self.sample.addhistory("detect",0,tip)
            self.sample.lastadd=0
        elif op=='aspirate':
            self.sample.addhistory("",-vol,tip)
            self.sample.lastadd=-(vol+SURFACEREMOVE)	# Extra for tip wetting
        elif op[0:3]=='mix':
            self.sample.addhistory(op,vol,tip)
            self.sample.lastadd=0
        else:
            print("LogEntry: bad op: ",op)
            assert(False)
        if self.sample.volume+self.sample.lastadd<0 and self.sample.volume!=0:
            self.sample.history=self.sample.history + ("{Emptied%.2f}"%(self.sample.volume+self.sample.lastadd))
            self.sample.volume=0
        else:
            self.sample.volume+=self.sample.lastadd
            
    def __str__(self):
        return "%s tip %d, %.2ful, %s"%(self.op,self.tip,self.vol,self.lc)
            
class Datalog(object):
    """Log data about transfers, liquid height measures"""

    def __init__(self):
        self.logentries={}
        self.lastSample={}
        
    def logop(self,op,tip,vol,wellx,welly,rack,grid,pos,lc,std,volset,isMulti):
        if grid==18 and pos==2:   # Make magplate refer to samples
            grid=4
            pos=3
            
        entry=LogEntry(op,tip,vol,wellx,welly,rack,grid,pos,lc,std,volset,isMulti)
        sname=entry.sample.name
        if sname in self.logentries:
            self.logentries[sname].append(entry)
        else:
            self.logentries[sname]=[entry]
        self.lastSample[tip]=entry.sample
        
    def logmeasure(self,tip,height,submerge,zmax,zadd,time):
        # Time is the time in seconds of this measurement
        sample=self.lastSample[tip]
        if len(sample.extrainfo)>0:
            elapsed=time-sample.extrainfo[0]
        else:
            elapsed=0

        #print "%s: %f"%(sample.name,elapsed)
        sample.extrainfo=[time]    # Keep track of last measurement time of this sample in the extrainfo list
        if sample.plate.location.zmax is not None:
            curzmax=2100-sample.plate.location.zmax-390+TIPOFFSETS[tip-1]
            if zmax!=curzmax:
                print("ZMax for plate %s, tip %d at time of run was %.0f, currently at %.0f"%(sample.plate.name, tip, zmax, curzmax))
                zmax=curzmax
        prevol=sample.volume-sample.lastadd		# Liquid height is measured before next op, whose volume effect has already been added to sample.volume
        if height==-1:
            vol=sample.plate.getliquidvolume((zadd+submerge)/10.0)
            if vol is not None:
                if prevol<vol and prevol!=0:
                    # The liquid measure failed, but based on the previous volume estimate, it was guaranteed to fail since the submerge depth would've been below bottom
                    # But if we don't know the volume (ie a prefilled tube -> prevol=0), then log this as a fail
                    h=" @[DEEP <%.1fmm:<%.1ful#%d]"%((zadd+submerge)/10.0,vol,tip)
                    #h=""
                else:
                    h=" @[FAIL <%.1fmm:<%.1ful#%d]"%((zadd+submerge)/10,vol,tip)
            else:
                h=" @[FAIL <%.1f#%d]"%((zadd+submerge)/10.0,tip)
        else:
            vol=sample.plate.getliquidvolume((height+submerge-zmax)/10.0)
            if vol is None:
                h=" @[%.1fmm,%.1fmm#%d]"%((height-zmax)/10.0,submerge/10.0,tip)
            else:
                if prevol==0:
                    print("Got a liquid height measurement for a well that should be empty -- assuming it was prefilled")
                    sample.volume=vol+sample.lastadd
                    prevol=vol
                expectHeight=sample.plate.getliquidheight(prevol)
                errorHeight=(height+submerge-zmax)-expectHeight*10
                h=" @[%.1fmm,%.1fmm:%.1ful#%d]"%((height-zmax)/10.0,submerge/10.0,vol,tip)
                if abs(errorHeight)>1:
                    if abs(errorHeight)>4:
                        emphasize="*"*(min(10,int(abs(errorHeight))-3))
                    else:
                        emphasize=''
                    h=h+"{%sE=%d;%.1ful}"%(emphasize,errorHeight,vol-prevol)
                sample.volume=sample.volume+(vol-prevol)
        # Insert BEFORE last history entry since the liquid height is measured before aspirate/dispense
        hsplit=sample.history.split(' ')
        if elapsed>=600:   # Log elapsed time if more than 10 min
            sample.history=" ".join(hsplit[:-1]+["(T%.0f)"%(elapsed/60)]+[h]+hsplit[-1:])
        else:
            sample.history=" ".join(hsplit[:-1]+[h]+hsplit[-1:])

    def logspeed(self,platename,speed):
        print("logspeed(%s,%d)"%(platename,speed))
        Sample.addallhistory("(S@%d)"%speed,onlyplate=platename)
            
    def __str__(self):
        s=""
        print(self.logentries)
        for e in self.logentries:
            le=self.logentries[e]
            s=s+str(le[0].sample)+":""\n"
            for ee in self.logentries[e]:
                s=s+"  "+str(ee)+"\n"
        return s

    @staticmethod
    def printallsamples():
        Sample.printallsamples()
