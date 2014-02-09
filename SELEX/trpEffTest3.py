from Experiment.sample import Sample
from Experiment.experiment import Experiment
import math
from TRPLib.TRP import TRP
import debughook

reagents=None
inputs=["L2b12-100","L2b12-10","L2b12-1","Neg"]
#inputs=["IN","Neg"]
rnagain=10    # Assumed DNA:RNA gain
endconc=10e-9	# PCR end concentration (nM) (at end of exponential phase)
pcreff=1.9   # Mean efficiency of PCR during exponential phase
tmplConc=endconc/3   # nM

ligdil=2*2*4*3*5
ligconc=tmplConc*3.0/10.0*rnagain/ligdil   # Expected concentration of ligation product here
pcrinconc=ligconc/4;
cycles=math.ceil(math.log(endconc/pcrinconc,pcreff))   # Amplify to end of exponential phase
print "PCR input conc=%.3g pM, PCR cycles=%.1f, End Conc=%.0f nM"%(pcrinconc*1e12,cycles,pcrinconc*(math.pow(pcreff,cycles))*1e9)

# Additional QPCR dilution
qdillig=10000/(ligdil*5)
t7dil=rnagain*2*25   # Back out expected RNA gain
qdilt7=10000/t7dil
print "QPCR 2nd dilution: Ligation products: %.1f, T7 products: %.1f"%(qdillig, qdilt7)

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


    # Round 1 (Keep cleaved -theo)
    print "***** Round 1 T7 *****"
    t71=trp.runT7New(theo=[False for i in inputs]+[True for i in inputs],src=inputs+inputs,tgt=[],vol=10,srcdil=10.0/3)
    sv1t7=trp.saveSamps(src=t71,vol=3,dil=25,plate=trp.e.DILPLATE)
    
    rt1=trp.runRT(pos=True,src=t71,tgt=[],vol=5,srcdil=2)
    trp.diluteInPlace(tgt=rt1,dil=4)

    lig1=trp.runLig(prefix="B",src=rt1,tgt=[],vol=10,srcdil=3)
    trp.diluteInPlace(tgt=lig1,dil=5)

    # Save in dilution plate
    sv1lig=trp.saveSamps(src=lig1,vol=20,dil=5,plate=trp.e.DILPLATE)

    # Only need to PCR -theo case, cleaved
    pcr1=trp.runPCR(prefix="B",src=lig1[0:len(inputs)],tgt=["%s.c"%i for i in inputs],vol=25,srcdil=4,ncycles=cycles)
    trp.diluteInPlace(tgt=pcr1,dil=3)
    sv1pcr=trp.saveSamps(src=pcr1,tgt=[], vol=50,dil=1)
    
    # Round 2 (Keep uncleaved +theo)
    print "***** Round 2 T7 *****"
    in2=pcr1+["Neg"]
    t72=trp.runT7New(theo=[True for i in in2]+[False for i in in2],src=in2+in2,tgt=["%s.T2+"%i for i in in2]+["%s.T2-"%i for i in in2],vol=10,srcdil=10.0/3)
    sv2t7=trp.saveSamps(src=t72,vol=3,dil=25,plate=trp.e.DILPLATE)

    rt2=trp.runRT(pos=True,src=t72,tgt=[],vol=5,srcdil=2)
    trp.diluteInPlace(tgt=rt2,dil=4)

    lig2=trp.runLig(prefix="A",src=rt2,tgt=[],vol=10,srcdil=3)
    trp.diluteInPlace(tgt=lig2,dil=5)
    sv2lig=trp.saveSamps(src=lig2,vol=20,dil=5,plate=trp.e.DILPLATE)

    # Only do PCR +theo case, uncleaved
    pcr2=trp.runPCR(prefix="B",src=lig2[0:len(in2)],tgt=["%s.u"%i for i in in2],vol=25,srcdil=4,ncycles=cycles)
    trp.diluteInPlace(tgt=pcr2,dil=3)
    sv2pcr=trp.saveSamps(src=pcr2,tgt=[],vol=50,dil=1)

    # QPCR
    qsamps=sv1lig+sv2lig+sv1t7+sv2t7     # Samples for QPCR
    dilneeded=[qdillig for d in sv1lig]+[qdillig for d in sv2lig]+[qdilt7 for d in sv1t7]+[qdilt7 for d in sv2t7]
    qpcrdil2=trp.runQPCRDIL(src=qsamps,tgt=[],vol=100,srcdil=dilneeded,dilPlate=True)
    trp.e.w.userprompt("Load QPCR plate and press return to start QPCR setup")
    trp.runQPCR(src=qpcrdil2,vol=15,srcdil=10.0/4)

trp.finish()

            
