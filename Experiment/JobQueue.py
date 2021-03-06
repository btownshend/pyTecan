"""Queue of jobs to be executed during idle times"""
from typing import List

from .experiment import Experiment
from . import logging
from .sample import Sample

# Annotation types
SampleListType = List[Sample]
FloatListType = List[float]

# noinspection PyShadowingBuiltins
class JobQueue(object):
    """Queue of jobs to be executed during idle times"""
    def __init__(self):
        self.nextID=1
        self.jobs={}
        self.debug=False
        self.runningJob=None	# Currently executing job

    def len(self):
        return len(self.jobs)

    def getID(self)->int:
        id=self.nextID
        self.nextID+=1
        return id

    def findPriors(self,sample:Sample,known):
        """Return any prior job entries that affect sample"""
        priors=[]
        for i,j in self.jobs.items():
            if j['type']=='transfer' and j['dest']==sample:
                priors.append(i)
            elif j['type']=='multitransfer' and j['dest']==sample:
                priors.append(i)
            elif j['type']=='shake' and j['sample']==sample:
                priors.append(i)
        priors=set(priors).difference(known)
        #if len(priors)>0:
        #print 'Adding prior dependences for sample ', sample,': ',priors
        return priors

    def addTransfer(self, volume:float, src:Sample, dest:Sample, prereqs=None):
        """Add a transfer operation to the queue, return the ID of the job (for use in prereqs)"""
        if prereqs is None:
            prereqs = []
        id=self.getID()
        priors=self.findPriors(src,prereqs)
        self.jobs[id]={'type':'transfer','volume':volume,'src':src,'dest':dest,'prereqs':set(prereqs).union(priors)}
        return id

    def addMultiTransfer(self, volume: FloatListType, src:Sample, dest:SampleListType, prereqs=None):
        """Add a transfer operation to the queue, return the ID of the job (for use in prereqs)"""
        if prereqs is None:
            prereqs = []
        id=self.getID()
        priors=self.findPriors(src,prereqs)
        self.jobs[id]={'type':'multitransfer','volume':volume,'src':src,'dest':dest,'prereqs':set(prereqs).union(priors)}
        return id

    def addShake(self, sample, prereqs=None):
        if prereqs is None:
            prereqs = []
        id=self.getID()
        priors=self.findPriors(sample,prereqs)
        self.jobs[id]={'type':'shake','sample':sample,'prereqs':set(prereqs).union(priors)}
        return id

    def dump(self):
        """Dump queue"""
        for id,j in self.jobs.items():
            print(id,j)

    def getJob(self):
        """Return the next job on the queue to execute, removing it from queue"""

        if self.runningJob is not None:
            logging.warning("Call of getJob() while a job is running - returning None")
            return None

        # Remove any shake jobs that are unneeded
        for id in list(self.jobs.keys()):   # Make copy so that we can handle deletes in loop
            if id not in self.jobs:
                continue  # Previously deleted
            j=self.jobs[id]
            if j['type']=='shake' and len(j['prereqs'])==0 and j['sample'].isMixed() and not Experiment.shakerIsActive():
                #print "Removing unneeded shake job ",id
                self.removeJob(id)

        for id in self.jobs:
            j=self.jobs[id]
            if j['type']!='transfer' or len(j['prereqs'])>0 or  j['src'].plate.location!=j['src'].plate.homeLocation or j['dest'].plate.location!=j['dest'].plate.homeLocation:
                #if j['type']=='transfer':
                #   print "Can't execute job ",id,": ",j,", curlocs=",j['src'].plate.curloc,", ",j['dest'].plate.curloc
                continue
            return id

        for id,j in self.jobs.items():
            if j['type']!='multitransfer' or len(j['prereqs'])>0 or  j['src'].plate.location!=j['src'].plate.homeLocation  or  j['dest'].plate.location!=j['dest'].plate.homeLocation:
                continue
            # Combine with all other multitransfers from same src
            alldest=[]
            allvol=[]
            for id2 in list(self.jobs.keys()):  # Make copy so we can delete
                if id2 not in self.jobs:
                    continue   # Previously deleted
                j2=self.jobs[id2]
                if j2['type']!='multitransfer' or len(j2['prereqs'])>0 or j['src']!=j2['src']:
                    continue
                alldest.append(j2['dest'])
                allvol.append(j2['volume'])
                self.removeJob(id2)
            combined=self.addMultiTransfer(volume=allvol,src=j['src'],dest=alldest,prereqs=[])
            return combined

        for id in self.jobs:
            j=self.jobs[id]
            if j['type']!='shake' or len(j['prereqs'])>0 or not j['sample'].plate.location==j['sample'].plate.homeLocation or Experiment.shakerIsActive():
                continue
            return id
        # Nothing to do
        return None

    def execJob(self,e,id):
        job=self.jobs[id]
        self.runningJob=job
        if self.debug:
            print("execJob(",id,"): ", end=' ')
        if job['type']=='shake':
            if job['sample'].isMixed():
                if self.debug:
                    print("no need to shake ",job['sample'].plate," because ",job['sample'].name," is already mixed.", end=' ')
            elif job['sample'].plate.plateType.maxspeeds is None:
                if self.debug:
                    print("Not shaking ",job['sample'].plate," because it is not compatible with shaker.", end=' ')
            elif job['sample'].hasBeads:
                if self.debug:
                    print("Not shaking ",job['sample'].name," because it has beads")
            else:
                if self.debug:
                    print("shaking ",job['sample'].plate," because ",job['sample'].name," is not mixed.", end=' ')
                e.shake(job['sample'].plate)
        elif  job['type']=='transfer':
            if self.debug:
                print(" transfer(",job['volume'],", ",job['src'].name,",",job['dest'].name,")", end=' ')
            e.transfer(job['volume'],job['src'],job['dest'],(True,False))
        elif  job['type']=='multitransfer':
            if self.debug:
                print("multitransfer(",job['volume'],", ",job['src'].name,",".join([x.name for x in job['dest']]),")", end=' ')
            e.multitransfer(job['volume'],job['src'],job['dest'])
        else:
            logging.error("Internal error")

        if self.debug:
            print()
        self.removeJob(id)
        self.runningJob=None

    def removeJob(self,id):
        for _,k in self.jobs.items():
            k['prereqs']=k['prereqs'].difference([id])
        self.jobs.pop(id)
        #print "Removed job ",id

