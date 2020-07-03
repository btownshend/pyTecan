import os
from .plate import Plate
from .platetype import PlateType
from .platelocation import PlateLocation

from .liquidclass import LCBleachMix,LCTrough

############ Plate types  #############
hspmaxspeeds={200:1400,150:1600,100:1850,50:2000,20:2200}	# From shaketest experiment
grenmaxspeeds={150:1750,125:1900,100:1950,75:2200,50:2200}	# From shaketest experiment
eppmaxspeeds={170:1200,119:1225,112:1300,91:1450,67:1600,58: 1700,40:1900,20:2000,0:2150} # From 10/24/17-run3
#eppmaxspeeds={195:1600,150:1800,125:1900,100:1950,75:2050,50:2150,25:2150,0:2150} # From shaketest experiment 5/17/16
#eppdilmaxspeeds={195:1400,150:1600,125:1700,100:1750,75:1850,50:1950,25:1950,0:1950} # Decrease by 200 RPM 7/7/16 to avoid spilling
#eppmaxspeeds={195:0,150:1150,138:1250,100:1350,75:1850,50:1950,25:1950,0:1950} # Decrease based on 9/23/16 testing with MTaq
#eppglycerolmaxspeeds={195:0,150:1150,138:1250,100:1350,90:1450,80:1500,70:1550,60:1650,50:1750,40:1950,20:2000,0:2000} # Decrease based on 10/21/16 testing with MTaq (with Glycerol @ 0.5%)
eppglycerolmaxspeeds=eppmaxspeeds
eppminspeeds={0:1900,20:1900,32:1800,64:1700,96:1400,150:1100}  # 1100@150ul untested

# Unusable volume is based on volume remaining at ZMax-1.5 (which is what Water-Bottom LC aspirates at)
# ZMax is from Carrier.cfg for the rack (zcoords.max)
TROUGH = PlateType("Trough 100ml",nx=1,ny=4,pierce=False,unusableVolume=100,maxVolume=100000,gemDepth=0,gemArea=1232,gemShape='flat',zmax=24.3)
EPPLOWBIND=PlateType("EppLoBind on carrier",nx=12,ny=8,pierce=False,unusableVolume=15,maxVolume=200,zmax=5.4,
                angle=17.5,r1=2.724,h1=8.49,v0=13.48,
                gemDepth=1.92, gemArea=13.51,
                gemShape='v-shaped',maxspeeds=eppmaxspeeds,minspeeds=eppminspeeds,glycerolmaxspeeds=eppglycerolmaxspeeds,glycerol=1)  # EppLoBind
RICBLOCK=PlateType("RIC Eppendorfs",nx=6,ny=5,pierce=False,unusableVolume=20,maxVolume=1700,angle=17.5,r1=4.088,h1=16.91,v0=10.23,gemDepth=1.02,gemArea=13.52,gemShape='v-shaped',
                   zmax=-0.6)
WHITEQPCR=PlateType("QPCR on HSP96xx",nx=12,ny=8,pierce=False,unusableVolume=15,maxVolume=200,zmax=9.9,
                angle=17.5,r1=2.704,h1=10.89,v0=0.44,gemDepth=3.17,gemArea=14.33,gemShape='v-shaped')
EPPRACK = PlateType("Eppendorf Tube, 16 Pos.", nx=1, ny=16, pierce=False, unusableVolume=30, maxVolume=1500,angle=17.5,zmax=37.1,
                r1=4.407,h1=17.34,v0=22.11,
                gemDepth=1.29, gemArea=16.98, gemShape='v-shaped')
CLEAR384=PlateType("384 Well, clear on carrier",nx=24,ny=16,yspacing=4.5,pierce=False,unusableVolume=15,maxVolume=130,zmax=5.1,
                gemArea=12.15, h1=-1.27,   # TODO
                gemShape='flat',maxspeeds=eppmaxspeeds,minspeeds=eppminspeeds,glycerolmaxspeeds=eppglycerolmaxspeeds,glycerol=1)  # TODO
GRENIER384=PlateType("Grenier384",nx=24,ny=16,yspacing=4.5,pierce=False,unusableVolume=15,maxVolume=130,zmax=5.2,
                angle=17.5,r1=2.070,h1=2.31,v0=26.2, 
                gemDepth=-0.44, gemArea=13.30,
                gemShape='v-shaped',maxspeeds=eppmaxspeeds,minspeeds=eppminspeeds,glycerolmaxspeeds=eppglycerolmaxspeeds,glycerol=1)  # TODO

