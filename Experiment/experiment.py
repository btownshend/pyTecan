from __future__ import print_function

from datetime import datetime
from hashlib import md5
from pprint import pprint
from typing import Dict, Tuple, List

from . import globals
from . import worklist
from . import thermocycler
from .db import db
from .sample import Sample
from . import liquidclass
from . import reagents
from . import decklayout
from . import clock
from . import logging
from .plate import Plate
from .platelocation import PlateLocation

import sys
import subprocess
import os

# Annotation types
SampleListType = List[Sample]
mixType = Tuple[bool, bool]
brokenTips= 0

def md5sum(filename: str) -> int:
    hashval = md5()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(128 * hashval.block_size), b""):
            hashval.update(chunk)
    return hashval.hexdigest()

class Experiment(object):
    __shakerActive = False
    DITIMASK=0   # Which tips are DiTis


    RPTEXTRA=0   # Extra amount when repeat pipetting
    MAXVOLUME=200  # Maximum volume for pipetting in ul

    def __init__(self):
        """Create a new experiment"""
        self.checksum=md5sum(sys.argv[0])
        self.checksum=self.checksum[-4:]
        pyTecan=os.path.dirname(os.path.realpath(__file__))
        try:
            self.gitlabel=subprocess.check_output(["git", "describe","--always"],cwd=pyTecan).decode('latin-1').strip()
        except Exception:
            self.gitlabel=None

        db.startrun(sys.argv[0],datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),self.checksum,self.gitlabel)
        worklist.userprompt("Generated %s (%s-%s pyTecan-%s) program ID %s"%(datetime.now().ctime(),sys.argv[0],self.checksum,self.gitlabel,str(db.program)),timeout=10)
        #worklist.userprompt("The following reagent tubes should be present: %s"%Sample.getAllLocOnPlate(decklayout.REAGENTPLATE))
        epp=Sample.getAllLocOnPlate(decklayout.EPPENDORFS)
        if len(epp)>0:
            worklist.userprompt("The following eppendorf tubes should be present: %s"%epp)
        worklist.email(dest='cdsrobot@gmail.com',subject='Run started (Generate: %s) expected runtime %.0f minutes'%(datetime.now().ctime(),clock.totalTime/60.0 if clock.totalTime is not None else 0.0 ) )
        worklist.email(dest='cdsrobot@gmail.com',subject='Tecan error',onerror=1)
        self.cleanTips=0
        # self.sanitize()  # Not needed, TRP does it, also first use of tips will do this
        self.useDiTis=False
        self.tcrunning=False
        self.overrideSanitize=False   # True to not sanitize (only wash for new tips)
        self.overrideWash=False   # True to not even wash
        self.pgmStartTime=None
        self.pgmEndTime=None

        # Access TC and RIC early to be sure they are working
        thermocycler.test()

        #        worklist.periodicWash(15,4)
        if thermocycler.cycler=='PTC200':
            worklist.userprompt("Verify that PTC thermocycler lid pressure is set to correct value.")
        self.idlePgms=[]
        self.timerStartTime=[0.0]*8
        decklayout.initWellKnownSamples()
        self.addIdleProgram(self.volumeChecker)

    def volumeChecker(self,secondsAvail):
        #print("volumeChecker",secondsAvail)
        e1=clock.elapsed()
