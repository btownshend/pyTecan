import argparse
import os
import sys

from ..Experiment import globals
from ..Experiment import worklist, reagents, decklayout, clock, logging, thermocycler
from ..Experiment.concentration import Concentration
from ..Experiment.experiment import Experiment
from ..Experiment.plate import Plate
from ..Experiment.sample import Sample
from ..Experiment.db import db
from ..Experiment.config import Config
from ..Experiment.liquidclass import SURFACEREMOVE

from . import trplayout

maxVolumePerWell=150

trplayout.initWellKnownSamples()

# Ingredients based on volumes in spreadsheet to make 100ul  (can be scaled arbitrarily)
rp=trplayout.REAGENTPLATE
reagents.add("MT7", plate=rp, well="A1", conc=2.5, extraVol=30, ingredients={'glycerol': 0.5 * 37.5, 'SuperaseIn': 0.5 * 12.5, 'T7': 0.5 * 25, 'T7-ABE':62.5})
reagents.add("MPosRT",plate=rp,well="B1",conc=2,extraVol=30,ingredients={'Omniscript':0.5*10,'glycerol':0.5*10,'RT-ABE':90})
reagents.add("MExo",plate=rp,well="C1",conc=5,extraVol=30,ingredients={'ExoI':0.5*55,'ExoIII':0.5*7,'glycerol':0.5*(55+7),'NEBuffer1':10,'Water':28})
reagents.add("TheoX",plate=rp,well="C1",conc=4)
reagents.add("MTaqU",plate=rp,well="C1",conc=2,ingredients={'Taq':0.5*1,'glycerol':0.5*1,'TAQ-ABE':51,'Water':48})
reagents.add("MTaqC",plate=rp,well="D1",conc=2,ingredients={'Taq':0.5*1,'USER':0.5*2,'glycerol':0.5*3,'TAQ-ABE':51,'Water':46})
reagents.add("MTaqR",plate=rp,well="C2",conc=2,ingredients={'Taq':0.5*1,'glycerol':0.5*1,'TAQ-ABE':51,'Water':48})
reagents.add("MLigase",plate=rp,well="E1",conc=5,extraVol=50,ingredients={'T4DNALigase':0.5*2.50,'glycerol':0.5*2.50,'T4-ABE':97.47})

reagents.add("Unclvd-Stop",plate=rp,well="A2",conc=Concentration(4,1,'uM'),extraVol=30)
reagents.add("MTaqBar",plate=rp,well="B2",conc=2,ingredients={'Taq':0.5*1,'glycerol':0.5*1,'TAQ-ABE':51,'Water':48})
reagents.add("MKapaBar",plate=rp,well="B2",conc=2,ingredients={'Kapa':0.5*1,'glycerol':0.5*1,'TAQ-ABE':51,'Water':48})  # FIXME: These numbers are wrong (were for Taq)
reagents.add("MUser",plate=rp,well="B2",conc=5,extraVol=30,ingredients={'USER':0.5*2.5,'glycerol':0.5*2.5,'CutSmart':25,'Water':72.5})
reagents.add("Ampure",plate=rp,well="C2",conc=None,hasBeads=True)
reagents.add("EtOH80",plate=rp,well="D2")
reagents.add("BT88",plate=rp,well="E2",conc=Concentration(4000,800,'nM'),extraVol=30)

reagents.add("B-Stop",plate=rp,well="A3",conc=Concentration(4,1,'uM'),extraVol=30)
reagents.add("W-Stop",plate=rp,well="B3",conc=Concentration(4,1,'uM'),extraVol=30)
reagents.add("A-Stop",plate=rp,well="C3",conc=Concentration(4,1,'uM'),extraVol=30)
reagents.add("T7W-Stop",plate=rp,well="D3",conc=Concentration(4,1,'uM'),extraVol=30)
reagents.add("Z-Stop",plate=rp,well="D3",conc=Concentration(4,1,'uM'),extraVol=30)

reagents.add("SSD",plate=rp,well="A4",conc=10.0)
reagents.add("EDTA",plate=rp,well="A4",conc=Concentration(20,2,'mM'),extraVol=30)
#reagents.add("NaOH",well="B4",conc=1.0)
reagents.add("BeadBuffer",plate=rp,well="C4",conc=1)
#reagents.add("Dynabeads",well="D4",conc=4,hasBeads=True)
reagents.add("TE8",plate=rp,well="E4",conc=None)

reagents.add("EvaGreen",plate=rp,well="A5",conc=2)
reagents.add("EvaUSER",plate=rp,well="A5",conc=2,extraVol=100)
reagents.add("P-BCFwd",plate=rp,well="B5",conc=4)
reagents.add("P-T7BX",plate=rp,well="C5",conc=4)
reagents.add("P-T7ZX",plate=rp,well="C5",conc=4)
reagents.add("P-T7WX",plate=rp,well="D5",conc=4)
reagents.add("P-T7AX",plate=rp,well="E5",conc=4)
reagents.add("P-AX",plate=rp,well="E5",conc=4)

reagents.add("P-T7X",plate=rp,well="A6",conc=4)
reagents.add("P-WX",plate=rp,well="B6",conc=4)
reagents.add("P-BX",plate=rp,well="C6",conc=4)
reagents.add("P-BCRev",plate=rp,well="C6",conc=4)
reagents.add("P-ZX",plate=rp,well="C6",conc=4)
reagents.add("P-MX",plate=rp,well="D6",conc=4)
reagents.add("P-REF",plate=rp,well="E6",conc=4)

# Targets
reagents.add("T1",plate=rp,well='B4',conc=Concentration(10.0/3,1.0,'x'),extraVol=30)  # New targets (9/2017)
reagents.add("T1b",plate=rp,well='B4',conc=Concentration(10.0/3,1.0,'x'),extraVol=30)  # New targets (10/17/2017)
reagents.add("T1c",plate=rp,well='B4',conc=Concentration(10.0/3,1.0,'x'),extraVol=30)  # New targets (4/17/18)
reagents.add("T1d",plate=rp,well='B4',conc=Concentration(10.0/3,1.0,'x'),extraVol=30)  # New targets (7/10/18)
reagents.add("T1e",plate=rp,well='B4',conc=Concentration(10.0/3,1.0,'x'),extraVol=30)  # New targets (10/5/18)
reagents.add("T1f",plate=rp,well='B4',conc=Concentration(10.0/3,1.0,'x'),extraVol=30)  # New targets (10/9/18)
reagents.add("T1g",plate=rp,well='B4',conc=Concentration(10.0/3,1.0,'x'),extraVol=30)  # New targets (10/20/18)
reagents.add("T1h",plate=rp,well='B4',conc=Concentration(10.0/3,1.0,'x'),extraVol=30)  # New targets (11/?/18)
reagents.add("T1i",plate=rp,well='B4',conc=Concentration(10.0/3,1.0,'x'),extraVol=30)  # New targets (11/30/18)
reagents.add("T2",plate=rp,well='C4',conc=Concentration(10.0,1.0,'mM'),extraVol=30) # Acetyl CoA
reagents.add("T2b",plate=rp,well='C4',conc=Concentration(10.0/3,1.0,'x'),extraVol=30) # Acetyl CoA + Trans-Zeatin + Redox
reagents.add("T3",plate=rp,well=None,conc=Concentration(10.0/3,1.0,'x'),extraVol=30) # BIAs
reagents.add("T3d",plate=rp,well='E3',conc=Concentration(10.0/3,1.0,'x'),extraVol=30) # BIAs less S-Reticuline
reagents.add("T3e",plate=rp,well='E3',conc=Concentration(10.0/3,1.0,'x'),extraVol=30) # BIAs less S-Reticuline, reduced Noscapine (9/17)
reagents.add("T3f",plate=rp,well='E3',conc=Concentration(10.0/3,1.0,'x'),extraVol=30) # BIAs with 0.1uM S-Reticuline, 20uM Noscapine (10/17/17)
reagents.add("T3g",plate=rp,well='E3',conc=Concentration(10.0/3,1.0,'x'),extraVol=30) #Reduced Trans-Zeatin (12/9/17)
reagents.add("T6",plate=rp,well='D4',conc=Concentration(10.0/3,1.0,'x'),extraVol=30) # Redox
reagents.add("T25",plate=rp,well='C4',conc=Concentration(10.0/3,1.0,'x'),extraVol=30) # Acetyl CoA + Trans-Zeatin
#reagents.add("T25T6",well='E2',conc=Concentration(2.222,1.0,'x'),extraVol=30) # Acetyl CoA + Trans-Zeatin +Redox
reagents.add("8600", well='A1', conc=Concentration(10.0,1.0,'x'), extraVol=30, plate=trplayout.EPPENDORFS, noEvap=True, precious=True)  # HTS library at 10x in DMSO
reagents.add("8630", well='A1', conc=Concentration(10.0,1.0,'x'), extraVol=30, plate=trplayout.EPPENDORFS, noEvap=True, precious=True)  # HTS library at 10x in DMSO
reagents.add("DMSO", well='B1', conc=Concentration(10.0,1.0,'x'), extraVol=30, plate=trplayout.EPPENDORFS, noEvap=True, precious=True)  # DMSO
reagents.add("8607", well='B1', conc=Concentration(10.0,1.0,'x'), extraVol=30, plate=trplayout.EPPENDORFS, noEvap=True, precious=True)  # DMSO
    
