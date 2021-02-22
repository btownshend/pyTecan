import os
from .platetype import PlateType
from .platelocation import PlateLocation

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
# ZMax shown in Gemini configuration is 2100-(PlateType.zmax+PlateLocation.zoffset+39)*10
TROUGH = PlateType("Trough 100ml",nx=1,ny=4,pierce=False,unusableVolume=100,maxVolume=100000,r1=19.923,h1=0,gemDepth=0,gemArea=1247,gemShape='flat',zmax=6.8)
EPPLOWBIND=PlateType("EppLoBind on carrier",nx=12,ny=8,pierce=False,unusableVolume=15,maxVolume=200,zmax=5.4,
                angle=17.5,r1=2.724,h1=8.49,v0=13.48,
                gemDepth=1.92, gemArea=13.51,
                gemShape='v-shaped',maxspeeds=eppmaxspeeds,minspeeds=eppminspeeds,glycerolmaxspeeds=eppglycerolmaxspeeds,glycerol=1)  # EppLoBind
RICBLOCK=PlateType("RIC Eppendorfs",nx=6,ny=5,pierce=False,unusableVolume=20,maxVolume=1700,angle=17.5,r1=4.102,h1=16.79,v0=15.11,gemDepth=0.25,gemArea=14.07,gemShape='v-shaped',
                   zmax=-0.6)
WHITEQPCR=PlateType("QPCR on HSP96xx",nx=12,ny=8,pierce=False,unusableVolume=15,maxVolume=200,zmax=8.9,
                angle=17.5,r1=2.704,h1=10.89,v0=0.44,gemDepth=3.17,gemArea=14.33,gemShape='v-shaped')
EPPRACK = PlateType("Eppendorf Tube, 16 Pos.", nx=1, ny=16, pierce=False, unusableVolume=30, maxVolume=1500,angle=17.5,zmax=37.1,
                r1=4.407,h1=17.34,v0=22.11,
                gemDepth=10.47, gemArea=57.02, gemShape='v-shaped')
CLEAR384=PlateType("384 Well, clear on carrier",nx=24,ny=16,yspacing=4.5,pierce=False,unusableVolume=15,maxVolume=130,zmax=5.1,
                gemArea=15.19, r1=1.971, h1=-1.14,angle=None,
                gemShape='flat',maxspeeds=eppmaxspeeds,minspeeds=eppminspeeds,glycerolmaxspeeds=eppglycerolmaxspeeds,glycerol=1)  # TODO
GRENIER384=PlateType("Grenier384",nx=24,ny=16,yspacing=4.5,pierce=False,unusableVolume=10,maxVolume=130,zmax=5.2,
                angle=17.5,r1=2.070,h1=2.31,v0=26.2, 
                gemDepth=0.1, gemArea=13.30,
                gemShape='v-shaped',maxspeeds=eppmaxspeeds,minspeeds=eppminspeeds,glycerolmaxspeeds=eppglycerolmaxspeeds,glycerol=1)  # TODO
CLEANER_SHALLOW=PlateType("Cleaner shallow, 8 Pos.",nx=1,ny=8,gemShape='flat',gemArea=50.3,zmax=75,r1=0)
CLEANER_DEEP=PlateType("Cleaner deep, 8 Pos.",nx=1,ny=8,gemShape='flat',gemArea=50.3,zmax=15,r1=0)
WASTE=PlateType("Waste",nx=1,ny=4,gemShape='flat',gemArea=50.3,zmax=52,r1=0)

############ Plate locations  #############
# Plate locations are roughly equivalent to Gemini carriers
# Note: We currently tie the zmax to the location, since the same plate can be moved to different locations resulting in different heights
#   However, this creates a problem if a different plate type is moved to the same location
#   TODO: Make locations more like racks (with a base height) and then plates have a zmax that is relative to that
# Or, maybe, we don't really need the zmax here -- the parselog can retrieve the zmax that was being used at runtime
# A particular volume formula goes along with a particular zmax though...
TROUGH2=PlateLocation("Trough-Middle",3,2,carrierName="Trough 100ml, 3 Pos.",zoffset=10.0)
TROUGH3=PlateLocation("Trough-Front",3,3,carrierName="Trough 100ml, 3 Pos.",zoffset=10.0)
TROUGH1=PlateLocation("Trough-Rear",3,1,carrierName="Trough 100ml, 3 Pos.",zoffset=10.0)

RICLOC=PlateLocation("RIC",18,1,slopex=0,slopey=0,carrierName="RIC, Dual",zoffset=6.2+108.7)
SHAKERPLATELOC=PlateLocation("Shaker",9,0,vectorName="Shaker",lihaAccess=False)
SAMPLELOC=PlateLocation("SampleLoc",4,3,vectorName="Microplate Landscape",carrierName="MP, 3 Pos., landscape, RoMa",
                        zoffset=62.5)
DILUTIONLOC=PlateLocation("DilutionLoc",4,2,vectorName="Microplate Landscape",carrierName="MP, 3 Pos., landscape, RoMa",
                          zoffset=62.5)
PRODUCTLOC=PlateLocation("ProductLoc",18,2,vectorName="Microplate Product",carrierName="RIC, Dual", zoffset=6.2+113.5)
MAGPLATELOC=PlateLocation("MagPlate Carrier",18,2,vectorName="Magplate",carrierName="RIC, Dual",zoffset=62.5)
QPCRLOC=PlateLocation("QPCRLoc",4,1,carrierName="MP, 3 Pos., landscape, RoMa",zoffset=62.5)  # defined in worklist.py
EPPLOC=PlateLocation("EppLoc",13,1,carrierName="Eppendorf Tube, 16 Pos.",zoffset=0.0)
TCPOS=PlateLocation("TC",25,1,vectorName="TROBOT",lihaAccess=False,carrierName="PTC200-Off Deck")
HOTELPOS = PlateLocation("Hotel",25, 1, lihaAccess=False,carrierName="Hotel")
CLEANER_DEEPLOC = PlateLocation("Cleaner deep",1, 3, lihaAccess=True,carrierName="Wash station")
WASTELOC = PlateLocation("Waste",1, 2, lihaAccess=True,carrierName="Wash station")
CLEANER_SHALLOWLOC = PlateLocation("Cleaner shallow",1, 1, lihaAccess=True,carrierName="Wash station")
HOTEL = [ PlateLocation("HotelStack",25,i+1, lihaAccess=False,vectorName=f"HotelStack",carrierName="HotelStack") for i in range(5) ]

############ Physical Plates #############
#TIPOFFSETS=[390, 389, 394, 387]
TIPOFFSETS=[390, 390, 390, 390]

############ Header file containing matching deck layout  #############
# TODO: Use carrier.py to roll a new header on the fly
headerfile=os.path.join(os.path.dirname(__file__),"../header.gem")
headerfile384samp=os.path.join(os.path.dirname(__file__),"../header384samp.gem")
