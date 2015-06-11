from Experiment.sample import Sample, ASPIRATEFACTOR
from Experiment.experiment import Experiment
from Experiment.experiment import Concentration
import os
import sys
import math

maxVolumePerWell=150

class Reagents:
    MT7=Sample("MT7",Experiment.REAGENTPLATE,"A1",2.5)
    MPosRT=Sample("MPosRT",Experiment.REAGENTPLATE,"B1",2)
    MNegRT=Sample("MNegRT",Experiment.REAGENTPLATE,None,2)
    MLigAT7=Sample("MLigAT7",Experiment.REAGENTPLATE,"D1",3)	# Conc is relative to annealing time (not to post-ligase)
    MLigBT7W=Sample("MLigBT7W",Experiment.REAGENTPLATE,"E1",3)
    MLigase=Sample("MLigase",Experiment.REAGENTPLATE,"A2",3)

    Theo=Sample("Theo",Experiment.REAGENTPLATE,None,Concentration(25,7.5,'mM'))
    #EDTA=Sample("EDTA",Experiment.REAGENTPLATE,None,Concentration(50.0,4,'mM'))
    #BT43=Sample("BT43",Experiment.REAGENTPLATE,None,Concentration(10,0.5,'uM'))
    #EVA=Sample("EvaGreen",Experiment.REAGENTPLATE,None,2)
    #BT47=Sample("BT047",Experiment.REAGENTPLATE,None,Concentration(10,0.4,'uM'))
    #BT29=Sample("BT029",Experiment.REAGENTPLATE,None,Concentration(10,0.4,'uM'))
    #BT30=Sample("BT030",Experiment.REAGENTPLATE,None,Concentration(10,0.4,'uM'))
    MStopX=Sample("MStpX",Experiment.REAGENTPLATE,"C2",2)
    MQRef=Sample("MQREF",Experiment.REAGENTPLATE,"D2",10.0/6)
    MQAX=Sample("MQAX",Experiment.REAGENTPLATE,"E2",10.0/6)
    MQBX=Sample("MQBX",Experiment.REAGENTPLATE,"A3",10.0/6)
    PCRAX=Sample("MPCRAX",Experiment.REAGENTPLATE,"B3",4.0/3)
    PCRBX=Sample("MPCRBX",Experiment.REAGENTPLATE,"C3",4.0/3)
    MQMX=Sample("MQMX",Experiment.REAGENTPLATE,"D3",10.0/6)
    MQWX=Sample("MQWX",Experiment.REAGENTPLATE,"E3",10.0/6)
    SSD=Sample("SSD",Experiment.REAGENTPLATE,"A4",10.0)
    MLigAT7W=Sample("MLigAT7W",Experiment.REAGENTPLATE,"B4",3)
    BeadBuffer=Sample("BeadBuffer",Experiment.REAGENTPLATE,"C4",4)
    Dynabeads=Sample("Dynabeads",Experiment.REAGENTPLATE,"D4",Concentration(6,2,'mg/ml'))
    MQT7W=Sample("MQT7X",Experiment.REAGENTPLATE,"E4",15.0/9)
    MStopBeads=Sample("MStpBeads",Experiment.REAGENTPLATE,"A5",3.7)
    QPCRREF=Sample("QPCRREF",Experiment.REAGENTPLATE,"B5",Concentration(50,50,'pM'))
    all=[MT7,MPosRT,MNegRT,MLigAT7,MLigBT7W,MLigase,Theo,MStopX,MQRef,MQAX,MQBX,PCRAX,PCRBX,MQMX,SSD,MLigAT7W,MQWX,Dynabeads,MQT7W,BeadBuffer,MStopBeads,QPCRREF]
    UNUSED=Sample("LeakyA1",Experiment.SAMPLEPLATE,"A1",0)
    UNUSED2=Sample("LeakyH12",Experiment.SAMPLEPLATE,"H12",0)
    
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
                    tgts[i]=nm
                    break
    return tgts

