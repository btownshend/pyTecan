import sys
import math
import liquidclass
from worklist import WorkList
from concentration import Concentration


MAXVOLUME=200
MINLIQUIDDETECTVOLUME=15
#MINLIQUIDDETECTVOLUME=1000  # Liquid detect may be broken
#MINMIXTOPVOLUME=50   # Use manual mix if trying to mix more than this volume  (aspirates at ZMax-1.5mm, dispenses at ZMax-5mm)
MINMIXTOPVOLUME=1e10   # Disabled manual mix -- may be causing bubbles
SHOWTIPS=False
SHOWTIPHISTORY=False
SHOWINGREDIENTS=False
MINDEPOSITVOLUME=5.0	# Minimum volume to end up with in a well after dispensing
MINSIDEDISPENSEVOLUME=10.0  # minimum final volume in well to use side-dispensing.  Side-dispensing with small volumes may result in pulling droplet up sidewall
EVAPTIME=3600	# Time in seconds after which to give an evaporation warning

_Sample__allsamples = []
tiphistory={}

#Updated LC's:
# Water-Bottom
# Fixed Aspirate (single): 20ul/s, 200ms, STAG=20,LAG=1 (WAS 0),TAG=0,EXC=0,COND=0, zmax-1.5mm , retract to z-start  20mm/s
# Fixed Aspirate (multi): 20ul/s, 200ms, STAG=20,LAG=0,TAG=0,EXC=1 (to waste),COND=0
# Fixed Dispense (single): 100ul/s, 100ul/s, 500ms, no TAG after each dispense, no LD, z-max -1.5mm, touch left @10mm/s;100ms (WAS no touch), retract to z-dispense 20 mm/s
# Fixed Dispense (multi): 100ul/s, 100ul/s, 500ms), no TAG after each dispense
#
# Water-InLiquid
# Detect simultaneously and twice with all tips, cond good, det 60mm/s, double 4mm/s
# Fixed Aspirate (single): 20ul/s, 200ms, STAG=20,LAG=1,TAG=0,EXC=0,COND=0, liquid detect +3.5mm center with tracking, retract to liquid level-5mm  20mm/s
# Fixed Aspirate (multi): 20ul/s, 200ms, STAG=20,LAG=0,TAG=0,EXC=2 (to waste),COND=0 
# Fixed Dispense (single): 100ul/s, 100ul/s, 500ms, no TAG after each dispense, no LD, liquid detect +1mm center with tracking, retract to liquid level-5mm  20 mm/s
# Fixed Dispense (multi): 100ul/s, 100ul/s, 500ms(WAS 0), no TAG after each dispense
# Water-Mix
# Fixed Aspirate (single): 100ul/s, 200ms, STAG=20,LAG=0,TAG=0,EXC=0,COND=0,zmax-1.5mm, retract to z-dispense  20mm/s
# Fixed Aspirate (multi): 20ul/s, 200ms, STAG=20,LAG=0,TAG=0,EXC=1 (to waste),COND=0
# Fixed Dispense (single): 225ul/s, 225ul/s, 500ms, no TAG after each dispense, no LD, z-max -5mm, no touch, retract to z=dispense 20 mm/s
# Fixed Dispense (multi): 225ul/s, 225ul/s, 500ms, no TAG after each dispense

#Water-BottomSide 
# Same as water-Bottom, but dispense with tip at right side
# Fixed Aspirate (single): 20ul/s, 200ms, STAG=20,LAG=1 (WAS 0),TAG=0,EXC=0,COND=0, zmax-1.5mm , retract to z-start  20mm/s
# Fixed Aspirate (multi): 20ul/s, 200ms, STAG=20,LAG=0,TAG=0,EXC=1 (to waste),COND=0
# Fixed Dispense (single): 100ul/s, 100ul/s, 500ms, no TAG after each dispense, no LD, z-max -1.5mm (right side), touch left @10mm/s;100ms (WAS no touch), retract to z-dispense 20 mm/s
# Fixed Dispense (multi): 100ul/s, 100ul/s, 500ms), no TAG after each dispense
# Sometimes gives small bubbles on right side usually near surface, usually tip 2

