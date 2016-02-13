import worklist
from sample import Sample
from concentration import Concentration
import liquidclass
import os.path
from datetime import datetime
from plate import Plate
import reagents

_Experiment__shakerActive = False

class Experiment(object):
    WASHLOC=Plate("Wash",1,2,1,8,False,0)
    # Use dimensional data from Robot/Calibration/20150302-LiquidHeights
    REAGENTPLATE=Plate("Reagents",18,1,6,5,False,unusableVolume=20,maxVolume=1700,zmax=569,angle=17.5,r1=4.05,h1=17.71,v0=12.9)
    MAGPLATELOC=Plate("MagPlate",18,2,12,8,False,unusableVolume=9,maxVolume=200,zmax=1459,angle=17.5,r1=2.80,h1=10.04,v0=10.8)   # HSP9601 on magnetic plate  (Use same well dimesnsions as SAMPLE)
    hspmaxspeeds={200:1400,150:1600,100:1850,50:2000,20:2200};	# From shaketest experiment
    grenmaxspeeds={150:1750,125:1900,100:1950,75:2200,50:2200};	# From shaketest experiment
    
#  SAMPLEPLATE=Plate("Samples",4,3,12,8,False,unusableVolume=15,maxVolume=200,zmax=1028,angle=17.5,r1=2.80,h1=10.04,v0=10.8,vectorName="Microplate Landscape",maxspeeds=hspmaxspeeds);  # HSP96xx
    SAMPLEPLATE=Plate("Samples",4,3,12,8,False,unusableVolume=15,maxVolume=200,zmax=1028,angle=17.5,r1=2.69,h1=8.94,v0=13.2,vectorName="Microplate Landscape",maxspeeds=hspmaxspeeds);  # EppLoBind
    SHAKERPLATELOC=Plate("Shaker",9,0,1,1)
    #    READERPLATE=Plate("Reader",4,1,12,8,False,15)
    QPCRPLATE=Plate("qPCR",4,1,12,8,False,unusableVolume=15,maxVolume=200,zmax=984,angle=17.5,r1=2.66,h1=9.37,v0=7.9)
#    DILPLATE=Plate("Dilutions",4,2,12,8,False,unusableVolume=15,maxVolume=200,zmax=1028,angle=17.5,r1=2.84,h1=9.76,v0=11.9,vectorName="Microplate Landscape",maxspeeds=hspmaxspeeds) # HSP96xx
    DILPLATE=Plate("Dilutions",4,2,12,8,False,unusableVolume=15,maxVolume=200,zmax=1028,angle=17.5,r1=2.69,h1=7.70,v0=17.9,vectorName="Microplate Landscape",maxspeeds=hspmaxspeeds) # EppLoBind
