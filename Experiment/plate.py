import math
import globals

_Plate__allplates=[]

"An object representing a microplate or other container on the deck"
class Plate(object):
    "A plate object which includes a name, location, and size"
    def __init__(self,name, grid, pos, nx=12, ny=8,pierce=False,unusableVolume=5,maxVolume=200,zmax=None,angle=None,r1=None,h1=None,v0=None,vectorName=None,maxspeeds=None,liquidTemp=22.7):
        self.name=name
        self.grid=grid
        self.pos=pos
        self.unusableVolume=unusableVolume
        self.homegrid=grid
        self.homepos=pos
        self.homeUnusableVolume=unusableVolume
        self.nx=nx
        self.ny=ny
        self.wells=[i*ny+j for i in range(nx) for j in range(ny) ]		# List of wells, can be modified to skip particular wells
        self.pierce=pierce
        self.maxVolume=maxVolume
        self.warned=False
        self.curloc="Home"
        self.zmax=zmax
        if angle is None:
            self.angle=None
        else:
            self.angle=angle*math.pi/180
        self.r1=r1
        self.h1=h1
        self.v0=v0
        self.vectorName=vectorName		# Name of vector used for RoMa to pickup plate
        self.maxspeeds=maxspeeds
        self.liquidTemp=liquidTemp
        global __allplates
        __allplates.append(self)

    @classmethod
    def lookup(cls,grid,pos):
        global __allplates
        for p in __allplates:
            if p.grid==grid and p.pos==pos:
                return p
        return None

    def movetoloc(self,dest,newloc=None):
        self.curloc=dest
        if  dest=="Home":
            self.grid=self.homegrid
            self.pos=self.homepos
            self.unusableVolume=self.homeUnusableVolume
        else:
            assert newloc!=None
            self.grid=newloc.grid
            self.pos=newloc.pos
            self.unusableVolume=newloc.unusableVolume

    def getliquidheight(self,volume):
        'Get liquid height in mm above ZMax'
        if self.angle is None:
            if not self.warned:
                print "No liquid height equation for plate %s"%self.name
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
        'Get surface area of liquid in mm^2 when filled to given volume'
        if self.angle is None:
            if not self.warned:
                print "No liquid height equation for plate %s"%self.name
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

    def mixingratio(self,dewpoint):
        B=0.6219907  # kg/kg
        Tn=240.7263
        m=7.591386
        A=6.116441
        Pw=A*10.0**(m*dewpoint/(Tn+dewpoint))
        Ptot=1013   # Atmospheric pressure
        mr=B*Pw/(Ptot-Pw)
        return mr

    def getevaprate(self,volume,vel=0):
        'Get rate of evaporation of well in ul/min with given volume at specified self.dewpoint'
        assert volume>=0
        EVAPFUDGE=0.69		# Fudge factor -- makes computed evaporation match up with observed
        area=self.getliquidarea(volume)
        x=self.mixingratio(globals.dewpoint)
        xs=self.mixingratio(self.liquidTemp)
        #print "vol=",volume,", area=",area
        if area==None:
            return 0
        theta=25+19*vel
        evaprate=theta*area/1000/1000*(xs-x)*1e6
        #print "Air temp=%.1fC, DP=%.1fC, x=%.3f, xs=%.3f, vol=%.1f ul, area=%.0f mm^2, evaprate=%.3f ul/h"%(self.liquidTemp,self.dewpoint,x,xs,volume,area,evaprate)
        return evaprate*EVAPFUDGE
    
    def getliquidvolume(self,height):
        'Compute liquid volume given height above zmax in mm'
        if self.angle is None:
            return None

        h0=self.h1-self.r1/math.tan(self.angle/2)
        v1=math.pi/3*(self.h1-h0)*self.r1*self.r1-self.v0
        if height>self.h1:
            volume=(height-self.h1)*math.pi*self.r1*self.r1+v1
        else:
            volume=(height-h0)**3*math.pi/3*(self.r1/(self.h1-h0))**2-self.v0
        #print "h0=",h0,", v1=",v1,", h=",height,", vol=",volume,", h=",self.getliquidheight(volume)
        return volume

    def getmixspeeds(self,minvol,maxvol):
        'Get shaker speed range for given well volume'
        maxspeed=0
        if self.maxspeeds is not None:
            # Use the highest speed for which this volume or more is known to not spill
            for vol,speed in self.maxspeeds.iteritems():
                # print "maxvol=%f,vol=%f,speed=%f,maxspeed=%f"%(maxvol,vol,speed,maxspeed)
                if maxvol<=vol and speed>maxspeed:
                    maxspeed=speed
        if maxspeed==0:
            print "ERROR: No shaker speed data for volume of %.0f ul"%maxvol
            assert False

        # Theoretical minimum mixing speed
        # From: http://www.qinstruments.com/en/applications/optimization-of-mixing-parameters.html
        surftension=71.97  	# Surface tension mN/m (for water, most other substances are lower, so this is conservative)
        welldiam=self.r1*2	# mm - use widest part for conservative estimate (smaller region will mix at lower RPM)
        density=1e-3		    # g/ul (for water)
        d0=2			 				# mixing diameter (mm) (for BioShake 3000)
        minspeed=60*math.sqrt(surftension*welldiam/(4*math.pi*minvol*density*d0))
        # Units will be sqrt(mN/m * mm / ul*(mg/ul)*mm) = sqrt(mN/(m*mg)) = s^-1 * 60 = min^-1
        #print "mix(%.0f,%.0f) = [%.0f, %.0f]"%(minvol,maxvol,minspeed,maxspeed)
        return (minspeed,maxspeed)

    def wellname(self,well):
        if well is None:
            return "None"
        col=int(well/self.ny)
        row=well-col*self.ny
        return "%c%d"%(chr(65+row),col+1)

    def wellnumber(self,wellname):
        'Convert a wellname, such as "A3" to a well index -- inverse of wellname()'
        for i in range(self.nx*self.ny):
            if self.wellname(i)==wellname:
                return i
        print "Illegal well name, %s, for plate %s"%(wellname, self.name)
        assert False

    def __str__(self):
        return self.name
        #return "%s(%s,%s)"%(self.name,self.grid,self.pos)

