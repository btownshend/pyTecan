from Experiment.plate import Plate
from Experiment.sample import Sample
from Experiment.worklist import WorkList
from Experiment.experiment import *
import copy


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

nT7=3
S_R1_T7=[Sample("R1.T7.%d"%i,e.SAMPLEPLATE,i+spos) for i in range(nT7)]; spos=spos+nT7

nRT=nT7
S_R1_RTPos=[Sample("R1.RT.%d"%i,e.SAMPLEPLATE,i+spos) for i in range(nRT)]; spos=spos+nRT
S_R1_RTNeg=[Sample("R1.RTNeg.%d"%i,e.SAMPLEPLATE,i+spos) for i in range(nRT)]; spos=spos+nRT
S_R1_RT=copy.copy(S_R1_RTPos)
S_R1_RT.extend(S_R1_RTNeg)

nExt=nRT*2
S_R1_EXT=[Sample("R1.EXT.%d"%i,e.SAMPLEPLATE,i+spos) for i in range(nExt)]; spos=spos+nRT

scale=1   # Overall scale of reactions

Sample.printallsamples("Before T7")
e.stage('T7',[S_T7,S_Theo],[S_L2b12,S_L2b12,S_L2b12Cntl],S_R1_T7,10*scale)
e.runpgm("37-15MIN")

Sample.printallsamples("Before Stop")
e.dilute(S_R1_T7,2)
e.stage('Stop',[S_Stop],[],S_R1_T7,20*scale)

Sample.printallsamples("Before RT")
e.dilute(S_R1_T7,2)
e.stage('RT',[S_MRT],S_R1_T7,S_R1_RTPos,5*scale)
e.stage('RT',[S_MRTNeg],S_R1_T7,S_R1_RTNeg,5*scale)
e.runpgm("TRP-SS")

Sample.printallsamples("Before Ligation")
e.dilute(S_R1_RT,5)
e.stage('LigAnneal',[S_LIGB],S_R1_RT,S_R1_EXT,10*scale)
e.runpgm("TRP-ANNEAL")
e.dilute(S_R1_EXT,2)
e.stage('Ligation',[S_LIGASE],[],S_R1_EXT,20*scale)

Sample.printallsamples("After Ligation")

e.printsetup()

e.w.save("trp1.gwl")
