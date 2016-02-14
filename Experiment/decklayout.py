import os
from plate import Plate
from sample import Sample

############ Plates and plate locations  #############
WASHLOC=Plate("Wash",1,2,1,8,False,0)
# Use dimensional data from Robot/Calibration/20150302-LiquidHeights
REAGENTPLATE=Plate("Reagents",18,1,6,5,False,unusableVolume=20,maxVolume=1700,zmax=569,angle=17.5,r1=4.05,h1=17.71,v0=12.9)
MAGPLATELOC=Plate("MagPlate",18,2,12,8,False,unusableVolume=9,maxVolume=200,zmax=1459,angle=17.5,r1=2.80,h1=10.04,v0=10.8)   # HSP9601 on magnetic plate  (Use same well dimesnsions as SAMPLE)
hspmaxspeeds={200:1400,150:1600,100:1850,50:2000,20:2200};	# From shaketest experiment
grenmaxspeeds={150:1750,125:1900,100:1950,75:2200,50:2200};	# From shaketest experiment

#  SAMPLEPLATE=Plate("Samples",4,3,12,8,False,unusableVolume=15,maxVolume=200,zmax=1028,angle=17.5,r1=2.80,h1=10.04,v0=10.8,vectorName="Microplate Landscape",maxspeeds=hspmaxspeeds);  # HSP96xx
SAMPLEPLATE=Plate("Samples",4,3,12,8,False,unusableVolume=15,maxVolume=200,zmax=1028,angle=17.5,r1=2.69,h1=8.94,v0=13.2,vectorName="Microplate Landscape",maxspeeds=hspmaxspeeds);  # EppLoBind
SAMPLEPLATE.wells=SAMPLEPLATE.wells[1:-1]	 # Skip A1 and H12 due to leakage
SHAKERPLATELOC=Plate("Shaker",9,0,1,1)
#    READERPLATE=Plate("Reader",4,1,12,8,False,15)
QPCRPLATE=Plate("qPCR",4,1,12,8,False,unusableVolume=15,maxVolume=200,zmax=984,angle=17.5,r1=2.66,h1=9.37,v0=7.9)
#    DILPLATE=Plate("Dilutions",4,2,12,8,False,unusableVolume=15,maxVolume=200,zmax=1028,angle=17.5,r1=2.84,h1=9.76,v0=11.9,vectorName="Microplate Landscape",maxspeeds=hspmaxspeeds) # HSP96xx
DILPLATE=Plate("Dilutions",4,2,12,8,False,unusableVolume=15,maxVolume=200,zmax=1028,angle=17.5,r1=2.69,h1=7.70,v0=17.9,vectorName="Microplate Landscape",maxspeeds=hspmaxspeeds) # EppLoBind
#    DILPLATE=Plate("Dilutions-LB",4,2,12,8,False,unusableVolume=15,maxVolume=200,zmax=1028,angle=100,r1=2.92,h1=0.81,v0=6.8,vectorName="Grenier Landscape",maxspeeds=grenmaxspeeds) # Grenier 651901 Lobind plate
SSDDILLOC=Plate("SSDDil",3,1,1,4,False,100,100000)
WATERLOC=Plate("Water",3,2,1,4,False,100,100000)
BLEACHLOC=Plate("Bleach",3,3,1,4,False,0,100000)
PTCPOS=Plate("PTC",25,1,1,1)
HOTELPOS=Plate("Hotel",25,0,1,1)
WASTE=Plate("Waste",20,3,1,1)
EPPENDORFS=Plate("Eppendorfs",13,1,1,16,False,unusableVolume=30,maxVolume=1500,zmax=1337,angle=17.5,h1=17.56,r1=4.42,v0=29.6)

############ Well-known samples  #############
WATER=Sample("Water",WATERLOC,-1,None,50000)
SSDDIL=Sample("SSDDil",SSDDILLOC,-1,None,50000)
BLEACH=Sample("RNase-Away",BLEACHLOC,-1,None,50000)

############ Header file containing matching deck layout  #############
headerfile=os.path.expanduser("~/Dropbox/Synbio/Robot/pyTecan/header.gem")
