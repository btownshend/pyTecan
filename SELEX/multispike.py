from Experiment.sample import Sample
from Experiment.experiment import Experiment
import math
from TRPLib.TRP import TRP
import debughook

reagents=None
srcprefix="B"
firstround=25
ndblrounds=4
doqpcr=True

# Computation of PCR cycles
rnagain=10    # Assumed DNA:RNA gain
endconc=50e-9	# PCR target end concentration (nM) (at end of exponential phase)
pcreff=1.9   # Mean efficiency of PCR during exponential phase
tmplConc=endconc/2   # nM
inputConc=tmplConc*3   # Extra boost for first round to maximize diversity

dil1=10.0/3.0*2*2*3*4    # (T7)*(Stop)*(RT)*(RTDil)*(PCR)
pcrinconc1=tmplConc*rnagain/dil1   # Expected concentration of RT product at input to PCR
pcrvol=25
cycles1=math.ceil(math.log(endconc/pcrinconc1,pcreff))   # Amplify to end of exponential phase

dil2=10.0/3.0*2*2*3*3*4    # (T7)*(Stop)*(RT)*(RTDil)*(Lig)*(PCR)
pcrinconc2=tmplConc*rnagain/dil2   # Expected concentration of ligation product at input to PCR
cycles2=math.ceil(math.log(endconc/pcrinconc2,pcreff))   # Amplify to end of exponential phase

# Adjust number of cycles based on empirical observations
cycles1+=6+2
cycles2+=3+2

print "PCR1 input conc=%.3g pM, PCR cycles=%.1f, End Conc=%.0f nM"%(pcrinconc1*1e12,cycles1,pcrinconc1*(math.pow(pcreff,cycles1))*1e9)
print "PCR2 input conc=%.3g pM, PCR cycles=%.1f, End Conc=%.0f nM"%(pcrinconc2*1e12,cycles2,pcrinconc2*(math.pow(pcreff,cycles2))*1e9)
print "Diversity at PCR1 input in first round = %.1g molecules"%(pcrinconc1*(inputConc/tmplConc)*(pcrvol*1e-6)*6.022e23)
print "Diversity at PCR2 input in second round = %.1g molecules"%(pcrinconc2*(pcrvol*1e-6)*6.022e23)

