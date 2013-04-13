from Experiment.sample import Sample
from Experiment.experiment import *
import debughook


nRep=4
lc="Water-Test1"
firstWell=8*8

### Setup samples
e=Experiment()

allReagents=[]
R_Dye=Sample("DYE",e.REAGENTPLATE,96,100); allReagents.append(R_Dye)

# Fill sample wells with 105ul water
wellno=firstWell
e.w.getDITI(15,200)
for i in range(nRep*2):
    e.w.aspirate(range(4),"Water on liquid level",105,e.WATERLOC)
    e.w.dispense(range(wellno, wellno+4),"Water-Bottom",105,e.SAMPLEPLATE)
    wellno+=4
e.w.dropDITI(15,e.WASTE)

# Transfer dye
volumes=[1, 2, 3, 4, 5, 6, 7, 8]
wellno=firstWell
for i in range(nRep):
    e.w.wash(15)
    e.w.getDITI(1,200)
    for v in volumes:
        if i==nRep-1:
            #
            e.w.aspirate([0],"Water on liquid level",v,e.WATERLOC)
        else:
            e.w.aspirate([15],lc,v,e.EPPENDORFS)
        e.w.dispense([wellno],lc,v,e.SAMPLEPLATE)
        wellno+=1
    e.w.dropDITI(1,e.WASTE)
        
# Mix and transfer to platereader plate
e.w.wash(15)
wellno=firstWell
for i in range(nRep*2):
        e.w.getDITI(15,200)
        for k in range(4):
            # Mix
            e.w.aspirate(range(wellno,wellno+4),"Water-Bottom",90,e.SAMPLEPLATE)
            e.w.dispense(range(wellno,wellno+4),"Water-Top",90,e.SAMPLEPLATE)

        e.w.aspirate(range(wellno,wellno+4),"Water-Bottom",100,e.SAMPLEPLATE)
        e.w.dispense(range(wellno,wellno+4),"Water-Top",100,e.READERPLATE)
        e.w.dropDITI(15,e.WASTE)
        wellno+=4
    
        
# Save worklist to a file
e.savegem("header.gem","dyetest.gem")
e.savesummary("dyetest.txt")