#    DILPLATE=Plate("Dilutions-LB",4,2,12,8,False,unusableVolume=15,maxVolume=200,zmax=1028,angle=100,r1=2.92,h1=0.81,v0=6.8,vectorName="Grenier Landscape",maxspeeds=grenmaxspeeds) # Grenier 651901 Lobind plate
    SSDDILLOC=Plate("SSDDil",3,1,1,4,False,100,100000)
    WATERLOC=Plate("Water",3,2,1,4,False,100,100000)
    BLEACHLOC=Plate("Bleach",3,3,1,4,False,0,100000)
    PTCPOS=Plate("PTC",25,1,1,1)
    HOTELPOS=Plate("Hotel",25,0,1,1)
    WASTE=Plate("Waste",20,3,1,1)
    EPPENDORFS=Plate("Eppendorfs",13,1,1,16,False,unusableVolume=30,maxVolume=1500,zmax=1337,angle=17.5,h1=17.56,r1=4.42,v0=29.6)
    WATER=Sample("Water",WATERLOC,-1,None,50000)
    SSDDIL=Sample("SSDDil",SSDDILLOC,-1,None,50000)
    BLEACH=Sample("RNase-Away",BLEACHLOC,-1,None,50000)
    DITIMASK=0   # Which tips are DiTis
    headerfile=os.path.expanduser("~/Dropbox/Synbio/Robot/pyTecan/header.gem")

    RPTEXTRA=0   # Extra amount when repeat pipetting
    MAXVOLUME=200  # Maximum volume for pipetting in ul

    def __init__(self,totalTime=None):
        'Create a new experiment with given sample locations for water and WASTE;  totalTime is expected run time in seconds, if known'
        worklist.comment("Generated %s"%(datetime.now().ctime()));
        worklist.userprompt("The following reagent tubes should be present: %s"%Sample.getAllLocOnPlate(self.REAGENTPLATE))
        worklist.userprompt("The following eppendorf tubes should be present: %s"%Sample.getAllLocOnPlate(self.EPPENDORFS))
        worklist.email(dest='cdsrobot@gmail.com',subject='Run started (Generate: %s)'%(datetime.now().ctime()))
        worklist.email(dest='cdsrobot@gmail.com',subject='Tecan error',onerror=1)
        self.cleanTips=0
        # self.sanitize()  # Not needed, TRP does it, also first use of tips will do this
        self.useDiTis=False
        self.thermotime=0		# Time waiting for thermocycler without pipetting
        self.pipandthermotime=0		# Time while pipetting and thermocycling   (elapsed=time pipetting, whether or not thermocycling also)
        self.BLEACH.mixLC=liquidclass.LCBleachMix
        self.ptcrunning=False
        self.overrideSanitize=False
        self.totalTime=totalTime
        
        # Access PTC and RIC early to be sure they are working
        worklist.pyrun("PTC\\ptctest.py")
        #        worklist.periodicWash(15,4)
        worklist.userprompt("Verify that PTC thermocycler lid pressure is set to '2'.")
        self.idlePgms=[]
        self.timerStartTime=[None]*8
        
    def addIdleProgram(self,pgm):
        self.idlePgms.append(pgm)
        
    def setreagenttemp(self,temp=None):
        if temp==None:
            worklist.pyrun("RIC\\ricset.py IDLE")
        else:
            worklist.variable("dewpoint",temp,userprompt="Enter dewpoint",minval=0,maxval=20)
            worklist.variable("rictemp","~dewpoint~+2")
            worklist.pyrun("RIC\\ricset.py ~rictemp~")
