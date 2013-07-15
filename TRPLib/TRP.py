from Experiment.sample import Sample
from Experiment.experiment import Experiment
from Experiment.experiment import Concentration
import os
import sys

maxVolumePerWell=150

class Reagents:
    MT7=Sample("MT7",Experiment.REAGENTPLATE,None,2.5)
    MPosRT=Sample("MPosRT",Experiment.REAGENTPLATE,None,2)
    MNegRT=Sample("MNegRT",Experiment.REAGENTPLATE,None,2)
    MLigA=Sample("MLigAN7",Experiment.REAGENTPLATE,None,3)
    MLigB=Sample("MLigBN7",Experiment.REAGENTPLATE,None,3)
    MLigase=Sample("MLigase",Experiment.REAGENTPLATE,None,3)

    Theo=Sample("Theo",Experiment.REAGENTPLATE,None,Concentration(25,7.5,'mM'))
    #EDTA=Sample("EDTA",Experiment.REAGENTPLATE,None,Concentration(50.0,4,'mM'))
    #BT43=Sample("BT43",Experiment.REAGENTPLATE,None,Concentration(10,0.5,'uM'))
    #EVA=Sample("EvaGreen",Experiment.REAGENTPLATE,None,2)
    #BT47=Sample("BT047",Experiment.REAGENTPLATE,None,Concentration(10,0.4,'uM'))
    #BT29=Sample("BT029",Experiment.REAGENTPLATE,None,Concentration(10,0.4,'uM'))
    #BT30=Sample("BT030",Experiment.REAGENTPLATE,None,Concentration(10,0.4,'uM'))
    MStopNT=Sample("MStpNoTheo",Experiment.REAGENTPLATE,None,2)
    MStopWT=Sample("MStpWithTheo",Experiment.REAGENTPLATE,None,2)
    MQA=Sample("MQA",Experiment.REAGENTPLATE,None,10.0/6)
    MQB=Sample("MQB",Experiment.REAGENTPLATE,None,10.0/6)
    PCRA=Sample("MPCRA",Experiment.REAGENTPLATE,None,4.0/3)
    PCRB=Sample("MPCRB",Experiment.REAGENTPLATE,None,4.0/3)
    all=[MT7,MPosRT,MNegRT,MLigA,MLigB,MLigase,Theo,MStopNT,MStopWT,MQA,MQB,PCRA,PCRB]

def listify(x):
    'Convert a list of (lists or scalars) into a list of equal length lists'
    n=1
    for i in x:
        if isinstance(i,list):
            n=max(n,len(i))
    result=[]
    for i in x:
        if isinstance(i,list):
            result.append(i)
        else:
            result.append([i for j in range(n)])
    return result

def findsamps(x,createIfMissing=True,plate=Experiment.SAMPLEPLATE):
    'Find or create samples for given sample names'
    s=[]
    for i in x:
        t=Sample.lookup(i)
        if t==None:
            if createIfMissing:
                t=Sample(i,plate)
            else:
                print "Unable to locate sample '%s'"%i
                assert(False)
        s.append(t)
    return s

def adjustSrcDil(src,srcdil):
    'Adjust source concentration to give desired dilution'
    for i in range(len(src)):
        src[i].conc.final=src[i].conc.stock/srcdil[i]