#Water-MixSlow
# Same as water-Bottom, but single 20ul/s,20ul dispense (for mixing without bubbles)
#   Seems that faster dispense creates bubbles, unsure why
# Fixed Aspirate (single): 20ul/s, 200ms, STAG=20,LAG=1 (WAS 0),TAG=0,EXC=0,COND=0, zmax-1.5mm , retract to z-start  20mm/s
# Fixed Aspirate (multi): 20ul/s, 200ms, STAG=20,LAG=0,TAG=0,EXC=1 (to waste),COND=0
# Fixed Dispense (single): 20ul/s, 20ul/s, 500ms, no TAG after each dispense, no LD, z-max -1.5mm, touch left @10mm/s;100ms (WAS no touch), retract to z-dispense 20 mm/s
# Fixed Dispense (multi): 100ul/s, 100ul/s, 500ms), no TAG after each dispense
#

class Sample(object):
    @staticmethod
    def printallsamples(txt="",fd=sys.stdout,w=None):
        print >>fd,"\n%s by plate:"%txt
        plates=set([s.plate for s in __allsamples]);
        for p in sorted(plates, key=lambda p:p.name.upper()):
            print >>fd,"Samples in plate: ",p
            for s in __allsamples:
                if len(s.history)==0:
                    continue   # Not used
                if s.plate==p:
                    if w!=None:
                        print >>fd,s,("%06x"%(w.getHashCode(grid=s.plate.grid,pos=s.plate.pos,well=s.well)&0xffffff))
                    else:
                        print >>fd,s
            print >>fd
        if SHOWTIPS and SHOWTIPHISTORY:
            print >>fd,"\nTip history:\n"
            for t in tiphistory:
                print >>fd,"%d: %s\n"%(t,tiphistory[t])
            
    @staticmethod
    def numSamplesOnPlate(plate):
        cnt=0
        for s in __allsamples:
            if s.plate==plate and len(s.history)>0:
                cnt+=1
        return cnt
        
    def __init__(self,name,plate,well=None,conc=None,volume=0,hasBeads=False,extraVol=50):
        if well!=None and well!=-1:
            if not isinstance(well,int):
                well=plate.wellnumber(well)
            for s in __allsamples:
                if s.well==well and s.plate==plate:
                    print "Attempt to assign sample %s to plate %s, well %s that already contains %s"%(name,str(plate),plate.wellname(well),s.name)
                    well=None
                    break
            
        if well==None:
            # Find first unused well
            found=False
            well=0
            while not found:
                found=True
                for s in __allsamples:
                    if s.plate==plate and s.well==well:
                        well=well+1
                        found=False
                        break
        elif well==-1:
            well=None
                    
        for s in __allsamples:
            if s.plate==plate and s.well==well:
                print "Attempt to assign sample %s to plate %s, well %s that already contains %s"%(name,str(plate),plate.wellname(well),s.name)
