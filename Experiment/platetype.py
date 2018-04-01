import math
from . import globals
from . import logging


def interpolate(dictionary, x0):
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

    def __init__(self,name, nx=12, ny=8,pierce=False,unusableVolume=5,maxVolume=200,zmax=None,angle=None,r1=None,h1=None,v0=None,gemDepth=None,gemArea=None,gemShape=None,vectorName=None,maxspeeds=None,glycerolmaxspeeds=None,glycerol=None,minspeeds=None):
        self.name=name
        self.unusableVolume=unusableVolume   # FIXME: unusableVolume did depend on where the plate was (was that for the magnet?)
        self.nx=nx
        self.ny=ny
        self.pierce=pierce
        self.maxVolume=maxVolume
        self.warned=False
        self.zmax=zmax
        if angle is None:
            self.angle=None
        else:
            self.angle=angle*math.pi/180
        self.r1=r1
        self.h1=h1
        self.v0=v0
        self.gemDepth=gemDepth		  # Values programmed into Gemini so we can foretell what volumes Gemini will come up with for a given height
        self.gemArea=gemArea
        self.gemShape=gemShape
        self.vectorName=vectorName		# Name of vector used for RoMa to pickup plate
        self.maxspeeds=maxspeeds
        self.glycerolmaxspeeds=glycerolmaxspeeds
        self.glycerol=glycerol			# Glycerol fraction for above speeds
        self.minspeeds=minspeeds

    def markUsed(self,firstWell,lastWell=None):
        first=self.wellnumber(firstWell)
        if lastWell is None:
            last=first
        else:
            last=self.wellnumber(lastWell)
        self.wells=[w for w in self.wells if w<first or w>last]
        logging.warning("Marking wells %s:%s on plate %s as unavailable: now have %d wells"%(firstWell,self.wellname(last),self.name,len(self.wells)))


    def getliquidheight(self,volume):
        """Get liquid height in mm above ZMax"""
        if self.angle is None:
            if self.gemShape=='flat':
                return volume*1.0/self.gemArea
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

    def getliquidarea(self,volume):
        """Get surface area of liquid in mm^2 when filled to given volume"""
        if self.angle is None:
            if self.gemShape=='flat':
                return self.gemArea
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
    def mixingratio(dewpoint):
        B=0.6219907  # kg/kg
        Tn=240.7263
        m=7.591386
        A=6.116441
        Pw=A*10.0**(m*dewpoint/(Tn+dewpoint))
        Ptot=1013   # Atmospheric pressure
        mr=B*Pw/(Ptot-Pw)
        return mr

    def getevaprate(self,volume,liquidTemp, vel=0):
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

    def getliquidvolume(self,height):
        """Compute liquid volume given height above zmax in mm"""
        if self.angle is None:
            if self.gemShape=='flat':
                return self.gemArea*height
            return None

        h0=self.h1-self.r1/math.tan(self.angle/2)
        v1=math.pi/3*(self.h1-h0)*self.r1*self.r1-self.v0
        if height>self.h1:
            volume=(height-self.h1)*math.pi*self.r1*self.r1+v1
        else:
            volume=(height-h0)**3*math.pi/3*(self.r1/(self.h1-h0))**2-self.v0
        #print "h0=",h0,", v1=",v1,", h=",height,", vol=",volume,", h=",self.getliquidheight(volume)
        return volume

    def getgemliquidvolume(self,height):
        """Compute liquid volume given height above zmax in mm the way Gemini will do it"""
        if height is None:
            volume=None
        elif self.gemShape=='flat':
            volume=self.gemArea*height
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

    def getgemliquidheight(self,volume):
        """Compute liquid height above zmax in mm given volume the way Gemini will do it"""
        if volume is None:
            height=None
        elif self.gemShape=='flat':
            height=volume/self.gemArea
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

    def wellname(self,well):
        if well is None:
            return "None"
        col=well//self.ny
        row=well-col*self.ny
        return "%c%d"%(chr(65+row),col+1)

    def wellnumber(self,wellname):
        """Convert a wellname, such as "A3" to a well index -- inverse of wellname()"""
        for i in range(self.nx*self.ny):
            if self.wellname(i)==wellname:
                return i
        logging.error("Illegal well name, %s, for plate %s"%(wellname, self.name))

    def __str__(self):
        return self.name
        #return "%s(%s,%s)"%(self.name,self.grid,self.pos)

