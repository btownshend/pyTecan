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
    MLigAN7=Sample("MLigAN7",Experiment.REAGENTPLATE,None,3)
    MLigBN7=Sample("MLigBN7",Experiment.REAGENTPLATE,None,3)
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
    MQM=Sample("MQM",Experiment.REAGENTPLATE,None,10.0/6)
    MQT=Sample("MQT",Experiment.REAGENTPLATE,None,10.0/6)
    SSD=Sample("SSD",Experiment.REAGENTPLATE,None,10.0)
    all=[MT7,MPosRT,MNegRT,MLigAN7,MLigBN7,MLigase,Theo,MStopNT,MStopWT,MQA,MQB,PCRA,PCRB,MQM,MQT,SSD]

def listify(x):
    'Convert a list of (lists or scalars) into a list of equal length lists'
    n=1
    for i in x:
        if isinstance(i,list):
            n=max(n,len(i))
    result=[]
    for i in x:
        if isinstance(i,list):
            assert(len(i)==n or len(i)==0)
            result.append(i)
        else:
            result.append([i for j in range(n)])
    return result

# Make sure all target names are uniques
def uniqueTargets(tgts):
    for i in range(len(tgts)):
        if tgts[i] in tgts[:i]:
            for k in range(100):
                nm="%s.%d"%(tgts[i],k+2)
                if nm not in tgts:
                    tgts[i]=nm;
                    break
    return tgts

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
        if src[i].conc==None:
            #            src[i].conc=Concentration(srcdil[i],1)
            pass
        else:
            src[i].conc.final=src[i].conc.stock*1.0/srcdil[i]