def findsamps(x,createIfMissing=True,plate=Experiment.SAMPLEPLATE,unique=False):
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
        elif unique and t.volume>0:
            print "findsamps(%s) -> sample already exists and contains %.1ful but unique flag was set"%(i,t.volume)
            assert(False)
        s.append(t)
    return s

class TRP(object):
           
    def __init__(self):
        'Create a new TRP run'
        self.e=Experiment()
        self.r=Reagents()
        self.e.setreagenttemp(6.0)
        self.e.sanitize(3,50)    # Heavy sanitize
            
    def addTemplates(self,names,stockconc,finalconc=None,units="nM",plate=Experiment.REAGENTPLATE):
        if finalconc==None:
            print "Warning: final concentration of template not specified, assuming 0.6x (should add to addTemplates() call"
            [names,stockconc]=listify([names,stockconc])
            finalconc=[0.6*x for x in stockconc]
        else:
            [names,stockconc,finalconc]=listify([names,stockconc,finalconc])
        for i in range(len(names)):
            Sample(names[i],plate,None,Concentration(stockconc[i],finalconc[i],units))

    def finish(self):
        self.e.lihahome()
        self.e.w.userprompt("Process complete. Continue to turn off reagent cooler")
        self.e.setreagenttemp(None)

        #Sample.printallsamples("At completion")
        hasError=False
        for s in Sample.getAllOnPlate():
            if s.volume<1.0 and s.conc!=None and not s.hasBeads:
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
            
        stgt=findsamps(tgt,True,plate,unique=True)
        ssrc=findsamps(src,False)

        if dilutant==None:
            dilutant=self.e.WATER
        self.e.multitransfer([vol[i]*(dil[i]-1) for i in range(len(vol))],dilutant,stgt,(False,False))
        for i in range(len(ssrc)):
            self.e.transfer(vol[i],ssrc[i],stgt[i],(True,True))
            stgt[i].conc=Concentration(1.0/dil[i])
            
        return tgt
            
    def runT7Setup(self,theo,src,vol,srcdil,tgt):
        [theo,src,tgt,srcdil]=listify([theo,src,tgt,srcdil])
        if len(tgt)==0:
            for i in range(len(src)):
                if theo[i]:
                    tgt.append("%s.T+"%src[i])
                else:
                    tgt.append("%s.T-"%src[i])

        tgt=uniqueTargets(tgt)

        # Convert sample names to actual samples
        stgt=findsamps(tgt,unique=True)
        ssrc=findsamps(src,False)
        self.e.w.comment("runT7: source=%s"%[str(s) for s in ssrc])

        MT7vol=vol*1.0/self.r.MT7.conc.dilutionneeded()
        sourcevols=[vol*1.0/s.conc.dilutionneeded() for s in ssrc]
        theovols=[(vol*1.0/self.r.Theo.conc.dilutionneeded() if t else 0) for t in theo]
        watervols=[vol-theovols[i]-sourcevols[i]-MT7vol for i in range(len(ssrc))]

        if sum(watervols)>0.01:
            self.e.multitransfer(watervols,self.e.WATER,stgt,(False,False))
        self.e.multitransfer([MT7vol for s in stgt],self.r.MT7,stgt,(False,False))
        self.e.multitransfer([tv for tv in theovols if tv>0.01],self.r.Theo,[stgt[i] for i in range(len(theovols)) if theovols[i]>0],(False,False),ignoreContents=True)
        for i in range(len(ssrc)):
            self.e.transfer(sourcevols[i],ssrc[i],stgt[i],(True,True))
        return tgt
    
    def runT7Pgm(self,vol,dur):
        pgm="TRP37-%d"%dur
        self.e.w.pyrun('PTC\\ptcsetpgm.py %s TEMP@37,%d TEMP@25,2'%(pgm,dur*60))
        self.e.runpgm(pgm,dur, False,vol)

    def runT7Stop(self,theo,tgt,stopmaster=None,srcdil=2):
        [theo,tgt,stopmaster,srcdil]=listify([theo,tgt,stopmaster,srcdil])
        if stopmaster==None:
            stopmaster=["MStpS_NT" if t==0 else "MStpS_WT" for t in theo]
            
        stgt=findsamps(tgt,False)

        # Adjust source dilution
        for i in range(len(stgt)):
            stgt[i].conc=Concentration(srcdil[i],1)

        ## Stop
        sstopmaster=findsamps(stopmaster,False)
        for i in range(len(stgt)):
            stopvol=stgt[i].volume/(sstopmaster[i].conc.dilutionneeded()-1)
            finalvol=stgt[i].volume+stopvol
            self.e.transfer(finalvol-stgt[i].volume,sstopmaster[i],stgt[i],(False,True))
            
        return tgt
    
    def runT7(self,theo,src,vol,srcdil,tgt=None,dur=15,stopmaster=None):
        if tgt==None:
            tgt=[]
        [theo,src,tgt,srcdil,stopmaster]=listify([theo,src,tgt,srcdil,stopmaster])
        tgt=self.runT7Setup(theo,src,vol,srcdil,tgt)
        self.runT7Pgm(vol,dur)
        tgt=self.runT7Stop(theo,tgt,stopmaster)
        return tgt

    def intervalMix(self,src,dur,mixTime=60,useShaker=True):
        'Pause for incubations, mixing at regular intervals'
        ssrc=findsamps(src,False)
        if useShaker:
            self.e.shake(ssrc[0].plate,dur=mixTime)
        else:
            self.e.starttimer()
            if dur>mixTime:
                # Will need at least one mix
                # Get clean tips
                self.e.sanitize()
                while dur>mixTime:
                    if len(src)<=4:
                        # Fake that they are clean so we can reuse them for each mix
                        self.e.cleanTips=0xf
                    self.e.waittimer(mixTime)
                    self.e.starttimer()
                    dur=dur-mixTime
                    for s in ssrc:
                        self.e.mix(s,nmix=2)
                    self.e.w.flushQueue()
            self.e.waittimer(dur)

    def bindBeads(self,src,beads="Dynabeads",beadConc=None,buffer="BeadBuffer",incTime=60,addBuffer=False):
        [src,beads,buffer,beadConc]=listify([src,beads,buffer,beadConc])

        ssrc=findsamps(src,False)
        for s in ssrc:
            if s.plate!=self.e.SAMPLEPLATE:
                print "runBeadCleanup: src ",s," is not in sample plate."
                assert(0)
            
        sbeads=findsamps(beads,False)
        sbuffer=findsamps(buffer,False)
        # Calculate volumes needed
        if addBuffer:
            buffervol=[ssrc[i].volume/(sbuffer[i].conc.dilutionneeded()-1) for i in range(len(ssrc))]
            # Add binding buffer to bring to 1x (beads will already be in 1x, so don't need to provide for them)
            for i in range(len(ssrc)):
                self.e.transfer(buffervol[i],sbuffer[i],ssrc[i],(False,True))
        else:
            buffervol=[0.0 for i in range(len(ssrc))]

        beadConc=[sbeads[i].conc.final if beadConc[i]==None else beadConc[i] for i in range(len(sbeads))]
        beadvol=[(ssrc[i].volume+buffervol[i])/(sbeads[i].conc.stock/beadConc[i]-1) for i in range(len(ssrc))]

        # Transfer the beads
        for i in range(len(ssrc)):
            sbeads[i].isMixed=False	# Force a mix
            ssrc[i].conc=None		# Can't track concentration of beads
            self.e.transfer(beadvol[i],sbeads[i],ssrc[i],(i==0,False))	# Mix beads before
            ssrc[i].setHasBeads()	# Mark the source tubes as having beads to change condition, liquid classes
            
        self.intervalMix(src,incTime) # Wait for binding

    def sepWait(self,ssrc,sepTime=None):
        if sepTime==None:
            maxvol=max([s.volume for s in ssrc])
            if maxvol > 50:
                sepTime=60
            else:
                sepTime=30
        self.e.pause(sepTime)	# Wait for separation
        
    def beadWash(self,src,washTgt=None,sepTime=None,residualVolume=10,keepWash=False,numWashes=2,wash="Water",washVol=50,keepFinal=False,finalTgt=None,keepVol=4.2,keepDil=5):
        [src,wash]=listify([src,wash])
        ssrc=findsamps(src,False)
        # Do all washes while on magnet
        assert(len(set([s.plate for s in ssrc]))==1)	# All on same plate
        self.e.moveplate(ssrc[0].plate,"Magnet")	# Move to magnet
        self.sepWait(ssrc,sepTime)
        if keepWash:
            if washTgt==None:
                washTgt=[]
                for i in range(len(src)):
                    washTgt.append("%s.Wash"%src[i])
            if any([s.volume-residualVolume+numWashes*(washVol-residualVolume) > self.e.DILPLATE.maxVolume-20 for s in ssrc]):
                print "Saving %.1f ul of wash in eppendorfs"%(numWashes*washVol)
                sWashTgt=findsamps(washTgt,plate=self.e.EPPENDORFS,unique=True)
            else:
                sWashTgt=findsamps(washTgt,plate=self.e.DILPLATE,unique=True)

        if keepFinal:
            if finalTgt==None:
                finalTgt=[]
                for i in range(len(src)):
                    finalTgt.append("%s.Final"%src[i])

        if any([s.volume>residualVolume for s in ssrc]):
            # Separate and remove supernatant

            # Remove the supernatant
            for i in range(len(ssrc)):
                if ssrc[i].volume > residualVolume:
                    if keepWash:
                        self.e.transfer((ssrc[i].volume-residualVolume)/ASPIRATEFACTOR,ssrc[i],sWashTgt[i])	# Keep supernatants
                        sWashTgt[i].conc=None	# Allow it to be reused
                        sWashTgt[i].setHasBeads()   # To have it mixed before any aspirations
                    else:
                        self.e.dispose((ssrc[i].volume-residualVolume)/ASPIRATEFACTOR,ssrc[i])	# Discard supernatant
                
        # Wash
        swash=findsamps(wash,False)
        for washnum in range(numWashes):
            if keepFinal and washnum==numWashes-1:
                'Retain sample of final'
                self.e.moveplate(ssrc[0].plate,"Home")
                for i in range(len(ssrc)):
                    self.e.transfer(washVol-ssrc[i].volume,swash[i],ssrc[i],mix=(False,True))	# Add wash

                self.saveSamps(src=src,tgt=finalTgt,vol=keepVol,dil=keepDil,plate=Experiment.DILPLATE)
                self.e.moveplate(ssrc[0].plate,"Magnet")	# Move to magnet
            else:
                for i in range(len(ssrc)):
                    self.e.transfer(washVol-ssrc[i].volume,swash[i],ssrc[i],mix=(False,False))	# Add wash

            self.sepWait(ssrc,sepTime)
                
            for i in range(len(ssrc)):
                if keepWash:
                    self.e.transfer((ssrc[i].volume-residualVolume)/ASPIRATEFACTOR,ssrc[i],sWashTgt[i])	# Remove wash
                    sWashTgt[i].conc=None	# Allow it to be reused
                else:
                    self.e.dispose((ssrc[i].volume-residualVolume)/ASPIRATEFACTOR,ssrc[i])	# Remove wash

        self.e.moveplate(ssrc[0].plate,"Home")

        # Should only be residualVolume left with beads now
        result=[]
        if keepWash:
            result=result+washTgt
        if keepFinal:
            result=result+finalTgt

        return result

    def beadAddElutant(self,src,elutant="Water",elutionVol=30,eluteTime=60):
        [src,elutionVol,elutant]=listify([src,elutionVol,elutant])
        ssrc=findsamps(src,False)
        selutant=findsamps(elutant,False)
        for i in range(len(ssrc)):
            if elutionVol[i]<30:
                print "Warning: elution from beads with %.1f ul < minimum of 30ul"%elutionVol[i]
                print "  src=",ssrc[i]
            self.e.transfer(elutionVol[i]-ssrc[i].volume,selutant[i],ssrc[i],(False,True))	# Add elution buffer and mix

        # Go through some cycles of waiting, mixing
        self.intervalMix(src,eluteTime)

    def beadSupernatant(self,src,tgt=None,sepTime=None,residualVolume=10,plate=None):
        if tgt==None:
            tgt=[]

        [src,tgt]=listify([src,tgt])
        if len(tgt)==0:
            for i in range(len(src)):
                tgt.append("%s.SN"%src[i])
        ssrc=findsamps(src,False)
        stgt=findsamps(tgt,plate=plate,unique=True)

        self.e.moveplate(ssrc[0].plate,"Magnet")	# Move to magnet
        self.sepWait(ssrc,sepTime)

        for i in range(len(ssrc)):
            self.e.transfer((ssrc[i].volume-residualVolume)/ASPIRATEFACTOR,ssrc[i],stgt[i])	# Transfer elution to new tube

        self.e.moveplate(ssrc[0].plate,"Home")
        return tgt
    
    def runRT(self,pos,src,vol,srcdil,tgt=None,dur=20):
        result=self.runRTSetup(pos,src,vol,srcdil,tgt)
        self.runRTPgm(dur)
        return result
    
    def runRxOnBeads(self,src,vol,master):
        'Run reaction on beads in given total volume'
        [vol,src,master]=listify([vol,src,master])
        ssrc=findsamps(src,False)
        smaster=findsamps(master)
        mastervol=[vol[i]/smaster[i].conc.dilutionneeded() for i in range(len(vol))]
        watervol=[vol[i]-ssrc[i].volume-mastervol[i] for i in range(len(vol))]
        if any([w < -0.01 for w in watervol]):
            print "runRTOnBeads: negative amount of water needed"
            assert(False)
        for i in range(len(ssrc)):
            if  watervol[i]>0:
                self.e.transfer(watervol[i],self.e.WATER,ssrc[i],(False,False))
        for i in range(len(ssrc)):
            self.e.transfer(mastervol[i],smaster[i],ssrc[i],(False,True))

    def runRTOnBeads(self,src,vol,dur=20):
        'Run RT on beads in given volume'
        self.runRxOnBeads(src,vol,"MPosRT")
        self.runRTPgm(dur)
        
    def runRTSetup(self,pos,src,vol,srcdil,tgt=None):
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
        stgt=findsamps(tgt,unique=True)
        ssrc=findsamps(src,False)

        # Adjust source dilution
        for i in range(len(ssrc)):
            ssrc[i].conc=Concentration(srcdil[i],1)
            
        #    e.stage('MPosRT',[self.r.MOSBuffer,self.r.MOS],[],[self.r.MPosRT],ASPIRATEFACTOR*(self.vol.RT*nRT/2)/2+self.vol.Extra+MULTIEXCESS,2)
        #    e.stage('MNegRT',[self.r.MOSBuffer],[],[self.r.MNegRT],ASPIRATEFACTOR*(self.vol.RT*negRT)/2+self.vol.Extra+MULTIEXCESS,2)
        if any(p for p in pos):
            self.e.stage('RTPos',[self.r.MPosRT],[ssrc[i] for i in range(len(ssrc)) if pos[i]],[stgt[i] for i in range(len(stgt)) if pos[i]],[vol[i] for i in range(len(vol)) if pos[i]])
        if any(not p for p in pos):
            self.e.stage('RTNeg',[self.r.MNegRT],[ssrc[i] for i in range(len(ssrc)) if not pos[i]],[stgt[i] for i in range(len(stgt)) if not pos[i]],[vol[i] for i in range(len(vol)) if not pos[i]])
        return tgt

    def runRTPgm(self,dur=20):
        pgm="TRP37-%d"%dur
        self.e.w.pyrun('PTC\\ptcsetpgm.py %s TEMP@37,%d TEMP@25,2'%(pgm,dur*60))
        self.e.runpgm("TRP37-%d"%dur,dur,False,100)		# Volume doesn't matter since it's just an incubation, use 100ul
 
    def runLig(self,prefix=None,src=None,vol=None,srcdil=None,tgt=None,master=None,anneal=True,ligtemp=25):
        if tgt==None:
            tgt=[]
        if master==None:
            master=["MLigAN7" if p=='A' else "MLigBN7" for p in prefix]

        #Extension
        # e.g: trp.runLig(prefix=["B","B","B","B","B","B","B","B"],src=["1.RT-","1.RT+","1.RTNeg-","1.RTNeg+","2.RT-","2.RT-","2.RTNeg+","2.RTNeg+"],tgt=["1.RT-B","1.RT+B","1.RTNeg-B","1.RTNeg+B","2.RT-A","2.RT-B","2.RTNeg+B","2.RTNeg+B"],vol=[10,10,10,10,10,10,10,10],srcdil=[2,2,2,2,2,2,2,2])
        [src,tgt,vol,srcdil,master]=listify([src,tgt,vol,srcdil,master])
        if len(tgt)==0:
            tgt=["%s.%s"%(src[i],master[i]) for i in range(len(src))]

        tgt=uniqueTargets(tgt)
        stgt=findsamps(tgt,unique=True)
        ssrc=findsamps(src,False)
        smaster=findsamps(master,False)

        # Need to check since an unused ligation master mix will not have a concentration
        minsrcdil=1/(1-1/smaster[0].conc.dilutionneeded()-1/self.r.MLigase.conc.dilutionneeded())
        for i in srcdil:
            if i<minsrcdil:
                print "runLig: srcdil=%.2f, but must be at least %.2f based on concentrations of master mixes"%(i,minsrcdil)
                assert(False)

        # Adjust source dilution
        for i in range(len(ssrc)):
            ssrc[i].conc=Concentration(srcdil[i],1)

        i=0
        while i<len(stgt):
            lasti=i+1
            while lasti<len(stgt) and smaster[i]==smaster[lasti]:
                lasti=lasti+1
            self.e.stage('LigAnneal',[smaster[i]],ssrc[i:lasti],stgt[i:lasti],[vol[j]/1.5 for j in range(i,lasti)],1.5)
            i=lasti
            
        if anneal:
            self.e.runpgm("TRPANN",5,False,max(vol),hotlidmode="CONSTANT",hotlidtemp=100)
        self.e.stage('Ligation',[self.r.MLigase],[],stgt,vol)
        self.runLigPgm(max(vol),ligtemp)
        return tgt
        
    def runLigPgm(self,vol,ligtemp,inactivate=True):
        if inactivate:
            pgm="LIG15-%.0f"%ligtemp
            self.e.w.pyrun('PTC\\ptcsetpgm.py %s TEMP@%.0f,900 TEMP@65,600 TEMP@25,30'%(pgm,ligtemp))
            self.e.runpgm(pgm,27,False,vol,hotlidmode="TRACKING",hotlidtemp=10)
        elif ligtemp==25:
            self.e.w.comment('Ligation at room temp')
            self.e.pause(15*60)
        else:
            pgm="TRP%.0f-15"%ligtemp
            self.e.w.pyrun('PTC\\ptcsetpgm.py %s TEMP@%.0f,900 TEMP@25,30'%(pgm,ligtemp))
            self.e.runpgm(pgm,17,False,vol,hotlidmode="TRACKING",hotlidtemp=10)

    def runLigOnBeads(self,src,vol,ligmaster,anneal=True,ligtemp=25):
        'Run ligation on beads'
        [vol,src]=listify([vol,src])
        annealvol=[v*(1-1/self.r.MLigase.conc.dilutionneeded()) for v in vol]
        ssrc=findsamps(src,False)
        self.runRxOnBeads(src,annealvol,ligmaster)
        if anneal:
            self.e.runpgm("TRPANN",5,False,max([s.volume for s in ssrc]),hotlidmode="CONSTANT",hotlidtemp=100)

        ## Add ligase
        self.runRxOnBeads(src,vol,"MLigase")
        self.runLigPgm(max(vol),ligtemp,inactivate=False)	# Do not heat inactivate since it may denature the beads

    def runPCR(self,prefix,src,vol,srcdil,tgt=None,ncycles=20,suffix='S'):
        if tgt==None:
            tgt=[]
        ## PCR
        # e.g. trp.runPCR(prefix=["A"],src=["1.RT+"],tgt=["1.PCR"],vol=[50],srcdil=[5])
        [prefix,src,tgt,vol,srcdil,suffix]=listify([prefix,src,tgt,vol,srcdil,suffix])
        if len(tgt)==0:
            tgt=["%s.P%c%c"%(src[i],prefix[i],suffix[i]) for i in range(len(src))]

        tgt=uniqueTargets(tgt)
        stgt=findsamps(tgt,unique=True)
        #print "stgt[0]=",str(stgt[0])
        ssrc=findsamps(src,False)
        
        primer=[prefix[i]+suffix[i] for i in range(len(prefix))]
        #print "primer=",primer
        if any(p=='AS' for p in primer):
               self.e.stage('PCRAS',[self.r.PCRAS],[ssrc[i] for i in range(len(ssrc)) if primer[i]=='AS'],[stgt[i] for i in range(len(stgt)) if primer[i]=='AS'],[vol[i] for i in range(len(vol)) if primer[i]=='AS'])
        if any(p=='BS' for p in primer):
               self.e.stage('PCRBS',[self.r.PCRBS],[ssrc[i] for i in range(len(ssrc)) if primer[i]=='BS'],[stgt[i] for i in range(len(stgt)) if primer[i]=='BS'],[vol[i] for i in range(len(vol)) if primer[i]=='BS'])
        if any(p=='AX' for p in primer):
               self.e.stage('PCRAX',[self.r.PCRAX],[ssrc[i] for i in range(len(ssrc)) if primer[i]=='AX'],[stgt[i] for i in range(len(stgt)) if primer[i]=='AX'],[vol[i] for i in range(len(vol)) if primer[i]=='AX'])
        if any(p=='BX' for p in primer):
               self.e.stage('PCRBX',[self.r.PCRBX],[ssrc[i] for i in range(len(ssrc)) if primer[i]=='BX'],[stgt[i] for i in range(len(stgt)) if primer[i]=='BX'],[vol[i] for i in range(len(vol)) if primer[i]=='BX'])
        pgm="PCR%d"%ncycles
        #        self.e.w.pyrun('PTC\\ptcsetpgm.py %s TEMP@95,120 TEMP@95,30 TEMP@55,30 TEMP@72,25 GOTO@2,%d TEMP@72,180 TEMP@16,2'%(pgm,ncycles-1))
        self.e.w.pyrun('PTC\\ptcsetpgm.py %s TEMP@95,120 TEMP@95,10 TEMP@57,10 GOTO@2,%d TEMP@72,120 TEMP@25,2'%(pgm,ncycles-1))
        self.e.runpgm(pgm,4.80+1.55*ncycles,False,max(vol),hotlidmode="CONSTANT",hotlidtemp=100)
        return tgt

    def runPCROnBeads(self,prefix,src,vol,ncycles,suffix,annealtemp=57):
        [prefix,src,vol,suffix]=listify([prefix,src,vol,suffix])

        primer=["MPCR"+prefix[i]+suffix[i] for i in range(len(prefix))]
        self.runRxOnBeads(src,vol,primer)

        pgm="PCR%d"%ncycles
        #        self.e.w.pyrun('PTC\\ptcsetpgm.py %s TEMP@95,120 TEMP@95,30 TEMP@55,30 TEMP@72,25 GOTO@2,%d TEMP@72,180 TEMP@16,2'%(pgm,ncycles-1))
        self.e.w.pyrun('PTC\\ptcsetpgm.py %s TEMP@95,120 TEMP@95,10 TEMP@%f,10 GOTO@2,%d TEMP@72,120 TEMP@25,2'%(pgm,annealtemp,ncycles-1))
        self.e.runpgm(pgm,4.80+1.55*ncycles,False,max(vol),hotlidmode="CONSTANT",hotlidtemp=100)
    
    def diluteInPlace(self,tgt,dil=None,finalvol=None):
        # Dilute in place
        # e.g.: trp.diluteInPlace(tgt=rt1,dil=2)
        [tgt,dil,finalvol]=listify([tgt,dil,finalvol])
        tgt=uniqueTargets(tgt)
        stgt=findsamps(tgt,False)
        dilutant=self.e.WATER
        for i in range(len(stgt)):
            if finalvol[i]!=None and dil[i]==None:
                self.e.transfer(finalvol[i]-stgt[i].volume,dilutant,stgt[i],mix=(False,True))
            elif finalvol[i]==None and dil[i]!=None:
                self.e.transfer(stgt[i].volume*(dil[i]-1),dilutant,stgt[i],mix=(False,True))
            else:
                print "diluteInPlace: cannot specify both dil and finalvol"
                assert(False)
        return tgt   #  The name of the samples are unchanged -- the predilution names
        
    def runQPCRDIL(self,src,vol,srcdil,tgt=None,dilPlate=False,shaker=True):
        if tgt==None:
            tgt=[]
        [src,vol,srcdil]=listify([src,vol,srcdil])
        vol=[float(v) for v in vol]
        if len(tgt)==0:
            tgt=["%s.D%.0f"%(src[i],srcdil[i]) for i in range(len(src))]
        tgt=uniqueTargets(tgt)
        if dilPlate:
            stgt=findsamps(tgt,True,Experiment.DILPLATE,unique=True)
        else:
            stgt=findsamps(tgt,True,Experiment.SAMPLEPLATE,unique=True)
        ssrc=findsamps(src,False)

        ssdvol=[v/Reagents.SSD.conc.dilutionneeded() for v in vol]
        srcvol=[vol[i]/srcdil[i] for i in range(len(vol))]
        watervol=[vol[i]-ssdvol[i]-srcvol[i] for i in range(len(vol))]
