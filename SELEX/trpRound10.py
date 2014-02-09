from Experiment.sample import Sample
from Experiment.experiment import Experiment
import math
from TRPLib.trp import TRP

reagents=None
input="BT401"

for iteration in range(2):
    print "Iteration ",iteration+1
    trp=TRP()
    if iteration==0:
        trp.addTemplates([input],200)   # Add a template with stock concentration 200nM
    else:   
        reagents=Sample.getAllOnPlate(Experiment.REAGENTPLATE)
        for r in reagents:
            if r.volume<0:
                r.initvolume=-r.volume+20
        Sample.clearall()


    # Round 1 (Keep uncleaved B +theo)
    t71=trp.runT7(theo=[False,True],src=[input,input],tgt=[],vol=[15,15],srcdil=4)
    sv1t7=trp.saveSamps(src=t71,tgt=[],vol=[8,8],dil=[4,4])
    rt1=trp.runRT(pos=[True,True],src=t71,tgt=[],vol=[15,20],srcdil=2)
    trp.diluteInPlace(tgt=rt1,dil=2)
    sv1rt=trp.saveSamps(src=rt1,tgt=[],vol=15,dil=2)
    pcr1=trp.runPCR(prefix=["B"],src=rt1[1],tgt=[],vol=50,srcdil=4)
    trp.diluteInPlace(tgt=pcr1,dil=3)
    sv1pcr=trp.saveSamps(src=pcr1,tgt=["R1"],vol=130,dil=1)
    
    # Round 2 (-theo, Ligate with A, keep cleaved A)
    t72=trp.runT7(theo=[False,True],src=sv1pcr+sv1pcr,tgt=[],vol=15,srcdil=4)
    sv2t7=trp.saveSamps(src=t72,tgt=[],vol=[5,5],dil=[4,4])
    rt2=trp.runRT(pos=[True for i in t72+sv1t7]+[False for i in t72+sv1t7],src=t72+sv1t7+t72+sv1t7,tgt=[],vol=[12,8,8,8,8,8,8,8],srcdil=2)
    trp.diluteInPlace(tgt=rt2,dil=2)
    lig2=trp.runLig(prefix="A",src=rt2+sv1rt,tgt=[],vol=[40,12,12,12,12,12,12,12,12,12],srcdil=3)
    qsamps=lig2+sv1t7+sv2t7     # Samples for QPCR
    diltolig=[24,24,24*4,24*4,24,24,24*4,24*4,24*2,24*2]+[8,8]+[8,8]  # Their dilution so far from the T7 product point (before stop added)
    dilneeded=[40000/d for d in diltolig]
    qdil1=[max(50,math.sqrt(d)) for d in dilneeded]   # Split dilution equally, but don't use more than 3ul in first step
    qdil2=[dilneeded[i]/qdil1[i] for i in range(len(qdil1))]   # Whatever remains
    qpcrdil1=trp.runQPCRDIL(src=qsamps,vol=150,srcdil=qdil1)   # First dilution before starting PCR (so the rest of the QPCR setup can be done while PCR is running)
    pcr2=trp.runPCR(prefix="A",src="R1.T-.RT+.LA",tgt=[],vol=100,srcdil=4)
    qpcrdil2=trp.runQPCRDIL(src=qpcrdil1,vol=150,srcdil=qdil2)
    trp.runQPCR(src=qpcrdil2,vol=15,srcdil=10.0/4)
    sv2pcr=trp.saveSamps(src=pcr2,tgt=["R2"],vol=85,dil=1)

trp.finish()

            
