import os
from plate import Plate
from sample import Sample
from liquidclass import LCBleachMix

############ Plates and plate locations  #############
WASHLOC=Plate("Wash",1,2,1,8,False,0)
# Use dimensional data from Robot/Calibration/20150302-LiquidHeights
REAGENTPLATE=Plate("Reagents",18,1,6,5,False,unusableVolume=20,maxVolume=1700,zmax=569,angle=17.5,r1=4.062,h1=17.75,v0=13.7,slopex=-0.022,slopey=-0.038,gemDepth=5.17,gemArea=29.25,gemShape='v-shaped')
MAGPLATELOC=Plate("MagPlate",18,2,12,8,False,unusableVolume=9,maxVolume=200,zmax=1459,angle=17.5,r1=2.80,h1=10.04,v0=10.8)   # HSP9601 on magnetic plate  (Use same well dimensions as SAMPLE)
hspmaxspeeds={200:1400,150:1600,100:1850,50:2000,20:2200}	# From shaketest experiment
grenmaxspeeds={150:1750,125:1900,100:1950,75:2200,50:2200}	# From shaketest experiment
eppmaxspeeds={195:1600,150:1900,125:2000,100:2050,75:2150,50:2150,25:2400,0:2400} # From shaketest experiment 3/27/16
eppminspeeds={32:1800,64:1700,96:1400,200:1300}

SAMPLEPLATE=Plate("Samples",4,3,12,8,False,unusableVolume=15,maxVolume=200,zmax=1028,angle=17.5,r1=2.69,h1=8.94,v0=13.2,gemDepth=2.00,gemArea=16.57,gemShape='v-shaped',vectorName="Microplate Landscape",maxspeeds=eppmaxspeeds,minspeeds=eppminspeeds)  # EppLoBind
SAMPLEPLATE.wells=SAMPLEPLATE.wells[1:-1]	 # Skip A1 and H12 due to leakage
SHAKERPLATELOC=Plate("Shaker",9,0,1,1)
QPCRPLATE=Plate("qPCR",4,1,12,8,False,unusableVolume=15,maxVolume=200,zmax=984,angle=17.5,r1=2.66,h1=9.37,v0=7.9,gemDepth=2.29,gemArea=15.19,gemShape='v-shaped')
DILPLATE=Plate("Dilutions",4,2,12,8,False,unusableVolume=15,maxVolume=200,zmax=1028,angle=17.5,r1=2.715,h1=8.81,v0=13.5,slopex=-0.003,slopey=0.044,gemDepth=1.22,gemArea=16.17,gemShape='v-shaped',vectorName="Microplate Landscape",maxspeeds=eppmaxspeeds,minspeeds=eppminspeeds) # EppLoBind

SSDDILLOC=Plate("SSDDil",3,1,1,4,False,100,100000,gemDepth=0,gemArea=1232,gemShape='flat')
WATERLOC=Plate("Water",3,2,1,4,False,100,100000,gemDepth=0,gemArea=1232,gemShape='flat')
BLEACHLOC=Plate("Bleach",3,3,1,4,False,0,100000,gemDepth=0,gemArea=1232,gemShape='flat')
PTCPOS=Plate("PTC",25,1,1,1)
HOTELPOS=Plate("Hotel",25,0,1,1)
WASTE=Plate("Waste",20,3,1,1)
EPPENDORFS=Plate("Eppendorfs",13,1,1,16,False,unusableVolume=30,maxVolume=1500,zmax=1337,angle=17.5,h1=17.56,r1=4.42,v0=29.6,gemDepth=3.15,gemArea=31.4,gemShape='v-shaped')

############ Well-known samples  #############
def initWellKnownSamples():
    global WATER, SSDDIL, BLEACH
    WATER=Sample("Water",WATERLOC,-1,None,50000)
    SSDDIL=Sample("SSDDil",SSDDILLOC,-1,None,50000)
    BLEACH=Sample("RNase-Away",BLEACHLOC,-1,None,50000,mixLC=LCBleachMix)

initWellKnownSamples()

############ Header file containing matching deck layout  #############
headerfile=os.path.join(os.path.dirname(__file__),"../header.gem")
