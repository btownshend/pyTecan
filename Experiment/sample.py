from __future__ import print_function

import sys
import math
from . import liquidclass
from . import worklist
from .concentration import Concentration
from . import clock
from . import logging
from .platetype import interpolate
from .db import db
from .decklayout import MAGPLATELOC

MAXVOLUME=200
MINLIQUIDDETECTVOLUME=15
#MINLIQUIDDETECTVOLUME=1000  # Liquid detect may be broken
#MINMIXTOPVOLUME=50   # Use manual mix if trying to mix more than this volume  (aspirates at ZMax-1.5mm, dispenses at ZMax-5mm)
MINMIXTOPVOLUME=1e10   # Disabled manual mix -- may be causing bubbles
SHOWTIPS=False
SHOWTIPHISTORY=False
SHOWINGREDIENTS=False
MINDEPOSITVOLUME=4.0	# Minimum volume to end up with in a well after dispensing
MINSIDEDISPENSEVOLUME=10.0  # minimum final volume in well to use side-dispensing.  Side-dispensing with small volumes may result in pulling droplet up sidewall
MIXLOSS=3.26		# Amount of sample lost during mixes  (in addition to any prefill volume)
BEADSETTLINGTIME=10*60 	# Time (in seconds) after which beads should be remixed before use

