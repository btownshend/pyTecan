import math
from . import globals
from . import logging

class Plate(object):
    """An object representing a microplate or other container on the deck; includes a name, location, and size"""
    __allplates = []

    def __init__(self,name, ptype, ploc, liquidTemp=22.7,backupPlate=None):
        self.name=name
        self.plateType=ptype
        self.homePos=ploc
        self.pos=ploc
        self.wells=[i*ny+j for i in range(nx) for j in range(ny) ]		# List of wells, can be modified to skip particular wells
        self.curloc="Home"
        self.liquidTemp=liquidTemp
        self.backupPlate=backupPlate	   # Backup plate to use when this one is full
        Plate.__allplates.append(self)

    def markUsed(self,firstWell,lastWell=None):
        first=self.wellnumber(firstWell)
        if lastWell is None:
            last=first
        else:
            last=self.wellnumber(lastWell)
        self.wells=[w for w in self.wells if w<first or w>last]
        logging.warning("Marking wells %s:%s on plate %s as unavailable: now have %d wells"%(firstWell,self.wellname(last),self.name,len(self.wells)))


    @classmethod
    def lookup(cls,grid,pos):
        for p in Plate.__allplates:
            if p.grid==grid and p.pos==pos:
                return p
        return None

    @classmethod
    def reset(cls):
        for p in Plate.__allplates:
            p.movetoloc("Home")

    def movetoloc(self,dest,newloc=None):
        self.curloc=dest
        if  dest=="Home":
            self.grid=self.homegrid
            self.pos=self.homepos
            self.unusableVolume=self.homeUnusableVolume
        else:
            assert newloc is not None
            self.grid=newloc.grid
            self.pos=newloc.pos
            self.unusableVolume=newloc.unusableVolume

    def getliquidheight(self,volume):
        """Get liquid height in mm above ZMax"""
        return self.plateType.getliquidheight(volume)

    def getliquidarea(self,volume):
        """Get surface area of liquid in mm^2 when filled to given volume"""
        return self.plateType.getliquidarea(volume)

    def getevaprate(self,volume,vel=0):
        """Get rate of evaporation of well in ul/min with given volume at specified self.dewpoint"""
        return self.plateType.getevaprate(volume,self.liquidTemp,vel)

    def getliquidvolume(self,height):
        """Compute liquid volume given height above zmax in mm"""
        return self.plateType.getliquidvolume(height)

    def getgemliquidvolume(self,height):
        """Compute liquid volume given height above zmax in mm the way Gemini will do it"""
        return self.plateType.getgemliquidvolume(height)

    def getgemliquidheight(self,volume):
        """Compute liquid height above zmax in mm given volume the way Gemini will do it"""
        return self.plateType.getgemliquidheight(volume)

    def wellname(self,well):
        return self.plateType.wellname(well)

    def wellnumber(self,wellname):
        """Convert a wellname, such as "A3" to a well index -- inverse of wellname()"""
        return self.plateType.wellnumber(wellname)

    def __str__(self):
        return self.name
        #return "%s(%s,%s)"%(self.name,self.grid,self.pos)

