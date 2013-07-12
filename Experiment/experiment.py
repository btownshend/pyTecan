from worklist import *
from sample import Sample
from concentration import Concentration
import liquidclass
import os.path

ptcrunning=False

class Experiment(object):
    WASHLOC=Plate("Wash",1,2,1,8)
    REAGENTPLATE=Plate("Reagents",3,1,6,5,True)
    SAMPLEPLATE=Plate("Samples",10,3,12,8)
    READERPLATE=Plate("Reader",10,2,12,8)
    QPCRPLATE=Plate("qPCR",10,2,12,8)
    WATERLOC=Plate("Water",17,2,1,4)
    RNASEAWAYLOC=Plate("Water",17,1,1,4)
    PTCPOS=Plate("PTC",25,1,1,1)
    HOTELPOS=Plate("Hotel",25,0,1,1)
    WASTE=Plate("Waste",20,3,1,1)
    EPPENDORFS=Plate("Eppendorfs",19,1,1,16)
    WATER=Sample("Water",WATERLOC,None,None,10000)
    RNASEAWAY=Sample("RNase-Away",RNASEAWAYLOC,0,None,10000)
    DITIMASK=0   # Which tips are DiTis
    headerfile=os.path.expanduser("~/Dropbox/Synbio/Robot/pyTecan/header.gem")

    RPTEXTRA=0   # Extra amount when repeat pipetting
    MAXVOLUME=200  # Maximum volume for pipetting in ul

    def __init__(self):
        'Create a new experiment with given sample locations for water and self.WASTE'
        self.w=WorkList()
        self.cleanTips=0
        self.sanitize()
        self.useDiTis=False
        self.thermotime=0
        self.RNASEAWAY.mixLC=liquidclass.LC("RNaseAway-Mix")
        self.ptcrunning=False
        #        self.w.periodicWash(15,4)
        
    def setreagenttemp(self,temp=None):
        if temp==None:
            self.w.pyrun("RIC\\ricset.py IDLE")
        else:
            self.w.pyrun("RIC\\ricset.py %f"%temp)

    def saveworklist(self,filename):
        self.w.saveworklist(filename)

    def savegem(self,filename):
        self.w.savegem(self.headerfile,filename)
        
    def savesummary(self,filename):
        # Print amount of samples needed
        fd=open(filename,"w")
        print >>fd,"Deck layout:"
        print >>fd,self.REAGENTPLATE
        print >>fd,self.SAMPLEPLATE
        print >>fd,self.QPCRPLATE
        print >>fd,self.WATERLOC
        print >>fd,self.WASTE
        print >>fd,self.RNASEAWAYLOC
        print >>fd,self.WASHLOC
        
        print >>fd
        print >>fd,"DiTi usage:",self.w.getDITIcnt()
        print >>fd

        print >>fd,"Run time: %d (pipetting) + %d (thermocycling) = %d minutes\n"%(self.w.elapsed/60.0,self.thermotime/60, (self.w.elapsed+self.thermotime)/60)
        Sample.printprep(fd)
        Sample.printallsamples("All Samples:",fd)
        
    def sanitize(self):
        'Deep wash including RNase-Away treatment'
        self.w.comment("Sanitize")
        self.w.wash(15,1,2)
        fixedTips=(~self.DITIMASK)&15
        fixedWells=[]
        for i in range(4):
            if (fixedTips & (1<<i)) != 0:
                fixedWells.append(i)
        self.w.mix(fixedTips,fixedWells,self.RNASEAWAY.mixLC,200,self.RNASEAWAY.plate,1);
        self.w.wash(fixedTips,1,10,True)
        self.cleanTips|=fixedTips
        print "* Sanitize"
        
    def cleantip(self):
        'Get the mask for a clean tip, washing if needed'
        if self.cleanTips==0:
            self.cleanTips=(~self.DITIMASK)&15
            #self.w.wash(self.cleanTips)
            self.sanitize()
        tipMask=1
        while (self.cleanTips & tipMask)==0:
            tipMask<<=1
        self.cleanTips&=~tipMask
        return tipMask
            
    def multitransfer(self, volumes, src, dests,mix=(False,False),getDITI=True,dropDITI=True):
        'Multi pipette from src to multiple dest.  mix is (src,dest) mixing'
        #print "multitransfer(",volumes,",",src,",",dests,",",mix,",",getDITI,",",dropDITI,")"
        if self.ptcrunning and (src.plate==Experiment.SAMPLEPLATE or len([1 for d in dests if d.plate==Experiment.SAMPLEPLATE])>0):
            self.waitpgm()
            
        if isinstance(volumes,(int,long,float)):
            # Same volume for each dest
            volumes=[volumes for i in range(len(dests))]
        assert(len(volumes)==len(dests))
        if len([d.volume for d in dests if d.conc!=None])==0:
            maxval=0
        else:
            maxval=max([d.volume for d in dests if d.conc != None])
        #print "volumes=",[d.volume for d in dests],", conc=",[str(d.conc) for d in dests],", maxval=",maxval
        if mix[1]==False and len(volumes)>1 and maxval<.01:
            if sum(volumes)>self.MAXVOLUME:
                print "sum(volumes)=%.1f, MAXVOL=%.1f"%(sum(volumes),self.MAXVOLUME)
                for i in range(1,len(volumes)):
                    if sum(volumes[0:i+1])>self.MAXVOLUME:
                        print "Splitting multi with total volume of %.1f ul into smaller chunks < %.1f ul after %d dispenses "%(sum(volumes),self.MAXVOLUME,i),
                        destvol=max([d.volume for d in dests[0:i]])
                        reuseTip=destvol<=0
                        if reuseTip:
                            print "with tip reuse"
                        else:
                            print "without tip reuse"
                        self.multitransfer(volumes[0:i],src,dests[0:i],mix,getDITI,not reuseTip)
                        self.multitransfer(volumes[i:],src,dests[i:],(False,mix[1]),not reuseTip,dropDITI)
                        return
                    
            if self.useDiTis:
                tipMask=4
                if  getDITI:
                    ditivol=sum(volumes)+src.inliquidLC.multicond+src.inliquidLC.multiexcess
                    self.w.getDITI(tipMask&self.DITIMASK,min(self.MAXVOLUME,ditivol),True,True)
            else:
                tipMask=self.cleantip()

            cmt="Multi-add  %s to samples %s"%(src.name,",".join("%s[%.1f]"%(dests[i].name,volumes[i]) for i in range(len(dests))))
            print "*",cmt
            self.w.comment(cmt)

            if mix[0] and not src.isMixed:
                src.mix(tipMask,self.w)
            src.aspirate(tipMask,self.w,sum(volumes),True)
            for i in range(len(dests)):
                if volumes[i]>0.01:
                    dests[i].dispense(tipMask,self.w,volumes[i],src.conc)
                    dests[i].addhistory(src.name,volumes[i],tipMask)
            if self.useDiTis and dropDITI:
                self.w.dropDITI(tipMask&self.DITIMASK,self.WASTE)
        else:
            for i in range(len(dests)):
                if volumes[i]>0.01:
                    self.transfer(volumes[i],src,dests[i],(mix[0] and i==0,mix[1]),getDITI,dropDITI)

    def transfer(self, volume, src, dest, mix=(False,False), getDITI=True, dropDITI=True):
        if self.ptcrunning and (src.plate==Experiment.SAMPLEPLATE or dest.plate==Experiment.SAMPLEPLATE)>0:
            self.waitpgm()
        if volume>self.MAXVOLUME:
            destvol=max([d.volume for d in dests[0:i]])
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
        if mix[1] and dest.volume>0:
            cmt=cmt+" with dest mix"
            ditivolume=max(ditivolume,volume+dest.volume)
            #            print "Mix volume=%.1f ul"%(ditivolume)
        if self.useDiTis:
            tipMask=4
            if getDITI:
                self.w.getDITI(tipMask&self.DITIMASK,ditivolume)
        else:
            tipMask=self.cleantip()
        print "*",cmt
        self.w.comment(cmt)

        if mix[0] and not src.isMixed:
            src.mix(tipMask,self.w)
        src.aspirate(tipMask,self.w,volume)
        dest.dispense(tipMask,self.w,volume,src.conc)
        dest.addhistory(src.name,volume,tipMask)
        if mix[1]:
            dest.mix(tipMask,self.w)
        if self.useDiTis and dropDITI:
            self.w.dropDITI(tipMask&self.DITIMASK,self.WASTE)

    def stage(self,stagename,reagents,sources,samples,volume,finalx=1.0,destMix=True):
        # Add water to sample wells as needed (multi)
        # Pipette reagents into sample wells (multi)
        # Pipette sources into sample wells
        # Concs are in x (>=1)
        #        Sample.printallsamples("Before "+stagename)
        print "\nStage: ", stagename, "reagents=",[str(r) for r in reagents], ",sources=",[str(s) for s in sources],",samples=",[str(s) for s in samples],str(volume)
        if len(samples)==0:
            print "No samples\n"
            return

        self.w.comment(stagename)
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
            print "Error: Ingredients add up to more than desired volume;  need to add water=",watervols
            assert(False)

        if sum(watervols)>0.01:
            self.multitransfer(watervols,self.WATER,samples,(False,destMix and (len(reagents)+len(sources)==0)))

        for i in range(len(reagents)):
            self.multitransfer([reagentvols[i]*v for v in volume],reagents[i],samples,(True,destMix and (len(sources)==0 and i==len(reagents)-1)))

        if len(sources)>0:
            assert(len(sources)<=len(samples))
            for i in range(len(sources)):
                self.transfer(sourcevols[i],sources[i],samples[i],(True,destMix))


    def lihahome(self):
        'Move LiHa to left of deck'
        self.w.moveliha(self.WASHLOC)
        
    def runpgm(self,pgm,duration,waitForCompletion=True):
        # move to thermocycler
        self.lihahome()
        cmt="run %s"%pgm
        self.w.comment(cmt)
        print "*",cmt
        self.w.pyrun("PTC\\ptclid.py OPEN")
        self.w.vector("Microplate Landscape",self.SAMPLEPLATE,self.w.SAFETOEND,True,self.w.DONOTMOVE,self.w.CLOSE)
        self.w.vector("PTC200",self.PTCPOS,self.w.SAFETOEND,True,self.w.DONOTMOVE,self.w.OPEN)
        self.w.vector("Hotel 1 Lid",self.HOTELPOS,self.w.SAFETOEND,True,self.w.DONOTMOVE,self.w.CLOSE)
        self.w.vector("PTC200lid",self.PTCPOS,self.w.SAFETOEND,True,self.w.DONOTMOVE,self.w.OPEN)
        self.w.romahome()
        self.w.pyrun("PTC\\ptclid.py CLOSE")
        #        pgm="PAUSE30"  # For debugging
        self.w.pyrun('PTC\\ptcrun.py %s CALC ON'%pgm)
        self.thermotime+=duration*60+self.w.elapsed   # Add on elapsed time so we can cancel out intervening time in waitpgm()
        self.ptcrunning=True
        if waitForCompletion:
            self.waitpgm()
            
    def waitpgm(self):
        if not self.ptcrunning:
            return
        print "* Wait for PTC to finish"
        self.sanitize()   # Sanitize tips before waiting for this to be done
        self.thermotime-=self.w.elapsed
        self.w.pyrun('PTC\\ptcwait.py')
        self.w.pyrun("PTC\\ptclid.py OPEN")
        #        self.w.pyrun('PTC\\ptcrun.py %s CALC ON'%"COOLDOWN")
        #        self.w.pyrun('PTC\\ptcwait.py')
        self.w.vector("PTC200lid",self.PTCPOS,self.w.SAFETOEND,True,self.w.DONOTMOVE,self.w.CLOSE)
        self.w.vector("Hotel 1 Lid",self.HOTELPOS,self.w.SAFETOEND,True,self.w.DONOTMOVE,self.w.OPEN)

        self.w.vector("PTC200WigglePos",self.PTCPOS,self.w.SAFETOEND,False,self.w.DONOTMOVE,self.w.DONOTMOVE)
        self.w.vector("PTC200Wiggle",self.PTCPOS,self.w.SAFETOEND,False,self.w.DONOTMOVE,self.w.CLOSE,True)
        self.w.vector("PTC200Wiggle",self.PTCPOS,self.w.ENDTOSAFE,False,self.w.DONOTMOVE,self.w.OPEN,True)
        self.w.vector("PTC200WigglePos",self.PTCPOS,self.w.ENDTOSAFE,False,self.w.DONOTMOVE,self.w.DONOTMOVE)

        self.w.vector("PTC200",self.PTCPOS,self.w.SAFETOEND,True,self.w.DONOTMOVE,self.w.CLOSE)
        self.w.vector("Microplate Landscape",self.SAMPLEPLATE,self.w.SAFETOEND,True,self.w.DONOTMOVE,self.w.OPEN)
        # Verify plate is in place
        self.w.vector("Microplate Landscape",self.SAMPLEPLATE,self.w.SAFETOEND,False,self.w.DONOTMOVE,self.w.CLOSE)
        self.w.vector("Microplate Landscape",self.SAMPLEPLATE,self.w.ENDTOSAFE,False,self.w.OPEN,self.w.DONOTMOVE)
        self.w.romahome()
        self.ptcrunning=False
        #self.w.userprompt("Plate should be back on deck. Press return to continue")


    def dilute(self,samples,factor):
        for s in samples:
            s.dilute(factor)