class TRP(object):
           
    def __init__(self):
        'Create a new TRP run'
        self.e=Experiment()
        self.r=Reagents();
        self.e.setreagenttemp(6.0)
        self.e.sanitize(3,50)    # Heavy sanitize
            
    def addTemplates(self,names,stockconc,finalconc=1.0,units="nM",plate=Experiment.REAGENTPLATE):
        for s in names:
            Sample(s,plate,None,Concentration(stockconc,finalconc,units))

    def finish(self):
        self.e.lihahome()
        self.e.w.userprompt("Process complete. Continue to turn off reagent cooler")
        self.e.setreagenttemp(None)

        #Sample.printallsamples("At completion")
        hasError=False
        for s in Sample.getAllOnPlate():
            if s.volume<1.0 and s.conc!=None:
                print "ERROR: Insufficient volume for ", s," need at least ",1.0-s.volume," ul additional"
                hasError=True
            elif s.volume<2.5 and s.conc!=None:
                print "WARNING: Low final volume for ", s
            elif s.volume>s.plate.maxVolume:
                print "ERROR: Excess final volume  (",s.volume,") for ",s,", maximum is ",s.plate.maxVolume
                hasError=True
            elif s.initvolume>s.plate.maxVolume:
                print "ERROR: Excess initial volume (",s.initvolume,") for ",s,", maximum is ",s.plate.maxVolume
                hasError=True
                
        if hasError:
            print "NO OUTPUT DUE TO ERRORS"
            assert(False)
            
        # Save worklist to a file
        #e.saveworklist("trp1.gwl")
        (scriptname,ext)=os.path.splitext(sys.argv[0])
        self.e.savegem(scriptname+".gem")
        self.e.savesummary(scriptname+".txt")
        Sample.savematlab(scriptname+".m")
        
    def saveSamps(self,src,vol,dil,tgt=None,dilutant=None,plate=None):
        if tgt==None:
            tgt=[]
        [src,vol,dil]=listify([src,vol,dil])
        if len(tgt)==0:
            tgt=["%s.D%.0f"%(src[i],dil[i]) for i in range(len(src))]
        tgt=uniqueTargets(tgt)
        if plate==None:
            plate=self.e.REAGENTPLATE
            
        stgt=findsamps(tgt,True,plate)
        ssrc=findsamps(src,False)

        origdil=[x.conc.stock/x.conc.final for x in ssrc]
        # print "About to dilute ",str(ssrc[0])," by ",dil[0]," using ",vol[0]," ul, origdil=",origdil[0]
        adjustSrcDil(ssrc,dil)
        if dilutant!=None:
            if dilutant.conc==None:
                self.e.stage('SAVE',[],ssrc,stgt,[vol[i]*dil[i] for i in range(len(vol))],dilutant=dilutant)
            else:
                self.e.stage('SAVE',[dilutant],ssrc,stgt,[vol[i]*dil[i] for i in range(len(vol))])
        else:
            self.e.stage('SAVE',[],ssrc,stgt,[vol[i]*dil[i] for i in range(len(vol))])
        # Back out the dilution
        adjustSrcDil(ssrc,origdil)
        return tgt
            
    def runT7(self,theo,src,vol,srcdil,tgt=None,dur=15):
        if tgt==None:
            tgt=[]
        [theo,src,tgt,srcdil]=listify([theo,src,tgt,srcdil])
        if len(tgt)==0:
            for i in range(len(src)):
                if theo[i]:
                    tgt.append("%s.T+"%src[i])
                else:
                    tgt.append("%s.T-"%src[i])

        tgt=uniqueTargets(tgt)
        # Convert sample names to actual samples
        stgt=findsamps(tgt)
        ssrc=findsamps(src,False)
        adjustSrcDil(ssrc,srcdil)
        self.e.w.comment("runT7: source=%s"%[str(s) for s in ssrc])

        MT7vol=vol*1.0/self.r.MT7.conc.dilutionneeded()
        sourcevols=[vol*1.0/s.conc.dilutionneeded() for s in ssrc]
        theovols=[vol*1.0/self.r.Theo.conc.dilutionneeded()*(1 if t else 0) for t in theo]
        watervols=[vol-theovols[i]-sourcevols[i]-MT7vol for i in range(len(ssrc))]

        if sum(watervols)>0.01:
            self.e.multitransfer(watervols,self.e.WATER,stgt,(False,False))
        self.e.multitransfer([MT7vol for s in stgt],self.r.MT7,stgt,(False,False))
        self.e.multitransfer([tv for tv in theovols if tv>0.01],self.r.Theo,[stgt[i] for i in range(len(theovols)) if theovols[i]>0],(False,False),ignoreContents=True);
        for i in range(len(ssrc)):
            self.e.transfer(sourcevols[i],ssrc[i],stgt[i],(True,True))

        self.e.runpgm("TRP37-%d"%dur,dur, False,vol)

        ## Stop
        self.e.dilute(stgt,2)

        for i in range(len(stgt)):
            if theo[i]:
                self.e.transfer(vol,self.r.MStopNT,stgt[i],(False,True))
            else:
                self.e.transfer(vol,self.r.MStopWT,stgt[i],(False,True))

        return tgt
    
    def runRT(self,pos,src,vol,srcdil,tgt=None):
        if tgt==None:
            tgt=[]
        [pos,src,tgt,vol,srcdil]=listify([pos,src,tgt,vol,srcdil])
        if len(tgt)==0:
            for i in range(len(src)):
                if pos[i]:
                    tgt.append("%s.RT+"%src[i])
                else:
                    tgt.append("%s.RT-"%src[i])

        tgt=uniqueTargets(tgt)
        stgt=findsamps(tgt)
        ssrc=findsamps(src,False)
        adjustSrcDil(ssrc,srcdil)

        #    e.stage('MPosRT',[self.r.MOSBuffer,self.r.MOS],[],[self.r.MPosRT],ASPIRATEFACTOR*(self.vol.RT*nRT/2)/2+self.vol.Extra+MULTIEXCESS,2)
        #    e.stage('MNegRT',[self.r.MOSBuffer],[],[self.r.MNegRT],ASPIRATEFACTOR*(self.vol.RT*negRT)/2+self.vol.Extra+MULTIEXCESS,2)
        if any(p for p in pos):
            self.e.stage('RTPos',[self.r.MPosRT],[ssrc[i] for i in range(len(ssrc)) if pos[i]],[stgt[i] for i in range(len(stgt)) if pos[i]],[vol[i] for i in range(len(vol)) if pos[i]])
        if any(not p for p in pos):
            self.e.stage('RTNeg',[self.r.MNegRT],[ssrc[i] for i in range(len(ssrc)) if not pos[i]],[stgt[i] for i in range(len(stgt)) if not pos[i]],[vol[i] for i in range(len(vol)) if not pos[i]])
        self.e.runpgm("TRP37-20",20,False,max(vol))
        return tgt
 
    def runLig(self,prefix,src,vol,srcdil,tgt=None,ligA="MLigAN7",ligB="MLigBN7"):
        if tgt==None:
            tgt=[]
        #Extension
        # e.g: trp.runLig(prefix=["B","B","B","B","B","B","B","B"],src=["1.RT-","1.RT+","1.RTNeg-","1.RTNeg+","2.RT-","2.RT-","2.RTNeg+","2.RTNeg+"],tgt=["1.RT-B","1.RT+B","1.RTNeg-B","1.RTNeg+B","2.RT-A","2.RT-B","2.RTNeg+B","2.RTNeg+B"],vol=[10,10,10,10,10,10,10,10],srcdil=[2,2,2,2,2,2,2,2])
        [prefix,src,tgt,vol,srcdil,ligA]=listify([prefix,src,tgt,vol,srcdil,ligB])
        if len(tgt)==0:
            tgt=["%s.L%c"%(src[i],prefix[i]) for i in range(len(src))]

        tgt=uniqueTargets(tgt)
        stgt=findsamps(tgt)
        ssrc=findsamps(src,False)
        sligA=findsamps(ligA,False)
        sligB=findsamps(ligB,False)

        if prefix[0]=='A':
            # Need to check since an unused ligation master mix will not have a concentration
            minsrcdil=1/(1-1/sligA[0].conc.dilutionneeded()-1/self.r.MLigase.conc.dilutionneeded())
        else:
            minsrcdil=1/(1-1/sligB[0].conc.dilutionneeded()-1/self.r.MLigase.conc.dilutionneeded())
            
        for i in srcdil:
            if i<minsrcdil:
                print "runLig: srcdil=%.2f, but must be at least %.2f"%(i,minsrcdil)
                assert(False)

        adjustSrcDil(ssrc,srcdil)

        for i in range(len(stgt)):
            if prefix[i]=='A':
                self.e.stage('LigAnnealA',[sligA[i]],[ssrc[i]],[stgt[i]],[vol[i]/1.5],1.5)
            else:
                self.e.stage('LigAnnealB',[sligB[i]],[ssrc[i]],[stgt[i]],[vol[i]/1.5],1.5)
            
        self.e.runpgm("TRPANN",5,False,max(vol),hotlidmode="CONSTANT",hotlidtemp=100)
        self.e.stage('Ligation',[self.r.MLigase],[],stgt,vol)
        self.e.runpgm("LIG15RT",26,False,max(vol),hotlidmode="TRACKING",hotlidtemp=10)
        return tgt
 
    def runPCR(self,prefix,src,vol,srcdil,tgt=None,ncycles=20):
        if tgt==None:
            tgt=[]
        ## PCR
        # e.g. trp.runPCR(prefix=["A"],src=["1.RT+"],tgt=["1.PCR"],vol=[50],srcdil=[5])
        [prefix,src,tgt,vol,srcdil]=listify([prefix,src,tgt,vol,srcdil])
        if len(tgt)==0:
            tgt=["%s.P%c"%(src[i],prefix[i]) for i in range(len(src))]

        tgt=uniqueTargets(tgt)
        stgt=findsamps(tgt)
        ssrc=findsamps(src,False)
        adjustSrcDil(ssrc,srcdil)
        
        if any(p=='A' for p in prefix):
               self.e.stage('PCRA',[self.r.PCRA],[ssrc[i] for i in range(len(ssrc)) if prefix[i]=='A'],[stgt[i] for i in range(len(stgt)) if prefix[i]=='A'],[vol[i] for i in range(len(vol)) if prefix[i]=='A'])
        if any(p=='B' for p in prefix):
               self.e.stage('PCRB',[self.r.PCRB],[ssrc[i] for i in range(len(ssrc)) if prefix[i]=='B'],[stgt[i] for i in range(len(stgt)) if prefix[i]=='B'],[vol[i] for i in range(len(vol)) if prefix[i]=='B'])
        pgm="PCR%d"%ncycles;
        #        self.e.w.pyrun('PTC\\ptcsetpgm.py %s TEMP@95,120 TEMP@95,30 TEMP@55,30 TEMP@72,25 GOTO@2,%d TEMP@72,180 TEMP@16,2'%(pgm,ncycles-1));
        self.e.w.pyrun('PTC\\ptcsetpgm.py %s TEMP@95,120 TEMP@95,10 TEMP@57,10 GOTO@2,%d TEMP@72,120 TEMP@25,2'%(pgm,ncycles-1));
        self.e.runpgm(pgm,4.80+1.55*ncycles,False,max(vol),hotlidmode="CONSTANT",hotlidtemp=100)
        return tgt
    
    def diluteInPlace(self,tgt,dil):
        # Dilute in place
        # e.g.: trp.diluteInPlace(tgt=rt1,dil=2)
        [tgt,dil]=listify([tgt,dil])
        tgt=uniqueTargets(tgt)
        stgt=findsamps(tgt,False)
        adjustSrcDil(stgt,dil)
        self.e.stage('Dilute',[],[],stgt,[stgt[i].volume*dil[i] for i in range(len(stgt))])
        return tgt
        
    def runQPCRDIL(self,src,vol,srcdil,tgt=None,dilPlate=False):
        if isinstance(srcdil,list) and ( not isinstance(src,list) or len(srcdil)!=len(src)):
            print "Cannot have multiple dilutions for a single sample"
            assert(FALSE)
            
        if tgt==None:
            tgt=[]
        ## QPCR setup
        # e.g. trp.runQPCR(src=["1.RT-B","1.RT+B","1.RTNeg-B","1.RTNeg+B","2.RT-A","2.RT-B","2.RTNeg+B","2.RTNeg+B"],vol=10,srcdil=100)
        [src,vol,srcdil]=listify([src,vol,srcdil])
        if len(tgt)==0:
            tgt=["%s.D%.0f"%(src[i],srcdil[i]) for i in range(len(src))]
        tgt=uniqueTargets(tgt)
        if dilPlate:
            stgt=findsamps(tgt,True,Experiment.DILPLATE)
        else:
            stgt=findsamps(tgt,True,Experiment.QPCRPLATE)
        ssrc=findsamps(src,False)
        adjustSrcDil(ssrc,[d for d in srcdil])
        
        self.e.stage('QPCRDIL',[Reagents.SSD],ssrc,stgt,max(vol))
        return tgt
        
    def runQPCR(self,src,vol,srcdil,primers=["A","B"]):
        ## QPCR setup
        # e.g. trp.runQPCR(src=["1.RT-B","1.RT+B","1.RTNeg-B","1.RTNeg+B","2.RT-A","2.RT-B","2.RTNeg+B","2.RTNeg+B"],vol=10,srcdil=100)
        self.e.w.comment("runQPCR: primers=%s, source=%s"%([p for p in primers],[s for s in src]))
        [src,vol,srcdil]=listify([src,vol,srcdil])
        ssrc=findsamps(src,False)
        adjustSrcDil(ssrc,[d for d in srcdil])

        # Build a list of sets to be run
        all=[]
        for i in range(len(ssrc)):
            for p in primers:
                tgt=findsamps(["%s.Q%s"%(src[i],p)],True,Experiment.QPCRPLATE)
                all=all+[(ssrc[i],tgt[0],p,vol[i])]

        # Fill the master mixes
        dil={}
        for p in primers:
            mq=findsamps(["MQ%s"%p],False)[0]
            t=[a[1] for a in all if a[2]==p]
            v=[a[3]/mq.conc.dilutionneeded() for a in all if a[2]==p]
            self.e.multitransfer(v,mq,t,(False,False))
            dil[p]=1.0/(1-1/mq.conc.dilutionneeded())
            
        # Add the samples
        self.e.w.setOptimization(True)
        for s in ssrc:
            t=[a[1] for a in all if a[0]==s]
            v=[a[3]/dil[a[2]] for a in all if a[0]==s]
            for i in range(len(t)):
                self.e.transfer(v[i],s,t[i],(False,False))
        self.e.w.setOptimization(False)
        
        return [a[1] for a in all]
