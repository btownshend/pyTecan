# Reagent - a set of samples that are allocated as they are needed
import sys
from Experiment.sample import Sample
import decklayout

all={}

class Reagent:
    def __init__(self,name,plate=decklayout.REAGENTPLATE,well=None,conc=None,hasBeads=False,extraVol=50):
        self.sample=None
        self.name=name
        self.plate=plate
        self.preferredWell=well
        self.conc=conc
        self.hasBeads=hasBeads
        self.extraVol=extraVol
        self.initVol=0
        
    def get(self):
        if self.sample==None:
            print "Creating sample for reagent %s with %.1f ul"%(self.name,self.initVol)
            self.sample=Sample(self.name,self.plate,self.preferredWell,self.conc,hasBeads=self.hasBeads,volume=self.initVol)
            wellname=self.sample.plate.wellname(self.sample.well)
            if self.preferredWell != None and self.preferredWell != wellname:
                print "WARNING: %s moved from preferred well %s to %s\n"%(self.name,self.preferredWell,wellname)
        return self.sample

    def reset(self):
        'Reset reagent: clear sample, adjust initial volume to make current volume equal to extraVol'
        if self.sample!=None:
            adj=self.extraVol-self.sample.volume
            if adj>0:
                print "Adjusting initVol of %s to %.1f"%(self.name,self.initVol+adj)
                self.initVol+=adj
            self.sample=None

def isReagent(name):
    return name in all

def get(name):
    return all[name].get()

def __getattr__(name):
    return get(name)

def add(name,plate=decklayout.REAGENTPLATE,well=None,conc=None,hasBeads=False,extraVol=50):
    if name in all:
        print "ERROR: Attempt to add duplicate reagent, ",name
        assert(False)
    all[name]=Reagent(name,plate,well,conc,hasBeads,extraVol)
    return all[name]

def reset():
    for r in all:
        all[r].reset()

def printprep(fd=sys.stdout):
    notes="Reagents to provide:"
    total=0
    for r in all.itervalues():
        s=r.sample
        if s==None:
            continue
        if s.conc!=None:
            c="[%s]"%str(s.conc)
        else:
            c=""   
        if s.volume==r.initVol:
            'Not used'
            #note="%s%s in %s.%s not consumed"%(s.name,c,str(s.plate),s.plate.wellname(s.well))
            #notes=notes+"\n"+note
        elif r.initVol>0:
            note="%s%s in %s.%s consume %.1f ul, provide %.1f ul"%(s.name,c,str(s.plate),s.plate.wellname(s.well),r.initVol-s.volume,r.initVol)
            notes=notes+"\n"+note
        if s.plate.name=="Reagents":
            total+=round((r.initVol-s.volume)*10)/10.0
        if r.initVol>s.plate.maxVolume:
            print "ERROR: Excess initial volume (",r.initVol,") for ",s,", maximum is ",s.plate.maxVolume

    print >>fd,notes
    print >>fd,"Total reagents volume = %.1f ul"%total


