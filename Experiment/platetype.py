import math
from . import globals
from . import logging
from typing import Dict

from .carrier import Carrier

InterpDict = Dict[float, float]

def interpolate(dictionary: InterpDict, x0: float):
    """Interpolate a dictionary of x:y values at given x0 value using linear interpolation"""
    lowbound=None
    highbound=None
    for x,y in dictionary.items():
        if x<=x0 and (lowbound is None or lowbound[0]<x):
            lowbound=(x,y)
        if x>=x0 and (highbound is None or highbound[0]>x):
            highbound=(x,y)
    if lowbound is None or highbound is None:
        return None

    if highbound[0]==lowbound[0]:
        y0=(highbound[1]+lowbound[1])/2.0
    else:
        y0=(x0-lowbound[0])/(highbound[0]-lowbound[0])*(highbound[1]-lowbound[1]) + lowbound[1]
    #print "x0=",x0,", y0=",y0,", low=",lowbound,", high=",highbound
    #print "interp(",dict,",",x0,")=",y0
    return y0


class PlateType(object):
    """An object representing a type of microplate or other container ; includes a name, and physical parameters"""
    __allplatetypes = []

    def __init__(self,name: str, nx:int =12, ny:int=8,pierce:bool=False,unusableVolume:float=5,maxVolume:float=200,angle:float=None,r1:float=None,h1:float=0,v0:float=None,gemDepth:float=None,gemArea:float=None,gemShape:str=None,maxspeeds=None,glycerolmaxspeeds=None,glycerol:float=None,minspeeds=None,yspacing=9,zmax=None):
        self.name=name
        self.unusableVolume=unusableVolume   # FIXME: unusableVolume did depend on where the plate was (was that for the magnet?)
        self.nx=nx
        self.ny=ny
        self.yspacing=yspacing
        self.pierce=pierce
        self.maxVolume=maxVolume
        self.warned=False
        if (angle is None and v0 is not None) or (angle is not None and v0 is None) or r1 is None or h1 is None:
            print(f"Invalid volume settings for {self.name}: angle={angle}, v0={v0}, r1={r1}, h1={h1}")
        if angle is None:
            self.angle=None
        else:
            self.angle=angle*math.pi/180  # Convert to radians
        self.r1=r1
        self.h1=h1
        self.v0=v0
        if ((gemShape == 'v-shaped' or gemShape=='round') and (gemDepth is None or gemDepth<=0)) or (gemShape=='flat' and (gemDepth!=0 and gemDepth is not None) ):
            print(f"Invalid gem volume settings for {self.name}: shape={gemShape}, depth={gemDepth}")
        self.gemDepth=gemDepth if gemDepth is not None else 0.0		  # Values programmed into Gemini so we can foretell what volumes Gemini will come up with for a given height
        self.gemArea=gemArea
        self.gemShape=gemShape
        self.maxspeeds=maxspeeds
        self.glycerolmaxspeeds=glycerolmaxspeeds
        self.glycerol=glycerol			# Glycerol fraction for above speeds
        self.minspeeds=minspeeds
        self.zmax=zmax  # Position of bottom of well relative to bottom of plate in mm
        # zmax in robot is in tenths, adds the carrier offset, and is measured from 2100 above deck
        self.rack = Carrier.cfg().findrack(self.name)
        if self.rack is None:
            print(f"PlateType '{name}' references unknown rack: '{self.name}'")
            print(f"Known racks: {','.join([c['name'] for c in Carrier.cfg().racks])}")
        else:
            if self.gemArea != self.rack['area']:
                print(f"rack '{self.rack['name']}' area is {self.rack['area']}, but plateType '{self.name}' gemArea is {self.gemArea}")
            if self.gemDepth != self.rack['depth'] and (self.gemDepth is not None or self.rack['depth']!=0):
                print(f"rack '{self.rack['name']}' depth is {self.rack['depth']}, but plateType '{self.name}' gemDepth is {self.gemDepth}")
            if ((self.gemShape=='flat') != (self.rack['depth']==0) ) or ((self.gemShape=='v-shaped') != (self.rack['depth']>0)):
                # carries encode shape into depth:  0=flat, negative=round, positive=v-shaped
                print(f"rack '{self.rack['name']}' depth is {self.rack['depth']}, but plateType '{self.name}' gemShape is {self.gemShape}")
            if self.pierce != self.rack['piercing'][0]!=0:
                print(f"rack '{self.rack['name']}' pierce is {self.rack['piercing']}, but plateType '{self.name}' pierce is {self.pierce}")
            if self.nx != self.rack['wells'][0] or self.ny != self.rack['wells'][1]+self.rack['tipsperwell']-1:
                print(f"rack '{self.rack['name']}' wells is {self.rack['wells']}, tipsperwell={self.rack['tipsperwell']} but plateType '{self.name}' nx,ny is {self.nx},{self.ny}")
            if self.zmax != self.rack['zcoords']['max']:
                print(f"rack '{self.rack['name']}' zcoords.max is {self.rack['zcoords']['max']}, but plateType '{self.name}' zmnax is {self.zmax}")


        PlateType.__allplatetypes.append(self)

    @classmethod
    def lookupByName(cls,name):
        for p in PlateType.__allplatetypes:
            if p.name==name:
                return p
        return None

    def getliquidheight(self,volume):
        """Get liquid height in mm above ZMax"""
        if self.angle is None:
            if self.r1 is not None and self.h1 is not None:
                return volume*1.0/(math.pi*self.r1*self.r1) + self.h1   # h1 is the distance of the well bottom above the zmax point
            if not self.warned:
                logging.warning("No liquid height equation for plate %s"%self.name)
                self.warned=True
            return None

        h0=self.h1-self.r1/math.tan(self.angle/2)
        v1=math.pi/3*(self.h1-h0)*self.r1*self.r1-self.v0
        if volume>=v1:
            height=(volume-v1)/(math.pi*self.r1*self.r1)+self.h1
        elif volume+self.v0<0:
            height=h0
        else:
            height=((volume+self.v0)*(3/math.pi)*((self.h1-h0)/self.r1)**2)**(1.0/3)+h0
            #        print "%s,vol=%.1f, height=%.1f"%(self.name,volume,height)
        return height

    def getliquidarea(self,volume:float):
        """Get surface area of liquid in mm^2 when filled to given volume"""
        if self.angle is None:
            if self.r1 is not None:
                return math.pi*self.r1*self.r1
            if not self.warned:
                logging.warning("No liquid height equation for plate %s"%self.name)
                self.warned=True
            return None

        h0=self.h1-self.r1/math.tan(self.angle/2)
        v1=math.pi/3*(self.h1-h0)*self.r1*self.r1-self.v0
        if volume>=v1:
            radius=self.r1
        elif volume+self.v0<0:
            radius=0
        else:
            height=((volume+self.v0)*(3/math.pi)*((self.h1-h0)/self.r1)**2)**(1.0/3)+h0
            radius=(height-h0)/(self.h1-h0)*self.r1
        area=math.pi*radius*radius
        #print "%s,vol=%.1f, radius=%.1f, area=%.1f"%(self.name,volume,radius,area)
        return area

    @staticmethod
    def mixingratio(dewpoint:float):
        B=0.6219907  # kg/kg
        Tn=240.7263
        m=7.591386
        A=6.116441
        Pw=A*10.0**(m*dewpoint/(Tn+dewpoint))
        Ptot=1013   # Atmospheric pressure
        mr=B*Pw/(Ptot-Pw)
        return mr

    def getevaprate(self,volume:float,liquidTemp:float, vel:float=0):
        """Get rate of evaporation of well in ul/min with given volume at specified liquidTemp and global dewpoint"""
        assert volume>=0
        EVAPFUDGE=0.69		# Fudge factor -- makes computed evaporation match up with observed
        area=self.getliquidarea(volume)
        x=self.mixingratio(globals.dewpoint)
        xs=self.mixingratio(liquidTemp)
        #print "vol=",volume,", area=",area
        if area is None:
            return 0
        theta=25+19*vel
        evaprate=theta*area/1000.0/1000*(xs-x)*1e6
        #print "Plate=%s,Air temp=%.1fC, DP=%.1fC, x=%.3f, xs=%.3f, vol=%.1f ul, area=%.0f mm^2, evaprate=%.3f ul/h"%(self.name,self.liquidTemp,globals.dewpoint,x,xs,volume,area,evaprate)
        return evaprate*EVAPFUDGE

    def getliquidvolume(self,height:float):
        """Compute liquid volume given height above zmax in mm"""
        if self.angle is None:
            if self.r1 is not None and self.h1 is not None:
                return (math.pi*self.r1*self.r1)*(height-self.h1)   # h1 is the distance of the well bottom above the zmax point
            return None

        h0=self.h1-self.r1/math.tan(self.angle/2)
        v1=math.pi/3*(self.h1-h0)*self.r1*self.r1-self.v0
        if height>self.h1:
            volume=(height-self.h1)*math.pi*self.r1*self.r1+v1
        else:
            volume=(height-h0)**3*math.pi/3*(self.r1/(self.h1-h0))**2-self.v0
        #print "h0=",h0,", v1=",v1,", h=",height,", vol=",volume,", h=",self.getliquidheight(volume)
        return volume

    def getgemliquidvolume(self,height:float):
        """Compute liquid volume given height above zmax in mm the way Gemini will do it"""
        if height is None:
            volume=None
        elif self.gemShape=='flat':
            volume=self.gemArea*height  # Gemini has no offset -- assumes that zmax is bottom of well
        elif self.gemShape=='v-shaped':
            r0=math.sqrt(self.gemArea/math.pi)
            if height<self.gemDepth:
                'conical'
                r=height/self.gemDepth*r0
                volume=1.0/3*math.pi*r*r*height
            else:
                volume=1.0/3*math.pi*r0*r0*self.gemDepth+self.gemArea*(height-self.gemDepth)
        else:
            volume=None
        return volume

    def getgemliquidheight(self,volume:float):
        """Compute liquid height above zmax in mm given volume the way Gemini will do it"""
        if volume is None:
            height=None
        elif self.gemShape=='flat':
            height=volume/self.gemArea   # Gemini has no offset -- assumes that zmax is bottom of well
        elif self.gemShape=='v-shaped':
            r0=math.sqrt(self.gemArea/math.pi)
            conevolume=1.0/3*math.pi*r0*r0*self.gemDepth
            if volume<conevolume:
                'conical'
                height=math.pow(volume*3/math.pi*(self.gemDepth/r0)**2,1.0/3)
            else:
                height=(volume-conevolume)/self.gemArea+self.gemDepth
        else:
            height=None
        return height

    def wellname(self,well:int):
        if well is None:
            return "None"
        col=well//self.ny
        row=well-col*self.ny
        return "%c%d"%(chr(65+row),col+1)

    def wellnumber(self,wellname:str):
        """Convert a wellname, such as "A3" to a well index -- inverse of wellname()"""
        if wellname[1]=='0':
            wellname=wellname[0]+wellname[2:]
        for i in range(self.nx*self.ny):
            if self.wellname(i)==wellname:
                return i
        logging.error("Illegal well name, %s, for plate %s"%(wellname, self.name))

    def __str__(self):
        return self.name
        #return "%s(%s,%s)"%(self.name,self.grid,self.pos)

