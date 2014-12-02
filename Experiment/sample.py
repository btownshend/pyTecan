import sys
import liquidclass
from worklist import WorkList
from concentration import Concentration

ASPIRATEFACTOR=1.02
ASPIRATEEXTRA=1.0
#MINLIQUIDDETECTVOLUME=70
MINLIQUIDDETECTVOLUME=1000  # Liquid detect may be broken
#MINMIXTOPVOLUME=50   # Use manual mix if trying to mix more than this volume  (aspirates at ZMax-1.5mm, dispenses at ZMax-5mm)
MINMIXTOPVOLUME=1e10   # Disabled manual mix -- may be causing bubbles
MULTIEXCESS=1  # Excess volume aspirate when using multi-dispense
SHOWTIPS=False
SHOWINGREDIENTS=False
_Sample__allsamples = []
tiphistory={}

#Updated LC's:
# Water-Bottom
# Fixed Aspirate (single): 20ul/s, 200ms, STAG=20,LAG=1 (WAS 0),TAG=0,EXC=0,COND=0, zmax-1.5mm , retract to z-start  20mm/s
# Fixed Aspirate (multi): 20ul/s, 200ms, STAG=20,LAG=0,TAG=0,EXC=1 (to waste),COND=0
# Fixed Dispense (single): 100ul/s, 100ul/s, 500ms, no TAG after each dispense, no LD, z-max -1.5mm, touch left @10mm/s;100ms (WAS no touch), retract to z-dispense 20 mm/s
# Fixed Dispense (multi): 100ul/s, 100ul/s, 500ms), no TAG after each dispense
#
# Water-InLiquid
# Detect simultaneously and twice with all tips, cond good, det 60mm/s, double 4mm/s
# Fixed Aspirate (single): 20ul/s, 200ms, STAG=20,LAG=1,TAG=0,EXC=0,COND=0, liquid detect +3.5mm center with tracking, retract to liquid level-5mm  20mm/s
# Fixed Aspirate (multi): 20ul/s, 200ms, STAG=20,LAG=0,TAG=0,EXC=2 (to waste),COND=0 
# Fixed Dispense (single): 100ul/s, 100ul/s, 500ms, no TAG after each dispense, no LD, liquid detect +1mm center with tracking, retract to liquid level-5mm  20 mm/s
# Fixed Dispense (multi): 100ul/s, 100ul/s, 500ms(WAS 0), no TAG after each dispense
# Water-Mix
# Fixed Aspirate (single): 100ul/s, 200ms, STAG=20,LAG=0,TAG=0,EXC=0,COND=0,zmax-1.5mm, retract to z-dispense  20mm/s
# Fixed Aspirate (multi): 20ul/s, 200ms, STAG=20,LAG=0,TAG=0,EXC=1 (to waste),COND=0
# Fixed Dispense (single): 225ul/s, 225ul/s, 500ms, no TAG after each dispense, no LD, z-max -5mm, no touch, retract to z=dispense 20 mm/s
# Fixed Dispense (multi): 225ul/s, 225ul/s, 500ms, no TAG after each dispense

#Water-BottomSide 
# Same as water-Bottom, but dispense with tip at right side
# Fixed Aspirate (single): 20ul/s, 200ms, STAG=20,LAG=1 (WAS 0),TAG=0,EXC=0,COND=0, zmax-1.5mm , retract to z-start  20mm/s
# Fixed Aspirate (multi): 20ul/s, 200ms, STAG=20,LAG=0,TAG=0,EXC=1 (to waste),COND=0
# Fixed Dispense (single): 100ul/s, 100ul/s, 500ms, no TAG after each dispense, no LD, z-max -1.5mm (right side), touch left @10mm/s;100ms (WAS no touch), retract to z-dispense 20 mm/s
# Fixed Dispense (multi): 100ul/s, 100ul/s, 500ms), no TAG after each dispense
# Sometimes gives small bubbles on right side usually near surface, usually tip 2

#Water-MixSlow
# Same as water-Bottom, but single 20ul/s,20ul dispense (for mixing without bubbles)
#   Seems that faster dispense creates bubbles, unsure why
# Fixed Aspirate (single): 20ul/s, 200ms, STAG=20,LAG=1 (WAS 0),TAG=0,EXC=0,COND=0, zmax-1.5mm , retract to z-start  20mm/s
# Fixed Aspirate (multi): 20ul/s, 200ms, STAG=20,LAG=0,TAG=0,EXC=1 (to waste),COND=0
# Fixed Dispense (single): 20ul/s, 20ul/s, 500ms, no TAG after each dispense, no LD, z-max -1.5mm, touch left @10mm/s;100ms (WAS no touch), retract to z-dispense 20 mm/s
# Fixed Dispense (multi): 100ul/s, 100ul/s, 500ms), no TAG after each dispense
#

