import os
from plate import Plate
from sample import Sample
from liquidclass import LCBleachMix
from worklist import WASHLOC, QPCRLOC

############ Plates and plate locations  #############
#WASHLOC=Plate("Wash",1,2,1,8,False,0)   # Defined in worklist

# Use dimensional data from Robot/Calibration/20150302-LiquidHeights
#REAGENTPLATE=Plate("Reagents",18,1,6,5,False,unusableVolume=20,maxVolume=1700,zmax=569,angle=17.5,r1=4.062,h1=17.75,v0=13.7,slopex=-0.022,slopey=-0.038,gemDepth=24.45,gemArea=51.61,gemHOffset=-7.15,gemShape='v-shaped')  
#REAGENTPLATE=Plate("Reagents",18,1,6,5,False,unusableVolume=20,maxVolume=1700,zmax=569,angle=17.5,r1=4.062,h1=17.75,v0=13.7,slopex=-0.022,slopey=-0.038,gemDepth=13.83,gemArea=51.84,gemHOffset=0,gemShape='v-shaped')
REAGENTPLATE=Plate("Reagents",18,1,6,5,False,unusableVolume=20,maxVolume=1700,zmax=569,angle=17.5,r1=4.062,h1=17.75,v0=13.7,slopex=-0.022,slopey=-0.038,gemDepth=9.59,gemArea=43.03,gemHOffset=0,gemShape='v-shaped')  
MAGPLATELOC=Plate("MagPlate",18,2,12,8,False,unusableVolume=9,maxVolume=200,zmax=1459,angle=17.5,r1=2.80,h1=10.04,v0=10.8)   # HSP9601 on magnetic plate  (Use same well dimensions as SAMPLE)
hspmaxspeeds={200:1400,150:1600,100:1850,50:2000,20:2200}	# From shaketest experiment
grenmaxspeeds={150:1750,125:1900,100:1950,75:2200,50:2200}	# From shaketest experiment
eppmaxspeeds={195:1600,150:1800,125:1900,100:1950,75:2050,50:2150,25:2150,0:2150} # From shaketest experiment 5/17/16
#eppdilmaxspeeds={195:1400,150:1600,125:1700,100:1750,75:1850,50:1950,25:1950,0:1950} # Decrease by 200 RPM 7/7/16 to avoid spilling
#eppmaxspeeds={195:0,150:1150,138:1250,100:1350,75:1850,50:1950,25:1950,0:1950} # Decrease based on 9/23/16 testing with MTaq
eppglycerolmaxspeeds={195:0,150:1150,138:1250,100:1350,90:1450,80:1500,70:1550,60:1650,50:1750,40:1950,20:2000,0:2000} # Decrease based on 10/21/16 testing with MTaq (with Glycerol @ 0.5%)
eppminspeeds={20:1900,32:1800,64:1700,96:1400,150:1100}  # 1100@150ul untested

SAMPLEPLATE=Plate("Samples",4,3,12,8,False,unusableVolume=15,maxVolume=200,
                zmax=1033,angle=17.5,r1=2.698,h1=9.31,v0=17.21,slopex=0.000,slopey=0.000,
                gemDepth=2.81,gemArea=16.41,
                gemShape='v-shaped',vectorName="Microplate Landscape",maxspeeds=eppmaxspeeds,minspeeds=eppminspeeds,glycerolmaxspeeds=eppglycerolmaxspeeds,glycerol=0.005)  # EppLoBind
SAMPLEPLATE.wells=SAMPLEPLATE.wells[1:-1]	 # Skip A1 and H12 due to leakage
SHAKERPLATELOC=Plate("Shaker",9,0,1,1)
QPCRPLATE=Plate("qPCR",QPCRLOC.grid,QPCRLOC.pos,12,8,False,unusableVolume=15,maxVolume=200,
                zmax=996,angle=17.5,r1=2.704,h1=10.89,v0=0.44,slopex=0.000,slopey=0.000,gemDepth=3.17,gemArea=14.33,
                gemShape='v-shaped')
# If changing location of QPCRPLATE, also update QPCRLOC in worklist.py
DILPLATE=Plate("Dilutions",4,2,12,8,False,unusableVolume=15,maxVolume=200,
               zmax=1033,angle=17.5,r1=2.705,h1=9.13,v0=13.14,slopex=0.000,slopey=0.000,gemDepth=2.81,gemArea=16.41,
               gemShape='v-shaped',vectorName="Microplate Landscape",maxspeeds=eppmaxspeeds,minspeeds=eppminspeeds,glycerolmaxspeeds=eppglycerolmaxspeeds,glycerol=0.005) # EppLoBind

SSDDILLOC=Plate("SSDDil",3,1,1,4,False,100,100000,zmax=1367,gemDepth=0,gemArea=1232,gemShape='flat')
WATERLOC=Plate("Water",3,2,1,4,False,100,100000,zmax=1367,gemDepth=0,gemArea=1232,gemShape='flat')
BLEACHLOC=Plate("Bleach",3,3,1,4,False,0,100000,zmax=1367,gemDepth=0,gemArea=1232,gemShape='flat')
PTCPOS=Plate("PTC",25,1,1,1)
HOTELPOS=Plate("Hotel",25,0,1,1)
WASTE=Plate("Waste",20,3,1,1)
EPPENDORFS=Plate("Eppendorfs",13,1,1,16,False,unusableVolume=30,maxVolume=1500,zmax=1337,angle=17.5,h1=17.56,r1=4.42,v0=29.6,gemDepth=3.15,gemArea=31.4,gemShape='v-shaped')
TIPOFFSETS=[390, 390, 394, 386]
    
############ Well-known samples  #############
def initWellKnownSamples():
    global WATER, SSDDIL, BLEACH
    WATER=Sample("Water",WATERLOC,-1,None,50000)
    SSDDIL=Sample("SSDDil",SSDDILLOC,-1,None,50000)
    BLEACH=Sample("RNase-Away",BLEACHLOC,-1,None,50000,mixLC=LCBleachMix)

initWellKnownSamples()

############ Header file containing matching deck layout  #############
headerfile=os.path.join(os.path.dirname(__file__),"../header.gem")
