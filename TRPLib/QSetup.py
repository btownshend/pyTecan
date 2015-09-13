# Setup QPCR experiments
import TRP
import os
import sys
import math
from Experiment.experiment import Experiment
from Experiment.sample import Sample
from TRPLib.TRP import uniqueTargets, diluteName

class QSetup(object):
    MINDILVOL=50.0
    MAXDILVOL=150.0
    TGTINVOL=4
    
    def __init__(self,trp,vol=15,maxdil=32,debug=False):
        'Create a new QPCR setup structure'
        self.volume=vol
        self.samples=[]
        self.needDil=[]
        self.primers=[]
        self.nreplicates=[]
        self.dilProds=[]
        self.reuse=[]   # Index of prior dilution that can be used as input to this one; otherwise None
        self.stages=[]
        self.MAXDIL=maxdil
        self.trp=trp
        self.debug=debug
        
    def addSamples(self, src, needDil, primers,nreplicates=1,names=None):
        'Add sample(s) to list of qPCRs to do'
        saveDil=min(needDil,self.MAXDIL)
        if needDil/saveDil>1 and needDil/saveDil<2:
            saveDil=math.sqrt(needDil)
        saveVol=max(self.MINDILVOL/saveDil,self.TGTINVOL)
        if names==None:
            tgt=[diluteName(src[i],saveDil) for i in range(len(src))]
        else:
            tgt=[diluteName(names[i],saveDil) for i in range(len(src))]
        sv=tgt
        for i in range(len(tgt)):
            t=Sample.lookup(tgt[i])
            if t==None or t.volume==0:
                #print "Save ",src[i]
                svtmp=self.trp.runQPCRDIL(src=[src[i]],vol=saveVol*saveDil,srcdil=saveDil,tgt=[tgt[i]],dilPlate=True)  
                #svtmp=self.trp.saveSamps(src=[src[i]],tgt=[tgt[i]],vol=saveVol,dil=saveDil,plate=Experiment.DILPLATE,mix=(False,False))
                sv[i]=svtmp[0]
        if self.debug:
            print "addSamples(src=",src,", tgt=",tgt,", needDil=","%.1f"%needDil,", primers=",primers,", nrep=",nreplicates,")"
        needDil=needDil/saveDil
        self.samples=self.samples+sv
        self.needDil=self.needDil+[needDil]*len(sv)
        self.primers=self.primers+[primers]*len(sv)
        self.nreplicates=self.nreplicates+[nreplicates]*len(sv)
        self.stages=self.stages+[int(math.ceil(math.log(needDil)/math.log(self.MAXDIL)))]*len(sv)
        self.reuse=self.reuse+[None]*len(sv)

    def findReuses(self):
        'Find any prior dilutions that can be reused'
        maxstages=max(self.stages)
        for j in range(len(self.samples)):
            for i in range(len(self.samples)):
                # Check if we can reuse i to form j
                if i!=j and self.samples[i]==self.samples[j] and self.needDil[i]<self.needDil[j] and self.needDil[i]>1:
                    # Possible reuse
                    # Check if we already have a better one
                    if self.reuse[j]!=None and self.needDil[self.reuse[j]]>self.needDil[i]:
                        continue
                    # Check if it would increase number of stages
                    stages=int(math.ceil(math.log(self.needDil[j]/self.needDil[i])/math.log(self.MAXDIL))+self.stages[i])
                    if stages>maxstages:
                        continue
                    print "Reuse %s@%f to form %s@%f"%(self.samples[i],self.needDil[i],self.samples[j],self.needDil[j])
                    self.reuse[j]=i
                    self.stages[j]=stages
            totalDil=self.needDil[j]
            stages=self.stages[j]
            if self.reuse[j] != None:
                totalDil = totalDil / self.needDil[self.reuse[j]]
                stages = stages - self.stages[self.reuse[j]]
            if stages>1:
                print "Need to form %s@%f by diluting %f in %d stages "%(self.samples[j],self.needDil[j],totalDil,stages)
                d=1
                if self.reuse[j]!=None:
                    d=self.needDil[self.reuse[j]]
                for k in range(stages-1):
                    d=min(d*self.MAXDIL,totalDil)
                    self.addSamples([self.samples[j]],d,[])	# Add extra intermediate that can be reused
                    if k==0:
                        self.reuse[-1]=self.reuse[j]
                    else:
                        self.reuse[-1]=len(self.samples)-2
                self.reuse[j]=len(self.samples)-1
                
        for i in range(len(self.samples)):
            print "%d: %s@%f"%(i,self.samples[i],self.needDil[i]),
            if self.reuse[i]!=None:
                print ", use %d with additional %f dilution"%(self.reuse[i], self.needDil[i]/self.needDil[self.reuse[i]]),
            print " [%d stages]"%self.stages[i]
                
    def allprimers(self):
        return set([p for sublist in self.primers for p in sublist])

    def addReferences(self,mindil=1,nsteps=6,dstep=4,nreplicates=1,ref="QPCRREF",primers=None):
        'Add all needed references'
        #print "addReferences(mindil=",mindil,", nsteps=",nsteps,", dstep=",dstep,", nrep=", nreplicates, ", ref=",ref,")"
        if primers==None:
            primers=self.allprimers()
        for i in range(nsteps):
            self.addSamples(src=[ref],needDil=mindil*math.pow(dstep,i),primers=primers,nreplicates=nreplicates)
        self.addSamples(src=["SSDDil"],needDil=1,primers=self.allprimers(),nreplicates=nreplicates)

    def run(self):
        'Run the dilutions and QPCR setup'
        #print "run()"

        # Find reuses
        #self.findReuses()   # Not used yet

        # Make dilutions
        # Store resulting diluted products in self.dilProds
        dilProds=self.samples
        needDil=self.needDil
        for stage in range(4):
            stageDil=needDil[:]
            for i in range(len(stageDil)):
                if stageDil[i]>self.MAXDIL:
                    nstages=math.ceil(math.log(stageDil[i])/math.log(self.MAXDIL))
                    stageDil[i]=math.pow(stageDil[i],1/nstages)
            inds=[i for i in range(len(stageDil)) if stageDil[i]>1.1]
            if len(inds)==0:
                break
            print "Dilution stage ",stage,": ",[round(x,1) for x in stageDil if x>1.1]
            if stage>0:
                vol=[self.MAXDILVOL for i in inds]
            else:
                vol=[min(self.MAXDILVOL,max(self.MINDILVOL,x*self.TGTINVOL)) for x in [stageDil[i] for i in inds]]  # Make sure there's enough for  qPCR (6ul each) or next dilution (typicaly 5ul) and leaves 15 at end
                print "vol=",vol
            ptmp=self.trp.runQPCRDIL(src=[dilProds[i] for i in inds],vol=vol,srcdil=[stageDil[i] for i in inds],tgt=None,dilPlate=True)  
            for i in range(len(inds)):
                dilProds[inds[i]]=ptmp[i]
            needDil=[needDil[i]/stageDil[i] for i in range(len(needDil))]
        self.dilProds=dilProds

        # Setup qPCRs
        for p in self.allprimers():
            # Build list of relevant entries
            ind=[ i for i in range(len(self.samples)) if p in self.primers[i]]
            self.trp.runQPCR(src=[self.dilProds[i] for i in ind],vol=self.volume,srcdil=10.0/4,primers=[p],nreplicates=[self.nreplicates[i] for i in ind])
