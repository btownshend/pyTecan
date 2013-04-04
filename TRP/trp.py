from worklist import *
from sample import *

import copy

#from .. import debughook

REAGENTPLATE=Plate("Reagents",3,1,12,8)
SAMPLEPLATE=Plate("Samples",10,3,12,8)
WATERLOC=Plate("Water",17,2,1,1)
PTCPOS=Plate("PTC",25,1,1,1)
HOTELPOS=Plate("Hotel",25,0,1,1)
WASTE=Plate("Waste",19,3,1,1)
RPTEXTRA=0.2   # Extra amount when repeat pipetting
REAGENTEXTRA=5	# Absoute amount of extra in each supply well of reagents
REAGENTFRAC=0.1	# Relative amount of extra in each supply well of reagents (use max of EXTRA and FRAC)


WATER=Sample("Water",WATERLOC,0,None)

def multitransfer(w, volumes, src, dests,mix=False):
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
        w.comment(cmt)
        v=sum(volumes)*(1+RPTEXTRA)
        w.getDITI(1,v)
        src.aspirate(w,v)
        for i in range(len(dests)):
            if volumes[i]>0:
                dests[i].dispense(w,volumes[i],src.conc)
                dests[i].addhistory(src.name,volumes[i])
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
    dest.addhistory(src.name,volume)
    if mix:
        dest.mix(w)
    w.dropDITI(1,WASTE)

def stage(w,reagents,sources,samples,volume):
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


def runpgm(pgm):
    # move to thermocycler
    cmt="run %s"%pgm
    w.comment(cmt)
    print "*",cmt
    w.execute("ptc200exec LID OPEN")
    w.vector("Microplate Landscape",SAMPLEPLATE,w.SAFETOEND,True,w.DONOTMOVE,w.CLOSE)
    w.vector("PTC200",PTCPOS,w.SAFETOEND,True,w.DONOTMOVE,w.OPEN)
    w.vector("Hotel 1 Lid",HOTELPOS,w.SAFETOEND,True,w.DONOTMOVE,w.CLOSE)
    w.vector("PTC200lid",PTCPOS,w.SAFETOEND,True,w.DONOTMOVE,w.OPEN)
    w.romahome()
    w.execute("ptc200exec LID CLOSE")
    w.execute('ptc200exec RUN "%s"'%pgm)
    w.execute('ptc200wait')


def t7(w,reagents,templates,samples,volume):
    w.comment('T7')
    stage(w,reagents,templates,samples,volume)

def stop(w,reagents,samples,volume):
    w.comment('STOP')
    stage(w,reagents,[],samples,volume)

def rt(w,reagents,sources,samples,volume):
    w.comment('RT')
    stage(w,reagents, sources,samples,volume)

def dilute(w,samples,factor):
    for s in samples:
        s.dilute(factor)

def printallsamples(txt=""):
    print "\n%s:"%txt
    for s in allsamples:
        print s
    print ""
    
def printsetup():
    print  "Preparation:"
    notes="Notes:"
    for s in allsamples:
        if s.volume<0:
            extra=max(REAGENTEXTRA,-REAGENTFRAC*s.volume)
            if s.conc!=None:
                c="@%.2fx"%s.conc
            else:
                c=""   
            note="%s%s in %s.%s consume %.1f ul, provide %.1f ul"%(s.name,c,str(s.plate),str(s.well),-s.volume,extra-s.volume)
            notes=notes+"\n"+note
    print notes

w=WorkList()
rpos=0; spos=0;
S_T7=Sample("M-T7",REAGENTPLATE,rpos,2); rpos=rpos+1
S_Theo=Sample("Theo",REAGENTPLATE,rpos,25/7.5); rpos=rpos+1
S_L2b12=Sample("L2b12",REAGENTPLATE,rpos,10); rpos=rpos+1
S_L2b12Cntl=Sample("L2b12Cntl",REAGENTPLATE,rpos,10); rpos=rpos+1
S_Stop=Sample("M-Stp",REAGENTPLATE,rpos,2); rpos=rpos+1
S_MRT=Sample("M-RT",REAGENTPLATE,rpos,2); rpos=rpos+1
S_MRTNeg=Sample("M-RTNeg",REAGENTPLATE,rpos,2); rpos=rpos+1
S_LIGB=Sample("M-LIGB",REAGENTPLATE,rpos,1.25); rpos=rpos+1
S_LIGASE=Sample("M-LIGASE",REAGENTPLATE,rpos,2); rpos=rpos+1

nT7=3
S_R1_T7=[Sample("R1.T7.%d"%i,SAMPLEPLATE,i+spos) for i in range(nT7)]; spos=spos+nT7

nRT=nT7
S_R1_RTPos=[Sample("R1.RT.%d"%i,SAMPLEPLATE,i+spos) for i in range(nRT)]; spos=spos+nRT
S_R1_RTNeg=[Sample("R1.RTNeg.%d"%i,SAMPLEPLATE,i+spos) for i in range(nRT)]; spos=spos+nRT
S_R1_RT=copy.copy(S_R1_RTPos)
S_R1_RT.extend(S_R1_RTNeg)

nExt=nRT*2
S_R1_EXT=[Sample("R1.EXT.%d"%i,SAMPLEPLATE,i+spos) for i in range(nExt)]; spos=spos+nRT

scale=1   # Overall scale of reactions

printallsamples("Before T7")
t7(w,[S_T7,S_Theo],[S_L2b12,S_L2b12,S_L2b12Cntl],S_R1_T7,10*scale)
runpgm("37-15MIN")

printallsamples("Before Stop")
dilute(w,S_R1_T7,2)
stop(w,[S_Stop],S_R1_T7,20*scale)

printallsamples("Before RT")
dilute(w,S_R1_T7,2)
rt(w,[S_MRT],S_R1_T7,S_R1_RTPos,5*scale)
rt(w,[S_MRTNeg],S_R1_T7,S_R1_RTNeg,5*scale)
runpgm("TRP-SS")

printallsamples("Before Ligation")
dilute(w,S_R1_RT,5)
stage(w,[S_LIGB],S_R1_RT,S_R1_EXT,10*scale)
runpgm("TRP-ANNEAL")
dilute(w,S_R1_EXT,2)
stage(w,[S_LIGASE],[],S_R1_EXT,20*scale)

printallsamples("After Ligation")

printsetup()

w.save("trp.gwl")
