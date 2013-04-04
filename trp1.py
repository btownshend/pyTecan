from Experiment.sample import Sample
from Experiment.experiment import *

scale=1   # Overall scale of reactions

### Setup samples
e=Experiment()
rpos=0; spos=0;qpos=0
S_T7=Sample("MT7",e.REAGENTPLATE,rpos,2); rpos=rpos+1
S_Theo=Sample("Theo",e.REAGENTPLATE,rpos,25/7.5); rpos=rpos+1
S_L2b12=Sample("L2b12",e.REAGENTPLATE,rpos,10); rpos=rpos+1
S_L2b12Cntl=Sample("L2b12Cntl",e.REAGENTPLATE,rpos,10); rpos=rpos+1
S_Stop=Sample("MStp",e.REAGENTPLATE,rpos,2); rpos=rpos+1
S_MRT=Sample("MRT",e.REAGENTPLATE,rpos,2); rpos=rpos+1
S_MRTNeg=Sample("MRTNeg",e.REAGENTPLATE,rpos,2); rpos=rpos+1
S_LIGB=Sample("MLigB",e.REAGENTPLATE,rpos,1.25); rpos=rpos+1
S_LIGASE=Sample("MLigase",e.REAGENTPLATE,rpos,2); rpos=rpos+1
S_MQA=Sample("MQA",e.REAGENTPLATE,rpos,20.0/12); rpos=rpos+1
S_MQB=Sample("MQB",e.REAGENTPLATE,rpos,20.0/12); rpos=rpos+1

### T7 
templates=[S_L2b12,S_L2b12,S_L2b12Cntl]
nT7=len(templates)
S_R1_T7MINUS=[Sample("R1.T7PLUS.%d"%i,e.SAMPLEPLATE,i+spos) for i in range(nT7)]; spos=spos+nT7
S_R1_T7PLUS=[Sample("R1.T7MINUS.%d"%i,e.SAMPLEPLATE,i+spos) for i in range(nT7)]; spos=spos+nT7
S_R1_T7=S_R1_T7MINUS+S_R1_T7PLUS
e.stage('T7M',[S_T7],templates,S_R1_T7MINUS,10*scale)
e.stage('T7P',[S_T7,S_Theo],templates,S_R1_T7PLUS,10*scale)
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

S_R1_RT=S_R1_RTPos+S_R1_RTNeg
nRT*=2
e.runpgm("TRP-SS")

## Extension
e.dilute(S_R1_RT,5)
nExt=nRT
S_R1_EXT=[Sample("R1.EXT.%d"%i,e.SAMPLEPLATE,i+spos) for i in range(nExt)]; spos=spos+nExt
e.stage('LigAnneal',[S_LIGB],S_R1_RT,S_R1_EXT,10*scale)
e.runpgm("TRP-ANNEAL")

e.dilute(S_R1_EXT,2)
e.stage('Ligation',[S_LIGASE],[],S_R1_EXT,20*scale)
e.runpgm("TRP-EXTEND")

## Dilute for qPCR
e.dilute(S_R1_EXT,20)
S_R1_EXTDIL=[Sample("R1.EXTDIL.%d"%i,e.SAMPLEPLATE,i+spos) for i in range(nExt)]; spos=spos+nExt
e.stage('PreQPCR-Dilute',[],S_R1_EXT,S_R1_EXTDIL,200)
        
## qPCR
e.dilute(S_R1_EXTDIL,20.0/8.0)
nQPCR=nExt
S_QPCR_A=[Sample("QPCR.A.%d"%i,e.QPCRPLATE,i+qpos) for i in range(nQPCR)]; qpos=qpos+nQPCR
e.stage('QPCRA',[S_MQA],S_R1_EXTDIL,S_QPCR_A,10)
S_QPCR_B=[Sample("QPCR.B.%d"%i,e.QPCRPLATE,i+qpos) for i in range(nQPCR)]; qpos=qpos+nQPCR
e.stage('QPCRA',[S_MQB],S_R1_EXTDIL,S_QPCR_B,10)
S_QPCR=S_QPCR_A+S_QPCR_B
nQPCR=nQPCR*2

# Save worklist to a file
e.saveworklist("trp1.gwl")
e.savegem("header.gem","trp1.gem")
e.savesummary("trp1.txt")
