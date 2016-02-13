class Reagent:
    def __init__(self,name,plate=Experiment.REAGENTPLATE,well=None,conc=None,hasBeads=False,extraVol=50):
        self.sample=None
        self.name=name
        self.plate=plate
        self.preferredWell=well
        self.conc=conc
        self.hasBeads=hasBeads
        self.extraVol=extraVol

    def get(self):
        if self.sample==None:
            self.sample=Sample.lookup(self.name)
            if self.sample==None:
                print "Creating sample ",self.name
                self.sample=Sample(self.name,self.plate,self.preferredWell,self.conc,hasBeads=self.hasBeads,extraVol=self.extraVol)
                wellname=self.sample.plate.wellname(self.sample.well)
                if self.preferredWell != None and self.preferredWell != wellname:
                    print "WARNING: %s moved from preferred well %s to %s\n"%(self.name,self.preferredWell,wellname)
        return self.sample
    

class Reagents:
    def __getattr__(self,name):
        return self.get(name)

    def isReagent(self,name):
        return name in self.all
    
    def get(self,name):
        return self.all[name].get()
        
    def addReagent(self,name,plate=Experiment.REAGENTPLATE,well=None,conc=None,hasBeads=False,extraVol=50):
        self.all[name]=Reagent(name,plate,well,conc,hasBeads,extraVol)

    def __init__(self):
        self.all={}
        self.addReagent("MT7",well="A1",conc=2.5,extraVol=30)
        self.addReagent("MPosRT",well="B1",conc=2,extraVol=30)
        self.addReagent("MNegRT",well=None,conc=2)
        self.addReagent("MLigAT7",well="D1",conc=3)	# Conc is relative to annealing time (not to post-ligase)
        self.addReagent("MLigBT7W",well="E1",conc=3)
        self.addReagent("MLigase",well="A2",conc=3)

        self.addReagent("Theo",well=None,conc=Concentration(25,7.5,'mM'))
        self.addReagent("MStopXBio",well="B2",conc=2)
        self.addReagent("MStpX",well="C2",conc=2)
        self.addReagent("MQREF",well="D2",conc=10.0/6)
        self.addReagent("MQAX",well="E2",conc=10.0/6)
        self.addReagent("MQBX",well="A3",conc=10.0/6)
        self.addReagent("MPCRAX",well="B3",conc=4.0/3)
        self.addReagent("MPCRBX",well="C3",conc=4.0/3)
        self.addReagent("MQMX",well="D3",conc=10.0/6)
        self.addReagent("MQWX",well="E3",conc=10.0/6)
        self.addReagent("SSD",well="A4",conc=10.0)
        self.addReagent("MLigAT7W",well="B4",conc=3)
        self.addReagent("BeadBuffer",well="C4",conc=1)
        self.addReagent("Dynabeads",well="D4",conc=2,hasBeads=True)
        self.addReagent("MQT7X",well="E4",conc=15.0/9)
        self.addReagent("MStpBeads",well="A5",conc=3.7)
        self.addReagent("QPCRREF",well="B5",conc=Concentration(50,50,'pM'))
        self.addReagent("MLigBT7",well=None,conc=3)
        self.addReagent("MPCRT7X",well="C5",conc=4.0/3)
        self.addReagent("NaOH",well="D5",conc=1.0)
        self.addReagent("MLigBT7WBio",well="E5",conc=3)
        self.addReagent("MLigBT7Bio",well="A6",conc=3)
        self.addReagent("MPCR",well=None,conc=4)
        self.addReagent("MLigB",well=None,conc=3)
        self.UNUSED=Sample("LeakyA1",Experiment.SAMPLEPLATE,"A1",0)
        self.UNUSED2=Sample("LeakyH12",Experiment.SAMPLEPLATE,"H12",0)
