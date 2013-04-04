from worklist import *

allsamples=[]
defaultLC="Water-BT"   # Default liquid class
defaultMixFrac = 0.9

class Sample(object):
    @staticmethod
    def printallsamples(txt=""):
        print "\n%s:"%txt
        for s in allsamples:
            print s
        print ""

    def __init__(self,name,plate,well,conc=None,volume=0,liquidClass=defaultLC):
        for s in allsamples:
            if s.plate==plate and s.well==well:
                print "Aliasing %s as %s"%(s.name,name)
                assert(False)
                
        self.name=name
        self.plate=plate
        self.well=well
        self.conc=conc
        self.volume=volume
        self.liquidClass=liquidClass
        self.history=""
        allsamples.append(self)
        
    def dilute(self,factor):
        'Dilute sample -- just increases its recorded concentration'
        self.conc=self.conc*factor

    def aspirate(self,w,volume):
        w.aspirate([self.well],self.liquidClass,volume,self.plate)
        self.volume=self.volume-volume
        if self.volume<0:
            print "Warning: %s is now short by %.1f ul"%(self.name,-self.volume)
            
    def dispense(self,w,volume,conc):
        w.dispense([self.well],self.liquidClass,volume,self.plate)
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
            assert(c1==c2)
            self.conc=c1
        self.volume=self.volume+volume

    def addhistory(self,name,vol):
        if len(self.history)>0:
            self.history=self.history+",%s[%.1f]"%(name,vol)
        else:
            self.history="%s[%.1f]"%(name,vol)
        
    def mix(self,w,mixFrac=defaultMixFrac):
        w.mix([self.well],self.liquidClass,self.volume*mixFrac,self.plate,3)

    def __str__(self):
        if self.conc==None:
            return "%s(%s.%s,%.2f ul,LC=%s) %s"%(self.name,str(self.plate),str(self.well),self.volume,self.liquidClass,self.history)
        else:
            return "%s(%s.%s,%.2fx,%.2f ul,LC=%s) %s"%(self.name,str(self.plate),str(self.well),self.conc,self.volume,self.liquidClass,self.history)

    
