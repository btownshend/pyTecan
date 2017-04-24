# Generic selection progam
import debughook
import math

from Experiment.concentration import Concentration
from Experiment.sample import Sample
from Experiment import worklist, reagents, decklayout
from TRPLib.TRP import TRP
from TRPLib.QSetup import QSetup
from pcrgain import pcrgain

class PGMAnalytic(TRP):
    '''Selection experiment'''
    
    def __init__(self,inputs,doexo=False,doampure=False,directT7=True,templateDilution=0.6,tmplFinalConc=5,saveDil=None,saveRNA=False):
        # Initialize field values which will never change during multiple calls to pgm()
        self.inputs=inputs
        self.doexo=doexo
        self.doampure=doampure
        self.directT7=directT7
        self.tmplFinalConc=tmplFinalConc
        self.templateDilution=templateDilution
        self.saveDil=saveDil
        self.saveRNA=saveRNA
        
        # General parameters
        self.qConc = 0.050			# Target qPCR concentration in nM (corresponds to Ct ~ 10)
        self.pcrSave=True		    # Save PCR products
        self.savedilplate=True	# Save PCR products on dilutions plate
        self.usertime=10				# USER incubation time in minutes
        self.dopcr=False			    # Run PCR of samples
        self.cleavage=0.30			# Estimated cleavage (for computing dilutions of qPCRs)
        
        # Computed parameters
        self.t7vol=20+(5 if saveRNA else 0)
        self.t7dur=30
        self.rtvol=8
        self.pcrdil=80
        self.pcrvol=50
        self.pcrcycles=10
        self.rnaConc=3029*self.tmplFinalConc/(self.tmplFinalConc+54.6)*self.t7dur/60   # Expected concentration of RNA
        
        # Add templates
        if self.directT7:
            self.srcs = self.addTemplates([inp['name'] for inp in inputs],stockconc=tmplFinalConc/templateDilution,finalconc=tmplFinalConc,plate=decklayout.SAMPLEPLATE,looplengths=[inp['looplength'] for inp in inputs],initVol=self.t7vol*templateDilution,extraVol=0)
        else:
            self.srcs = self.addTemplates([inp['name'] for inp in inputs],stockconc=tmplFinalConc/templateDilution,finalconc=tmplFinalConc,plate=decklayout.DILPLATE,looplengths=[inp['looplength'] for inp in inputs],extraVol=15) 
        
    def setup(self):
        TRP.setup(self)
        worklist.setOptimization(True)

    def pgm(self):
        q = QSetup(self,maxdil=16,debug=False,mindilvol=60)
        self.e.addIdleProgram(q.idler)
        input = [s.getsample()  for s in self.srcs]


        # Save RT product from first (uncleaved) round and then use it during 2nd (cleaved) round for ligation and qPCR measurements
        prefixIn=[inp['prefix'] for inp in self.inputs]
        prefixOut=["A" if p=="W" else "B" if p=="A" else "W" if p=="B" else "BADPREFIX" for p in prefixIn]

        qpcrPrimers=["REF","MX","T7X"]
        if "W" in prefixIn+prefixOut:
            qpcrPrimers+=["T7WX"]
        if "A" in prefixIn+prefixOut:
            qpcrPrimers+=["T7AX"]
        if "B" in prefixIn+prefixOut:
            qpcrPrimers+=["T7BX"]
        q.addSamples(decklayout.SSDDIL,1,qpcrPrimers,save=False)   # Negative controls
            
        print "Starting new cleavage round, will add prefix: ",prefixOut

        names=[i.name for i in input]
            
        print "######## T7 ###########"
        print "Inputs:  (t7vol=%.2f)"%self.t7vol
        for inp in input:
            print "    %s:  %.1ful@%.1f nM, use %.1f ul (%.3f pmoles)"%(inp.name,inp.volume,inp.conc.stock,self.t7vol/inp.conc.dilutionneeded(), self.t7vol*inp.conc.final/1000)

        print "input[0]=",input[0]
        needDil = max([inp.conc.final for inp in input])*1.0/self.qConc
        if self.directT7:
            # Just add MT7 and possibly water to each well
            mconc=reagents.getsample("MT7").conc.dilutionneeded()
            for i in range(len(input)):
                watervol=self.t7vol*(1-1/mconc)-input[i].volume
                if watervol>0.1:
                    self.e.transfer(watervol,decklayout.WATER,input[i],mix=(False,False))
                self.e.transfer(self.t7vol/mconc,reagents.getsample("MT7"),input[i],mix=(False,False))
                assert(input[i].volume==self.t7vol)
            rxs=input
        else:
            rxs = self.runT7Setup(src=input,vol=self.t7vol,srcdil=[inp.conc.dilutionneeded() for inp in input])
        print "input[0]=",input[0]
            
        #for i in range(len(rxs)):
        #   q.addSamples(src=rxs],needDil=needDil,primers=["T7"+prefixIn[i]+"X","MX","T7X","REF"],names=["%s.T-"%names[i]])
        
        self.runT7Pgm(dur=self.t7dur,vol=self.t7vol)
        print "Template conc=%.1f nM, estimated RNA concentration in T7 reaction at %.0f nM"%(self.tmplFinalConc,self.rnaConc)
        
        print "######## Stop ###########"
        self.e.lihahome()

        print "Have %.1f ul before stop"%rxs[0].volume
        preStopVolume=rxs[0].volume
        self.addEDTA(tgt=rxs,finalconc=2)	# Stop to 2mM EDTA final
        
        stopDil=rxs[0].volume/preStopVolume

        if self.saveRNA:
            self.saveSamps(src=rxs,vol=5,dil=2,plate=decklayout.DILPLATE,dilutant=reagents.getsample("TE8"),mix=(False,False))   # Save to check [RNA] on Qubit, bioanalyzer

        stop=[ "A-Stop" if n=="A" else "B-Stop" if n=="B" else "W-Stop" if n=="W" else "BADPREFIX" for n in prefixOut]

        for i in range(len(rxs)):
            rxs[i].name=rxs[i].name+"."+stop[i]

        needDil = self.rnaConc/self.qConc/stopDil
        #q.addSamples(src=rxs,needDil=needDil,primers=["T7AX","MX","T7X","REF"],names=["%s.stopped"%r.name for r in rxs])
        
        print "######## RT  Setup ###########"
        rtDil=4
        hiTemp=95
        rtDur=20

        rxin=rxs
        rxs=self.runRT(src=rxs,vol=self.rtvol,srcdil=rtDil,heatInactivate=True,hiTemp=hiTemp,dur=rtDur,incTemp=50,stop=[reagents.getsample(s) for s in stop])    # Heat inactivate also allows splint to fold
        print "RT volume= ",[x.volume for x in rxs]
        for r in rxin:
            if r.volume>20:
                print "Have more T7 reaction remaining than needed: %s has %.1f ul"%(r.name,r.volume)

        needDil /= rtDil
        rtPostDil=5
        if rtPostDil!=1:
            self.diluteInPlace(tgt=rxs,dil=rtPostDil)
            needDil /= rtPostDil
        #q.addSamples(src=rxs,needDil=needDil,primers=["T7AX","MX","REF"],names=["%s.rt"%r.name for r in rxs])

        print "######## Ligation setup  ###########"
        extdil=5.0/4
        reagents.getsample("MLigase").conc=Concentration(5)
        extvol=20;
        print "Extension volume=",extvol
        rxs=self.runLig(rxs,vol=extvol)

        print "Ligation volume= ",[x.volume for x in rxs]
        needDil=needDil/extdil
        extpostdil=4
        if extpostdil>1:
            print "Dilution after extension: %.2f"%extpostdil
            self.diluteInPlace(tgt=rxs,dil=extpostdil)
            needDil=needDil/extpostdil
            if not self.doexo:
                self.pcrdil=self.pcrdil/extpostdil

        if self.saveDil is not None:
            ext=self.saveSamps(src=rxs,vol=3,dil=self.saveDil,dilutant=reagents.getsample("TE8"),tgt=[Sample("%s.ext"%n,decklayout.DILPLATE) for n in names],mix=(False,True))   # Save cDNA product for subsequent NGS
            for i in range(len(rxs)):
                q.addSamples(src=[ext[i]],needDil=needDil/self.saveDil,primers=["T7"+prefixIn[i]+"X","T7"+prefixOut[i]+"X","MX","T7X","REF"],names=["%s.ext"%names[i]])
        else:
            for i in range(len(rxs)):
                q.addSamples(src=[rxs[i]],needDil=needDil,primers=["T7"+prefixIn[i]+"X","T7"+prefixOut[i]+"X","MX","T7X","REF"],names=["%s.ext"%names[i]])

        if self.doexo:
            print "######## Exo ###########"
            prevvol=rxs[0].volume
            rxs=self.runExo(rxs,incTime=30,inPlace=True)
            exoDil=rxs[0].volume/prevvol
            needDil/=exoDil
            needDil/=7   #  Anecdotal based on Ct's -- large components (MX) reduced by exo digestion
            q.addSamples(src=rxs,needDil=needDil,primers=["T7AX","T7BX","MX","T7X","REF"],names=["%s.exo"%names[i] for i in range(len(rxs))])
            #exo=self.saveSamps(src=rxs,vol=10*exoDil,dil=2/exoDil,dilutant=reagents.getsample("TE8"),tgt=[Sample("%s.exo"%n,decklayout.SAMPLEPLATE) for n in names])   # Save cDNA product
        else:
            exoDil=1
            exo=[]
        
        if self.doampure:
            print "######## Ampure Cleanup ###########"
            ratio=1.5
            elutionVol=30
            cleanIn=ext+exo+user
            needDil=needDil*cleanIn[0].volume/elutionVol
            clean=self.runAmpure(src=cleanIn,ratio=ratio,elutionVol=elutionVol)
            q.addSamples(src=[clean[i] for i in range(len(rxs))],needDil=needDil,primers=["T7AX","MX","T7X","REF"])
            rxs=rxs+clean   # Use the cleaned products for PCR
            
        totalDil=stopDil*rtDil*rtPostDil*extdil*extpostdil*exoDil
        fracRetained=rxs[0].volume/(self.t7vol*totalDil)
        print "Total dilution from T7 to Pre-pcr Product = %.2f*%.2f*%.2f*%.2f*%.2f*%.2f = %.2f, fraction retained=%.0f%%"%(stopDil,rtDil,rtPostDil,extdil,extpostdil,exoDil,totalDil,fracRetained*100)

        if self.dopcr:
            print "######### PCR #############"
            print "PCR Volume: %.1f, Dilution: %.1f, volumes available for PCR: [%s]"%(self.pcrvol, self.pcrdil,",".join(["%.1f"%r.volume for r in rxs]))
            maxSampleVolume=100  # Maximum sample volume of each PCR reaction (thermocycler limit, and mixing limit)

            initConc=needDil*self.qConc/self.pcrdil
            if self.doexo:
                initConc=initConc*7*self.cleavage		# Back out 7x dilution in exo step, but only use cleaved as input conc
            else:
                initConc=initConc*self.cleavage		# Only use cleaved as input conc

            gain=pcrgain(initConc,400,self.pcrcycles)
            finalConc=initConc*gain
            print "Estimated starting concentration in PCR = %.1f nM, running %d cycles -> %.0f nM\n"%(needDil*self.qConc,self.pcrcycles,finalConc)
            pcr=self.runPCR(src=rxs,vol=self.pcrvol,srcdil=self.pcrdil,ncycles=self.pcrcycles,primers=["T7%sX"%x for x in prefixOut],usertime=self.usertime,fastCycling=True)
                
            needDil=finalConc/self.qConc
            pcrpostdil=2
            if pcrpostdil>1:
                self.diluteInPlace(pcr,pcrpostdil)
                needDil=needDil/pcrpostdil
            print "Projected final concentration = %.0f nM (after %.1fx dilution)"%(needDil*self.qConc,pcrpostdil)
            for i in range(len(pcr)):
                pcr[i].conc=Concentration(stock=finalConc/pcrpostdil,final=None,units='nM')

            if self.pcrSave:
                # Save samples at 1x
                if self.savedilplate:
                    sv=self.saveSamps(src=pcr[:len(rxs)],vol=[x.volume-16.4 for x in pcr[:len(rxs)]],dil=1,plate=decklayout.DILPLATE)
                else:
                    sv=self.saveSamps(src=pcr[:len(rxs)],vol=[x.volume-16.4 for x in pcr[:len(rxs)]],dil=1,plate=decklayout.EPPENDORFS)

                # for i in range(len(pcr)):
                #     q.addSamples(pcr,needDil,["T7%sX"%prefixOut[i]])

                processEff=0.5   # Estimate of overall efficiency of process
                print "Saved %.2f pmoles of product (%.0f ul @ %.1f nM)"%(sv[0].volume*sv[0].conc.stock/1000,sv[0].volume,sv[0].conc.stock)

        print "######### qPCR ###########"
        #q.addReferences(mindil=4,nsteps=6,primers=["T7X","MX","T7AX"])
        q.run(confirm=False)
