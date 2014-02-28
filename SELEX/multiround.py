from Experiment.sample import Sample
from Experiment.experiment import Experiment
import math
from TRPLib.TRP import TRP
import debughook

reagents=None
srcprefix="A"
firstround=1
ndblrounds=4
doqpcr=False

# Computation of PCR cycles
rnagain=10    # Assumed DNA:RNA gain
endconc=10e-9	# PCR target end concentration (nM) (at end of exponential phase)
pcreff=1.9   # Mean efficiency of PCR during exponential phase
tmplConc=endconc/6   # nM

dil1=10.0/3.0*2*2*3*3*4    # (T7)*(Stop)*(RT)*(RTDil)*(PCR)
pcrinconc1=tmplConc*rnagain/dil1   # Expected concentration of RT product at input to PCR
cycles1=math.ceil(math.log(endconc/pcrinconc1,pcreff))   # Amplify to end of exponential phase

dil2=10.0/3.0*2*2*3*3*4    # (T7)*(Stop)*(RT)*(RTDil)*(Lig)*(PCR)
pcrinconc2=tmplConc*rnagain/dil2   # Expected concentration of ligation product at input to PCR
cycles2=math.ceil(math.log(endconc/pcrinconc2,pcreff))   # Amplify to end of exponential phase

# Adjust number of cycles based on empirical observations
cycles1+=7
cycles2+=2

print "PCR1 input conc=%.3g pM, PCR cycles=%.1f, End Conc=%.0f nM"%(pcrinconc1*1e12,cycles1,pcrinconc1*(math.pow(pcreff,cycles1))*1e9)
print "PCR2 input conc=%.3g pM, PCR cycles=%.1f, End Conc=%.0f nM"%(pcrinconc2*1e12,cycles2,pcrinconc2*(math.pow(pcreff,cycles2))*1e9)

for iteration in range(2):
    print "Iteration ",iteration+1
    trp=TRP()
    input="IN-"+srcprefix
    if iteration==0:
        #rnastore=Sample("RNA Storage",Experiment.REAGENTPLATE,None,None)
        trp.addTemplates([input],tmplConc*1e9)   # Add a template with stock concentration same as subsequent PCR products
    else:   
        reagents=Sample.getAllOnPlate(Experiment.REAGENTPLATE)
        for r in reagents:
            if r.volume<0:
                r.initvolume=-r.volume+20
        Sample.clearall()

    currprefix=srcprefix
    if currprefix=='A':
        altprefix='B'
    else:
        altprefix='A'
    sv=[]
    svligtype=[]
    svdil=[]
    t7all=[]
    
    for round in range(ndblrounds):
        # Round 1 (Keep uncleaved +theo)
        t71=trp.runT7(theo=[True],src=input,vol=12,srcdil=10.0/3,dur=15)
        t7all=t7all+t71
        rt1=trp.runRT(pos=[True],src=t71,vol=[10],srcdil=2)
        trp.diluteInPlace(tgt=t71,dil=5)  # Dilute more to conserve
        trp.diluteInPlace(tgt=rt1,dil=9)   # Dilute same as combined RT+Ligation steps in second half of double-round, reduce inhibition of PCR
        if doqpcr:
            sv=sv+trp.saveSamps(src=rt1,vol=8,dil=5)
            svligtype=svligtype+[altprefix]
            svdil=svdil+[2*2*3*5]
        pcr1=trp.runPCR(prefix=[currprefix],src=rt1,vol=25,srcdil=4,ncycles=cycles1)
        trp.diluteInPlace(tgt=pcr1,dil=6)
        sv1pcr=trp.saveSamps(src=pcr1,tgt=["R%d-%c"%(firstround+round*2,currprefix)],vol=125,dil=1,plate=trp.e.EPPENDORFS)
    
        # Round 2 (-theo, Ligate, keep cleaved)
        t72=trp.runT7(theo=[False],src=sv1pcr,vol=12,srcdil=10.0/3)
        t7all=t7all+t72
        rt2=trp.runRT(pos=True,src=t72,vol=[10],srcdil=2)
        trp.diluteInPlace(tgt=t72,dil=5)  # Dilute more to conserve
        trp.diluteInPlace(tgt=rt2,dil=3)
        if doqpcr:
            sv=sv+trp.saveSamps(src=rt2,vol=8,dil=5)
            svligtype=svligtype+[altprefix]
            svdil=svdil+[2*2*3*5]
        altprefix=currprefix
        if currprefix=="B":
            currprefix="A"
        else:
            currprefix="B"
        if round==ndblrounds-1 and doqpcr:
            # Do the analysis as well
            lig2=trp.runLig(prefix=[currprefix]+svligtype,src=rt2+sv,vol=[19]+[10 for s in sv],srcdil=3)
            qsamps=lig2[1:]    # Samples for QPCR
            lig2=lig2[0:1]
            trp.diluteInPlace(tgt=qsamps,dil=5)
            qpcrdilt7=trp.runQPCRDIL(src=t7all,tgt=[],vol=100,srcdil=33.33,dilPlate=True)   # Dilute T7 products first
            qsamps=qsamps+qpcrdilt7
            dilneeded=[10000.0/(d*3*5) for d in svdil]+[10000.0/(2*5*33.33) for d in qpcrdilt7]
            qpcrdil1=trp.runQPCRDIL(src=qsamps,tgt=[],vol=100,srcdil=dilneeded,dilPlate=True)   # First dilution before starting PCR (so the rest of the QPCR setup can be done while PCR is running)
        else:
            lig2=trp.runLig(prefix=currprefix,src=rt2,vol=[24],srcdil=3)
        pcr2=trp.runPCR(prefix=currprefix,src=lig2,vol=25,srcdil=4,ncycles=cycles2)
        if round==ndblrounds-1 and doqpcr:
            trp.e.w.userprompt("Press return to start QPCR setup")
            trp.runQPCR(src=qpcrdil1,vol=15,srcdil=10.0/4)
        trp.diluteInPlace(tgt=pcr2,dil=6)
        input=trp.saveSamps(src=pcr2,tgt=["R%d-%c"%(firstround+1+round*2,currprefix)],vol=125,dil=1,plate=trp.e.EPPENDORFS)


trp.finish()

            