for iteration in range(2):
    print "Iteration ",iteration+1
    trp=TRP()
    templates=["In"+srcprefix,"In"+srcprefix+"-spike"]
    
    if iteration==0:
        #rnastore=Sample("RNA Storage",Experiment.REAGENTPLATE,None,None)
        trp.addTemplates(templates,inputConc*1e9)   # Add a template with stock concentration same as subsequent PCR products
        trp.addTemplates(["BT423"],1)   # Add a template with stock concentration same as subsequent PCR products
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
    ligsave=[]
    pcrsave=[]
    input=templates
    
    for round in range(ndblrounds):
        # Round 1 (Keep uncleaved +theo)
        t71=trp.runT7(theo=True,src=input,vol=10,srcdil=10.0/3,dur=15)

        rt1=trp.runRT(pos=True,src=t71,vol=10,srcdil=2)
        t71=trp.diluteInPlace(tgt=t71,dil=5)  # Dilute more to conserve
        rt1=trp.diluteInPlace(tgt=rt1,dil=3)   # Returned to old dilution of 3

        # Save RT product so can do ligation during 2nd round
        sv1rt=trp.saveSamps(src=rt1,vol=8,dil=3,plate=trp.e.DILPLATE)

        prodbase="R%d-%c"%(firstround+round*2,currprefix)
        pcr1=trp.runPCR(prefix=currprefix,src=rt1,tgt=[prodbase,prodbase+"-spike"],vol=pcrvol,srcdil=4,ncycles=cycles1)
        pcr1=trp.diluteInPlace(tgt=pcr1,dil=2)
        eppie=trp.saveSamps(src=pcr1,tgt=[prodbase+".D3",prodbase+"-spike.D3"],vol=32,dil=3,plate=trp.e.EPPENDORFS)
        # And save in dilution plate for qPCR (will need 400x dilution from this point) (also eppie may be removed before end)
        pcrsave=pcrsave+trp.saveSamps(src=eppie,vol=5,dil=20, plate=trp.e.DILPLATE)

        # Round 2 (-theo, Ligate, keep cleaved)
        t72=trp.runT7(theo=False,src=pcr1,vol=10,srcdil=10.0/3)

        rt2=trp.runRT(pos=True,src=t72,vol=10,srcdil=2)
        t72=trp.diluteInPlace(tgt=t72,dil=5)  # Dilute more to conserve
        rt2=trp.diluteInPlace(tgt=rt2,dil=3)

        # Swap prefixes
        altprefix=currprefix
        if currprefix=="B":
            currprefix="A"
        else:
            currprefix="B"
            
        # Run ligation of the first-half round too
        lig2=trp.runLig(prefix=currprefix,src=sv1rt+rt2,vol=[17,17,25,25],srcdil=3)
        # Save ligation products for qPCR (note that round 1 had 5x more dilution of RT product, so back that out here)
        ligsave1=trp.saveSamps(src=lig2[:2],vol=4,dil=16,plate=trp.e.DILPLATE,dilutant=trp.r.SSD)
        ligsave2=trp.saveSamps(src=lig2[2:],vol=2,dil=16*3,plate=trp.e.DILPLATE,dilutant=trp.r.SSD)
        ligsave=ligsave+ligsave1+ligsave2

        prodbase="R%d-%c"%(firstround+1+round*2,currprefix)
        pcr2=trp.runPCR(prefix=currprefix,tgt=[prodbase,prodbase+"-spike"],src=lig2[2:4],vol=pcrvol,srcdil=4,ncycles=cycles2)
        pcr2=trp.diluteInPlace(tgt=pcr2,dil=2)

        # Save PCR product in eppendorfs for archive
        eppie= trp.saveSamps(src=pcr2,tgt=[prodbase+".D3",prodbase+"-spike.D3"],vol=32,dil=3,plate=trp.e.EPPENDORFS)

        # And save in dilution plate for qPCR (will need 400x dilution from this point)
        pcrsave=pcrsave+trp.saveSamps(src=eppie,vol=5,dil=20, plate=trp.e.DILPLATE)
        
        # But use PCR product from sample plate for next rount to avoid extra dilution
        input=pcr2

    if doqpcr:
        # Setup qPCR
        # Do A,B,M,T of input and PCR products (4*9), A,B of ligation products (2*8), M,T of BT423
        # Saved products should already be at correct concentration for qPCR
        #trp.e.w.setOptimization(True)
        print "Setting up qPCR of %d ligation products with A,B primers"%(len(ligsave))
        trp.runQPCR(src=ligsave,vol=15,srcdil=15.0/6,primers=["A","B"])
        # Need to dilute templates to match PCR products
        tmpldil1=trp.saveSamps(src=templates,vol=4,dil=20.0/3,plate=trp.e.DILPLATE)
        tmpldil2=trp.saveSamps(src=["BT423"]+tmpldil1+pcrsave,vol=4,dil=20,plate=trp.e.DILPLATE) 
        tmpldil3=trp.saveSamps(src=tmpldil2,vol=4,dil=16,dilutant=trp.r.SSD,plate=trp.e.DILPLATE)
        notSpiked=[t for t in tmpldil3 if "spike" not in  t]
        spiked=[t for t in tmpldil3 if "spike" in t]
        print "Setting up qPCR of  %d non-spiked template/PCR products with A,B,M,T primers"%(len(notSpiked))
        trp.runQPCR(src=notSpiked+["Water"],vol=15,srcdil=15.0/6,primers=["A","B","M","T"])
        print "Setting up qPCR of  %d spiked template/PCR products with M,T primers"%(len(tmpldil3[3:]))
        trp.runQPCR(src=spiked,vol=15,srcdil=15.0/6,primers=["M","T"])
        trp.e.w.setOptimization(False)

trp.finish()

            
