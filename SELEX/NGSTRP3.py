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
    #"BT919-W_theolib_X",
    #"BT919-W_theolib_XwTheo",
    #"BT920-W_tetlib_X",
    #"BT920-W_tetlib_XwTetra",
    #"BT921-W_neolib_X",
    #"BT921-W_neolib_XwNeo",
    #"BT922-W_codeinelib_X",
    #"BT922-W_codeinelib_XwCode",
    #"BT923-W_dopalib_X",
    #"BT923-W_dopalib_XwDopa",
    #"BT924-W_norlaudlib_X",
    #"BT924-W_norlaudlib_XwNor",
    "BT927-W_sTRSV_X_1",
    "BT925-W_tyrosinelib_X",
    "BT925-W_tyrosinelib_XwTyro",
    "BT926-W_sanglib_X",
    "BT926-W_sanglib_XwSang",
    "BT728-W_L2b8_X",
    "BT728-W_L2b8_XwTheo",  
    "BT927-W_sTRSV_X_2",  
]

srcprefix=["W"]*len(input)
ligprefix=["A"]*len(input)
srcsuffix=["X"]*len(input)
stem1=["N7"]*len(input)
ligate=True
nreplicates=[1]*len(input)
timepoints=[5,60]

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
            pcr=pcr+[(srcprefix[i]+srcsuffix[i],ligprefix[i]+srcsuffix[i],"REF")]
            stop=stop+["MStp"+srcsuffix[i]]
            

ligmaster=ligmaster*2
pcr=pcr*2
#print "srcs=",srcs
#print "tmplqpcr=",tmplqpcr
#print "ligmaster=",ligmaster
#print "pcr=",pcr
#print "stop=",stop

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
               

trp=TRP()

reagents=None



for iteration in range(2):
    print "Iteration ",iteration+1
    trp.e.w.setOptimization(False)

    if iteration==0:
        trp.addTemplates(input,stockconc=10.0/6.0,units="x",plate=Experiment.EPPENDORFS)   # Add a template
    else:   
        reagents=Sample.getAllOnPlate(Experiment.REAGENTPLATE)+Sample.getAllOnPlate(Experiment.EPPENDORFS)
        for r in reagents:
            if r.volume<=0:
                r.initvolume=-r.volume+r.plate.unusableVolume
        Sample.clearall()

    t71=trp.runT7Setup(theo=False,src=srcs*2,tgt=["%s.T%d"%(srcs[i],timepoints[j])  for j in range(len(timepoints)) for i in range(len(srcs))],vol=10,srcdil=10.0/6)
    timesofar=0
    for i in range(len(timepoints)):
        lastelapse=trp.e.w.elapsed
        trp.runT7Pgm(10,timepoints[i]-timesofar) # vol, duration
        timesofar=timesofar+timepoints[i]
        tp=trp.runT7Stop(theo=False,vol=10,tgt=t71[(i*len(srcs)):((i+1)*len(srcs))],stopmaster=stop)
        print "Dead time=%.1f min"%((trp.e.w.elapsed-lastelapse)/60.0)

    trp.diluteInPlace(tgt=t71,dil=5)

    # Dilute input samples enough to use in qPCR directly (should be 5000/(rnagain*2*5)  = 20)
    qpcrdil1=trp.runQPCRDIL(src=t71,tgt=[],vol=100,srcdil=20,dilPlate=True)   
    rt1=trp.runRT(pos=True,src=t71,tgt=[],vol=10,srcdil=2)
    rt1=trp.diluteInPlace(tgt=rt1,dil=5)
    lig1=trp.runLig(src=rt1,tgt=[],vol=25,srcdil=3,master=ligmaster)
    prods=trp.saveSamps(lig1,vol=5,dil=10,plate=Experiment.DILPLATE)
    
    trp.runQPCR(src=qpcrdil1,vol=15,srcdil=10.0/4,primers=["WX","REF"])
    trp.runQPCR(src=prods,vol=15,srcdil=10.0/4,primers=["WX","AX","REF"])
        
    
trp.finish()
