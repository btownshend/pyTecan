from Experiment.sample import Sample
from Experiment.experiment import *
import debughook
import os.path
import sys

scale=1   # Overall scale of reactions
nreplicates=1  
negRT=1   # Number of negative RTs (first ones only are run with RT)  set very high to run negative of all reactions
keepA=True
keepB=False

### Setup samples
e=Experiment()
e.setreagenttemp(4.0)
spos=0;qpos=0

allReagents=[];
R_MT7=Sample("MT7",e.REAGENTPLATE,len(allReagents),2,15); allReagents.append(R_MT7)
R_Theo=Sample("Theo",e.REAGENTPLATE,len(allReagents),25/7.5,8); allReagents.append(R_Theo)
R_L2b12=Sample("L2b12",e.REAGENTPLATE,len(allReagents),5,9); allReagents.append(R_L2b12)
R_L2b12Cntl=Sample("L2b12Cntl",e.REAGENTPLATE,len(allReagents),5,0); allReagents.append(R_L2b12Cntl)
R_MStop=Sample("MStp",e.REAGENTPLATE,len(allReagents),2,25); allReagents.append(R_MStop)
R_MRT=Sample("MRT",e.REAGENTPLATE,len(allReagents),2,10); allReagents.append(R_MRT)
R_MRTNeg=Sample("MRTNeg",e.REAGENTPLATE,len(allReagents),2,7.5); allReagents.append(R_MRTNeg)
R_MLigB=Sample("MLigB",e.REAGENTPLATE,len(allReagents),1.25,29); allReagents.append(R_MLigB)
R_MLigase=Sample("MLigase",e.REAGENTPLATE,len(allReagents),2,35); allReagents.append(R_MLigase)
R_MQA=Sample("MQA",e.REAGENTPLATE,len(allReagents),20.0/12,23); allReagents.append(R_MQA)
R_MQB=Sample("MQB",e.REAGENTPLATE,len(allReagents),20.0/12,23); allReagents.append(R_MQB)
R_PCRA=Sample("MPCRA",e.REAGENTPLATE,len(allReagents),2.0); allReagents.append(R_PCRA)
R_PCRB=Sample("MPCRB",e.REAGENTPLATE,len(allReagents),2.0); allReagents.append(R_PCRB)

totaldilution=1

### T7 

templates=[R_L2b12]
#templates=[R_L2b12,R_L2b12Cntl]
nTemplates=len(templates)
nT7=nTemplates*nreplicates
S_T7MINUS=[Sample("R1.T7PLUS.%d"%i,e.SAMPLEPLATE,i+spos) for i in range(nT7)]; spos=spos+nT7
S_T7PLUS=[Sample("R1.T7MINUS.%d"%i,e.SAMPLEPLATE,i+spos) for i in range(nT7)]; spos=spos+nT7
S_T7=S_T7MINUS+S_T7PLUS
for i in range(nreplicates):
    e.stage('T7M',[R_MT7],templates,S_T7MINUS[i*nTemplates:(i+1)*nTemplates],10*scale)
    e.stage('T7P',[R_MT7,R_Theo],templates,S_T7PLUS[i*nTemplates:(i+1)*nTemplates],10*scale)
nT7*=2
e.runpgm("37-15MIN",15)

## Stop
e.dilute(S_T7,2);totaldilution*=2
e.stage('Stop',[R_MStop],[],S_T7,20*scale)

### RT
e.dilute(S_T7,2);totaldilution*=2
nRT=nT7
S_RTPos=[Sample("R1.RT.%d"%i,e.SAMPLEPLATE,i+spos) for i in range(nRT)]; spos=spos+nRT
e.stage('RTPos',[R_MRT],S_T7,S_RTPos,5*scale)

negRT=min(nRT,negRT)
S_RTNeg=[Sample("R1.RTNeg.%d"%i,e.SAMPLEPLATE,i+spos) for i in range(negRT)]; spos=spos+negRT
e.stage('RTNeg',[R_MRTNeg],S_T7[0:negRT],S_RTNeg,5*scale)
S_RT=S_RTPos+S_RTNeg
nRT=len(S_RT)
e.runpgm("TRP-SS",65)

