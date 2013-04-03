from worklist import *
import sitecustomize

REAGENTPLATE=Plate("Reagents",3,1,12,8)
SAMPLEPLATE=Plate("Samples",10,3,12,8)
WATERLOC=Plate("Water",17,2,1,1)
PTCPOS=Plate("PTC",25,1,1,1)

WASTE=Plate("Waste",19,3,1,1)
RPTEXTRA=0.2   # Extra amount when repeat pipetting

allsamples=[]

class Sample(object):
    def __init__(self,name,plate,well,conc=None,volume=0,liquidClass="Water-LV"):
        for s in allsamples:
            if s.plate==plate and s.well==well:
                print "Aliasing %s as %s"%(s.name,name)
                assert(False)
                
        self.name=name
        self.plate=plate
        self.well=well
        self.conc=conc
        self.volume=volume
        self.liquidClass=liquidClass
        allsamples.append(self)
        
    def dilute(self,factor):
        'Dilute sample -- just increases its recorded concentration'
        self.conc=self.conc*factor

    def aspirate(self,w,volume):
        w.aspirate([self.well],self.liquidClass,volume,self.plate)
        self.volume=self.volume-volume
        if self.volume<0:
            print "Warning: %s is now short by %.1f ul"%(self.name,-self.volume)
            
    def dispense(self,w,volume,conc):
        w.dispense([self.well],self.liquidClass,volume,self.plate)
        # Assume we're diluting the contents
        if self.conc==None and conc==None:
            pass
        elif conc==None or volume==0:
            self.conc=(self.conc*self.volume)/(self.volume+volume)
        elif self.conc==None or self.volume==0:
            self.conc=(conc*volume)/(self.volume+volume)
        else:
            # Both have concentrations, they should match
            c1=(self.conc*self.volume)/(self.volume+volume)
            c2=(conc*volume)/(self.volume+volume)
            assert(c1==c2)
            self.conc=c1

        self.volume=self.volume+volume

    def mix(self,w):
        w.mix([self.well],self.liquidClass,self.volume*0.9,self.plate,3)

    def __str__(self):
        if self.conc==None:
            return "%s(%s.%s,%.2f ul,LC=%s)"%(self.name,str(self.plate),str(self.well),self.volume,self.liquidClass)
        else:
            return "%s(%s.%s,%.2fx,%.2f ul,LC=%s)"%(self.name,str(self.plate),str(self.well),self.conc,self.volume,self.liquidClass)

WATER=Sample("Water",WATERLOC,0,None)

def multitransfer(w, volumes, src, dests,mix=False):
    'Multi pipette from src to multiple dest'
    useMulti=False   # Disable for now, use single transfers
    if isinstance(volumes,(int,long,float)):
        # Same volume for each dest
        volumes=[volumes for i in range(len(dests))]
    assert(len(volumes)==len(dests))
    cmt="Add  %s to samples %s"%(src.name,",".join("%s[%.1f]"%(dests[i].name,volumes[i]) for i in range(len(dests))))
    if mix:
        cmt=cmt+" with mix"
    print "*",cmt
    w.comment(cmt)
    if useMulti and mix==False:
        v=sum(volumes)*(1+RPTEXTRA)
        w.getDITI(1,v)
        src.aspirate(w,v)
        for i in range(len(dests)):
            if volumes[i]>0:
                dests[i].dispense(w,volumes[i],src.conc)
        w.dropDITI(1,WASTE)
    else:
        for i in range(len(dests)):
            transfer(w,volumes[i],src,dests[i],mix)

def transfer(w, volume, src, dest, mix=False):
    cmt="Add %.1f ul of %s to %s"%(volume, src.name, dest.name)
    if mix:
        cmt=cmt+" with mix"
    print "*",cmt
    w.comment(cmt)
    w.getDITI(1,volume)
    src.aspirate(w,volume)
    dest.dispense(w,volume,src.conc)
    if mix:
        dest.mix(w)
    w.dropDITI(1,WASTE)

def stage(w,reagents,sources,samples,volume,pgm=None):
    # Add water to sample wells as needed (multi)
    # Pipette reagents into sample wells (multi)
    # Pipette sources into sample wells
    # Concs are in x (>=1)
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
        multitransfer(w,watervols,WATER,samples,len(sources)==0 and len(reagents)==0)

    for i in range(len(reagents)):
        multitransfer(w,reagentvols[i],reagents[i],samples,len(sources)==0)

    if len(sources)>0:
        assert(len(sources)==len(samples))
        for i in range(len(sources)):
            transfer(w,sourcevols[i],sources[i],samples[i],True)

    if pgm!=None:
        # move to thermocycler
        w.execute("ptc200exec LID OPEN")
        w.vector("sample",SAMPLEPLATE,w.SAFETOEND,True,w.DONOTMOVE,w.CLOSE)
        w.vector("ptc200",PTCPOS,w.SAFETOEND,True,w.DONOTMOVE,w.OPEN)
        w.romahome()
        w.execute("ptc200exec LID CLOSE")
        w.execute('ptc200exec RUN "%s"'%pgm)
        w.execute('ptc200wait')


def t7(w,reagents,templates,samples,volume):
    w.comment('T7')
    stage(w,reagents,templates,samples,volume,"30-15MIN")

def stop(w,reagents,samples,volume):
    w.comment('STOP')
    for s in samples:
        s.dilute(2)
    stage(w,reagents,[],samples,volume)

def rt(w,reagents,sources,samples,volume):
    w.comment('RT')
    for s in sources:
        s.dilute(2)
    stage(w,reagents, sources,samples,volume,"TRP-SS")

def printallsamples(txt=""):
    print "\n%s:"%txt
    for s in allsamples:
        print s
    print ""
    
w=WorkList()
rpos=0; spos=0;
S_T7=Sample("M-T7",REAGENTPLATE,rpos,2); rpos=rpos+1
S_Theo=Sample("Theo",REAGENTPLATE,rpos,25/7.5); rpos=rpos+1
S_MRT=Sample("M-RT",REAGENTPLATE,rpos,2); rpos=rpos+1
S_Stop=Sample("M-Stp",REAGENTPLATE,rpos,2); rpos=rpos+1
S_L2b12=Sample("L2b12",REAGENTPLATE,rpos,10); rpos=rpos+1
S_L2b12Cntl=Sample("L2b12Cntl",REAGENTPLATE,rpos,10); rpos=rpos+1
nT7=3
S_R1_T7=[Sample("R1.T7.%d"%i,SAMPLEPLATE,i+spos) for i in range(nT7)]; spos=spos+nT7
nRT=nT7
S_R1_RT=[Sample("R1.RT.%d"%i,SAMPLEPLATE,i+spos) for i in range(nRT)]; spos=spos+nRT
scale=1
printallsamples("Before T7")
t7(w,[S_T7,S_Theo],[S_L2b12,S_L2b12,S_L2b12Cntl],S_R1_T7,10*scale)
printallsamples("Before Stop")
stop(w,[S_Stop],S_R1_T7,20*scale)
printallsamples("Before RT")
rt(w,[S_MRT],S_R1_T7,S_R1_RT,5*scale)
printallsamples("After RT")

print  "Preparation:"
for s in allsamples:
    if s.volume<0:
        if s.conc!=None:
            print "%s@%.2fx in %s.%s consume %.1f ul"%(s.name,s.conc,str(s.plate),str(s.well),-s.volume)
        else:
            print "%s in %s.%s consume %.1f ul"%(s.name,str(s.plate),str(s.well),-s.volume)
        
w.save("trp.gwk")
