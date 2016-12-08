# Generic selection progam
import debughook
import math

from Experiment.concentration import Concentration
from Experiment.sample import Sample
from Experiment import worklist, reagents, decklayout
from TRPLib.TRP import TRP
from TRPLib.QSetup import QSetup
from pcrgain import pcrgain

class PGMSelect(TRP):
    '''Selection experiment'''
    
    def __init__(self,inputs,nrounds,firstID,pmolesIn,doexo=False,doampure=False,directT7=True,templateDilution=0.3,tmplFinalConc=50,saveDil=10):
        # Initialize field values which will never change during multiple calls to pgm()
        self.inputs=inputs
        self.nrounds=nrounds
        self.doexo=doexo
        self.doampure=doampure
        self.directT7=directT7
        self.tmplFinalConc=tmplFinalConc
        self.templateDilution=templateDilution
        self.pmolesIn=pmolesIn
        self.firstID=firstID
        self.saveDil=saveDil
        
        # General parameters
        self.qConc = 0.025			# Target qPCR concentration in nM (corresponds to Ct ~ 10)
        self.rnaConc=2000		    # Expectec concentration of RNA
        self.pcrSave=True		    # Save PCR products
        self.savedilplate=True	# Save PCR products on dilutions plate
        self.usertime=10				# USER incubation time in minutes
        self.rtSave=False			# True to save RT product from uncleaved round and run ligation during cleaved round
        self.dopcr=True			    # Run PCR of samples
        self.cleavage=0.30			# Estimated cleavage (for computing dilutions of qPCRs)
        
        # Computed parameters
        self.t7vol1=max(20,self.pmolesIn*1000/tmplFinalConc)
        self.rtvol1=max(8,self.pmolesIn*1000/self.rnaConc)
        self.pcrdil1=80
        self.pcrvol1=self.pmolesIn*1000/(self.rnaConc*0.9/4)*self.pcrdil1    # Concentration up to PCR dilution is RNA concentration after EDTA addition and RT setup
        self.pcrcycles1=10
        
        self.t7vol2=max(22,self.pmolesIn*1000/self.tmplFinalConc)
        self.rtvol2=max(9,self.pmolesIn*1000/self.rnaConc)
        self.pcrdil2=40
        self.pcrvol2=self.pmolesIn*1000/(self.rnaConc*0.9/4/1.25)*self.pcrdil2  # Concentration up to PCR dilution is RNA concentration after EDTA addition and RT setup and Ligation
        self.pcrcycles2=10

        # Add templates
        if self.directT7:
            self.srcs = self.addTemplates([inp['name'] for inp in inputs],stockconc=tmplFinalConc/templateDilution,finalconc=tmplFinalConc,plate=decklayout.SAMPLEPLATE,looplengths=[inp['looplength'] for inp in inputs],initVol=self.t7vol1*templateDilution,extraVol=0)
        else:
            self.srcs = self.addTemplates([inp['name'] for inp in inputs],stockconc=tmplFinalConc/templateDilution,finalconc=tmplFinalConc,plate=decklayout.DILPLATE,looplengths=[inp['looplength'] for inp in inputs],extraVol=15) 
        
    def setup(self):
        TRP.setup(self)
        worklist.setOptimization(True)

    def pgm(self):
        q = QSetup(self,maxdil=16,debug=False,mindilvol=60)
        self.e.addIdleProgram(q.idler)
        t7in = [s.getsample()  for s in self.srcs]

        qpcrPrimers=["REF","MX","T7X","T7AX","T7BX","T7WX"]
        q.addSamples(decklayout.SSDDIL,1,qpcrPrimers,save=False)   # Negative controls
        self.trackIndices=[]

        # Save RT product from first (uncleaved) round and then use it during 2nd (cleaved) round for ligation and qPCR measurements
        self.rndNum=0
        self.nextID=self.firstID
        curPrefix=[inp['prefix'] for inp in self.inputs]

        while self.rndNum<self.nrounds:
            self.rndNum=self.rndNum+1
                
            prefixOut=["A" if p=="W" else "B" if p=="A" else "W" if p=="B" else "BADPREFIX" for p in curPrefix]
            self.t7vol1=max(20,self.pmolesIn*1000/min([inp.conc.final for inp in t7in]))
            r1=self.oneround(q,t7in,prefixOut,prefixIn=curPrefix,keepCleaved=False,rtvol=self.rtvol1,t7vol=self.t7vol1,cycles=self.pcrcycles1,pcrdil=self.pcrdil1,pcrvol=self.pcrvol1)
            # pcrvol is set to have same diversity as input 
            for i in range(len(r1)):
                r1[i].name="%s_%d_R%dU_%s"%(curPrefix[i],self.nextID,self.inputs[i]['round']+self.rndNum,self.inputs[i]['ligand'])
                self.nextID+=1
                r1[i].conc.final=r1[i].conc.stock*self.templateDilution
            if self.rndNum>=self.nrounds:
                logging.warning("Warning: ending on an uncleaved round")
                break
            
            self.rndNum=self.rndNum+1
            if self.rndNum==self.nrounds:
                print "Tracking with qPCR for final round"
                self.trackIndices=range(len(t7in))	# Track the final round

            print "prefixIn=",curPrefix
            print "prefixOut=",prefixOut
            
            self.t7vol2=max(20,self.pmolesIn*1000/min([inp.conc.final for inp in r1]))
            r2=self.oneround(q,r1,prefixOut,prefixIn=curPrefix,keepCleaved=True,rtvol=self.rtvol2,t7vol=self.t7vol2,cycles=self.pcrcycles2,pcrdil=self.pcrdil2,pcrvol=self.pcrvol2)
            # pcrvol is set to have same diversity as input = (self.t7vol2*self.templateDilution/rnagain*stopdil*rtdil*extdil*exodil*pcrdil)
            for i in range(len(self.inputs)):
                r2[i].name="%s_%d_R%dC_%s"%(prefixOut[i],self.nextID,self.inputs[i]['round']+self.rndNum,self.inputs[i]['ligand'])
                self.nextID+=1
                r2[i].conc.final=r2[i].conc.stock*self.templateDilution
            if len(self.trackIndices)>0:
                q.addSamples(src=r2,needDil=r2[0].conc.stock/self.qConc,primers=qpcrPrimers)
            t7in=r2
            curPrefix=prefixOut
            
        print "######### qPCR ###########"
        #q.addReferences(mindil=4,nsteps=6,primers=["T7X","MX","T7AX"])
        #worklist.userprompt('Continue to setup qPCR')
        q.run()
        
    def oneround(self,q,input,prefixOut,prefixIn,keepCleaved,t7vol,rtvol,pcrdil,cycles,pcrvol):
        if keepCleaved:
            print "Starting new cleavage round, will add prefix: ",prefixOut
        else:
            print "Starting new uncleaved round, will retain prefix: ",prefixIn

        names=[i.name for i in input]
            
        print "######## T7 ###########"
        print "Inputs:  (t7vol=%.2f)"%t7vol
        for inp in input:
            print "    %s:  %.1ful@%.1f nM, use %.1f ul (%.3f pmoles)"%(inp.name,inp.volume,inp.conc.stock,t7vol/inp.conc.dilutionneeded(), t7vol*inp.conc.final/1000)
            # inp.conc.final=inp.conc.stock*self.templateDilution
        needDil = max([inp.conc.stock for inp in input])*1.0/self.qConc
        if self.directT7 and  self.rndNum==1:
            # Just add ligands and MT7 to each well
            for i in range(len(input)):
                ligand=reagents.getsample(self.inputs[i]['ligand'])
                self.e.transfer(t7vol/ligand.conc.dilutionneeded(),ligand,input[i],mix=(False,False))
            mconc=reagents.getsample("MT7").conc.dilutionneeded()
            for i in range(len(input)):
                watervol=t7vol*(1-1/mconc)-input[i].volume
                if watervol>0.1:
                    self.e.transfer(watervol,decklayout.WATER,input[i],mix=(False,False))
                self.e.transfer(t7vol/mconc,reagents.getsample("MT7"),input[i],mix=(False,False))
                assert(input[i].volume==t7vol)
            rxs=input
        elif self.rndNum==self.nrounds:
            rxs = self.runT7Setup(src=input,vol=t7vol,srcdil=[inp.conc.dilutionneeded() for inp in input])
            rxs += self.runT7Setup(ligands=[reagents.getsample(inp['ligand']) for inp in self.inputs],src=input,vol=t7vol,srcdil=[inp.conc.dilutionneeded() for inp in input])
            prefixIn+=prefixIn
            prefixOut+=prefixOut
            names+=["%s+"%n for n in names]
        elif keepCleaved:
            rxs = self.runT7Setup(src=input,vol=t7vol,srcdil=[inp.conc.dilutionneeded() for inp in input])
        else:
            rxs = self.runT7Setup(ligands=[reagents.getsample(inp['ligand']) for inp in self.inputs],src=input,vol=t7vol,srcdil=[inp.conc.dilutionneeded() for inp in input])
            
        for i in range(len(rxs)):
            rxs[i].name="%s.rx"%names[i]


        #for i in self.trackIndices:
        #   q.addSamples(src=[rxs[i]],needDil=needDil,primers=["T7"+prefixIn[i]+"X","MX","T7X","REF"],names=["%s.T-"%names[i]])
        
        needDil = needDil*max([inp.conc.dilutionneeded() for inp in input])
        t7dur=30
        self.runT7Pgm(dur=t7dur,vol=t7vol)
        self.rnaConc=min(40,inp.conc.final)*t7dur*65/30
        print "Estimate RNA concentration in T7 reaction at %.0f nM"%self.rnaConc

        print "######## Stop ###########"
        #self.saveSamps(src=rxs,vol=5,dil=10,plate=decklayout.EPPENDORFS,dilutant=reagents.getsample("TE8"),mix=(False,False))   # Save to check [RNA] on Qubit, bioanalyzer

        self.e.lihahome()

        print "Have %.1f ul before stop"%rxs[0].volume
        preStopVolume=rxs[0].volume
        self.addEDTA(tgt=rxs,finalconc=2)	# Stop to 2mM EDTA final
        
        stop=["Unclvd-Stop" if (not keepCleaved and not self.rtSave) else "A-Stop" if n=="A" else "B-Stop" if n=="B" else "W-Stop" if n=="W" else "BADPREFIX" for n in prefixOut]

        stopDil=rxs[0].volume/preStopVolume
        needDil = self.rnaConc/self.qConc/stopDil
        #q.addSamples(src=rxs,needDil=needDil,primers=["T7AX","MX","T7X","REF"],names=["%s.stopped"%r.name for r in rxs])
        
        print "######## RT  Setup ###########"
        rtDil=4
        hiTemp=95
        rtDur=20

        rxs=self.runRT(src=rxs,vol=rtvol,srcdil=rtDil,heatInactivate=True,hiTemp=hiTemp,dur=rtDur,incTemp=50,stop=[reagents.getsample(s) for s in stop])    # Heat inactivate also allows splint to fold
        print "RT volume= ",[x.volume for x in rxs]
        needDil /= rtDil
        #q.addSamples(src=rxs,needDil=needDil,primers=["T7AX","MX","REF"],names=["%s.rt"%r.name for r in rxs])

        rtSaveDil=10
        rtSaveVol=3.5

        if self.rtSave and not keepCleaved:
            # Also include RT from a prior round from here on
            for r in self.lastSaved:
                newsamp=Sample("%s.samp"%r.name,decklayout.SAMPLEPLATE)
                self.e.transfer(rxs[0].volume,r,newsamp,(False,False))
                rxs.append(newsamp)
            
        if keepCleaved:
            print "######## Ligation setup  ###########"
            extdil=5.0/4
            reagents.getsample("MLigase").conc=Concentration(5)
            rxs=self.runLig(rxs,inPlace=True)

            print "Ligation volume= ",[x.volume for x in rxs]
            needDil=needDil/extdil
            extpostdil=2
            if extpostdil>1:
                print "Dilution after extension: %.2f"%extpostdil
                self.diluteInPlace(tgt=rxs,dil=extpostdil)
                needDil=needDil/extpostdil
                if not self.doexo:
                    pcrdil=pcrdil/extpostdil
                    
            if self.saveDil is not None:
                ext=self.saveSamps(src=rxs,vol=3,dil=self.saveDil,dilutant=reagents.getsample("TE8"),tgt=[Sample("%s.ext"%n,decklayout.DILPLATE) for n in names],mix=(False,True))   # Save cDNA product for subsequent NGS
                for i in self.trackIndices:
                    q.addSamples(src=[ext[i]],needDil=needDil/self.saveDil,primers=["T7"+prefixIn[i]+"X","T7"+prefixOut[i]+"X","MX","T7X","REF"],names=["%s.ext"%names[i]])
            else:
                for i in self.trackIndices:
                    q.addSamples(src=[rxs[i]],needDil=needDil,primers=["T7"+prefixIn[i]+"X","T7"+prefixOut[i]+"X","MX","T7X","REF"],names=["%s.ext"%names[i]])
                    isave=i+len(input)
                    if isave<len(rxs):
                        # samples restored
                        q.addSamples(src=[rxs[isave]],needDil=needDil/rtSaveDil,primers=["T7"+rxs[isave].name[0]+"X","T7"+("B" if rxs[isave].name[0]=="A" else "W" if rxs[isave].name[0]=="B" else "A")+"X","MX","T7X","REF"])

            if self.doexo:
                print "######## Exo ###########"
                prevvol=rxs[0].volume
                rxs=self.runExo(rxs,incTime=30,inPlace=True)
                exoDil=rxs[0].volume/prevvol
                needDil/=exoDil
                needDil/=7   #  Anecdotal based on Ct's -- large components (MX) reduced by exo digestion
                q.addSamples(src=[rxs[i] for i in self.trackIndices],needDil=needDil,primers=["T7AX","T7BX","MX","T7X","REF"],names=["%s.exo"%names[i] for i in self.trackIndices])
                #exo=self.saveSamps(src=rxs,vol=10*exoDil,dil=2/exoDil,dilutant=reagents.getsample("TE8"),tgt=[Sample("%s.exo"%n,decklayout.SAMPLEPLATE) for n in names])   # Save cDNA product
            else:
                exoDil=1
                exo=[]
        else:
            extdil=1
            extpostdil=1
            exoDil=1

            #user=self.runUser(rxs,vol=20)
            #needDil=needDil*4/5
            #q.addSamples(src=user,needDil=needDil,primers=["T7AX","MX","T7X","REF"],names=["%s.user"%n for n in names])
        
            
        if self.doampure:
            print "######## Ampure Cleanup ###########"
            ratio=1.5
            elutionVol=30
            cleanIn=ext+exo+user
            needDil=needDil*cleanIn[0].volume/elutionVol
            clean=self.runAmpure(src=cleanIn,ratio=ratio,elutionVol=elutionVol)
            q.addSamples(src=[clean[i] for i in self.trackIndices],needDil=needDil,primers=["T7AX","MX","T7X","REF"])
            rxs=rxs+clean   # Use the cleaned products for PCR
            
        totalDil=stopDil*rtDil*extdil*extpostdil*exoDil
        fracRetained=rxs[0].volume/(t7vol*totalDil)
        print "Total dilution from T7 to Pre-pcr Product = %.2f*%.2f*%.2f*%.2f*%.2f = %.2f, fraction retained=%.0f%%"%(stopDil,rtDil,extdil,extpostdil,exoDil,totalDil,fracRetained*100)

        if self.rtSave and not keepCleaved:
            # Remove the extra samples
            assert(len(self.lastSaved)>0)
            rxs=rxs[:len(rxs)-len(self.lastSaved)]
            self.lastSaved=[]

        if len(rxs)>len(input):
            rxs=rxs[0:len(input)]    # Only keep -target products
            prefixOut=prefixOut[0:len(input)]
            prefixIn=prefixIn[0:len(input)]
            
        if self.dopcr:
            print "######### PCR #############"
            print "PCR Volume: %.1f, Dilution: %.1f, volumes available for PCR: [%s]"%(pcrvol, pcrdil,",".join(["%.1f"%r.volume for r in rxs]))
            maxSampleVolume=100  # Maximum sample volume of each PCR reaction (thermocycler limit, and mixing limit)

            initConc=needDil*self.qConc/pcrdil
            if keepCleaved:
                if self.doexo:
                    initConc=initConc*7*self.cleavage		# Back out 7x dilution in exo step, but only use cleaved as input conc
                else:
                    initConc=initConc*self.cleavage		# Only use cleaved as input conc

            gain=pcrgain(initConc,400,cycles)
            finalConc=initConc*gain
            print "Estimated starting concentration in PCR = %.1f nM, running %d cycles -> %.0f nM\n"%(needDil*self.qConc,cycles,finalConc)
            nsplit=int(math.ceil(pcrvol*1.0/maxSampleVolume))
            print "Split each PCR into %d reactions"%nsplit
            srcdil=(1-1.0/3-1.0/4)
            sampNeeded=pcrvol/pcrdil
            if self.rtSave and keepCleaved:
                sampNeeded+=rtSaveVol
            maxvol=max([r.volume for r in rxs]);
            minvol=min([r.volume for r in rxs]);
            predil=min(75/maxvol,(40+1.4*nsplit)/(minvol-sampNeeded))  # Dilute to have 40ul left -- keeps enough sample to allow good mixing
            if keepCleaved and self.rtSave and predil>rtSaveDil:
                print "Reducing predil from %.1f to %.1f (rtSaveDil)"%(predil, rtSaveDil)
                predil=rtSaveDil
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

            pcr=self.runPCR(src=rxs*nsplit,vol=pcrvol/nsplit,srcdil=pcrdil*1.0/predil,ncycles=cycles,primers=["T7%sX"%x for x in (prefixOut if keepCleaved else prefixIn)]*nsplit,usertime=self.usertime if keepCleaved else None,fastCycling=True,inPlace=False)
                
            needDil=finalConc/self.qConc
            print "Projected final concentration = %.0f nM"%(needDil*self.qConc)
            for i in range(len(pcr)):
                pcr[i].conc=Concentration(stock=finalConc,final=None,units='nM')

            if self.pcrSave:
                # Save samples at 1x
                if self.savedilplate:
                    sv=self.saveSamps(src=pcr[:len(rxs)],vol=[x.volume-16.4 for x in pcr[:len(rxs)]],dil=1,plate=decklayout.DILPLATE)
                else:
                    sv=self.saveSamps(src=pcr[:len(rxs)],vol=[x.volume-16.4 for x in pcr[:len(rxs)]],dil=1,plate=decklayout.EPPENDORFS)
                if nsplit>1:
                    # Combine split
                    for i in range(len(rxs),len(rxs)*nsplit):
                        self.e.transfer(pcr[i].volume-16.4,pcr[i],sv[i%len(sv)],mix=(False,i>=len(rxs)*(nsplit-1)))
                    # Correct concentration (above would've assumed it was diluted)
                    for i in range(len(sv)):
                        sv[i].conc=pcr[i].conc

                # for i in range(len(pcr)):
                #     q.addSamples(pcr,needDil,["T7%sX"%prefixOut[i]])

                processEff=0.5   # Estimate of overall efficiency of process
                print "Saved %.2f pmoles of product (%.0f ul @ %.1f nM)"%(sv[0].volume*sv[0].conc.stock/1000,sv[0].volume,sv[0].conc.stock)
                return sv
            else:
                return pcr[:len(rxs)]
        else:
            return rxs
    

    
