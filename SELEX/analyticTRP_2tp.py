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

# Configuration for this run (up to 16  total samples in reagent plate)
input=[
    "BT809",
    "BT810",
    "BT811",
    "BT812",
    "BT815",
    "BT818",
    "BT823",
    "BT829",
    "BT830",
    "BT832",
    "BT833",
    "BT834",
    "BT835",
    "BT837",
    "BT838",
    "BT840",
]
srcprefix="W"
ligprefix="A"
srcsuffix="X"
stem1="N7"
ligate=True
nreplicates=[1]*len(input)
timepoints=[10,60]

# Setup replicated inputs
ligmaster="MLig"+ligprefix+stem1
stop="MStp"+srcsuffix

srcs=[]
for k in range(max(nreplicates)):
    for i in range(len(input)):
        if nreplicates[i]>k:
            srcs=srcs+[input[i]]

tmplqpcr=[srcprefix+srcsuffix]
pcr=[srcprefix+srcsuffix,ligprefix+srcsuffix]
print "srcs=",srcs
print "tmplqpcr=",tmplqpcr
print "ligmaster=",ligmaster
print "pcr=",pcr
print "stop=",stop

# Create ligation master mix samples
if Sample.lookup(ligmaster)==None:
	Sample(ligmaster,Experiment.REAGENTPLATE,None,3)

if Sample.lookup(stop)==None:
    Sample(stop,Experiment.REAGENTPLATE,None,2)

for pm in pcr:
    if Sample.lookup("MQ"+pm)==None:
        Sample("MQ"+pm,Experiment.REAGENTPLATE,None,10.0/6)

for pm in tmplqpcr:
    if Sample.lookup("MQ"+pm)==None:
        Sample("MQ"+pm,Experiment.REAGENTPLATE,None,10.0/6)
    
reagents=None


for iteration in range(2):
    print "Iteration ",iteration+1
    trp=TRP()
    trp.e.w.setOptimization(True)

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
        trp.runT7Pgm(10,timepoints[i]-timesofar)
        timesofar=timesofar+timepoints[i]
        tp=trp.runT7Stop(theo=False,vol=10,tgt=t71[(i*len(srcs)):((i+1)*len(srcs))],stopmaster=stop)
        print "Dead time=%.1f min"%((trp.e.w.elapsed-lastelapse)/60.0)

    trp.diluteInPlace(tgt=t71,dil=5)
    print t71

    # Dilute input samples enough to use in qPCR directly (should be 5000/(rnagain*2*5)  = 20)
    qpcrdil1=trp.runQPCRDIL(src=t71,tgt=[],vol=100,srcdil=20,dilPlate=True)   
    rt1=trp.runRT(pos=True,src=t71,tgt=[],vol=5,srcdil=2)
    rt1=trp.diluteInPlace(tgt=rt1,dil=5)
    lig1=trp.runLig(src=rt1,tgt=[],vol=10,srcdil=3,master=ligmaster)
    prods=trp.diluteInPlace(tgt=lig1,dil=10)
        
    print "qpcrdil1=",qpcrdil1
    trp.runQPCR(src=qpcrdil1,vol=15,srcdil=10.0/4,primers=tmplqpcr)
    print "prods=",prods
    trp.runQPCR(src=prods,vol=15,srcdil=10.0/4,primers=pcr)

trp.finish()

