from Experiment.sample import Sample
from Experiment.experiment import Experiment
import math
from TRPLib.TRP import TRP
from TRPLib.TRP import findsamps
import copy

reagents=None
inputs=[]
concs=[10,5,2.5,1.25]
for iteration in range(2):
    print "Iteration ",iteration+1
    trp=TRP()
    if iteration==0:
        for conc in concs:
            input="DNA@%d"%conc
            inputs.append(input)
            trp.addTemplates([input],conc,finalconc=conc)  
    else:   
        reagents=Sample.getAllOnPlate(Experiment.REAGENTPLATE)
        for r in reagents:
            if r.volume<0:
                r.initvolume=-r.volume+20
        Sample.clearall()

    dilneeded=[c/.020 for c in concs]
    qdil1=[min(40,d/2) for d in dilneeded]   # 40x for first dilution
    qdil2=[dilneeded[i]*1.0/qdil1[i] for i in range(len(qdil1))]   # Whatever remains
    qpcrdil1=trp.runQPCRDIL(src=inputs,tgt=[],vol=100,srcdil=qdil1,dilPlate=False)   # First dilution before starting PCR (so the rest of the QPCR setup can be done while PCR is running)
    qpcrdil2x1=trp.runQPCRDIL(src=qpcrdil1,tgt=[],vol=100,srcdil=qdil2)
    #    qpcrdil2x2=trp.runQPCRDIL(src=qpcrdil1[0:2],tgt=['x2a','x2b'],vol=100,srcdil=[d*2 for d in qdil2[0:2]])
    qpcrdil2x4=trp.runQPCRDIL(src=qpcrdil1[0:2],tgt=['x4a','x4b'],vol=100,srcdil=[d*4 for d in qdil2[0:2]])
    qpcrdil2x4b=trp.runQPCRDIL(src=qpcrdil2x1[0:2],tgt=['x4ab','x4bb'],vol=100,srcdil=[4 for d in qdil2[0:2]])
    qpcrdil2x16=trp.runQPCRDIL(src=qpcrdil2x1[0:2],tgt=['x16a','x16b'],vol=100,srcdil=[16 for d in qdil2[0:2]])
    qpcrdil2=qpcrdil2x1+qpcrdil2x4+qpcrdil2x4b+qpcrdil2x16
    trp.runQPCR(src=qpcrdil2,vol=15,srcdil=10.0/4)

trp.finish()

            