#        print "srcdil=",srcdil,", ssdvol=",ssdvol,", srcvol=", srcvol, ", watervol=", watervol
        self.e.multitransfer(watervol,self.e.WATER,stgt,(False,False))
        self.e.multitransfer(ssdvol,Reagents.SSD,stgt,(False,False))
        
        for i in range(len(ssrc)):
            stgt[i].conc=None		# Assume dilutant does not have a concentration of its own
            # Check if we can align the tips here
            if i<len(ssrc)-3 and stgt[i].well+1==stgt[i+1].well and stgt[i].well+2==stgt[i+2].well and stgt[i].well+3==stgt[i+3].well and stgt[i].well%4==0 and self.e.cleanTips!=15:
                #print "Aligning tips"
                self.e.sanitize()
            self.e.transfer(srcvol[i],ssrc[i],stgt[i],(True,not shaker))
            if stgt[i].conc != None:
                stgt[i].conc.final=None	# Final conc are meaningless now
            
        if shaker:
            self.e.shake(stgt[0].plate)
        return tgt
        
    def runQPCR(self,src,vol,srcdil,primers=["A","B"],nreplicates=1):
        ## QPCR setup
        # e.g. trp.runQPCR(src=["1.RT-B","1.RT+B","1.RTNeg-B","1.RTNeg+B","2.RT-A","2.RT-B","2.RTNeg+B","2.RTNeg+B"],vol=10,srcdil=100)
        self.e.w.comment("runQPCR: primers=%s, source=%s"%([p for p in primers],[s for s in src]))
        [src,vol,srcdil,nreplicates]=listify([src,vol,srcdil,nreplicates])
        ssrc=findsamps(src,False)

        # Build a list of sets to be run
        all=[]
        for repl in range(max(nreplicates)):
            for p in primers:
                for i in range(len(ssrc)):
                    if nreplicates[i]<=repl:
                        continue
                    if repl==0:
                        sampname="%s.Q%s"%(src[i],p)
                    else:
                        sampname="%s.Q%s.%d"%(src[i],p,repl+1)
                    tgt=findsamps([sampname],True,Experiment.QPCRPLATE,unique=True)
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
        self.e.sanitize()		# In case we are aligned
        for a in all:
            s=a[0]
            t=a[1]
            p=a[2]
            v=a[3]/dil[p]
            t.conc=None		# Concentration of master mix is irrelevant now
            self.e.transfer(v,s,t,(False,False))
            
        return [a[1] for a in all]
