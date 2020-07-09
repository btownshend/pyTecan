#sys.path.append(os.path.join(os.path.dirname(__file__),'../Experiment'))
#print("path=",sys.path)
from datetime import timedelta

from Experiment.decklayout import TIPOFFSETS
from Experiment.experiment import Experiment
from Experiment.liquidclass import SURFACEREMOVE
from Experiment.plate import Plate
from Experiment.platetype import PlateType
from Experiment.sample import Sample
from Experiment import sample
from Experiment import logging

def getSample(wellx,welly,rack,grid,pos):
        plate=Plate.lookup(grid,pos)
        if plate is None:
            plate = Plate(rack, grid, pos)
        elif plate.plateType.name != rack:
            print(f"Expected plate type {plate.plateType.name} at {grid},{pos}, but found {rack} - overriding")
            plate.plateType = PlateType.lookupByName(rack)
            if plate.plateType is None:
                print("No such plateType: ", rack)
                assert False

        wellname="%c%d"%(ord('A')+welly-1,wellx)
        well=plate.wellnumber(wellname)
        s=Sample.lookupByWell(plate, well)
        if s is None:
            s=Sample("%s.%d.%d.%d" % (rack, grid, pos, well), plate, well)
            if grid==3:
                s.volume=20000   # Troughs
            else:
                s.volume=0
        return s
    
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
                logging.notice("LogEntry: bad op (%s) for LC %s"%(op,lc))
                assert False
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
            logging.warning("LogEntry: bad op: %s"%op)
            assert False
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
        self.ex = Experiment()  # This casuses all the plate definitions in Experiment to be loaded
        sample.SHOWTIPS = True
        
    def logop(self,op,tip,vol,wellx,welly,rack,grid,pos,lc,std,volset,isMulti):
        # if grid==18 and pos==2:   # Make magplate refer to samples
        #     grid=4
        #     pos=3
            
        entry=LogEntry(op,tip,vol,wellx,welly,rack,grid,pos,lc,std,volset,isMulti)
        sname=entry.sample.name
        if sname in self.logentries:
            self.logentries[sname].append(entry)
        else:
            self.logentries[sname]=[entry]
        self.lastSample[tip]=entry.sample
        
    def logmeasure(self,tip,height,submerge,zmax,zadd,time):
        # Time is the time in seconds of this measurement
        lsamp=self.lastSample[tip]
        if len(lsamp.extrainfo)>0:
            elapsed=time-lsamp.extrainfo[0]
        else:
            elapsed=timedelta(0)

        #print "%s: %f"%(sample.name,elapsed)
        lsamp.extrainfo=[time]    # Keep track of last measurement time of this sample in the extrainfo list
        curzmax=2100-lsamp.plate.getzmax()-390+TIPOFFSETS[tip-1]
        if zmax!=curzmax:
            logging.warning("ZMax for plate %s, tip %d at time of run was %.0f, currently at %.0f"%(lsamp.plate.name, tip, zmax, curzmax))
            zmax=curzmax
        prevol=lsamp.volume-lsamp.lastadd		# Liquid height is measured before next op, whose volume effect has already been added to sample.volume
        if height==-1:
            vol=lsamp.plate.getliquidvolume((zadd+submerge)/10.0)
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
            vol=lsamp.plate.getliquidvolume((height+submerge-zmax)/10.0)
            if vol is None:
                h=" @[%.1fmm,%.1fmm#%d]"%((height-zmax)/10.0,submerge/10.0,tip)
            else:
                if prevol==0:
                    logging.notice("Got a liquid height measurement for a well that should be empty -- assuming it was prefilled")
                    lsamp.volume=vol+lsamp.lastadd
                    prevol=vol
                expectHeight=lsamp.plate.getliquidheight(prevol)
                errorHeight=(height+submerge-zmax)-expectHeight*10
                h=" @[%.1fmm,%.1fmm:%.1ful#%d]"%((height-zmax)/10.0,submerge/10.0,vol,tip)
                if abs(errorHeight)>1:
                    if abs(errorHeight)>4:
                        emphasize="*"*(min(10,int(abs(errorHeight))-3))
                    else:
                        emphasize=''
                    h=h+"{%sE=%d;%.1ful}"%(emphasize,errorHeight,vol-prevol)
                lsamp.volume=lsamp.volume+(vol-prevol)
        # Insert BEFORE last history entry since the liquid height is measured before aspirate/dispense
        hsplit=lsamp.history.split(' ')
        if elapsed.total_seconds()>=600:   # Log elapsed time if more than 10 min
            lsamp.history=" ".join(hsplit[:-1]+["(T%.0f)"%(elapsed.total_seconds()/60)]+[h]+hsplit[-1:])
        else:
            lsamp.history=" ".join(hsplit[:-1]+[h]+hsplit[-1:])

    @staticmethod
    def logspeed(platename, speed):
        logging.notice("logspeed(%s,%d)"%(platename,speed))
        Sample.addallhistory("(S@%d)"%speed,onlyplate=platename)
            
    def __str__(self):
        s=""
        logging.notice(str(self.logentries))
        for e in self.logentries:
            le=self.logentries[e]
            s=s+str(le[0].sample)+":""\n"
            for ee in self.logentries[e]:
                s=s+"  "+str(ee)+"\n"
        return s

    @staticmethod
    def printallsamples(fd):
        Sample.printallsamples(fd=fd)
