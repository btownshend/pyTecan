from Experiment.sample import Sample
from Experiment.experiment import Experiment
from Experiment.experiment import Concentration
import os
import sys
import math

maxVolumePerWell=150

class Reagent:
    def __init__(self,name,plate=Experiment.REAGENTPLATE,well=None,conc=None,hasBeads=False,extraVol=50):
        self.sample=None
        self.name=name
        self.plate=plate
        self.preferredWell=well
        self.conc=conc
        self.hasBeads=hasBeads
        self.extraVol=extraVol

    def get(self):
        if self.sample==None:
            print "Creating sample ",self.name
            self.sample=Sample(self.name,self.plate,self.preferredWell,self.conc,hasBeads=self.hasBeads,extraVol=self.extraVol)
            wellname=self.sample.plate.wellname(self.sample.well)
            if self.preferredWell != None and self.preferredWell != wellname:
                print "WARNING: %s moved from preferred well %s to %s\n"%(self.name,self.preferredWell,wellname)
        return self.sample
    

class Reagents:
    def __getattr__(self,name):
        return self.get(name)

    def isReagent(self,name):
        return name in self.all
    
    def get(self,name):
        return self.all[name].get()
        
    def addReagent(self,name,plate=Experiment.REAGENTPLATE,well=None,conc=None,hasBeads=False,extraVol=50):
        self.all[name]=Reagent(name,plate,well,conc,hasBeads,extraVol)

    def __init__(self):
        self.all={}
        self.addReagent("MT7",well="A1",conc=2.5,extraVol=30)
        self.addReagent("MPosRT",well="B1",conc=2,extraVol=30)
        self.addReagent("MNegRT",well=None,conc=2)
        self.addReagent("MLigAT7",well="D1",conc=3)	# Conc is relative to annealing time (not to post-ligase)
        self.addReagent("MLigBT7W",well="E1",conc=3)
        self.addReagent("MLigase",well="A2",conc=3)

        self.addReagent("Theo",well=None,conc=Concentration(25,7.5,'mM'))
        self.addReagent("MStopXBio",well="B2",conc=2)
        self.addReagent("MStpX",well="C2",conc=2)
        self.addReagent("MQREF",well="D2",conc=10.0/6)
        self.addReagent("MQAX",well="E2",conc=10.0/6)
        self.addReagent("MQBX",well="A3",conc=10.0/6)
        self.addReagent("MPCRAX",well="B3",conc=4.0/3)
        self.addReagent("MPCRBX",well="C3",conc=4.0/3)
        self.addReagent("MQMX",well="D3",conc=10.0/6)
        self.addReagent("MQWX",well="E3",conc=10.0/6)
        self.addReagent("SSD",well="A4",conc=10.0)
        self.addReagent("MLigAT7W",well="B4",conc=3)
        self.addReagent("BeadBuffer",well="C4",conc=1)
        self.addReagent("Dynabeads",well="D4",conc=2,hasBeads=True)
        self.addReagent("MQT7X",well="E4",conc=15.0/9)
        self.addReagent("MStpBeads",well="A5",conc=3.7)
        self.addReagent("QPCRREF",well="B5",conc=Concentration(50,50,'pM'))
        self.addReagent("MLigBT7",well=None,conc=3)
        self.addReagent("MPCRT7X",well="C5",conc=4.0/3)
        self.addReagent("NaOH",well="D5",conc=1.0)
        self.addReagent("MLigBT7WBio",well="E5",conc=3)
        self.addReagent("MLigBT7Bio",well="A6",conc=3)
        self.addReagent("MPCR",well=None,conc=4)
        self.UNUSED=Sample("LeakyA1",Experiment.SAMPLEPLATE,"A1",0)
        self.UNUSED2=Sample("LeakyH12",Experiment.SAMPLEPLATE,"H12",0)
    
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
        si=Sample.lookup(tgts[i])
        if tgts[i] in tgts[:i] or (si!=None and si.volume!=0):
            for k in range(100):
                nm="%s.%d"%(tgts[i],k+2)
                si=Sample.lookup(nm)
                if nm not in tgts and (si==None or si.volume==0):
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

