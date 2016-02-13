# Reagent - a set of samples that are allocated as they are needed
#  Always stored in REAGENTPLATE
from Experiment.sample import Sample
from experiment import Experiment

all={}

class Reagent:
    def __init__(self,name,plate=Experiment.REAGENTPLATE,well=None,conc=None,hasBeads=False,extraVol=50):
        self.sample=None
        self.name=name
        self.plate=plate
        self.preferredWell=well
        self.conc=conc
        self.hasBeads=hasBeads
        self.extraVol=extraVol

    def get(self):
        if self.sample==None:
            self.sample=Sample.lookup(self.name)
            if self.sample==None:
                print "Creating sample ",self.name
                self.sample=Sample(self.name,self.plate,self.preferredWell,self.conc,hasBeads=self.hasBeads,extraVol=self.extraVol)
                wellname=self.sample.plate.wellname(self.sample.well)
                if self.preferredWell != None and self.preferredWell != wellname:
                    print "WARNING: %s moved from preferred well %s to %s\n"%(self.name,self.preferredWell,wellname)
        return self.sample
    

def isReagent(name):
    return name in all

def get(name):
    return all[name].get()

def __getattr__(name):
    return get(name)

def add(name,plate=Experiment.REAGENTPLATE,well=None,conc=None,hasBeads=False,extraVol=50):
    all[name]=Reagent(name,plate,well,conc,hasBeads,extraVol)

