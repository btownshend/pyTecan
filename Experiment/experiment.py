from worklist import *
from sample import Sample

#from .. import debughook

class Experiment(object):
    REAGENTPLATE=Plate("Reagents",3,1,12,8)
    SAMPLEPLATE=Plate("Samples",10,3,12,8)
    QPCRPLATE=Plate("qPCR",10,2,12,8)
    WATERLOC=Plate("Water",17,2,1,4)
    PTCPOS=Plate("PTC",25,1,1,1)
    HOTELPOS=Plate("Hotel",25,0,1,1)
    WASTE=Plate("Waste",19,3,1,1)

    WATER=Sample("Water",WATERLOC,0,None)

    RPTEXTRA=0   # Extra amount when repeat pipetting
    MAXVOLUME=200  # Maximum volume for pipetting in ul

    def __init__(self):
        'Create a new experiment with given sample locations for water and self.WASTE'
        self.w=WorkList()
        self.w.wash(15)
        
    def setreagenttemp(self,temp=None):
        if temp==None:
            self.w.pyrun("RIC\\ricset.py IDLE")
        else:
            self.w.pyrun("RIC\\ricset.py %f"%temp)

    def saveworklist(self,filename):
        self.w.saveworklist(filename)

    def savegem(self,headerfile,filename):
        self.w.savegem(headerfile,filename)
        
    def savesummary(self,filename):
        # Print amount of samples needed
        fd=open(filename,"w")
        print >>fd,"Deck layout:"
        print >>fd,self.REAGENTPLATE
        print >>fd,self.SAMPLEPLATE
        print >>fd,self.QPCRPLATE
        print >>fd,self.WATERLOC
        print >>fd,self.WASTE
        print >>fd
        print >>fd,"DiTi usage:",self.w.getDITIcnt()
        print >>fd
        Sample.printprep(fd)
        Sample.printallsamples("All Samples:",fd)
        
    def multitransfer(self, volumes, src, dests,mix=False):
        'Multi pipette from src to multiple dest'
        useMulti=True   # Disable for now, use single transfers
        if isinstance(volumes,(int,long,float)):
            # Same volume for each dest
            volumes=[volumes for i in range(len(dests))]
        assert(len(volumes)==len(dests))
        if useMulti and mix==False and len(volumes)>1:
            if sum(volumes)>self.MAXVOLUME:
                print "sum(volumes)=%.1f, MAXVOL=%.1f"%(sum(volumes),self.MAXVOLUME)
                for i in range(1,len(volumes)):
                    if sum(volumes[0:i+1])>self.MAXVOLUME:
                        print "Splitting multi with total volume of %.1f ul into smaller chunks < %.1f ul after %d dispenses"%(sum(volumes),self.MAXVOLUME,i)
                        self.multitransfer(volumes[0:i],src,dests[0:i],mix)
                        self.multitransfer(volumes[i:],src,dests[i:],mix)
                        return
                    
            cmt="Multi-add  %s to samples %s"%(src.name,",".join("%s[%.1f]"%(dests[i].name,volumes[i]) for i in range(len(dests))))
            if mix:
                cmt=cmt+" with mix"
            print "*",cmt
            self.w.comment(cmt)
            v=sum(volumes)*(1+self.RPTEXTRA)
            self.w.getDITI(1,v,True,True)
            src.aspirate(self.w,v)
            for i in range(len(dests)):
                if volumes[i]>0:
                    dests[i].dispense(self.w,volumes[i],src.conc)
                    dests[i].addhistory(src.name,volumes[i])
            self.w.dropDITI(1,self.WASTE)
        else:
            for i in range(len(dests)):
                self.transfer(volumes[i],src,dests[i],mix)

    def transfer(self, volume, src, dest, mix=False):
        if volume>self.MAXVOLUME:
            print "Splitting large transfer of %.1f ul into smaller chunks < %.1f ul"%(volume,self.MAXVOLUME)
            self.transfer(self.MAXVOLUME,src,dest,mix)
            self.transfer(volume-self.MAXVOLUME,src,dest,mix)
            return
        
        cmt="Add %.1f ul of %s to %s"%(volume, src.name, dest.name)
        ditivolume=volume
        if mix:
            cmt=cmt+" with mix"
            ditivolume=max(volume,volume+dest.volume)
            print "Mix volume=%.1f ul"%(ditivolume)
        print "*",cmt
        self.w.comment(cmt)
        self.w.getDITI(1,ditivolume)
        src.aspirate(self.w,volume)
        dest.dispense(self.w,volume,src.conc)
        dest.addhistory(src.name,volume)
        if mix:
            dest.mix(self.w)
        self.w.dropDITI(1,self.WASTE)

    def stage(self,stagename,reagents,sources,samples,volume):
        # Add water to sample wells as needed (multi)
        # Pipette reagents into sample wells (multi)
        # Pipette sources into sample wells
        # Concs are in x (>=1)
        Sample.printallsamples("Before "+stagename)
        self.w.comment(stagename)
        assert(volume>0)
        volume=float(volume)
        reagentvols=[volume/x.conc for x in reagents]
        if len(sources)>0:
            sourcevols=[volume/x.conc for x in sources]
            watervols=[volume-sum(reagentvols)-samples[i].volume-sourcevols[i] for i in range(len(samples))]
        else:
            watervols=[volume-sum(reagentvols)-samples[i].volume for i in range(len(samples))]

        assert(min(watervols)>=0)
        if sum(watervols)>0:
            self.multitransfer(watervols,self.WATER,samples,False)

        for i in range(len(reagents)):
            self.multitransfer(reagentvols[i],reagents[i],samples,len(sources)==0)

        if len(sources)>0:
            assert(len(sources)==len(samples))
            for i in range(len(sources)):
                self.transfer(sourcevols[i],sources[i],samples[i],True)


    def runpgm(self,pgm):
        # move to thermocycler
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
        pgm="PAUSE30"  # For debugging
        self.w.pyrun('PTC\\ptcrun.py %s CALC ON'%pgm)
        self.w.pyrun('PTC\\ptcwait.py')
        self.w.pyrun("PTC\\ptclid.py OPEN")
        self.w.vector("PTC200lid",self.PTCPOS,self.w.SAFETOEND,True,self.w.DONOTMOVE,self.w.CLOSE)
        self.w.vector("Hotel 1 Lid",self.HOTELPOS,self.w.SAFETOEND,True,self.w.DONOTMOVE,self.w.OPEN)
        self.w.vector("PTC200",self.PTCPOS,self.w.SAFETOEND,True,self.w.DONOTMOVE,self.w.CLOSE)
        self.w.vector("Microplate Landscape",self.SAMPLEPLATE,self.w.SAFETOEND,True,self.w.DONOTMOVE,self.w.OPEN)
        self.w.romahome()


    def dilute(self,samples,factor):
        for s in samples:
            s.dilute(factor)
