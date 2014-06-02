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
from TRPLib.TRP import findsamps
import debughook

# Configuration for this run (up to 15 total samples in reagent plate)
timepoints=[2,5,10,15,30,45,60,90,120]

input=[
    "A_L2b12_S@10nM",
    "A_L2b12_S@10nM+Theo"
]
srcprefix=["A"]*len(input)
ligprefix=["B"]*len(input)
srcsuffix=["S"]*len(input)
nreplicates=[1]*len(input)
stem1=["N7"]*len(input)
ligate=True
t7vol=10;

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
            pcr=pcr+[(srcprefix[i]+srcsuffix[i],ligprefix[i]+srcsuffix[i])]
            stop=stop+["MStp"+srcsuffix[i]]


alllig=[]
allpcr=[]
alltmplqpcr=[]
for i in range(len(timepoints)):
    alllig=alllig+ligmaster
    allpcr=allpcr+pcr
    alltmplqpcr=alltmplqpcr+tmplqpcr
    
ligmaster=alllig
pcr=allpcr
tmplqpcr=alltmplqpcr
    
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
    trp.e.w.setOptimization(True)

    if iteration==0:
        trp.addTemplates(input,stockconc=10.0/6.0,units="x",plate=Experiment.EPPENDORFS)   # Add a template
    else:   
        reagents=Sample.getAllOnPlate(Experiment.REAGENTPLATE)+Sample.getAllOnPlate(Experiment.EPPENDORFS)
        for r in reagents:
            if r.volume<=0:
                r.initvolume=-r.volume+r.plate.unusableVolume
        Sample.clearall()

    t71master=["%s.MT"%s for s in srcs]
    trp.runT7Setup(theo=False,src=srcs,tgt=t71master,vol=len(timepoints)*(t7vol*1.02+2)+1+15+20,srcdil=10.0/6)
    startTime=trp.e.w.elapsed
    t71=[]
    stopDelay=0*60
    for i in range(len(timepoints)):
        trp.e.sanitize()
        pauseTime=(timepoints[i]*60-(trp.e.w.elapsed-startTime)-stopDelay)
        if pauseTime>0:
            print "Pausing for %.1f minutes"%(pauseTime/60.0)
            trp.e.w.userprompt("Pausing to incubate first T7 at room temperature...",pauseTime)
        tp=trp.saveSamps(src=t71master,tgt=["%s.T%d"%(s,timepoints[i]) for s in srcs],vol=t7vol,dil=1,plate=trp.e.SAMPLEPLATE)
        trp.runT7Stop(theo=False,vol=t7vol,tgt=tp,stopmaster=stop)
        print "T7 stop %d done at %.1f minutes"%(i,(trp.e.w.elapsed-startTime)/60.0)
        trp.diluteInPlace(tgt=tp,dil=5)
        trp.e.w.flushQueue()
        t71=t71+tp
        

    # Dilute input samples enough to use in qPCR directly (should be 5000/(rnagain*2*5)  = 20)
    qpcrdil1=trp.runQPCRDIL(src=t71,tgt=[],vol=100,srcdil=20,dilPlate=False)   
    rt1=trp.runRT(pos=True,src=t71,tgt=[],vol=5,srcdil=2)
    rt1=trp.diluteInPlace(tgt=rt1,dil=5)
    lig1=trp.runLig(src=rt1,tgt=[],vol=10,srcdil=3,master=ligmaster)
    prods=trp.diluteInPlace(tgt=lig1,dil=10)
        
    for i in range(len(qpcrdil1)):
        trp.runQPCR(src=qpcrdil1[i],vol=15,srcdil=10.0/4,primers=[tmplqpcr[i]])
    for i in range(len(prods)):
        trp.runQPCR(src=[prods[i]],vol=15,srcdil=10.0/4,primers=pcr[i])

trp.finish()