############ Plate locations  #############
# Plate locations are roughly equivalent to Gemini carriers
# Note: We currently tie the zmax to the location, since the same plate can be moved to different locations resulting in different heights
#   However, this creates a problem if a different plate type is moved to the same location
#   TODO: Make locations more like racks (with a base height) and then plates have a zmax that is relative to that
# Or, maybe, we don't really need the zmax here -- the parselog can retrieve the zmax that was being used at runtime
# A particular volume formula goes along with a particular zmax though...
WATERLOC=PlateLocation("Water",3,2,carrierName="Trough 100ml, 3 Pos.",zoffset=10.0)
BLEACHLOC=PlateLocation("Bleach",3,3,carrierName="Trough 100ml, 3 Pos.",zoffset=10.0)
SSDDILLOC=PlateLocation("SSDDil",3,1,carrierName="Trough 100ml, 3 Pos.",zoffset=10.0)

RICLOC=PlateLocation("RIC",18,1,slopex=0,slopey=0,carrierName="RIC, Microplate",zoffset=6.2+108.7)
MAGPLATELOC=PlateLocation("MagPlate",18,2,vectorName="Magplate")
SHAKERPLATELOC=PlateLocation("Shaker",9,0,vectorName="Shaker",lihaAccess=False)
SAMPLELOC=PlateLocation("SampleLoc",4,3,vectorName="Microplate Landscape",carrierName="MP, 3 Pos., landscape, RoMa",
                        zoffset=62.5)
DILUTIONLOC=PlateLocation("DilutionLoc",4,2,vectorName="Microplate Landscape",carrierName="MP, 3 Pos., landscape, RoMa",
                          zoffset=62.5)
PRODUCTLOC=PlateLocation("ProductLoc",18,2,vectorName="Microplate Product",carrierName="RIC, Microplate", zoffset=6.2)
QPCRLOC=PlateLocation("QPCRLoc",4,1,carrierName="MP, 3 Pos., landscape, RoMa",zoffset=62.5)  # defined in worklist.py
WASHLOC=PlateLocation("Wash",1,2,lihaAccess=False,carrierName="Wash Station")  # defined in worklist.py
EPPLOC=PlateLocation("EppLoc",13,1,carrierName="Eppendorf Tube, 16 Pos.",zoffset=0.0)
TCPOS=PlateLocation("TC",25,1,vectorName="TROBOT",lihaAccess=False)
HOTELPOS = PlateLocation("Hotel",25, 0, lihaAccess=False)
WASTE = PlateLocation("Waste",20, 3, lihaAccess=False)
HOTEL = [ PlateLocation(f"Hotel{i+1}",25,0, lihaAccess=False,vectorName=f"Hotel{i+1}") for i in range(6) ]

############ Physical Plates #############
WATERTROUGH=Plate(name="Water",plateType=TROUGH, plateLocation=WATERLOC)
BLEACHTROUGH=Plate(name="Bleach",plateType=TROUGH, plateLocation=BLEACHLOC)
SSDTROUGH=Plate(name="SSDDil",plateType=TROUGH, plateLocation=SSDDILLOC)

SAMPLEPLATE=Plate(name="Samples",plateType=EPPLOWBIND,plateLocation=SAMPLELOC)
DILPLATE=Plate(name="Dilutions",plateType=EPPLOWBIND,plateLocation=DILUTIONLOC,backupPlate=SAMPLEPLATE)
EPPENDORFS=Plate(name="Eppendorfs",plateType=EPPRACK,plateLocation=EPPLOC)
REAGENTPLATE=Plate(name="Reagents",plateType=RICBLOCK, plateLocation=RICLOC)
QPCRPLATE=Plate(name="QPCR",plateType=WHITEQPCR, plateLocation=QPCRLOC)
PRODUCTPLATE=Plate(name="Products",plateType=EPPLOWBIND,plateLocation=PRODUCTLOC)

#TIPOFFSETS=[390, 389, 394, 387]
TIPOFFSETS=[390, 390, 390, 390]


############ Well-known samples  #############
WATER=None
SSDDIL=None
BLEACH=None


def initWellKnownSamples():
    global WATER, SSDDIL, BLEACH
    from .sample import Sample

    WATER=Sample("Water",WATERTROUGH,-1,None,100000)
    WATER.inliquidLC=LCTrough    # Faster liquid detect
    SSDDIL=Sample("SSDDil",SSDTROUGH,-1,None,100000)
    SSDDIL.inliquidLC=LCTrough  # Faster liquid detect
    BLEACH=Sample("RNase-Away",BLEACHTROUGH,-1,None,100000,mixLC=LCBleachMix)


############ Header file containing matching deck layout  #############
headerfile=os.path.join(os.path.dirname(__file__),"../header.gem")
headerfile384samp=os.path.join(os.path.dirname(__file__),"../header384samp.gem")