##        for r in sorted(reagents..allReagents.values(), key=lambda r: r.sample.well if r.sample is not None else -1):

        for s in sorted(Sample.allsamples(),key=lambda z: "%s.%02d"%(z.plate,z.well) if z.well is not None else ""):
            if s is None:
                continue
            if s.plate!=decklayout.REAGENTPLATE and (s.plate!=decklayout.EPPENDORFS or s.volume==0):
                # Was getting arm collided errors with PRODUCTS plate after contents removed -- zmax may be off, but just skip vol checks for now
                continue
            if s.plate==decklayout.REAGENTPLATE or s.plate==decklayout.EPPENDORFS:
                freq=3600
            else:
                freq=3600*4
            if s.lastLevelCheck is None or clock.elapsed() - s.lastLevelCheck >= freq:
                # Not too frequently
                print("Level check of", s.name)
                s.leveldetect(self.cleantip())
                s.lastLevelCheck = clock.elapsed()
            if secondsAvail-(clock.elapsed()-e1)<120:
                break   # Don't infringe on time available
        #print("volumeChecker done after %.0f seconds"%(clock.elapsed()-e1))

    def addIdleProgram(self,pgm):
        self.idlePgms.append(pgm)

    @staticmethod
    def setreagenttemp(temp: float=None):
        tracking=True
        if tracking:
            if temp is not None:
                print("Using RIC dewpoint tracking for PRODUCT and REAGENT plates, assuming dewpoint=%.1f for evaporation calculations"%globals.dewpoint)
                decklayout.REAGENTPLATE.liquidTemp=globals.dewpoint+1
                decklayout.PRODUCTPLATE.liquidTemp=globals.dewpoint+1
            else:
                pass   # Nothing to do at end
        elif temp is None:
            worklist.pyrun("RIC\\ricset.py IDLE",version=2)
            decklayout.REAGENTPLATE.liquidTemp=22.7
        else:
            worklist.variable("dewpoint",temp,userprompt="Enter dewpoint",minval=0,maxval=20)
            worklist.variable("rictemp","~dewpoint~+2")
            worklist.pyrun("RIC\\ricset.py ~rictemp~",version=2)
            decklayout.REAGENTPLATE.liquidTemp=temp+2   # Assumes that temp is the one used
