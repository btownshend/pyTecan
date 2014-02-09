from Experiment.sample import Sample
from Experiment.experiment import Experiment
import math
from TRPLib.trp import TRP

reagents=None

for iteration in range(2):
    print "Iteration ",iteration+1
    trp=TRP()
    if iteration==0:
        trp.addTemplates(["IN"],200)   # Add a template with stock concentration 200nM
    else:   
        reagents=Sample.getAllOnPlate(Experiment.REAGENTPLATE)
        for r in reagents:
            if r.volume<0:
                r.initvolume=-r.volume+20
        Sample.clearall()

            
    # Round 1
    t71=trp.runT7(theo=[False,True],src=["IN","IN"],tgt=[],vol=[10,20],srcdil=10.0/3)
    sv1=trp.saveSamps(src=t71,tgt=[],vol=[10,10],dil=[4,4])
    rt1=trp.runRT(pos=[True],src=["IN.T+"],tgt=[],vol=30,srcdil=2)
    trp.diluteInPlace(tgt=rt1,dil=2)
    sv2=trp.saveSamps(src=rt1,tgt=[],vol=20,dil=2)
    pcr1=trp.runPCR(prefix=["A"],src=rt1,tgt=[],vol=100,srcdil=4)
    sv3=trp.saveSamps(src=pcr1,tgt=["R1"],vol=85,dil=3)
    
    # Round 2
    t72=trp.runT7(theo=[False,True],src=sv3+sv3,tgt=[],vol=[15,10],srcdil=10.0/3)
    rt2=trp.runRT(pos=[True for i in t72+sv1]+[False for i in t72+sv1],src=t72+sv1+t72+sv1,tgt=[],vol=[30,8,8,8,8,8,8,8],srcdil=2)
    trp.diluteInPlace(tgt=rt2,dil=2)
    lig2=trp.runLig(prefix="B",src=rt2+sv2,tgt=[],vol=[69,12,12,12,12,12,12,12,12],srcdil=3.0)
    dilneeded=6000/12
    qpcrdil1=trp.runQPCRDIL(src=lig2,vol=100,srcdil=math.sqrt(dilneeded))
    dilneeded=math.sqrt(dilneeded)
    pcr2=trp.runPCR(prefix="B",src="R1.T-.RT+.LB",tgt=["R2.1","R2.2"],vol=100,srcdil=4)
    qpcrdil2=trp.runQPCRDIL(src=qpcrdil1,vol=100,srcdil=math.sqrt(6000.0/12))
    trp.runQPCR(src=qpcrdil2,vol=10,srcdil=10.0/4)
    sv4=trp.saveSamps(src=pcr2,tgt=["R2","R2.3Xdil"],vol=85,dil=[1,3])

trp.finish()

            
