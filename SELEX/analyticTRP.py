# Run analytic TRP of a set of samples
from Experiment.sample import Sample
from Experiment.experiment import Experiment
import math
from TRPLib.TRP import TRP
import debughook

# Configuration for this run (up to 15 total samples including replicates, 10 if also using QM)
input=["BT423","R4A","R8A","528","530","531","BT532","BT533","BT534","BT535"]
srcprefix=["A","A","A","A","A","A","A","A","A","A"];
nreplicates=[1,1,1,1,1,1,1,1,1,1];

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
        trp.addTemplates(input,2)   # Add a template with stock concentration 8nM
    else:   
        reagents=Sample.getAllOnPlate(Experiment.REAGENTPLATE)
        for r in reagents:
            if r.volume<0:
                r.initvolume=-r.volume+20
        Sample.clearall()


#    t71=trp.runT7(theo=[False for i in inputs]+[True for i in inputs],src=inputs+inputs,tgt=[],vol=10,srcdil=80.0/24,dur=15)
    t71=trp.runT7(theo=[y for x in inputs for y in [False,True]],src=[x for x in inputs for y in [False,True]],tgt=[],vol=10,srcdil=80.0/24,dur=15)
    rt1=trp.runRT(pos=True,src=t71,tgt=[],vol=5,srcdil=2)
    trp.diluteInPlace(tgt=rt1,dil=4)
    lig1=trp.runLig(prefix=prodprefixes+prodprefixes,src=rt1,tgt=[],vol=10,srcdil=3)

    # Dilute input samples (can do this while ligation is still running)
    qpcrdil1=trp.runQPCRDIL(src=inputs,tgt=[],vol=100,srcdil=40,dilPlate=True)   

    # Dilute positive ligation products (this will wait for PTC to finish)
    poslig=[s for s in lig1 if s[0:3]!="Neg"]
    # Less further dilution for negative ligation products (use directly in qPCR)
    neglig=[s for s in lig1 if s[0:3]=="Neg"]
    trp.diluteInPlace(tgt=poslig,dil=10)
    trp.diluteInPlace(tgt=neglig,dil=3)

    # Compute remaining dilution needed
    # Assume 25x RNA:DNA gain (needed to reduce dilution of DNA)
    diltohere=[24/80.0 * 25 *40 for s in qpcrdil1]+[2*2*4*3*10 for s in poslig]  # Their dilution so far from the T7 product point (before stop added)
    dilneeded=[5000.0/d for d in diltohere]

    trp.e.w.userprompt("Load QPCR plate and press return to start QPCR setup")
    qpcrdil2=trp.runQPCRDIL(src=qpcrdil1+poslig,tgt=[],vol=100,srcdil=dilneeded,dilPlate=True)
    trp.runQPCR(src=qpcrdil2+neglig,vol=15,srcdil=10.0/4,useMid=True)

trp.finish()