enablevolchecks=True  # True to enable volume checks before aspiration

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
    __allsamples = []
    __historyOptions = ["normal", "shake", "detect", "tc", "evap"]

    @staticmethod
    def allsamples():
        return Sample.__allsamples

    @staticmethod
    def printallsamples(txt="",fd=sys.stdout,w=None):
        print("\n%s by plate:"%txt, file=fd)
        plates=set([s.plate for s in Sample.__allsamples])
        for p in sorted(plates, key=lambda x:x.name.upper()):
            print("Samples in plate: ",p, file=fd)
            for s in sorted(Sample.__allsamples, key=lambda x:x.well if x.well is not None else 0):
                if len(s.history)==0:
                    continue   # Not used
                if s.plate==p:
                    if w is not None:
                        print(s,("%06x"%(s.getHash()&0xffffff)), file=fd)
                    else:
                        print(s, file=fd)
            print(file=fd)
        if SHOWTIPS and SHOWTIPHISTORY:
            print("\nTip history:\n", file=fd)
            for t in tiphistory:
                print("%d: %s\n"%(t,tiphistory[t]), file=fd)

    @staticmethod
    def evapcheckallsamples():
        for s in Sample.__allsamples:
            s.evapcheck("end")
    
    @staticmethod
    def numSamplesOnPlate(plate):
        cnt=0
        for s in Sample.__allsamples:
            if s.plate==plate and len(s.history)>0:
                cnt+=1
        return cnt

    @staticmethod
    def setHistoryOptions(opts):
        Sample.__historyOptions=opts
        
    def __init__(self, name, plate, well=None, conc=None, volume=0, hasBeads=False, extraVol=50, mixLC=liquidclass.LCMixBottom, firstWell=None,
                 extrainfo=None, ingredients=None, atEnd=False, refillable=False,noEvap=False,precious=False):
        if extrainfo is None:
            extrainfo = []
        while True:
            # wrap with a loop to allow use of backupPlate
            # If firstWell is not None, then it is a hint of the first well position that should be used
            if well is not None and well!=-1:
                if not isinstance(well,int):
                    well=plate.wellnumber(well)
                if well not in plate.wells:
                    logging.warning("Attempt to assign sample %s to well %d (%s) which is not legal on plate %s"%(name,well,plate.wellname(well),plate.name))
                for s in Sample.__allsamples:
                    if s.well==well and s.plate==plate:
                        logging.warning("Attempt to assign sample %s to plate %s, well %s that already contains %s"%(name,str(plate),plate.wellname(well),s.name))
                        if firstWell is None:
                            firstWell=well
                        well=None
                        break

            if well is None:
                # Find first unused well
                found=False
                if firstWell is not None:
                    # First check only wells>=firstWell
                    for well in plate.wells:
                        if well<firstWell:
                            continue
                        found=True
                        for s in Sample.__allsamples:
                            if s.plate==plate and s.well==well:
                                well=well+1
                                found=False
                                break
                        if found:
                            break

                if not found:
                    well=max(plate.wells) if atEnd else min(plate.wells) 
                    while (well>=0) if atEnd else (well<=max(plate.wells)):
                        if well not in plate.wells:
                            well = well + (-1 if atEnd else 1)
                            continue
                        found=True
                        for s in Sample.__allsamples:
                            if s.plate==plate and s.well==well:
                                well=well+(-1 if atEnd else 1)
                                found=False
                                break
                        if found:
                            break
            elif well==-1:
                well=None

            if well is not None and well>=plate.plateType.nx*plate.plateType.ny:
                # Overflow
                if plate.backupPlate is not None:
                    # Overflow onto backup plate
                    logging.warning("Overflow of %s plate, moving %s to %s plate -- verify carefully!"%(plate.name,name,plate.backupPlate.name))
                    plate=plate.backupPlate
                    well=None
                    continue
                else:
                    logging.error("Overflow of plate %s while adding %s"%(str(plate),name))

            break

        for s in Sample.__allsamples:
            if s.plate==plate and s.well==well:
                logging.error("Attempt to assign sample %s to plate %s, well %s that already contains %s"%(name,str(plate),plate.wellname(well),s.name))

        if name in [s.name for s in Sample.__allsamples]:
            while name in [s.name for s in Sample.__allsamples]:
                name=name+"#"
            logging.notice("renaming sample to %s"%name)
        self.name=name
        self.plate=plate
        self.well=well
        if isinstance(conc,Concentration) or conc is None:
            self.conc=conc
        else:
            self.conc=Concentration(conc)
        self.volume=volume
        self.initVol=volume
        if volume>0:
            if ingredients is None:
                self.ingredients={name:volume}
            else:
                self.ingredients=ingredients.copy()
                total=sum([v for v in ingredients.values()])
                for k in self.ingredients:
                    self.ingredients[k]=self.ingredients[k]*volume/total
            self.lastvolcheck=None
        else:
            self.ingredients={}
            self.lastvolcheck=0   # Assume that it has already been checked for 0 (since it can't be any less...)

        self.precious=precious
        self.checkingredients()

        if plate.plateType.pierce:
            self.bottomLC=liquidclass.LCWaterPierce
            self.bottomSideLC=self.bottomLC  # Can't use side with piercing
            self.inliquidLC=self.bottomLC  # Can't use liquid detection when piercing
        else:
            self.bottomSideLC=liquidclass.LCWaterBottomSide
            if self.precious:
                self.bottomLC=liquidclass.LCPreciousBottom
                self.inliquidLC=liquidclass.LCPreciousInLiquid
            else:
                self.bottomLC=liquidclass.LCWaterBottom
                self.inliquidLC=liquidclass.LCWaterInLiquid

        self.beadsLC=liquidclass.LCWaterBottomBeads
        self.mixLC=mixLC
        self.airLC=liquidclass.LCAir
        # Same as bottom for now
        self.emptyLC=self.bottomLC
        self.history=""
        Sample.__allsamples.append(self)
        if hasBeads:
            self.lastMixed=None
        else:
            self.lastMixed=clock.elapsed()-20*60		# Assume it was last mixed an 20 min before start of run
        self.wellMixed=True
        self.initHasBeads=hasBeads
        self.hasBeads=hasBeads		# Setting this to true overrides the manual conditioning
        self.extraVol=extraVol			# Extra volume to provide
        self.evap=0   # Amount that has evaporated
        if self.plate.name=="Samples":
            self.lastevapupdate=clock.pipetting
        else:
            self.lastevapupdate=clock.elapsed()
        self.extrainfo=extrainfo
        self.emptied=False
        self.refillable=refillable   # When using refillable, self.volume still refers to the total volume throughout the entire run; could be higher than tube capacity
        # But the actual volume in the tube will always be <=self.volume
        self.lastLevelCheck = None
        self.noEvap=noEvap   # True to disable evaporation (such as for DMSO)
        db.newsample(self)
        
    def isMixed(self):
        """Check if sample is currently mixed"""
        if self.lastMixed is None:
            return False
        elif not self.hasBeads:
            return True
        else:
            return clock.elapsed()-self.lastMixed < BEADSETTLINGTIME

    def sampleWellPosition(self):
        """Convert a sample well number to a well position as used by Gemini worklist"""
        if self.well is None:
            return None
        elif isinstance(self.well,int):
            ival=int(self.well)
            (col,row)=divmod(ival,self.plate.plateType.ny)
            col=col+1
            row=row+1
        else:
            col=int(self.well[1:])
            # noinspection PyUnresolvedReferences
            row=ord(self.well[0])-ord('A')+1
        assert 1 <= row <= self.plate.plateType.ny and 1 <= col <= self.plate.plateType.nx
        wellpos=(row-1)+self.plate.plateType.ny*(col-1)
        #print "sampleWellPosition(%d) -> %d"%(self.well,wellpos)
        return wellpos

    def getHash(self):
        return worklist.getHashCode(grid=self.plate.location.grid,pos=self.plate.location.pos-1,well=self.sampleWellPosition())

    @classmethod
    def clearall(cls):
        """Clear all samples"""
        Sample.__allsamples=[]		# Clear list of samples
        db.clearSamples()
        # for s in Sample.__allsamples:
        #     s.history=""
        #     s.lastMixed=None
        #     s.hasBeads=s.initHasBeads
        #     if s.volume==0:
        #         s.conc=None
        #         s.ingredients={}
        #     else:
        #         s.ingredients={s.name:s.volume}
        #     s.firstdispense = 0					# Last time accessed

    @classmethod
    def clearplate(cls,plate):
        """Remove all samples from give plate"""
        print(cls)
        allnew=[s for s in Sample.__allsamples if s.plate!=plate]
        Sample.__allsamples=allnew

    @classmethod
    def lookup(cls,name):
        for s in Sample.__allsamples:
            if s.name==name:
                return s
        return None

    @classmethod
    def lookupByWell(cls,plate,well):
        for s in Sample.__allsamples:
            if s.plate==plate and (s.well==well or s.well is None):
                return s
        return None

    @classmethod
    def getAllOnPlate(cls,plate=None,onlyUsed=True):
        result=[]
        for s in Sample.__allsamples:
            if (plate is None or s.plate==plate) and (not onlyUsed or len(s.history)>0):
                result.append(s)
        return result

    @classmethod
    def getAllLocOnPlate(cls,plate=None):
        result=""
        for s in Sample.__allsamples:
            if (plate is None or s.plate==plate) and len(s.history)>0:
                result+=" %s"%(s.plate.wellname(s.well))
        return result

    def dilute(self,factor):
        """Dilute sample -- just increases its recorded concentration"""
        if self.conc is not None:
            self.conc=self.conc.dilute(1.0/factor)

    def evapcheck(self,op,thresh=0.20):
        """Update amount of evaporation and check for issues"""
        if self.noEvap:  # Override
            return
        if self.plate.name=="Samples":
            dt=clock.pipetting-self.lastevapupdate	# Assume no evaporation while in TC
            if dt<-0.1:
                # This may happen during thermocycler operation since pipetting while thermocycling is moved to pipthermotime after waitpgm() is called
                logging.notice( "%s: clock went backwards: pipetting=%f, lastevapupdate=%f, dt=%f -- probably OK due to counting pipetting time during TC operation"%(self.name, clock.pipetting,self.lastevapupdate,dt))
        else:
            dt=clock.elapsed()-self.lastevapupdate
            if dt<-0.1:
                logging.error( "%s: clock went backwards: elapsed=%f, lastevapupdate=%f, dt=%f"%(self.name, clock.elapsed(),self.lastevapupdate,dt))
        if dt<=0.1:
            return
        for i in range(10):   # Break it into smaller steps since volume affects rate
            evaprate=self.plate.getevaprate(max(0,self.volume-self.evap))
            self.evap+=evaprate*dt/3600/10
            self.evap=min(self.evap,self.volume)
        if op=='aspirate'  and self.evap>thresh*self.volume and self.evap>2.0 and self.volume>0:
            pctevap=self.evap/self.volume*100
            logging.warning(" %s (%s.%s, vol=%.1f ul) may have %.1f ul of evaporation (%.0f%%)"%(self.name,str(self.plate),self.plate.wellname(self.well),self.volume,self.evap,pctevap))
            if "evap" in Sample.__historyOptions:
                self.history= self.history + (' [Evap: %0.1f ul]' % self.evap)
        self.lastevapupdate+=dt
        
    def amountToRemove(self,tgtVolume):
        """Calculate amount of volume to remove from sample to hit tgtVolume"""
        assert not self.refillable   # Can't know how much is present
        self.evapcheck('check')
        volume=self.volume-tgtVolume	# Run through with nominal volume
        removed=0.0
        nloop=0
        while abs(self.volume-removed-tgtVolume)>0.1 and nloop<5:
            if nloop>0:
                volume=self.volume-removed-tgtVolume+volume
            lc=self.chooseLC(volume)
            if self.hasBeads and self.plate.location==MAGPLATELOC:
                # With beads don't do any manual conditioning and don't remove extra (since we usually want to control exact amounts left behind, if any)
                removed=lc.volRemoved(volume,multi=False)
            else:
                removed=lc.volRemoved(volume,multi=True)
                if self.hasBeads:
                    removed=removed+MIXLOSS
            #print "Removing %.1f from %.1f leaves %.1f (tgt=%.1f)"%(volume,self.volume,self.volume-removed,tgtVolume)
            nloop+=1
        return volume

    def leveldetect(self,tipMask):
        worklist.detectLiquid(tipMask,[self.well],self.inliquidLC,self.plate,allowDelay=True)

    def volcheck(self,tipMask,well,volToRemove):
        """Check if the well contains the expected volume"""
        if not enablevolchecks:
            return
        
        # For refillable wells, this should not depend on self.volume, since that will only be an upper bound
        if self.lastvolcheck is not None:
            # Decide if a volume check is needed
            if volToRemove==0:
                # No need to check if not removing anything and it has been checked previously (i.e. lastvolcheck is not None)
                return
            if not self.refillable and (self.volume-volToRemove > max(30,self.lastvolcheck-200) or self.volume-volToRemove>200):
                # Not needed (but always check refillable wells)
                return
        self.lastvolcheck=self.volume
        height=self.plate.getliquidheight(self.volume)
        gemvol=self.plate.getgemliquidvolume(height)	# Volume that would be reported by Gemini for this height
        if not self.refillable and gemvol is None:
            logging.warning( "No volume equation for %s, skipping initial volume check"%self.name)
            return

        volcrit=self.plate.unusableVolume()*0.8+volToRemove
        if self.refillable:
            # Warn when getting low (shouldn't happen if we're on top of refilling)
            volwarn=max(volcrit,self.plate.unusableVolume())
        else:
            # Warn when getting low
            volwarn=max(volcrit,self.volume*0.80,self.volume+50)
            volwarn=min(volwarn,2000)  # Dont issue warnings for large volume containers

        heightwarn=min(self.plate.getliquidheight(volwarn),height-1.0)	# threshold is lower of 1mm or 80%
        gemvolwarn=self.plate.getgemliquidvolume(heightwarn)	# Volume that would be reported by Gemini for this height

        heightcrit=self.plate.getliquidheight(volcrit)
        gemvolcrit=self.plate.getgemliquidvolume(heightcrit)	# Volume that would be reported by Gemini for this height
    
        worklist.flushQueue()
        worklist.comment( "Check that %s contains %.1f ul (warn< %.1f, crit<%.1f), (expected gemvol=%.1f (warn<%.1f,crit<%.1f); height=%.1f (>%.1f) )"%(self.name,self.volume,volwarn,volcrit,gemvol,gemvolwarn,gemvolcrit,height,heightwarn))
        tipnum=0
        tm=tipMask
        while tm>0:
            tm=tm>>1
            tipnum+=1

        volvar='detected_volume_%d'%tipnum
        worklist.variable(volvar,-2)
        worklist.detectLiquid(tipMask,well,self.inliquidLC,self.plate)
        doneLabel=worklist.getlabel()
        worklist.condition(volvar,">",gemvolwarn,doneLabel)
        ptmp=clock.pipetting
        warnLabel=worklist.getlabel()
        worklist.condition(volvar,">",gemvolcrit,warnLabel)
        worklist.moveliha(worklist.WASHLOC)	# Get LiHa out of the way
        if self.refillable:
            msg="Failed volume check of %s(refillable) - should have at least %.0f ul (gemvol=~%s~, crit=%.0f)"%(self.name,volcrit,volvar,gemvolcrit)
        else:
            msg="Failed volume check of %s - should have %.0f ul (gemvol=~%s~, crit=%.0f)"%(self.name,self.volume,volvar,gemvolcrit)
        worklist.email(dest='cdsrobot@gmail.com',subject=msg)
        worklist.stringvariable("response","retry",msg+" Enter 'ignore' to ignore and continue, otherwise will retry.")
        worklist.condition("response","==","ignore",doneLabel)
        # Retry
        worklist.detectLiquid(tipMask,well,self.inliquidLC,self.plate)
        worklist.condition(volvar,">",gemvolcrit,doneLabel)
        worklist.stringvariable("response","retry","Still have <%.0f. Enter 'ignore' to ignore and continue, otherwise will retry."%self.volume)
        worklist.condition("response","==","ignore",doneLabel)
        # Retry again
        worklist.detectLiquid(tipMask,well,self.inliquidLC,self.plate)
        worklist.condition(volvar,">",gemvolcrit,doneLabel)
        worklist.stringvariable("response","ignore","Still have <%.0f. Will continue regardless."%self.volume)
        worklist.condition("response","!=","warn",doneLabel)

        worklist.comment(warnLabel)
        if self.refillable:
            msg="Warning: volume check of %s(refillable) - should have at least %.0f ul (gemvol=~%s~, warn=%.0f, crit=%.0f)"%(self.name,volwarn,volvar,gemvolwarn,gemvolcrit)
        else:
            msg="Warning: volume check of %s - should have %.0f ul (gemvol=~%s~, warn=%.0f, crit=%.0f)"%(self.name,self.volume,volvar,gemvolwarn,gemvolcrit)
        worklist.email(dest='cdsrobot@gmail.com',subject=msg)
        worklist.comment(doneLabel)
        clock.pipetting=ptmp   # All the retries don't usually happen, so don't count in total time
        self.addhistory("LD",0,tipMask,"detect")

    def aspirate(self,tipMask,volume,multi=False,lc=None):
        self.evapcheck('aspirate')
        if self.plate.getzmax() is None:
            logging.error( "Aspirate from illegal location: %s" % self.plate.location)
        removeAll=volume==self.volume
        if removeAll:
            logging.notice("Removing all contents (%.1ful) from %s"%(volume,self.name))
            
        if volume<0.1:
            logging.notice("attempt to aspirate only %.3f ul from %s ignored"%(volume,self.name))
            return
        if volume<2 and not multi and self.name!="Water":
            logging.warning("Inaccurate for < 2ul:  attempting to aspirate %.1f ul from %s"%(volume,self.name))
        if volume>self.volume > 0:
            logging.error("Attempt to aspirate %.1f ul from %s that contains only %.1f ul"%(volume, self.name, self.volume))
        if not self.isMixed() and self.plate.location!=MAGPLATELOC:
            if self.hasBeads and self.lastMixed is not None:
                logging.mixwarning("Aspirate %.1f ul from sample %s that has beads and has not been mixed for %.0f sec. "%(volume,self.name,clock.elapsed()-self.lastMixed))
            elif not self.wellMixed:
                logging.mixwarning("Aspirate %.1f ul from unmixed sample %s. "%(volume,self.name))
        if not self.wellMixed and self.plate.location!=MAGPLATELOC:
            logging.mixwarning("Aspirate %.1f ul from poorly mixed sample %s (shake speed was too low). "%(volume,self.name))

        if self.well is None:
            well=[]
            for i in range(4):
                if (tipMask & (1<<i)) != 0:
                    well.append(i)
        else:
            well=[self.well]

        if lc is None:
            lc=self.chooseLC(volume)
            
        self.volcheck(tipMask,well,volume)

        if (self.hasBeads and self.plate.location==MAGPLATELOC) or removeAll:
            # With beads don't do any manual conditioning and don't remove extra (since we usually want to control exact amounts left behind, if any)
            worklist.aspirateNC(tipMask,well,lc,volume,self.plate)
            remove=lc.volRemoved(volume,multi=multi)
            if self.volume==volume:
                # Removing all, ignore excess remove
                remove=self.volume-0.1   # Leave behind enough to be able to keep track of ingredients
                self.emptied=True
        else:
            if multi:
                worklist.aspirate(tipMask,well,lc,volume,self.plate)
            else:
                worklist.aspirateNC(tipMask,well,lc,volume,self.plate)
            # Manual conditioning handled in worklist
            remove=lc.volRemoved(volume,multi=multi)

            if remove+0.1 > self.volume > 0:
                logging.warning("Removing all contents (%.1f from %.1ful) from %s"%(remove,self.volume,self.name))
                remove=self.volume-0.1   # Leave residual

        self.removeVolume(remove)

        if self.volume+.001<self.plate.unusableVolume() and self.volume+remove>0 and not (self.hasBeads and self.plate.location==MAGPLATELOC) and not removeAll:
            logging.warning("Aspiration of %.1ful from %s brings volume down to %.1ful which is less than its unusable volume of %.1f ul"%(remove,self.name,self.volume,self.plate.unusableVolume()))
            
        self.addhistory("",-remove,tipMask)
        #self.addhistory("[%06x]"%(self.getHash(w)&0xffffff),-remove,tipMask)

    def removeVolume(self,remove):
        """ Remove volume and update ingredients"""
        if not self.ingredients:
            # No ingredients, but removing something -- happens during initial passes
            self.ingredients[self.name]=-remove
        else:
            for k in self.ingredients:
                self.ingredients[k] *= (self.volume-remove)/self.volume

        self.volume=self.volume-remove
        self.checkingredients()
        
    def aspirateAir(self,tipMask,volume):
        """Aspirate air over a well"""
        worklist.aspirateNC(tipMask,[self.well],self.airLC,volume,self.plate)

    def dispense(self,tipMask,volume,src,lc=None):
        assert not self.refillable    # Dispensing into a refillable well not supported
        self.evapcheck('dispense')
        if self.plate.getzmax() is None:
            logging.error( "Dispense to illegal location: %s"%self.plate.location)

        if volume<0.1:
            logging.notice("attempt to dispense only %.1f ul to %s ignored"%(volume,self.name))
            return

        if self.volume+volume < MINDEPOSITVOLUME:
            logging.warning("Dispense of %.1ful into %s results in total of %.1ful which is less than minimum deposit volume of %.1f ul"%(volume,self.name,self.volume+volume,MINDEPOSITVOLUME))

        #well=[self.well if self.well!=None else 2**(tipMask-1)-1 ]
        well=[self.well if self.well is not None else int(math.log(tipMask, 2))]
        if self.well is None:
            logging.warning("Dispense with well is None, not sure what right logic is..., using well=%d"%well[0])

        if self.volume+volume > self.plate.plateType.maxVolume and not self.refillable:
            logging.error("Dispense of %.1ful into %s results in total of %.1ful which is more than the maximum volume of %.1f ul"%(volume,self.name,self.volume+volume,self.plate.plateType.maxVolume))

        if lc is None:
            if self.hasBeads and self.plate.location==MAGPLATELOC:
                assert not self.refillable
                lc=self.beadsLC
            elif self.volume>=MINLIQUIDDETECTVOLUME:
                lc=self.inliquidLC
            elif self.volume+volume>=MINSIDEDISPENSEVOLUME:
                lc=self.bottomSideLC
            else:
                lc=self.bottomLC
        worklist.dispense(tipMask,well,lc,volume,self.plate)
        
        # Assume we're diluting the contents
        if self.conc is None and src.conc is None:
            pass
        elif src.conc is None or volume==0:
            if self.volume==0:
                self.conc=None
            else:
                self.conc=self.conc.dilute((self.volume+volume)/self.volume)
        elif self.conc is None or self.volume==0 or self.conc.final is None or src.conc.final is None:
            self.conc=src.conc.dilute((self.volume+volume)/volume)
        else:
            # Both have concentrations, they should match
            c1=self.conc.dilute((self.volume+volume)/self.volume)
            c2=src.conc.dilute((self.volume+volume)/volume)
            if abs(c1.stock/c1.final-c2.stock/c2.final)>.01:
                logging.warning("Dispense of %.1ful of %s@%.2fx into %.1ful of %s@%.2fx does not equalize concentrations"%(volume,src.name,src.conc.dilutionneeded(),self.volume,self.name,self.conc.dilutionneeded()))
                #assert abs(c1.stock/c1.final-c2.stock/c2.final)<.01
                self.conc=None
            else:
                self.conc=Concentration(c1.stock/c1.final,1.0,'x')  # Since there are multiple ingredients express concentration as x

         # Set to not mixed after second ingredient added
        if self.volume>0:
            self.lastMixed=None
            self.wellMixed=False

        if src.hasBeads and src.plate.location!=MAGPLATELOC:
            #print "Set %s to have beads since %s does\n"%(self.name,src.name)
            self.hasBeads=True

        self.volume=self.volume+volume

        self.emptied=False
        #self.addhistory("%06x %s"%(self.getHash(w)&0xffffff,src.name),volume,tipMask)
        self.addhistory(src.name,volume,tipMask)
        self.addingredients(src,volume)

    def addhistory(self, name, vol, tip, htype="normal"):
        if htype not in Sample.__historyOptions:
            return
        if vol>=0:
            if SHOWTIPS:
                s="%s[%.1f#%d]"%(name,vol,tip)
            else:
                s="%s[%.1f]"%(name,vol)
            if len(self.history)>0:
                self.history=self.history+" +"+s
            else:
                self.history=s
        elif vol<0:
            if SHOWTIPS:
                s="%s[%.1f#%d]"%(name,-vol,tip)
            else:
                s="%s[%.1f]"%(name,-vol)
            if len(self.history)>0:
                self.history=self.history+" -"+s
            else:
                self.history="-"+s
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
    def addallhistory(msg, addToEmpty=False, onlyplate=None, onlybeads=False, htype="normal"):
        """Add history entry to all samples (such as # during thermocycling)"""
        if htype not in Sample.__historyOptions:
            return  # Not logging this type
        for s in Sample.__allsamples:
            if (onlyplate is None or onlyplate==s.plate.name) and (not onlybeads or s.hasBeads):
                if len(s.history)>0 or (s.volume>0 and msg[0]!='('):
                    s.history+=" "+msg
                elif addToEmpty:
                    s.history=msg

    @staticmethod
    def shaken(plate,speed):
        """Called after shaking to mark all samples as mixed"""
        for s in Sample.__allsamples:
            if plate==s.plate.name and s.volume>0:
                if not s.wellMixed:
                    (minx,maxx)=s.getmixspeeds()
                    s.wellMixed=speed>=minx-1
                s.lastMixed=clock.elapsed()

    @staticmethod
    def notMixed(plate):
        """Called after thermocycling to mark all samples as unmixed (since they have condensation)"""
        for s in Sample.__allsamples:
            if plate==s.plate.name and s.volume>0:
                s.lastMixed=None
                # Don't set wellMixed to false though -- if it was well mixed before, then any shaking will bring down condensation and it should be well mixed
                #s.wellMixed=False

    def checkingredients(self):
        total=0.0
        for k in self.ingredients:
            total=total+self.ingredients[k]
        if abs(total-self.volume)>0.01:
            print("Ingredients of %s add up to %.2f ul, but volume=%.2f"%(self.name,total, self.volume))
            assert False
            
    def addingredients(self,src,vol):
        """Update ingredients by adding ingredients from src"""
        for k in src.ingredients:
            if src.plate.location==MAGPLATELOC and k=='BIND-UNUSED':
                pass  # Wasn't transferred
            else:
                addition=src.ingredients[k]/src.volume*vol
                if k in self.ingredients:
                    self.ingredients[k]+=addition
                else:
                    self.ingredients[k]=addition
        self.checkingredients()

    def glycerolfrac(self):
        """Return fraction of sample that is Glycerol"""
        if not 'glycerol' in self.ingredients:
            return 0.0
        total=sum([v for v in self.ingredients.values()])
        return self.ingredients['glycerol']*1.0/total

    def getmixspeeds(self):
        """Get minimum, maximum speed for mixing this sample"""
        assert not self.refillable   # Mixing of refillable wells not supported (unknown volume)
        ptype=self.plate.plateType

        if self.isMixed():
            minspeed=0
        elif self.wellMixed:
            minspeed=1000   # Was already mixed, but may have settled or have condensation
        else:
            minspeed=interpolate(ptype.minspeeds,self.volume)
            if minspeed is None:
                assumeSpeed=1900
                logging.notice("No shaker min speed data for volume of %.0f ul, assuming %.0f rpm"%(self.volume,assumeSpeed))
                minspeed=assumeSpeed

        maxspeed=interpolate(ptype.maxspeeds,self.volume)
        if maxspeed is None:
            assumeSpeed=1200
            logging.warning("No shaker max speed data for volume of %.0f ul, assuming %.0f rpm"%(self.volume,assumeSpeed))
            maxspeed=assumeSpeed
            
        glycerol=self.glycerolfrac()
        if glycerol>0:
            gmaxspeed=interpolate(ptype.glycerolmaxspeeds,self.volume)
            if gmaxspeed is None:
                logging.warning("No shaker max speed data for glycerol with volume of %.0f ul, using no-glycerol speed of  %.0f rpm"%(self.volume,maxspeed))
                gmaxspeed=maxspeed

            if glycerol>ptype.glycerol:
                logging.notice("Sample %s contains %.1f%% Glycerol (more than tested of %.1f%%)"%(self.name,glycerol*100,ptype.glycerol*100))
                maxspeed=gmaxspeed
            else:
                maxspeed=maxspeed+(gmaxspeed-maxspeed)*(glycerol/ptype.glycerol)
            if maxspeed<minspeed:
                if maxspeed<minspeed-1:
                    logging.notice("%s with %.1ful and %.1f%% glycerol has minspeed of %.0f greater than maxspeed of %.0f"%(self.name,self.volume,glycerol*100,minspeed,maxspeed))
                minspeed=maxspeed	# Glycerol presence should also reduce minspeed
        return minspeed, maxspeed
    
    def chooseLC(self,aspirateVolume=0):
        if self.refillable:
            return self.inliquidLC   # Since volume is unknown, this is the only option
        if self.volume-aspirateVolume>=MINLIQUIDDETECTVOLUME:
            if aspirateVolume==0:
                return self.inliquidLC	# Not aspirating, should be fine

            # Try using liquid detection
            initheight=self.plate.getliquidheight(self.volume)		# True height at start
            finalheight=self.plate.getliquidheight(self.volume-aspirateVolume)	# True height at end of aspirate
            initgemvolume=self.plate.getgemliquidvolume(initheight)		# How much will Gemini think we have at start
            if initgemvolume<aspirateVolume+15:
                # Not enough
                msg="Aspirate %.1f ul from %.1f ul,  gem will think initial volume is %.1ful which is too low to reliably work - not using LD"%(aspirateVolume,self.volume,initgemvolume)
                logging.notice(msg)
            else:
                finalgemvolume=initgemvolume-aspirateVolume
                finalgemheight=self.plate.getgemliquidheight(finalgemvolume)
                finaltipdepth=self.inliquidLC.submerge-(finalgemheight-finalheight)
                msg="Aspirate %.1f ul from %.1f ul in %s:  height goes from %.1f to %.1f mm, gem will think initial volume is %.1ful and final height %.1f mm"%(aspirateVolume,self.volume,self.name,initheight,finalheight,initgemvolume,finalgemheight)
                if finalgemheight-0.1<self.inliquidLC.submerge:
                    # Gemini won't be able to submerge as much as requested
                    logging.notice(msg+": Gemini would think there's not enough liquid to submerge %.1f mm - not using LD"%self.inliquidLC.submerge)
                elif finaltipdepth<0.1:
                    # Tracking is off so much that tip will break surface of water during operation 
                    logging.notice(msg+": tip will not be submerged enough (depth=%.1f mm) - not using LD"%finaltipdepth)
                else:
                    # Should be good
                    #logging.notice(msg)
                    return self.inliquidLC
        # No liquid detect:
        if self.volume==0 and aspirateVolume==0:
            return self.emptyLC
        elif self.hasBeads and self.plate.location==MAGPLATELOC:
            return self.beadsLC
        else:
            return self.bottomLC

        # Mix, return true if actually did a mix, false otherwise
    def mix(self,tipMask,preaspirateAir=False,nmix=4):
        assert not self.refillable   # Not supported -- unknown volume
        if self.isMixed() and self.wellMixed:
            logging.notice( "mix() called for sample %s, which is already mixed"%self.name)
            return False
        logging.mixwarning("Pipette mixing of %s may introduce bubbles"%self.name)

        self.volcheck(tipMask,[self.well],0)

        blowvol=5
        extraspace=blowvol+0.1
        if preaspirateAir:
            extraspace+=5
        mixvol=self.volume		  # -self.plate.unusableVolume();  # Can mix entire volume, if air is aspirated, it will just be dispensed first without making a bubble
        if self.volume>MAXVOLUME-extraspace:
            mixvol=MAXVOLUME-extraspace
            logging.mixwarning("Mix of %s limited to %.0f ul instead of full volume of %.0ful"%(self.name,mixvol,self.volume))
        well=[self.well if self.well is not None else 2 ** (tipMask - 1) - 1]
        mixprefillvol=5
        if mixvol<self.plate.unusableVolume()-mixprefillvol:
            logging.notice("Not enough volume in sample %s (%.1f) to mix"%(self.name,self.volume))
            self.history+="(UNMIXED)"
            return False
        else:
            if preaspirateAir:
                # Aspirate some air to avoid mixing with excess volume aspirated into pipette from source in previous transfer
                self.aspirateAir(tipMask,5)
            # noinspection PyUnreachableCode,PyUnreachableCode
            if False:		# this results in losing mixprefillvol of sample which was not mixed; remainder has different concentration than planned
                worklist.aspirateNC(tipMask,well,self.inliquidLC,mixprefillvol,self.plate)
                self.removeVolume(mixprefillvol)
                self.addhistory("(PRE)",-mixprefillvol,tipMask)
                worklist.mix(tipMask,well,self.mixLC,mixvol,self.plate,nmix)
                mstr="(MB)"
            elif False: # self.volume>=MINLIQUIDDETECTVOLUME:    # Another short-lived strategy
                worklist.mix(tipMask,well,self.inliquidLC,mixvol,self.plate,nmix)
                self.history+="(MLD)"
            else:
                height=self.plate.getliquidheight(self.volume)
                if height is None:
                    worklist.mix(tipMask,well,self.mixLC,mixvol,self.plate,nmix)
                    mstr="(MB)"
                else:
                    mixheight=math.floor(height-1)			# At least 1mm below liquid height
                    if mixheight<2:
                        mixheight=2
