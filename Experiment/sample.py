import sys
import liquidclass
from worklist import WorkList

defaultMixFrac = 0.9
defaultMixLeave = 3
MINLIQUIDDETECTVOLUME=50

_Sample__allsamples = []

class Sample(object):
    @staticmethod
    def printallsamples(txt="",fd=sys.stdout):
        print >>fd,"\n%s:"%txt
        for s in __allsamples:
            print >>fd,s
        print >>fd
    def __init__(self,name,plate,well,conc=None,volume=0,liquidClass=liquidclass.LCDefault):
        for s in __allsamples:
            if s.plate==plate and s.well==well:
                print "Aliasing %s as %s"%(s.name,name)
                assert(False)
                
        self.name=name
        self.plate=plate
        self.well=well
        self.conc=conc
        self.volume=volume
        self.initvolume=volume
        self.bottomLC=liquidclass.LC("%s-Bottom"%liquidClass.name,liquidClass.singletag,liquidClass.multicond,liquidClass.multiexcess)
        self.inliquidLC=liquidclass.LC("%s-InLiquid"%liquidClass.name,liquidClass.singletag,liquidClass.multicond,liquidClass.multiexcess)
        # Same as empty for now 
        self.emptyLC=liquidclass.LC("%s-Bottom"%liquidClass.name,liquidClass.singletag,liquidClass.multicond,liquidClass.multiexcess)
        self.history=""
        __allsamples.append(self)
        self.isMixed=volume==0

    def dilute(self,factor):
        'Dilute sample -- just increases its recorded concentration'
        if self.conc!=None:
            self.conc=self.conc*factor

    def aspirate(self,tipMask,w,volume):
        w.aspirate(tipMask,[self.well],self.chooseLC(True),volume,self.plate)
        self.volume=self.volume-volume
        if self.volume<0:
            print "Warning: %s is now short by %.1f ul"%(self.name,-self.volume)
            
    def dispense(self,tipMask,w,volume,conc):
        w.dispense(tipMask,[self.well],self.chooseLC(),volume,self.plate)

        # Assume we're diluting the contents
        if self.conc==None and conc==None:
            pass
        elif conc==None or volume==0:
            self.conc=(self.conc*self.volume)/(self.volume+volume)
        elif self.conc==None or self.volume==0:
            self.conc=(conc*volume)/(self.volume+volume)
        else:
            # Both have concentrations, they should match
            c1=(self.conc*self.volume)/(self.volume+volume)
            c2=(conc*volume)/(self.volume+volume)
            assert(abs(c1-c2)<.01)
            self.conc=c1
         # Set to not mixed after second ingredient added
        self.isMixed=self.volume==0
        self.volume=self.volume+volume

    def addhistory(self,name,vol):
        if len(self.history)>0:
            self.history=self.history+"+%s[%.1f]"%(name,vol)
        else:
            self.history="%s[%.1f]"%(name,vol)
        
    def chooseLC(self,isAspirate=False):
        if self.volume>MINLIQUIDDETECTVOLUME:
            return self.inliquidLC
        elif self.volume==0 and not isAspirate:
            return self.emptyLC
        else:
            return self.bottomLC
        
    def mix(self,tipMask,w,mixFrac=defaultMixFrac):
        if self.isMixed:
            print "Sample %s is already mixed"%self.name
            return
        mixvol=min(self.volume*mixFrac,self.volume-defaultMixLeave)
        if mixvol<2:
            print "Not enough volume in sample %s to mix"%self.name
        else:
            w.mix(tipMask,[self.well],self.chooseLC(),mixvol,self.plate,3)
            self.isMixed=True
            
    def __str__(self):
        if self.conc==None:
            return "%s(%s.%s,%.2f ul,LC=%s) %s"%(self.name,str(self.plate),str(self.well),self.volume,self.bottomLC.name,self.history)
        else:
            return "%s(%s.%s,%.2fx,%.2f ul,LC=%s) %s"%(self.name,str(self.plate),str(self.well),self.conc,self.volume,self.bottomLC.name,self.history)

    
    @staticmethod
    def printprep(fd=sys.stdout):
        notes="Reagents:"
        for s in __allsamples:
            if s.initvolume>0:
                if s.conc!=None:
                    c="@%.2fx"%s.conc
                else:
                    c=""   
                note="%s%s in %s.%s consume %.1f ul, provide %.1f ul"%(s.name,c,str(s.plate),str(s.well),s.initvolume-s.volume,s.initvolume)
                notes=notes+"\n"+note
        print >>fd,notes
