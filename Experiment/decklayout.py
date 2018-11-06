import os
from .plate import Plate
from .platetype import PlateType
from .platelocation import PlateLocation

from .liquidclass import LCBleachMix

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


TROUGH = PlateType("Trough",nx=1,ny=4,pierce=False,unusableVolume=100,maxVolume=100000,gemDepth=0,gemArea=1232,gemShape='flat')
EPPLOWBIND=PlateType("EppLowBind",nx=12,ny=8,pierce=False,unusableVolume=15,maxVolume=200,
                angle=17.5,r1=2.717,h1=8.22,v0=14.22,
                gemDepth=1.92, gemArea=13.51,
                gemShape='v-shaped',maxspeeds=eppmaxspeeds,minspeeds=eppminspeeds,glycerolmaxspeeds=eppglycerolmaxspeeds,glycerol=1)  # EppLoBind
RICBLOCK=PlateType("RICBlock",nx=6,ny=5,pierce=False,unusableVolume=20,maxVolume=1700,angle=17.5,r1=4.088,h1=16.91,v0=10.23,gemDepth=1.02,gemArea=13.52,gemShape='v-shaped')
WHITEQPCR=PlateType("qPCRPlate",nx=12,ny=8,pierce=False,unusableVolume=15,maxVolume=200,
                angle=17.5,r1=2.704,h1=10.89,v0=0.44,gemDepth=3.17,gemArea=14.33,gemShape='v-shaped')
EPPRACK = PlateType("EppRack", nx=1, ny=16, pierce=False, unusableVolume=30, maxVolume=1500,angle=17.5,
                r1=4.419,h1=17.40,v0=19.41, gemDepth=1.29, gemArea=16.98, gemShape='v-shaped')

############ Plate locations  #############
WATERLOC=PlateLocation("Water",3,2,zmax=1367)
BLEACHLOC=PlateLocation("Bleach",3,3,zmax=1367)
SSDDILLOC=PlateLocation("SSDDil",3,1,zmax=1367)

RICLOC=PlateLocation("RIC",18,1,slopex=0,slopey=0,zmax=567)
MAGPLATELOC=PlateLocation("MagPlate",18,2,zmax=1459,vectorName="Magplate")
SHAKERPLATELOC=PlateLocation("Shaker",9,0,vectorName="Shaker")
SAMPLELOC=PlateLocation("Home",4,3,zmax=1031,vectorName="Microplate Landscape")
DILUTIONLOC=PlateLocation("DilutionLoc",4,2,zmax=1031,vectorName="Microplate Landscape")
PRODUCTLOC=PlateLocation("ProductLoc",18,2,zmax=465,vectorName="Microplate Product")
QPCRLOC=PlateLocation("QPCRLoc",4,1,zmax=996)  # defined in worklist.py
WASHLOC=PlateLocation("Wash",1,2)  # defined in worklist.py
EPPLOC=PlateLocation("EppLoc",13,1,zmax=1339)
TCPOS=PlateLocation("TC",25,1,vectorName="TROBOT")
#TCPOS=PlateLocation("TC",25,1,vectorName="PTC200")
HOTELPOS = PlateLocation("Hotel",25, 0)
WASTE = PlateLocation("Waste",20, 3)

############ Physical Plates #############
WATERTROUGH=Plate(name="Water",plateType=TROUGH, plateLocation=WATERLOC)
BLEACHTROUGH=Plate(name="Bleach",plateType=TROUGH, plateLocation=BLEACHLOC)
SSDTROUGH=Plate(name="SSDDil",plateType=TROUGH, plateLocation=SSDDILLOC)

SAMPLEPLATE=Plate(name="Samples",plateType=EPPLOWBIND,plateLocation=SAMPLELOC)
SAMPLEPLATE.wells = SAMPLEPLATE.wells[1:-1]  # Skip A1 and H12 due to leakage
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

    WATER=Sample("Water",WATERTROUGH,-1,None,50000)
    SSDDIL=Sample("SSDDil",SSDTROUGH,-1,None,50000)
    BLEACH=Sample("RNase-Away",BLEACHTROUGH,-1,None,50000,mixLC=LCBleachMix)


############ Header file containing matching deck layout  #############
headerfile=os.path.join(os.path.dirname(__file__),"../header.gem")
