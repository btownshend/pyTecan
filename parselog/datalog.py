import sys
sys.path.append('/Users/bst/Dropbox/SynBio/robot/pyTecan/Experiment')
print "path=",sys.path
import sample
from sample import Sample
from plate import Plate
from experiment import Experiment
from liquidclass import SURFACEREMOVE

e=Experiment()		# This casuses all the plate definitions in Experiment to be loaded
sample.SHOWTIPS=True

def getSample(wellx,welly,rack,grid,pos):
        plate=Plate.lookup(grid,pos)
        if plate==None:
            plate=Plate(rack,grid,pos)
        wellname="%c%d"%(ord('A')+welly-1,wellx)
        well=plate.wellnumber(wellname)
        sample=Sample.lookupByWell(plate,well)
        if sample==None:
            sample=Sample("%s.%d.%d.%d"%(rack,grid,pos,well),plate,well)
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
                print "LogEntry: bad op (%s) for LC %s"%(op,lc)
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
            print "LogEntry: bad op: ",op
            assert(False)
        self.sample.volume+=self.sample.lastadd
             
    def __str__(self):
        return "%s tip %d, %.2ful, %s"%(self.op,self.tip,self.vol,self.lc)
            
class Datalog(object):
    'Log data about transfers, liquid height measures'

    def __init__(self):
        self.logentries={}
        self.lastSample={}
        
    def logop(self,op,tip,vol,wellx,welly,rack,grid,pos,lc,std,volset,isMulti):
        entry=LogEntry(op,tip,vol,wellx,welly,rack,grid,pos,lc,std,volset,isMulti)
        sname=entry.sample.name
        if sname in self.logentries:
            self.logentries[sname].append(entry)
        else:
            self.logentries[sname]=[entry]
        self.lastSample[tip]=entry.sample
        
    def logmeasure(self,tip,height,submerge,zmax,zadd):
        sample=self.lastSample[tip]
        if height==-1:
            vol=sample.plate.getliquidvolume((zadd+submerge)/10.0)
            h=" @[FAIL <%d:<%.1f#%d]"%(zadd+submerge,vol,tip)
        else:
            vol=sample.plate.getliquidvolume((height+submerge-zmax)/10.0)
            if vol==None:
                h=" @[%d,%d#%d]"%(height-zmax,submerge,tip)
            else:
                prevol=sample.volume-sample.lastadd		# Liquid height is measured before next op, whose volume effect has already been added to sample.volume
                if prevol==0:
                    print "Got a liquid height measurement for a well that should be empty -- assuming it was prefilled"
                    sample.volume=vol+sample.lastadd
                    prevol=vol
                expectHeight=sample.plate.getliquidheight(prevol)
                errorHeight=(height+submerge-zmax)-expectHeight*10
                if abs(errorHeight)>4.5:
                    emphasize='****'
                else:
                    emphasize=''
                h=" @[%d,%d:%.1f#%d]{%sE=%d;%.1f}"%(height-zmax,submerge,vol,tip,emphasize,errorHeight,vol-prevol)
        # Insert BEFORE last history entry since the liquid height is measured before aspirate/dispense
        hsplit=sample.history.split(' ')
        sample.history=" ".join(hsplit[:-1]+[h]+hsplit[-1:])

    def __str__(self):
        s=""
        print self.logentries
        for e in self.logentries:
            le=self.logentries[e]
            s=s+str(le[0].sample)+":""\n"
            for ee in self.logentries[e]:
                s=s+"  "+str(ee)+"\n"
        return s

    @staticmethod
    def printallsamples():
        Sample.printallsamples()
