# Setup QPCR experiments
import TRP
import os
import sys
import math

class QSetup(object):
    MINDILVOL=50.0
    MAXDILVOL=150.0
    TGTINVOL=4
    
    def __init__(self,vol=15,maxdil=32):
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
        
    def addSamples(self, src, needDil, primers,nreplicates=1):
        'Add sample(s) to list of qPCRs to do'
        #print "addSamples(src=",src,", needDil=","%.1f"%needDil,", primers=",primers,", nrep=",nreplicates,")"
        self.samples=self.samples+src
        self.needDil=self.needDil+[needDil]*len(src)
        self.primers=self.primers+[primers]*len(src)
        self.nreplicates=self.nreplicates+[nreplicates]*len(src)
        self.stages=self.stages+[int(math.ceil(math.log(needDil)/math.log(self.MAXDIL)))]*len(src)
        self.reuse=self.reuse+[None]*len(src)

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

    def addReferences(self,mindil=1,nsteps=6,dstep=4,nreplicates=1,ref="QPCRREF"):
        'Add all needed references'
        #print "addReferences(mindil=",mindil,", nsteps=",nsteps,", dstep=",dstep,", nrep=", nreplicates, ", ref=",ref,")"
        for i in range(nsteps):
            self.addSamples(src=[ref],needDil=mindil*math.pow(dstep,i),primers=self.allprimers(),nreplicates=nreplicates)
        self.addSamples(src=["Water"],needDil=1,primers=self.allprimers(),nreplicates=nreplicates)

    def run(self,trp):
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
            ptmp=trp.runQPCRDIL(src=[dilProds[i] for i in inds],vol=vol,srcdil=[stageDil[i] for i in inds],tgt=None,dilPlate=True)  
            for i in range(len(inds)):
                dilProds[inds[i]]=ptmp[i]
            needDil=[needDil[i]/stageDil[i] for i in range(len(needDil))]
        self.dilProds=dilProds

        # Setup qPCRs
        for p in self.allprimers():
            # Build list of relevant entries
            ind=[ i for i in range(len(self.samples)) if p in self.primers[i]]
            trp.runQPCR(src=[self.dilProds[i] for i in ind],vol=self.volume,srcdil=10.0/4,primers=[p],nreplicates=[self.nreplicates[i] for i in ind])
