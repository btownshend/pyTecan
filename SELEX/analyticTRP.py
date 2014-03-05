# Run analytic TRP of a set of samples
from Experiment.sample import Sample
from Experiment.experiment import Experiment
from Experiment.experiment import Concentration
import math
from TRPLib.TRP import TRP
import debughook

# Configuration for this run (up to 15 total samples in reagent plate)
ref=[] # ["BT537"]
graded=["BT576","BT577","BT578","BT579","BT580","BT581","BT582","BT583"]
switchesA=[] #["BT587","BT588","BT589"]
switchesB=[] # ["BT590","BT591","BT592","BT593","BT594"]
input=ref+graded+switchesA+switchesB
srcprefix=["A"]*len(ref+graded+switchesA)+["B"]*len(switchesB)
nreplicates=[1]*len(input)
plustheo=[0]*len(ref)+[1]*len(graded)+[1]*len(switchesA+switchesB)

stockConc=20
ligate=True

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
    # Use Theo as EDTA instead
    trp.r.Theo.name="EDTA";
    trp.r.Theo.conc=Concentration(25/7.5,1,'mM')
    if iteration==0:
        trp.addTemplates(input,stockConc,stockConc*24/80,plate=Experiment.EPPENDORFS)   # Add a template
    else:   
        reagents=Sample.getAllOnPlate(Experiment.REAGENTPLATE)+Sample.getAllOnPlate(Experiment.EPPENDORFS)
        for r in reagents:
            if r.volume<=0:
                r.initvolume=-r.volume+r.plate.unusableVolume
        Sample.clearall()

    t71=trp.runT7(theo=theo,src=srcs,tgt=[],vol=10,srcdil=80.0/24,dur=15)
    t71=trp.diluteInPlace(tgt=t71,dil=5)
    # Dilute input samples enough to use in qPCR directly (should be 5000/(rnagain*2*5)  = 20)
    qpcrdil1=trp.runQPCRDIL(src=t71,tgt=[],vol=100,srcdil=20,dilPlate=True)   
    rt1=trp.runRT(pos=True,src=t71,tgt=[],vol=5,srcdil=2)
    if ligate:
        rt1=trp.diluteInPlace(tgt=rt1,dil=5)
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
        
    trp.runQPCR(src=[qpcrdil1[i] for i in range(len(qpcrdil1)) if srcprefixes[i]=='A'],vol=15,srcdil=10.0/4,primers=["A"])
    trp.runQPCR(src=[qpcrdil1[i] for i in range(len(qpcrdil1)) if srcprefixes[i]=='B'],vol=15,srcdil=10.0/4,primers=["B"])
    trp.runQPCR(src=prods,vol=15,srcdil=10.0/4,primers=["A","B","M"])

trp.finish()

