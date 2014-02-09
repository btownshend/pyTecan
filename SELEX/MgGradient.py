# Run analytic TRP of a set of samples
from Experiment.sample import Sample
from Experiment.experiment import Experiment
import math
from TRPLib.TRP import TRP
import debughook

# Configuration for this run (up to 15 total samples including replicates)
input=["R55A","R54B","R47A","R39A","R31A","R23A","BT423","BT270"];
srcprefix=["A","B","A","A","A","A","A","A"];
nreplicates=[2,1,1,1,1,1,1,1];

# Setup replicated inputs
inputs=[];
srcprefixes=[];
prodprefixes=[];
for k in range(max(nreplicates)):
    for i in range(len(input)):
        if nreplicates[i]>k:
            inputs=inputs+[input[i]];
            srcprefixes=srcprefixes+[srcprefix[i]];
            if srcprefix[i]=='A':
                prodprefixes=prodprefixes+['B'];
            else:
                prodprefixes=prodprefixes+['A'];

reagents=None

for iteration in range(2):
    print "Iteration ",iteration+1
    trp=TRP()
    if iteration==0:
        trp.addTemplates(input,8)   # Add a template with stock concentration 8nM
    else:   
        reagents=Sample.getAllOnPlate(Experiment.REAGENTPLATE)
        for r in reagents:
            if r.volume<0:
                r.initvolume=-r.volume+20
        Sample.clearall()


    t71=trp.runT7(theo=[False for i in inputs]+[True for i in inputs],src=inputs+inputs,tgt=[],vol=10,srcdil=80.0/24,dur=15)
    trp.diluteInPlace(tgt=t71,dil=2)
    rt1=trp.runRT(pos=True,src=t71,tgt=[],vol=5,srcdil=2)
    trp.diluteInPlace(tgt=rt1,dil=4)
    lig1=trp.runLig(prefix=prodprefixes+prodprefixes,src=rt1,tgt=[],vol=10,srcdil=3)
    trp.diluteInPlace(tgt=lig1,dil=4)
    # Dilute input samples
    qpcrdil1=trp.runQPCRDIL(src=inputs,tgt=[],vol=100,srcdil=40,dilPlate=True)   
    diltohere=[6*40 for s in inputs]+[2*2*2*4*3*4 for s in lig1]  # Their dilution so far from the T7 product point (before stop added)
    dilneeded=[10000/d for d in diltohere]
    # trp.e.w.userprompt("Load QPCR plate and press return to start QPCR setup")
    qpcrdil2=trp.runQPCRDIL(src=qpcrdil1+lig1,tgt=[],vol=100,srcdil=dilneeded,dilPlate=True)
    trp.runQPCR(src=qpcrdil2,vol=15,srcdil=10.0/4)

trp.finish()

            
