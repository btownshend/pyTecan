# Reagent - a set of samples that are allocated as they are needed
from __future__ import print_function

import sys
import operator
from .sample import Sample
from . import logging
from . import decklayout
from .concentration import Concentration
from .plate import Plate
from . import clock

class Reagent(object):
    allReagents={}

    def __init__(self, name:str , plate:Plate=None, well:str=None, conc:Concentration=None, hasBeads:bool=False, extraVol:float=50, initVol:float=0, extrainfo=None, ingredients=None, refillable=False, noEvap=False,precious=False):
        if extrainfo is None:
            extrainfo = []
        self.sample=None
        self.name=name
        if plate is None:
            self.plate=decklayout.REAGENTPLATE
        else:
            self.plate=plate
        self.preferredWell=well
        self.conc=conc
        self.hasBeads=hasBeads
        self.extraVol=extraVol
        self.initVol=initVol
        self.extrainfo=extrainfo
        self.ingredients=ingredients
        self.refillable=refillable
        self.noEvap=noEvap
        self.precious=precious
        
    def __str__(self):
        s=self.name
        return s
    def __repr__(self):
        return str(self)

    def getsample(self):
        if self.sample is None:
            #print "Creating sample for reagent %s with %.1f ul"%(self.name,self.initVol)
            self.sample=Sample(self.name,self.plate,self.preferredWell,self.conc,hasBeads=self.hasBeads,volume=self.initVol,extrainfo=self.extrainfo,ingredients=self.ingredients,refillable=self.refillable,noEvap=self.noEvap,precious=self.precious)
            wellname=self.sample.plate.wellname(self.sample.well)
            if self.preferredWell is not None and self.preferredWell != wellname:
                logging.warning("%s moved from preferred well %s to %s\n"%(self.name,self.preferredWell,wellname))
        return self.sample

    def reset(self):
        """Reset reagent: clear sample, adjust initial volume to make current volume equal to extraVol"""
        if self.sample is not None:
            adj=self.extraVol-self.sample.volume
            if adj>0:
                print("Adjusting initVol of %s to %.1f (adj=%.1f)"%(self.name,self.initVol+adj,adj))
                self.initVol+=adj
            self.sample=None
            self.getsample()   # Re-allocate sample


def isReagent(name:str):
    return name in Reagent.allReagents

def getsample(name:str):
    return Reagent.allReagents[name].getsample()

def lookup(name:str):
    return Reagent.allReagents[name]

def add(name, plate:Plate=None, well=None, conc:Concentration=None, hasBeads:bool=False, extraVol:float=50, initVol:float=0, extrainfo=None, ingredients=None, refillable=False, noEvap=False, precious=False):
    if extrainfo is None:
        extrainfo = []
    if plate is None:
        plate=decklayout.REAGENTPLATE
    if name in Reagent.allReagents:
        logging.error("Attempt to add duplicate reagent, "+name)
    Reagent.allReagents[name]=Reagent(name,plate,well,conc,hasBeads,extraVol,initVol=initVol,extrainfo=extrainfo,ingredients=ingredients,refillable=refillable,noEvap=noEvap,precious=precious)
    return Reagent.allReagents[name]

def reset():
    for r in Reagent.allReagents:
        Reagent.allReagents[r].reset()

def printprep(fd=sys.stdout):
    for p in sorted(set([r.plate for r in Reagent.allReagents.values()]),key=operator.attrgetter('name')):
        print("\nPlate %s:"%p.name, file=fd)
        total=0
        extras=0
        for r in sorted(iter(Reagent.allReagents.values()), key=lambda x:x.sample.well if x.sample is not None else 0):
            s=r.sample
            if s is None:
                continue
            if s.plate!=p:
                continue
            if s.conc is not None:
                c="[%s]"%str(s.conc)
            else:
                c=""
            if s.volume==r.initVol:
                # Not used
                #note="%s%s in %s.%s not consumed"%(s.name,c,str(s.plate),s.plate.wellname(s.well))
                #notes=notes+"\n"+note
                pass
            elif r.initVol>0:
                if r.refillable:
                    initStr = "up to %.1f ul (refillable)"%r.initVol
                else:
                    initStr = "%.1f ul"%r.initVol
                print("%s%s in %s.%s consume %.1f ul, provide %s"%(s.name,c,s.plate.name,s.plate.wellname(s.well),r.initVol-s.volume,initStr), file=fd)
            total+=round((r.initVol-s.volume)*10)/10.0
            extras+=r.extraVol
            if r.initVol>s.plate.plateType.maxVolume and not r.refillable:
                logging.error("Excess initial volume (%.1f) for %s, maximum is %.1f"%(r.initVol,s.name,s.plate.plateType.maxVolume))
        print("Total %s volume = %.1f ul (%.1f ul with extras)"%(p.name,total,total+extras), file=fd)