class Sample(object):
    @staticmethod
    def printallsamples(txt="",fd=sys.stdout,w=None):
        print >>fd,"\n%s by plate:"%txt
        plates=set([s.plate for s in __allsamples]);
        for p in sorted(plates, key=lambda p:p.name.upper()):
            print >>fd,"Samples in plate: ",p
            for s in __allsamples:
                if s.plate==p:
                    if w!=None:
                        print >>fd,s,("%06x"%(w.getHashCode(grid=s.plate.grid,pos=s.plate.pos,well=s.well)&0xffffff))
                    else:
                        print >>fd,s
            print >>fd
        if SHOWTIPS:
            print >>fd,"\nTip history:\n"
            for t in tiphistory:
                print >>fd,"%d: %s\n"%(t,tiphistory[t])
            
    def __init__(self,name,plate,well=None,conc=None,volume=0,liquidClass=liquidclass.LCDefault):
        if well==None:
            # Find first unused well
            well=0
            for s in __allsamples:
                if s.plate==plate and s.well>=well:
                    well=s.well+1
        elif well==-1:
            well=None
                    
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
        if volume>0:
            self.ingredients={name:volume}
        else:
            self.ingredients={}
            
        if plate.pierce:
            self.bottomLC=liquidclass.LC("%s-Pierce"%liquidClass.name,liquidClass.singletag,liquidClass.multicond,liquidClass.multiexcess)
            self.bottomSideLC=bottomLC
            self.inliquidLC=self.bottomLC  # Can't use liquid detection when piercing
        else:
            self.bottomLC=liquidclass.LC("%s-Bottom"%liquidClass.name,liquidClass.singletag,liquidClass.multicond,liquidClass.multiexcess)
            self.bottomSideLC=liquidclass.LC("%s-BottomSide"%liquidClass.name,liquidClass.singletag,liquidClass.multicond,liquidClass.multiexcess)
            self.inliquidLC=liquidclass.LC("%s-InLiquid"%liquidClass.name,liquidClass.singletag,liquidClass.multicond,liquidClass.multiexcess)

        self.mixLC=liquidclass.LC("%s-MixSlow"%liquidClass.name,liquidClass.singletag,liquidClass.multicond,liquidClass.multiexcess)
        self.airLC=liquidclass.LC("Air")
        # Same as bottom for now 
        self.emptyLC=self.bottomLC
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
                s.ingredients={}
            else:
                s.ingredients={s.name:s.volume}

    @classmethod
    def lookup(cls,name):
        for s in __allsamples:
            if s.name==name:
                return s
        return None
    
    @classmethod
    def getAllOnPlate(cls,plate=None):  
        result=[]
        for s in __allsamples:
            if plate==None or s.plate==plate:
                result.append(s)  
        return result 
                 
    @classmethod
    def getAllLocOnPlate(cls,plate=None):  
        result=""
        for s in __allsamples:
            if (plate==None or s.plate==plate) and s.volume!=s.initvolume:
                result+=" %s"%(s.plate.wellname(s.well))
        return result 

    def dilute(self,factor):
        'Dilute sample -- just increases its recorded concentration'
        if self.conc!=None:
                self.conc=self.conc.dilute(1.0/factor)

    def aspirate(self,tipMask,w,volume,multi=False):
        if volume<2 and not multi and self.name!="Water":
            print "WARNING: Inaccurate for < 2ul:  attempting to aspirate %.1f ul"%volume
        
        # Aspirates more than dispensed
        aspVolume=volume+ASPIRATEEXTRA
        if self.well==None:
                well=[]
                for i in range(4):
                        if (tipMask & (1<<i)) != 0:
                            well.append(i)
        else:
                well=[self.well]
        
        lc=self.chooseLC(aspVolume)
        w.aspirate(tipMask,well,lc,aspVolume,self.plate)
        # Manual conditioning handled in worklist
        remove=aspVolume*ASPIRATEFACTOR+MULTIEXCESS
        for k in self.ingredients:
            self.ingredients[k] *= (self.volume-remove)/self.volume
        self.volume=self.volume-remove
        if self.volume+.001<self.plate.unusableVolume and self.volume>0:
            # TODO - this hould be more visible in output
            print "Warning: Aspiration of %.1ful from %s brings volume down to %.1ful which is less than its unusable volume of %.1f ul"%(aspVolume,self.name,self.volume,self.plate.unusableVolume)
        self.addhistory("",-remove,tipMask)

    def aspirateAir(self,tipMask,w,volume):
        'Aspirate air over a well'
        w.aspirateNC(tipMask,[self.well],self.airLC,volume,self.plate)
        
    def dispense(self,tipMask,w,volume,conc):
        well=[self.well if self.well!=None else 2**(tipMask-1)-1 ]
        w.dispense(tipMask,well,self.bottomSideLC,volume,self.plate)

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
            if SHOWTIPS:
                    str="%s[%.1f#%d]"%(name,vol,tip)
            else:
                    str="%s[%.1f]"%(name,vol)
            if len(self.history)>0:
                self.history=self.history+" +"+str
            else:
                self.history=str
        elif vol<0:
            str=" -%.1f"%(-vol)
            if len(self.history)>0:
                self.history=self.history+str
            else:
                self.history=str
        name=self.name
        if name=="RNase-Away":
            if tip in tiphistory and tiphistory[tip][-1]=='\n':
                tiphistory[tip]=tiphistory[tip][:-1]
            fstr="*\n"
        elif vol==0:
            fstr=name
        else:
            fstr="%s[%d]"%(name,vol)
        if tip in tiphistory:
            tiphistory[tip]+=" %s"%fstr
        else:
            tiphistory[tip]=fstr

    @staticmethod
    def addallhistory(msg,addToEmpty=False):
        'Add history entry to all samples (such as # during thermocycling)'
        for s in __allsamples:
            if len(s.history)>0:
                s.history+=" "+msg
            elif addToEmpty:
                s.history=msg
                
    def addingredients(self,src,vol):
        'Update ingredients by adding ingredients from src'
        for k in src.ingredients:
            addition=src.ingredients[k]/src.volume*vol
            if k in self.ingredients:
                self.ingredients[k]+=addition
            else:
                self.ingredients[k]=addition
            
    def chooseLC(self,aspirateVolume=0):
        if self.volume-aspirateVolume>=MINLIQUIDDETECTVOLUME:
            return self.inliquidLC
        elif self.volume==0 and aspirateVolume==0:
            return self.emptyLC
        else:
            return self.bottomLC
        
        # Mix, return true if actually did a mix, false otherwise
    def mix(self,tipMask,w,preaspirateAir=False):
        nmix=4
        if self.isMixed:
            #print "Sample %s is already mixed"%self.name
            return False
        mixvol=self.volume-self.plate.unusableVolume;
        well=[self.well if self.well!=None else 2**(tipMask-1)-1 ]
        if mixvol<2:
            #print "Not enough volume in sample %s to mix"%self.name
            self.history+="(UNMIXED)"
            return False
        else:
            if preaspirateAir:
                # Aspirate some air to avoid mixing with excess volume aspirated into pipette from source in previous transfer
                self.aspirateAir(tipMask,w,5)
            if self.volume-mixvol>=MINLIQUIDDETECTVOLUME:
                w.mix(tipMask,well,self.inliquidLC,mixvol,self.plate,nmix)
                self.history+="(MLD)"
            else:
                w.mix(tipMask,well,self.mixLC,mixvol,self.plate,nmix)
                self.history+="(MB)"

            tiphistory[tipMask]+=" %s-Mix[%d]"%(self.name,mixvol)
            self.isMixed=True
            return True
            
    def __str__(self):
        s="%-32s "%(self.name)
        if self.conc!=None:
            s+=" %-18s"%("[%s]"%str(self.conc))
        else:
            s+=" %-18s"%""
        s+=" %-30s"%("(%s.%s,%.2f ul)"%(str(self.plate),self.plate.wellname(self.well),self.volume))
        s+=" %s"%self.history
        if SHOWINGREDIENTS:
                s+=self.ingredientstr()
        return s

    def ingredientstr(self):
        s="{"
        for k in self.ingredients:
            s+="%s:%.4g "%(k,self.ingredients[k])
        s+="}"
        return s

    @staticmethod
    def printprep(fd=sys.stdout):
        notes="Reagents:"
        total=0
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
            if s.plate.name=="Reagents":
                total+=round((s.initvolume-s.volume)*10)/10.0
        print >>fd,notes
        print >>fd,"Total reagents volume = %.1f ul"%total

    @staticmethod
    def savematlab(filename):
        fd=open(filename,"w")
        print >>fd,"samps=[];"
        for s in __allsamples:
            ing=""
            ingvol=""
            for k in s.ingredients:
                if len(ing)==0:
                    ing="'%s'"%k
                    ingvol="%g"%s.ingredients[k]
                else:
                    ing=ing+",'%s'"%k
                    ingvol=ingvol+",%g"%s.ingredients[k]
            
            print >>fd,"samps=[samps,struct('name','%s','plate','%s','well','%s','concentration','%s','history','%s','ingredients',{{%s}},'volumes',[%s])];"%(s.name,s.plate,s.plate.wellname(s.well),str(s.conc),s.history,ing,ingvol)
        fd.close()
