class PlateLocation(object):
    """An object representing a location on the deck of a container"""
    __allplatelocations = []

    def __init__(self, name: str, grid: int, pos: int, slopex:float=0, slopey:float=0, vectorName:str = None, lihaAccess:bool = True,
                 carrierName=None,zoffset=0):
        self.name=name
        self.grid=grid
        self.pos=pos
        self.slopex=slopex  # Slope of plate in mm/well; +ve indicates right edge is higher than left edge
        self.slopey=slopey  # Slope of plate in mm/well; +ve indicates bottom edge is higher than top edge
        self.zoffset=zoffset   # Offset of underlying carrier at this pos, in mm from surface of deck
        self.vectorName=vectorName		# Name of vector used for RoMa to pickup plate
        self.lihaAccess=lihaAccess
        if carrierName is None:
            self.carrierName=self.name
        else:
            self.carrierName=carrierName
        PlateLocation.__allplatelocations.append(self)

    @classmethod
    def lookupByName(cls,name):
        for p in PlateType.__allplatetypes:
            if p.name==name:
                return p
        return None

    @classmethod
    def lookupByLocation(cls,grid,pos):
        for p in PlateLocation.__allplatelocations:
            if p.grid==grid and p.pos==pos:
                return p
        return None

    def __str__(self):
        #return "%s(%d,%d)"%(self.name,self.grid,self.pos)
        return self.name