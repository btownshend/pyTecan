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
    
    def __init__(self,inputs,rounds,firstID,pmolesIn,doexo=False,doampure=False,directT7=True,templateDilution=0.3,tmplFinalConc=50,saveDil=24,qpcrWait=False,allLig=False,qpcrStages=["negative","template","ext","finalpcr"],finalPlus=True, cleaveOnly=False,t7dur=30,columnclean=False,douser=False,usertime=10,pcrdil=None,exotime=60,singlePrefix=False,noPCRCleave=False,saveRNA=False):
        # Initialize field values which will never change during multiple calls to pgm()
        for i in range(len(inputs)):
            if 'ligand' not in inputs[i]:
                inputs[i]['ligand']=None
            if 'round' not in inputs[i]:
                inputs[i]['round']=None
            if 'name' not in inputs[i]:
                if inputs[i]['ligand'] is None:
                    inputs[i]['name']='%s_%d_R%d'%(inputs[i]['prefix'],inputs[i]['ID'],inputs[i]['round'])
                else:
                    inputs[i]['name']='%s_%d_R%d_%s'%(inputs[i]['prefix'],inputs[i]['ID'],inputs[i]['round'],inputs[i]['ligand'])
        self.inputs=inputs
        self.rounds=rounds
        self.nrounds=len(rounds)
        self.doexo=doexo
        self.exotime=exotime
        self.doampure=doampure
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
        self.cleaveOnly=cleaveOnly
        self.t7dur=t7dur
        self.columnclean=columnclean
        self.douser=douser
        self.usertime=usertime				# USER incubation time in minutes
        self.singlePrefix=singlePrefix
        self.noPCRCleave=noPCRCleave   # Skip PCR on cleave-selection rounds
        self.saveRNA=saveRNA
        
        # General parameters
        self.qConc = 0.050			# Target qPCR concentration in nM (corresponds to Ct ~ 10)
       # Expected concentration of RNA (actually back-computed from MX concentration after RT)
       # Limited to [stop]*4/0.9
        self.rnaConc=min(1000*4/0.9,8314*self.tmplFinalConc/(self.tmplFinalConc+55)*self.t7dur/30)
        self.pcrSave=True		    # Save PCR products
        self.savedilplate=True	# Save PCR products on dilutions plate
        self.rtSave=False			# True to save RT product from uncleaved round and run ligation during cleaved round
        self.dopcr=True			    # Run PCR of samples
        self.cleavage=0.40			# Estimated cleavage (for computing dilutions of qPCRs)
        self.exopostdil=2
        self.extpostdil=2
        self.nopcrdil=4
        self.userMelt=False
        self.maxDilVolume=100
        self.maxSampVolume=125
        self.rtcopies=4    				# Number of copies maintained in RT stage
        self.rtHI=False				   # Heat inactive/refold after RT
        self.saveRNADilution=10
        self.ligInPlace=True
        self.allprimers=["REF","MX","T7X","T7WX"]    # Will get updated after first pass with all primers used

        self.rtpostdil=[3.0 if r=='U' else 1.0 for r in self.rounds]
        # Computed parameters
        if pcrdil is None:
            self.pcrdilU=80.0/self.extpostdil/(self.exopostdil if self.doexo else 1)
            self.pcrdilC=self.pcrdilU/2
        else:
            self.pcrdilU=pcrdil
            self.pcrdilC=pcrdil
        pcrvolU=max(100,self.pmolesIn*1000/(self.rnaConc*0.9/4)*self.pcrdilU)    # Concentration up to PCR dilution is RNA concentration after EDTA addition and RT setup
        # Use at least 100ul so the evaporation of the saved sample that occurs during the run will be relatively small
        self.pcrcyclesU=10
        pcrvolC=max(100,self.pmolesIn*1000/(self.rnaConc*0.9/4/1.25)*self.pcrdilC)  # Concentration up to PCR dilution is RNA concentration after EDTA addition and RT setup and Ligation
        self.pcrcyclesC=10

        rtvolU=max(8,self.pmolesIn*self.rtcopies*1e-12/(self.rnaConc*1e-9/4)*1e6)    # Compute volume so that full utilization of RNA results in rtcopies * input diversity
        rtvolC=max(9,self.pmolesIn*self.rtcopies*1e-12/(self.rnaConc*1e-9/4)*1e6)    # Compute volume so that full utilization of RNA results in rtcopies * input diversity
        if self.noPCRCleave:
            rtvolC=max(rtvolC,25)	# Need to have enough for subsequent T7 reaction

        if "rt" in self.qpcrStages:
            rtvolU=max(rtvolU,15)/self.rtpostdil+5.4
            rtvolC=max(rtvolC,15)/self.rtpostdil+5.4
            if "ext" in self.qpcrStages:
                rtvolC+=1.4

        self.t7extravols=((4+1.4)*0.9 if 'stopped' in self.qpcrStages else 0)+ ((5+1.4)*0.9 if self.saveRNA else 0)
        print "self.t7extravols=%.1f ul\n"%self.t7extravols
        t7volU=min(self.maxSampVolume,max((15.1+rtvolU/4.0+1.4)*0.9+self.t7extravols,self.pmolesIn*1000/tmplFinalConc))
        t7volC=min(self.maxSampVolume,max((15.1+rtvolC/4.0+1.4)*0.9+self.t7extravols,self.pmolesIn*1000/tmplFinalConc))


        self.t7vol=[t7volC if roundType=='C' else t7volU for roundType in self.rounds]
        if 'template' in self.qpcrStages:
            self.t7vol[0]+=5.4
        self.rtvol=[rtvolC if roundType=='C' else rtvolU for roundType in self.rounds]
        self.pcrvol=[pcrvolC if roundType=='C' else pcrvolU for roundType in self.rounds]

    def setup(self):
        TRP.setup(self)
        worklist.setOptimization(True)

    def pgm(self):
        q = QSetup(self,maxdil=16,debug=False,mindilvol=60)
        self.e.addIdleProgram(q.idler)

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
                r1=self.oneround(q,r1,prefixOut,prefixIn=curPrefix,keepCleaved=False,rtvol=self.rtvol[self.rndNum-1],t7vol=self.t7vol[self.rndNum-1],cycles=self.pcrcyclesU,pcrdil=self.pcrdilU,pcrvol=self.pcrvol[self.rndNum-1],dolig=self.allLig)
            else:
                assert(roundType=='C')
                r1=self.oneround(q,r1,prefixOut,prefixIn=curPrefix,keepCleaved=True,rtvol=self.rtvol[self.rndNum-1],t7vol=self.t7vol[self.rndNum-1],cycles=self.pcrcyclesC,pcrdil=self.pcrdilC,pcrvol=self.pcrvol[self.rndNum-1],dolig=True)

            for i in range(len(r1)):
                r1[i].name="%s_Out_%d"%(prefixOut[i],self.nextID)
                if self.inputs[i]['round'] is not None:
                    r1[i].name="%s_R%d%c"%(r1[i].name,self.inputs[i]['round']+self.rndNum,roundType)
                if self.inputs[i]['ligand'] is not None and roundType=='U':
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
        if self.rtSave:
            assert(dolig)
            
        names=[i.name for i in input]
            
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
        elif self.rndNum==self.nrounds and self.finalPlus and keepCleaved:
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

        print "Estimate RNA concentration in T7 reaction at %.0f nM"%self.rnaConc
        
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
        rtDil=4
        hiTemp=95
        rtDur=20

        stop=["Unclvd-Stop" if (not dolig) else "T7W-Stop" if self.singlePrefix else "%s-Stop"%n for n in prefixOut]
        rxs=self.runRT(src=rxs,vol=rtvol,srcdil=rtDil,heatInactivate=self.rtHI,hiTemp=hiTemp,dur=rtDur,incTemp=50,stop=[reagents.getsample(s) for s in stop])    # Heat inactivate also allows splint to fold
        for i in range(len(rxs)):
            if dolig and not self.singlePrefix:
                rxs[i].name=names[i]+"."+prefixOut[i]+".rt"
            else:
                rxs[i].name=names[i]+".rt"

        print "RT volume= [",",".join(["%.1f "%x.volume for x in rxs]),"]"
        needDil /= rtDil
        if self.rtpostdil[self.rndNum-1]>1:
            print "Dilution after RT: %.2f"%self.rtpostdil[self.rndNum-1]
            self.diluteInPlace(tgt=rxs,dil=self.rtpostdil[self.rndNum-1])
            needDil=needDil/self.rtpostdil[self.rndNum-1]

        if "rt" in self.qpcrStages:
            for i in range(len(rxs)):
                q.addSamples(src=rxs[i:i+1],needDil=needDil,primers=primerSet[i],names=["%s.rt"%names[i]])

        rtSaveDil=10
        rtSaveVol=3.5

        if self.rtSave and not keepCleaved:
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
                rxs=self.runLig(rxs,inPlace=True,srcdil=extdil)
            else:
                rxs=self.runLig(rxs,inPlace=False,srcdil=extdil,vol=20)

            print "Ligation volume= ",[x.volume for x in rxs]
            needDil=needDil/extdil
            if self.extpostdil>1:
                print "Dilution after extension: %.2f"%self.extpostdil
                self.diluteInPlace(tgt=rxs,dil=self.extpostdil)
                needDil=needDil/self.extpostdil
                    
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
                    for i in range(len(input)):
                        q.addSamples(src=[rxs[i]],needDil=needDil,primers=primerSet[i],names=["%s.ext"%names[i]])
                        isave=i+len(input)
                        if isave<len(rxs):
                            # samples restored
                            q.addSamples(src=[rxs[isave]],needDil=needDil/rtSaveDil,primers=primerSet[isave])

            if self.doexo:
                print "######## Exo ########### %.0f min"%(clock.elapsed()/60)
                prevvol=rxs[0].volume
                rxs=self.runExo(rxs,incTime=self.exotime,inPlace=True,hiTemp=95,hiTime=20)
                print "Exo volume=[%s]"%",".join(["%.1f"%r.volume for r in rxs])
                exoDil=rxs[0].volume/prevvol
                needDil/=exoDil
                needDil/=7   #  Anecdotal based on Ct's -- large components (MX) reduced by exo digestion
                if self.exopostdil>1:
                    print "Dilution after exo: %.2f"%self.exopostdil
                    self.diluteInPlace(tgt=rxs,dil=self.exopostdil)
                    needDil=needDil/self.exopostdil

                if self.saveDil is not None:
                    exo=self.saveSamps(src=rxs,vol=3,dil=self.saveDil,dilutant=reagents.getsample("TE8"),tgt=[Sample("%s.exo"%n,decklayout.DILPLATE) for n in names])   # Save cDNA product
                    if "exo" in self.qpcrStages:
                        for i in range(len(exo)):
                            q.addSamples(src=[exo[i]],needDil=needDil/self.saveDil,primers=primerSet[i],names=["%s.exo"%names[i]])
                else:
                    if "exo" in self.qpcrStages:
                        for i in range(len(rxs)):
                            q.addSamples(src=[rxs[i]],needDil=needDil,primers=primerSet[i],names=["%s.exo"%names[i]])
                    
            else:
                exoDil=1
                self.exopostdil=1
                exo=[]
        else:
            extdil=1
            self.extpostdil=1
            self.exopostdil=1
            exoDil=1
            
        if self.doampure:
            print "######## Ampure Cleanup ########### %.0f min"%(clock.elapsed()/60)
            ratio=1.8
            elutionVol=30
            needDil=needDil*rxs[0].volume/elutionVol
            print "Ampure cleanup of [%s] into %.1f ul"%(",".join(["%.1f"%r.volume for r in rxs]),elutionVol)
            clean=self.runAmpure(src=rxs,ratio=ratio,elutionVol=elutionVol)
            if "ampure" in self.qpcrStages:
                for i in range(len(clean)):
                    q.addSamples(src=[clean[i]],needDil=needDil,primers=primerSet[i],names=["%s.amp"%names[i]])
            rxs=clean   # Use the cleaned products for PCR

        if self.columnclean:
            print "######## Column Cleanup ########### %.0f min"%(clock.elapsed()/60)
            elutionVol=30
            cleaned=[Sample("%s.cln"%r.name,decklayout.SAMPLEPLATE,volume=elutionVol,ingredients=r.ingredients) for r in rxs]
            columnDil=elutionVol/rxs[0].volume
            print "Column cleanup of [%s] into %.1f ul"%(",".join(["%.1f"%r.volume for r in rxs]),elutionVol)
            inwells=",".join([r.plate.wellname(r.well) for r in rxs])
            outwells=",".join([r.plate.wellname(r.well) for r in cleaned])
            msg="Run column cleanup of wells [%s], elute in %.1f ul and put products into wells [%s]"%(inwells,elutionVol,outwells)
            print msg
            worklist.userprompt(msg)
            needDil=needDil/columnDil
            rxs=cleaned
            if "column" in self.qpcrStages:
                for i in range(len(rxs)):
                    q.addSamples(src=rxs[i],needDil=needDil,primers=primerSet[i],names=["%s.cln"%names[i]])
        else:
            columnDil=1
            
        if self.douser:
            print "######## User ########### %.0f min"%(clock.elapsed()/60)
            prevvol=rxs[0].volume
            if self.userMelt:
                self.runUser(rxs,incTime=self.usertime,inPlace=True,hiTime=1,hiTemp=95)
            else:
                self.runUser(rxs,incTime=self.usertime,inPlace=True)
            print "USER volume=[%s]"%",".join(["%.1f"%r.volume for r in rxs])
            userDil=rxs[0].volume/prevvol
            needDil/=userDil
            if "user" in self.qpcrStages:
                for i in range(len(rxs)):
                    q.addSamples(src=rxs[i],needDil=needDil,primers=primerSet[i],names=["%s.user"%names[i]])
        else:
            userDil=1

        totalDil=stopDil*rtDil*self.rtpostdil[self.rndNum-1]*extdil*self.extpostdil*exoDil*self.exopostdil*columnDil*userDil
        fracRetained=rxs[0].volume/(t7vol*totalDil)
        print "Total dilution from T7 to Pre-pcr Product = %.2f*%.2f*%.2f*%.2f*%.2f*%.2f*%.2f*%.2f*%.2f = %.2f, fraction retained=%.0f%%"%(stopDil,rtDil,self.rtpostdil[self.rndNum-1],extdil,self.extpostdil,exoDil,self.exopostdil,columnDil,userDil,totalDil,fracRetained*100)

        if self.rtSave and not keepCleaved:
            # Remove the extra samples
            assert(len(self.lastSaved)>0)
            rxs=rxs[:len(rxs)-len(self.lastSaved)]
            self.lastSaved=[]

        if len(rxs)>len(input):
            rxs=rxs[0:len(input)]    # Only keep -target products
            prefixOut=prefixOut[0:len(input)]
            prefixIn=prefixIn[0:len(input)]
            
        if self.dopcr and not (keepCleaved and self.noPCRCleave):
            print "######### PCR ############# %.0f min"%(clock.elapsed()/60)
            maxvol=max([r.volume for r in rxs])
            print "PCR Volume: %.1f, Dilution: %.1f, volumes available for PCR: [%s]"%(pcrvol, pcrdil,",".join(["%.1f"%r.volume for r in rxs]))
            maxPCRVolume=100  # Maximum sample volume of each PCR reaction (thermocycler limit, and mixing limit)

            initConc=needDil*self.qConc/pcrdil
            if keepCleaved:
                if self.doexo:
                    initConc=initConc*7*self.cleavage		# Back out 7x dilution in exo step, but only use cleaved as input conc
                else:
                    initConc=initConc*self.cleavage		# Only use cleaved as input conc
            else:
                initConc=initConc*(1-self.cleavage)
                
            gain=pcrgain(initConc,400,cycles)
            finalConc=min(200,initConc*gain)
            print "Estimated starting concentration in PCR = %.1f nM, running %d cycles -> %.0f nM\n"%(needDil*self.qConc/pcrdil,cycles,finalConc)
            nsplit=int(math.ceil(pcrvol*1.0/maxPCRVolume))
            print "Split each PCR into %d reactions"%nsplit
            minsrcdil=1/(1-1.0/3-1.0/4)
            sampNeeded=pcrvol/pcrdil
            if self.rtSave and keepCleaved:
                sampNeeded+=rtSaveVol
            maxvol=max([r.volume for r in rxs]);
            minvol=min([r.volume for r in rxs]);
            predil=min(self.maxDilVolume/maxvol,(40+1.4*nsplit)/(minvol-sampNeeded))  # Dilute to have 40ul left -- keeps enough sample to allow good mixing
            if keepCleaved and self.rtSave and predil>rtSaveDil:
                print "Reducing predil from %.1f to %.1f (rtSaveDil)"%(predil, rtSaveDil)
                predil=rtSaveDil
            if pcrdil/predil<minsrcdil:
                predil=pcrdil/minsrcdil	  # Need to dilute at least this into PCR
            if predil>1:
                self.diluteInPlace(rxs,predil)
                self.e.shakeSamples(rxs)
                print "Pre-diluting by %.1fx into [%s] ul"%(predil,",".join(["%.1f"%r.volume for r in rxs]))
            if keepCleaved and self.rtSave:
                assert(len(rxs)==len(rtSave))
                print "Saving %.1f ul of each pre-PCR sample (@%.1f*%.1f dilution)"%(rtSaveVol ,predil, rtSaveDil/predil)
                self.lastSaved=[Sample("%s.sv"%x.name,decklayout.DILPLATE) for x in rxs]
                for i in range(len(rxs)):
                    # Save with rtSaveDil dilution to reduce amount of RT consumed (will have Ct's 2-3 lower than others)
                    self.e.transfer(rtSaveVol*predil,rxs[i],self.lastSaved[i],(False,False))
                    self.e.transfer(rtSaveVol*(rtSaveDil/predil-1),decklayout.WATER,self.lastSaved[i],(False,True))  # Use pipette mixing -- shaker mixing will be too slow

            #print "NSplit=",nsplit,", PCR vol=",pcrvol/nsplit,", srcdil=",pcrdil*1.0/predil,", input vol=",pcrvol/nsplit/pcrdil*predil
            minvol=min([r.volume for r in rxs]);
            maxpcrvol=(minvol-15-1.4*nsplit)*pcrdil/predil
            if maxpcrvol<pcrvol:
                print "Reducing PCR volume from %.1ful to %.1ful due to limited input"%(pcrvol, maxpcrvol)
                pcrvol=maxpcrvol

            pcr=self.runPCR(src=rxs*nsplit,vol=pcrvol/nsplit,srcdil=pcrdil*1.0/predil,ncycles=cycles,primers=["T7%sX"%("" if self.singlePrefix and keepCleaved else x) for x in (prefixOut if keepCleaved else prefixIn)]*nsplit,usertime=self.usertime if keepCleaved and not self.douser else None,fastCycling=False,inPlace=False)
            for i in range(len(pcr)):
                pcr[i].name=names[i]+".pcr"
                
            print "Volume remaining in PCR input source: [",",".join(["%.1f"%r.volume for r in rxs]),"]"
            needDil=finalConc/self.qConc
            print "Projected final concentration = %.0f nM"%(needDil*self.qConc)
            for i in range(len(pcr)):
                pcr[i].conc=Concentration(stock=finalConc,final=None,units='nM')

            if self.pcrSave:
                # Save samples at 1x (move all contents -- can ignore warnings)
                maxSaveVol=self.maxDilVolume*1.0/nsplit

                if self.savedilplate:
                    sv=self.saveSamps(src=pcr[:len(rxs)],vol=[min([maxSaveVol,x.volume]) for x in pcr[:len(rxs)]],dil=1,plate=decklayout.DILPLATE,atEnd=True)
                else:
                    sv=self.saveSamps(src=pcr[:len(rxs)],vol=[x.volume for x in pcr[:len(rxs)]],dil=1,plate=decklayout.EPPENDORFS)
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
            dil=self.extpostdil*exoDil*self.exopostdil*columnDil*userDil
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

    def __init__(self,inputs,saveRNA=False,tmplFinalConc=5,qpcrStage=["ext","negative"],templateDilution=0.6):
        super(PGMAnalytic, self).__init__(inputs=inputs,rounds='C',firstID=1,pmolesIn=0,saveRNA=saveRNA,qpcrStages=qpcrStage,templateDilution=templateDilution,tmplFinalConc=tmplFinalConc)
        self.dopcr=False
        self.saveRNADilution=2
        self.ligInPlace=False
        rtvolC=8
        self.extpostdil=4
        self.rtpostdil=[2]
        self.saveDil=None
