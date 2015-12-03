class JobQueue(object):
    def __init__(self):
        self.nextID=1
        self.jobs={}
        self.debug=False
        
    def len(self):
        return len(self.jobs)
    
    def getID(self):
        id=self.nextID
        self.nextID+=1
        return id
    
    def findPriors(self,sample,known):
        'Return any prior job entries that affect sample'
        priors=[]
        for i,j in self.jobs.iteritems():
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

    def addTransfer(self,volume,src,dest,prereqs=[]):
        'Add a transfer operation to the queue, return the ID of the job (for use in prereqs)'
        id=self.getID()
        priors=self.findPriors(src,prereqs)
        self.jobs[id]={'type':'transfer','volume':volume,'src':src,'dest':dest,'prereqs':set(prereqs).union(priors)}
        return id
    
    def addMultiTransfer(self,volume,src,dest,prereqs=[]):
        'Add a transfer operation to the queue, return the ID of the job (for use in prereqs)'
        id=self.getID()
        priors=self.findPriors(src,prereqs)
        self.jobs[id]={'type':'multitransfer','volume':volume,'src':src,'dest':dest,'prereqs':set(prereqs).union(priors)}
        return id
    
    def addShake(self,sample,prereqs=[]):
        id=self.getID()
        priors=self.findPriors(sample,prereqs)
        self.jobs[id]={'type':'shake','sample':sample,'prereqs':set(prereqs).union(priors)}
        return id
    
    def dump(self):
        'Dump queue'
        for id,j in self.jobs.iteritems():
            print id,j
            
    def getJob(self):
        'Return the next job on the queue to execute, removing it from queue'

        # Remove any shake jobs that are unneeded
        for id,j in self.jobs.items():
            if j['type']=='shake' and len(j['prereqs'])==0 and j['sample'].isMixed:
                self.removeJob(id)

        for id in self.jobs:
            j=self.jobs[id]
            if j['type']!='transfer' or len(j['prereqs'])>0 or  j['src'].plate.curloc!='Home' or  j['dest'].plate.curloc!='Home':
                #if j['type']=='transfer':
                #   print "Can't execute job ",id,": ",j,", curlocs=",j['src'].plate.curloc,", ",j['dest'].plate.curloc
                continue
            return id

        for id,j in self.jobs.iteritems():
            if j['type']!='multitransfer' or len(j['prereqs'])>0 or  j['src'].plate.curloc!='Home'  or  j['dest'].plate.curloc!='Home':
                continue
            # Combine with all other multitransfers from same src
            alldest=[]
            allvol=[]
            for id2,j2 in self.jobs.items():
                if j2['type']!='multitransfer' or len(j2['prereqs'])>0 or j['src']!=j2['src']:
                    continue
                alldest.append(j2['dest'])
                allvol.append(j2['volume'])
                self.removeJob(id2)
            combined=self.addMultiTransfer(volume=allvol,src=j['src'],dest=alldest,prereqs=[])
            return combined

        for id in self.jobs:
            j=self.jobs[id]
            if j['type']!='shake' or len(j['prereqs'])>0 or not j['sample'].plate.curloc=='Home':
                continue
            return id
        # Nothing to do
        return None

    def execJob(self,e,id):
        job=self.jobs[id]
        if self.debug:
            print "execJob(",id,"): ",
        if job['type']=='shake':
            if not job['sample'].isMixed:
                if self.debug:
                    print "shaking ",job['sample'].plate," because ",job['sample'].name," is not mixed.",
                e.shake(job['sample'].plate)
            else:
                if self.debug:
                    print "no need to shake ",job['sample'].plate," because ",job['sample'].name," is already mixed.",
        elif  job['type']=='transfer':
            if self.debug:
                print " transfer(",job['volume'],", ",job['src'].name,",",job['dest'].name,")",
            e.transfer(job['volume'],job['src'],job['dest'])
        elif  job['type']=='multitransfer':
            if self.debug:
                print "multitransfer(",job['volume'],", ",job['src'].name,",".join([x.name for x in job['dest']]),")",
            e.multitransfer(job['volume'],job['src'],job['dest'])
        else:
            assert(False)
        if self.debug:
            print
        self.removeJob(id)

    def removeJob(self,id):
        for ik,k in self.jobs.iteritems():
            k['prereqs']=k['prereqs'].difference([id])
        self.jobs.pop(id)
        #print "Removed job ",id
            
