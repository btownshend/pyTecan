# Generic selection progam
import debughook
import math

from Experiment.concentration import Concentration
from Experiment.sample import Sample
from Experiment import worklist, reagents, decklayout, logging,clock
from TRPLib.TRP import TRP
from TRPLib.QSetup import QSetup
from pcrgain import pcrgain

        
class PGMSelect(TRP):
    '''Selection experiment'''
    
    def __init__(self,inputs,rounds,firstID,pmolesIn,directT7=True,templateDilution=0.3,tmplFinalConc=50,saveDil=24,qpcrWait=False,allLig=False,qpcrStages=["negative","template","ext","finalpcr"],finalPlus=True,t7dur=30,usertime=10,singlePrefix=False,noPCRCleave=False,saveRNA=False):
        # Initialize field values which will never change during multiple calls to pgm()
        self.inputs=inputs
        self.rounds=rounds   # String of U or C for each round to be run
        self.directT7=directT7
        self.tmplFinalConc=tmplFinalConc
        self.templateDilution=templateDilution
        self.pmolesIn=pmolesIn
        self.firstID=firstID
        self.saveDil=saveDil
        self.qpcrWait=qpcrWait
        self.allLig=allLig
        self.qpcrStages=qpcrStages
        self.finalPlus=finalPlus
        self.t7dur=t7dur
        self.usertime=usertime				# USER incubation time in minutes
        self.singlePrefix=singlePrefix
        self.noPCRCleave=noPCRCleave   # Skip PCR on cleave-selection rounds
        self.saveRNA=saveRNA
        
        # General parameters
        self.qConc = 0.050			# Target qPCR concentration in nM (corresponds to Ct ~ 10)
       # Expected concentration of RNA (actually back-computed from MX concentration after RT)
       # Limited to [stop]*4/0.9
        self.pcrSave=True		    # Save PCR products
        self.savedilplate=True	# Save PCR products on dilutions plate
        self.rtCarryForward=False			# True to save RT product from uncleaved round and run ligation during cleaved round
        self.rtSave=False			# True to save RT product for gel analysis
        self.rtSaveVol=11		   # Volume to take from RT (before dilution)
        self.rtSaveDil=2			    # Amount to dilute RT saved volume in TE8
        self.dopcr=True			    # Run PCR of samples
        self.cleavage=0.40			# Estimated cleavage (for computing dilutions of qPCRs)
        self.extpostdil=[2.0 if r=='C' else 1.0 for r in self.rounds]
        self.nopcrdil=4
        self.userMelt=False
        self.maxSampVolume=125
        self.pcrcopies=1				# Number of copies maintained in PCR stage (propagates back to RT stage)
        self.rtHI=False				   # Heat inactive/refold after RT
        self.rtDil=4
        self.saveRNADilution=10
        self.ligInPlace=True
        self.allprimers=["REF","MX","T7X","T7WX"]    # Will get updated after first pass with all primers used
        self.rtpostdil=[3.0 if r=='U' else 1.0 for r in self.rounds]
        self.rtdur=20
        self.ligdur=15
        self.pcrdil=[(80 if r=='U' else 40) for r in self.rounds]
        self.maxPCRVolume=100  # Maximum sample volume of each PCR reaction (thermocycler limit, and mixing limit)
        self.pcrcycles=[10 for r in self.rounds]
        self.rnaInput=False
        self.stopConc=1	   # Concentration of stop in uM
        self.savePCRAtEnd=False
        self.barcoding=False   # True to use unique barcode primers in cleaved rounds
        self.setVolumes()
        
    def setVolumes(self):
        # Computed parameters
        self.rnaConc=8314*self.tmplFinalConc/(self.tmplFinalConc+55)*self.t7dur/30
        maxConc=1000*self.stopConc*4/0.9
        if maxConc<self.rnaConc:
            logging.warning( "Stop@%.1f uM limits usable RNA to %.0f/%.0f nM"%(self.stopConc,maxConc,self.rnaConc))
            self.rnaConc=min(maxConc,self.rnaConc)
        stopConc=self.rnaConc*0.9
        rtConc=stopConc/self.rtDil
        rtdilConc=[rtConc/self.rtpostdil[i] for i in range(len(self.rounds))]
        ligConc=[rtdilConc[i]/1.25 for i in range(len(self.rounds))]
        ligdilConc=[ligConc[i]/self.extpostdil[i] for i in range(len(self.rounds))]
        pcrConc=[ligConc[i]/self.pcrdil[i] for i in range(len(self.rounds))]
        
        print "Concs(nM):  RNA: %.0f, Stop: %.0f, RT: %.0f, RTDil: %.0f, Lig: %.0f, LigDil: %.0f, PCRIn: %.0f"%(self.rnaConc, stopConc, rtConc, rtdilConc[0], ligConc[0], ligdilConc[0], pcrConc[0])
        self.pcrvol=[self.pcrcopies*self.pmolesIn*1000/pcrConc[i] for i in range(len(self.rounds))]
        # Use at least 100ul so the evaporation of the saved sample that occurs during the run will be relatively small
        self.pcrvol=[max(100,v) for v in self.pcrvol]
        pcrExtra=[1.4*math.ceil(v/self.maxPCRVolume) for v in self.pcrvol]
        self.minligvol=[self.pcrvol[i]/self.pcrdil[i]+(pcrExtra[i]+ (4.4 if self.saveDil is not None else 5.4 if 'ext' in self.qpcrStages else 0)+15.1)/self.extpostdil[i] for i in range(len(self.pcrvol))]
        print "minligvol=[%s]"%(",".join(["%.1f"%v for v in self.minligvol]))

        # Compute RT volume 
        self.rtvol=[ (self.minligvol[i]/1.25/self.rtpostdil[i]) if self.rounds[i]=='C' else (self.pcrvol[i]*1.0/self.pcrdil[i]+(pcrExtra[i]+15.1)/self.rtpostdil[i]) for i in range(len(self.rounds))]
        print  "self.rtvol=",self.rtvol,", rtSave=",self.rtSave
        if self.rtSave:
            self.rtvol=[max(15.0/self.rtpostdil[i],self.rtvol[i])+(self.rtSaveVol+1.4)/self.rtpostdil[i] for i in range(len(self.rtvol))]  # Extra for saves
        elif "rt" in self.qpcrStages:		# Take from save if rtSave is set
            self.rtvol=[max(15.0/self.rtpostdil[i],self.rtvol[i])+5.4/self.rtpostdil[i] for i in range(len(self.rtvol))]  # Extra for qPCR
        #print  "self.rtvol=",self.rtvol
        self.rtvol=[max(v,8.0) for v in self.rtvol]   # Minimum volume
        self.rtvol=[min(v,self.maxSampVolume) for v in self.rtvol]  # Maximum volume
        
        self.t7extravols=((4+1.4)*0.9 if 'stopped' in self.qpcrStages else 0)+ ((5+1.4)*0.9 if self.saveRNA else 0)
        #print "self.t7extravols=%.1f ul\n"%self.t7extravols
        self.t7vol=[max((15.1+self.rtvol[i]/4.0+1.4)*0.9+self.t7extravols,self.pmolesIn*1000/self.tmplFinalConc) for i in range(len(self.rounds))]
        self.t7vol=[max(18.0,v) for v in self.t7vol]   # Make sure that there's enough to add at least 2ul of stop
        self.t7vol=[min(self.maxSampVolume,v) for v in self.t7vol]   # Make sure no tubes overflow
        if 'template' in self.qpcrStages:
            self.t7vol[0]+=5.4
        
    def setup(self):
        TRP.setup(self)
        worklist.setOptimization(True)

    def pgm(self):
        q = QSetup(self,maxdil=16,debug=False,mindilvol=60)
        self.e.addIdleProgram(q.idler)

        if self.barcoding:
            # Setup barcode primers for cleaved rounds only
            self.bcprimers=[["BC-%s-R%d_T7"%(inp['ligand'],r+1) for inp in self.inputs] if self.rounds[r]=='C' else None for r in range(len(self.rounds))]
            for bcp in self.bcprimers:
                if bcp is not None:
                    for p in ["P-%s"%pp for pp in bcp]:
                        if not reagents.isReagent(p):
                            reagents.add(name=p,conc=4,extraVol=30,plate=decklayout.REAGENTPLATE,well="B2")
                        s=reagents.getsample(p)   # Force allocation of a well
                        print "Adding %s to reagents at well %s"%(p,s.plate.wellname(s.well))
            print "BC primers=", self.bcprimers
            
        # Add any missing fields to inputs
        for i in range(len(self.inputs)):
            if 'ligand' not in self.inputs[i]:
                self.inputs[i]['ligand']=None
            if 'round' not in self.inputs[i]:
                self.inputs[i]['round']=None
            if 'name' not in self.inputs[i]:
                if self.inputs[i]['ligand'] is None:
                    self.inputs[i]['name']='%s_%d_R%d'%(self.inputs[i]['prefix'],self.inputs[i]['ID'],self.inputs[i]['round'])
                else:
                    self.inputs[i]['name']='%s_%d_R%d_%s'%(self.inputs[i]['prefix'],self.inputs[i]['ID'],self.inputs[i]['round'],self.inputs[i]['ligand'])

        # Add templates
        if self.directT7:
            self.srcs = self.addTemplates([inp['name'] for inp in self.inputs],stockconc=self.tmplFinalConc/self.templateDilution,finalconc=self.tmplFinalConc,plate=decklayout.SAMPLEPLATE,looplengths=[inp['looplength'] for inp in self.inputs],initVol=self.t7vol[0]*self.templateDilution,extraVol=0)
        else:
            self.srcs = self.addTemplates([inp['name'] for inp in self.inputs],stockconc=self.tmplFinalConc/self.templateDilution,finalconc=self.tmplFinalConc,plate=decklayout.DILPLATE,looplengths=[inp['looplength'] for inp in self.inputs],extraVol=15) 

        t7in = [s.getsample()  for s in self.srcs]
        
        if "negative" in self.qpcrStages:
            q.addSamples(decklayout.SSDDIL,1,self.allprimers,save=False)   # Negative controls
        
        # Save RT product from first (uncleaved) round and then use it during 2nd (cleaved) round for ligation and qPCR measurements
        self.rndNum=0
        self.nextID=self.firstID
        curPrefix=[inp['prefix'] for inp in self.inputs]
        r1=t7in
        
        for roundType in self.rounds:
            # Run a single round of roundType "C" or "U" with r1 as input
            # Set r1 to new output at end

            # Computed output prefix
            prefixOut=["W" if self.singlePrefix else "A" if p=="W" else "B" if p=="A" else "W" if p=="B" else "BADPREFIX" for p in curPrefix]
            # May be explicitly overridden
            for i in range(len(self.inputs)):
                if 'stop' in self.inputs[i]:
                    if isinstance(self.inputs[i]['stop'],list):
                        assert(len(self.inputs[i]['stop'])==len(self.rounds))
                        prefixOut[i]=self.inputs[i]['stop'][self.rndNum]
                    else:
                        prefixOut[i]=self.inputs[i]['stop']
                if prefixOut[i] not in ['A','B','W','T7W']:
                    print 'Stop for %s must be one of A,B,W,T7W, but found %s'%(self.inputs[i]['name'],prefixOut[i])
                    assert False
            self.rndNum=self.rndNum+1
            
            if roundType=='U':
                r1=self.oneround(q,r1,prefixOut,prefixIn=curPrefix,keepCleaved=False,rtvol=self.rtvol[self.rndNum-1],t7vol=self.t7vol[self.rndNum-1],cycles=self.pcrcycles[self.rndNum-1],pcrdil=self.pcrdil[self.rndNum-1],pcrvol=self.pcrvol[self.rndNum-1],dolig=self.allLig)
            else:
                assert(roundType=='C')
                r1=self.oneround(q,r1,prefixOut,prefixIn=curPrefix,keepCleaved=True,rtvol=self.rtvol[self.rndNum-1],t7vol=self.t7vol[self.rndNum-1],cycles=self.pcrcycles[self.rndNum-1],pcrdil=self.pcrdil[self.rndNum-1],pcrvol=self.pcrvol[self.rndNum-1],dolig=True)

            for i in range(len(r1)):
                r1[i].name="%s_%d"%(prefixOut[i],self.nextID)
                if self.inputs[i]['round'] is not None:
                    r1[i].name="%s_R%d%c"%(r1[i].name,self.inputs[i]['round']+self.rndNum,roundType)
                if self.inputs[i]['ligand'] is not None:
                    r1[i].name="%s_%s"%(r1[i].name,self.inputs[i]['ligand'])
                print "Used ID ", self.nextID," for ", r1[i].name,": ",r1[i]
                self.nextID+=1
                r1[i].conc.final=r1[i].conc.stock*self.templateDilution
            curPrefix=prefixOut

        if "finalpcr" in self.qpcrStages:
            for i in range(len(r1)):
                if self.singlePrefix:
                    q.addSamples(src=r1[i],needDil=r1[i].conc.stock/self.qConc,primers=["T7X","MX"])
                else:
                    q.addSamples(src=r1[i],needDil=r1[i].conc.stock/self.qConc,primers=["T7X","T7"+prefixOut[i]+"X","MX"])
            
        print "######### qPCR ########### %.0f min"%(clock.elapsed()/60)
        self.allprimers=q.allprimers()
        q.run(confirm=self.qpcrWait)
        
    def oneround(self,q,input,prefixOut,prefixIn,keepCleaved,t7vol,rtvol,pcrdil,cycles,pcrvol,dolig):
        if self.singlePrefix:
            primerSet=[["MX","REF","T7X","T7"+prefixIn[i]+"X"] for i in range(len(prefixIn))]
        else:
            primerSet=[["T7"+prefixIn[i]+"X","T7"+prefixOut[i].replace("T7","")+"X","MX","T7X","REF"] for i in range(len(prefixIn))]
        
        if keepCleaved:
            print "Starting new cleavage round, will add prefix: ",prefixOut
            assert(dolig)
        else:
            print "Starting new uncleaved round, will retain prefix: ",prefixIn
        print "prefixOut=",prefixOut,", prefixIn=",prefixIn,",t7vol=",t7vol,",rtvol=",rtvol,",pcrdil=",pcrdil,",cycles=",cycles,",dolig=",dolig
        if self.rtCarryForward:
            assert(dolig)
            
        names=[i.name for i in input]
            
        if self.rnaInput:
            rxs=input
            stopDil=1
        else:
            print "######## T7 ########### %.0f min"%(clock.elapsed()/60)
            print "Inputs:  (t7vol=%.2f)"%t7vol
            inconc=[inp.conc.final for inp in input]
            for inp in input:
                if inp.conc.units=='nM':
                    print "    %s:  %.1ful@%.1f %s, use %.1f ul (%.3f pmoles)"%(inp.name,inp.volume,inp.conc.stock,inp.conc.units,t7vol/inp.conc.dilutionneeded(), t7vol*inp.conc.final/1000)
                    needDil = max([inp.conc.stock for inp in input])*1.0/self.qConc
                else:
                    print "    %s:  %.1ful@%.1f %s, use %.1f ul"%(inp.name,inp.volume,inp.conc.stock,inp.conc.units,t7vol/inp.conc.dilutionneeded())
                    needDil=100/self.qConc   # Assume 100nM
                # inp.conc.final=inp.conc.stock*self.templateDilution
            if self.directT7 and  self.rndNum==1:
                # Just add ligands and MT7 to each well
                if not keepCleaved:
                    for i in range(len(input)):
                        if self.inputs[i]['ligand'] is not None:
                            ligand=reagents.getsample(self.inputs[i]['ligand'])
                            self.e.transfer(t7vol/ligand.conc.dilutionneeded(),ligand,input[i],mix=(False,False))
                            names[i]+="+"
                mconc=reagents.getsample("MT7").conc.dilutionneeded()
                for i in range(len(input)):
                    watervol=t7vol*(1-1/mconc)-input[i].volume
                    if watervol>0.1:
                        self.e.transfer(watervol,decklayout.WATER,input[i],mix=(False,False))
                    self.e.transfer(t7vol/mconc,reagents.getsample("MT7"),input[i],mix=(False,False))
                    assert(abs(input[i].volume-t7vol)<0.1)
                rxs=input
            elif self.rndNum==len(self.rounds) and self.finalPlus and keepCleaved:
                rxs = self.runT7Setup(src=input,vol=t7vol,srcdil=[inp.conc.dilutionneeded() for inp in input])
                for i in range(len(input)):
                    inp=input[i]
                    if self.inputs[i]['ligand'] is not None:
                        rxs += self.runT7Setup(ligands=[reagents.getsample(self.inputs[i]['ligand'])],src=[inp],vol=t7vol,srcdil=[inp.conc.dilutionneeded()])
                        prefixIn+=[prefixIn[i]]
                        prefixOut+=[prefixOut[i]]
                        primerSet+=[primerSet[i]]
                        names+=["%s+"%names[i]]
            elif keepCleaved:
                rxs = self.runT7Setup(src=input,vol=t7vol,srcdil=[inp.conc.dilutionneeded() for inp in input])
            else:
                rxs = self.runT7Setup(ligands=[reagents.getsample(inp['ligand']) for inp in self.inputs],src=input,vol=t7vol,srcdil=[inp.conc.dilutionneeded() for inp in input])

            if self.rndNum==1 and "template" in self.qpcrStages:
                # Initial input 
                for i in range(len(rxs)):
                    q.addSamples(src=rxs[i],needDil=needDil,primers=primerSet[i],names=["%s.T"%names[i]])

            needDil = needDil*max([inp.conc.dilutionneeded() for inp in input])
            self.runT7Pgm(dur=self.t7dur,vol=t7vol)
            for i in range(len(rxs)):
                rxs[i].name="%s.t7"%names[i]

            print "Estimate usable RNA concentration in T7 reaction at %.0f nM"%self.rnaConc

            print "######## Stop ########### %.0f min"%(clock.elapsed()/60)
            self.e.lihahome()

            print "Have %.1f ul before stop"%rxs[0].volume
            preStopVolume=rxs[0].volume
            self.addEDTA(tgt=rxs,finalconc=2)	# Stop to 2mM EDTA final

            stopDil=rxs[0].volume/preStopVolume

            if self.saveRNA:
                self.saveSamps(src=rxs,vol=5,dil=self.saveRNADilution,plate=decklayout.DILPLATE,dilutant=reagents.getsample("TE8"),mix=(False,False))   # Save to check [RNA] on Qubit, bioanalyzer

        needDil = self.rnaConc/self.qConc/stopDil

        if "stopped" in self.qpcrStages:
            for i in range(len(rxs)):
                q.addSamples(src=rxs[i:i+1],needDil=needDil,primers=primerSet[i],names=["%s.stopped"%names[i]])
        
        print "######## RT  Setup ########### %.0f min"%(clock.elapsed()/60)
        hiTemp=95

        stop=["Unclvd-Stop" if (not dolig) else "T7W-Stop" if self.singlePrefix else "%s-Stop"%n for n in prefixOut]
        rt=self.runRT(src=rxs,vol=rtvol,srcdil=self.rtDil,heatInactivate=self.rtHI,hiTemp=hiTemp,dur=self.rtdur,incTemp=50,stop=[reagents.getsample(s) for s in stop],stopConc=self.stopConc)    # Heat inactivate also allows splint to fold
        
        rxs=rt
        for i in range(len(rxs)):
            if dolig and not self.singlePrefix:
                rxs[i].name=names[i]+"."+prefixOut[i]+".rt"
            else:
                rxs[i].name=names[i]+".rt"

        print "RT volume= [",",".join(["%.1f "%x.volume for x in rxs]),"]"
        
        needDil /=self.rtDil
        if self.rtpostdil[self.rndNum-1]>1:
            print "Dilution after RT: %.2f"%self.rtpostdil[self.rndNum-1]
            self.diluteInPlace(tgt=rxs,dil=self.rtpostdil[self.rndNum-1])
            needDil=needDil/self.rtpostdil[self.rndNum-1]

        if self.rtSave:
            rtsv=self.saveSamps(src=rxs,vol=self.rtSaveVol,dil=self.rtSaveDil,plate=decklayout.DILPLATE,dilutant=reagents.getsample("TE8"),mix=(False,False))   # Save to check RT product on gel (2x dil)

            if "rt" in self.qpcrStages:
                for i in range(len(rxs)):
                    q.addSamples(src=rtsv[i:i+1],needDil=needDil/2,primers=primerSet[i],names=["%s.rt"%names[i]])
        else:
            if "rt" in self.qpcrStages:
                for i in range(len(rxs)):
                    q.addSamples(src=rxs[i:i+1],needDil=needDil,primers=primerSet[i],names=["%s.rt"%names[i]])

        rtCarryForwardDil=10
        rtCarryForwardVol=3.5

        if self.rtCarryForward and not keepCleaved:
            # Also include RT from a prior round from here on
            for r in self.lastSaved:
                newsamp=Sample("%s.samp"%r.name,decklayout.SAMPLEPLATE)
                self.e.transfer(rxs[0].volume,r,newsamp,(False,False))
                rxs.append(newsamp)
            
        if dolig:
            print "######## Ligation setup  ########### %.0f min"%(clock.elapsed()/60)
            extdil=5.0/4
            reagents.getsample("MLigase").conc=Concentration(5)
            if self.ligInPlace:
                rxs=self.runLig(rxs,inPlace=True,srcdil=extdil,incTime=self.ligdur)
            else:
                rxs=self.runLig(rxs,inPlace=False,srcdil=extdil,vol=20,incTime=self.ligdur)

            print "Ligation volume= ",[x.volume for x in rxs]
            needDil=needDil/extdil
            if self.extpostdil[self.rndNum-1]>1:
                print "Dilution after extension: %.2f"%self.extpostdil[self.rndNum-1]
                self.diluteInPlace(tgt=rxs,dil=self.extpostdil[self.rndNum-1])
                needDil=needDil/self.extpostdil[self.rndNum-1]
                pcrdil=pcrdil*1.0/self.extpostdil[self.rndNum-1]
                
            if self.saveDil is not None:
                ext=self.saveSamps(src=rxs,vol=3,dil=self.saveDil,dilutant=reagents.getsample("TE8"),tgt=[Sample("%s.ext"%n,decklayout.DILPLATE) for n in names],mix=(False,True))   # Save cDNA product for subsequent NGS
                if "ext" in self.qpcrStages:
                    for i in range(len(ext)):
                        # Make sure we don't take more than 2 more steps
                        maxdil=q.MAXDIL*q.MAXDIL
                        if needDil/self.saveDil>maxdil:
                            logging.notice( "Diluting ext by %.0fx instead of needed %.0f to save steps"%(maxdil,needDil/self.saveDil))
                        q.addSamples(src=[ext[i]],needDil=min(maxdil,needDil/self.saveDil),primers=primerSet[i],names=["%s.ext"%names[i]],save=False)
            else:
                if "ext" in self.qpcrStages:
                    print "needDil=",needDil
                    for i in range(len(names)):
                        q.addSamples(src=[rxs[i]],needDil=needDil,primers=primerSet[i],names=["%s.ext"%names[i]])
                        isave=i+len(names)
                        if isave<len(rxs):
                            # samples restored
                            q.addSamples(src=[rxs[isave]],needDil=needDil/rtCarryForwardDil,primers=primerSet[isave])
        else:
            extdil=1
            self.extpostdil[self.rndNum-1]=1
            if self.rtpostdil[self.rndNum-1]>1:
                pcrdil=pcrdil*1.0/self.rtpostdil[self.rndNum-1]

        totalDil=stopDil*self.rtDil*self.rtpostdil[self.rndNum-1]*extdil*self.extpostdil[self.rndNum-1]
        fracRetained=rxs[0].volume/(t7vol*totalDil)
        print "Total dilution from T7 to Pre-pcr Product = %.2f*%.2f*%.2f*%.2f*%.2f = %.2f, fraction retained=%.0f%%"%(stopDil,self.rtDil,self.rtpostdil[self.rndNum-1],extdil,self.extpostdil[self.rndNum-1],totalDil,fracRetained*100)

        if self.rtCarryForward and not keepCleaved:
            # Remove the extra samples
            assert(len(self.lastSaved)>0)
            rxs=rxs[:len(rxs)-len(self.lastSaved)]
            self.lastSaved=[]

        if len(rxs)>len(input):
            # Have extra samples due when self.finalPlus is True
            rxs=rxs[0:len(input)]    # Only keep -target products
            prefixOut=prefixOut[0:len(input)]
            prefixIn=prefixIn[0:len(input)]
            
        if self.dopcr and not (keepCleaved and self.noPCRCleave):
            print "######### PCR ############# %.0f min"%(clock.elapsed()/60)
            maxvol=max([r.volume for r in rxs])
            print "PCR Volume: %.1f, Dilution: %.1f, volumes available for PCR: [%s]"%(pcrvol, pcrdil,",".join(["%.1f"%r.volume for r in rxs]))

            initConc=needDil*self.qConc/pcrdil
            if keepCleaved:
                initConc=initConc*self.cleavage		# Only use cleaved as input conc
            else:
                initConc=initConc*(1-self.cleavage)
                
            gain=pcrgain(initConc,400,cycles)
            finalConc=min(200,initConc*gain)
            print "Estimated starting concentration in PCR = %.1f nM, running %d cycles -> %.0f nM\n"%(needDil*self.qConc/pcrdil,cycles,finalConc)
            nsplit=int(math.ceil(pcrvol*1.0/self.maxPCRVolume))
            print "Split each PCR into %d reactions"%nsplit
            minsrcdil=1/(1-1.0/3-1.0/4)
            sampNeeded=pcrvol/pcrdil
            if self.rtCarryForward and keepCleaved:
                sampNeeded+=rtCarryForwardVol
            maxvol=max([r.volume for r in rxs]);
            minvol=min([r.volume for r in rxs]);
            if keepCleaved and self.rtCarryForward:
                assert(len(rxs)==len(rtCarryForward))
                print "Saving %.1f ul of each pre-PCR sample"%(rtCarryForwardVol )
                self.lastSaved=[Sample("%s.sv"%x.name,decklayout.DILPLATE) for x in rxs]
                for i in range(len(rxs)):
                    # Save with rtCarryForwardDil dilution to reduce amount of RT consumed (will have Ct's 2-3 lower than others)
                    self.e.transfer(rtCarryForwardVol,rxs[i],self.lastSaved[i],(False,False))
                    self.e.transfer(rtCarryForwardVol*(rtCarryForwardDil-1),decklayout.WATER,self.lastSaved[i],(False,True))  # Use pipette mixing -- shaker mixing will be too slow

            #print "NSplit=",nsplit,", PCR vol=",pcrvol/nsplit,", srcdil=",pcrdil,", input vol=",pcrvol/nsplit/pcrdil
            minvol=min([r.volume for r in rxs]);
            maxpcrvol=(minvol-15-1.4*nsplit)*pcrdil
            if maxpcrvol<pcrvol:
                print "Reducing PCR volume from %.1ful to %.1ful due to limited input"%(pcrvol, maxpcrvol)
                pcrvol=maxpcrvol

            if self.singlePrefix:
                if self.barcoding:
                    primers=self.bcprimers[self.rndNum-1]
                else:
                    primers=None
                if primers==None:
                    if keepCleaved:
                        master="MTaqC"
                    else:
                        master="MTaqU"
                else:
                    master="MTaqBar"
                pcr=self.runPCR(src=rxs*nsplit,vol=pcrvol/nsplit,srcdil=pcrdil,ncycles=cycles,primers=primers,usertime=self.usertime if keepCleaved else None,fastCycling=False,inPlace=False,master=master)
            else:
                pcr=self.runPCR(src=rxs*nsplit,vol=pcrvol/nsplit,srcdil=pcrdil,ncycles=cycles,primers=["T7%sX"%("" if self.singlePrefix and keepCleaved else x) for x in (prefixOut if keepCleaved else prefixIn)]*nsplit,usertime=self.usertime if keepCleaved else None,fastCycling=False,inPlace=False)
            if len(pcr)<=len(names):
                # Don't relabel if we've split
                for i in range(len(pcr)):
                    pcr[i].name=names[i]+".pcr"
                
            #print "Volume remaining in PCR input source: [",",".join(["%.1f"%r.volume for r in rxs]),"]"
            needDil=finalConc/self.qConc
            print "Projected final concentration = %.0f nM"%(needDil*self.qConc)
            for i in range(len(pcr)):
                pcr[i].conc=Concentration(stock=finalConc,final=None,units='nM')

            if self.pcrSave:
                # Save samples at 1x (move all contents -- can ignore warnings)
                maxSaveVol=(100 if self.savedilplate else 1500)*1.0/nsplit

                sv=self.saveSamps(src=pcr[:len(rxs)],vol=[min([maxSaveVol,x.volume]) for x in pcr[:len(rxs)]],dil=1,plate=(decklayout.DILPLATE if self.savedilplate else decklayout.EPPENDORFS),atEnd=self.savePCRAtEnd)
                if nsplit>1:
                    # Combine split
                    for i in range(len(rxs),len(rxs)*nsplit):
                        self.e.transfer(min([maxSaveVol,pcr[i].volume]),pcr[i],sv[i%len(sv)],mix=(False,i>=len(rxs)*(nsplit-1)))
                    # Correct concentration (above would've assumed it was diluted)
                    for i in range(len(sv)):
                        sv[i].conc=pcr[i].conc

                if "pcr" in self.qpcrStages:
                    for i in range(len(sv)):
                        q.addSamples(sv[i],needDil,primers=primerSet[i],names=["%s.pcr"%names[i]])

                processEff=0.5   # Estimate of overall efficiency of process
                print "Saved %.2f pmoles of product (%.0f ul @ %.1f nM)"%(sv[0].volume*sv[0].conc.stock/1000,sv[0].volume,sv[0].conc.stock)
                return sv
            else:
                return pcr[:len(rxs)]
        elif self.noPCRCleave:
            print "Dilution instead of PCR: %.2f"%self.nopcrdil
            # Need to add enough t7prefix to compensate for all of the Stop primer currently present, regardless of whether it is for cleaved or uncleaved
            # Will result in some short transcripts corresponding to the stop primers that are not used for cleaved product, producing just GGG_W_GTCTGC in the next round.  These would be reverse-trancribed, but may compete for T7 yield
            t7prefix=reagents.getsample("BT88")
            dil=self.extpostdil[self.rndNum-1]*userDil
            stopconc=1000.0/dil
            bt88conc=t7prefix.conc.stock
            relbt88=stopconc/bt88conc
            print "Using EXT with %.0fnM of stop oligo as input to next T7, need %.2ful of BT88@%.0fnM per ul of sample"%(stopconc,relbt88,bt88conc)
            for r in rxs:
                vol=r.volume*relbt88
                t7prefix.conc.final=t7prefix.conc.stock*vol/(r.volume+vol)
                r.conc.final=r.conc.stock*r.volume/(r.volume+vol)
                self.e.transfer(vol,t7prefix,r,mix=(False,False))

            if self.nopcrdil>(1+relbt88):
                self.diluteInPlace(tgt=rxs,dil=self.nopcrdil/(1.0+relbt88))
                needDil=needDil/self.nopcrdil
                print "Dilution of EXT product: %.2fx * %.2fx = %2.fx\n"%(1+relbt88,self.nopcrdil/(1+relbt88),self.nopcrdil)
            else:
                print "Dilution of EXT product: %.2fx\n"%(1+relbt88)

            return rxs
        else:
            return rxs


class PGMAnalytic(PGMSelect):
    "Analytic experiment"

    def __init__(self,inputs,saveRNA=False,tmplFinalConc=5,qpcrStages=["ext","negative"],templateDilution=0.6):
        super(PGMAnalytic, self).__init__(inputs=inputs,rounds='C',firstID=1,pmolesIn=0,saveRNA=saveRNA,qpcrStages=qpcrStages,templateDilution=templateDilution,tmplFinalConc=tmplFinalConc)
        self.dopcr=False
        self.saveRNADilution=2
        self.ligInPlace=True
        self.rtpostdil=[2]
        self.extpostdil=[2]
        self.saveDil=None
        self.setVolumes()
