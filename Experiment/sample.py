import sys
import liquidclass
from worklist import WorkList
from concentration import Concentration

defaultMixFrac = 0.8
defaultMixLeave = 3
ASPIRATEFACTOR=1.1
MINLIQUIDDETECTVOLUME=50
MULTIEXCESS=1  # Excess volume aspirate when using multi-dispense
_Sample__allsamples = []

#Updated LC's:
# Water-Bottom
# Fixed Aspirate (single): 20ul/s, 200ms, STAG=20,LAG=1 (WAS 0),TAG=0,EXC=0,COND=0, zmax-1mm (WAS -0.2mm), retract to z-dispense  20mm/s
# Fixed Aspirate (multi): 20ul/s, 200ms, STAG=20,LAG=0,TAG=0,EXC=2 (to waste),COND=0 (WAS 2ul)
# Fixed Dispense (single): 100ul/s, 100ul/s, 500ms, no TAG after each dispense, no LD, z-max -1mm (WAS -2mm), touch left @10mm/s;100ms (WAS no touch), retract to z-dispense 20 mm/s
# Fixed Dispense (multi): 100ul/s (WAS 600), 100ul/s(WAS 400), 500ms(WAS 0), no TAG after each dispense
# Water-InLiquid
# Fixed Aspirate (single): 20ul/s, 200ms, STAG=20,LAG=1 (WAS 0),TAG=0,EXC=0,COND=0, liquid detect +1mm center with tracking, retract to liquid level-5mm  20mm/s
# Fixed Aspirate (multi): 20ul/s, 200ms, STAG=20,LAG=0,TAG=0,EXC=2 (to waste),COND=0 (WAS 2ul)
# Fixed Dispense (single): 100ul/s, 100ul/s, 500ms, no TAG after each dispense, no LD, liquid detect +1mm center with tracking, retract to liquid level-5mm (WAS -2) 20 mm/s
# Fixed Dispense (multi): 100ul/s (WAS 600), 100ul/s(WAS 400), 500ms(WAS 0), no TAG after each dispense
# Water-Mix
# Fixed Aspirate (single): 100ul/s, 200ms, STAG=20,LAG=0,TAG=0,EXC=0,COND=0,zmax-1mm, retract to z-dispense  20mm/s
# Fixed Aspirate (multi): 20ul/s, 200ms, STAG=20,LAG=0,TAG=0,EXC=2 (to waste),COND=0
# Fixed Dispense (single): 100ul/s, 100ul/s, 500ms, no TAG after each dispense, no LD, z-max -5mm, no touch, retract to current-pos 20 mm/s
# Fixed Dispense (multi): 100ul/s (WAS 600), 100ul/s(WAS 400), 500ms(WAS 0), no TAG after each dispense