#            worklist.pyrun("RIC\\ricset.py %s"%temp)

    def saveworklist(self,filename):
        worklist.saveworklist(filename)

    def savegem(self,filename):
        worklist.flushQueue()
        worklist.savegem(self.headerfile,filename)
        
    def savesummary(self,filename):
        # Print amount of samples needed
        fd=open(filename,"w")
        print >>fd,"Deck layout:"
        print >>fd,self.REAGENTPLATE
        print >>fd,self.SAMPLEPLATE
        print >>fd,self.QPCRPLATE
        print >>fd,self.WATERLOC
        print >>fd,self.WASTE
        print >>fd,self.BLEACHLOC
        print >>fd,self.WASHLOC
        
        print >>fd
        print >>fd,"DiTi usage:",worklist.getDITIcnt()
        print >>fd

        print >>fd,"Run time: %d (pipetting only) + %d (thermocycling only) + %d (both) = %d minutes\n"%((worklist.elapsed-self.pipandthermotime)/60.0,self.thermotime/60, self.pipandthermotime/60, (worklist.elapsed+self.thermotime)/60)
        reagents.printprep(fd)
        Sample.printallsamples("All Samples:",fd,w=worklist)
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
                    self.BLEACH.addhistory("SANITIZE",0,1<<i)
            worklist.mix(fixedTips,fixedWells,self.BLEACH.mixLC,200,self.BLEACH.plate,nmix,False);
            worklist.wash(fixedTips,1,deepvol,True)
        self.cleanTips|=fixedTips
        # print "* Sanitize"
        if self.totalTime!=None:
            worklist.comment("Estimated elapsed: %d minutes, remaining run time: %d minutes"%((self.thermotime+worklist.elapsed)/60,(self.totalTime-(worklist.elapsed+self.thermotime))/60))
        else:
            worklist.comment("Estimated elapsed: %d minutes"%((self.thermotime+worklist.elapsed)/60))
        
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
            
    def multitransfer(self, volumes, src, dests,mix=(False,False),getDITI=True,dropDITI=True,ignoreContents=False):
        'Multi pipette from src to multiple dest.  mix is (src,dest) mixing'
        #print "multitransfer(",volumes,",",src,",",dests,",",mix,",",getDITI,",",dropDITI,")"
        if self.ptcrunning and (src.plate==Experiment.SAMPLEPLATE or len([1 for d in dests if d.plate==Experiment.SAMPLEPLATE])>0):
            self.waitpgm()
            
        if isinstance(volumes,(int,long,float)):
            # Same volume for each dest
            volumes=[volumes for i in range(len(dests))]
        assert(len(volumes)==len(dests))
        #        if len([d.volume for d in dests if d.conc!=None])==0:
        if len([dests[i].volume for i in range(0,len(dests)) if dests[i].conc != None and volumes[i]>0.01])==0:
            maxval=0
        else:
            maxval=max([dests[i].volume for i in range(0,len(dests)) if dests[i].conc != None and volumes[i]>0.01])
            #         maxval=max([d.volume for d in dests if d.conc != None])
        #print "volumes=",[d.volume for d in dests],", conc=",[str(d.conc) for d in dests],", maxval=",maxval
        if mix[1]==False and len(volumes)>1 and ( maxval<.01 or ignoreContents):
            if sum(volumes)>self.MAXVOLUME:
                #print "sum(volumes)=%.1f, MAXVOL=%.1f"%(sum(volumes),self.MAXVOLUME)
                for i in range(1,len(volumes)):
                    if sum(volumes[0:i+1])>self.MAXVOLUME:
                        destvol=max([d.volume for d in dests[0:i]])
                        reuseTip=destvol<=0
                        # print "Splitting multi with total volume of %.1f ul into smaller chunks < %.1f ul after %d dispenses "%(sum(volumes),self.MAXVOLUME,i),
                        # if reuseTip:
                        #     print "with tip reuse"
                        # else:
                        #     print "without tip reuse"
                        self.multitransfer(volumes[0:i],src,dests[0:i],mix,getDITI,not reuseTip)
                        self.multitransfer(volumes[i:],src,dests[i:],(False,mix[1]),not reuseTip,dropDITI)
                        return
                    
            if self.useDiTis:
                tipMask=4
                if  getDITI:
                    ditivol=sum(volumes)+src.inliquidLC.multicond+src.inliquidLC.multiexcess
                    worklist.getDITI(tipMask&self.DITIMASK,min(self.MAXVOLUME,ditivol),True,True)
            else:
                tipMask=self.cleantip()

            cmt="Multi-add  %s to samples %s"%(src.name,",".join("%s[%.1f]"%(dests[i].name,volumes[i]) for i in range(len(dests))))
            #print "*",cmt
            worklist.comment(cmt)

            if mix[0] and not src.isMixed:
                src.mix(tipMask,worklist)
            src.aspirate(tipMask,worklist,sum(volumes),True)
            for i in range(len(dests)):
                if volumes[i]>0.01:
                    dests[i].dispense(tipMask,worklist,volumes[i],src)
            if self.useDiTis and dropDITI:
                worklist.dropDITI(tipMask&self.DITIMASK,self.WASTE)
        else:
            for i in range(len(dests)):
                if volumes[i]>0.01:
                    self.transfer(volumes[i],src,dests[i],(mix[0] and i==0,mix[1]),getDITI,dropDITI)

    def transfer(self, volume, src, dest, mix=(False,False), getDITI=True, dropDITI=True):
        if self.ptcrunning and (src.plate==Experiment.SAMPLEPLATE or dest.plate==Experiment.SAMPLEPLATE)>0:
            self.waitpgm()
        if volume>self.MAXVOLUME:
            destvol=dest.volume
            reuseTip=destvol<=0
            print "Splitting large transfer of %.1f ul into smaller chunks < %.1f ul "%(volume,self.MAXVOLUME),
            if reuseTip:
                print "with tip reuse"
            else:
                print "without tip reuse"
            self.transfer(self.MAXVOLUME,src,dest,mix,getDITI,False)
            self.transfer(volume-self.MAXVOLUME,src,dest,(mix[0] and not reuseTip,mix[1]),False,dropDITI)
            return
        
        cmt="Add %.1f ul of %s to %s"%(volume, src.name, dest.name)
        ditivolume=volume+src.inliquidLC.singletag
        if mix[0] and not src.isMixed:
            cmt=cmt+" with src mix"
            ditivolume=max(ditivolume,src.volume)
        if mix[1] and dest.volume>0 and not src.isMixed:
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

        if mix[0]:
            src.mix(tipMask,worklist)
        src.aspirate(tipMask,worklist,volume)
        dest.dispense(tipMask,worklist,volume,src)
        if mix[1]:
            dest.mix(tipMask,worklist,True)

        if self.useDiTis and dropDITI:
            worklist.dropDITI(tipMask&self.DITIMASK,self.WASTE)

    # Mix
    def mix(self, src, nmix=4):
        if self.ptcrunning and src.plate==Experiment.SAMPLEPLATE:
            self.waitpgm()

        cmt="Mix %s"%(src.name)
        tipMask=self.cleantip()
        worklist.comment(cmt)
        src.isMixed=False	# Force a mix
        src.mix(tipMask,worklist,False,nmix=nmix)

    def dispose(self, volume, src,  mix=False, getDITI=True, dropDITI=True):
        'Dispose of a given volume by aspirating and not dispensing (will go to waste during next wash)'
        if self.ptcrunning and src.plate==Experiment.SAMPLEPLATE:
            self.waitpgm()
        if volume>self.MAXVOLUME:
            reuseTip=False   # Since we need to wash to get rid of it
            print "Splitting large transfer of %.1f ul into smaller chunks < %.1f ul "%(volume,self.MAXVOLUME),
            if reuseTip:
                print "with tip reuse"
            else:
                print "without tip reuse"
            self.dispose(self.MAXVOLUME,src,mix,getDITI,dropDITI)
            self.dispose(volume-self.MAXVOLUME,src,False,getDITI,dropDITI)
            return
        
        cmt="Remove and dispose of %.1f ul from %s"%(volume, src.name)
        ditivolume=volume+src.inliquidLC.singletag
        if mix and not src.isMixed:
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

        if mix and not src.isMixed:
            src.mix(tipMask,worklist)
        src.aspirate(tipMask,worklist,volume)

        if self.useDiTis and dropDITI:
            worklist.dropDITI(tipMask&self.DITIMASK,self.WASTE)

    def stage(self,stagename,reagents,sources,samples,volume,finalx=1.0,destMix=True,dilutant=None):
        # Add water to sample wells as needed (multi)
        # Pipette reagents into sample wells (multi)
        # Pipette sources into sample wells
        # Concs are in x (>=1)

        # Sample.printallsamples("Before "+stagename)
        # print "\nStage: ", stagename, "reagents=",[str(r) for r in reagents], ",sources=",[str(s) for s in sources],",samples=",[str(s) for s in samples],str(volume)

        if len(samples)==0:
            print "No samples\n"
            return

        if dilutant==None:
            dilutant=self.WATER
            
        worklist.comment("Stage: "+stagename)
        if not isinstance(volume,list):
            volume=[volume for i in range(len(samples))]
        for i in range(len(volume)):
            assert(volume[i]>0)
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
            print "Error: Ingredients add up to more than desired volume by %.1f ul"%(-min(watervols))
            for s in samples:
                if (s.volume>0):
                    print "Note: %s already contains %.1f ul\n"%(s.name,s.volume)
            assert(False)

        if sum(watervols)>0.01:
            self.multitransfer(watervols,dilutant,samples,(False,destMix and (len(reagents)+len(sources)==0)))

        for i in range(len(reagents)):
            self.multitransfer([reagentvols[i]*v for v in volume],reagents[i],samples,(True,destMix and (len(sources)==0 and i==len(reagents)-1)))

        if len(sources)>0:
            assert(len(sources)<=len(samples))
            for i in range(len(sources)):
                self.transfer(sourcevols[i],sources[i],samples[i],(True,destMix))


    def lihahome(self):
        'Move LiHa to left of deck'
        worklist.moveliha(self.WASHLOC)
        
    def runpgm(self,pgm,duration,waitForCompletion=True,volume=10,hotlidmode="TRACKING",hotlidtemp=1):
        if self.ptcrunning:
            print "ERROR: Attempt to start a progam on PTC when it is already running"
            assert(False)
        if len(pgm)>8:
            print "ERROR: PTC program name (%s) too long (max is 8 char)"%pgm
            assert(False)
        # move to thermocycler
        worklist.flushQueue()
        self.lihahome()
        cmt="run %s"%pgm
        worklist.comment(cmt)
        #print "*",cmt
        worklist.pyrun("PTC\\ptclid.py OPEN")
        self.moveplate(self.SAMPLEPLATE,"PTC")
        worklist.vector("Hotel 1 Lid",self.HOTELPOS,worklist.SAFETOEND,True,worklist.DONOTMOVE,worklist.CLOSE)
        worklist.vector("PTC200lid",self.PTCPOS,worklist.SAFETOEND,True,worklist.DONOTMOVE,worklist.OPEN)
        worklist.romahome()
        worklist.pyrun("PTC\\ptclid.py CLOSE")
        #        pgm="PAUSE30"  # For debugging
        assert(hotlidmode=="TRACKING" or hotlidmode=="CONSTANT")
        assert((hotlidmode=="TRACKING" and hotlidtemp>=0 and hotlidtemp<=45) or (hotlidmode=="CONSTANT" and hotlidtemp>30))
        worklist.pyrun('PTC\\ptcrun.py %s CALC %s,%d %d'%(pgm,hotlidmode,hotlidtemp,volume))
        self.pgmStartTime=worklist.elapsed
        self.pgmEndTime=duration*60+worklist.elapsed
        self.ptcrunning=True
        Sample.addallhistory("{%s}"%pgm,addToEmpty=False,onlyplate=self.SAMPLEPLATE.name)
        if waitForCompletion:
            self.waitpgm()
            
    def moveplate(self,plate,dest="Home",returnHome=True):
        if self.ptcrunning and plate==Experiment.SAMPLEPLATE:
            self.waitpgm()

        # move to given destination (one of "Home","Magnet","Shaker","PTC" )
        if plate!=self.SAMPLEPLATE and plate!=self.DILPLATE:
            print "Only able to move %s or %s plates, not %s"%(self.SAMPLEPLATE.name,self.DILPLATE.name,plate.name)
            assert(False)
            
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
            worklist.vector("Magplate",self.MAGPLATELOC,worklist.SAFETOEND,True,worklist.DONOTMOVE,worklist.CLOSE)
        elif plate.curloc=="Shaker":
            worklist.vector("Shaker",self.SHAKERPLATELOC,worklist.SAFETOEND,True,worklist.DONOTMOVE,worklist.CLOSE)
        elif plate.curloc=="PTC":
            worklist.vector("PTC200",self.PTCPOS,worklist.SAFETOEND,True,worklist.DONOTMOVE,worklist.CLOSE)
        else:
            print "Plate %s is in unknown location: %s"%(plate.name,plate.curloc)
            assert(False)

        if dest=="Home":
            plate.movetoloc(dest)
            worklist.vector(plate.vectorName,plate,worklist.SAFETOEND,True,worklist.DONOTMOVE,worklist.OPEN)
        elif dest=="Magnet":
            plate.movetoloc(dest,self.MAGPLATELOC)
            worklist.vector("Magplate",self.MAGPLATELOC,worklist.SAFETOEND,True,worklist.DONOTMOVE,worklist.OPEN)
        elif dest=="Shaker":
            plate.movetoloc(dest,self.SHAKERPLATELOC)
            worklist.vector("Shaker",self.SHAKERPLATELOC,worklist.SAFETOEND,True,worklist.DONOTMOVE,worklist.OPEN)
        elif dest=="PTC":
            plate.movetoloc(dest,self.PTCPOS)
            worklist.vector("PTC200",self.PTCPOS,worklist.SAFETOEND,True,worklist.DONOTMOVE,worklist.OPEN)
        else:
            print "Attempt to move plate %s to unknown location: %s"%(plate.name,dest)
            assert(False)

        Sample.addallhistory("{->%s}"%dest,onlyplate=plate.name)
        if returnHome:
            worklist.romahome()

    def shake(self,plate,dur=60,speed=None,accel=5,returnPlate=True):
        if self.ptcrunning and plate==Experiment.SAMPLEPLATE:
            self.waitpgm()

        # Move the plate to the shaker, run for the given time, and bring plate back
        samps=Sample.getAllOnPlate(plate)
        maxvol=max([x.volume for x in samps])
        minvol=min([x.volume for x in samps if not x.isMixed]+[200])
        (minspeed,maxspeed)=plate.getmixspeeds(minvol*0.95,maxvol+5)	# Assume volumes could be off 

        if speed==None:
            if minspeed<maxspeed:
                speed=(maxspeed+minspeed)/2
            else:
                speed=maxspeed

        warned=False
        
        if speed>maxspeed:
            print "WARNING: %s plate contains wells with up to %.2f ul, which may spill at %d RPM: "%(plate.name, maxvol, speed),
            for x in samps:
                tmp=plate.getmixspeeds(x.volume,x.volume)
                if tmp[1]<speed:
                    print "%s[%.1ful, max=%.0f RPM] "%(x.name,x.volume,tmp[1]),
            print
            warned=True
            
        if speed<minspeed:
            print "WARNING: %s plate contains unmixed wells with as little as %.2f ul, which may not be mixed at %d RPM: "%(plate.name, minvol, speed),
            for x in samps:
                if x.isMixed:
                    continue
                tmp=plate.getmixspeeds(x.volume,x.volume)
                if speed<tmp[0]:
                    print "%s[%.1ful, min=%.0f RPM] "%(x.name,x.volume,tmp[0]),
            print
            warned=True

        if  warned:
            print "         Mixing %s at %.0f RPM (min unmixed vol=%.0ful ->  min RPM=%.0f;  max vol=%.0ful -> max RPM=%.f)"%(plate.name, speed, minvol, minspeed, maxvol, maxspeed)

        oldloc=plate.curloc
        self.moveplate(plate,"Shaker",returnHome=False)
        __shakerActive=True
        worklist.pyrun("BioShake\\bioexec.py setElmLockPos")
        worklist.pyrun("BioShake\\bioexec.py setShakeTargetSpeed%d"%speed)
        worklist.pyrun("BioShake\\bioexec.py setShakeAcceleration%d"%accel)
        worklist.pyrun("BioShake\\bioexec.py shakeOn")
        self.starttimer()
        Sample.mixall(plate.name)
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
        self.timerStartTime[timer]=worklist.elapsed
    	worklist.starttimer(timer)

    def waittimer(self,duration,timer=1):
        if self.timerStartTime[timer]+duration-worklist.elapsed > 20:
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
        while self.pgmEndTime-worklist.elapsed > 120:
            # Run any idle programs
            oldElapsed=worklist.elapsed
            for ip in self.idlePgms:
                if self.pgmEndTime-worklist.elapsed > 120:
                    #print "Executing idle program with %.0f seconds"%(self.pgmEndTime-worklist.elapsed)
                    ip(self.pgmEndTime-worklist.elapsed-120)
            if oldElapsed==worklist.elapsed:
                # Nothing was done
                break
            worklist.flushQueue()		# Just in case

        self.pipandthermotime+=(worklist.elapsed-self.pgmStartTime)
        self.thermotime+=(self.pgmEndTime-worklist.elapsed)
        print "Waiting for PTC with %.0f seconds expected to remain"%(self.pgmEndTime-worklist.elapsed)
        worklist.pyrun('PTC\\ptcwait.py')
        worklist.pyrun("PTC\\ptclid.py OPEN")
        #        worklist.pyrun('PTC\\ptcrun.py %s CALC ON'%"COOLDOWN")
        #        worklist.pyrun('PTC\\ptcwait.py')
        worklist.vector("PTC200lid",self.PTCPOS,worklist.SAFETOEND,True,worklist.DONOTMOVE,worklist.CLOSE)
        worklist.vector("Hotel 1 Lid",self.HOTELPOS,worklist.SAFETOEND,True,worklist.DONOTMOVE,worklist.OPEN)

        worklist.vector("PTC200WigglePos",self.PTCPOS,worklist.SAFETOEND,False,worklist.DONOTMOVE,worklist.DONOTMOVE)
        worklist.vector("PTC200Wiggle",self.PTCPOS,worklist.SAFETOEND,False,worklist.DONOTMOVE,worklist.CLOSE,True)
        worklist.vector("PTC200Wiggle",self.PTCPOS,worklist.ENDTOSAFE,False,worklist.DONOTMOVE,worklist.OPEN,True)
        worklist.vector("PTC200WigglePos",self.PTCPOS,worklist.ENDTOSAFE,False,worklist.DONOTMOVE,worklist.DONOTMOVE)

        worklist.vector("PTC200Wiggle2Pos",self.PTCPOS,worklist.SAFETOEND,False,worklist.DONOTMOVE,worklist.DONOTMOVE)
        worklist.vector("PTC200Wiggle2",self.PTCPOS,worklist.SAFETOEND,False,worklist.DONOTMOVE,worklist.CLOSE,True)
        worklist.vector("PTC200Wiggle2",self.PTCPOS,worklist.ENDTOSAFE,False,worklist.DONOTMOVE,worklist.OPEN,True)
        worklist.vector("PTC200Wiggle2Pos",self.PTCPOS,worklist.ENDTOSAFE,False,worklist.DONOTMOVE,worklist.DONOTMOVE)

        worklist.vector("PTC200WigglePos",self.PTCPOS,worklist.SAFETOEND,False,worklist.DONOTMOVE,worklist.DONOTMOVE)
        worklist.vector("PTC200Wiggle",self.PTCPOS,worklist.SAFETOEND,False,worklist.DONOTMOVE,worklist.CLOSE,True)
        worklist.vector("PTC200Wiggle",self.PTCPOS,worklist.ENDTOSAFE,False,worklist.DONOTMOVE,worklist.OPEN,True)
        worklist.vector("PTC200WigglePos",self.PTCPOS,worklist.ENDTOSAFE,False,worklist.DONOTMOVE,worklist.DONOTMOVE)

        self.ptcrunning=False
        self.moveplate(self.SAMPLEPLATE,"Home")
        # Verify plate is in place
        worklist.vector(self.SAMPLEPLATE.vectorName,self.SAMPLEPLATE,worklist.SAFETOEND,False,worklist.DONOTMOVE,worklist.CLOSE)
        worklist.vector(self.SAMPLEPLATE.vectorName,self.SAMPLEPLATE,worklist.ENDTOSAFE,False,worklist.OPEN,worklist.DONOTMOVE)
        worklist.romahome()
        #worklist.userprompt("Plate should be back on deck. Press return to continue")
        # Wash tips again to remove any drips that may have formed while waiting for PTC
        worklist.wash(15,1,5,True)


    def dilute(self,samples,factor):
        if isinstance(factor,list):
            assert(len(samples)==len(factor))
            for i in range(len(samples)):
                samples[i].dilute(factor[i])
        else:
            for s in samples:
                s.dilute(factor)