#            worklist.pyrun("RIC\\ricset.py %s"%temp,version=2)

    @staticmethod
    def saveworklist(filename: str):
        worklist.saveworklist(filename)

    def savegem(self,filename: str, header=decklayout.headerfile):
        worklist.flushQueue()
        db.endrun()   # May have already been ended before waiting to turn off reagent chiller; idempotent
        worklist.comment("Completed (%s-%s)"%(sys.argv[0],self.checksum))
        worklist.flushQueue()
        worklist.savegem(header,filename)

    def savesummary(self,filename:str ,settings: Dict =None):
        # Print amount of samples needed
        fd=open(filename,"w")
        # print >>fd,"Deck layout:"
        # print >>fd,decklayout.REAGENTPLATE
        # print >>fd,decklayout.SAMPLEPLATE
        # print >>fd,decklayout.QPCRPLATE
        # print >>fd,decklayout.WATERLOC
        # print >>fd,decklayout.WASTE
        # print >>fd,decklayout.BLEACHLOC
        # print >>fd,decklayout.WASHLOC
        # print >>fd
        #print >>fd,"DiTi usage:",worklist.getDITIcnt()
        #print >>fd
        print("Generated %s (%s-%s pyTecan-%s)"%(datetime.now().ctime(),sys.argv[0],self.checksum,self.gitlabel), file=fd)
        rtime="Run time: %d (pipetting only) + %d (thermocycling only) + %d (both) = %d minutes (%.1f hours)\n"%(clock.pipetting/60.0,clock.thermotime/60, clock.pipandthermotime/60, clock.elapsed()/60, clock.elapsed()/3600.0)
        print(rtime)
        print(rtime, file=fd)
        reagents.printprep(fd)
        Sample.printallsamples("All Samples:",fd,w=worklist)
        liquidclass.LC.printalllc(fd)
        if settings is not None:
            pprint (settings,stream=fd)
        fd.close()

    def sanitize(self,nmix:int=1,deepvol:float=10,force:bool=False):
        """Deep wash including RNase-Away treatment"""
        fixedTips=(~self.DITIMASK)&15&~brokenTips
        worklist.flushQueue()
        if not force and fixedTips==self.cleanTips:
            # print no sanitize needed
            worklist.comment("Sanitize not needed cleanTips=%d"%self.cleanTips)
            return
        worklist.comment("Sanitize (cleanTips=%d)"%self.cleanTips)
        if not self.overrideWash:
            worklist.wash(fixedTips,1,2)
        fixedWells=[]
        if not self.overrideSanitize and not self.overrideWash:
            for i in range(4):
                if (fixedTips & (1<<i)) != 0:
                    fixedWells.append(i)
                    decklayout.BLEACH.addhistory("SANITIZE",0,1<<i)
            worklist.mix(fixedTips,fixedWells,decklayout.BLEACH.mixLC,200,decklayout.BLEACH.plate,nmix,False)
            worklist.wash(fixedTips,1,deepvol,True)
        self.cleanTips|=fixedTips
        
        # print "* Sanitize"
        worklist.comment(clock.statusString())

    def cleantip(self):
        """Get the mask for a clean tip, washing if needed"""
        if self.cleanTips==0:
            #worklist.wash(self.cleanTips)
            self.sanitize()
        tipMask=1
        while (self.cleanTips & tipMask)==0:
            tipMask<<=1
        self.cleanTips&=~tipMask
        return tipMask


    def multitransfer(self, volumes, src: Sample, dests: SampleListType,mix: mixType=(True,False),getDITI:bool=True,dropDITI:bool=True,ignoreContents:bool=False,extraFrac:float=0.05,allowSplit=True,lc=(None,None)):
        """Multi pipette from src to multiple dest.  mix is (src,dest) mixing -- only mix src if needed though"""
        #print "multitransfer(",volumes,",",src,",",dests,",",mix,",",getDITI,",",dropDITI,")"
        if self.tcrunning and (src.plate.location==decklayout.TCPOS or len([1 for d in dests if d.plate.location==decklayout.TCPOS])>0):
            self.waitpgm()

        if isinstance(volumes,(int,float)):
            # Same volume for each dest
            volumes=[volumes for _ in range(len(dests))]
        assert len(volumes)==len(dests)
        #        if len([d.volume for d in dests if d.conc!=None])==0:
        if len([dests[i].volume for i in range(0,len(dests)) if dests[i].conc is not None and volumes[i]>0.01])==0:
            maxval=0
        else:
            maxval=max([dests[i].volume for i in range(0,len(dests)) if dests[i].conc is not None and volumes[i] > 0.01])
            #         maxval=max([d.volume for d in dests if d.conc != None])
        #print "volumes=",[d.volume for d in dests],", conc=",[str(d.conc) for d in dests],", maxval=",maxval
        if not mix[1] and len(volumes)>1 and ( maxval<.01 or ignoreContents):
            if not allowSplit:
                vmax=sum(volumes)
            elif len(dests)>=24:
                vmax=max([sum(volumes[i::4]) for i in range(4)])
            elif len(dests)>=12:
                vmax=max([sum(volumes[i::2]) for i in range(2)])
            else:
                vmax=sum(volumes)
            if vmax*(1+extraFrac)>self.MAXVOLUME:
                #print "sum(volumes)=%.1f, MAXVOL=%.1f"%(sum(volumes),self.MAXVOLUME)
                for i in range(1,len(volumes)):
                    if sum(volumes[0:i+1])*(1+extraFrac)>self.MAXVOLUME:
                        destvol=max([d.volume for d in dests[0:i]])
                        reuseTip=destvol<=0
                        # print "Splitting multi with total volume of %.1f ul into smaller chunks < %.1f ul after %d dispenses "%(sum(volumes),self.MAXVOLUME,i),
                        # if reuseTip:
                        #     print "with tip reuse"
                        # else:
                        #     print "without tip reuse"
                        self.multitransfer(volumes[0:i],src,dests[0:i],mix,getDITI,not reuseTip,extraFrac=extraFrac,lc=lc)
                        self.multitransfer(volumes[i:],src,dests[i:],(False,mix[1]),not reuseTip,dropDITI,extraFrac=extraFrac,lc=lc)
                        return

            if mix[0] and not src.isMixed() and (src.plate.vectorName is not None):
                worklist.comment("shaking for src mix of "+src.name)
                self.shakeSamples([src])  # Need to do this before allocating a tip since washing during this will modify the tip clean states

            if self.useDiTis:
                tipMask=4
                if  getDITI:
                    ditivol=sum(volumes)*(1+extraFrac)+src.inliquidLC.multicond+src.inliquidLC.multiexcess
                    worklist.getDITI(tipMask&self.DITIMASK,min(self.MAXVOLUME,ditivol),True)
            else:
                tipMask=self.cleantip()
                
            cmt="Multi-add  %s to samples %s"%(src.name,",".join("%s[%.1f]"%(dests[i].name,volumes[i]) for i in range(len(dests))))
            #print "*",cmt
            worklist.comment(cmt)

            if mix[0] and (not src.isMixed() or not src.wellMixed):
                if src.plate.location.lihaAccess:
                    logging.notice("Forcing pipette mix of "+src.name)
                    worklist.comment("pipette mix for src mix of "+src.name)
                    src.mix(tipMask)	# Manual mix (after allocating a tip for this)

            if len(dests)>=8 and allowSplit:
                print("Running multi-tip transfer")
                worklist.flushQueue()
                worklist.comment("Multi-tip transfer of "+src.name)
                self.sanitize()   # Make sure all tips are clean
                for i in range(4):
                    tipMask=1<<i
                    src.aspirate(tipMask,sum(volumes[i::4])*(1+extraFrac),multi=True,lc=lc[0])	# Aspirate extra
                for i in range(len(dests)):
                    tipMask=1<<(i%4)
                    if volumes[i]>0.01:
                        dests[i].dispense(tipMask,volumes[i],src,lc=lc[1])
                self.cleanTips=0  # All are dirty now
                worklist.flushQueue()
                worklist.comment("Done multi-tip transfer of "+src.name)
            else:
                src.aspirate(tipMask,sum(volumes)*(1+extraFrac),multi=True,lc=lc[0])	# Aspirate extra
                for i in range(len(dests)):
                    if volumes[i]>0.01:
                        dests[i].dispense(tipMask,volumes[i],src,lc=lc[1])
                if self.useDiTis and dropDITI:
                    worklist.dropDITI(tipMask&self.DITIMASK,decklayout.WASTE)
        else:
            for i in range(len(dests)):
                if volumes[i]>0.01:
                    self.transfer(volumes[i],src,dests[i],(mix[0] and i==0,mix[1]),getDITI,dropDITI,lc=lc)

    def transfer(self, volume: float, src: Sample, dest: Sample, mix: mixType=(True,False), getDITI:bool=True, dropDITI:bool=True,multi=True,lc=(None,None)):
        if self.tcrunning and (src.plate.location==decklayout.TCPOS or dest.plate.location==decklayout.TCPOS)>0:
            self.waitpgm()

        if volume>self.MAXVOLUME:
            destvol=dest.volume
            reuseTip=destvol<=0
            msg="Splitting large transfer of %.1f ul into smaller chunks < %.1f ul "%(volume,self.MAXVOLUME)
            if reuseTip:
                msg+= "with tip reuse"
            else:
                msg+= "without tip reuse"
            logging.notice(msg)
            self.transfer(self.MAXVOLUME,src,dest,mix,getDITI,multi=False,lc=lc)   # Don't use multitransfer mode since this would reduce volume
            self.transfer(volume-self.MAXVOLUME,src,dest,(mix[0] and not reuseTip,mix[1]),dropDITI=dropDITI,multi=False,lc=lc)
            return

        cmt="Add %.1f ul of %s to %s"%(volume, src.name, dest.name)
        ditivolume=volume+src.inliquidLC.singletag
        if mix[0] and not src.isMixed():
            cmt=cmt+" with src mix"
            ditivolume=max(ditivolume,src.volume)
        if mix[1] and dest.volume>0 and not src.isMixed():
            cmt=cmt+" with dest mix"
            ditivolume=max(ditivolume,volume+dest.volume)
            #            print "Mix volume=%.1f ul"%(ditivolume)
        if mix[0] and not src.isMixed() and (src.plate.location.vectorName is not None):
            worklist.comment("shaking for src mix of "+src.name)
            self.shakeSamples([src])  # Need to do this before allocating a tip since washing during this will modify the tip clean states

        if self.useDiTis:
            tipMask=4
            if getDITI:
                worklist.getDITI(tipMask&self.DITIMASK,ditivolume)
        else:
            tipMask=self.cleantip()
        #print "*",cmt
        worklist.comment(cmt)

        if mix[0] and (not src.isMixed() or not src.wellMixed):
            if src.plate.location.lihaAccess:
                logging.notice("Forcing pipette mix of "+src.name)
                worklist.comment("pipette mix for src mix of "+src.name)
                src.mix(tipMask)	# Manual mix (after allocating a tip for this)
            
        src.aspirate(tipMask,volume,lc=lc[0],multi=multi)
        dest.dispense(tipMask,volume,src,lc=lc[1])
        if mix[1]:
            dest.mix(tipMask,True)

        if self.useDiTis and dropDITI:
            worklist.dropDITI(tipMask&self.DITIMASK,decklayout.WASTE)

    # Mix
    def mix(self, src:Sample, nmix:int=4):
        if self.tcrunning and src.plate.location==decklayout.TCPOS:
            self.waitpgm()

        cmt="Mix %s" % src.name
        tipMask=self.cleantip()
        worklist.comment(cmt)
        src.lastMixed=None	# Force a mix
        src.mix(tipMask,False,nmix=nmix)

    def dispose(self, volume:float, src:Sample,  mix:bool=False, getDITI:bool=True, dropDITI:bool=True):
        """Dispose of a given volume by aspirating and not dispensing (will go to waste during next wash)"""
        if self.tcrunning and src.plate.location==decklayout.TCPOS:
            self.waitpgm()
        if volume>self.MAXVOLUME:
            reuseTip=False   # Since we need to wash to get rid of it
            msg="Splitting large transfer of %.1f ul into smaller chunks < %.1f ul "%(volume,self.MAXVOLUME),
            if reuseTip:
                msg+= "with tip reuse"
            else:
                msg+= "without tip reuse"
            logging.notice(msg)
            self.dispose(self.MAXVOLUME,src,mix,getDITI,dropDITI)
            self.dispose(volume-self.MAXVOLUME,src,False,getDITI,dropDITI)
            return

        cmt="Remove and dispose of %.1f ul from %s"%(volume, src.name)
        ditivolume=volume+src.inliquidLC.singletag
        if mix and not src.isMixed():
            cmt=cmt+" with src mix"
            ditivolume=max(ditivolume,src.volume)
        if self.useDiTis:
            tipMask=4
            if getDITI:
                worklist.getDITI(tipMask&self.DITIMASK,ditivolume)
        else:
            tipMask=self.cleantip()
        #print "*",cmt
        worklist.comment(cmt)

        if mix and not src.isMixed():
            src.mix(tipMask)
        src.aspirate(tipMask,volume,multi=False)

        if self.useDiTis and dropDITI:
            worklist.dropDITI(tipMask&self.DITIMASK,decklayout.WASTE)

    # noinspection PyShadowingNames
    def stage(self,stagename:str,reagents: SampleListType,sources: SampleListType,samples: SampleListType,volume,finalx:float =1.0,destMix:bool=True,dilutant: Sample=None):
        # Add water to sample wells as needed (multi)
        # Pipette reagents into sample wells (multi)
        # Pipette sources into sample wells
        # Concs are in x (>=1)

        # Sample.printallsamples("Before "+stagename)
        # print "\nStage: ", stagename, "reagents=",[str(r) for r in reagents], ",sources=",[str(s) for s in sources],",samples=",[str(s) for s in samples],str(volume)

        if len(samples)==0:
            logging.notice("No samples")
            return

        if dilutant is None:
            dilutant=decklayout.WATER

        worklist.flushQueue()
        worklist.comment("Stage: "+stagename)
        if not isinstance(volume,list):
            volume=[volume for _ in range(len(samples))]
        assert all([v>0 for v in volume])
        volume=[float(v) for v in volume]

        reagentvols=[1.0/x.conc.dilutionneeded()*finalx for x in reagents]
        sourcevols=[]
        if len(sources)>0:
            sourcevols=[volume[i]*1.0/sources[i].conc.dilutionneeded()*finalx for i in range(len(sources))]
            while len(sourcevols)<len(samples):
                sourcevols.append(0)
            watervols=[volume[i]*(1-sum(reagentvols))-samples[i].volume-sourcevols[i] for i in range(len(samples))]
        else:
            watervols=[volume[i]*(1-sum(reagentvols))-samples[i].volume for i in range(len(samples))]

        if min(watervols)<-0.01:
            msg="Error: Ingredients add up to more than desired volume by %.1f ul"%(-min(watervols))
            for s in samples:
                if s.volume>0:
                    msg=msg+" Note: %s already contains %.1f ul\n"%(s.name,s.volume)
            logging.error(msg)

        watervols2=[w if w<=2 else 0 for w in watervols]   # Move later since volume is low
        watervols=[w if w>2 else 0 for w in watervols]  # Only move>=2 at beginning
        if any([w>0.01 for w in watervols]):
            self.multitransfer(watervols,dilutant,samples,(False,destMix and (len(reagents)+len(sources)==0)))

        for i in range(len(reagents)):
            self.multitransfer([reagentvols[i]*v for v in volume],reagents[i],samples,(True,destMix and (len(sources)==0 and i==len(reagents)-1)))

        if any([w>0.01 for w in watervols2]):
            self.multitransfer(watervols2,dilutant,samples,(False,destMix and (len(reagents)+len(sources)==0)))

        if len(sources)>0:
            assert len(sources)<=len(samples)
            for i in range(len(sources)):
                self.transfer(sourcevols[i],sources[i],samples[i],(True,destMix))


    @staticmethod
    def lihahome():
        """Move LiHa to left of deck"""
        worklist.moveliha(decklayout.WASHLOC)

    def runpgm(self,plate:Plate, pgm: str,duration:float,waitForCompletion:bool=True,volume:float=10):
        if self.tcrunning:
            logging.error("Attempt to start a progam on TC when it is already running")
        if len(pgm)>8:
            logging.error("TC program name (%s) too long (max is 8 char)"%pgm)
        # move to thermocycler
        worklist.flushQueue()
        # Make sure email on error is set (in case program restarted in the middle)
        worklist.email(dest='cdsrobot@gmail.com',subject='Tecan error',onerror=1)
        self.lihahome()
        cmt="run %s"%pgm
        worklist.comment(cmt)
        #print "*",cmt
        thermocycler.lid(1)
        self.moveplate(plate,decklayout.TCPOS)
        worklist.vector("Hotel 1 Lid",decklayout.HOTELPOS,worklist.SAFETOEND,True,worklist.DONOTMOVE,worklist.CLOSE)
        worklist.vector("%slid"%thermocycler.cycler,decklayout.TCPOS,worklist.SAFETOEND,True,worklist.DONOTMOVE,worklist.OPEN)
        worklist.romahome()
        thermocycler.lid(0)
        #        pgm="PAUSE30"  # For debugging
        thermocycler.run(pgm,volume)
        self.pgmStartTime=clock.pipetting
        self.pgmEndTime=duration*60+clock.pipetting
        self.tcrunning=True
        Sample.addallhistory("{%s}" % pgm, addToEmpty=False, onlyplate=decklayout.SAMPLEPLATE.name, htype="tc")
        if waitForCompletion:
            self.waitpgm()

    def moveplate(self,plate:Plate,dest:PlateLocation,returnHome:bool=True):
        if self.tcrunning and plate.location==decklayout.TCPOS:
            self.waitpgm()

        # move to given destination (one of "Home","Magnet","Shaker","TC" )
        if dest is None:
            logging.error("Home location for plates no longer supported")
            #dest=plate.homeLocation
        if plate.location.vectorName is None:
            logging.error("moveplate: Attempt to move plate %s from %s, which doesn't have a vector"%(plate.name,plate.location))
        if dest.vectorName is None:
            logging.error("moveplate: Attempt to move plate %s to %s, which doesn't have a vector"%(plate.name,dest))

        occ=Plate.lookupLocation(dest)
        if occ==plate:
            logging.warning("moveplate: Attempt to move plate %s to %s, which is already there"%(plate.name,dest))
        elif occ is not None and occ.location.name==dest.name:
            logging.error("moveplate: Attempt to move plate %s to %s, which is already occupied by %s"%(plate.name,dest,occ))

        # print("Move plate %s from %s to %s"%(plate.name,plate.location,destLoc))
        worklist.flushQueue()
        self.lihahome()
        cmt="moveplate %s %s"%(plate.name,dest)
        worklist.comment(cmt)
        worklist.vector(None,plate.location,worklist.SAFETOEND,True,worklist.DONOTMOVE,worklist.CLOSE)
        plate.movetoloc(dest)
        worklist.vector(None,dest,worklist.SAFETOEND,True,worklist.DONOTMOVE,worklist.OPEN)

        #Sample.addallhistory("{->%s}"%dest,onlyplate=plate.name)
        if returnHome:
            worklist.romahome()

    def shakeSamples(self,samples:SampleListType,dur:float=60,speed:float=None,accel:float=10,returnPlate:bool=True):
        """Shake plates if any of the given samples are on that plate and  needs mixing"""
        if self.tcrunning and any([s.plate.location==decklayout.TCPOS for s in samples]):
            self.waitpgm()

        for p in set([s.plate for s in samples if not s.isMixed()  ]):
            if p.plateType.maxspeeds is not None:
                self.shake(p,returnPlate=returnPlate,speed=speed,samps=[s for s in samples if s.plate==p],dur=dur,accel=accel)

    def shake(self,plate:Plate, dur:float=60,speed:float=None,accel:float=10,returnPlate:bool=True,samps: SampleListType=None,force: bool=False):
        if self.tcrunning and plate.location==decklayout.TCPOS:
            self.waitpgm()

        # Move the plate to the shaker, run for the given time, and bring plate back
        allsamps=Sample.getAllOnPlate(plate)
        if samps is None:
            samps=allsamps

        if all([x.isMixed() for x in samps]) and not force:
            logging.notice( "No need to shake "+plate.name+", but doing so anyway.")

        minspeed=0
        maxspeed=2000
        for x in samps:
            (a,b)=x.getmixspeeds()
            minspeed=max([a,minspeed])
        for x in allsamps:
            (a,b)=x.getmixspeeds()
            maxspeed=min([b,maxspeed])
            
        if speed is None:
            if minspeed<maxspeed:
                speed=max((maxspeed+minspeed)/2,maxspeed-50)    # Mix as fast as safely possible (but always above minspeed)
            else:
                speed=maxspeed

        if speed<minspeed-2 or speed>maxspeed+2:
            others=""
            for x in allsamps:
                (a,b)=x.getmixspeeds()
                if b==speed or (a>speed and not x.isMixed() and x in samps):
                    if a is not None and a>0:
                        others+=" {%s: %.1ful,G=%.2f%%,min=%.0f,max=%.0f}"%(x.name,x.volume,x.glycerolfrac()*100,a,b)
                    else:
                        others+=" {%s: %.1ful,G=%.2f%%,max=%.0f}"%(x.name,x.volume,x.glycerolfrac()*100,b)
            logging.mixwarning("Mixing %s at %.0f RPM; < minspeed(%.0f)  or > maxspeed(%.0f), limits=[%s]"%(plate.name,speed,minspeed,maxspeed,others))
        else:
            logging.notice("Mixing %s at %.0f RPM ( min RPM=%.0f, max RPM=%.f)"%(plate.name, speed, minspeed, maxspeed))
            
        oldloc=plate.location
        self.moveplate(plate,decklayout.SHAKERPLATELOC,returnHome=False)

        Experiment.__shakerActive=True
        worklist.pyrun("BioShake\\bioexec.py setElmLockPos",version=2)
        worklist.pyrun("BioShake\\bioexec.py setShakeTargetSpeed%.0f"%speed,version=2)
        worklist.pyrun("BioShake\\bioexec.py setShakeAcceleration%d"%accel,version=2)
        worklist.pyrun("BioShake\\bioexec.py shakeOn",version=2)
        self.starttimer()
        Sample.shaken(plate.name,speed)
        Sample.addallhistory("(S%d@%.0f)" % (dur,speed), onlyplate=plate.name, htype="shake")
        self.waittimer(dur)
        worklist.pyrun("BioShake\\bioexec.py shakeOff",version=2)
        self.starttimer()
        self.waittimer(accel+1)
        worklist.pyrun("BioShake\\bioexec.py setElmUnlockPos",version=2)
        Experiment.__shakerActive=False
        if returnPlate:
            self.moveplate(plate,oldloc)

    @staticmethod
    def shakerIsActive() -> bool:
        return Experiment.__shakerActive

    def starttimer(self,timer:int=1):
        self.timerStartTime[timer]=clock.pipetting
        worklist.starttimer(timer)

    def waittimer(self,duration:float,timer:int=1):
        if self.timerStartTime[timer]+duration-clock.pipetting > 20:
            # Might as well sanitize while we're waiting
            self.sanitize()
        if duration>0:
            worklist.waittimer(duration,timer)
            #Sample.addallhistory("{%ds}"%duration)

    def pause(self,duration:float):
        self.starttimer()
        self.waittimer(duration)
        Sample.addallhistory("(%ds)" % duration, htype="pause")

    def waitpgm(self, sanitize:bool=True):
        if not self.tcrunning:
            return
        #print "* Wait for TC to finish"

        worklist.comment("Wait for TC")
        while self.pgmEndTime-clock.pipetting > 120:
            # Run any idle programs
            oldElapsed=clock.pipetting
            for ip in self.idlePgms:
                if self.pgmEndTime-clock.pipetting > 120:
                    #print "Executing idle program with %.0f seconds"%(self.pgmEndTime-clock.pipetting)
                    ip(self.pgmEndTime-clock.pipetting-120)
            if oldElapsed==clock.pipetting:
                # Nothing was done
                break
            worklist.flushQueue()		# Just in case

        if sanitize:
            self.sanitize()   # Sanitize tips before waiting for this to be done

        clock.pipandthermotime+=(clock.pipetting-self.pgmStartTime)
        clock.thermotime+=(self.pgmEndTime-clock.pipetting)
        clock.pipetting=self.pgmStartTime

        #print "Waiting for TC with %.0f seconds expected to remain"%(self.pgmEndTime-clock.pipetting)
        self.lihahome()
        thermocycler.wait()
        thermocycler.lid(1)
        #        worklist.pyrun('PTC\\ptcrun.py %s CALC ON'%"COOLDOWN")
        #        thermocycler.wait()
        worklist.vector("%slid"%thermocycler.cycler,decklayout.TCPOS,worklist.SAFETOEND,True,worklist.DONOTMOVE,worklist.CLOSE)
        worklist.vector("Hotel 1 Lid",decklayout.HOTELPOS,worklist.SAFETOEND,True,worklist.DONOTMOVE,worklist.OPEN)

        if thermocycler.cycler=='PTC200':
            worklist.vector("PTC200WigglePos",decklayout.TCPOS,worklist.SAFETOEND,False,worklist.DONOTMOVE,worklist.DONOTMOVE)
            worklist.vector("PTC200Wiggle",decklayout.TCPOS,worklist.SAFETOEND,False,worklist.DONOTMOVE,worklist.CLOSE,True)
            worklist.vector("PTC200Wiggle",decklayout.TCPOS,worklist.ENDTOSAFE,False,worklist.DONOTMOVE,worklist.OPEN,True)
            worklist.vector("PTC200WigglePos",decklayout.TCPOS,worklist.ENDTOSAFE,False,worklist.DONOTMOVE,worklist.DONOTMOVE)

            worklist.vector("PTC200Wiggle2Pos",decklayout.TCPOS,worklist.SAFETOEND,False,worklist.DONOTMOVE,worklist.DONOTMOVE)
            worklist.vector("PTC200Wiggle2",decklayout.TCPOS,worklist.SAFETOEND,False,worklist.DONOTMOVE,worklist.CLOSE,True)
            worklist.vector("PTC200Wiggle2",decklayout.TCPOS,worklist.ENDTOSAFE,False,worklist.DONOTMOVE,worklist.OPEN,True)
            worklist.vector("PTC200Wiggle2Pos",decklayout.TCPOS,worklist.ENDTOSAFE,False,worklist.DONOTMOVE,worklist.DONOTMOVE)

            worklist.vector("PTC200WigglePos",decklayout.TCPOS,worklist.SAFETOEND,False,worklist.DONOTMOVE,worklist.DONOTMOVE)
            worklist.vector("PTC200Wiggle",decklayout.TCPOS,worklist.SAFETOEND,False,worklist.DONOTMOVE,worklist.CLOSE,True)
            worklist.vector("PTC200Wiggle",decklayout.TCPOS,worklist.ENDTOSAFE,False,worklist.DONOTMOVE,worklist.OPEN,True)
            worklist.vector("PTC200WigglePos",decklayout.TCPOS,worklist.ENDTOSAFE,False,worklist.DONOTMOVE,worklist.DONOTMOVE)

        self.tcrunning=False
        self.moveplate(decklayout.SAMPLEPLATE,decklayout.SAMPLELOC)  # Move HOME
        # Mark all samples on plate as unmixed (due to condensation)
        Sample.notMixed(decklayout.SAMPLEPLATE.name)
        if thermocycler.cycler=='PTC200':
            # Verify plate is in place
            worklist.vector(None,decklayout.SAMPLELOC,worklist.SAFETOEND,False,worklist.DONOTMOVE,worklist.CLOSE)
            worklist.vector(None,decklayout.SAMPLELOC,worklist.ENDTOSAFE,False,worklist.OPEN,worklist.DONOTMOVE)
        worklist.romahome()
        #worklist.userprompt("Plate should be back on deck. Press return to continue")
        # Wash tips again to remove any drips that may have formed while waiting for TC
        worklist.wash(15&~brokenTips,1,5,True)


    @staticmethod
    def dilute(samples: SampleListType, factor:float):
        if isinstance(factor,list):
            assert len(samples)==len(factor)
            for i in range(len(samples)):
                samples[i].dilute(factor[i])
        else:
            for s in samples:
                s.dilute(factor)
