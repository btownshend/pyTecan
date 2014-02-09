from Experiment.sample import Sample
from Experiment.experiment import Experiment
import math
from TRPLib.TRP import TRP

reagents=None
input="BT422"
ctl="BT423"
srcprefix="B"
prodprefix="A"
ctlprefix="A"
ctlprodprefix="B"

for iteration in range(2):
    print "Iteration ",iteration+1
    trp=TRP()
    if iteration==0:
        trp.addTemplates([input,ctl],80)   # Add a template with stock concentration 80nM
    else:   
        reagents=Sample.getAllOnPlate(Experiment.REAGENTPLATE)
        for r in reagents:
            if r.volume<0:
                r.initvolume=-r.volume+20
        Sample.clearall()


    # Round 1 (Keep uncleaved +theo)
    t71=trp.runT7(theo=[False,True,False],src=[input,input,ctl],tgt=[],vol=18,srcdil=80.0/24,dur=30)
    sv1t7=trp.saveSamps(src=t71,tgt=[],vol=10,dil=4)
    rt1=trp.runRT(pos=[True,True,True ],src=t71,tgt=[],vol=22,srcdil=2)
    trp.diluteInPlace(tgt=rt1,dil=2)
    sv1rt=trp.saveSamps(src=rt1,tgt=[],vol=15,dil=2)
    pcr1=trp.runPCR(prefix=[srcprefix],src=rt1[1],tgt=[],vol=50,srcdil=4)
    trp.diluteInPlace(tgt=pcr1,dil=3)
    sv1pcr=trp.saveSamps(src=pcr1,tgt=["R1"],vol=125,dil=1)
    
    # Round 2 (-theo, Ligate, keep cleaved)
    t72=trp.runT7(theo=[False,True],src=sv1pcr+sv1pcr,tgt=[],vol=17,srcdil=80.0/24)
    sv2t7=trp.saveSamps(src=t72,tgt=[],vol=7,dil=4)
    rt2=trp.runRT(pos=[True for i in t72+sv1t7]+[False for i in t72+sv1t7],src=t72+sv1t7+t72+sv1t7,tgt=[],vol=[12]+[9 for s in t72[1:]+sv1t7+t72+sv1t7],srcdil=2)
    trp.diluteInPlace(tgt=rt2,dil=2)
    lig2=trp.runLig(prefix=[prodprefix for s in rt2]+[prodprefix,prodprefix,ctlprodprefix],src=rt2+sv1rt,tgt=[],vol=[30]+[16 for s in rt2[1:]+sv1rt],srcdil=3)
    qsamps=lig2+sv1t7+sv2t7     # Samples for QPCR
    diltolig=[24 for s in t72]+[24*4 for s in sv1t7]+[24 for s in t72]+[24*4 for s in sv1t7]+[16*3 for s in sv1rt]+[8 for s in sv1t7]+[8 for s in sv2t7]   # Their dilution so far from the T7 product point (before stop added)
    dilneeded=[10000/d for d in diltolig]
    qdil1=[40 for d in dilneeded]   # 40x for first dilution
    qdil2=[dilneeded[i]/qdil1[i] for i in range(len(qdil1))]   # Whatever remains
    qpcrdil1=trp.runQPCRDIL(src=qsamps,tgt=[],vol=100,srcdil=qdil1,dilPlate=True)   # First dilution before starting PCR (so the rest of the QPCR setup can be done while PCR is running)
    pcr2=trp.runPCR(prefix=prodprefix,src="R1.T-.RT+.L"+prodprefix,tgt=[],vol=50,srcdil=4)
    trp.e.w.userprompt("Load QPCR plate and press return to start QPCR setup")
    qpcrdil2x1=trp.runQPCRDIL(src=qpcrdil1,tgt=[],vol=100,srcdil=qdil2)
    #    qpcrdil2x2=trp.runQPCRDIL(src=qpcrdil1[0:2],tgt=['x2a','x2b'],vol=100,srcdil=[d*2 for d in qdil2[0:2]])
    qpcrdil2x4=trp.runQPCRDIL(src=qpcrdil1[0:2],tgt=['x4a','x4b'],vol=100,srcdil=[d*4 for d in qdil2[0:2]])
    qpcrdil2x4b=trp.runQPCRDIL(src=qpcrdil2x1[0:2],tgt=['x4ab','x4bb'],vol=100,srcdil=[4 for d in qdil2[0:2]])
    qpcrdil2x16=trp.runQPCRDIL(src=qpcrdil2x1[0:2],tgt=['x16a','x16b'],vol=100,srcdil=[16 for d in qdil2[0:2]])
    qpcrdil2=qpcrdil2x1+qpcrdil2x4+qpcrdil2x4b+qpcrdil2x16
    trp.runQPCR(src=qpcrdil2,vol=15,srcdil=10.0/4)
    trp.diluteInPlace(tgt=pcr2,dil=3)
    sv2pcr=trp.saveSamps(src=pcr2,tgt=["R2"],vol=125,dil=1)

trp.finish()

            