def diluteName(name,dilution):
    # Create a name for a dilution of another sample
    # Collapses any current dilution
    components = name.split('.')
    curdil=1
    replicate=1
#    if len(components[-1])==1:
#        replicate=int(components[-1])
#        components=components[:-1]
        
    if components[-1][0]=='D':
        olddilstr=components[-1][1:]
        curdil=float(olddilstr.replace("_","."))
        if curdil==0:
            curdil=1
        else:
            components=components[:-1]
    dilstr="%.2f"%(curdil*dilution)
    while dilstr[-1]=='0':
        dilstr=dilstr[:-1]
    if dilstr[-1]=='.':
        dilstr=dilstr[:-1]
    dilstr=dilstr.replace(".","_")
    result=".".join(components) + ".D"+dilstr
#    if replicate!=1:
#        result=result+"."+"%d"%replicate
#    print "%s diluted %.2f -> %s"%(name,dilution,result)
    return result

class TRP(object):
    r=Reagents()
    
    def __init__(self,totalTime=None):	# Estimate of total run time in seconds
        'Create a new TRP run'
        self.e=Experiment(totalTime)
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
            
        print "Wells used:  samples: %d, dilutions: %d, qPCR: %d\n"%(Sample.numSamplesOnPlate(self.e.SAMPLEPLATE),Sample.numSamplesOnPlate(self.e.DILPLATE),Sample.numSamplesOnPlate(self.e.QPCRPLATE))
        # Save worklist to a file
        #e.saveworklist("trp1.gwl")
        (scriptname,ext)=os.path.splitext(sys.argv[0])
        self.e.savegem(scriptname+".gem")
        self.e.savesummary(scriptname+".txt")
        Sample.savematlab(scriptname+".m")
        
    ########################
    # Save samples to another well
    ########################
    def saveSamps(self,src,vol,dil,tgt=None,dilutant=None,plate=None,mix=(True,True)):
        if tgt==None:
            tgt=[]
        [src,vol,dil]=listify([src,vol,dil])
        if len(tgt)==0:
            tgt=[diluteName(src[i],dil[i]) for i in range(len(src))]
        tgt=uniqueTargets(tgt)
        if plate==None:
            plate=self.e.REAGENTPLATE
            
        stgt=findsamps(tgt,True,plate,unique=True)
        ssrc=findsamps(src,False)

        if dilutant==None:
            dilutant=self.e.WATER
        self.e.multitransfer([vol[i]*(dil[i]-1) for i in range(len(vol))],dilutant,stgt,(False,False))
        for i in range(len(ssrc)):
            if not ssrc[i].isMixed:
                self.e.shake(ssrc[i].plate,returnPlate=True)
            self.e.transfer(vol[i],ssrc[i],stgt[i],mix)
            stgt[i].conc=Concentration(1.0/dil[i])
            
        return tgt
    
    def distribute(self,src,dil,vol,wells,tgt=None,dilutant=None,plate=Experiment.SAMPLEPLATE):
        
        if tgt==None:
            tgt=[]
        if len(tgt)==0:
            tgt=["%s.dist%d"%(src[0],j) for j in range(wells)]
        
        tgt=uniqueTargets(tgt)
        stgt=findsamps(tgt,unique=True)
        ssrc=findsamps(src,False)
        if dilutant==None:
            dilutant=self.e.WATER
        self.e.multitransfer([vol*(dil-1) for i in range(wells)],dilutant,stgt,(False,False))
        if not ssrc[0].isMixed:
            self.e.shake(ssrc[0].plate,returnPlate=True)
        self.e.multitransfer([vol for i in range(wells)],ssrc[0],stgt,(False,False))
        return tgt


    ########################
    # Dilute samples in place
    ########################
    def diluteInPlace(self,tgt,dil=None,finalvol=None):
        # Dilute in place
        # e.g.: trp.diluteInPlace(tgt=rt1,dil=2)
        [tgt,dil,finalvol]=listify([tgt,dil,finalvol])
        stgt=findsamps(tgt,False)
        dilutant=self.e.WATER
        for i in range(len(stgt)):
            if finalvol[i]!=None and dil[i]==None:
                self.e.transfer(finalvol[i]-stgt[i].volume,dilutant,stgt[i],mix=(False,False))
            elif finalvol[i]==None and dil[i]!=None:
                self.e.transfer(stgt[i].volume*(dil[i]-1),dilutant,stgt[i],mix=(False,False))
            else:
                print "diluteInPlace: cannot specify both dil and finalvol"
                assert(False)
        #print "after dilute, stgt[0]=",str(stgt[0]),",mixed=",stgt[0].isMixed
        return tgt   #  The name of the samples are unchanged -- the predilution names

    ########################
    # Run a reaction in place
    ########################
    def runRxInPlace(self,src,vol,master,returnPlate=True,finalx=1.0):
        'Run reaction on beads in given total volume'
        [vol,src,master]=listify([vol,src,master])
        ssrc=findsamps(src,False)
        smaster=[self.r.get(m) for m in master]
        mastervol=[vol[i]*finalx/smaster[i].conc.dilutionneeded() for i in range(len(vol))]
        watervol=[vol[i]-ssrc[i].volume-mastervol[i] for i in range(len(vol))]
        if any([w < -0.01 for w in watervol]):
            print "runRxInPlace: negative amount of water needed: ",w
            assert(False)
        for i in range(len(ssrc)):
            if  watervol[i]>0:
                self.e.transfer(watervol[i],self.e.WATER,ssrc[i],(False,False))
        for i in range(len(ssrc)):
            self.e.transfer(mastervol[i],smaster[i],ssrc[i],(False,ssrc[i].hasBeads))
        self.e.shake(ssrc[0].plate,returnPlate=returnPlate)

    ########################
    # T7 - Transcription
    ########################
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
        sourcevols=[vol*1.0/s for s in srcdil]
        if any(theo):
            theovols=[(vol*1.0/self.r.Theo.conc.dilutionneeded() if t else 0) for t in theo]
            watervols=[vol-theovols[i]-sourcevols[i]-MT7vol for i in range(len(ssrc))]
        else:
            watervols=[vol-sourcevols[i]-MT7vol for i in range(len(ssrc))]

        if sum(watervols)>0.01:
            self.e.multitransfer(watervols,self.e.WATER,stgt,(False,False))
        self.e.multitransfer([MT7vol for s in stgt],self.r.MT7,stgt,(False,False))
        if any(theo):
            self.e.multitransfer([tv for tv in theovols if tv>0.01],self.r.Theo,[stgt[i] for i in range(len(theovols)) if theovols[i]>0],(False,False),ignoreContents=True)
        for i in range(len(ssrc)):
            self.e.transfer(sourcevols[i],ssrc[i],stgt[i],(True,False))
        self.e.shake(stgt[0].plate,returnPlate=True)
        for t in stgt:
            t.ingredients['BIND']=1e-20*sum(t.ingredients.values())
        return tgt
    
    def runT7Pgm(self,vol,dur):
        if dur<100:
            pgm="TRP37-%d"%dur
        else:
            pgm="T37-%d"%dur
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
        sstopmaster=[self.r.get(s) for s in stopmaster]
        for i in range(len(stgt)):
            stopvol=stgt[i].volume/(sstopmaster[i].conc.dilutionneeded()-1)
            finalvol=stgt[i].volume+stopvol
            self.e.transfer(finalvol-stgt[i].volume,sstopmaster[i],stgt[i],(False,False))
            
        self.e.shake(stgt[0].plate,returnPlate=True)
        return tgt
    
    def runT7(self,theo,src,vol,srcdil,tgt=None,dur=15,stopmaster=None):
        if tgt==None:
            tgt=[]
        [theo,src,tgt,srcdil,stopmaster]=listify([theo,src,tgt,srcdil,stopmaster])
        tgt=self.runT7Setup(theo,src,vol,srcdil,tgt)
        self.runT7Pgm(vol,dur)
        tgt=self.runT7Stop(theo,tgt,stopmaster)
        return tgt

    ########################
    # Beads
    ########################
    def bindBeads(self,src,beads="Dynabeads",beadConc=None,buffer="BeadBuffer",incTime=60,addBuffer=False):
        [src,beads,buffer,beadConc]=listify([src,beads,buffer,beadConc])

        ssrc=findsamps(src,False)
        for s in ssrc:
            if s.plate!=self.e.SAMPLEPLATE:
                print "runBeadCleanup: src ",s," is not in sample plate."
                assert(0)
            s.conc=None		# Can't track concentration of beads
            
        self.e.moveplate(ssrc[0].plate,"Home")		# Make sure we do this off the magnet

        sbeads=[self.r.get(b) for b in beads]
        sbuffer=[self.r.get(b) for b in buffer]
        # Calculate volumes needed
        beadConc=[sbeads[i].conc.final if beadConc[i]==None else beadConc[i] for i in range(len(sbeads))]
        beadDil=sbeads[i].conc.stock/beadConc[i]
        if addBuffer:
            totalvol=[s.volume/(1-1.0/beadDil-1.0/sbuffer[i].conc.dilutionneeded()) for s in ssrc]
            buffervol=[totalvol[i]/sbuffer[i].conc.dilutionneeded() for i in range(len(ssrc))]
            # Add binding buffer to bring to 1x (beads will already be in 1x, so don't need to provide for them)
            for i in range(len(ssrc)):
                self.e.transfer(buffervol[i],sbuffer[i],ssrc[i],(False,False))
        else:
            buffervol=[0.0 for i in range(len(ssrc))]
            totalvol=[s.volume/(1-1.0/beadDil) for s in ssrc]

        beadvol=[t/beadDil for t in totalvol]

        # Transfer the beads
        for i in range(len(ssrc)):
            self.e.transfer(beadvol[i],sbeads[i],ssrc[i],(i==0,True))	# Mix beads before and after

        self.e.shake(ssrc[0].plate,dur=incTime,returnPlate=False)

    def sepWait(self,ssrc,sepTime=None):
        if sepTime==None:
            maxvol=max([s.volume for s in ssrc])
            if maxvol > 50:
                sepTime=50
            else:
                sepTime=30
        self.e.pause(sepTime)	# Wait for separation
        
    def beadWash(self,src,washTgt=None,sepTime=None,residualVolume=10,keepWash=False,numWashes=2,wash="Water",washVol=50,keepFinal=False,finalTgt=None,keepVol=4.2,keepDil=5):
        # Perform washes
        # If keepWash is true, retain all washes (combined)
        # If keepFinal is true, take a sample of the final wash (diluted by keepDil)
        [src,wash]=listify([src,wash])
        ssrc=findsamps(src,False)
        # Do all washes while on magnet
        assert(len(set([s.plate for s in ssrc]))==1)	# All on same plate
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
            self.e.moveplate(ssrc[0].plate,"Magnet")	# Move to magnet
            self.sepWait(ssrc,sepTime)

            # Remove the supernatant
            for i in range(len(ssrc)):
                if ssrc[i].volume > residualVolume:
                    if keepWash:
                        self.e.transfer(ssrc[i].volume-residualVolume,ssrc[i],sWashTgt[i])	# Keep supernatants
                        sWashTgt[i].conc=None	# Allow it to be reused
                    else:
                        self.e.dispose(ssrc[i].volume-residualVolume,ssrc[i])	# Discard supernatant
                
        # Wash
        swash=[]
        for w in wash:
            if self.r.isReagent(w):
                swash.append(self.r.get(w))
            else:
                swash=swash+findsamps([w],False)

        for washnum in range(numWashes):
            self.e.moveplate(ssrc[0].plate,"Home")
            if keepFinal and washnum==numWashes-1:
                'Retain sample of final'
                for i in range(len(ssrc)):
                    ssrc[i].conc=None
                    self.e.transfer(washVol-ssrc[i].volume,swash[i],ssrc[i],mix=(False,True))	# Add wash
                self.e.shake(ssrc[0].plate,returnPlate=True)
                self.saveSamps(src=src,tgt=finalTgt,vol=keepVol,dil=keepDil,plate=Experiment.DILPLATE)
            else:
                for i in range(len(ssrc)):
                    ssrc[i].conc=None
                    self.e.transfer(washVol-ssrc[i].volume,swash[i],ssrc[i],mix=(False,False))	# Add wash, no need to pipette mix since some heterogenity won't hurt here
                self.e.shake(ssrc[0].plate,returnPlate=False)

            self.e.moveplate(ssrc[0].plate,"Magnet")	# Move to magnet
                
            self.sepWait(ssrc,sepTime)
                
            for i in range(len(ssrc)):
                if keepWash:
                    self.e.transfer(ssrc[i].volume-residualVolume,ssrc[i],sWashTgt[i])	# Remove wash
                    sWashTgt[i].conc=None	# Allow it to be reused
                else:
                    self.e.dispose(ssrc[i].volume-residualVolume,ssrc[i])	# Remove wash

        self.e.moveplate(ssrc[0].plate,"Home")

        # Should only be residualVolume left with beads now
        result=[]
        if keepWash:
            result=result+washTgt
        if keepFinal:
            result=result+finalTgt

        return result

    def beadAddElutant(self,src,elutant="Water",elutionVol=30,eluteTime=60,returnPlate=True,temp=None):
        [src,elutionVol,elutant]=listify([src,elutionVol,elutant])
        ssrc=findsamps(src,False)
        selutant=findsamps(elutant,False)
        for i in range(len(ssrc)):
            if elutionVol[i]<30:
                print "Warning: elution from beads with %.1f ul < minimum of 30ul"%elutionVol[i]
                print "  src=",ssrc[i]
            self.e.transfer(elutionVol[i]-ssrc[i].volume,selutant[i],ssrc[i],(False,True))	
        if temp==None:
            self.e.shake(ssrc[0].plate,dur=eluteTime,returnPlate=returnPlate)
        else:
            self.e.shake(ssrc[0].plate,dur=30,returnPlate=False)
            self.e.w.pyrun('PTC\\ptcsetpgm.py elute TEMP@%d,%d TEMP@25,2'%(temp,eluteTime))
            self.e.runpgm("elute",eluteTime/60,False,elutionVol[0])
            if returnPlate:
                self.e.moveplate(ssrc[0].plate,"Home")

    def beadSupernatant(self,src,tgt=None,sepTime=None,residualVolume=10,plate=None,reuseDest=False):
        if tgt==None:
            tgt=[]

        [src,tgt]=listify([src,tgt])
        if len(tgt)==0:
            for i in range(len(src)):
                tgt.append("%s.SN"%src[i])
        ssrc=findsamps(src,False)
        if plate==None:
            plate=self.e.SAMPLEPLATE
        stgt=findsamps(tgt,plate=plate,unique=not reuseDest)

        if not ssrc[0].isMixed:
            self.e.shake(ssrc[0].plate,returnPlate=False)

        self.e.moveplate(ssrc[0].plate,"Magnet")	# Move to magnet
        self.sepWait(ssrc,sepTime)

        for i in range(len(ssrc)):
            self.e.transfer(ssrc[i].volume-residualVolume,ssrc[i],stgt[i])	# Transfer elution to new tube

        self.e.moveplate(ssrc[0].plate,"Home")
        return tgt

    def beadCombine(self,src,residualVolume=10,suspendVolume=150,sepTime=None):
        'Combine everything in the src wells into a the first well; assumes that there are enough beads in that well for all the combination'
        ssrc=findsamps(src)
        stgt=ssrc[0]
        for s in ssrc[1:]:
            # Combine s with tgt
            if stgt.volume>residualVolume:
                self.e.moveplate(stgt.plate,"Magnet")	# Move to magnet
                self.sepWait([stgt],sepTime)
                self.e.dispose(stgt.volume-residualVolume,stgt)
            self.e.moveplate(stgt.plate,"Home")	
            if s.volume<suspendVolume:
                self.e.transfer(suspendVolume-s.volume,self.e.WATER,s,(False,False))
            vol=s.volume-residualVolume-1
            s.conc=None
            self.e.transfer(vol,s,stgt,mix=(True,True))

        self.e.moveplate(stgt.plate,"Home")	
        return src[0:1]
    
    ########################
    # RT - Reverse Transcription
    ########################
    def runRT(self,pos,src,vol,srcdil,tgt=None,dur=20,heatInactivate=False):
        result=self.runRTSetup(pos,src,vol,srcdil,tgt)
        self.runRTPgm(dur,heatInactivate=heatInactivate)
        return result
    
    def runRTOnBeads(self,src,vol,dur=20):
        'Run RT on beads in given volume'
        ssrc=findsamps(src,False)

        # Adjust source dilution
        for i in range(len(ssrc)):
            ssrc[i].conc=None

        self.runRxInPlace(src,vol,"MPosRT",returnPlate=False)
        self.runRTPgm(dur)
        
    def runRTSetup(self,pos,src,vol,srcdil,tgt=None,rtmaster=None):
        assert(pos)	# Negative handling disabled
        if rtmaster==None:
            rtmaster=self.r.MPosRT
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
        if any(p for p in pos):
            self.e.stage('RTPos',[rtmaster],[ssrc[i] for i in range(len(ssrc)) if pos[i]],[stgt[i] for i in range(len(stgt)) if pos[i]],[vol[i] for i in range(len(vol)) if pos[i]],destMix=False)
        #    e.stage('MNegRT',[self.r.MOSBuffer],[],[self.r.MNegRT],ASPIRATEFACTOR*(self.vol.RT*negRT)/2+self.vol.Extra+MULTIEXCESS,2)
        #if any(not p for p in pos):
                #self.e.stage('RTNeg',[self.r.MNegRT],[ssrc[i] for i in range(len(ssrc)) if not pos[i]],[stgt[i] for i in range(len(stgt)) if not pos[i]],[vol[i] for i in range(len(vol)) if not pos[i]],destMix=False)
        self.e.shake(stgt[0].plate,returnPlate=True)
        return tgt

    def runRTPgm(self,dur=20,heatInactivate=False):
        if heatInactivate:
            hidur=15
            pgm="RT-%d"%dur
            self.e.w.pyrun('PTC\\ptcsetpgm.py %s TEMP@37,%d TEMP@95,%d TEMP@25,2'%(pgm,dur*60,hidur*60))
            self.e.runpgm(pgm,dur+hidur,False,100)		# Volume doesn't matter since it's just an incubation, use 100ul
        else:
            if dur<100:
                pgm="TRP37-%d"%dur
            else:
                pgm="T37-%d"%dur
            self.e.w.pyrun('PTC\\ptcsetpgm.py %s TEMP@37,%d TEMP@25,2'%(pgm,dur*60))
            self.e.runpgm(pgm,dur,False,100)		# Volume doesn't matter since it's just an incubation, use 100ul
 
    ########################
    # Lig - Ligation
    ########################
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
        smaster=[self.r.get(m) for m in master]

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
            self.e.stage('LigAnneal',[smaster[i]],ssrc[i:lasti],stgt[i:lasti],[vol[j]/1.5 for j in range(i,lasti)],1.5,destMix=False)
            i=lasti
            
        if anneal:
            self.e.shake(stgt[0].plate,returnPlate=False)
            self.e.runpgm("TRPANN",5,False,max(vol),hotlidmode="CONSTANT",hotlidtemp=100)
        self.e.stage('Ligation',[self.r.MLigase],[],stgt,vol,destMix=False)
        self.e.shake(stgt[0].plate,returnPlate=False)
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

        # Adjust source dilution
        for i in range(len(ssrc)):
            ssrc[i].conc=None

        self.runRxInPlace(src,annealvol,ligmaster,returnPlate=not anneal,finalx=1.5)
        if anneal:
            self.e.runpgm("TRPANN",5,False,max([s.volume for s in ssrc]),hotlidmode="CONSTANT",hotlidtemp=100)

        ## Add ligase
        self.runRxInPlace(src,vol,"MLigase",returnPlate=False)
        self.runLigPgm(max(vol),ligtemp,inactivate=False)	# Do not heat inactivate since it may denature the beads

    ########################
    # PCR
    ########################
    def runPCR(self,prefix,src,vol,srcdil,tgt=None,ncycles=20,suffix='S'):
        if tgt==None:
            tgt=[]
        ## PCR
        # e.g. trp.runPCR(prefix=["A"],src=["1.RT+"],tgt=["1.PCR"],vol=[50],srcdil=[5])
        [prefix,src,tgt,vol,srcdil,suffix]=listify([prefix,src,tgt,vol,srcdil,suffix])
        if len(tgt)==0:
            tgt=["%s.P%s%s"%(src[i],prefix[i],suffix[i]) for i in range(len(src))]

        tgt=uniqueTargets(tgt)
        stgt=findsamps(tgt,unique=True)
        #print "stgt[0]=",str(stgt[0])
        ssrc=findsamps(src,False)
        
        # Adjust source dilution
        for i in range(len(ssrc)):
            ssrc[i].conc=Concentration(srcdil[i],1)

        primer=[prefix[i]+suffix[i] for i in range(len(prefix))]
        #print "primer=",primer
        if any(p=='AS' for p in primer):
               self.e.stage('PCRAS',[self.r.PCRAS],[ssrc[i] for i in range(len(ssrc)) if primer[i]=='AS'],[stgt[i] for i in range(len(stgt)) if primer[i]=='AS'],[vol[i] for i in range(len(vol)) if primer[i]=='AS'],destMix=False)
        if any(p=='BS' for p in primer):
               self.e.stage('PCRBS',[self.r.PCRBS],[ssrc[i] for i in range(len(ssrc)) if primer[i]=='BS'],[stgt[i] for i in range(len(stgt)) if primer[i]=='BS'],[vol[i] for i in range(len(vol)) if primer[i]=='BS'],destMix=False)
        if any(p=='AX' for p in primer):
               self.e.stage('PCRAX',[self.r.PCRAX],[ssrc[i] for i in range(len(ssrc)) if primer[i]=='AX'],[stgt[i] for i in range(len(stgt)) if primer[i]=='AX'],[vol[i] for i in range(len(vol)) if primer[i]=='AX'],destMix=False)
        if any(p=='BX' for p in primer):
               self.e.stage('PCRBX',[self.r.PCRBX],[ssrc[i] for i in range(len(ssrc)) if primer[i]=='BX'],[stgt[i] for i in range(len(stgt)) if primer[i]=='BX'],[vol[i] for i in range(len(vol)) if primer[i]=='BX'],destMix=False)
        if any(p=='T7X' for p in primer):
               self.e.stage('PCRT7X',[self.r.PCRT7X],[ssrc[i] for i in range(len(ssrc)) if primer[i]=='T7X'],[stgt[i] for i in range(len(stgt)) if primer[i]=='T7X'],[vol[i] for i in range(len(vol)) if primer[i]=='T7X'],destMix=False)
        pgm="PCR%d"%ncycles
        self.e.shake(stgt[0].plate,returnPlate=False)
        #        self.e.w.pyrun('PTC\\ptcsetpgm.py %s TEMP@95,120 TEMP@95,30 TEMP@55,30 TEMP@72,25 GOTO@2,%d TEMP@72,180 TEMP@16,2'%(pgm,ncycles-1))
        self.e.w.pyrun('PTC\\ptcsetpgm.py %s TEMP@95,120 TEMP@95,10 TEMP@57,10 GOTO@2,%d TEMP@72,120 TEMP@25,2'%(pgm,ncycles-1))
        self.e.runpgm(pgm,4.80+1.55*ncycles,False,max(vol),hotlidmode="CONSTANT",hotlidtemp=100)
        return tgt

    def runPCROnBeads(self,prefix,src,vol,ncycles,suffix,annealtemp=57,save=None):
        [prefix,src,vol,suffix]=listify([prefix,src,vol,suffix])

        primer=["MPCR"+prefix[i]+suffix[i] for i in range(len(prefix))]
        self.runRxInPlace(src,vol,primer,returnPlate=(save!=None))
        if save!=None:
            self.saveSamps(src=src,vol=5,dil=10,tgt=save,plate=self.e.DILPLATE,mix=(False,False),dilutant=self.e.SSDDIL)

        pgm="PCR%d"%ncycles
        #        self.e.w.pyrun('PTC\\ptcsetpgm.py %s TEMP@95,120 TEMP@95,30 TEMP@55,30 TEMP@72,25 GOTO@2,%d TEMP@72,180 TEMP@16,2'%(pgm,ncycles-1))
        self.e.w.pyrun('PTC\\ptcsetpgm.py %s TEMP@95,120 TEMP@95,10 TEMP@%f,10 GOTO@2,%d TEMP@72,120 TEMP@25,2'%(pgm,annealtemp,ncycles-1))
        self.e.runpgm(pgm,4.80+1.55*ncycles,False,max(vol),hotlidmode="CONSTANT",hotlidtemp=100)
    
    ########################
    # qPCR
    ########################
    def runQPCRDIL(self,src,vol,srcdil,tgt=None,dilPlate=False,pipMix=False,dilutant=Experiment.SSDDIL):
        if tgt==None:
            tgt=[]
        [src,vol,srcdil]=listify([src,vol,srcdil])
        vol=[float(v) for v in vol]
        if len(tgt)==0:
            tgt=[diluteName(src[i],srcdil[i]) for i in range(len(src))]
        tgt=uniqueTargets(tgt)
        if dilPlate:
            stgt=findsamps(tgt,True,Experiment.DILPLATE,unique=True)
        else:
            stgt=findsamps(tgt,True,Experiment.SAMPLEPLATE,unique=True)
        ssrc=findsamps(src,False)

        srcvol=[vol[i]/srcdil[i] for i in range(len(vol))]
        watervol=[vol[i]-srcvol[i] for i in range(len(vol))]
        if len(watervol) > 4 and sum(watervol)>800:
            print "Could optimize distribution of ",len(watervol)," moves of ",dilutant.name,": vol=[", ["%.1f"%w for w in watervol],"]"
        self.e.multitransfer(watervol,dilutant,stgt,(False,False))
        
        for i in range(len(ssrc)):
            stgt[i].conc=None		# Assume dilutant does not have a concentration of its own
            if not ssrc[i].isMixed and ssrc[i].plate.name!="Eppendorfs":
                self.e.shake(ssrc[i].plate,returnPlate=True)
            # Check if we can align the tips here
            if i<len(ssrc)-3 and stgt[i].well+1==stgt[i+1].well and stgt[i].well+2==stgt[i+2].well and stgt[i].well+3==stgt[i+3].well and stgt[i].well%4==0 and self.e.cleanTips!=15:
                #print "Aligning tips"
                self.e.sanitize()
            self.e.transfer(srcvol[i],ssrc[i],stgt[i],(not ssrc[i].isMixed,pipMix))
            if stgt[i].conc != None:
                stgt[i].conc.final=None	# Final conc are meaningless now
            
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
            mname="MQ%s"%p
            if not self.r.isReagent(mname):
                self.r.addReagent(name=mname,conc=15.0/9.0,extraVol=30)
            mq=self.r.get(mname)
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
            if not s.isMixed:
                self.e.shake(s.plate,returnPlate=True)
            self.e.transfer(v,s,t,(False,False))
            
        return [a[1] for a in all]
