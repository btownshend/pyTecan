# Setup QPCR experiments
import TRP
import os
import sys
import math

class QSetup(object):

    def __init__(self,vol=15):
        'Create a new QPCR setup structure'
        self.volume=vol
        self.samples=[]
        self.needDil=[]
        self.primers=[]
        self.nreplicates=[]
        self.dilProds=[]
        
    def addSamples(self, src, needDil, primers,nreplicates=1):
        'Add sample(s) to list of qPCRs to do'
        print "addSamples(src=",src,", needDil=",needDil,", primers=",primers,", nrep=",nreplicates,")"
        self.samples=self.samples+src
        self.needDil=self.needDil+[needDil]*len(src)
        self.primers=self.primers+[primers]*len(src)
        self.nreplicates=self.nreplicates+[nreplicates]*len(src)

    def allprimers(self):
        return set([p for sublist in self.primers for p in sublist])

    def addReferences(self,mindil=1,nsteps=6,dstep=4,nreplicates=1,ref="QPCRREF"):
        'Add all needed references'
        print "addReferences(mindil=",mindil,", nsteps=",nsteps,", dstep=",dstep,", nrep=", nreplicates, ", ref=",ref,")"
        for i in range(nsteps):
            self.addSamples(src=[ref],needDil=mindil*math.pow(dstep,i),primers=self.allprimers(),nreplicates=nreplicates)
        self.addSamples(src=["Water"],needDil=1,primers=self.allprimers(),nreplicates=nreplicates)

    def run(self,trp):
        'Run the dilutions and QPCR setup'
        print "run()"

        # Make dilutions
        # Store resulting diluted products in self.dilProds
        dilProds=self.samples
        needDil=self.needDil
        for stage in range(4):
            stageDil=needDil[:]
            for i in range(len(stageDil)):
                if stageDil[i]>25:
                    nstages=math.ceil(math.log(stageDil[i])/math.log(25))
                    stageDil[i]=math.pow(stageDil[i],1/nstages)
            inds=[i for i in range(len(stageDil)) if stageDil[i]!=1]
            if len(inds)==0:
                break
            print "Dilution stage ",stage,": ",[round(x,1) for x in stageDil if x!=1]
            vol=[max(60,x*5) for x in [stageDil[i] for i in inds]]  # Make sure there's enough for  qPCR (6ul each) or next dilution (typicaly 5ul) and leaves 15 at end
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
