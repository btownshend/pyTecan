from . import logging
from .platelocation import PlateLocation
from .platetype import PlateType

class Plate(object):
    """An object representing a microplate or other container on the deck; includes a name, location, and size"""
    __allplates = []

    def __init__(self, name: str, plateType: PlateType, plateLocation: PlateLocation, liquidTemp=22.7,
                 backupPlate: 'Plate' = None):
        assert(isinstance(plateLocation,PlateLocation))
        assert(isinstance(plateType, PlateType))
        self.name=name
        self.plateType=plateType
        self.location=plateLocation
        self.wells=[i*plateType.ny+j for i in range(plateType.nx) for j in range(plateType.ny) ]		# List of wells, can be modified to skip particular wells
        self.liquidTemp=liquidTemp
        self.backupPlate=backupPlate	   # Backup plate to use when this one is full
        Plate.__allplates.append(self)

    def getzmax(self):
        if self.plateType.zmax is None or self.location.zoffset is None:
            return None
        zmax = 2100-(self.plateType.zmax + self.location.zoffset)*10-390
        # Check old way
        if zmax!=self.location.oldzmax:
            print(f"**** New zmax is {zmax}, but old way is {self.location.oldzmax}")
        return zmax

    def markUsed(self,firstWell,lastWell=None):
        first=self.wellnumber(firstWell)
        if lastWell is None:
            last=first
        else:
            last=self.wellnumber(lastWell)
        self.wells=[w for w in self.wells if w<first or w>last]
        logging.warning("Marking wells %s:%s on plate %s as unavailable: now have %d wells"%(firstWell,self.wellname(last),self.name,len(self.wells)))


    @classmethod
    def allPlates(cls):
        return Plate.__allplates

    @classmethod
    def lookup(cls,grid,pos):
        for p in Plate.__allplates:
            if p.location is not None and (p.location.grid==grid and p.location.pos==pos):
                return p
        return None

    @classmethod
    def lookupByName(cls,name):
        for p in Plate.__allplates:
            if p.name==name:
                return p
        return None

    @classmethod
    def reset(cls):
        pass

    def unusableVolume(self):
        return self.plateType.unusableVolume

    def movetoloc(self,newloc: PlateLocation):
        assert(isinstance(newloc,PlateLocation))
        self.location=newloc
        # FIXME: handle lower unusable volume for magplate

    def getliquidheight(self,volume:float):
        """Get liquid height in mm above ZMax"""
        return self.plateType.getliquidheight(volume)

    def getliquidarea(self,volume:float):
        """Get surface area of liquid in mm^2 when filled to given volume"""
        return self.plateType.getliquidarea(volume)

    def getevaprate(self,volume:float,vel:float=0):
        """Get rate of evaporation of well in ul/min with given volume at specified self.dewpoint"""
        return self.plateType.getevaprate(volume,self.liquidTemp,vel)

    def getliquidvolume(self,height:float):
        """Compute liquid volume given height above zmax in mm"""
        return self.plateType.getliquidvolume(height)

    def getgemliquidvolume(self,height:float):
        """Compute liquid volume given height above zmax in mm the way Gemini will do it"""
        return self.plateType.getgemliquidvolume(height)

    def getgemliquidheight(self,volume:float):
        """Compute liquid height above zmax in mm given volume the way Gemini will do it"""
        return self.plateType.getgemliquidheight(volume)

    def wellname(self,well):
        return self.plateType.wellname(well)

    def wellnumber(self,wellname:str):
        """Convert a wellname, such as "A3" to a well index -- inverse of wellname()"""
        return self.plateType.wellnumber(wellname)

    def __str__(self):
        return self.name
        #return "%s(%s,%s)"%(self.name,self.grid,self.pos)

    @classmethod
    def lookupLocation(cls, dest:PlateLocation):
        return cls.lookup(dest.grid,dest.pos)

