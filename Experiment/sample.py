import sys
import math
import liquidclass
import worklist
from concentration import Concentration
import clock
import logging
from plate import interpolate

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
        plates=set([s.plate for s in __allsamples])
        for p in sorted(plates, key=lambda p:p.name.upper()):
            print >>fd,"Samples in plate: ",p
            for s in sorted(__allsamples, key=lambda p:p.well):
                if len(s.history)==0:
                    continue   # Not used
                if s.plate==p:
                    if w!=None:
                        print >>fd,s,("%06x"%(s.getHash()&0xffffff))
                    else:
                        print >>fd,s
            print >>fd
        if SHOWTIPS and SHOWTIPHISTORY:
            print >>fd,"\nTip history:\n"
            for t in tiphistory:
                print >>fd,"%d: %s\n"%(t,tiphistory[t])

    @staticmethod
    def numSamplesOnPlate(plate):
        cnt=0
        for s in __allsamples:
            if s.plate==plate and len(s.history)>0:
                cnt+=1
        return cnt

    def __init__(self,name,plate,well=None,conc=None,volume=0,hasBeads=False,extraVol=50,mixLC=liquidclass.LCMixBottom,firstWell=None,extrainfo=[],ingredients=None):
        # If firstWell is not None, then it is a hint of the first well position that should be used
        if well!=None and well!=-1:
            if not isinstance(well,int):
                well=plate.wellnumber(well)
            if well not in plate.wells:
                logging.warning("Attempt to assign sample %s to well %d (%s) which is not legal on plate %s"%(name,well,plate.wellname(well),plate.name))
            for s in __allsamples:
                if s.well==well and s.plate==plate:
                    logging.warning("Attempt to assign sample %s to plate %s, well %s that already contains %s"%(name,str(plate),plate.wellname(well),s.name))
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
                    for s in __allsamples:
                        if s.plate==plate and s.well==well:
                            well=well+1
                            found=False
                            break
                    if found:
                        break

            if not found:
                for well in plate.wells:
                    found=True
                    for s in __allsamples:
                        if s.plate==plate and s.well==well:
                            well=well+1
                            found=False
                            break
                    if found:
                        break
        elif well==-1:
            well=None

        for s in __allsamples:
            if s.plate==plate and s.well==well:
                logging.error("Attempt to assign sample %s to plate %s, well %s that already contains %s"%(name,str(plate),plate.wellname(well),s.name))
        if name in [s.name for s in __allsamples]:
            while name in [s.name for s in __allsamples]:
                name=name+"#"
            logging.notice("renaming sample to %s"%name)
        self.name=name
        self.plate=plate
        if well>=plate.nx*plate.ny:
            logging.error("Overflow of plate %s while adding %s"%(str(plate),name))

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
                self.ingredients=ingredients
                total=sum([v for v in ingredients.values()])
                for k in self.ingredients:
                    self.ingredients[k]=self.ingredients[k]*volume/total
            self.lastvolcheck=None
        else:
            self.ingredients={}
            self.lastvolcheck=0   # Assume that it has already been checked for 0 (since it can't be any less...)

        if plate.pierce:
            self.bottomLC=liquidclass.LCWaterPierce
            self.bottomSideLC=self.bottomLC  # Can't use side with piercing
            self.inliquidLC=self.bottomLC  # Can't use liquid detection when piercing
        else:
            self.bottomLC=liquidclass.LCWaterBottom
            self.bottomSideLC=liquidclass.LCWaterBottomSide
            self.inliquidLC=liquidclass.LCWaterInLiquid

        self.beadsLC=liquidclass.LCWaterBottomBeads
        self.mixLC=mixLC
        self.airLC=liquidclass.LCAir
        # Same as bottom for now
        self.emptyLC=self.bottomLC
        self.history=""
        __allsamples.append(self)
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
        
    def isMixed(self):
        'Check if sample is currently mixed'
        if self.lastMixed is None:
            return False
        elif not self.hasBeads:
            return True
        else:
            return clock.elapsed()-self.lastMixed < BEADSETTLINGTIME

    def sampleWellPosition(self):
        'Convert a sample well number to a well position as used by Gemini worklist'
        if self.well is None:
            return None
        elif isinstance(self.well,(long,int)):
            ival=int(self.well)
            (col,row)=divmod(ival,self.plate.ny)
            col=col+1
            row=row+1
        else:
            col=int(self.well[1:])
            row=ord(self.well[0])-ord('A')+1
        assert row>=1 and row<=self.plate.ny and col>=1 and col<=self.plate.nx
        wellpos=(row-1)+self.plate.ny*(col-1)
        #print "sampleWellPosition(%d) -> %d"%(self.well,wellpos)
        return wellpos

    def getHash(self):
        return worklist.getHashCode(grid=self.plate.grid,pos=self.plate.pos-1,well=self.sampleWellPosition())

    @classmethod
    def clearall(cls):
        'Clear all samples'
        global __allsamples
        __allsamples=[]		# Clear list of samples
        # for s in __allsamples:
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
        'Remove all samples from give plate'
        print cls
        global __allsamples
        allnew=[s for s in __allsamples if s.plate!=plate]
        __allsamples=allnew

    @classmethod
    def lookup(cls,name):
        for s in __allsamples:
            if s.name==name:
                return s
        return None

    @classmethod
    def lookupByWell(cls,plate,well):
        for s in __allsamples:
            if s.plate==plate and s.well==well:
                return s
        return None

    @classmethod
    def getAllOnPlate(cls,plate=None):
        result=[]
        for s in __allsamples:
            if (plate is None or s.plate==plate) and len(s.history)>0:
                result.append(s)
        return result

    @classmethod
    def getAllLocOnPlate(cls,plate=None):
        result=""
        for s in __allsamples:
            if (plate is None or s.plate==plate) and len(s.history)>0:
                result+=" %s"%(s.plate.wellname(s.well))
        return result

    def dilute(self,factor):
        'Dilute sample -- just increases its recorded concentration'
        if self.conc!=None:
            self.conc=self.conc.dilute(1.0/factor)

    def evapcheck(self,op,thresh=0.20):
        'Update amount of evaporation and check for issues'
        if self.plate.name=="Samples":
            dt=clock.pipetting-self.lastevapupdate	# Assume no evaporation while in PTC
        else:
            dt=clock.elapsed()-self.lastevapupdate
        if dt<-0.1:
            logging.error( "clock went backwards: elapsed=%f, lastevapupdate=%f, dt=%f"%(clock.elapsed(),self.lastevapupdate,dt))
        if dt<=0.1:
            return
        for i in range(10):   # Break it into smaller steps since volume affects rate
            evaprate=self.plate.getevaprate(max(0,self.volume-self.evap))
            self.evap+=evaprate*dt/3600/10
        if op=='aspirate' and self.evap>thresh*self.volume and self.evap>2.0 and self.volume>0:
            pctevap=self.evap/self.volume*100
            logging.warning(" %s (%s.%s, vol=%.1f ul) may have %.1f ul of evaporation (%.0f%%)"%(self.name,str(self.plate),self.plate.wellname(self.well),self.volume,self.evap,pctevap))
            self.history= self.history + (' [Evap: %0.1f ul]'%(self.evap))
        self.lastevapupdate+=dt

    def amountToRemove(self,tgtVolume):
        'Calculate amount of volume to remove from sample to hit tgtVolume'
        self.evapcheck('check')
        volume=self.volume-tgtVolume	# Run through with nominal volume
        removed=0.0
        nloop=0
        while abs(self.volume-removed-tgtVolume)>0.1 and nloop<5:
            if nloop>0:
                volume=self.volume-removed-tgtVolume+volume
            lc=self.chooseLC(volume)
            if self.hasBeads and self.plate.curloc=="Magnet":
                # With beads don't do any manual conditioning and don't remove extra (since we usually want to control exact amounts left behind, if any)
                removed=lc.volRemoved(volume,multi=False)
            else:
                removed=lc.volRemoved(volume,multi=True)
                if self.hasBeads:
                    removed=removed+MIXLOSS
            #print "Removing %.1f from %.1f leaves %.1f (tgt=%.1f)"%(volume,self.volume,self.volume-removed,tgtVolume)
            nloop+=1
        return volume

    def volcheck(self,tipMask,well,volToRemove):
        '''Check if the well contains the expected volume'''
        if self.lastvolcheck is not None:
            # Decide if a volume check is needed
            if volToRemove==0:
                # No need to check if not removing anything and it has been checked previously (i.e. lastvolcheck is not None)
                return
            if self.volume-volToRemove > max(30,self.lastvolcheck-200) or self.volume-volToRemove>200:
                # Not needed
                return
        self.lastvolcheck=self.volume
        height=self.plate.getliquidheight(self.volume)
        gemvol=self.plate.getgemliquidvolume(height)	# Volume that would be reported by Gemini for this height
        if gemvol is None:
            logging.warning( "No volume equation for %s, skipping initial volume check"%self.name)
            return

        volwarn=self.volume*0.80
        heightwarn=min(self.plate.getliquidheight(volwarn),height-1.0)	# threshold is lower of 1mm or 80%
        gemvolwarn=self.plate.getgemliquidvolume(heightwarn)	# Volume that would be reported by Gemini for this height

        volcrit=self.plate.unusableVolume*0.8+volToRemove
        heightcrit=self.plate.getliquidheight(volcrit)
        gemvolcrit=self.plate.getgemliquidvolume(heightcrit)	# Volume that would be reported by Gemini for this height
    
        worklist.flushQueue()
        worklist.comment( "Check that %s contains %.1f ul (warn< %.1f, crit<%.1f), (gemvol=%.1f (warn<%.1f,crit<%.1f); height=%.1f (>%.1f) )"%(self.name,self.volume,volwarn,volcrit,gemvol,gemvolwarn,gemvolcrit,height,heightwarn))
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
        ptmp=clock.pipetting;
        warnLabel=worklist.getlabel()
        worklist.condition(volvar,">",gemvolcrit,warnLabel)
        worklist.moveliha(worklist.WASHLOC)	# Get LiHa out of the way
        msg="Failed volume check of %s - should have  %.0f ul (gemvol=~%s~, crit=%.0f)"%(self.name,self.volume,volvar,gemvolcrit)
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
        msg="Warning: volume check of %s - should have  %.0f ul (gemvol=~%s~, warn=%.0f, crit=%.0f)"%(self.name,self.volume,volvar,gemvolwarn,gemvolcrit)
        worklist.email(dest='cdsrobot@gmail.com',subject=msg)
        worklist.comment(doneLabel)
        clock.pipetting=ptmp   # All the retries don't usually happen, so don't count in total time
        self.addhistory("LD",0,tipMask)

    def aspirate(self,tipMask,volume,multi=False):
        self.evapcheck('aspirate')
        if self.plate.curloc=='PTC':
            logging.error( "Aspirate from PTC!, loc=%d,%d"%(self.plate.grid,self.plate.pos))

        if volume<0.1:
            logging.warning("attempt to aspirate only %.1f ul from %s ignored"%(volume,self.name))
            return
        if volume<2 and not multi and self.name!="Water":
            logging.warning("Inaccurate for < 2ul:  attempting to aspirate %.1f ul from %s"%(volume,self.name))
        if volume>self.volume and self.volume>0:
            logging.error("Attempt to aspirate %.1f ul from %s that contains only %.1f ul"%(volume, self.name, self.volume))
        if not self.isMixed() and self.plate.curloc!="Magnet":
            if self.hasBeads and self.lastMixed is not None:
                logging.mixwarning("Aspirate %.1f ul from sample %s that has beads and has not been mixed for %.0f sec. "%(volume,self.name,clock.elapsed()-self.lastMixed))
            else:
                logging.mixwarning("Aspirate %.1f ul from unmixed sample %s. "%(volume,self.name))
        if not self.wellMixed and self.plate.curloc!="Magnet":
            logging.mixwarning("Aspirate %.1f ul from poorly mixed sample %s (shake speed was too low). "%(volume,self.name))

        if self.well is None:
            well=[]
            for i in range(4):
                if (tipMask & (1<<i)) != 0:
                    well.append(i)
        else:
            well=[self.well]

        lc=self.chooseLC(volume)
            
        self.volcheck(tipMask,well,volume)

        if self.hasBeads and self.plate.curloc=="Magnet":
            # With beads don't do any manual conditioning and don't remove extra (since we usually want to control exact amounts left behind, if any)
            worklist.aspirateNC(tipMask,well,lc,volume,self.plate)
            remove=lc.volRemoved(volume,multi=False)
            if self.volume==volume:
                # Removing all, ignore excess remove
                remove=self.volume
                self.ingredients={}
        else:
            worklist.aspirate(tipMask,well,lc,volume,self.plate)
            # Manual conditioning handled in worklist
            remove=lc.volRemoved(volume,multi=True)

        if self.volume<remove and self.volume>0:
            logging.warning("Removing all contents (%.1f from %.1ful) from %s"%(remove,self.volume,self.name))
            remove=self.volume-0.1   # Leave residual

        for k in self.ingredients:
            if self.plate.curloc=="Magnet" and k=='BIND':
                pass
            else:
                self.ingredients[k] *= (self.volume-remove)/self.volume

        self.volume=self.volume-remove
        if self.volume+.001<self.plate.unusableVolume and self.volume+remove>0 and not (self.hasBeads and self.plate.curloc=='Magnet'):
            logging.warning("Aspiration of %.1ful from %s brings volume down to %.1ful which is less than its unusable volume of %.1f ul"%(remove,self.name,self.volume,self.plate.unusableVolume))
            
        self.addhistory("",-remove,tipMask)
        #self.addhistory("[%06x]"%(self.getHash(w)&0xffffff),-remove,tipMask)

    def aspirateAir(self,tipMask,volume):
        'Aspirate air over a well'
        worklist.aspirateNC(tipMask,[self.well],self.airLC,volume,self.plate)

    def dispense(self,tipMask,volume,src):
        self.evapcheck('dispense')
        if self.plate.curloc=='PTC':
            logging.error("Dispense to PTC!, loc=(%d,%d)"%(self.plate.grid,self.plate.pos))

        if volume<0.1:
            logging.warning("attempt to dispense only %.1f ul to %s ignored"%(volume,self.name))
            return

        if self.volume+volume < MINDEPOSITVOLUME:
            logging.warning("Dispense of %.1ful into %s results in total of %.1ful which is less than minimum deposit volume of %.1f ul"%(volume,self.name,self.volume+volume,MINDEPOSITVOLUME))

        #well=[self.well if self.well!=None else 2**(tipMask-1)-1 ]
        well=[self.well if self.well!=None else int(math.log(tipMask,2)) ]
        if self.well is None:
            logging.warning("Dispense with well is None, not sure what right logic is..., using well=%d"%well[0])

        if self.volume+volume > self.plate.maxVolume:
            logging.error("Dispense of %.1ful into %s results in total of %.1ful which is more than the maximum volume of %.1f ul"%(volume,self.name,self.volume+volume,self.plate.maxVolume))

        if self.hasBeads and self.plate.curloc=="Magnet":
            worklist.dispense(tipMask,well,self.beadsLC,volume,self.plate)
        elif self.volume>=MINLIQUIDDETECTVOLUME:
            worklist.dispense(tipMask,well,self.inliquidLC,volume,self.plate)
        elif self.volume+volume>=MINSIDEDISPENSEVOLUME:
            worklist.dispense(tipMask,well,self.bottomSideLC,volume,self.plate)
        else:
            worklist.dispense(tipMask,well,self.bottomLC,volume,self.plate)

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

        if src.hasBeads and src.plate.curloc!="Magnet":
            #print "Set %s to have beads since %s does\n"%(self.name,src.name)
            self.hasBeads=True

        self.volume=self.volume+volume
        #self.addhistory("%06x %s"%(self.getHash(w)&0xffffff,src.name),volume,tipMask)
        self.addhistory(src.name,volume,tipMask)
        self.addingredients(src,volume)

    def addhistory(self,name,vol,tip):
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
    def addallhistory(msg,addToEmpty=False,onlyplate=None,onlybeads=False):
        'Add history entry to all samples (such as # during thermocycling)'
        for s in __allsamples:
            if (onlyplate is None or onlyplate==s.plate.name) and (not onlybeads or s.hasBeads):
                if len(s.history)>0 or (s.volume>0 and msg[0]!='('):
                    s.history+=" "+msg
                elif addToEmpty:
                    s.history=msg

    @staticmethod
    def shaken(plate,speed):
        'Called after shaking to mark all samples as mixed'
        for s in __allsamples:
            if plate==s.plate.name and s.volume>0:
                if not s.wellMixed:
                    (minx,maxx)=s.getmixspeeds()
                    s.wellMixed=speed>=minx-1
                s.lastMixed=clock.elapsed()

    @staticmethod
    def notMixed(plate):
        'Called after thermocycling to mark all samples as unmixed (since they have condensation)'
        for s in __allsamples:
            if plate==s.plate.name and s.volume>0:
                s.lastMixed=None
                # Don't set wellMixed to false though -- if it was well mixed before, then any shaking will bring down condensation and it should be well mixed
                #s.wellMixed=False

    def addingredients(self,src,vol):
        'Update ingredients by adding ingredients from src'
        for k in src.ingredients:
            if src.plate.curloc=="Magnet" and k=='BIND-UNUSED':
                pass  # Wasn't transferred
            else:
                addition=src.ingredients[k]/src.volume*vol
                if k in self.ingredients:
                    self.ingredients[k]+=addition
                else:
                    self.ingredients[k]=addition

    def glycerolfrac(self):
        'Return fraction of sample that is Glycerol'
        if not 'glycerol' in self.ingredients:
            return 0.0
        total=sum([v for v in self.ingredients.values()])
        return self.ingredients['glycerol']/total

    def getmixspeeds(self):
        'Get minimum, maximum speed for mixing this sample'
        if self.isMixed():
            minspeed=0
        else:
            minspeed=interpolate(self.plate.minspeeds,self.volume)
            if minspeed is None:
                assumeSpeed=1900
                logging.notice("No shaker min speed data for volume of %.0f ul, assuming %.0f rpm"%(self.volume,assumeSpeed))
                minspeed=assumeSpeed

        maxspeed=interpolate(self.plate.maxspeeds,self.volume)
        glycerol=self.glycerolfrac()
        if glycerol>0:
            gmaxspeed=interpolate(self.plate.glycerolmaxspeeds,self.volume)
            if glycerol>self.plate.glycerol:
                logging.notice("Sample %s contains %.1f%% Glycerol (more than tested of %.1f%%)"%(self.name,glycerol*100,self.plate.glycerol*100))
                maxspeed=gmaxspeed
            else:
                maxspeed=maxspeed+(gmaxspeed-maxspeed)*(glycerol/self.plate.glycerol)
            if maxspeed<minspeed:
                logging.notice("%s with %.1ful and %.1f%% glycerol has minspeed of %.0f greater than maxspeed of %.0f"%(self.name,self.volume,glycerol*100,minspeed,maxspeed))
                minspeed=maxspeed	# Glycerol presence should also reduce minspeed

        return (minspeed,maxspeed)
    
    def chooseLC(self,aspirateVolume=0):
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
                msg="Aspirate %.1f ul from %.1f ul:  height goes from %.1f to %.1f mm, gem will think initial volume is %.1ful and final height %.1f mm"%(aspirateVolume,self.volume,initheight,finalheight,initgemvolume,finalgemheight)
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
        elif self.hasBeads and self.plate.curloc=="Magnet":
            return self.beadsLC
        else:
            return self.bottomLC

        # Mix, return true if actually did a mix, false otherwise
    def mix(self,tipMask,preaspirateAir=False,nmix=4):
        if self.isMixed() and self.wellMixed:
            logging.notice( "mix() called for sample %s, which is already mixed"%self.name)
            return False
        logging.mixwarning("Pipette mixing of %s may introduce bubbles"%self.name)

        self.volcheck(tipMask,[self.well],0)

        blowvol=5
        mstr=""
        extraspace=blowvol+0.1
        if preaspirateAir:
            extraspace+=5
        mixvol=self.volume		  # -self.plate.unusableVolume;  # Can mix entire volume, if air is aspirated, it will just be dispensed first without making a bubble
        if self.volume>MAXVOLUME-extraspace:
            mixvol=MAXVOLUME-extraspace
            logging.mixwarning("Mix of %s limited to %.0f ul instead of full volume of %.0ful"%(self.name,mixvol,self.volume))
        well=[self.well if self.well!=None else 2**(tipMask-1)-1 ]
        mixprefillvol=5
        if mixvol<self.plate.unusableVolume-mixprefillvol:
            logging.notice("Not enough volume in sample %s (%.1f) to mix"%(self.name,self.volume))
            self.history+="(UNMIXED)"
            return False
        else:
            if preaspirateAir:
                # Aspirate some air to avoid mixing with excess volume aspirated into pipette from source in previous transfer
                self.aspirateAir(tipMask,5)
            if False:		# this results in losing mixprefillvol of sample which was not mixed; remainder has different concentration than planned
                worklist.aspirateNC(tipMask,well,self.inliquidLC,mixprefillvol,self.plate)
                self.volume-=mixprefillvol
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
                    if blowvol>0:
                        blowoutLC=liquidclass.LCBlowoutLD
                        worklist.aspirateNC(tipMask,well,self.airLC,(blowvol+0.1),self.plate)
                    if self.volume<30:
                        worklist.mix(tipMask,well,self.mixLC,mixvol,self.plate,nmix)
                        mstr="(MB)"
                    else:
                        for _ in range(nmix):
                            worklist.aspirateNC(tipMask,well,mixLC,mixvol,self.plate)
                            worklist.dispense(tipMask,well,mixLC,mixvol,self.plate)
                        mstr="(M@%d)"%(mixheight)
                    if blowvol>0:
                        worklist.dispense(tipMask,well,blowoutLC,blowvol,self.plate)
                        worklist.dispense(tipMask,well,liquidclass.LCDip,0.1,self.plate)

            self.volume-=MIXLOSS
            self.addhistory(mstr,-MIXLOSS,tipMask)
            self.lastMixed=clock.elapsed()
            self.wellMixed=True
            return True

    def __str__(self):
        s="%-32s "%(self.name)
        if self.conc!=None:
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
            volString="%.1f"%(self.volume)
            
        s+=" %-30s"%("(%s.%s,%s ul%s%s)"%(self.plate.name,self.plate.wellname(self.well),volString,evapString,beadString))
        hist=self.history
        trunchistory=self.plate.name!="Samples"
        if trunchistory and len(hist)>0:
            # Remove any trailing {xx} or (xx) markers from history
            wds=hist.strip().split(' ')
            for i in range(len(wds)-1,-1,-1):
                if wds[i][0]!='(' and wds[i][0]!='{':
                    hist=' '.join(wds[:i+1])
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

            print >>fd,"samps=[samps,struct('name','%s','plate','%s','well','%s','concentration','%s','history','%s','ingredients',{{%s}},'volumes',[%s],'extrainfo',[%s])];"%(s.name,s.plate,s.plate.wellname(s.well),str(s.conc),s.history,ing,ingvol,",".join(["%d"%x for x in s.extrainfo]))
        fd.close()