class TRP(object):
           
    def __init__(self):
        'Create a new TRP run'
        self.e=Experiment()
        self.r=Reagents();
        
    def addTemplates(self,names,stockconc):
        for s in names:
            Sample(s,Experiment.REAGENTPLATE,None,Concentration(stockconc,None,"nM"))

    def finish(self):
        self.e.lihahome()
        self.e.w.userprompt("Process complete. Continue to turn off reagent cooler")
        self.e.setreagenttemp(None)

        Sample.printallsamples("At completion")
        short=False
        for s in Sample.getAllOnPlate():
            if s.volume<1.0 and s.conc!=None:
                print "ERROR: Insufficient volume for ", s," need at least ",1.0-s.volume," ul additional"
                short=True
            elif s.volume<2.5 and s.conc!=None:
                print "WARNING: Low final volume for ", s
                
        if short:
            print "NO OUTPUT DUE TO ERRORS"
            assert(False)
            
        # Save worklist to a file
        #e.saveworklist("trp1.gwl")
        (scriptname,ext)=os.path.splitext(sys.argv[0])
        self.e.savegem(scriptname+".gem")
        self.e.savesummary(scriptname+".txt")
            
    def saveSamps(self,src,tgt,vol,dil):
        [src,vol,dil]=listify([src,vol,dil])
        if len(tgt)==0:
            tgt=["%s.SAVE"%s for s in src]
        stgt=findsamps(tgt,True,self.e.REAGENTPLATE)
        ssrc=findsamps(src,False)
        self.e.dilute(ssrc,dil)
        self.e.stage('SAVE',[],ssrc,stgt,[vol[i]*dil[i] for i in range(len(vol))])
        # Back out the dilution
        self.e.dilute(ssrc,[1.0/d for d in dil])
        return tgt
            
    def runT7(self,theo,src,tgt,vol,srcdil):
        [theo,src,tgt,vol,srcdil]=listify([theo,src,tgt,vol,srcdil])
        if len(tgt)==0:
            for i in range(len(src)):
                if theo[i]:
                    tgt.append("%s.T+"%src[i])
                else:
                    tgt.append("%s.T-"%src[i])

        # Convert sample names to actual samples
        stgt=findsamps(tgt)
        ssrc=findsamps(src,False)
        adjustSrcDil(ssrc,srcdil)

        self.e.stage('T7M',[self.r.MT7],[ssrc[i] for i in range(len(ssrc)) if not theo[i]],[stgt[i] for i in range(len(ssrc)) if not theo[i]],[vol[i] for i in range(len(ssrc)) if not theo[i]])
        self.e.stage('T7P',[self.r.MT7,self.r.Theo],[ssrc[i] for i in range(len(ssrc)) if theo[i]],[stgt[i] for i in range(len(ssrc)) if theo[i]],[vol[i] for i in range(len(ssrc)) if theo[i]])
        self.e.runpgm("TRP37-15",15, False,max(vol))

        ## Stop
        self.e.dilute(stgt,2)

        if any(theo):
            self.e.stage('StopWT',[self.r.MStopWT],[],[stgt[i] for i in range(len(ssrc)) if not theo[i]],[2*vol[i] for i in range(len(ssrc)) if not theo[i]])
            self.e.stage('StopNT',[self.r.MStopNT],[],[stgt[i] for i in range(len(ssrc)) if theo[i]],[2*vol[i] for i in range(len(ssrc)) if theo[i]])
        else:
            self.e.stage('StopNT',[self.r.MStopWT],[],stgt,[2*v for v in vol])
        return tgt
    
    def runRT(self,pos,src,tgt,vol,srcdil):
        [pos,src,tgt,vol,srcdil]=listify([pos,src,tgt,vol,srcdil])
        if len(tgt)==0:
            for i in range(len(src)):
                if pos[i]:
                    tgt.append("%s.RT+"%src[i])
                else:
                    tgt.append("%s.RT-"%src[i])

        stgt=findsamps(tgt)
        ssrc=findsamps(src,False)
        adjustSrcDil(ssrc,srcdil)

        #    e.stage('MPosRT',[self.r.MOSBuffer,self.r.MOS],[],[self.r.MPosRT],ASPIRATEFACTOR*(self.vol.RT*nRT/2)/2+self.vol.Extra+MULTIEXCESS,2)
        #    e.stage('MNegRT',[self.r.MOSBuffer],[],[self.r.MNegRT],ASPIRATEFACTOR*(self.vol.RT*negRT)/2+self.vol.Extra+MULTIEXCESS,2)
        self.e.stage('RTPos',[self.r.MPosRT],[ssrc[i] for i in range(len(ssrc)) if pos[i]],[stgt[i] for i in range(len(stgt)) if pos[i]],[vol[i] for i in range(len(vol)) if pos[i]])
        self.e.stage('RTNeg',[self.r.MNegRT],[ssrc[i] for i in range(len(ssrc)) if not pos[i]],[stgt[i] for i in range(len(stgt)) if not pos[i]],[vol[i] for i in range(len(vol)) if not pos[i]])
        self.e.runpgm("TRP37-20",20,False,max(vol))
        return tgt
 
    def runLig(self,prefix,src,tgt,vol,srcdil):
        #Extension
        # e.g: trp.runLig(prefix=["B","B","B","B","B","B","B","B"],src=["1.RT-","1.RT+","1.RTNeg-","1.RTNeg+","2.RT-","2.RT-","2.RTNeg+","2.RTNeg+"],tgt=["1.RT-B","1.RT+B","1.RTNeg-B","1.RTNeg+B","2.RT-A","2.RT-B","2.RTNeg+B","2.RTNeg+B"],vol=[10,10,10,10,10,10,10,10],srcdil=[2,2,2,2,2,2,2,2])
        [prefix,src,tgt,vol,srcdil]=listify([prefix,src,tgt,vol,srcdil])
        if prefix[0]=='A':
            # Need to check since an unused ligation master mix will not have a concentration
            minsrcdil=1/(1-1/self.r.MLigA.conc.dilutionneeded()-1/self.r.MLigase.conc.dilutionneeded())
        else:
            minsrcdil=1/(1-1/self.r.MLigB.conc.dilutionneeded()-1/self.r.MLigase.conc.dilutionneeded())
            
        for i in srcdil:
            if i<minsrcdil:
                print "runLig: srcdil=%.2f, but must be at least %.2f"%(i,minsrcdil)
                assert(False)
        if len(tgt)==0:
            tgt=["%s.L%c"%(src[i],prefix[i]) for i in range(len(src))]

        stgt=findsamps(tgt)
        ssrc=findsamps(src,False)
        adjustSrcDil(ssrc,srcdil)
        
        self.e.stage('LigAnnealA',[self.r.MLigA],[ssrc[i] for i in range(len(ssrc)) if prefix[i]=='A'],[stgt[i] for i in range(len(stgt)) if prefix[i]=='A'],[vol[i]/1.5 for i in range(len(vol)) if prefix[i]=='A'],1.5)
        self.e.stage('LigAnnealB',[self.r.MLigB],[ssrc[i] for i in range(len(ssrc)) if prefix[i]=='B'],[stgt[i] for i in range(len(stgt)) if prefix[i]=='B'],[vol[i]/1.5 for i in range(len(vol)) if prefix[i]=='B'],1.5)
 
        self.e.runpgm("TRPANN",5,False,max(vol))
        self.e.stage('Ligation',[self.r.MLigase],[],stgt,vol)
        self.e.runpgm("TRPLIG",40,False,max(vol))
        return tgt
 
    def runPCR(self,prefix,src,tgt,vol,srcdil):
        ## PCR
        # e.g. trp.runPCR(prefix=["A"],src=["1.RT+"],tgt=["1.PCR"],vol=[50],srcdil=[5])
        [prefix,src,tgt,vol,srcdil]=listify([prefix,src,tgt,vol,srcdil])
        if len(tgt)==0:
            tgt=["%s.P%c"%(src[i],prefix[i]) for i in range(len(src))]

        stgt=findsamps(tgt)
        ssrc=findsamps(src,False)
        adjustSrcDil(ssrc,srcdil)
        
        self.e.stage('PCRA',[self.r.PCRA],[ssrc[i] for i in range(len(ssrc)) if prefix[i]=='A'],[stgt[i] for i in range(len(stgt)) if prefix[i]=='A'],[vol[i] for i in range(len(vol)) if prefix[i]=='A'])
        self.e.stage('PCRB',[self.r.PCRB],[ssrc[i] for i in range(len(ssrc)) if prefix[i]=='B'],[stgt[i] for i in range(len(stgt)) if prefix[i]=='B'],[vol[i] for i in range(len(vol)) if prefix[i]=='B'])
        self.e.runpgm("PCR20",60,False,max(vol))
        return tgt
    
    def diluteInPlace(self,tgt,dil):
        # Dilute in place
        # e.g.: trp.diluteInPlace(tgt=rt1,dil=2)
        [tgt,dil]=listify([tgt,dil])
        stgt=findsamps(tgt,False)
        adjustSrcDil(stgt,dil);
        self.e.stage('Dilute',[],[],stgt,[stgt[i].volume*dil[i] for i in range(len(stgt))])
        return tgt
        
    def runQPCRDIL(self,src,vol,srcdil):
        ## QPCR setup
        # e.g. trp.runQPCR(src=["1.RT-B","1.RT+B","1.RTNeg-B","1.RTNeg+B","2.RT-A","2.RT-B","2.RTNeg+B","2.RTNeg+B"],vol=10,srcdil=100)
        [src,vol,srcdil]=listify([src,vol,srcdil])
        tgtdil=["%s.D"%(src[i]) for i in range(len(src))]
        stgtdil=findsamps(tgtdil,True,Experiment.QPCRPLATE)
        ssrc=findsamps(src,False)
        adjustSrcDil(ssrc,[d for d in srcdil])
        
        self.e.stage('QPCRDIL',[],ssrc,stgtdil,max(vol))
        return tgtdil
        
    def runQPCR(self,src,vol,srcdil):
        ## QPCR setup
        # e.g. trp.runQPCR(src=["1.RT-B","1.RT+B","1.RTNeg-B","1.RTNeg+B","2.RT-A","2.RT-B","2.RTNeg+B","2.RTNeg+B"],vol=10,srcdil=100)
        [src,vol,srcdil]=listify([src,vol,srcdil])
        tgtqpcrA=["%s.QA"%(src[i]) for i in range(len(src))]+["Water.QA"]   # Extra sample for water
        tgtqpcrB=["%s.QB"%(src[i]) for i in range(len(src))] +["Water.QB"]
        vol=vol+[vol[1]]   # For water sample
        stgtqpcrA=findsamps(tgtqpcrA,True,Experiment.QPCRPLATE)
        stgtqpcrB=findsamps(tgtqpcrB,True,Experiment.QPCRPLATE)
        ssrc=findsamps(src,False)
        adjustSrcDil(ssrc,[d for d in srcdil])
        
        self.e.stage('QPCRA',[self.r.MQA],ssrc,stgtqpcrA,vol,1.0,False)  # No dest mix
        self.e.stage('QPCRB',[self.r.MQB],ssrc,stgtqpcrB,vol,1.0,False)
        return stgtqpcrA+stgtqpcrB