#                print "Aliasing %s as %s"%(s.name,name)
                assert(False)
            if s.name==name:
                print "Already have a sample called %s"%name
                assert(False)
        self.name=name
        self.plate=plate
        if well>=plate.nx*plate.ny:
                print "Overflow of plate %s"%str(plate)
                for s in __allsamples:
                    if s.plate==plate:
                        print s
                assert(False)
                
        self.well=well
        if isinstance(conc,Concentration) or conc==None:
                self.conc=conc
        else:
                self.conc=Concentration(conc)
        self.volume=volume
        self.initvolume=volume
        if volume>0:
            self.ingredients={name:volume}
        else:
            self.ingredients={}
            
        if plate.pierce:
            self.bottomLC=liquidclass.LCWaterPierce
            self.bottomSideLC=bottomLC  # Can't use side with piercing
            self.inliquidLC=self.bottomLC  # Can't use liquid detection when piercing
        else:
            self.bottomLC=liquidclass.LCWaterBottom
            self.bottomSideLC=liquidclass.LCWaterBottomSide
            self.inliquidLC=liquidclass.LCWaterInLiquid

        self.beadsLC=liquidclass.LCWaterBottomBeads
        self.mixLC=liquidclass.LCMixSlow
        self.airLC=liquidclass.LCAir
        # Same as bottom for now 
        self.emptyLC=self.bottomLC
        self.history=""
        __allsamples.append(self)
        self.isMixed=True
        self.initHasBeads=hasBeads
        self.hasBeads=hasBeads		# Setting this to true overrides the manual conditioning
        self.extraVol=extraVol			# Extra volume to provide
        self.firstdispense = 0					# Last time accessed
        
    @classmethod
    def clearall(cls):
        'Clear all samples'
        for s in __allsamples:
            s.volume=s.initvolume
            s.history=""
            s.isMixed=True
            s.hasBeads=s.initHasBeads
            if s.volume==0:
                s.conc=None
                s.ingredients={}
            else:
                s.ingredients={s.name:s.volume}
            s.firstdispense = 0					# Last time accessed

    @classmethod
    def lookup(cls,name):
        for s in __allsamples:
            if s.name==name:
                return s
        return None
    
    @classmethod
    def lookupByWell(cls,plate,well):
        for s in __allsamples:
            if s.plate==plate and s.well==well:
                return s
        return None
    
    @classmethod
    def getAllOnPlate(cls,plate=None):  
        result=[]
        for s in __allsamples:
            if plate==None or s.plate==plate:
                result.append(s)  
        return result 
                 
    @classmethod
    def getAllLocOnPlate(cls,plate=None):  
        result=""
        for s in __allsamples:
            if (plate==None or s.plate==plate) and s.volume!=s.initvolume:
                result+=" %s"%(s.plate.wellname(s.well))
        return result 

    def dilute(self,factor):
        'Dilute sample -- just increases its recorded concentration'
        if self.conc!=None:
                self.conc=self.conc.dilute(1.0/factor)

    def evapcheck(self,w,op):
        'Check if the time between accesses of a well is too long'
        # Not quite right -- doesn't take into account thermocycler time
        if self.firstdispense>0 and w.elapsed-self.firstdispense>EVAPTIME and self.plate.name!="Reagents" and op=='aspirate':
            print "WARNING:  %s (%s.%s, vol=%.1f ul) accessed after %.0f minutes, evaporation may be an issue"%(self.name,str(self.plate),self.plate.wellname(self.well),self.volume, (w.elapsed-self.firstdispense)/60)
            self.history= self.history + (' [Evap: %d]'%( (w.elapsed-self.firstdispense)/60))
            self.firstdispense=-1	# Don't mention again
        if op=='dispense' and self.firstdispense==0:
            self.firstdispense=w.elapsed
        
    def aspirate(self,tipMask,w,volume,multi=False):
        self.evapcheck(w,'aspirate')
        if self.plate.curloc=='PTC':
            print "Aspirate from PTC!, loc=",self.plate.grid,",",self.plate.pos
            assert(False)

        if volume<2 and not multi and self.name!="Water":
            print "WARNING: Inaccurate for < 2ul:  attempting to aspirate %.1f ul from %s"%(volume,self.name)
        if volume>self.volume and self.volume>0:
            print "ERROR:Attempt to aspirate %.1f ul from %s that contains only %.1f ul"%(volume, self.name, self.volume)
        if not self.isMixed:
            print "WARNING: Aspirate %.1f ul from unmixed sample %s. "%(volume,self.name)

        if self.well==None:
                well=[]
                for i in range(4):
                        if (tipMask & (1<<i)) != 0:
                            well.append(i)
        else:
                well=[self.well]
        
        lc=self.chooseLC(volume)
        if self.hasBeads and self.plate.curloc=="Magnet":
            # With beads don't do any manual conditioning and don't remove extra (since we usually want to control exact amounts left behind, if any)
            w.aspirateNC(tipMask,well,lc,volume,self.plate)
            remove=lc.volRemoved(volume,multi=False)
            if self.volume==volume:
                # Removing all, ignore excess remove
                remove=self.volume
                self.ingredients={}
        else:
            if self.hasBeads:
                #print "%s has beads -- mixing before aspirate"%self.name
                self.mix(tipMask,w)
            w.aspirate(tipMask,well,lc,volume,self.plate)
            # Manual conditioning handled in worklist
            remove=lc.volRemoved(volume,multi=True)

        if self.volume<remove and self.volume>0:
            print "WARNING: Removing all contents (%.1f from %.1ful) from %s"%(remove,self.volume,self.name)
            remove=self.volume
            self.ingredients={}
        for k in self.ingredients:
            if self.plate.curloc=="Magnet" and k=='BIND':
                pass
            else:
                self.ingredients[k] *= (self.volume-remove)/self.volume

        self.volume=self.volume-remove
        if self.volume+.001<self.plate.unusableVolume and self.volume>0:
            # TODO - this should be more visible in output
            print "Warning: Aspiration of %.1ful from %s brings volume down to %.1ful which is less than its unusable volume of %.1f ul"%(remove,self.name,self.volume,self.plate.unusableVolume)

        self.addhistory("",-remove,tipMask)

    def aspirateAir(self,tipMask,w,volume):
        'Aspirate air over a well'
        w.aspirateNC(tipMask,[self.well],self.airLC,volume,self.plate)
        
    def dispense(self,tipMask,w,volume,src):
        self.evapcheck(w,'dispense')
        if self.plate.curloc=='PTC':
            print "Dispense to PTC!, loc=",self.plate.grid,",",self.plate.pos
            assert(False)
            
        if self.volume+volume < MINDEPOSITVOLUME:
            print "Warning: Dispense of %.1ful into %s results in total of %.1ful which is less than minimum deposit volume of %.1f ul"%(volume,self.name,self.volume+volume,MINDEPOSITVOLUME)

        #well=[self.well if self.well!=None else 2**(tipMask-1)-1 ]
        well=[self.well if self.well!=None else int(math.log(tipMask,2)) ]
        if self.well==None:
            print "Warning: Dispense with well==None, not sure what right logic is..., using well=%d"%well[0]

        if self.volume+volume > self.plate.maxVolume:
            print "Warning: Dispense of %.1ful into %s results in total of %.1ful which is more than the maximum volume of %.1f ul"%(volume,self.name,self.volume+volume,self.plate.maxVolume)
            
        if self.hasBeads and self.plate.curloc=="Magnet":
            w.dispense(tipMask,well,self.beadsLC,volume,self.plate)
        elif self.volume>=MINLIQUIDDETECTVOLUME:
            w.dispense(tipMask,well,self.inliquidLC,volume,self.plate)
        elif self.volume+volume>=MINSIDEDISPENSEVOLUME:
            w.dispense(tipMask,well,self.bottomSideLC,volume,self.plate)
        else:
            w.dispense(tipMask,well,self.bottomLC,volume,self.plate)

        # Assume we're diluting the contents
        if self.conc==None and src.conc==None:
            pass
        elif src.conc==None or volume==0:
            if self.volume==0:
                self.conc=None
            else:
                self.conc=self.conc.dilute((self.volume+volume)/self.volume)
        elif self.conc==None or self.volume==0:
            self.conc=src.conc.dilute((self.volume+volume)/volume)
        else:
            # Both have concentrations, they should match
            c1=self.conc.dilute((self.volume+volume)/self.volume)
            c2=src.conc.dilute((self.volume+volume)/volume)
            if ( abs(c1.stock/c1.final-c2.stock/c2.final)>.01 ):
                print "Warning: Dispense of %.1ful of %s@%.2fx into %.1ful of %s@%.2fx does not equalize concentrations"%(volume,src.name,src.conc.dilutionneeded(),self.volume,self.name,self.conc.dilutionneeded())
                #assert(abs(c1.stock/c1.final-c2.stock/c2.final)<.01)
                self.conc=None
            else:
                self.conc=Concentration(c1.stock/c1.final,1.0,'x')  # Since there are multiple ingredients express concentration as x

         # Set to not mixed after second ingredient added
        self.isMixed=self.volume==0
        if src.hasBeads and src.plate.curloc!="Magnet":
            #print "Set %s to have beads since %s does\n"%(self.name,src.name)
            self.hasBeads=True
            self.isMixed=False
        self.volume=self.volume+volume
        self.addhistory(src.name,volume,tipMask)
        self.addingredients(src,volume)
            
    def addhistory(self,name,vol,tip):
        if vol>=0:
            if SHOWTIPS:
                    str="%s[%.1f#%d]"%(name,vol,tip)
            else:
                    str="%s[%.1f]"%(name,vol)
            if len(self.history)>0:
                self.history=self.history+" +"+str
            else:
                self.history=str
        elif vol<0:
            if SHOWTIPS:
                    str="%s[%.1f#%d]"%(name,-vol,tip)
            else:
                    str="%s[%.1f]"%(name,-vol)
            if len(self.history)>0:
                self.history=self.history+" -"+str
            else:
                self.history="-"+str
        name=self.name
        if name=="RNase-Away":
            if tip in tiphistory and tiphistory[tip][-1]=='\n':
                tiphistory[tip]=tiphistory[tip][:-1]
            fstr="*\n"
        elif vol==0:
            fstr=name
        else:
            fstr="%s[%d]"%(name,vol)
        if tip in tiphistory:
            tiphistory[tip]+=" %s"%fstr
        else:
            tiphistory[tip]=fstr

    @staticmethod
    def addallhistory(msg,addToEmpty=False,onlyplate=None,onlybeads=False):
        'Add history entry to all samples (such as # during thermocycling)'
        for s in __allsamples:
            if (onlyplate==None or onlyplate==s.plate.name) and (not onlybeads or s.hasBeads):
                if len(s.history)>0:
                    s.history+=" "+msg
                elif addToEmpty:
                    s.history=msg
            
    @staticmethod
    def mixall(plate):
        'Mark all on given plate as mixed'
        for s in __allsamples:
            if plate==s.plate.name and s.volume>0:
                s.isMixed=True
                
    def addingredients(self,src,vol):
        'Update ingredients by adding ingredients from src'
        for k in src.ingredients:
            if src.plate.curloc=="Magnet" and k=='BIND-UNUSED':
                pass  # Wasn't transferred
            else:
                addition=src.ingredients[k]/src.volume*vol
                if k in self.ingredients:
                    self.ingredients[k]+=addition
                else:
                    self.ingredients[k]=addition
            
    def chooseLC(self,aspirateVolume=0):
        if self.volume-aspirateVolume>=MINLIQUIDDETECTVOLUME:
            return self.inliquidLC
        elif self.volume==0 and aspirateVolume==0:
            return self.emptyLC
        elif self.hasBeads and self.plate.curloc=="Magnet":
            return self.beadsLC
        else:
            return self.bottomLC
        
        # Mix, return true if actually did a mix, false otherwise
    def mix(self,tipMask,w,preaspirateAir=False,nmix=4):
        if self.isMixed and not self.hasBeads:
            #print "Sample %s is already mixed"%self.name
            return False
        blowvol=20
        extraspace=blowvol+0.1
        if preaspirateAir:
            extraspace+=5
        mixvol=self.volume		  # -self.plate.unusableVolume;  # Can mix entire volume, if air is aspirated, it will just be dispensed first without making a bubble
        if self.volume>MAXVOLUME-extraspace:
            mixvol=MAXVOLUME-extraspace
            print "Warning: Mix of %s limited to %.0f ul instead of full volume of %.0ful"%(self.name,mixvol,self.volume)
        well=[self.well if self.well!=None else 2**(tipMask-1)-1 ]
        if mixvol<self.plate.unusableVolume:
            #print "Not enough volume in sample %s to mix"%self.name
            self.history+="(UNMIXED)"
            return False
        else:
            if preaspirateAir:
                # Aspirate some air to avoid mixing with excess volume aspirated into pipette from source in previous transfer
                self.aspirateAir(tipMask,w,5)
            if self.volume>=MINLIQUIDDETECTVOLUME:
                w.mix(tipMask,well,self.inliquidLC,mixvol,self.plate,nmix)
                self.history+="(MLD)"
            else:
                height=self.plate.getliquidheight(self.volume)
                if height==None:
                    w.mix(tipMask,well,self.mixLC,mixvol,self.plate,nmix)
                    self.history+="(MB*)"
                else:
                    mixheight=math.floor(height-1)			# At least 1mm below liquid height
                    if mixheight<2:
                        mixheight=2
                    blowheight=math.ceil(height)			# Anywhere above
