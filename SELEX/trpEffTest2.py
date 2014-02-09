from Experiment.sample import Sample
from Experiment.experiment import Experiment
import math
from TRPLib.TRP import TRP
import debughook

reagents=None
inputs=["L2b12-100","L2b12-10","L2b12-1"]
#inputs=["IN"]
srcprefix="A"
prodprefix="B"
rnagain=10;    # Assumed DNA:RNA gain
endconc=10e-9;	# PCR end concentration (nM) (at end of exponential phase)
pcreff=1.9;   # Mean efficiency of PCR during exponential phase
tmplConc=endconc/3;   # nM

for iteration in range(2):
    print "Iteration ",iteration+1
    trp=TRP()
    if iteration==0:
        trp.addTemplates(inputs,tmplConc*1e9)   # Add a template with stock concentration 
    else:   
        reagents=Sample.getAllOnPlate(Experiment.REAGENTPLATE)
        for r in reagents:
            if r.volume<0:
                r.initvolume=-r.volume+20
        Sample.clearall()


    # Round 1 (Keep uncleaved +theo)
    t71=trp.runT7New(theo=True,src=inputs,tgt=["%s.T1+"%i for i in inputs],vol=10,srcdil=10.0/3,dur=30)
    trp.diluteInPlace(tgt=t71,dil=5)
    rt1=trp.runRT(pos=True,src=t71,tgt=[],vol=5,srcdil=2)
    trp.diluteInPlace(tgt=rt1,dil=4)

    rtconc=tmplConc*3.0/10.0*rnagain/(2*5*2*4*4)   # Expected concentration of ligation product here
    cycles=math.ceil(math.log(endconc/rtconc,pcreff));   # Amplify to end of exponential phase
    print "PCR input conc=%.3g pM, PCR cycles=%.1f, End Conc=%.0f nM"%(rtconc*1e12,cycles,endconc*1e9)

    pcr1=trp.runPCR(prefix=srcprefix,src=rt1,tgt=[],vol=25,srcdil=4,ncycles=cycles)
    trp.diluteInPlace(tgt=pcr1,dil=3)
    sv1pcr=trp.saveSamps(src=pcr1,tgt=["%s.R1"%i for i in inputs], vol=55,dil=1)
    
    # Round 2 (both rounds, +/-theo, Ligate, keep cleaved)
    r2in=sv1pcr+inputs
    t72=trp.runT7New(theo=[False for i in r2in]+[True for i in r2in],src=r2in+r2in,tgt=[],vol=10,srcdil=10.0/3)
    trp.diluteInPlace(tgt=t72,dil=5)
    sv2t7=trp.saveSamps(src=t72,vol=10,dil=10,plate=trp.e.DILPLATE)
    rt2=trp.runRT(pos=True,src=t72,tgt=[],vol=5,srcdil=2)
    trp.diluteInPlace(tgt=rt2,dil=4)
    lig2=trp.runLig(prefix=prodprefix,src=rt2,tgt=[],vol=10,srcdil=3)
    trp.diluteInPlace(tgt=lig2,dil=5)
    qsamps=lig2+sv2t7     # Samples for QPCR
    diltolig=[2*5*2*4*3*5 for d in lig2] + [2*5*10*rnagain for d in sv2t7]   # Their dilution so far from the T7 product point (before stop added)
    dilneeded=[10000.0/d for d in diltolig]
    #    qdil1=[40 for d in dilneeded]   # 40x for first dilution
    #    qdil2=[dilneeded[i]/qdil1[i] for i in range(len(qdil1))]   # Whatever remains
    # qpcrdil1=trp.runQPCRDIL(src=qsamps,tgt=[],vol=100,srcdil=qdil1,dilPlate=False)   # First dilution before starting PCR (so the rest of the QPCR setup can be done while PCR is running)
    ligconc=(endconc/3.0)*3.0/10.0*rnagain/diltolig[0]   # Expected concentration of ligation product here
    cycles=math.ceil(math.log(endconc/ligconc,pcreff));   # Amplify to end of exponential phase
    print "PCR input conc=%.3g pM, PCR cycles=%.1f, End Conc=%.0f nM"%(ligconc*1e12,cycles,endconc*1e9)
    pcr2=trp.runPCR(prefix=prodprefix,src=lig2[0:len(sv1pcr)],tgt=[],vol=25,srcdil=4,ncycles=cycles)
    qpcrdil2=trp.runQPCRDIL(src=qsamps,tgt=[],vol=100,srcdil=dilneeded,dilPlate=True)
    trp.e.w.userprompt("Load QPCR plate and press return to start QPCR setup")
    trp.runQPCR(src=qpcrdil2,vol=15,srcdil=10.0/4)
    trp.diluteInPlace(tgt=pcr2,dil=3)
    sv2pcr=trp.saveSamps(src=pcr2,tgt=[],vol=55,dil=1)

trp.finish()

            
