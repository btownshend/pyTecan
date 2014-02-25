# Run analytic TRP of a set of samples
from Experiment.sample import Sample
from Experiment.experiment import Experiment
import math
from TRPLib.TRP import TRP
import debughook

# Configuration for this run (up to 15 total samples in reagent plate)
input=["BT537","BT576","BT577","BT578","BT579","BT580","BT581","BT582","BT583","BT584","BT585","BT586","BT587","BT588","BT589"]
srcprefix=["A","A","A","A","A","A","A","A","A","A","A","A","A","A","A"]
nreplicates=[1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
plustheo=[1,0,0,0,0,0,0,0,0,1,1,1,1,1,1]

stockConc=10
#primers=["A","M"]
ligate=True
primers=["A","B","M"]

# Setup replicated inputs
srcs=[]
theo=[]
srcprefixes=[]
prodprefixes=[]
for k in range(max(nreplicates)):
    for i in range(len(input)):
        if nreplicates[i]>k:
            srcs=srcs+[input[i]]
            theo=theo+[False]
            srcprefixes=srcprefixes+[srcprefix[i]]
            if srcprefix[i]=='A':
                prodprefixes=prodprefixes+['B']
            else:
                prodprefixes=prodprefixes+['A']
            if plustheo[i]:
                srcs=srcs+[input[i]]
                theo=theo+[True]
                srcprefixes=srcprefixes+[srcprefix[i]]
                if srcprefix[i]=='A':
                    prodprefixes=prodprefixes+['B'];
                else:
                    prodprefixes=prodprefixes+['A'];
                    
                
reagents=None

for iteration in range(2):
    print "Iteration ",iteration+1
    trp=TRP()
    if iteration==0:
        trp.addTemplates(input,stockConc,stockConc*24/80,plate=Experiment.EPPENDORFS)   # Add a template
    else:   
        reagents=Sample.getAllOnPlate(Experiment.REAGENTPLATE)+Sample.getAllOnPlate(Experiment.EPPENDORFS)
        for r in reagents:
            if r.volume<0:
                r.initvolume=-r.volume+20
        Sample.clearall()

    t71=trp.runT7(theo=theo,src=srcs,tgt=[],vol=10,srcdil=80.0/24,dur=15)
    t71=trp.diluteInPlace(tgt=t71,dil=5)
    # Dilute input samples enough to use in qPCR directly (should be 5000/(rnagain*2*5)  = 20)
    qpcrdil1=trp.runQPCRDIL(src=t71,tgt=[],vol=100,srcdil=20,dilPlate=True)   
    rt1=trp.runRT(pos=True,src=t71,tgt=[],vol=5,srcdil=2)
    if ligate:
        rt1=trp.diluteInPlace(tgt=rt1,dil=4)
        lig1=trp.runLig(prefix=prodprefixes,src=rt1,tgt=[],vol=10,srcdil=3)
        # Dilute positive ligation products (this will wait for PTC to finish)
        poslig=[s for s in lig1 if s[0:3]!="Neg"]
        # Less further dilution for negative ligation products (use directly in qPCR)
        neglig=[s for s in lig1 if s[0:3]=="Neg"]
        poslig=trp.diluteInPlace(tgt=poslig,dil=10)
        neglig=trp.diluteInPlace(tgt=neglig,dil=3)
        prods=poslig+neglig
    else:
        rt1=trp.diluteInPlace(tgt=rt1,dil=20)
        prods=trp.saveSamps(src=rt1,vol=8,dil=(5000/(2*5*2*20)),plate=trp.e.DILPLATE,dilutant=trp.r.SSD)
        
    trp.runQPCR(src=qpcrdil1[:9],vol=15,srcdil=10.0/4,primers=["A","M"])
    trp.runQPCR(src=qpcrdil1[9:],vol=15,srcdil=10.0/4,primers=["M"])
    trp.runQPCR(src=prods[:9],vol=15,srcdil=10.0/4,primers=["A","B","M"])
    trp.runQPCR(src=prods[9:],vol=15,srcdil=10.0/4,primers=["A","M"])

trp.finish()