def listify(x):
    """Convert a list of (lists or scalars) into a list of equal length lists"""
    n=1
    for i in x:
        if isinstance(i,list):
            n=max(n,len(i))
    result=[]
    for i in x:
        if isinstance(i,list):
            assert(len(i)==n or len(i)==0)
            result.append(i)
        else:
            result.append([i]*n)
    return result

def diluteName(name,dilution):
    # Create a name for a dilution of another sample
    # Collapses any current dilution
    components = name.split('.')
    curdil=1
#   replicate=1
#    if len(components[-1])==1:
#        replicate=int(components[-1])
#        components=components[:-1]
        
    if len(components)>1 and components[-1][0]=='D':
        olddilstr=components[-1][1:]
        curdil=float(olddilstr.replace("_",".").replace('#',''))
        if curdil==0:
            curdil=1
        else:
            components=components[:-1]
    dilstr="%.2f"%(curdil*dilution)
    while dilstr[-1]=='0':
        dilstr=dilstr[:-1]
    if dilstr[-1]=='.':
        dilstr=dilstr[:-1]
    dilstr=dilstr.replace(".","_")
    result=".".join(components) + ".D"+dilstr
#    if replicate!=1:
#        result=result+"."+"%d"%replicate
#    print "%s diluted %.2f -> %s"%(name,dilution,result)
    return result

