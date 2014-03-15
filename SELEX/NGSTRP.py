# Run TRP to prepare for an NGS run
# Runs normal TRP followed by qPCR and PCR
# No theo added, always use MStopNoTheo since may have other targets
# Running +target achieved by second sample of input with target already added at 3.33x of final  concentration
# Handles W prefix too
# Uses appropriate extension split master mix
from Experiment.sample import Sample
from Experiment.experiment import Experiment
from Experiment.experiment import Concentration
import math
from TRPLib.TRP import TRP
import debughook

# Configuration for this run (up to 15 total samples in reagent plate)
input=[
    "BT537-T7_A_L2b12_S",
    "BT537-T7_A_L2b12_S+theo",
# "BT646-T7_B_N7N30_S-R57",
# "BT646-T7_B_N7N30_S-R57+theo",
# "BT647-T7_B_N7N30_S-R57c",
# "BT647-T7_B_N7N30_S-R57c+theo",
# "BT272-T7_A_sTRSV_S",
# "BT272-T7_A_sTRSV_S+Ammeline",
# "BT272-T7_A_sTRSV_S+Tetracyline",
# "BT272-T7_A_sTRSV_S+Neomycin",
# "BT272-T7_A_sTRSV_S+Adenine",
# "BT272-T7_A_sTRSV_S+Guanine",
# "BT272-T7_A_sTRSV_S+Theo",
"BT642+643-T7_A_Theo_S",
"BT642+643-T7_A_Theo_S +target",
"BT585-T7_A_TheoAAG_AAAAA_S",
"BT585-T7_A_TheoAAG_AAAAA_S+theo",
"BT596-T7_M_TheoAAG_AAAAA_M",
"BT596-T7_M_TheoAAG_AAAAA_M+theo",
"BT644+645-T7_W_Theo_W +target",
"BT634+636-T7_W_Ammeline_W+target",
"BT635+637-T7_W_Tetracycline_W+target",
"BT638+639-T7_W_Neomycin_W+target",
"BT632+640-T7_W_Adenine_W+target",
"BT633+641-T7_W_Guanine_W+target",
"BT648-T7_W_All_W",
    ]
srcprefix=["A"]*6+["W"]*9
nreplicates=[1]*len(input)
stem1=["N7"]*len(input)
ligate=True

# Setup replicated inputs
srcs=[]
srcprefixes=[]
ligmaster=[]
stop=[]
pcr=[]
for k in range(max(nreplicates)):
    for i in range(len(input)):
        if nreplicates[i]>k:
            srcs=srcs+[input[i]]
            srcprefixes=srcprefixes+[srcprefix[i]]
            if srcprefix[i]=='A':
                ligmaster=ligmaster+["MLigB"+stem1[i]]
                pcr=pcr+[("A","B")];
                stop=stop+['MStpNoTheo']
            elif  srcprefix[i]=='W':
                ligmaster=ligmaster+["MLigA"+stem1[i]]
                pcr=pcr+[("AW","W")];
                stop=stop+['MStpW']
            elif srcprefix[i]=='B':
                ligmaster=ligmaster+["MLigA"+stem1[i]]
                pcr=pcr+[("A","B")];
                stop=stop+['MStpNoTheo']
            else:
                assert(False)

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
    t71=trp.diluteInPlace(tgt=t71,dil=5)
    # Dilute input samples enough to use in qPCR directly (should be 5000/(rnagain*2*5)  = 20)
    qpcrdil1=trp.runQPCRDIL(src=t71,tgt=[],vol=100,srcdil=20,dilPlate=True)   
    rt1=trp.runRT(pos=True,src=t71,tgt=[],vol=5,srcdil=2)
    rt1=trp.diluteInPlace(tgt=rt1,dil=5)
    lig1=trp.runLig(src=rt1,tgt=[],vol=10,srcdil=3,master=ligmaster)
    prods=trp.diluteInPlace(tgt=lig1,dil=10)
        
    for i in range(len(qpcrdil1)):
        trp.runQPCR(src=qpcrdil1[i],vol=15,srcdil=10.0/4,primers=[srcprefixes[i]])
    for i in range(len(prods)):
        trp.runQPCR(src=[prods[i]],vol=15,srcdil=10.0/4,primers=pcr[i])

trp.finish()