#                    print 'Vol=%.1f ul, height=%.1f mm, mix=%d, blow=%d'%(self.volume,height,mixheight,blowheight)
                    mixLC=liquidclass.LCMix[min(12,mixheight)]
                    blowoutLC = liquidclass.LCBlowoutLD

                    if blowvol>0:
                        worklist.aspirateNC(tipMask,well,self.airLC,(blowvol+0.1),self.plate)
                    if self.volume<30:
                        worklist.mix(tipMask,well,self.mixLC,mixvol,self.plate,nmix)
                        mstr="(MB)"
                    else:
                        for _ in range(nmix):
                            worklist.aspirateNC(tipMask,well,mixLC,mixvol,self.plate)
                            worklist.dispense(tipMask,well,mixLC,mixvol,self.plate)
                        mstr="(M@%d)" % mixheight
                    if blowvol>0:
                        worklist.dispense(tipMask,well,blowoutLC,blowvol,self.plate)
                        worklist.dispense(tipMask,well,liquidclass.LCDip,0.1,self.plate)

            self.removeVolume(MIXLOSS)
            self.addhistory(mstr,-MIXLOSS,tipMask)
            self.lastMixed=clock.elapsed()
            self.wellMixed=True
            return True

    def __str__(self):
        s="%-32s " % self.name
        if self.conc is not None:
            s+=" %-18s"%("[%s]"%str(self.conc))
        else:
            s+=" %-18s"%""
        if self.hasBeads:
            beadString=",beads"
        else:
            beadString=""
        if self.evap>0.05*self.volume and self.evap>1.0:
            evapString=" -%.1f ul"%self.evap
        else:
            evapString=""
        if self.initVol!=0:
            volString="%.1f->%.1f"%(self.initVol, self.volume)
        else:
            volString="%.1f" % self.volume
        if self.refillable:
            volString=volString+"(refillable)"
            
        s+=" %-30s"%("(%s.%s,%s ul%s%s)"%(self.plate.name,self.plate.wellname(self.well),volString,evapString,beadString))
        hist=self.history
        trunchistory=True # self.plate.name!="Samples"
        if trunchistory and len(hist)>0:
            # Remove any trailing {xx} or (xx) markers from history
            wds=hist.strip().split(' ')
            pcnt=0;bcnt=0
            for i in range(len(wds)-1,-1,-1):
                if wds[i][0]=='(':
                    pcnt+=1
                elif wds[i][0]=='{':
                    bcnt+=1
                else:
                    if bcnt+pcnt>1:
                        hist=' '.join(wds[:i+1])
                        hist+=' ...%d incubations,%d shakes'%(bcnt,pcnt)
                    else:
                        hist=self.history # If only 1 element, don't bother truncating
                    break

        s+=" %s"%hist
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
    def savematlab(filename):
        fd=open(filename,"w")
        print("samps=[];", file=fd)
        for s in Sample.__allsamples:
            ing=""
            ingvol=""
            for k in s.ingredients:
                if len(ing)==0:
                    ing="'%s'"%k
                    ingvol="%g"%s.ingredients[k]
                else:
                    ing=ing+",'%s'"%k
                    ingvol=ingvol+",%g"%s.ingredients[k]

            print("samps=[samps,struct('name','%s','plate','%s','well','%s','concentration','%s','history','%s','ingredients',{{%s}},'volumes',[%s],'extrainfo',[%s])];"%(s.name,s.plate,s.plate.wellname(s.well),str(s.conc),s.history,ing,ingvol,",".join(["%d"%x for x in s.extrainfo])), file=fd)
        fd.close()