#                    print 'Vol=%.1f ul, height=%.1f mm, mix=%d, blow=%d'%(self.volume,height,mixheight,blowheight)
                    mixLC=liquidclass.LCMix[mixheight]
                    blowoutLC=liquidclass.LCBlowout[blowheight]
                    w.aspirateNC(tipMask,well,self.airLC,(blowvol+0.1),self.plate)
                    if self.volume<30:
                        w.mix(tipMask,well,self.mixLC,mixvol,self.plate,nmix)
                        self.history+="(MB)"
                    else:
                        for i in range(nmix):
                            w.aspirateNC(tipMask,well,mixLC,mixvol,self.plate)
                            w.dispense(tipMask,well,mixLC,mixvol,self.plate)
                        self.history+="(M@%d)"%(mixheight)
                    w.dispense(tipMask,well,blowoutLC,blowvol,self.plate)
                    w.dispense(tipMask,well,liquidclass.LCDip,0.1,self.plate)

            tiphistory[tipMask]+=" %s-Mix[%d]"%(self.name,mixvol)
            self.isMixed=True
            return True
            
    def __str__(self):
        s="%-32s "%(self.name)
        if self.conc!=None:
            s+=" %-18s"%("[%s]"%str(self.conc))
        else:
            s+=" %-18s"%""
        if self.hasBeads:
            beadString=",beads"
        else:
            beadString=""
        s+=" %-30s"%("(%s.%s,%.2f ul%s)"%(str(self.plate),self.plate.wellname(self.well),self.volume,beadString))
        hist=self.history
        trunchistory=True
        if trunchistory and len(hist)>0:
            # Remove any trailing {xx} or (xx) markers from history
            wds=hist.strip().split(' ')
            for i in range(len(wds)-1,-1,-1):
                if wds[i][0]!='(' and wds[i][0]!='{':
                    break
            hist=' '.join(wds[:i+1])

        s+=" %s"%hist
        if SHOWINGREDIENTS:
                s+=self.ingredientstr()
        return s

    def ingredientstr(self):
        s="{"
        for k in self.ingredients:
            s+="%s:%.4g "%(k,self.ingredients[k])
        s+="}"
        return s

    @staticmethod
    def printprep(fd=sys.stdout):
        notes="Reagents to provide:"
        total=0
        for s in sorted(__allsamples, key=lambda p:p.well):
            if s.conc!=None:
                c="[%s]"%str(s.conc)
            else:
                c=""   
            if s.volume==s.initvolume:
                'Not used'
                #note="%s%s in %s.%s not consumed"%(s.name,c,str(s.plate),s.plate.wellname(s.well))
                #notes=notes+"\n"+note
            elif s.initvolume>0:
                note="%s%s in %s.%s consume %.1f ul, provide %.1f ul"%(s.name,c,str(s.plate),s.plate.wellname(s.well),s.initvolume-s.volume,s.initvolume)
                notes=notes+"\n"+note
            if s.plate.name=="Reagents":
                total+=round((s.initvolume-s.volume)*10)/10.0
        print >>fd,notes
        print >>fd,"Total reagents volume = %.1f ul"%total

    @staticmethod
    def savematlab(filename):
        fd=open(filename,"w")
        print >>fd,"samps=[];"
        for s in __allsamples:
            ing=""
            ingvol=""
            for k in s.ingredients:
                if len(ing)==0:
                    ing="'%s'"%k
                    ingvol="%g"%s.ingredients[k]
                else:
                    ing=ing+",'%s'"%k
                    ingvol=ingvol+",%g"%s.ingredients[k]
            
            print >>fd,"samps=[samps,struct('name','%s','plate','%s','well','%s','concentration','%s','history','%s','ingredients',{{%s}},'volumes',[%s])];"%(s.name,s.plate,s.plate.wellname(s.well),str(s.conc),s.history,ing,ingvol)
        fd.close()
