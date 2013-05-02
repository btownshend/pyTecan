from Experiment.sample import Sample
from Experiment.experiment import *
import debughook
import os.path
import sys


## T7 parameters
templates=[]
#templates=[R_L2b12,R_L2b12Cntl]
nTemplates=max(1,len(templates))
nreplicates=1   # Number of replicates of each template
plusTheo=True

## RT parameters
negRT=2   # Number of negative RTs (first ones only are run with RT)  set very high to run negative of all reactions

## PCR Parameters
keepA=False
keepB=False

### Volume of reactions
scale=2   # Overall scale of reactions
volT7=10*scale
volRT=5*scale
volExt=10*scale
volPCR=10*scale
volQPCR=10*scale
volExtra=10  # Amount of extra in each reagent reservoir

### Calculate number of reactions in each stage
nT7=nTemplates*nreplicates
if plusTheo:
    nT7=nT7*2
negRT=min(nT7,negRT)

nRT=nT7+min(nT7,negRT)
nExt=nRT
if keepA:
    nPCRA=nExt
else:
    nPCRA=0
if keepB:
    nPCRB=nExt
else:
    nPCRB=0
nQPCRAB=nExt+1

### Setup samples
e=Experiment()
e.setreagenttemp(4.0)
spos=0;qpos=0

allReagents=[];
R_MT7=Sample("MT7",e.REAGENTPLATE,len(allReagents),1.429,nT7*volT7/1.429+volExtra); allReagents.append(R_MT7)

if plusTheo:
    R_Theo=Sample("Theo",e.REAGENTPLATE,len(allReagents),25/7.5,nT7/2*volT7/(25/7.5)+volExtra); allReagents.append(R_Theo)

#R_L2b12=Sample("L2b12",e.REAGENTPLATE,len(allReagents),10); allReagents.append(R_L2b12)

if not plusTheo:
    R_MStopNT=Sample("MStpNoTheo",e.REAGENTPLATE,len(allReagents),2,nT7*volT7*2/2+volExtra); allReagents.append(R_MStopNT)
else:
    R_MStopNT=Sample("MStpNoTheo",e.REAGENTPLATE,len(allReagents),2,nT7/2*volT7*2/2+volExtra); allReagents.append(R_MStopNT)
    R_MStopWT=Sample("MStpWithTheo",e.REAGENTPLATE,len(allReagents),2,R_MStopNT.volume); allReagents.append(R_MStopWT)

#R_MSS=Sample("MSS",e.REAGENTPLATE,len(allReagents),2); allReagents.append(R_MSS)
R_MOS=Sample("MOS",e.REAGENTPLATE,len(allReagents),2,nT7*volRT/2+volExtra); allReagents.append(R_MOS)
R_MNegRT=Sample("MNegRT",e.REAGENTPLATE,len(allReagents),2,negRT*volRT/2+volExtra); allReagents.append(R_MNegRT)

R_MLigB=Sample("MLigB",e.REAGENTPLATE,len(allReagents),1.25,nExt*volExt/1.25+volExtra); allReagents.append(R_MLigB)
R_MLigase=Sample("MLigase",e.REAGENTPLATE,len(allReagents),2,nExt*volExt*2/2+volExtra); allReagents.append(R_MLigase)

R_MQA=Sample("MQA",e.REAGENTPLATE,len(allReagents),20.0/12,nQPCRAB*volQPCR/(20.0/12)+volExtra); allReagents.append(R_MQA)
R_MQB=Sample("MQB",e.REAGENTPLATE,len(allReagents),20.0/12,nQPCRAB*volQPCR/(20.0/12)+volExtra); allReagents.append(R_MQB)

#R_PCRA=Sample("MPCRA",e.REAGENTPLATE,len(allReagents),2.0); allReagents.append(R_PCRA)
#R_PCRB=Sample("MPCRB",e.REAGENTPLATE,len(allReagents),2.0); allReagents.append(R_PCRB)

totaldilution=1

### T7 

if plusTheo:
    S_T7MINUS=[Sample("R1.T7MINUS.%d"%i,e.SAMPLEPLATE,i+spos) for i in range(nT7/2)]; spos=spos+nT7/2
    S_T7PLUS=[Sample("R1.T7PLUS.%d"%i,e.SAMPLEPLATE,i+spos) for i in range(nT7/2)]; spos=spos+nT7/2
else:
    S_T7MINUS=[Sample("R1.T7MINUS.%d"%i,e.SAMPLEPLATE,i+spos) for i in range(nT7)]; spos=spos+nT7
    S_T7PLUS=[]
    
S_T7=S_T7MINUS+S_T7PLUS
assert(nT7==len(S_T7))

