from worklist import *
from sample import *

#from .. import debughook

class Experiment(object):
    REAGENTPLATE=Plate("Reagents",3,1,12,8)
    SAMPLEPLATE=Plate("Samples",10,3,12,8)
    WATERLOC=Plate("Water",17,2,1,1)
    PTCPOS=Plate("PTC",25,1,1,1)
    HOTELPOS=Plate("Hotel",25,0,1,1)
    WASTE=Plate("Waste",19,3,1,1)

    WATER=Sample("Water",WATERLOC,0,None)

    RPTEXTRA=0.2   # Extra amount when repeat pipetting
    REAGENTEXTRA=5	# Absoute amount of extra in each supply well of reagents
    REAGENTFRAC=0.1	# Relative amount of extra in each supply well of reagents (use max of EXTRA and FRAC)

    def __init__(self):
        'Create a new experiment with given sample locations for water and self.WASTE'
        self.w=WorkList()

    def multitransfer(self, volumes, src, dests,mix=False):
        'Multi pipette from src to multiple dest'
        useMulti=False   # Disable for now, use single transfers
        if isinstance(volumes,(int,long,float)):
            # Same volume for each dest
            volumes=[volumes for i in range(len(dests))]
        assert(len(volumes)==len(dests))
        if useMulti and mix==False:
            cmt="Add  %s to samples %s"%(src.name,",".join("%s[%.1f]"%(dests[i].name,volumes[i]) for i in range(len(dests))))
            if mix:
                cmt=cmt+" with mix"
            print "*",cmt
            self.w.comment(cmt)
            v=sum(volumes)*(1+RPTEXTRA)
            self.w.getDITI(1,v)
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
        cmt="Add %.1f ul of %s to %s"%(volume, src.name, dest.name)
        if mix:
            cmt=cmt+" with mix"
        print "*",cmt
        self.w.comment(cmt)
        self.w.getDITI(1,volume)
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
            self.multitransfer(watervols,self.WATER,samples,len(sources)==0 and len(reagents)==0)

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
        self.w.execute("ptc200exec LID OPEN")
        self.w.vector("Microplate Landscape",self.SAMPLEPLATE,self.w.SAFETOEND,True,self.w.DONOTMOVE,self.w.CLOSE)
        self.w.vector("PTC200",self.PTCPOS,self.w.SAFETOEND,True,self.w.DONOTMOVE,self.w.OPEN)
        self.w.vector("Hotel 1 Lid",self.HOTELPOS,self.w.SAFETOEND,True,self.w.DONOTMOVE,self.w.CLOSE)
        self.w.vector("PTC200lid",self.PTCPOS,self.w.SAFETOEND,True,self.w.DONOTMOVE,self.w.OPEN)
        self.w.romahome()
        self.w.execute("ptc200exec LID CLOSE")
        self.w.execute('ptc200exec RUN "%s"'%pgm)
        self.w.execute('ptc200wait')


    def dilute(self,samples,factor):
        for s in samples:
            s.dilute(factor)

    def printsetup(self):
        print  "Preparation:"
        notes="Notes:"
        for s in allsamples:
            if s.volume<0:
                extra=max(self.REAGENTEXTRA,-self.REAGENTFRAC*s.volume)
                if s.conc!=None:
                    c="@%.2fx"%s.conc
                else:
                    c=""   
                note="%s%s in %s.%s consume %.1f ul, provide %.1f ul"%(s.name,c,str(s.plate),str(s.well),-s.volume,extra-s.volume)
                notes=notes+"\n"+note
        print notes

