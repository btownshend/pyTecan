from datetime import datetime

import worklist
from sample import Sample
import liquidclass
import reagents
import decklayout
import clock
import globals
import logging

_Experiment__shakerActive = False

class Experiment(object):
    DITIMASK=0   # Which tips are DiTis

    RPTEXTRA=0   # Extra amount when repeat pipetting
    MAXVOLUME=200  # Maximum volume for pipetting in ul

    def __init__(self):
        'Create a new experiment with given sample locations for water and WASTE;  totalTime is expected run time in seconds, if known'
        worklist.comment("Generated %s"%(datetime.now().ctime()))
        worklist.userprompt("The following reagent tubes should be present: %s"%Sample.getAllLocOnPlate(decklayout.REAGENTPLATE))
        worklist.userprompt("The following eppendorf tubes should be present: %s"%Sample.getAllLocOnPlate(decklayout.EPPENDORFS))
        worklist.email(dest='cdsrobot@gmail.com',subject='Run started (Generate: %s)'%(datetime.now().ctime()))
        worklist.email(dest='cdsrobot@gmail.com',subject='Tecan error',onerror=1)
        self.cleanTips=0
        # self.sanitize()  # Not needed, TRP does it, also first use of tips will do this
        self.useDiTis=False
        self.ptcrunning=False
        self.overrideSanitize=False
        self.pgmStartTime=None
        self.pgmEndTime=None

        # Access PTC and RIC early to be sure they are working
        worklist.pyrun("PTC\\ptctest.py")
        #        worklist.periodicWash(15,4)
        worklist.userprompt("Verify that PTC thermocycler lid pressure is set to '2'.")
        self.idlePgms=[]
        self.timerStartTime=[None]*8

    def addIdleProgram(self,pgm):
        self.idlePgms.append(pgm)

    def setreagenttemp(self,temp=None):
        if temp is None:
            worklist.pyrun("RIC\\ricset.py IDLE")
            decklayout.REAGENTPLATE.liquidTemp=22.7
        else:
            worklist.variable("dewpoint",temp,userprompt="Enter dewpoint",minval=0,maxval=20)
            worklist.variable("rictemp","~dewpoint~+2")
            worklist.pyrun("RIC\\ricset.py ~rictemp~")
            decklayout.REAGENTPLATE.liquidTemp=temp+2   # Assumes that temp is the one used
