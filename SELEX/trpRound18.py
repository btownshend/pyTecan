from Experiment.sample import Sample
from Experiment.experiment import Experiment
import math
from TRPLib.trp import TRP

reagents=None
input="BT409"
srcprefix="B"
prodprefix="A"

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


    # Round 1 (Keep uncleaved +theo)
    t71=trp.runT7(theo=[False,True],src=[input,input],tgt=[],vol=[16,18],srcdil=4)
    sv1t7=trp.saveSamps(src=t71,tgt=[],vol=10,dil=[4,4])
    rt1=trp.runRT(pos=[True,True],src=t71,tgt=[],vol=[15,22],srcdil=2)
    trp.diluteInPlace(tgt=rt1,dil=2)
    sv1rt=trp.saveSamps(src=rt1,tgt=[],vol=15,dil=2)
    pcr1=trp.runPCR(prefix=[srcprefix],src=rt1[1],tgt=[],vol=50,srcdil=4)
    trp.diluteInPlace(tgt=pcr1,dil=3)
    sv1pcr=trp.saveSamps(src=pcr1,tgt=["R1"],vol=125,dil=1)
    
    # Round 2 (-theo, Ligate, keep cleaved)
    t72=trp.runT7(theo=[False,True],src=sv1pcr+sv1pcr,tgt=[],vol=17,srcdil=4)
    sv2t7=trp.saveSamps(src=t72,tgt=[],vol=7,dil=[4,4])
    rt2=trp.runRT(pos=[True for i in t72+sv1t7]+[False for i in t72+sv1t7],src=t72+sv1t7+t72+sv1t7,tgt=[],vol=[11,9,9,9,9,9,9,9],srcdil=2)
    trp.diluteInPlace(tgt=rt2,dil=2)
    lig2=trp.runLig(prefix=prodprefix,src=rt2+sv1rt,tgt=[],vol=[30,15,15,15,15,15,15,15,15,15],srcdil=3)
    qsamps=lig2+sv1t7+sv2t7     # Samples for QPCR
    diltolig=[24,24,24*4,24*4,24,24,24*4,24*4,24*2,24*2]+[8,8]+[8,8]  # Their dilution so far from the T7 product point (before stop added)
    dilneeded=[20000/d for d in diltolig]
    qdil1=[max(50,math.sqrt(d)) for d in dilneeded]   # Split dilution equally, but don't use more than 3ul in first step
    qdil2=[dilneeded[i]/qdil1[i] for i in range(len(qdil1))]   # Whatever remains
    qpcrdil1=trp.runQPCRDIL(src=qsamps,tgt=[],vol=150,srcdil=qdil1)   # First dilution before starting PCR (so the rest of the QPCR setup can be done while PCR is running)
    pcr2=trp.runPCR(prefix=prodprefix,src="R1.T-.RT+.L"+prodprefix,tgt=[],vol=50,srcdil=4)
    qpcrdil2x1=trp.runQPCRDIL(src=qpcrdil1,tgt=[],vol=150,srcdil=qdil2)
    qpcrdil2x2=trp.runQPCRDIL(src=qpcrdil1[0:2],tgt=['x2a','x2b'],vol=150,srcdil=[d*2 for d in qdil2[0:2]])
    qpcrdil2x4=trp.runQPCRDIL(src=qpcrdil1[0:2],tgt=['x4a','x4b'],vol=150,srcdil=[d*4 for d in qdil2[0:2]])
    qpcrdil2=qpcrdil2x1+qpcrdil2x2+qpcrdil2x4
    trp.runQPCR(src=qpcrdil2,vol=15,srcdil=10.0/4)
    trp.diluteInPlace(tgt=pcr2,dil=3)
    sv2pcr=trp.saveSamps(src=pcr2,tgt=["R2"],vol=125,dil=1)

trp.finish()

            
