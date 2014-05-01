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
    "W_tetracycline_AAAATGA_X",
    "W_tetracycline_AAAATGA_X+tet",
    "W_tetracycline_TGAAGTT_X",
    "W_tetracycline_TGAAGTT_X+tet",
    "W_GGATTGC_tetracycline_X",
    "W_GGATTGC_tetracycline_X+tet",
    "W_TGGTTGG_tetracycline_X",
    "W_TGGTTGG_tetracycline_X+tet",
    "W_TGCATGG_tetracycline_X", 
    "W_TGCATGG_tetracycline_X+tet",
    "W_AGGGGGT_guanine_X",
    "W_AGGGGGT_guanine_X+guanine",
    "W_guanine_TGGGAGT_X",
    "W_guanine_TGGGAGT_X+guanine",
    "W_L2b8_X",
    "W_L2b8_X+theo",
]
srcprefix=["W"]*len(input)
ligprefix=["A"]*len(input)
srcsuffix=["X"]*len(input)
nreplicates=[1]*len(input)
stem1=["N7"]*len(input)
ligate=True

# Setup replicated inputs
srcs=[]
tmplqpcr=[]
ligmaster=[]
stop=[]
pcr=[]
for k in range(max(nreplicates)):
    for i in range(len(input)):
        if nreplicates[i]>k:
            srcs=srcs+[input[i]]
            tmplqpcr=tmplqpcr+[srcprefix[i]+srcsuffix[i]]
            ligmaster=ligmaster+["MLig"+ligprefix[i]+stem1[i]]
            pcr=pcr+[(srcprefix[i]+srcsuffix[i],ligprefix[i]+srcsuffix[i])];
            stop=stop+["MStp"+srcsuffix[i]];

#print srcs
#print tmplqpcr
#print ligmaster
#print pcr

# Create ligation master mix samples
for lm in set(ligmaster):
    if Sample.lookup(lm)==None:
        Sample(lm,Experiment.REAGENTPLATE,None,3)

for st in set(stop):
    if Sample.lookup(st)==None:
        Sample(st,Experiment.REAGENTPLATE,None,2)

for p in pcr:
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
    rt1=trp.runRT(pos=True,src=t71,tgt=[],vol=5,srcdil=2)
    rt1=trp.diluteInPlace(tgt=rt1,dil=5)
    lig1=trp.runLig(src=rt1,tgt=[],vol=10,srcdil=3,master=ligmaster)
    prods=trp.diluteInPlace(tgt=lig1,dil=10)
        
    for i in range(len(qpcrdil1)):
        trp.runQPCR(src=qpcrdil1[i],vol=15,srcdil=10.0/4,primers=[tmplqpcr[i]])
    for i in range(len(prods)):
        trp.runQPCR(src=[prods[i]],vol=15,srcdil=10.0/4,primers=pcr[i])

trp.finish()

