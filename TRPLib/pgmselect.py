# Generic selection progam
from __future__ import print_function

import math

from Experiment import worklist, reagents, decklayout, logging, clock, thermocycler
from Experiment.concentration import Concentration
from Experiment.sample import Sample
from TRPLib.QSetup import QSetup
from TRPLib.TRP import TRP
from .pcrgain import pcrgain
from Experiment.db import db

reagents.add("BT5310",well="B5",conc=Concentration(20,20,"pM"))


# noinspection PyAttributeOutsideInit
class PGMSelect(TRP):
    """Selection experiment"""
    
    def __init__(self, inputs, rounds=None, firstID=None, pmolesIn=None, rnddef=None, directT7=True, templateDilution=0.3, tmplFinalConc=50,
                 saveDil=24, qpcrWait=False, allLig=False, qpcrStages=None, finalPlus=True, t7dur=30, usertime=10,
                 singlePrefix=False, noPCRCleave=False, saveRNA=False, useMX=True, refillable=False,enrich=1.4):
        # Initialize field values which will never change during multiple calls to pgm()
        # Can use rounds="UZUWUZ" (e.g.) OR rnddef which is a list of specs for each round with rtype (U,W,Z), tref
        super(PGMSelect, self).__init__()
        if refillable:
            reagents.lookup("MT7").refillable=True
            reagents.lookup("MPosRT").refillable=True
            reagents.lookup("MTaqU").refillable=True
            
            reagents.lookup("MTaqC").refillable=True
            reagents.lookup("MTaqBar").refillable=True
            reagents.lookup("MLigase").refillable=True
            reagents.lookup("P-T7ZX").refillable=True
            reagents.lookup("P-T7WX").refillable=True
            reagents.lookup("TE8").refillable=True
            reagents.lookup("Unclvd-Stop").refillable=True
            reagents.lookup("W-Stop").refillable=True
            reagents.lookup("Z-Stop").refillable=True
            reagents.lookup("8600").refillable=True
            reagents.lookup("DMSO").refillable=True
        if qpcrStages is None:
            qpcrStages = ["negative", "template", "ext", "finalpcr"]
        self.inputs=inputs
        if rnddef is not None:
            assert rounds is None
            self.rounds=[r['rtype'] for r in rnddef]   # String of U or C for each round to be run
            self.rnddef=rnddef
        else:
           # Old interface, uses rounds instead of rnddef
            assert rounds is not None
            self.rounds=rounds
            self.rnddef=[{'rtype':r} for r in rounds]

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
        self.extraQPCRPrimers=None
        self.useMX=useMX
        self.pauseAfterStop=False
        self.roundCallback=None   # Callback at the beginning of each round;  called as callback(self,rndNum,roundType)
        
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
        self.maxSampVolume=125.0
        self.pcrcopies=1				# Number of copies maintained in PCR stage (propagates back to RT stage)
        self.rtHI=False				   # Heat inactive/refold after RT
        self.rtDil=4
        self.edtastop=False
        self.saveRNADilution=10
        self.saveRNAVolume=5
        self.ligInPlace=True
        self.allprimers=["REF","T7X","WX"]    # Will get updated after first pass with all primers used
        if self.useMX:
            self.allprimers.append("MX")
        self.rtpostdil=[3.0 if r=='U' else 1.0 for r in self.rounds]
        self.rtdur=20
        self.ligdur=15
        self.maxdilstep=16   # Maximum dilute per qPCR dilution step
        self.pcrdil=[(80 if r=='U' else 40) for r in self.rounds]
        self.maxPCRVolume=100  # Maximum sample volume of each PCR reaction (thermocycler limit, and mixing limit)
        self.pcrcycles=[10 for _ in self.rounds]
        self.rnaInput=False
        self.stopConc=1	   # Concentration of stop in uM
        self.barcoding=False   # True to use do a barcoding PCR
        self.enrich=enrich   # Estimate of enrichment/round -- scales number of pmoles needed to carry
        self.lowhi=True
        self.regenPCRCycles=None
        self.regenPCRVolume=100
        self.regenPCRDilution=10
        self.setVolumes()
        #self.savePlate=decklayout.DILPLATE
        self.savePlate=decklayout.PRODUCTPLATE
        
    def setVolumes(self):
        # Computed parameters
        # Observed data:   0.1nM@30min -> gain ~1000
        self.rnaConc=8314.0*self.tmplFinalConc/(self.tmplFinalConc+55)*self.t7dur/30
        if self.tmplFinalConc<1:
            self.rnaConc*=6   # Kludge based on being off at 0.1nM template concentrations
        self.rnaConc=max(40.0,self.rnaConc)   # Another kludge
        if isinstance(self.stopConc,list):
            minStopConc=min(self.stopConc)
        else:
            minStopConc=self.stopConc
        maxConc=1000*minStopConc*4/0.9
        if maxConc<self.rnaConc:
            logging.warning( "Stop@%.1f uM limits usable RNA to %.0f/%.0f nM"%(minStopConc,maxConc,self.rnaConc))
            self.rnaConc=min(maxConc,self.rnaConc)
        stopConc=self.rnaConc*0.9
        rtConc=stopConc/self.rtDil
        rtdilConc=[rtConc/self.rtpostdil[i] for i in range(len(self.rounds))]
        ligConc=[None if self.rounds[i]=='U' else rtdilConc[i]/1.25 for i in range(len(self.rounds))]
        ligdilConc=[None if self.rounds[i]=='U' else ligConc[i]/self.extpostdil[i] for i in range(len(self.rounds))]
        pcrConc=[rtConc/self.pcrdil[i] if self.rounds[i]=='U' else ligConc[i]/self.pcrdil[i] for i in range(len(self.rounds))]
        
        for i in range(len(self.rounds)):
            if ligConc[i] is None:
                print("R%d Concs(nM):  RNA: %.0f, Stop: %.0f, RT: %.0f, RTDil: %.0f, PCRIn: %.0f"%(i, self.rnaConc, stopConc, rtConc, rtdilConc[i], pcrConc[i]))
            else:
                print("R%d Concs(nM):  RNA: %.0f, Stop: %.0f, RT: %.0f, RTDil: %.0f, Lig: %.0f, LigDil: %.0f, PCRIn: %.0f"%(i, self.rnaConc, stopConc, rtConc, rtdilConc[i], ligConc[i], ligdilConc[i], pcrConc[i]))

        self.pcrvol=[self.pcrcopies*self.pmolesIn*1000/pcrConc[i]/math.pow(self.enrich,(i+1.0)) for i in range(len(self.rounds))]
        self.pcrvol=[max(16,p) for p in self.pcrvol]   # Minimum practical volume assuming components at 2x,4x
        if len(self.rounds)>1:
            # Use at least 100ul so the evaporation of the saved sample that occurs during the run will be relatively small
            self.pcrvol=[max(100,v) for v in self.pcrvol]
        print("pcrvol=[%s]"%(",".join(["%.1f"%v for v in self.pcrvol])))
        pcrExtra=[1.4*math.ceil(v*1.0/self.maxPCRVolume) for v in self.pcrvol]
        print("pcrExtra=[%s]"%(",".join(["%.1f"%v for v in pcrExtra])))
        self.minligvol=[(self.pcrvol[i]*1.0+pcrExtra[i])/self.pcrdil[i]+((4.4 if self.saveDil is not None else 5.4 if 'ext' in self.qpcrStages else 0)+15.1)/self.extpostdil[i] for i in range(len(self.pcrvol))]
        print("minligvol=[%s]"%(",".join(["%.1f"%v for v in self.minligvol])))

        # Compute RT volume 
        self.rtvol=[ ((self.minligvol[i]/1.25+3.3)/self.rtpostdil[i]) if self.rounds[i]!='U' else (self.pcrvol[i]*1.0/self.pcrdil[i]+(pcrExtra[i]+15.1+3.3)/self.rtpostdil[i]) for i in range(len(self.rounds))]
        print("self.rtvol=",self.rtvol,", rtSave=",self.rtSave)
        if self.rtSave:
            self.rtvol=[max(15.0/self.rtpostdil[i],self.rtvol[i])+(self.rtSaveVol+1.4)/self.rtpostdil[i] for i in range(len(self.rtvol))]  # Extra for saves
        elif "rt" in self.qpcrStages:		# Take from save if rtSave is set
            self.rtvol=[max(15.0/self.rtpostdil[i],self.rtvol[i])+5.4/self.rtpostdil[i] for i in range(len(self.rtvol))]  # Extra for qPCR
        self.rtvol=[max(v,8.0) for v in self.rtvol]   # Minimum volume
        self.rtvol=[min(v,self.maxSampVolume) for v in self.rtvol]  # Maximum volume
        # print ("self.rtvol=",self.rtvol)
        
        self.t7extravols=((4+1.4) if 'stopped' in self.qpcrStages else 0)+ ((self.saveRNAVolume+1.4) if self.saveRNA else 0) # + 3.3  # 3.3 in case pipette mixing used
        #print "self.t7extravols=%.1f ul\n"%self.t7extravols
        #print "self.rtvol=%s ul\n"%(",".join(["%.1f "%x for x in self.rtvol]))

        # Compute dilutions due to tref additions
        trefdil=[1 for _ in self.rnddef ]
        for i in range(len(self.rnddef)-1):
            rd=self.rnddef[i]
            if 'tref' in rd:
                tref = rd['tref'][0]
                if tref is not None:
                    trefname = 'TRef%d' % tref
                    if not reagents.isReagent(trefname):
                        reagents.add(name=trefname, conc=10, extraVol=30, well="E4")
                    trefs = reagents.getsample(trefname)
                    trefdil[i+1]=(trefs.conc.dilutionneeded())/(trefs.conc.dilutionneeded()-1)
        print("Extra dilution due to tref additions: ",trefdil)
        self.t7vol=[max((15.1+self.rtvol[i]/4.0+1.4)+self.t7extravols,self.pmolesIn*1000.0/(self.tmplFinalConc if i==0 else 200*self.templateDilution)*trefdil[i]/math.pow(self.enrich,i*1.0)) for i in range(len(self.rounds))]
        print("self.t7vol=%s ul\n"%(",".join(["%.1f "%x for x in self.t7vol])))
        #self.t7vol=[max(18.0,v) for v in self.t7vol]   # Make sure that there's enough to add at least 2ul of stop
        if 'template' in self.qpcrStages:
            self.t7vol[0]+=5.4
        self.t7vol=[min(self.maxSampVolume,v) for v in self.t7vol]   # Make sure no tubes overflow
        
    def setup(self):
        TRP.setup(self)
        worklist.setOptimization(True)

    def pgm(self):
        q = QSetup(self,maxdil=self.maxdilstep,debug=False,mindilvol=60)
        self.e.addIdleProgram(q.idler)
            
        # Add any missing fields to inputs
        for i in range(len(self.inputs)):
            if 'ligand' not in self.inputs[i]:
                self.inputs[i]['ligand']=None
            if 'negligand' not in self.inputs[i]:
                self.inputs[i]['negligand']=None
            if 'round' not in self.inputs[i]:
                self.inputs[i]['round']=None
            if 'looplength' not in self.inputs[i]:
                self.inputs[i]['looplength']=[18,18]
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

        if self.dopcr:
            # Reserve space for  PCR products
            pcrprods=[ [Sample("R%d-T%s"%(r,inp['ligand']),self.savePlate) for inp in self.inputs] for r in range(len(self.rounds))]
        else:
            pcrprods=None

        t7in = [s.getsample()  for s in self.srcs]
        
        if "negative" in self.qpcrStages:
            q.addSamples(decklayout.SSDDIL,1,self.allprimers,save=False)   # Negative controls
        if "reference" in self.qpcrStages:
            q.addReferences(dstep=10,nsteps=5,primers=["WX","MX","T7X"] if self.useMX else ["WX","T7X"],ref=reagents.getsample("BT5310"),nreplicates=1)

        # Save RT product from first (uncleaved) round and then use it during 2nd (cleaved) round for ligation and qPCR measurements
        self.rndNum=0
        self.nextID=self.firstID
        curPrefix=[inp['prefix'] for inp in self.inputs]
        r1=t7in
        
        for roundType in self.rounds:
            # Run a single round of roundType with r1 as input
            # roundType is either "U" for uncleaved, or a new prefix for a cleaved round (with "T" being a T7 prepend)
            # Set r1 to new output at end

            if self.roundCallback is not None:
                self.roundCallback(self,self.rndNum,roundType)
                
            # Computed output prefix
            if roundType=='U':
                prefixOut=curPrefix
                stop=["Unclvd" for _ in curPrefix]
            else:
                if roundType=='T':
                    stop=['T7%s'%p for p in curPrefix]
                    prefixOut=curPrefix
                elif any([p==roundType for p in curPrefix]):
                    logging.error( "Round %d is a cleaved round but goes to %s without changing prefix"%(self.rndNum, roundType))
                    assert False
                else:
                    prefixOut=[roundType for _ in curPrefix]
                    stop=prefixOut

            # May be explicitly overridden
            for i in range(len(self.inputs)):
                if 'stop' in self.inputs[i]:
                    if isinstance(self.inputs[i]['stop'],list):
                        assert(len(self.inputs[i]['stop'])==len(self.rounds))
                        t=self.inputs[i]['stop'][self.rndNum]
                    else:
                        t=self.inputs[i]['stop']
                    if (roundType=='U') != (t=='U'):
                        print("Attempt to override round %d (type %s) with a input-specific round type of %s"%(self.rndNum, roundType, t))
                        assert False
                    if roundType!='U':
                        if t=='T':
                            stop[i]='T7%s'%curPrefix[i]
                            prefixOut[i]=curPrefix[i]
                        else:
                            stop[i]=t
                            prefixOut[i]=t

            self.rndNum=self.rndNum+1
            self.finalRound=self.rndNum==len(self.rounds)

            db.pushStatus("%s%d"%(roundType,self.rndNum))
            r1=self.oneround(q,r1,prefixOut=prefixOut,stop=stop,prefixIn=curPrefix,keepCleaved=(roundType!='U'),rtvol=self.rtvol[self.rndNum-1],t7vol=self.t7vol[self.rndNum-1],cycles=self.pcrcycles[self.rndNum-1],pcrdil=self.pcrdil[self.rndNum-1],pcrvol=self.pcrvol[self.rndNum-1],dolig=self.allLig or (roundType!='U'),pcrtgt=None if pcrprods is None else pcrprods[self.rndNum-1])
            db.popStatus()

            # Add TRefs specified in rnddefs 
            if 'tref' in self.rnddef[self.rndNum-1]:
                tref=self.rnddef[self.rndNum-1]['tref']
                assert len(tref)==len(r1)
                for i in range(len(r1)):
                    if tref[i] is not None:
                        trefname='TRef%d'%tref[i]
                        print("Adding %s to %s"%(trefname,r1[i].name))
                        if not reagents.isReagent(trefname):
                            reagents.add(name=trefname,conc=10,extraVol=30,well="E4")
                        trefSamp=reagents.getsample(trefname)
                        oldConc=r1[i].conc.stock
                        oldUnits=r1[i].conc.units
                        oldVol=r1[i].volume
                        self.e.transfer(r1[i].volume/(trefSamp.conc.dilutionneeded()-1),trefSamp,r1[i],mix=(False,False))    # TODO: Check that these end up mixed
                        r1[i].conc=Concentration(stock=oldConc*oldVol/r1[i].volume, units=oldUnits)   # Treat TRef as straight dilution
                        print("New conc=",r1[i].conc)

            for i in range(len(r1)):
                if self.inputs[i]['round'] is None:
                    r1[i].name="%s_%d"%(prefixOut[i],self.nextID)
                else:
                    r1[i].name="%d_%s_R%d%c"%(self.nextID,prefixOut[i],self.inputs[i]['round']+self.rndNum,roundType)
                if self.inputs[i]['ligand'] is not None:
                    r1[i].name="%s_%s"%(r1[i].name,self.inputs[i]['ligand'])
                print("Used ID ", self.nextID," for ", r1[i].name,": ",r1[i])
                self.nextID+=1
                r1[i].conc.final=r1[i].conc.stock*self.templateDilution

            curPrefix=prefixOut


        if "finalpcr" in self.qpcrStages:
            for i in range(len(r1)):
                if self.singlePrefix:
                    q.addSamples(src=r1[i],needDil=r1[i].conc.stock/self.qConc,primers=["T7X","MX"] if self.useMX else ["T7X"])
                else:
                    # noinspection PyUnboundLocalVariable
                    q.addSamples(src=r1[i],needDil=r1[i].conc.stock/self.qConc,primers=["T7X",prefixOut[i]+"X"]+(["MX"] if self.useMX else []))

        # Add TRefs if needed
        for i in range(len(r1)):
            if 'tref' in self.inputs[i]:
                trefname='TRef%d'%self.inputs[i]['tref']
                if not reagents.isReagent(trefname):
                    reagents.add(name=trefname,conc=10,extraVol=30)
                tref=reagents.getsample(trefname)
                self.e.transfer(r1[i].volume/(tref.conc.dilutionneeded()-1),tref,r1[i],mix=(False,False))

        db.pushStatus('qPCR')
        print("######### qPCR ########### %.0f min"%(clock.elapsed()/60))
        self.allprimers=q.allprimers()
        q.run(confirm=self.qpcrWait)
        db.popStatus()
        
    def oneround(self, q, inputs, prefixOut, stop, prefixIn, keepCleaved, t7vol, rtvol, pcrdil, cycles, pcrvol, dolig,pcrtgt=None):
        primerSet=[set(["REF","T7X",prefixIn[i]+"X",prefixOut[i]+"X"]+(["MX"] if self.useMX else [])) for i in range(len(prefixIn))]
        if self.extraQPCRPrimers is not None:
            primerSet=[set(list(p) + self.extraQPCRPrimers) for p in primerSet]
            print("primerSet=",primerSet)
            
        if keepCleaved:
            print("Starting new cleavage round, will add prefix: ",prefixOut)
            assert dolig
        else:
            print("Starting new uncleaved round, will retain prefix: ",prefixIn)
        print("stop=",stop,"prefixOut=",prefixOut,", prefixIn=",prefixIn,",t7vol=",round(t7vol,ndigits=2),",rtvol=",rtvol,",pcrdil=",pcrdil,",cycles=",cycles,",dolig=",dolig)
        if self.rtCarryForward:
            assert dolig
            
        names=[i.name for i in inputs]
            
        if self.rnaInput:
            rxs=inputs
            stopDil=1
        else:
            print("######## T7 ########### %.0f min"%(clock.elapsed()/60))
            db.pushStatus("T7")
            print("Inputs:  (t7vol=%.2f)"%t7vol)
            for inp in inputs:
                if inp.conc.units=='nM':
                    print("    %s:  %.1ful@%.1f %s, use %.1f ul (%.3f pmoles)"%(inp.name,inp.volume,inp.conc.stock,inp.conc.units,t7vol/inp.conc.dilutionneeded(), t7vol*inp.conc.final/1000))
                else:
                    print("    %s:  %.1ful@%.1f %s, use %.1f ul"%(inp.name,inp.volume,inp.conc.stock,inp.conc.units,t7vol/inp.conc.dilutionneeded()))
                # inp.conc.final=inp.conc.stock*self.templateDilution
            units=list(set([inp.conc.units for inp in inputs]))
            if len(units)>1:
                print("Inputs have inconsistent concentration units: ",units)
                assert False
            if units[0]=='nM':
                needDil = max([inp.conc.stock for inp in inputs]) * 1.0 / self.qConc
            else:
                needDil = 100 / self.qConc  # Assume 100nM

            if self.directT7 and  self.rndNum==1:
                # Just add ligands and MT7 to each well
                mconc=reagents.getsample("MT7").conc.dilutionneeded()
                for i in range(len(inputs)):
                    watervol=t7vol*(1-1/mconc) - inputs[i].volume
                    if watervol<-0.1:
                        print("Negative amount of water (%.1f ul) needed for T7 setup"%watervol)
                        assert False
                    elif watervol>0.1:
                        self.e.transfer(watervol, decklayout.WATER, inputs[i], mix=(False, False))
                    self.e.transfer(t7vol / mconc, reagents.getsample("MT7"), inputs[i], mix=(False, False))
                    assert(abs(inputs[i].volume - t7vol) < 0.1)
                # Add ligands last in case they crash out when they hit aqueous;  this way, they'll be as dilute as possible
                if keepCleaved:
                    for i in range(len(inputs)):
                        if self.inputs[i]['negligand'] is not None:
                            negligand=reagents.getsample(self.inputs[i]['negligand'])
                            self.e.transfer(t7vol / negligand.conc.dilutionneeded(), negligand, inputs[i], mix=(False, False))
                            names[i]+="+"
                else:
                    for i in range(len(inputs)):
                        if self.inputs[i]['ligand'] is not None:
                            ligand=reagents.getsample(self.inputs[i]['ligand'])
                            self.e.transfer(t7vol / ligand.conc.dilutionneeded(), ligand, inputs[i], mix=(False, False))
                            names[i]+="+"
                rxs=inputs
                self.e.shakeSamples(inputs,returnPlate=True)
            elif self.rndNum==len(self.rounds) and self.finalPlus and keepCleaved:
                rxs = self.runT7Setup(ligands=[reagents.getsample(inp['ligand']) for inp in self.inputs],src=inputs, vol=t7vol, srcdil=[inp.conc.dilutionneeded() for inp in inputs])
                for i in range(len(inputs)):
                    inp=inputs[i]
                    if self.inputs[i]['ligand'] is not None:
                        rxs += self.runT7Setup(ligands=[reagents.getsample(self.inputs[i]['ligand'])],src=[inp],vol=t7vol,srcdil=[inp.conc.dilutionneeded()])
                        prefixIn+=[prefixIn[i]]
                        prefixOut+=[prefixOut[i]]
                        stop+=[stop[i]]
                        primerSet+=[primerSet[i]]
                        names+=["%s+"%names[i]]
            elif keepCleaved:
                rxs = self.runT7Setup(ligands=[reagents.getsample(inp['negligand']) for inp in self.inputs], src=inputs, vol=t7vol, srcdil=[inp.conc.dilutionneeded() for inp in inputs])
            else:
                rxs = self.runT7Setup(ligands=[reagents.getsample(inp['ligand']) for inp in self.inputs], src=inputs, vol=t7vol, srcdil=[inp.conc.dilutionneeded() for inp in inputs])

            if self.rndNum==1 and "template" in self.qpcrStages:
                # Initial input 
                for i in range(len(rxs)):
                    q.addSamples(src=rxs[i],needDil=needDil,primers=primerSet[i],names=["%s.T"%names[i]])

            self.runT7Pgm(dur=self.t7dur,vol=t7vol)
            for i in range(len(rxs)):
                rxs[i].name="%s.t7"%names[i]

            self.e.lihahome()
            print("Estimate usable RNA concentration in T7 reaction at %.0f nM"%self.rnaConc)

            if self.rndNum==1:
                worklist.userprompt("T7 Incubation Started",120)
            
            self.e.waitpgm()   # So elapsed time will be updated
            db.popStatus()
            if self.edtastop:
                print("######## Stop ########### %.0f min"%(clock.elapsed()/60))
                db.pushStatus("Stop")
                print("Have %.1f ul before stop"%rxs[0].volume)
                preStopVolume=rxs[0].volume
                self.addEDTA(tgt=rxs,finalconc=2)	# Stop to 2mM EDTA final
                db.popStatus("Stop")

                stopDil=rxs[0].volume/preStopVolume
            else:
                stopDil=1

            if self.pauseAfterStop:
                worklist.userprompt("Post EDTA pause")
                
            if self.saveRNA:
                self.saveSamps(src=rxs,vol=self.saveRNAVolume,dil=self.saveRNADilution,plate=self.savePlate,dilutant=reagents.getsample("TE8"),mix=(False,False))   # Save to check [RNA] on Qubit, bioanalyzer

        needDil = self.rnaConc/self.qConc/stopDil

        if "stopped" in self.qpcrStages:
            for i in range(len(rxs)):
                q.addSamples(src=rxs[i:i+1],needDil=needDil,primers=primerSet[i],names=["%s.stopped"%names[i]])
        
        print("######## RT  Setup ########### %.0f min"%(clock.elapsed()/60))
        db.pushStatus("RT")
        hiTemp=95

        stop=["%s-Stop"%n for n in stop]
        rt=self.runRT(src=rxs,vol=rtvol,srcdil=self.rtDil,heatInactivate=self.rtHI,hiTemp=hiTemp,dur=self.rtdur,incTemp=50,stop=[reagents.getsample(s) for s in stop],stopConc=self.stopConc)    # Heat inactivate also allows splint to fold
        
        rxs=rt
        for i in range(len(rxs)):
            if dolig and not self.singlePrefix:
                rxs[i].name=names[i]+"."+prefixOut[i]+".rt"
            else:
                rxs[i].name=names[i]+".rt"

        print("RT volume= [",",".join(["%.1f "%x.volume for x in rxs]),"]")
        
        needDil /=self.rtDil
        if self.rtpostdil[self.rndNum-1]>1:
            print("Dilution after RT: %.2f"%self.rtpostdil[self.rndNum-1])
            self.diluteInPlace(tgt=rxs,dil=self.rtpostdil[self.rndNum-1])
            needDil=needDil/self.rtpostdil[self.rndNum-1]

        # Discard extra volume of any sample that has more than current rt volume so that we can shake at high speed
        for r in Sample.getAllOnPlate(rxs[0].plate):
            if r not in rxs and r.volume>max(15+1.4,rxs[0].volume)+4:
                remove=r.volume-(15+1.4)
                oldvol=r.volume
                if r.lastMixed is None:
                    r.lastMixed=clock.elapsed  # Override since we don't care about mixing for disposal
                self.e.dispose(remove,r)
                print("Discarding some of %s to reduce volume from %.1f to %.1f to allow faster shaking"%(r.name,oldvol,r.volume))

        print("RT volume= ",[x.volume for x in rxs])
        self.e.shakeSamples(rxs)
        
        if self.rtSave:
            rtsv=self.saveSamps(src=rxs,vol=self.rtSaveVol,dil=self.rtSaveDil,plate=self.savePlate,dilutant=reagents.getsample("TE8"),mix=(False,False))   # Save to check RT product on gel (2x dil)

            if "rt" in self.qpcrStages:
                for i in range(len(rxs)):
                    q.addSamples(src=rtsv[i:i+1],needDil=needDil/2,primers=self.rtprimers[self.rndNum-1] if hasattr(self,'rtprimers') else primerSet[i],names=["%s.rt"%names[i]])
        else:
            if "rt" in self.qpcrStages:
                for i in range(len(rxs)):
                    q.addSamples(src=rxs[i:i+1],needDil=needDil,primers=self.rtprimers[self.rndNum-1] if hasattr(self,'rtprimers') else primerSet[i],names=["%s.rt"%names[i]])

        rtCarryForwardDil=10
        rtCarryForwardVol=3.5

        if self.rtCarryForward and not keepCleaved:
            # Also include RT from a prior round from here on
            for r in self.lastSaved:
                newsamp=Sample("%s.samp"%r.name,decklayout.SAMPLEPLATE)
                self.e.transfer(rxs[0].volume,r,newsamp,(False,False))
                rxs.append(newsamp)
        db.popStatus()

        if dolig:
            print("######## Ligation setup  ########### %.0f min"%(clock.elapsed()/60))
            db.pushStatus("Ligation")
            extdil=5.0/4
            reagents.getsample("MLigase").conc=Concentration(5)
            if self.ligInPlace:
                rxs=self.runLig(rxs,inPlace=True,srcdil=extdil,incTime=self.ligdur)
            else:
                rxs=self.runLig(rxs,inPlace=False,srcdil=extdil,vol=20,incTime=self.ligdur)

            print("Ligation volume= ",[x.volume for x in rxs])
            needDil=needDil/extdil
            if self.extpostdil[self.rndNum-1]>1:
                print("Dilution after extension: %.2f"%self.extpostdil[self.rndNum-1])
                self.diluteInPlace(tgt=rxs,dil=self.extpostdil[self.rndNum-1],finalvol=100)
                needDil=needDil/self.extpostdil[self.rndNum-1]
                pcrdil=pcrdil*1.0/self.extpostdil[self.rndNum-1]
                
            if self.saveDil is not None:
                ext=self.saveSamps(src=rxs,vol=3,dil=self.saveDil,dilutant=reagents.getsample("TE8"),tgt=[Sample("%s.ext"%n,self.savePlate) for n in names],mix=(False,True))   # Save cDNA product for subsequent NGS
                if "ext" in self.qpcrStages:
                    for i in range(len(ext)):
                        # Make sure we don't take more than 2 more steps
                        maxdil=q.MAXDIL*q.MAXDIL
                        if needDil/self.saveDil>maxdil:
                            logging.notice( "Diluting ext by %.0fx instead of needed %.0f to save steps"%(maxdil,needDil/self.saveDil))
                        pset=primerSet[i]
                        if "extraQPCR" in self.inputs[i]:
                            pset.udpate(self.inputs[i]["extraQPCR"])
                        q.addSamples(src=[ext[i]],needDil=min(maxdil,needDil/self.saveDil),primers=pset,names=["%s.ext"%names[i]],save=False)
            else:
                if "ext" in self.qpcrStages:
                    print("needDil=",needDil)
                    for i in range(len(names)):
                        pset=primerSet[i]
                        if "extraQPCR" in self.inputs[i]:
                            pset.update(self.inputs[i]["extraQPCR"])
                        q.addSamples(src=[rxs[i]],needDil=needDil,primers=pset,names=["%s.ext"%names[i]])
                        isave=i+len(names)
                        if isave<len(rxs):
                            # samples restored
                            q.addSamples(src=[rxs[isave]],needDil=needDil/rtCarryForwardDil,primers=primerSet[isave])
            db.popStatus()
        else:
            extdil=1
            self.extpostdil[self.rndNum-1]=1
            if self.rtpostdil[self.rndNum-1]>1:
                pcrdil=pcrdil*1.0/self.rtpostdil[self.rndNum-1]

        totalDil=stopDil*self.rtDil*self.rtpostdil[self.rndNum-1]*extdil*self.extpostdil[self.rndNum-1]
        fracRetained=rxs[0].volume/(t7vol*totalDil)
        print("Total dilution from T7 to Pre-pcr Product = %.2f*%.2f*%.2f*%.2f*%.2f = %.2f, fraction retained=%.0f%%"%(stopDil,self.rtDil,self.rtpostdil[self.rndNum-1],extdil,self.extpostdil[self.rndNum-1],totalDil,fracRetained*100))

        if self.rtCarryForward and not keepCleaved:
            # Remove the extra samples
            assert(len(self.lastSaved)>0)
            rxs=rxs[:len(rxs)-len(self.lastSaved)]
            self.lastSaved=[]

        if len(rxs)>len(inputs):
            # Have extra samples due when self.finalPlus is True
            rxs= rxs[0:len(inputs)]    # Only keep -target products
            prefixOut= prefixOut[0:len(inputs)]
            prefixIn= prefixIn[0:len(inputs)]
            stop= stop[0:len(inputs)]
            
        if self.dopcr and not (keepCleaved and self.noPCRCleave):
            print("######### PCR ############# %.0f min"%(clock.elapsed()/60))
            db.pushStatus("PCR")
            print("PCR Volume: %.1f, Dilution: %.1f, volumes available for PCR: [%s]"%(pcrvol, pcrdil,",".join(["%.1f"%r.volume for r in rxs])))

            initConc=needDil*self.qConc/pcrdil
            if keepCleaved:
                initConc=initConc*self.cleavage		# Only use cleaved as input conc
            else:
                initConc=initConc*(1-self.cleavage)
                
            gain=pcrgain(initConc,400,cycles)
            finalConc=min(200,initConc*gain)
            print("Estimated starting concentration in PCR = %.1f nM, running %d cycles -> %.0f nM\n"%(needDil*self.qConc/pcrdil,cycles,finalConc))
            nsplit=int(math.ceil(pcrvol*1.0/self.maxPCRVolume))
            print("Split each PCR into %d reactions"%nsplit)
            sampNeeded=pcrvol/pcrdil
            if self.rtCarryForward and keepCleaved:
                sampNeeded+=rtCarryForwardVol
            if keepCleaved and self.rtCarryForward:
                print("Saving %.1f ul of each pre-PCR sample" % rtCarryForwardVol)
                self.lastSaved=[Sample("%s.sv"%x.name,self.savePlate) for x in rxs]
                for i in range(len(rxs)):
                    # Save with rtCarryForwardDil dilution to reduce amount of RT consumed (will have Ct's 2-3 lower than others)
                    self.e.transfer(rtCarryForwardVol,rxs[i],self.lastSaved[i],(False,False))
                    self.e.transfer(rtCarryForwardVol*(rtCarryForwardDil-1),decklayout.WATER,self.lastSaved[i],(False,True))  # Use pipette mixing -- shaker mixing will be too slow

            #print "NSplit=",nsplit,", PCR vol=",pcrvol/nsplit,", srcdil=",pcrdil,", input vol=",pcrvol/nsplit/pcrdil
            minvol=min([r.volume for r in rxs])
            maxpcrvol=(minvol-15-1.4*nsplit)*pcrdil
            if maxpcrvol<pcrvol:
                print("Reducing PCR volume from %.1ful to %.1ful due to limited input"%(pcrvol, maxpcrvol))
                pcrvol=maxpcrvol

            if self.barcoding:
                master="MTaqBar"
            elif keepCleaved:
                master="MTaqC"
            else:
                master="MTaqU"

            reagents.getsample(master)    # Allocate for this before primers
            
            if self.barcoding:
                primers=["BCFwd" if x%2==0 else "BCRev" for x in range(len(prefixOut))]
            else:
                primers=[("T7%sX"%x).replace("T7T7","T7") for x in prefixOut]*nsplit

            rnddef = self.rnddef[self.rndNum-1]

            print("Running PCR with master=",master,", primers=",primers)
            pcr=self.runPCR(src=rxs*nsplit,vol=pcrvol/nsplit,srcdil=pcrdil,ncycles=cycles,primers=primers,usertime=self.usertime if keepCleaved else None,fastCycling=False,inPlace=False,master=master,lowhi=self.lowhi,annealTemp=57)
            if keepCleaved and self.regenPCRCycles is not None:
                # Regenerate prefix
                pcr2=self.runPCR(src=pcr,vol=self.regenPCRVolume,srcdil=self.regenPCRDilution,ncycles=self.regenPCRCycles,primers=None,usertime=None,fastCycling=False,inPlace=False,master="MTaqR",lowhi=self.lowhi,annealTemp=55)
                # Add BT575p for 1 more cycle
                for p in pcr2:
                    self.e.transfer(p.volume*0.5/10,reagents.getsample("Unclvd-Stop"),p,(False,False))
                # One more cycle
                cycling=' TEMP@95,30 TEMP@55,30 TEMP@68,30 TEMP@25,2'
                thermocycler.setpgm('rfin',100,cycling)
                self.e.runpgm("rfin",5.0,False,max([p.volume for p in pcr2]))
                pcr=pcr2	# Use 2nd PCR as actual output

            if len(pcr)<=len(names):
                # Don't relabel if we've split
                for i in range(len(pcr)):
                    pcr[i].name=names[i]+".pcr"
                
            #print "Volume remaining in PCR input source: [",",".join(["%.1f"%r.volume for r in rxs]),"]"
            needDil=finalConc/self.qConc
            print("Projected final concentration = %.0f nM"%(needDil*self.qConc))
            for i in range(len(pcr)):
                pcr[i].conc=Concentration(stock=finalConc,final=None,units='nM')
            db.popStatus()

            if self.pcrSave:
                # Save samples at 1x (move all contents -- can ignore warnings)
                maxSaveVol=(100 if self.savedilplate else 1500)*1.0/nsplit

                if self.finalRound and nsplit==1 and self.savedilplate and pcrtgt is None:
                    print("Skipping save of final PCR")
                    sv=pcr
                else:
                    residual=2.4   # Amount to leave behind to avoid aspirating air
                    sv=self.saveSamps(src=pcr[:len(rxs)],vol=[min([maxSaveVol,x.volume-residual]) for x in pcr[:len(rxs)]],dil=1,plate=(self.savePlate if self.savedilplate else decklayout.EPPENDORFS),tgt=pcrtgt)
                    if nsplit>1:
                        # Combine split
                        for i in range(len(rxs),len(rxs)*nsplit):
                            self.e.transfer(min([maxSaveVol,pcr[i].volume-residual]),pcr[i],sv[i%len(sv)],mix=(False,False))
                        # Correct concentration (above would've assumed it was diluted)
                        for i in range(len(sv)):
                            sv[i].conc=pcr[i].conc
                        # Shake
                        self.e.shakeSamples(sv)

                if "pcr" in self.qpcrStages:
                    for i in range(len(sv)):
                        q.addSamples(sv[i],needDil,primers=primerSet[i],names=["%s.pcr"%names[i]])

                print("Have %.2f pmoles of product (%.0f ul @ %.1f nM)"%(sv[0].volume*sv[0].conc.stock/1000,sv[0].volume,sv[0].conc.stock))
                return sv
            else:
                assert "pcr" not in self.qpcrStages   ## Not implemented
                return pcr[:len(rxs)]

        elif self.noPCRCleave:
            print("Dilution instead of PCR: %.2f"%self.nopcrdil)
            # Need to add enough t7prefix to compensate for all of the Stop primer currently present, regardless of whether it is for cleaved or uncleaved
            # Will result in some short transcripts corresponding to the stop primers that are not used for cleaved product, producing just GGG_W_GTCTGC in the next round.  These would be reverse-trancribed, but may compete for T7 yield
            t7prefix=reagents.getsample("BT88")
            dil=self.extpostdil[self.rndNum-1]  # FIXME: Is this correct?  Used to have a 'userDil' term
            stopconc=1000.0/dil
            bt88conc=t7prefix.conc.stock
            relbt88=stopconc/bt88conc
            print("Using EXT with %.0fnM of stop oligo as input to next T7, need %.2ful of BT88@%.0fnM per ul of sample"%(stopconc,relbt88,bt88conc))
            for r in rxs:
                vol=r.volume*relbt88
                t7prefix.conc.final=t7prefix.conc.stock*vol/(r.volume+vol)
                r.conc.final=r.conc.stock*r.volume/(r.volume+vol)
                self.e.transfer(vol,t7prefix,r,mix=(False,False))

            if self.nopcrdil>(1+relbt88):
                self.diluteInPlace(tgt=rxs,dil=self.nopcrdil/(1.0+relbt88))
                #needDil=needDil/self.nopcrdil  # needDil not used subsequently
                print("Dilution of EXT product: %.2fx * %.2fx = %2.fx\n"%(1+relbt88,self.nopcrdil/(1+relbt88),self.nopcrdil))
            else:
                print("Dilution of EXT product: %.2fx\n"%(1+relbt88))

            return rxs, []
        else:
            return rxs, []


class PGMAnalytic(PGMSelect):
    """Analytic experiment"""

    def __init__(self, inputs, saveRNA=False, tmplFinalConc=5, qpcrStages=None, templateDilution=0.6,useMX=False):
        super(PGMAnalytic, self).__init__(inputs=inputs,rounds='C',firstID=1,pmolesIn=0,saveRNA=saveRNA,qpcrStages=qpcrStages,templateDilution=templateDilution,tmplFinalConc=tmplFinalConc,useMX=useMX)
        self.dopcr=True
        self.barcoding=True
        self.pcrSave=False
        self.saveRNADilution=2
        self.ligInPlace=True
        self.rtpostdil=[2]
        self.saveDil=None
        self.pcrdil=[375]
        self.extpostdil=[p/8.0 for p in self.pcrdil] # Make sure to predilute enough so that we have >= 2µl going into PCR
        self.pcrcycles=[5]
        self.setVolumes()