#            worklist.pyrun("RIC\\ricset.py %s"%temp)

    def saveworklist(self,filename):
        worklist.saveworklist(filename)

    def savegem(self,filename):
        worklist.flushQueue()
        worklist.savegem(decklayout.headerfile,filename)

    def savesummary(self,filename):
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

        rtime="Run time: %d (pipetting only) + %d (thermocycling only) + %d (both) = %d minutes\n"%(clock.pipetting/60.0,clock.thermotime/60, clock.pipandthermotime/60, clock.elapsed()/60)
        print rtime
        print >>fd,rtime
        reagents.printprep(fd)
        Sample.printallsamples("All Samples:",fd,w=worklist)
        liquidclass.LC.printalllc("All LC:",fd)
        fd.close()

    def sanitize(self,nmix=1,deepvol=20,force=False):
        'Deep wash including RNase-Away treatment'
        fixedTips=(~self.DITIMASK)&15
        worklist.flushQueue()
        if not force and fixedTips==self.cleanTips:
            # print no sanitize needed
            worklist.comment("Sanitize not needed cleanTips=%d"%self.cleanTips)
            return
        worklist.comment("Sanitize (cleanTips=%d)"%self.cleanTips)
        worklist.wash(15,1,2)
        fixedWells=[]
        if not self.overrideSanitize:
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
        'Get the mask for a clean tip, washing if needed'
        if self.cleanTips==0:
            #worklist.wash(self.cleanTips)
            self.sanitize()
        tipMask=1
        while (self.cleanTips & tipMask)==0:
            tipMask<<=1
        self.cleanTips&=~tipMask
        return tipMask

    def multitransfer(self, volumes, src, dests,mix=(True,False),getDITI=True,dropDITI=True,ignoreContents=False,extraFrac=0.05):
        'Multi pipette from src to multiple dest.  mix is (src,dest) mixing -- only mix src if needed though'
        #print "multitransfer(",volumes,",",src,",",dests,",",mix,",",getDITI,",",dropDITI,")"
        if self.ptcrunning and (src.plate==decklayout.SAMPLEPLATE or len([1 for d in dests if d.plate==decklayout.SAMPLEPLATE])>0):
            self.waitpgm()

        if isinstance(volumes,(int,long,float)):
            # Same volume for each dest
            volumes=[volumes for i in range(len(dests))]
        assert len(volumes)==len(dests)
        #        if len([d.volume for d in dests if d.conc!=None])==0:
        if len([dests[i].volume for i in range(0,len(dests)) if dests[i].conc != None and volumes[i]>0.01])==0:
            maxval=0
        else:
            maxval=max([dests[i].volume for i in range(0,len(dests)) if dests[i].conc != None and volumes[i]>0.01])
            #         maxval=max([d.volume for d in dests if d.conc != None])
        #print "volumes=",[d.volume for d in dests],", conc=",[str(d.conc) for d in dests],", maxval=",maxval
        if not mix[1] and len(volumes)>1 and ( maxval<.01 or ignoreContents):
            if sum(volumes)*(1+extraFrac)>self.MAXVOLUME:
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
                        self.multitransfer(volumes[0:i],src,dests[0:i],mix,getDITI,not reuseTip,extraFrac=extraFrac)
                        self.multitransfer(volumes[i:],src,dests[i:],(False,mix[1]),not reuseTip,dropDITI,extraFrac=extraFrac)
                        return

            if self.useDiTis:
                tipMask=4
                if  getDITI:
                    ditivol=sum(volumes)*(1+extraFrac)+src.inliquidLC.multicond+src.inliquidLC.multiexcess
                    worklist.getDITI(tipMask&self.DITIMASK,min(self.MAXVOLUME,ditivol),True,True)
            else:
                tipMask=self.cleantip()

            cmt="Multi-add  %s to samples %s"%(src.name,",".join("%s[%.1f]"%(dests[i].name,volumes[i]) for i in range(len(dests))))
            #print "*",cmt
            worklist.comment(cmt)

            if mix[0] and not src.isMixed():
                if src.plate==decklayout.SAMPLEPLATE or src.plate==decklayout.DILPLATE:
                    self.shakeSamples([src])
                else:
                    src.mix(tipMask)
            src.aspirate(tipMask,sum(volumes)*(1+extraFrac),True)	# Aspirate extra
            for i in range(len(dests)):
                if volumes[i]>0.01:
                    dests[i].dispense(tipMask,volumes[i],src)
            if self.useDiTis and dropDITI:
                worklist.dropDITI(tipMask&self.DITIMASK,decklayout.WASTE)
        else:
            for i in range(len(dests)):
                if volumes[i]>0.01:
                    self.transfer(volumes[i],src,dests[i],(mix[0] and i==0,mix[1]),getDITI,dropDITI)

    def transfer(self, volume, src, dest, mix=(True,False), getDITI=True, dropDITI=True):
        if self.ptcrunning and (src.plate==decklayout.SAMPLEPLATE or dest.plate==decklayout.SAMPLEPLATE)>0:
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
            self.transfer(self.MAXVOLUME,src,dest,mix,getDITI,False)
            self.transfer(volume-self.MAXVOLUME,src,dest,(mix[0] and not reuseTip,mix[1]),False,dropDITI)
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
        if self.useDiTis:
            tipMask=4
            if getDITI:
                worklist.getDITI(tipMask&self.DITIMASK,ditivolume)
        else:
            tipMask=self.cleantip()
        #print "*",cmt
        worklist.comment(cmt)

        if mix[0] and not src.isMixed():
            if src.plate==decklayout.SAMPLEPLATE or src.plate==decklayout.DILPLATE:
                self.shakeSamples([src])
            else:
                src.mix(tipMask)
        src.aspirate(tipMask,volume)
        dest.dispense(tipMask,volume,src)
        if mix[1]:
            dest.mix(tipMask,True)

        if self.useDiTis and dropDITI:
            worklist.dropDITI(tipMask&self.DITIMASK,decklayout.WASTE)

    # Mix
    def mix(self, src, nmix=4):
        if self.ptcrunning and src.plate==decklayout.SAMPLEPLATE:
            self.waitpgm()

        cmt="Mix %s"%(src.name)
        tipMask=self.cleantip()
        worklist.comment(cmt)
        src.lastMixed=None	# Force a mix
        src.mix(tipMask,False,nmix=nmix)

    def dispose(self, volume, src,  mix=False, getDITI=True, dropDITI=True):
        'Dispose of a given volume by aspirating and not dispensing (will go to waste during next wash)'
        if self.ptcrunning and src.plate==decklayout.SAMPLEPLATE:
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
        src.aspirate(tipMask,volume)

        if self.useDiTis and dropDITI:
            worklist.dropDITI(tipMask&self.DITIMASK,decklayout.WASTE)

    def stage(self,stagename,reagents,sources,samples,volume,finalx=1.0,destMix=True,dilutant=None):
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

        worklist.comment("Stage: "+stagename)
        if not isinstance(volume,list):
            volume=[volume for i in range(len(samples))]
        for i in range(len(volume)):
            assert volume[i]>0
            volume[i]=float(volume[i])

        reagentvols=[1.0/x.conc.dilutionneeded()*finalx for x in reagents]
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

        if sum(watervols)>0.01:
            self.multitransfer(watervols,dilutant,samples,(False,destMix and (len(reagents)+len(sources)==0)))

        for i in range(len(reagents)):
            self.multitransfer([reagentvols[i]*v for v in volume],reagents[i],samples,(True,destMix and (len(sources)==0 and i==len(reagents)-1)))

        if len(sources)>0:
            assert len(sources)<=len(samples)
            for i in range(len(sources)):
                self.transfer(sourcevols[i],sources[i],samples[i],(True,destMix))


    def lihahome(self):
        'Move LiHa to left of deck'
        worklist.moveliha(decklayout.WASHLOC)

    def runpgm(self,pgm,duration,waitForCompletion=True,volume=10,hotlidmode="TRACKING",hotlidtemp=1):
        if self.ptcrunning:
            logging.error("Attempt to start a progam on PTC when it is already running")
        if len(pgm)>8:
            logging.error("PTC program name (%s) too long (max is 8 char)"%pgm)
        # move to thermocycler
        worklist.flushQueue()
        self.lihahome()
        cmt="run %s"%pgm
        worklist.comment(cmt)
        #print "*",cmt
        worklist.pyrun("PTC\\ptclid.py OPEN")
        self.moveplate(decklayout.SAMPLEPLATE,"PTC")
        worklist.vector("Hotel 1 Lid",decklayout.HOTELPOS,worklist.SAFETOEND,True,worklist.DONOTMOVE,worklist.CLOSE)
        worklist.vector("PTC200lid",decklayout.PTCPOS,worklist.SAFETOEND,True,worklist.DONOTMOVE,worklist.OPEN)
        worklist.romahome()
        worklist.pyrun("PTC\\ptclid.py CLOSE")
        #        pgm="PAUSE30"  # For debugging
        assert hotlidmode=="TRACKING" or hotlidmode=="CONSTANT"
        assert (hotlidmode=="TRACKING" and hotlidtemp>=0 and hotlidtemp<=45) or (hotlidmode=="CONSTANT" and hotlidtemp>30)
        worklist.pyrun('PTC\\ptcrun.py %s CALC %s,%d %d'%(pgm,hotlidmode,hotlidtemp,volume))
        self.pgmStartTime=clock.pipetting
        self.pgmEndTime=duration*60+clock.pipetting
        self.ptcrunning=True
        Sample.addallhistory("{%s}"%pgm,addToEmpty=False,onlyplate=decklayout.SAMPLEPLATE.name)
        if waitForCompletion:
            self.waitpgm()

    def moveplate(self,plate,dest="Home",returnHome=True):
        if self.ptcrunning and plate==decklayout.SAMPLEPLATE:
            self.waitpgm()

        # move to given destination (one of "Home","Magnet","Shaker","PTC" )
        if plate!=decklayout.SAMPLEPLATE and plate!=decklayout.DILPLATE:
            logging.error("Only able to move %s or %s plates, not %s"%(decklayout.SAMPLEPLATE.name,decklayout.DILPLATE.name,plate.name))

        if plate.curloc==dest:
            #print "Plate %s is already at %s"%(plate.name,dest)
            return

        #print "Move plate %s from %s to %s"%(plate.name,plate.curloc,dest)
        worklist.flushQueue()
        self.lihahome()
        cmt="moveplate %s %s"%(plate.name,dest)
        worklist.comment(cmt)
        if plate.curloc=="Home":
            worklist.vector(plate.vectorName,plate,worklist.SAFETOEND,True,worklist.DONOTMOVE,worklist.CLOSE)
        elif plate.curloc=="Magnet":
            worklist.vector("Magplate",decklayout.MAGPLATELOC,worklist.SAFETOEND,True,worklist.DONOTMOVE,worklist.CLOSE)
        elif plate.curloc=="Shaker":
            worklist.vector("Shaker",decklayout.SHAKERPLATELOC,worklist.SAFETOEND,True,worklist.DONOTMOVE,worklist.CLOSE)
        elif plate.curloc=="PTC":
            worklist.vector("PTC200",decklayout.PTCPOS,worklist.SAFETOEND,True,worklist.DONOTMOVE,worklist.CLOSE)
        else:
            logging.error("Plate %s is in unknown location: %s"%(plate.name,plate.curloc))

        if dest=="Home":
            plate.movetoloc(dest)
            worklist.vector(plate.vectorName,plate,worklist.SAFETOEND,True,worklist.DONOTMOVE,worklist.OPEN)
        elif dest=="Magnet":
            plate.movetoloc(dest,decklayout.MAGPLATELOC)
            worklist.vector("Magplate",decklayout.MAGPLATELOC,worklist.SAFETOEND,True,worklist.DONOTMOVE,worklist.OPEN)
        elif dest=="Shaker":
            plate.movetoloc(dest,decklayout.SHAKERPLATELOC)
            worklist.vector("Shaker",decklayout.SHAKERPLATELOC,worklist.SAFETOEND,True,worklist.DONOTMOVE,worklist.OPEN)
        elif dest=="PTC":
            plate.movetoloc(dest,decklayout.PTCPOS)
            worklist.vector("PTC200",decklayout.PTCPOS,worklist.SAFETOEND,True,worklist.DONOTMOVE,worklist.OPEN)
        else:
            logging.error("Attempt to move plate %s to unknown location: %s"%(plate.name,dest))

        Sample.addallhistory("{->%s}"%dest,onlyplate=plate.name)
        if returnHome:
            worklist.romahome()

    def shakeSamples(self,samples,dur=60,speed=None,accel=5,returnPlate=True):
        "Shake plates if any of the given samples are on that plate and  needs mixing"
        if self.ptcrunning and any([s.plate==decklayout.SAMPLEPLATE for s in samples]):
            self.waitpgm()

        for p in set([s.plate for s in samples if not s.isMixed()  ]):
            if p.maxspeeds is not None:
                self.shake(p,returnPlate=returnPlate,speed=speed,samps=[s for s in samples if s.plate==p],dur=dur,accel=accel)

    def shake(self,plate,dur=60,speed=None,accel=5,returnPlate=True,samps=None):
        if self.ptcrunning and plate==decklayout.SAMPLEPLATE:
            self.waitpgm()

        # Move the plate to the shaker, run for the given time, and bring plate back
        allsamps=Sample.getAllOnPlate(plate)
        if samps is None:
            samps=allsamps
            
        if all([x.isMixed() for x in samps]):
            logging.notice( "No need to shake "+plate.name+", but doing so anyway.")
            
        maxvol=max([x.volume for x in allsamps])
        minvol=min([x.volume for x in samps if not x.isMixed() ]+[200])
        (minspeed,maxspeed)=plate.getmixspeeds(minvol*0.95,maxvol+5)	# Assume volumes could be off

        if minspeed>maxspeed:
            logging.warning("minspeed(%.0f) > maxspeed(%.0f)"%(minspeed,maxspeed))
        if speed is None:
            if minspeed<maxspeed:
                speed=(maxspeed+minspeed)/2
            else:
                speed=maxspeed

        warned=False

        if speed>maxspeed:
            msg="%s plate contains wells with up to %.2f ul, which may spill at %d RPM: "%(plate.name, maxvol, speed),
            for x in samps:
                tmp=plate.getmixspeeds(x.volume,x.volume)
                if tmp[1]<speed:
                    msg+="%s[%.1ful, max=%.0f RPM] "%(x.name,x.volume,tmp[1]),
            warned=True
            logging.warning(msg)
            
        if globals.verbose and speed<minspeed:
            msg="%s plate contains unmixed wells that may not be mixed at %d RPM: "%(plate.name, speed),
            for x in samps:
                if x.isMixed():
                    continue
                tmp=plate.getmixspeeds(x.volume*0.95,x.volume+5)
                if speed<tmp[0]:
                    msg+= "%s[%.1ful, min=%.0f RPM, max=%.0f RPM] "%(x.name,x.volume,tmp[0],tmp[1]),
            warned=True
            logging.notice(msg)

        if warned:
            logging.warning("Mixing %s at %.0f RPM (min unmixed vol=%.0ful ->  min RPM=%.0f;  max vol=%.0ful -> max RPM=%.f)"%(plate.name, speed, minvol, minspeed, maxvol, maxspeed))
        else:
            logging.notice("Mixing %s at %.0f RPM (min unmixed vol=%.0ful ->  min RPM=%.0f;  max vol=%.0ful -> max RPM=%.f)"%(plate.name, speed, minvol, minspeed, maxvol, maxspeed))

        oldloc=plate.curloc
        self.moveplate(plate,"Shaker",returnHome=False)
        global __shakerActive
        __shakerActive=True
        worklist.pyrun("BioShake\\bioexec.py setElmLockPos")
        worklist.pyrun("BioShake\\bioexec.py setShakeTargetSpeed%d"%speed)
        worklist.pyrun("BioShake\\bioexec.py setShakeAcceleration%d"%accel)
        worklist.pyrun("BioShake\\bioexec.py shakeOn")
        self.starttimer()
        Sample.shaken(plate.name,speed)
        Sample.addallhistory("(S%d@%.0f)"%(dur,speed),onlyplate=plate.name)
        self.waittimer(dur)
        worklist.pyrun("BioShake\\bioexec.py shakeOff")
        self.starttimer()
        self.waittimer(accel+4)
        worklist.pyrun("BioShake\\bioexec.py setElmUnlockPos")
        __shakerActive=False
        if returnPlate:
            self.moveplate(plate,oldloc)

    @staticmethod
    def shakerIsActive():
        return __shakerActive

    def starttimer(self,timer=1):
        self.timerStartTime[timer]=clock.pipetting
        worklist.starttimer(timer)

    def waittimer(self,duration,timer=1):
        if self.timerStartTime[timer]+duration-clock.pipetting > 20:
            # Might as well sanitize while we're waiting
            self.sanitize()
        if duration>0:
            worklist.waittimer(duration,timer)
            #Sample.addallhistory("{%ds}"%duration)

    def pause(self,duration):
        self.starttimer()
        self.waittimer(duration)
        Sample.addallhistory("(%ds)"%duration)

    def waitpgm(self, sanitize=True):
        if not self.ptcrunning:
            return
        #print "* Wait for PTC to finish"
        if sanitize:
            self.sanitize()   # Sanitize tips before waiting for this to be done
        worklist.comment("Wait for PTC")
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

        clock.pipandthermotime+=(clock.pipetting-self.pgmStartTime)
        clock.thermotime+=(self.pgmEndTime-clock.pipetting)
        clock.pipetting=self.pgmStartTime

        #print "Waiting for PTC with %.0f seconds expected to remain"%(self.pgmEndTime-clock.pipetting)
        worklist.pyrun('PTC\\ptcwait.py')
        worklist.pyrun("PTC\\ptclid.py OPEN")
        #        worklist.pyrun('PTC\\ptcrun.py %s CALC ON'%"COOLDOWN")
        #        worklist.pyrun('PTC\\ptcwait.py')
        worklist.vector("PTC200lid",decklayout.PTCPOS,worklist.SAFETOEND,True,worklist.DONOTMOVE,worklist.CLOSE)
        worklist.vector("Hotel 1 Lid",decklayout.HOTELPOS,worklist.SAFETOEND,True,worklist.DONOTMOVE,worklist.OPEN)

        worklist.vector("PTC200WigglePos",decklayout.PTCPOS,worklist.SAFETOEND,False,worklist.DONOTMOVE,worklist.DONOTMOVE)
        worklist.vector("PTC200Wiggle",decklayout.PTCPOS,worklist.SAFETOEND,False,worklist.DONOTMOVE,worklist.CLOSE,True)
        worklist.vector("PTC200Wiggle",decklayout.PTCPOS,worklist.ENDTOSAFE,False,worklist.DONOTMOVE,worklist.OPEN,True)
        worklist.vector("PTC200WigglePos",decklayout.PTCPOS,worklist.ENDTOSAFE,False,worklist.DONOTMOVE,worklist.DONOTMOVE)

        worklist.vector("PTC200Wiggle2Pos",decklayout.PTCPOS,worklist.SAFETOEND,False,worklist.DONOTMOVE,worklist.DONOTMOVE)
        worklist.vector("PTC200Wiggle2",decklayout.PTCPOS,worklist.SAFETOEND,False,worklist.DONOTMOVE,worklist.CLOSE,True)
        worklist.vector("PTC200Wiggle2",decklayout.PTCPOS,worklist.ENDTOSAFE,False,worklist.DONOTMOVE,worklist.OPEN,True)
        worklist.vector("PTC200Wiggle2Pos",decklayout.PTCPOS,worklist.ENDTOSAFE,False,worklist.DONOTMOVE,worklist.DONOTMOVE)

        worklist.vector("PTC200WigglePos",decklayout.PTCPOS,worklist.SAFETOEND,False,worklist.DONOTMOVE,worklist.DONOTMOVE)
        worklist.vector("PTC200Wiggle",decklayout.PTCPOS,worklist.SAFETOEND,False,worklist.DONOTMOVE,worklist.CLOSE,True)
        worklist.vector("PTC200Wiggle",decklayout.PTCPOS,worklist.ENDTOSAFE,False,worklist.DONOTMOVE,worklist.OPEN,True)
        worklist.vector("PTC200WigglePos",decklayout.PTCPOS,worklist.ENDTOSAFE,False,worklist.DONOTMOVE,worklist.DONOTMOVE)

        self.ptcrunning=False
        self.moveplate(decklayout.SAMPLEPLATE,"Home")
        # Mark all samples on plate as unmixed (due to condensation)
        Sample.notMixed(decklayout.SAMPLEPLATE.name)
        # Verify plate is in place
        worklist.vector(decklayout.SAMPLEPLATE.vectorName,decklayout.SAMPLEPLATE,worklist.SAFETOEND,False,worklist.DONOTMOVE,worklist.CLOSE)
        worklist.vector(decklayout.SAMPLEPLATE.vectorName,decklayout.SAMPLEPLATE,worklist.ENDTOSAFE,False,worklist.OPEN,worklist.DONOTMOVE)
        worklist.romahome()
        #worklist.userprompt("Plate should be back on deck. Press return to continue")
        # Wash tips again to remove any drips that may have formed while waiting for PTC
        worklist.wash(15,1,5,True)


    def dilute(self,samples,factor):
        if isinstance(factor,list):
            assert len(samples)==len(factor)
            for i in range(len(samples)):
                samples[i].dilute(factor[i])
        else:
            for s in samples:
                s.dilute(factor)
