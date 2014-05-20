# Run TRP analysis
# Runs normal TRP followed by qPCR and PCR
# Running +target achieved by second sample of input with target already added at 3.33x of final  concentration
# Handles arbitrary prefix/suffix
# Uses appropriate extension split master mix
from Experiment.sample import Sample
from Experiment.experiment import Experiment
from Experiment.experiment import Concentration
import math
from TRPLib.TRP import TRP
import debughook

# Configuration for this run (up to 15 total samples in reagent plate)
input=[
    "B_339612_S+theo",
]

srcprefix=["B"]*len(input)
ligprefix1=["A"]*len(input)
ligprefix2=["W"]*len(input)
srcsuffix=["S"]*len(input)
nreplicates=[1]*len(input)
stem1=["N7"]*len(ligprefix1)
ligate=True

# Setup replicated inputs
srcs=[]
tmplqpcr=[]
ligmaster1=[]
ligmaster2=[]
stop=[]
pcr1=[]
pcr2=[]
for k in range(max(nreplicates)):
    for i in range(len(input)):
        if nreplicates[i]>k:
            srcs=srcs+[input[i]]
            stop=stop+["MStp"+srcsuffix[i]]
            tmplqpcr=tmplqpcr+[srcprefix[i]+srcsuffix[i]]
            ligmaster1=ligmaster1+["MLig"+ligprefix1[i]+stem1[i]]
            pcr1=pcr1+[(srcprefix[i]+srcsuffix[i],ligprefix1[i]+srcsuffix[i])]
            ligmaster2=ligmaster2+["MLig"+ligprefix2[i]+stem1[i]]
            pcr2=pcr2+[(srcprefix[i]+srcsuffix[i],ligprefix2[i]+srcsuffix[i])]

print "srcs=",srcs
print "tmplqpcr=",tmplqpcr
print "ligmaster1=",ligmaster1
print "pcr1=",pcr1
print "ligmaster2=",ligmaster2
print "pcr2=",pcr2

# Create ligation master mix samples
for lm in set(ligmaster1+ligmaster2):
    if Sample.lookup(lm)==None:
        Sample(lm,Experiment.REAGENTPLATE,None,3)

for st in set(stop):
    if Sample.lookup(st)==None:
        Sample(st,Experiment.REAGENTPLATE,None,2)

for p in pcr1+pcr2:
    for pm in p:
        if Sample.lookup("MQ"+pm)==None:
            Sample("MQ"+pm,Experiment.REAGENTPLATE,None,10.0/6)

for pm in tmplqpcr:
    if Sample.lookup("MQ"+pm)==None:
        Sample("MQ"+pm,Experiment.REAGENTPLATE,None,10.0/6)
    
reagents=None


for iteration in range(2):
    print "Iteration ",iteration+1
    trp=TRP()

    if iteration==0:
        trp.addTemplates(input,stockconc=10.0/6.0,units="x",plate=Experiment.EPPENDORFS)   # Add a template
    else:   
        reagents=Sample.getAllOnPlate(Experiment.REAGENTPLATE)+Sample.getAllOnPlate(Experiment.EPPENDORFS)
        for r in reagents:
            if r.volume<=0:
                r.initvolume=-r.volume+r.plate.unusableVolume
        Sample.clearall()

    t71=trp.runT7(theo=False,src=srcs,tgt=[],vol=10,srcdil=10.0/6,dur=15,stopmaster=stop)
    #print t71
    t71=trp.diluteInPlace(tgt=t71,dil=5)
    # Dilute input samples enough to use in qPCR directly (should be 5000/(rnagain*2*5)  = 20)
    qpcrdil1=trp.runQPCRDIL(src=t71,tgt=[],vol=100,srcdil=20,dilPlate=True)
    
    rt1=trp.runRT(pos=True,src=t71,tgt=[],vol=30,srcdil=2)
    rt1=trp.diluteInPlace(tgt=rt1,dil=5)
    
    lig=trp.runLig(src=rt1*6,tgt=[],vol=20,srcdil=3,master=ligmaster1*3+ligmaster2*3)
    prods=trp.diluteInPlace(tgt=lig,dil=10)
    print "prod=",prods
    for i in range(len(qpcrdil1)):
        trp.runQPCR(src=qpcrdil1[i],vol=15,srcdil=10.0/4,primers=[tmplqpcr[i]])

    for p in pcr1:
        trp.runQPCR(src=prods[0:3],vol=15,srcdil=10.0/4,primers=p,nreplicates=3)
    for p in pcr2:
        trp.runQPCR(src=prods[3:6],vol=15,srcdil=10.0/4,primers=p,nreplicates=3)

trp.finish()

