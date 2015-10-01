'A liquid class'

SURFACEREMOVE=0.4	# Extra removed from wells due to tip wetting (assuming liquid detecting, aspirating 3.5mm below surface)

class LC(object):
    def __init__(self,name,singletag=0,singlelag=0,multicond=0,multiexcess=0,multitag=0,wetvolume=SURFACEREMOVE,ldetect=False):
        self.name=name
        self.multicond=multicond
        self.multiexcess=multiexcess
        self.singletag=singletag
        self.singlelag=singlelag
        self.multitag=multitag
        self.wetvolume=wetvolume
        self.ldetect=ldetect
        
    def __str__(self):
        #        return "%s(%d,%d,%d)"%(self.name,self.singletag,self.multicond,self.multiexcess)
        return self.name

    def volRemoved(self, vol, multi=True):
        # Compute actual amount removed when 'vol' is requested
        if multi:
            return vol+self.multiexcess+self.wetvolume
        else:
            return vol+self.wetvolume
        
LCWaterBottom=LC("Water-Bottom",singlelag=1,multiexcess=1)
LCWaterPierce=LC("Water-Pierce",singlelag=1,multiexcess=1)
LCWaterBottomSide=LC("Water-BottomSide",singlelag=1,multiexcess=1)
LCWaterBottomBeads=LC("Water-BottomBeads",singlelag=1,multiexcess=0)
LCWaterInLiquid=LC("Water-InLiquid",singlelag=1,multiexcess=1,ldetect=True)
LCMixSlow=LC("Water-MixSlow",multiexcess=1)
LCMix={height: LC("Mix_%d"%height,multiexcess=1) for height in range(1,13)}
LCBlowout={height: LC("Blowout_%d"%height,multiexcess=1) for height in range(1,15)}
LCAir=LC("Air")
LCBleachMix=LC("RNaseAway-Mix",  singletag=10,multiexcess=2,multitag=10)
LCDip=LC("Dip",multiexcess=1)