## Extension
e.dilute(S_RT,5);totaldilution*=5
nExt=nRT
S_EXT=[Sample("R1.EXT.%d"%i,e.SAMPLEPLATE,i+spos) for i in range(nExt)]; spos=spos+nExt
e.stage('LigAnneal',[R_MLigB],S_RT,S_EXT,10*scale)
e.runpgm("TRP-ANNEAL",5)

e.dilute(S_EXT,2)
e.stage('Ligation',[R_MLigase],[],S_EXT,20*scale)
e.runpgm("TRP-EXTEND",40)

## Dilute for PCR
e.dilute(S_EXT,20);totaldilution*=20
S_EXTDIL=[Sample("R1.EXTDIL.%d"%i,e.SAMPLEPLATE,i+spos) for i in range(nExt)]; spos=spos+nExt
e.stage('PrePCR-Dilute',[],S_EXT,S_EXTDIL,200)
        
## PCR
e.dilute(S_EXTDIL,2); totaldilution*=2
if keepA:
    S_PCRA=[Sample("R1.PCRA.%d"%i,e.SAMPLEPLATE,i+spos) for i in range(nExt)]; spos=spos+nExt
    e.stage('PCRA',[R_PCRA],S_EXTDIL,S_PCRA,10);
else:
    S_PCRA=[]
if keepB:
    S_PCRB=[Sample("R1.PCRB.%d"%i,e.SAMPLEPLATE,i+spos) for i in range(nExt)]; spos=spos+nExt
    e.stage('PCRB',[R_PCRB],S_EXTDIL,S_PCRB,10);
else:
    S_PCRB=[]
S_PCR=S_PCRA+S_PCRB
# Wait until after qPCR setup to run PCR

## qPCR
if totaldilution<2000:
    S_QPCRDIL=[Sample("R1.QPCRDIL.%d"%i,e.SAMPLEPLATE,i+spos) for i in range(nExt)]; spos=spos+nExt
    e.dilute(S_EXTDIL,2000/totaldilution); 
    e.stage('qPCR-Dilute',[],S_EXTDIL,S_QPCRDIL,200)
else:
    S_QPCRDIL=S_EXTDIL

e.dilute(S_QPCRDIL,20.0/8)
nQPCR=nExt
S_QPCR_A=[Sample("R1.QPCR.A.%d"%i,e.QPCRPLATE,i+qpos) for i in range(nQPCR)]; qpos=qpos+nQPCR
e.stage('QPCRA',[R_MQA],S_QPCRDIL,S_QPCR_A,10)
S_QPCR_B=[Sample("R1.QPCR.B.%d"%i,e.QPCRPLATE,i+qpos) for i in range(nQPCR)]; qpos=qpos+nQPCR
e.stage('QPCRA',[R_MQB],S_QPCRDIL,S_QPCR_B,10)
S_QPCR=S_QPCR_A+S_QPCR_B
nQPCR=nQPCR*2

# Run PCR program
e.runpgm("PCR",60)

e.w.userprompt("Process complete. Continue to turn off reagent cooler")
e.setreagenttemp(None)

# Save worklist to a file
#e.saveworklist("trp1.gwl")
(scriptname,ext)=os.path.splitext(sys.argv[0])
e.savegem(scriptname+".gem")
e.savesummary(scriptname+".txt")

# Build a script to prefill the reagent wells for testing
pre=Experiment()
#print "e=",e,"e.worklist=",e.w,",e.w.l=",e.w.list
#print "pre=",pre,"pre.worklist=",pre.w,",pre.w.l=",pre.w.list
pre.stage('Prefill',[],[],allReagents,20)  

e.savegem(scriptname+"-prefill.gem")
e.savesummary(scriptname+"-prefill.txt")