for i in range(nreplicates):
    e.stage('T7M',[R_MT7],templates,S_T7MINUS[i*nTemplates:(i+1)*nTemplates],volT7)
    if plusTheo:
        e.stage('T7P',[R_MT7,R_Theo],templates,S_T7PLUS[i*nTemplates:(i+1)*nTemplates],volT7)
e.runpgm("37-15MIN",15)

## Stop
e.dilute(S_T7,2);totaldilution*=2
e.stage('StopWT',[R_MStopWT],[],S_T7MINUS,2*volT7)
e.stage('StopNT',[R_MStopNT],[],S_T7PLUS,2*volT7)

### RT
e.dilute(S_T7,2);totaldilution*=2

S_RTPos=[Sample("R1.RT.%d"%i,e.SAMPLEPLATE,i+spos) for i in range(nT7)]; spos=spos+nT7
e.stage('RTPos',[R_MOS],S_T7,S_RTPos,volRT)

S_RTNeg=[Sample("R1.RTNeg.%d"%i,e.SAMPLEPLATE,i+spos) for i in range(negRT)]; spos=spos+negRT
e.stage('RTNeg',[R_MNegRT],S_T7[0:negRT],S_RTNeg,volRT)
e.runpgm("TRP-OS",50)

S_RT=S_RTPos+S_RTNeg
assert(nRT==len(S_RT))

## Extension
e.dilute(S_RT,5);totaldilution*=5
S_EXT=[Sample("R1.EXT.%d"%i,e.SAMPLEPLATE,i+spos) for i in range(nExt)]; spos=spos+nExt
e.stage('LigAnneal',[R_MLigB],S_RT,S_EXT,volExt)
e.runpgm("TRP-ANNEAL",5)

e.dilute(S_EXT,2); totaldilution*=2
e.stage('Ligation',[R_MLigase],[],S_EXT,2*volExt)
e.runpgm("TRP-EXTEND",40)

## Dilute for PCR
e.dilute(S_EXT,20);totaldilution*=200/(20*scale)
e.stage('PrePCR-Dilute',[],[],S_EXT,200)
        
## PCR
e.dilute(S_EXT,2); totaldilution*=2
if keepA:
    S_PCRA=[Sample("R1.PCRA.%d"%i,e.SAMPLEPLATE,i+spos) for i in range(nExt)]; spos=spos+nExt
    e.stage('PCRA',[R_PCRA],S_EXT,S_PCRA,volPCR);
else:
    S_PCRA=[]
if keepB:
    S_PCRB=[Sample("R1.PCRB.%d"%i,e.SAMPLEPLATE,i+spos) for i in range(nExt)]; spos=spos+nExt
    e.stage('PCRB',[R_PCRB],S_EXT,S_PCRB,volPCR);
else:
    S_PCRB=[]
S_PCR=S_PCRA+S_PCRB
# Wait until after qPCR setup to run PCR
e.dilute(S_EXT,0.5); totaldilution*=0.5   # Back out dilution used for qPCR setup

## qPCR
if totaldilution<2000:
    S_QPCRDIL=[Sample("R1.QPCRDIL.%d"%i,e.SAMPLEPLATE,i+spos) for i in range(nExt)]; spos=spos+nExt
    e.dilute(S_EXT,2000/totaldilution); 
    e.stage('qPCR-Dilute',[],S_EXT,S_QPCRDIL,200)
else:
    S_QPCRDIL=S_EXT

e.dilute(S_QPCRDIL,20.0/8);

S_QPCR_A=[Sample("R1.QPCR.A.%d"%i,e.QPCRPLATE,i+qpos) for i in range(nQPCRAB)]; qpos=qpos+nQPCRAB
e.stage('QPCRA',[R_MQA],S_QPCRDIL,S_QPCR_A,volQPCR)
S_QPCR_B=[Sample("R1.QPCR.B.%d"%i,e.QPCRPLATE,i+qpos) for i in range(nQPCRAB)]; qpos=qpos+nQPCRAB
e.stage('QPCRA',[R_MQB],S_QPCRDIL,S_QPCR_B,volQPCR)
S_QPCR=S_QPCR_A+S_QPCR_B

# Run PCR program
if len(S_PCR)>0:
    e.runpgm("PCR",60)

e.w.userprompt("Process complete. Continue to turn off reagent cooler")
e.setreagenttemp(None)

# Save worklist to a file
#e.saveworklist("trp1.gwl")
(scriptname,ext)=os.path.splitext(sys.argv[0])
e.savegem(scriptname+".gem")
e.savesummary(scriptname+".txt")