class TRP(object):
    def __init__(self):
        """Create a new TRP run"""
        self.e=None  # Placeholder
            
    def reset(self):
        """Reset this experiment so we can generate it again after adjusting the reagent initial volumes and total time"""
        rlist=Sample.getAllLocOnPlate(trplayout.REAGENTPLATE)  # Get list before resets
        epp=Sample.getAllLocOnPlate(trplayout.EPPENDORFS)

        totalTime=clock.elapsed()
        clock.reset(totalTime)
        #print "After reset, elapsed=%d"%clock.elapsed()
        worklist.reset()
        Sample.clearall()
        reagents.reset()
        Plate.reset()
        self.e=Experiment()
        print(f"reagents: {rlist}")
        if len(rlist)>0:
            worklist.userprompt(f"The following reagent tubes should be present: {rlist}")
        if len(epp)>0:
            worklist.userprompt(f"The following eppendorf tubes should be present: {epp}")

        trplayout.initWellKnownSamples()
        Experiment.setreagenttemp(globals.dewpoint)
        Sample.printallsamples()
        self.e.sanitize(3,50)    # Heavy sanitize

    @staticmethod
    def addTemplates(names, stockconc, finalconc=None, units="nM", plate=None, looplengths=None, extraVol=30, wellnames=None, initVol=0):
        """Add templates as "reagents", return the list of them"""
        if plate is None:
            plate=trplayout.EPPENDORFS
        if finalconc is None:
            logging.warning("final concentration of template not specified, assuming 0.6x (should add to addTemplates() call")
            [names,stockconc]=listify([names,stockconc])
            finalconc=[0.6*x for x in stockconc]
        else:
            [names,stockconc,finalconc]=listify([names,stockconc,finalconc])
        if len(set(names))!=len(names):
            logging.error("addTemplates: template names must be unique")
            
        r=[]
        if looplengths is not None:
            assert(len(names)==len(looplengths))
        for i in range(len(names)):
            if wellnames is None:
                well=None
            else:
                well=wellnames[i]
            if reagents.isReagent(names[i]):
                r.append(reagents.lookup(names[i]))
            elif looplengths is None:
                r.append(reagents.add(names[i],plate=plate,conc=Concentration(stockconc[i],finalconc[i],units),extraVol=extraVol,well=well,initVol=initVol))
            else:
                r.append(reagents.add(names[i],plate=plate,conc=Concentration(stockconc[i],finalconc[i],units),extraVol=extraVol,extrainfo=looplengths[i],well=well,initVol=initVol))
                
        return r
    
    def finish(self):
        self.e.lihahome()
        db.endrun()   # May have already been ended before waiting to turn off reagent chiller; idempotent
        worklist.userprompt("Process complete.",1)
        Sample.evapcheckallsamples()   #  Run an evap check to ensure that we compute with correct reagent block temp
        self.e.setreagenttemp(None)

        #Sample.printallsamples("At completion")
        hasError=False
        for s in Sample.getAllOnPlate():
            if s.volume<1.0 and s.conc is not None and not s.emptied:
                logging.error("Insufficient volume for %s: need at least %.1f ul additional"%(s.name,1.0-s.volume))
                #hasError=True
            elif s.volume<2.5 and s.conc is not None and not s.emptied:
                logging.warning("Low final volume for "+ s.name)
            elif s.volume>s.plate.plateType.maxVolume:
                logging.error("Excess final volume  (%.1f) for %s: maximum is %.1f ul"%(s.volume,s.name,s.plate.plateType.maxVolume))
                hasError=True
                
        if hasError:
            logging.error("NO OUTPUT DUE TO ERRORS")
            
        print("Wells used: ",end='')
        for plate in Plate.allPlates():
            nsamp=Sample.numSamplesOnPlate(plate)
            if nsamp>0:
                print(" %s:%d"%(plate.name,nsamp),end='')
        print()

        # Save worklist to a file
        #e.saveworklist("trp1.gwl")
        (scriptname,ext)=os.path.splitext(sys.argv[0])
        self.e.savegem(scriptname+".gem")
        self.e.savesummary(scriptname+".txt",vars(self))
        Sample.savematlab(scriptname+".m")
        
    ########################
    # Save samples to another well
    # 'vol' is amount to take from source, and then dilute by 'dil'
    ########################
    def saveSamps(self,src,vol,dil,tgt=None,dilutant=None,plate=None,mix=(True,False),atEnd=False):
        [src,vol,dil]=listify([src,vol,dil])
        if plate is None:
            plate=trplayout.REAGENTPLATE
        if tgt is None:
            tgt=[Sample(diluteName(src[i].name,dil[i]),plate,atEnd=atEnd) for i in range(len(src))]

        if any([d!=1.0 for d in dil]):
            if dilutant is None:
                dilutant=trplayout.WATER
            self.e.multitransfer([vol[i]*(dil[i]-1) for i in range(len(vol))],dilutant,tgt,(False,False))

        self.e.shakeSamples(src,returnPlate=True)
        for i in range(len(src)):
            self.e.transfer(vol[i],src[i],tgt[i],mix)
            tgt[i].conc=src[i].conc
            if tgt[i].conc is not None:
                tgt[i].conc.stock=tgt[i].conc.stock/dil[i]
            
        return tgt
    
    def distribute(self,src,dil,vol,wells,tgt=None,dilutant=None,plate=None):
        if plate is None:
            plate=src.plate
        if tgt is None:
            tgt=[Sample("%s.dist%d"%(src[0].name,j),plate) for j in range(wells)]
        
        if dilutant is None:
            dilutant=trplayout.WATER
        self.e.multitransfer([vol*(dil-1) for _ in range(wells)],dilutant,tgt)
        self.e.multitransfer([vol for _ in range(wells)],src[0],tgt)
        return tgt


    ########################
    # Dilute samples in place
    ########################
    def diluteInPlace(self,tgt,dil=None,finalvol=None):
        # Dilute in place
        # e.g.: trp.diluteInPlace(tgt=rt1,dil=2)
        [tgt,dil,finalvol]=listify([tgt,dil,finalvol])
        dilutant=trplayout.WATER
        dil2=[1 for _ in tgt]
        for i in range(len(tgt)):
            if finalvol[i] is not None and dil[i] is None:
                self.e.transfer(finalvol[i]-tgt[i].volume,dilutant,tgt[i],mix=(False,False))
            elif finalvol[i] is None and dil[i] is not None:
                self.e.transfer(tgt[i].volume*(dil[i]-1),dilutant,tgt[i],mix=(False,False))
            elif dil[i] is None:
                logging.error("diluteInPlace: neither dil nor finalvol were specified")
            else: # Both dil and finalvol specified
                dil1 = max(1,min(dil[i],finalvol[i]/tgt[i].volume))
                dil2[i] = dil[i]/dil1
                if dil1>1:
                    self.e.transfer(tgt[i].volume*(dil1-1),dilutant,tgt[i],mix=(False,False))


        if any([d2>1 for d2 in dil2]):
            self.e.shakeSamples(tgt)
            for i in range(len(tgt)):
                if dil2[i]>1:
                    disposeVol=tgt[i].volume - finalvol[i] / dil2[i]-SURFACEREMOVE
                    if disposeVol>0:
                        self.e.dispose(disposeVol, tgt[i])
                        if tgt[i].volume<4:
                            logging.error('diluteInPlace: only %.0f ul left in well after disposing of unneeded sample'%tgt[i].volume)
                        elif tgt[i].volume<20:
                            logging.warning('diluteInPlace: only %.0f ul left in well after disposing of unneeded sample'%tgt[i].volume)
                    self.e.transfer(tgt[i].volume * (dil2[i] - 1), dilutant, tgt[i], mix=(False, False))

        #print "after dilute, tgt[0]=",str(tgt[0]),",mixed=",tgt[0].isMixed()
        return tgt   #  The name of the samples are unchanged -- the predilution names

    ########################
    # Run a reaction in place
    ########################
    def runRxInPlace(self,src,vol,master,master2=None,master3=None,returnPlate=True,finalx=1.0):
        """Run reaction on beads in given total volume"""
        [vol,src,master,master2,master3]=listify([vol,src,master,master2,master3])
        mastervol=[vol[i]*finalx/master[i].conc.dilutionneeded() for i in range(len(vol))]
        master2vol=[0 if master2[i] is None else vol[i]*finalx/master2[i].conc.dilutionneeded() for i in range(len(vol))]
        master3vol=[0 if master3[i] is None else vol[i]*finalx/master3[i].conc.dilutionneeded() for i in range(len(vol))]
        watervol=[vol[i]-src[i].volume-mastervol[i]-master2vol[i]-master3vol[i] for i in range(len(vol))]
        if any([w < -0.02 for w in watervol]):
            logging.error("runRxInPlace: negative amount of water needed: %.2f"%min(watervol))

        for i in range(len(src)):
            if  watervol[i]+src[i].volume>=4.0 and watervol[i]>0.1:
                self.e.transfer(watervol[i], trplayout.WATER, src[i], (False, False))
                watervol[i]=0
        for i in range(len(src)):
            self.e.transfer(mastervol[i],master[i],src[i],(True,False))
        for i in range(len(src)):
            if master2vol[i]>0:
                self.e.transfer(master2vol[i],master2[i],src[i],(True,False))
            if master3vol[i]>0:
                self.e.transfer(master3vol[i],master3[i],src[i],(True,False))
        for i in range(len(src)):
            if  watervol[i]>=0.1:
                self.e.transfer(watervol[i], trplayout.WATER, src[i], (False, False))
        self.e.shakeSamples(src,returnPlate=returnPlate)

    ########################
    # T7 - Transcription
    ########################
    def runT7Setup(self, src, vol, srcdil, ligands=None, tgt=None, rlist=None):
        if rlist is None:
            rlist = ["MT7"]
        if isinstance(ligands,bool):
            if not ligands:
                ligands=None
            else:
                logging.error('runT7Setup:  ligands arg should be ligand samples or None, not True')
                
        [ligands,src,tgt,srcdil]=listify([ligands,src,tgt,srcdil])
        for i in range(len(src)):
            if tgt[i] is None:
                if ligands[i] is not None:
                    # src could be on Products or other plate, so don't have information as to what plate to use for this
                    # For now, just revert to using sample plate
                    #tgt[i]=Sample("%s.T+%s"%(src[i].name,ligands[i].name),src[i].plate)
                    tgt[i]=Sample("%s.T+%s" % (src[i].name,ligands[i].name), trplayout.SAMPLEPLATE)
                else:
                    #tgt[i]=Sample("%s.T-"%src[i].name,src[i].plate)
                    tgt[i]=Sample("%s.T-" % src[i].name, trplayout.SAMPLEPLATE)


        worklist.comment("runT7: source=%s"%[str(s) for s in src])

        rvols=[reagents.getsample(x).conc.volneeded(vol) for x in rlist]
        rtotal=sum(rvols)
        sourcevols=[vol*1.0/s for s in srcdil]
        ligandvols=[0 for _ in srcdil]
        watervols=[0 for _ in srcdil]
        for i in range(len(srcdil)):
            if ligands[i] is not None:
                ligandvols[i]=vol*1.0/ligands[i].conc.dilutionneeded()
                watervols[i]=vol-ligandvols[i]-sourcevols[i]-rtotal
            else:
                watervols[i]=vol-sourcevols[i]-rtotal

        if any([w<-.01 for w in watervols]):
            logging.error("runT7Setup: Negative amount of water required: "+str(watervols))

        if sum(watervols)>0.01:
            self.e.multitransfer(watervols, trplayout.WATER, tgt)
        for ir in range(len(rlist)):
            self.e.multitransfer([rvols[ir] for _ in tgt],reagents.getsample(rlist[ir]),tgt)
        for i in range(len(src)):
            self.e.transfer(sourcevols[i],src[i],tgt[i])
        for i in range(len(ligands)):
            if ligandvols[i] > 0.01:
                self.e.transfer(ligandvols[i],ligands[i],tgt[i])
        self.e.shakeSamples(tgt,returnPlate=True)
        for t in tgt:
            t.ingredients['BIND']=1e-20*sum(t.ingredients.values())
        return tgt
    
    def runT7Pgm(self,plate:Plate, vol,dur):
        if dur<100:
            pgm="TRP37-%d"%dur
        else:
            pgm="T37-%d"%dur
        thermocycler.setpgm(pgm,38,'TEMP@37,%d TEMP@25,2'%(dur*60))
        print("Running T7 at 37C for %d minutes"%dur)
        self.e.runpgm(plate, pgm,dur, False,vol)

    # noinspection PyUnusedLocal
    def runT7Stop(self,theo,tgt,stopmaster=None):
        del theo # Unused
        [tgt,stopmaster]=listify([tgt,stopmaster])
        assert( stopmaster is not None)
            
        ## Stop
        sstopmaster=[reagents.getsample(s) for s in stopmaster]
        for i in range(len(tgt)):
            stopvol=tgt[i].volume/(sstopmaster[i].conc.dilutionneeded()-1)
            finalvol=tgt[i].volume+stopvol
            tgt[i].conc=Concentration(finalvol/tgt[i].volume,1)  # Adjust source dilution to avoid warnings
            self.e.transfer(finalvol-tgt[i].volume,sstopmaster[i],tgt[i])
            
        self.e.shakeSamples(tgt,returnPlate=True)

        return tgt

    def addEDTA(self,tgt,finalconc=4):
        edta=reagents.getsample("EDTA")
        edta.conc.final=finalconc
        self.add(tgt,edta)
        
    def add(self,tgt,samp):
        srcdil=samp.conc.stock*1.0/(samp.conc.stock-samp.conc.final)
        for t in tgt:
            t.conc=Concentration(srcdil,1)
            v=t.volume*samp.conc.final/(samp.conc.stock-samp.conc.final)
            self.e.transfer(v,samp,t,mix=(False,False))
        self.e.shakeSamples(tgt,returnPlate=True)
        
    def runT7(self,theo,src,vol,srcdil,tgt=None,dur=15,stopmaster=None):
        [theo,src,tgt,srcdil,stopmaster]=listify([theo,src,tgt,srcdil,stopmaster])
        tgt=self.runT7Setup(theo,src,vol,srcdil,tgt)
        self.runT7Pgm(tgt[0].plate, vol,dur)
        tgt=self.runT7Stop(theo,tgt,stopmaster)
        return tgt

    ########################
    # Beads
    ########################
    def bindBeads(self,src,beads=None,beadConc=None,beadDil=None,bbuffer=None,incTime=60,addBuffer=False):
        if beads is None:
            beads=reagents.getsample("Dynabeads")
        if bbuffer is None:
            bbuffer=reagents.getsample("BeadBuffer")
            
        [src,beads,bbuffer,beadConc,beadDil]=listify([src,beads,bbuffer,beadConc,beadDil])

        for s in src:
            if s.plate.plateLocation.vectorName is None:
                logging.error( "runBeadCleanup: src "+s.name+" is on plate "+s.plate.name+", which cannot be moved to magnet.")

            s.conc=None		# Can't track concentration of beads
            
        self.e.moveplate(src[0].plate,"Home")		# Make sure we do this off the magnet

        # Calculate volumes needed
        beadDil=[beads[i].conc.stock/(beads[i].conc.final if beadConc[i] is None else beadConc[i]) if beadDil[i] is None else beadDil[i] for i in range(len(beads))]

        if addBuffer:
            totalvol=[src[i].volume/(1-1.0/beadDil[i]-1.0/bbuffer[i].conc.dilutionneeded()) for i in range(len(src))]
            buffervol=[totalvol[i]/bbuffer[i].conc.dilutionneeded() for i in range(len(src))]
            # Add binding buffer to bring to 1x (beads will already be in 1x, so don't need to provide for them)
            for i in range(len(src)):
                self.e.transfer(buffervol[i],bbuffer[i],src[i])
        else:
            totalvol=[src[i].volume/(1-1.0/beadDil[i]) for i in range(len(src))]

        beadvol=[totalvol[i]/beadDil[i] for i in range(len(totalvol))]

        # Transfer the beads
        for i in range(len(src)):
            self.e.transfer(beadvol[i],beads[i],src[i],(True,False))	# Mix beads before

        self.e.shakeSamples(src,dur=incTime,returnPlate=False)

    # noinspection PyUnusedLocal
    def sepWait(self,src,sepTime=None):
        del src # Unused
        if sepTime is None:
            #maxvol=max([s.volume for s in src])
            # if maxvol > 50:
            #     sepTime=50
            # else:
            #     sepTime=30
            sepTime=120
        self.e.pause(sepTime)	# Wait for separation
        
    def beadWash(self,src,washTgt=None,sepTime=None,residualVolume=0.1,keepWash=False,numWashes=2,wash=None,washVol=50,keepFinal=False,finalTgt=None,keepVol=4.2,keepDil=5,shakeWashes=False):
        # Perform washes
        # If keepWash is true, retain all washes (combined)
        # If keepFinal is true, take a sample of the final wash (diluted by keepDil)
        if wash is None:
            wash=trplayout.WATER
        [src,wash]=listify([src,wash])
        # Do all washes while on magnet
        assert(len(set([s.plate for s in src]))==1)	# All on same plate
        if keepWash:
            if washTgt is None:
                washTgt=[]
                for i in range(len(src)):
                    if src[i].volume-residualVolume+numWashes*(washVol-residualVolume) > trplayout.DILPLATE.maxVolume-20:
                        logging.notice("Saving %.1f ul of wash in eppendorfs"%(numWashes*washVol))
                        washTgt.append(Sample("%s.Wash" % src[i].name, trplayout.EPPENDORFS))
                    else:
                        washTgt.append(Sample("%s.Wash" % src[i].name, trplayout.DILPLATE))

        if keepFinal:
            if finalTgt is None:
                finalTgt=[]
                for i in range(len(src)):
                    finalTgt.append(Sample("%s.Final" % src[i].name, trplayout.DILPLATE))

        if any([s.volume>residualVolume for s in src]):
            # Separate and remove supernatant
            self.e.moveplate(src[0].plate,"Magnet")	# Move to magnet
            self.sepWait(src,sepTime)

            # Remove the supernatant
            for i in range(len(src)):
                if src[i].volume > residualVolume:
                    amt=src[i].amountToRemove(residualVolume)
                    if keepWash:
                        self.e.transfer(amt,src[i],washTgt[i])	# Keep supernatants
                        washTgt[i].conc=None	# Allow it to be reused
                    else:
                        self.e.dispose(amt,src[i])	# Discard supernatant
                
        # Wash

        for washnum in range(numWashes):
            if src[0].plate.location!=src[0].plate.homeLocation and src[0].plate.location!=trplayout.MAGPLATELOC:
                self.e.moveplate(src[0].plate,"Home")
            if keepFinal and washnum==numWashes-1:
                'Retain sample of final'
                for i in range(len(src)):
                    src[i].conc=None
                    self.e.transfer(washVol-src[i].volume,wash[i],src[i],mix=(False,True))	# Add wash
                self.e.shakeSamples(src,returnPlate=True)
                self.saveSamps(src=src, tgt=finalTgt, vol=keepVol, dil=keepDil, plate=trplayout.DILPLATE)
            else:
                for i in range(len(src)):
                    src[i].conc=None
                    self.e.transfer(washVol-src[i].volume,wash[i],src[i],mix=(False,False))	# Add wash, no need to pipette mix since some heterogenity won't hurt here
                if shakeWashes:
                    self.e.shakeSamples(src,returnPlate=False)

            self.e.moveplate(src[0].plate,"Magnet")	# Move to magnet
                
            self.sepWait(src,sepTime)
                
            for i in range(len(src)):
                amt=src[i].amountToRemove(residualVolume)
                if keepWash:
                    self.e.transfer(amt,src[i],washTgt[i],mix=(False,False))	# Remove wash
                    washTgt[i].conc=None	# Allow it to be reused
                else:
                    self.e.dispose(amt,src[i])	# Remove wash

        #self.e.moveplate(src[0].plate,"Home")

        # Should only be residualVolume left with beads now
        result=[]
        if keepWash:
            result=result+washTgt
        if keepFinal:
            result=result+finalTgt

        return result

    def beadAddElutant(self,src,elutant=None,elutionVol=30,eluteTime=60,returnPlate=True,temp=None):
        if elutant is None:
            elutant=trplayout.WATER
        [src,elutionVol,elutant]=listify([src,elutionVol,elutant])
        for i in range(len(src)):
            if elutionVol[i]<30:
                logging.warning("elution from beads of %s with %.1f ul < minimum of 30ul"%(src[i].name,elutionVol[i]))
            self.e.moveplate(src[i].plate,"Home")
            self.e.transfer(elutionVol[i]-src[i].volume,elutant[i],src[i],(False,True))	
        if temp is None:
            for plate in set([s.plate for s in src]):
                self.e.shake(plate,dur=eluteTime,returnPlate=returnPlate,force=True)
        else:
            self.e.shakeSamples(src,dur=30,returnPlate=False)
            thermocycler.setpgm('elute',temp+1,'TEMP@%d,%d TEMP@25,2'%(temp,eluteTime))
            self.e.runpgm(src[0].plate,"elute",eluteTime/60,False,elutionVol[0])
            if returnPlate:
                self.e.moveplate(src[0].plate,"Home")

    def beadSupernatant(self,src,tgt=None,sepTime=None,residualVolume=0.1,plate=None):
        if tgt is None:
            tgt=[]
            for i in range(len(src)):
                tgt.append(Sample("%s.SN"%src[i].name,src[i].plate if plate is None else plate))
        [src,tgt]=listify([src,tgt])

        if any([s.plate!=src[0].plate for s in src]):
            logging.error("beadSupernatant: Attempt to magsep on multiple plates at the same time")

        self.e.moveplate(src[0].plate,"Magnet")	# Move to magnet
        self.sepWait(src,sepTime)

        for i in range(len(src)):
            self.e.transfer(src[i].amountToRemove(residualVolume),src[i],tgt[i],(False,False))	# Transfer elution to new tube

        self.e.moveplate(src[0].plate,"Home")
        return tgt

    def beadCombine(self,src,residualVolume=0.1,suspendVolume=150,sepTime=None):
        """Combine everything in the src wells into a the first well; assumes that there are enough beads in that well for all the combination"""
        tgt=src[0]
        for s in src[1:]:
            # Combine s with tgt
            if tgt.volume>residualVolume:
                self.e.moveplate(tgt.plate,"Magnet")	# Move to magnet
                self.sepWait([tgt],sepTime)
                self.e.dispose(tgt.amountToRemove(residualVolume),tgt)
            self.e.moveplate(tgt.plate,"Home")	
            if s.volume<suspendVolume:
                self.e.transfer(suspendVolume - s.volume, trplayout.WATER, s, (False, False))
            vol=s.volume-residualVolume-1
            s.conc=None
            self.e.transfer(vol,s,tgt,mix=(True,True))

        self.e.moveplate(tgt.plate,"Home")	
        return src[0:1]
    
    ########################
    # Ampure Cleanup
    ########################
    def runAmpure(self,src,ratio,tgt=None,incTime=5*60,elutionVol=None,evapTime=2*60):
        if elutionVol is None:
            elutionVol=src[0].volume
        self.bindBeads(src=src,beads=reagents.getsample("Ampure"),beadDil=(ratio+1)/ratio,incTime=incTime)
        self.beadWash(src=src,wash=reagents.getsample("EtOH80"),washVol=100,numWashes=2)
        self.e.pause(evapTime)	# Wait for evaporation
        self.beadAddElutant(src=src,elutant=reagents.getsample("TE8"),elutionVol=elutionVol)
        if tgt is None:
            tgt=[Sample("%s.ampure"%r.name,r.plate) for r in src]
        res=self.beadSupernatant(src=src,sepTime=120,tgt=tgt)
        return res
    
    ########################
    # RT - Reverse Transcription
    ########################
    def runRT(self,src,vol,srcdil,tgt=None,dur=20,heatInactivate=False,hiTemp=None,incTemp=37,stop=None,stopConc=1.0):
        result=self.runRTSetup(src,vol,srcdil,tgt,stop=stop,stopConc=stopConc)
        self.runRTPgm(result[0].plate, dur,heatInactivate=heatInactivate,hiTemp=hiTemp,incTemp=incTemp,src=src)
        return result
    
    def runRTInPlace(self,src,vol,dur=20,heatInactivate=False,hiTemp=None,incTemp=37,stop=None):
        """Run RT on beads in given volume"""

        # Adjust source dilution
        for i in range(len(src)):
            src[i].conc=None

        if stop is not None:
            print('runRTInPlace does not support adding stop')
            assert False
            
        self.runRxInPlace(src,vol,reagents.getsample("MPosRT"),returnPlate=False)
        self.runRTPgm(src[0].plate, dur,heatInactivate=heatInactivate,hiTemp=hiTemp,incTemp=incTemp,src=src)
        
    def runRTSetup(self,src,vol,srcdil,tgt=None,rtmaster=None,stop=None,stopConc=1.0,prerefold=False):
        if rtmaster is None:
            rtmaster=reagents.getsample("MPosRT")
        if tgt is None:
            tgt=[Sample(s.name+".RT+",s.plate) for s in src]

        [src,tgt,vol,srcdil,stop,stopConc,rtmaster]=listify([src,tgt,vol,srcdil,stop,stopConc,rtmaster])

        # Adjust source dilution
        for i in range(len(src)):
            src[i].conc=Concentration(srcdil[i],1)

        for i in range(len(stop)):
            if stop[i] is not None:
                stop[i].conc.final=stopConc[i]   # FIXME: these usually all refer to the same underlying sample, so changing the same value multiple times
                if stop[i].conc.stock<4*stopConc[i]:
                    #stop[i].conc.stock=10   # Use 10uM stock (or higher)
                    logging.warning("Increase %s stock concentration to %.1f uM to accomodate stop at %.0f uM final"%(stop[i].name,4*stopConc[i],stopConc[i]),stderr=True)  # Need to write to stderr since this will only happen during first pass, for which stdout is supressed
                    stop[i].conc.stock=stopConc[i]*4
                
        if any([s is not None for s in stop]):
            print("Adding stop:  [%s]"%(",".join(["%s@%.1fuM (stock=%.1fuM)"%(stop[i].name,stopConc[i],stop[i].conc.stock) for i in range(len(stop))])))

        stopvol=[ 0 if stop[i] is None else vol[i]*stopConc[i]/stop[i].conc.stock for i in range(len(vol))]
        #assert(min(stopvol)==max(stopvol))   # Assume all stop volumes are the same
        #self.e.stage('RTPos',[rtmaster],[src[i] for i in range(len(src)) ],[tgt[i] for i in range(len(tgt)) ],[vol[i]-stopvol[i] for i in range(len(vol))],destMix=False,finalx=vol[0]/(vol[0]-stopvol[0]))
        
        
        watervol=[vol[i]-stopvol[i]-vol[i]/srcdil[i]-vol[i]/rtmaster[i].conc.dilutionneeded() for i in range(len(tgt))]
        self.e.multitransfer(watervol, trplayout.WATER, tgt, (False, False))
        for i in range(len(tgt)):
            if stopvol[i]>0.1:
                self.e.transfer(stopvol[i],stop[i],tgt[i],(False,False))
        for i in range(len(tgt)):
            self.e.transfer(vol[i]/srcdil[i],src[i],tgt[i],(False,False))
        self.e.shakeSamples(tgt,returnPlate=True)
        if prerefold:
            self.refold(tgt[0].plate)
        for i in range(len(tgt)):
            self.e.transfer(vol[i]/rtmaster[i].conc.dilutionneeded(),rtmaster[i],tgt[i],(False,False))
        self.e.shakeSamples(tgt,returnPlate=True)

        return tgt

    def runRTPgm(self,plate:Plate, dur=20,heatInactivate=False,hiTemp=None,incTemp=37,src=None):
        pgm="RT-%d"%dur
        if heatInactivate:
            if hiTemp is None:
                hiTemp=95
                print("Assuming RT heat inactivation temperature of ",hiTemp)
            hidur=2

            thermocycler.setpgm(pgm,hiTemp+1,'TEMP@%d,%d TEMP@%d,%d TEMP@25,2 RATE@0.5'%(incTemp,dur*60,hiTemp,hidur*60))
            self.e.runpgm(plate,pgm,dur+hidur+2.5,False,100)		# Volume doesn't matter since it's just an incubation, use 100ul
            print("Running RT at %dC for %d min, followed by heat inactivation/refold at %dC for %d minutes"%(incTemp,dur,hiTemp,hidur))
            assert(src is not None)
            # Mark samples as mixed (by thermal convection)
            print("Marking all samples on plate %s as mixed (by thermal convection) after RT with inactivation at %.0f"%(src[0].plate.name,hiTemp))
            for t in Sample.getAllOnPlate(src[0].plate):
                t.wellMixed=True
                t.lastMixed=clock.elapsed() # Will be cleared due to call to notMixed() later (due to condensation), but wellMixed=True will allow any shake to make it mixed
        else:
            thermocycler.setpgm(pgm,incTemp+1,'TEMP@%d,%d TEMP@25,2'%(incTemp,dur*60))
            self.e.runpgm(plate, pgm,dur,False,100)		# Volume doesn't matter since it's just an incubation, use 100ul
            print("Running RT at %dC for %d min without heat inactivation"%(incTemp,dur))

    def refold(self,plate:Plate, hiTemp=95,coolTemp=25,rate=0.5):
        pgm="Refold"
        hidur=2
        thermocycler.setpgm(pgm,hiTemp+1,'TEMP@%d,%d TEMP@%d,2 RATE@%.1f'%(hiTemp,hidur*60,coolTemp,rate))
        self.e.runpgm(plate,pgm,(hiTemp-coolTemp)/rate/60+hidur+2.5,False,100)		# Volume doesn't matter since it's just an incubation, use 100ul
        print("Running refold at %dC for %d min, followed by cooling to %dC at %.1fC/sec"%(hiTemp,hidur,coolTemp,rate))
             
    ########################
    # Incubation - run a single temp incubation followed by inactivation
    ########################
    def runIncubation(self,src=None,vol=None,srcdil=None,tgt=None,enzymes=None,incTemp=37,incTime=15,hiTemp=None,hiTime=0,inPlace=False):
        if len(enzymes)!=1:
            logging.error("runIncubation only supports a single master mix")
        if inPlace:
            if tgt is not None:
                logging.error("tgt specified for in-place incubation")
        elif tgt is None:
            tgt=[Sample("%s.%s"%(src[i].name,enzymes[0].name),src[i].plate) for i in range(len(src))]

        if srcdil is None:
            # Minimum dilution (no water)
            srcdil=1/(1-sum([1/e.conc.dilutionneeded() for e in enzymes]))

        if vol is None and inPlace:
            vol=[s.volume*srcdil for s in src]
            
        [src,tgt,vol,srcdil]=listify([src,tgt,vol,srcdil])

        # Adjust source dilution
        for i in range(len(src)):
            src[i].conc=Concentration(srcdil[i],1)

        if inPlace:
            self.runRxInPlace(src,vol,enzymes[0],returnPlate=(incTime is None))
            tgt=src
        else:
            self.e.stage('Incubation', enzymes, src, tgt, vol, destMix=False, dilutant=trplayout.WATER)
            self.e.shakeSamples(tgt,returnPlate=(incTime is None))

        if incTime is None:
            print("Setup only of incubation with %s"%enzymes[0].name)
        else:
            if hiTemp is None:
                thermocycler.setpgm('INC',incTemp+10,'TEMP@%.0f,%.0f TEMP@25,30'%(incTemp,incTime*60))
                print("Incubating at %dC for %d minutes without heat inactivation"%(incTemp, incTime))
                hiTime=0
            else:
                assert(hiTime>0)
                thermocycler.setpgm('INC',hiTemp+1,'TEMP@%.0f,%.0f TEMP@%.0f,%.0f TEMP@25,30'%(incTemp,incTime*60,hiTemp,hiTime*60))
                print("Incubating at %dC for %d minutes followed by heat inactivate at %dC for %d minutes"%(incTemp,incTime,hiTemp,hiTime))
            self.e.runpgm(tgt[0].plate, "INC",incTime+hiTime+2,False,max(vol))

        if hiTemp is not None:
            # Mark samples as mixed (by thermal convection)
            print("Marking samples as mixed (by thermal convection) following ligation with HI at %.0f"%hiTemp)
            for t in Sample.getAllOnPlate(src[0].plate):
                t.wellMixed=True
                t.lastMixed=clock.elapsed() # Will be cleared due to call to notMixed() later (due to condensation), but wellMixed=True will allow any shake to make it mixed

        return tgt

    ########################
    # USER - USER enzyme digestion
    ########################
    def runUser(self,src=None,vol=None,srcdil=None,tgt=None,incTime=15,inPlace=False,hiTemp=None,hiTime=0):
        return self.runIncubation(src=src,vol=vol,srcdil=srcdil,tgt=tgt,incTemp=37,incTime=incTime,enzymes=[reagents.getsample("MUser")],inPlace=inPlace,hiTime=hiTime,hiTemp=hiTemp)
        
    ########################
    # EXO - EXO enzyme digestion
    ########################
    def runExo(self,src=None,vol=None,srcdil=None,tgt=None,incTime=15,inPlace=False,hiTemp=80,hiTime=20):
        return self.runIncubation(src=src,vol=vol,srcdil=srcdil,tgt=tgt,incTemp=37,incTime=incTime,enzymes=[reagents.getsample("MExo")],inPlace=inPlace,hiTemp=hiTemp,hiTime=hiTime)
        
    ########################
    # Klenow extension
    ########################
    def runKlenow(self,src=None,vol=None,srcdil=None,tgt=None,incTime=15,hiTime=20,hiTemp=75,inPlace=False):
        assert(inPlace or vol is not None)
        return self.runIncubation(src=src,vol=vol,srcdil=srcdil,tgt=tgt,incTemp=37,incTime=incTime,hiTemp=hiTemp,hiTime=hiTime,enzymes=[reagents.getsample("MKlenow")],inPlace=inPlace)

    ########################
    # Ligation
    ########################
    def runLig(self,src=None,vol=None,srcdil=None,tgt=None,incTime=15,hiTime=10,hiTemp=65,inPlace=False):
        assert(inPlace or vol is not None)
        return self.runIncubation(src=src,vol=vol,srcdil=srcdil,tgt=tgt,incTemp=37,incTime=incTime,hiTemp=hiTemp,hiTime=hiTime,enzymes=[reagents.getsample("MLigase")],inPlace=inPlace)

    ########################
    # DNase digestion
    ########################
    def runDNase(self,src=None,vol=None,srcdil=None,tgt=None,incTime=15,hiTime=10,inPlace=False):
        return self.runIncubation(src=src,vol=vol,srcdil=srcdil,tgt=tgt,incTemp=37,incTime=incTime,hiTemp=75,hiTime=hiTime,enzymes=[reagents.getsample("MDNase")],inPlace=inPlace)

    ########################
    # PCR
    ########################
    def runPCR(self,primers,src,srcdil,vol=None,tgt=None,ncycles=20,usertime=None,fastCycling=False,inPlace=False,master="MTaq",annealTemp=None,kapa=False,lowhi=False):
        ## PCR
        if inPlace:
            if vol is not None:
                logging.error("runPCR: cannot specify volume when using inPlace=True, srcdil and input volume determine reaction volume")
            if tgt is not None:
                logging.error("runPCR: cannot specify tgt when using inPlace=True")
            if primers is None:
                [src,srcdil]=listify([src,srcdil])
            else:
                [primers,src,srcdil]=listify([primers,src,srcdil])
            vol=[src[i].volume*srcdil[i] for i in range(len(src))]
            tgt=src
        else: 
            if primers is None:
                [src,tgt,vol,srcdil]=listify([src,tgt,vol,srcdil])
            else:
                [primers,src,tgt,vol,srcdil]=listify([primers,src,tgt,vol,srcdil])
            for i in range(len(tgt)):
                if tgt[i] is None:
                    if primers is None:
                        tgt[i]=Sample("%s.%s"%(src[i].name,master),src[i].plate)
                    elif isinstance(primers[i],list):
                        tgt[i]=Sample("%s.P%s"%(src[i].name,"+".join(primers[i])),src[i].plate)
                    else:
                        tgt[i]=Sample("%s.P%s"%(src[i].name,primers[i]),src[i].plate)

        # Adjust source dilution
        for i in range(len(src)):
            src[i].conc=Concentration(srcdil[i],1)
        
        if primers is None:
            # No explicit primers
            if inPlace:
                self.runRxInPlace(src,vol,reagents.getsample(master),returnPlate=False)
            else:
                self.e.stage('PCR', [reagents.getsample(master)], src, tgt, vol, destMix=False, dilutant=trplayout.WATER)
        else:
            # Explicit primers
            logging.notice( "primer="+str(primers))

            # Add reagent entries for any missing primers
            if isinstance(primers[0],list):
                allprimers=[x for y in primers for x in y]
            else:
                allprimers=primers
            for up in set(allprimers):
                s="P-%s"%up
                if not reagents.isReagent(s):
                    reagents.add(name=s,conc=4,extraVol=30)

            if isinstance(primers[0],list):
                # Multiple primers
                if inPlace:
                    assert len(primers[0])==2
                    self.runRxInPlace(src,vol,reagents.getsample(master),master2=[reagents.getsample("P-%s"%p[0]) for p in primers],master3=[(reagents.getsample("P-%s"%p[1]) if p[1] is not None else None) for p in primers],returnPlate=False)
                else:
                    for i in range(len(primers)):
                        self.e.stage('PCR%d' % i, [reagents.getsample(master)] + [reagents.getsample("P-%s"%s) for s in primers[i]],src[i:i+1],tgt[i:i+1],vol[i:i+1], destMix=False, dilutant=trplayout.WATER)
                    #self.e.shakeSamples(tgt,returnPlate=False)
            else:
                # Single primer
                if inPlace:
                    self.runRxInPlace(src,vol,reagents.getsample(master),master2=[reagents.getsample("P-%s"%p) for p in primers],returnPlate=False)
                else:
                    for up in set(primers):
                        self.e.stage('PCR%s' % up, [reagents.getsample(master),reagents.getsample("P-%s"%up)], [src[i] for i in range(len(src)) if primers[i]==up], [tgt[i] for i in range(len(tgt)) if primers[i]==up], [vol[i] for i in range(len(vol)) if primers[i]==up],
                                     destMix=False, dilutant=trplayout.WATER)
                    #self.e.shakeSamples(tgt,returnPlate=False)

        pgm="PCR%d"%ncycles

        runTime=0

        if annealTemp is None:
            annealTemp=60 if kapa else 55

        meltTemp=98 if kapa else 95
        hotTime=180 if kapa else 30
        extTemp=72 if kapa else 68
        
        if lowhi:
            # First cycle at normal anneal, others at 66
            hotAnnealTemp=66
            cycling='TEMP@37,%d TEMP@95,%d TEMP@%.1f,30 TEMP@%.1f,30 TEMP@%.1f,30 TEMP@%.1f,30 TEMP@%.1f,30 TEMP@%.1f,30 GOTO@6,%d TEMP@%.1f,60 TEMP@25,2'%(1 if usertime is None else usertime*60,hotTime,meltTemp,annealTemp,extTemp,meltTemp,hotAnnealTemp,extTemp,ncycles-2,extTemp)
            runTime+=hotTime/60+2.8+3.0*ncycles
        elif fastCycling:
            cycling='TEMP@37,%d TEMP@95,%d TEMP@%.1f,10 TEMP@%.1f,10 TEMP @%.1f,1 GOTO@3,%d TEMP@%.1f,60 TEMP@25,2'%(1 if usertime is None else usertime*60,hotTime,meltTemp,annealTemp,extTemp,ncycles-1,extTemp)
            runTime+=hotTime/60+2.8+1.65*ncycles
        else:
            cycling='TEMP@37,%d TEMP@95,%d TEMP@%.1f,30 TEMP@%.1f,30 TEMP@%.1f,30 GOTO@3,%d TEMP@%.1f,60 TEMP@25,2'%(1 if usertime is None else usertime*60,hotTime,meltTemp,annealTemp,extTemp,ncycles-1,extTemp)
            runTime+=hotTime/60+2.8+3.0*ncycles

        if usertime is not None and usertime>0:
            runTime+=usertime

        print("PCR volume=[",",".join(["%.1f"%t.volume for t in tgt]), "], srcdil=[",",".join(["%.1fx"%s for s in srcdil]),"], program: %s"%cycling)

        thermocycler.setpgm(pgm,99,cycling)
        self.e.runpgm(tgt[0].plate, pgm,runTime,False,max(vol))
        # Mark samples as mixed (by thermal convection)
        print("Marking samples on plate %s as mixed (by thermal convection) after PCR"%tgt[0].plate.name)
        for t in Sample.getAllOnPlate(tgt[0].plate):
            t.wellMixed=True
            t.lastMixed=clock.elapsed()
        #self.e.shakeSamples(tgt,returnPlate=True)
        return tgt
    
    
    def runBCSetup(self, src, vol, srcdil, BC1=None, BC2=None, tgt=None, rlist=None):
        if rlist is None:
            rlist = ["MT7"]
        if isinstance(BC1,bool):
            if not BC1:
                BC1=None
            else:
                logging.error('runBCSetup:  ligands arg should be ligand samples or None, not True')
                
        [BC1,BC2,src,tgt,srcdil]=listify([BC1,BC2,src,tgt,srcdil])
        for i in range(len(src)):
            if tgt[i] is None:
                if BC1[i] is not None:
                    tgt[i]=Sample("%s.%s-%s"%(src[i].name,BC1[i].name,BC2[i].name),src[i].plate)
                else:
                    tgt[i]=Sample("%s.T-"%src[i].name,src[i].plate)

        worklist.comment("runBC: source=%s"%[str(s) for s in src])

        rvols=[reagents.getsample(x).conc.volneeded(vol) for x in rlist]
        rtotal=sum(rvols)
        sourcevols=[vol*1.0/s for s in srcdil]
        BC1vols=[0 for _ in srcdil]
        BC2vols=[0 for _ in srcdil]
        watervols=[0 for _ in srcdil]
        for i in range(len(srcdil)):
            if BC1[i] is not None:
                BC1vols[i]=vol*1.0/BC1[i].conc.dilutionneeded()
                BC2vols[i]=vol*1.0/BC2[i].conc.dilutionneeded()
                watervols[i]=vol-BC1vols[i]-BC2vols[i]-sourcevols[i]-rtotal
            else:
                watervols[i]=vol-sourcevols[i]-rtotal

        if any([w<-.1 for w in watervols]):
            logging.error("runT7Setup: Negative amount of water required: "+str(watervols))

        if sum(watervols)>0.01:
            self.e.multitransfer(watervols, trplayout.WATER, tgt)
        for ir in range(len(rlist)):
            self.e.multitransfer([rvols[ir] for _ in tgt],reagents.getsample(rlist[ir]),tgt)
        for i in range(len(BC1)):
            if BC1vols[i] > 0.01:
                self.e.transfer(BC1vols[i],BC1[i],tgt[i])
            if BC2vols[i] > 0.01:
                self.e.transfer(BC2vols[i],BC2[i],tgt[i])
        for i in range(len(src)):
            self.e.transfer(sourcevols[i],src[i],tgt[i])
        # self.e.shakeSamples(tgt,returnPlate=True)
        for t in tgt:
            t.ingredients['BIND']=1e-20*sum(t.ingredients.values())
        return tgt
    
    def runBCPCR(self,plate: Plate,ncycles,vol,usertime=None,kapa=True,annealTemp=None,fastCycling=False):
        pgm="PCR%d"%ncycles

        if usertime is None:
            runTime=0
        else:
            runTime=usertime

        if annealTemp is None:
            annealTemp=54 if kapa else 57

        meltTemp=98 if kapa else 95
        hotTime=180 if kapa else 30
        extTemp=72 if kapa else 68
        
        if fastCycling:
            cycling='TEMP@37,%d TEMP@95,%d TEMP@%.1f,10 TEMP@%.1f,10 TEMP @%.1f,1 GOTO@3,%d TEMP@%.1f,60 TEMP@25,2'%(1 if usertime is None else usertime*60,hotTime,meltTemp,annealTemp,extTemp,ncycles-1,extTemp)
            runTime+=hotTime/60+2.8+1.65*ncycles
        else:
            cycling='TEMP@37,%d TEMP@95,%d TEMP@%.1f,30 TEMP@%.1f,30 TEMP@%.1f,30 GOTO@3,%d TEMP@%.1f,60 TEMP@25,2'%(1 if usertime is None else usertime*60,hotTime,meltTemp,annealTemp,extTemp,ncycles-1,extTemp)
            runTime+=hotTime/60+2.8+3.0*ncycles
            
        thermocycler.setpgm(pgm,99,cycling)
        self.e.runpgm(plate, pgm,runTime,False,max(vol))
    

    ########################
    # qPCR
    ########################
    def runQPCRDIL(self,src,vol,srcdil,tgt=None,dilPlate=False,pipMix=False,dilutant=None):
        if dilutant is None:
            dilutant=trplayout.SSDDIL
        [src,vol,srcdil]=listify([src,vol,srcdil])
        vol=[float(v) for v in vol]
        if tgt is None:
            if dilPlate:
                tgt=[Sample(diluteName(src[i].name,srcdil[i]), trplayout.DILPLATE) for i in range(len(src))]
            else:
                tgt=[Sample(diluteName(src[i].name,srcdil[i]),src[i].plate) for i in range(len(src))]

        srcvol=[vol[i]/srcdil[i] for i in range(len(vol))]
        watervol=[vol[i]-srcvol[i] for i in range(len(vol))]
        if len(watervol) > 4 and sum(watervol)>800:
            logging.notice("Could optimize distribution of "+str(len(watervol))+" moves of "+dilutant.name+": vol=["+str(["%.1f"%w for w in watervol])+"]")
        self.e.multitransfer(watervol,dilutant,tgt,(False,False))
        
        self.e.shakeSamples(src,returnPlate=True)
        for i in range(len(src)):
            tgt[i].conc=None		# Assume dilutant does not have a concentration of its own
            # Check if we can align the tips here
            if i<len(src)-3 and tgt[i].well+1==tgt[i+1].well and tgt[i].well+2==tgt[i+2].well and tgt[i].well+3==tgt[i+3].well and tgt[i].well%4==0 and self.e.cleanTips!=15:
                #print "Aligning tips"
                self.e.sanitize()
            self.e.transfer(srcvol[i],src[i],tgt[i],(not src[i].isMixed(),pipMix))
            if tgt[i].conc is not None:
                tgt[i].conc.final=None	# Final conc are meaningless now
            
        return tgt
        
    def runQPCR(self,src,vol,primers,nreplicates=1,enzName="EvaUSER"):
        ## QPCR setup
        worklist.comment("runQPCR: primers=%s, source=%s"%([p for p in primers],[s.name for s in src]))
        [src,vol,nreplicates]=listify([src,vol,nreplicates])
        self.e.shakeSamples(src,returnPlate=True)

        # Build a list of sets to be run
        torun=[]
        for repl in range(max(nreplicates)):
            for p in primers:
                for i in range(len(src)):
                    if nreplicates[i]<=repl:
                        continue
                    if repl==0:
                        sampname="%s.Q%s"%(src[i].name,p)
                    else:
                        sampname="%s.Q%s.%d"%(src[i].name,p,repl+1)
                    s=Sample(sampname, trplayout.QPCRPLATE)
                    torun=torun+[(src[i],s,p,vol[i])]

        # Add enzyme
        e=reagents.getsample(enzName)
        v=[a[3]/e.conc.dilutionneeded() for a in torun]
        t=[a[1] for a in torun]
        self.e.multitransfer(v,e,t)

        # Make the target have 'none' concentration so we can multiadd to it again
        for s in t:
            s.conc=None

        # Fill the master mixes
        dil={}
        for p in primers:
            mname="P-%s"%p
            if not reagents.isReagent(mname):
                reagents.add(name=mname,conc=4,extraVol=30)
            mq=reagents.getsample(mname)
            t=[a[1] for a in torun if a[2]==p]
            v=[a[3]/mq.conc.dilutionneeded() for a in torun if a[2]==p]
            assert all([x>0 for x in v])
            self.e.multitransfer(v,mq,t,(False,False))
            dil[p]=1.0/(1-1/e.conc.dilutionneeded()-1/mq.conc.dilutionneeded())
            
        # Add the samples
        self.e.sanitize()		# In case we are aligned
        for a in torun:
            s=a[0]
            t=a[1]
            p=a[2]
            v=a[3]/dil[p]
            t.conc=None		# Concentration of master mix is irrelevant now
            self.e.transfer(v,s,t)
            
        return [a[1] for a in torun]

    def setup(self):
        """Setup for experiment -- run once.  Usually overridden by actual experiment"""
        worklist.setOptimization(True)

    def pgm(self):
        """Actual robot code generation -- may be run multiple times to establish initial volumes.  Overridden by actual experiment"""

    def run(self):
        parser=argparse.ArgumentParser(description="TRP")
        parser.add_argument('-v','--verbose',help='Enable verbose output',default=False,action="store_true")
        parser.add_argument('-D','--dewpoint',type=float,help='Dew point',default=10.0)
        parser.add_argument('-p','--password',type=str,help='DB Password')
        parser.add_argument('-N','--nodb',help='No DB logging',default=False,action="store_true")

        args=parser.parse_args()

        # Turn on DB access if needed
        Config.usedb=not args.nodb
        if args.password is not None:
            Config.password = args.password

        print("Estimating evaporation for dew point of %.1f C"%args.dewpoint)
        globals.dewpoint=args.dewpoint
        self.reset()

        self.setup()
        if args.verbose:
            globals.verbose=True
            print('------ Preliminary runs to set volume -----')
        else:
            sys.stdout=open(os.devnull,'w')
        self.pgm()
        if args.verbose:
            print('------ Second preliminary run to set volume -----')
        self.reset()
        self.pgm()
        if args.verbose:
            print('------ Main run -----')
        else:
            sys.stdout=sys.__stdout__


        self.reset()
        self.pgm()
        self.finish()