class Sample(object):
    @staticmethod
    def printallsamples(txt="",fd=sys.stdout):
        print >>fd,"\n%s:"%txt
        for s in __allsamples:
            print >>fd,s
        print >>fd
    def __init__(self,name,plate,well=None,conc=None,volume=0,liquidClass=liquidclass.LCDefault):
        if well==None:
            # Find first unused well
            well=0
            for s in __allsamples:
                if s.plate==plate and s.well>=well:
                    well=s.well+1
                    
        for s in __allsamples:
            if s.plate==plate and s.well==well:
                print "Aliasing %s as %s"%(s.name,name)
                assert(False)
	    if s.name==name:
		print "Already have a sample called %s"%name
                assert(False)
        self.name=name
        self.plate=plate
	if well>=plate.nx*plate.ny:
		print "Overflow of plate %s"%str(plate)
		assert(False)
		
        self.well=well
	if isinstance(conc,Concentration) or conc==None:
		self.conc=conc
	else:
		self.conc=Concentration(conc)
        self.volume=volume
        self.initvolume=volume
        if plate.pierce:
            self.bottomLC=liquidclass.LC("%s-Pierce"%liquidClass.name,liquidClass.singletag,liquidClass.multicond,liquidClass.multiexcess)
        else:
            self.bottomLC=liquidclass.LC("%s-Bottom"%liquidClass.name,liquidClass.singletag,liquidClass.multicond,liquidClass.multiexcess)
            self.inliquidLC=liquidclass.LC("%s-InLiquid"%liquidClass.name,liquidClass.singletag,liquidClass.multicond,liquidClass.multiexcess)

        self.mixLC=liquidclass.LC("%s-Mix"%liquidClass.name,liquidClass.singletag,liquidClass.multicond,liquidClass.multiexcess)
        # Same as empty for now 
        self.emptyLC=liquidclass.LC("%s-Bottom"%liquidClass.name,liquidClass.singletag,liquidClass.multicond,liquidClass.multiexcess)
        self.history=""
        __allsamples.append(self)
        self.isMixed=True

    @classmethod
    def clearall(cls):
        'Clear all samples'
        for s in __allsamples:
            s.volume=s.initvolume
            s.history=""
            s.isMixed=True
            if s.volume==0:
                s.conc=None

    @classmethod
    def lookup(cls,name):
        for s in __allsamples:
	    if s.name==name:
                return s
        return None
                
    def dilute(self,factor):
        'Dilute sample -- just increases its recorded concentration'
        if self.conc!=None:
		self.conc=self.conc.dilute(1.0/factor)

    def aspirate(self,tipMask,w,volume,multi=False):
        if volume<2 and not multi:
            print "WARNING: Inaccurate for < 2ul:  attempting to aspirate %.1f ul"%volume
        if volume<6:
            aspVolume=volume+1
        else:
            # Aspirates more than dispensed
            aspVolume=volume*ASPIRATEFACTOR
            
	if self.well==None:
		well=[]
		for i in range(4):
			if (tipMask & (1<<i)) != 0:
			    well.append(i)
	else:
		well=[self.well]
	
	lc=self.chooseLC(aspVolume)
        w.aspirate(tipMask,well,lc,volume,self.plate)
        # Manual conditioning handled in worklist
        self.volume=self.volume-aspVolume
        if multi:
            self.volume=self.volume-MULTIEXCESS
            self.addhistory("",-volume-MULTIEXCESS,tipMask)
        else:
            self.addhistory("",-volume,tipMask)
        if self.volume<0:
            print "Warning: %s is now short by %.1f ul"%(self.name,-self.volume)
            
    def dispense(self,tipMask,w,volume,conc):
        well=[self.well if self.well!=None else 2**(tipMask-1)-1 ]
        w.dispense(tipMask,well,self.chooseLC(),volume,self.plate)

        # Assume we're diluting the contents
        if self.conc==None and conc==None:
            pass
        elif conc==None or volume==0:
            self.conc=self.conc.dilute((self.volume+volume)/self.volume)
        elif self.conc==None or self.volume==0:
            self.conc=conc.dilute((self.volume+volume)/volume)
        else:
            # Both have concentrations, they should match
            c1=self.conc.dilute((self.volume+volume)/self.volume)
            c2=conc.dilute((self.volume+volume)/volume)
            assert(abs(c1.stock/c1.final-c2.stock/c2.final)<.01)
            self.conc=Concentration(c1.stock/c1.final,1.0,'x')  # Since there are multiple ingredients express concentration as x
         # Set to not mixed after second ingredient added
        self.isMixed=self.volume==0
        self.volume=self.volume+volume

    def addhistory(self,name,vol,tip):
        if vol>0:
            str="%s[%.1f#%d]"%(name,vol,tip)
            if len(self.history)>0:
                self.history=self.history+"+"+str
            else:
                self.history=str
        elif vol<0:
            str="-%.1f"%(-vol)
            if len(self.history)>0:
                self.history=self.history+str
            else:
                self.history=str
        
    def chooseLC(self,aspirateVolume=0):
        if self.volume-aspirateVolume>MINLIQUIDDETECTVOLUME:
            return self.inliquidLC
        elif self.volume==0 and aspirateVolume==0:
            return self.emptyLC
        else:
            return self.bottomLC
        
    def mix(self,tipMask,w,mixFrac=defaultMixFrac):
        if self.isMixed:
            print "Sample %s is already mixed"%self.name
            return
        mixvol=min(self.volume*mixFrac,self.volume-defaultMixLeave)
        well=[self.well if self.well!=None else 2**(tipMask-1)-1 ]
        if mixvol<2:
            print "Not enough volume in sample %s to mix"%self.name
	elif True:  # mixvol<20:
            w.mix(tipMask,well,self.chooseLC(mixvol),mixvol,self.plate,3)
            self.history+="(MB)"
            self.isMixed=True
        else:
            # Use special mix LC which aspirates from bottom, dispenses above, faster aspirate
            well=[self.well if self.well!=None else 2**(tipMask-1)-1 ]
            for i in range(3):
                w.aspirate(tipMask,well,self.mixLC,mixvol,self.plate)
                w.dispense(tipMask,well,self.mixLC,mixvol,self.plate)
            self.history+="(MT)"
            self.isMixed=True
            
    def __str__(self):
        if self.conc==None:
            return "%s(%s.%s,%.2f ul) %s"%(self.name,str(self.plate),self.plate.wellname(self.well),self.volume,self.history)
        else:
            return "%s[%s](%s.%s,%.2f ul) %s"%(self.name,str(self.conc),str(self.plate),self.plate.wellname(self.well),self.volume,self.history)

    
    @staticmethod
    def printprep(fd=sys.stdout):
        notes="Reagents:"
        for s in __allsamples:
            if s.conc!=None:
                c="[%s]"%str(s.conc)
            else:
                c=""   
	    if s.volume==s.initvolume:
		'Not used'
                note="%s%s in %s.%s not consumed"%(s.name,c,str(s.plate),s.plate.wellname(s.well))
                notes=notes+"\n"+note
            elif s.initvolume>0:
                note="%s%s in %s.%s consume %.1f ul, provide %.1f ul"%(s.name,c,str(s.plate),s.plate.wellname(s.well),s.initvolume-s.volume,s.initvolume)
                notes=notes+"\n"+note
        print >>fd,notes
