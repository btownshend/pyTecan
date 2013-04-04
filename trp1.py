from Experiment.sample import Sample
from Experiment.experiment import *
import copy

scale=1   # Overall scale of reactions

### Setup samples
e=Experiment()
rpos=0; spos=0;
S_T7=Sample("M-T7",e.REAGENTPLATE,rpos,2); rpos=rpos+1
S_Theo=Sample("Theo",e.REAGENTPLATE,rpos,25/7.5); rpos=rpos+1
S_L2b12=Sample("L2b12",e.REAGENTPLATE,rpos,10); rpos=rpos+1
S_L2b12Cntl=Sample("L2b12Cntl",e.REAGENTPLATE,rpos,10); rpos=rpos+1
S_Stop=Sample("M-Stp",e.REAGENTPLATE,rpos,2); rpos=rpos+1
S_MRT=Sample("M-RT",e.REAGENTPLATE,rpos,2); rpos=rpos+1
S_MRTNeg=Sample("M-RTNeg",e.REAGENTPLATE,rpos,2); rpos=rpos+1
S_LIGB=Sample("M-LIGB",e.REAGENTPLATE,rpos,1.25); rpos=rpos+1
S_LIGASE=Sample("M-LIGASE",e.REAGENTPLATE,rpos,2); rpos=rpos+1

### T7 
templates=[S_L2b12,S_L2b12,S_L2b12Cntl]
nT7=len(templates)
S_R1_T7MINUS=[Sample("R1.T7+.%d"%i,e.SAMPLEPLATE,i+spos) for i in range(nT7)]; spos=spos+nT7
S_R1_T7PLUS=[Sample("R1.T7-.%d"%i,e.SAMPLEPLATE,i+spos) for i in range(nT7)]; spos=spos+nT7
S_R1_T7=copy.copy(S_R1_T7MINUS)
S_R1_T7.extend(S_R1_T7PLUS)
e.stage('T7-',[S_T7],templates,S_R1_T7MINUS,10*scale)
e.stage('T7+',[S_T7,S_Theo],templates,S_R1_T7PLUS,10*scale)
nT7*=2
e.runpgm("37-15MIN")

## Stop
e.dilute(S_R1_T7,2)
e.stage('Stop',[S_Stop],[],S_R1_T7,20*scale)

### RT
e.dilute(S_R1_T7,2)
nRT=nT7
S_R1_RTPos=[Sample("R1.RT.%d"%i,e.SAMPLEPLATE,i+spos) for i in range(nRT)]; spos=spos+nRT
e.stage('RTPos',[S_MRT],S_R1_T7,S_R1_RTPos,5*scale)

S_R1_RTNeg=[Sample("R1.RTNeg.%d"%i,e.SAMPLEPLATE,i+spos) for i in range(nRT)]; spos=spos+nRT
e.stage('RTNeg',[S_MRTNeg],S_R1_T7,S_R1_RTNeg,5*scale)

S_R1_RT=copy.copy(S_R1_RTPos)
S_R1_RT.extend(S_R1_RTNeg)
nRT*=2
e.runpgm("TRP-SS")

## Extension
e.dilute(S_R1_RT,5)
nExt=nRT
S_R1_EXT=[Sample("R1.EXT.%d"%i,e.SAMPLEPLATE,i+spos) for i in range(nExt)]; spos=spos+nRT
e.stage('LigAnneal',[S_LIGB],S_R1_RT,S_R1_EXT,10*scale)
e.runpgm("TRP-ANNEAL")

e.dilute(S_R1_EXT,2)
e.stage('Ligation',[S_LIGASE],[],S_R1_EXT,20*scale)
e.runpgm("TRP-EXTEND")

# Save worklist to a file
e.saveworklist("trp1.gwl")
e.savesummary("trp1.txt")
