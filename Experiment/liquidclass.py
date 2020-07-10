"""A liquid class"""
import sys

SURFACEREMOVE=0.4	# Extra removed from wells due to tip wetting (assuming liquid detecting, aspirating 3.5mm below surface)


class LC(object):
    __alllc = []

    def __init__(self,name,singletag=0,singlelag=0,multicond=0,multiexcess=0,multitag=0,wetvolume=SURFACEREMOVE,ldetect=False,submerge=None):
        self.name=name
        self.multicond=multicond
        self.multiexcess=multiexcess
        self.singletag=singletag
        self.singlelag=singlelag
        self.multitag=multitag
        self.wetvolume=wetvolume
        self.ldetect=ldetect
        self.submerge=submerge
        self.used={}
        LC.__alllc.append(self)

    @staticmethod
    def printalllc(fd=sys.stdout):
        print("Liquid classes used:", file=fd)
        for lc in sorted(LC.__alllc, key=lambda p:p.name.upper()):
            ops=list(lc.used.keys())
            if len(ops)>0:
                print(lc.fullstr(), file=fd)

    def __str__(self):
        #        return "%s(%d,%d,%d)"%(self.name,self.singletag,self.multicond,self.multiexcess)
        return self.name

    @classmethod
    def lookupByName(cls,name):
        for p in LC.__alllc:
            if p.name==name:
                return p
        return None

    def fullstr(self):
        # Full details
        return "%-20s"%self.name+"("+" ".join(sorted(list(self.used.keys())))+") multi: (cond=%.1f, excess=%.1f, tag=%.1f)"%(self.multicond,self.multiexcess,self.multitag)+ ", single: (tag=%.1f, lag=%.1f)"%(self.singletag,self.singlelag)+", wetvol=%.1f"%self.wetvolume+", ldetect=%d"%self.ldetect

    def markUsed(self,op):
        self.used[op]=True

    def volRemoved(self, vol, multi=True):
        # Compute actual amount removed when 'vol' is requested
        if multi:
            return vol+self.multiexcess+self.wetvolume
        else:
            return vol+self.wetvolume

LCWaterAboveLiquid=LC("Water-Above",singlelag=1,multiexcess=1)
LCWaterBottom=LC("Water-Bottom",singlelag=1,multiexcess=1)
LCPreciousBottom=LC("Water-Bottom",singlelag=1,multiexcess=0)
LCWaterPierce=LC("Water-Pierce",singlelag=1,multiexcess=1)
LCWaterBottomSide=LC("Water-BottomSide",singlelag=1,multiexcess=1)
LCWaterBottomBeads=LC("Water-BottomBeads",singlelag=1,multiexcess=0)
LCWaterInLiquid=LC("Water-InLiquid",singlelag=1,multiexcess=1,ldetect=True,submerge=1)
LCPreciousInLiquid=LC("Precious-InLiquid",singlelag=1,multiexcess=0,ldetect=True,submerge=1)
LCMixSlow=LC("Water-MixSlow",multiexcess=1)
LCMix={height: LC("Mix_%d"%height,multiexcess=1) for height in range(1,30)}
LCMixBottom=LC("Water-MixBottom",multiexcess=1)
LCBlowoutLD=LC("Blowout_LD",multiexcess=1,singlelag=1,ldetect=True)
LCAir=LC("Air")
LCBleachMix=LC("RNaseAway-Mix",  singletag=10,multiexcess=2,multitag=10)
LCDip=LC("Dip",multiexcess=1)
LCPrefilled=LC("Prefilled")
LCTrough=LC("Trough-LD",singlelag=1,multiexcess=1,ldetect=True,submerge=1)   # Use faster liquid detect for troughs
