from .carrier import Carrier


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
        self.carrier = Carrier.cfg().findcarrier(self.carrierName)
        if self.carrier is None:
            print(f"PlateLocation '{name}' references unknown carrier: '{self.carrierName}'")
            print(f"Known carriers: {','.join([c['name'] for c in Carrier.cfg().carriers])}")
        else:
            if self.zoffset != self.carrier['refoffset'][2]:
                print(f"carrier '{self.carrier['name']}' refoffset[z] is {self.carrier['refoffset'][2]}, but plateLocation '{self.name}' zoffset is {self.zoffset}")
            if self.lihaAccess == self.carrier['romaonly']:
                print(f"carrier '{self.carrier['name']}' romaonly is {self.carrier['romaonly']}, but plateLocation '{self.name}' lihaAccess is {self.lihaAccess}")
        PlateLocation.__allplatelocations.append(self)

    @classmethod
    def lookupByLocation(cls,grid,pos):
        for p in PlateLocation.__allplatelocations:
            if p.grid==grid and p.pos==pos:
                return p
        return None

    def __str__(self):
        #return "%s(%d,%d)"%(self.name,self.grid,self.pos)
        return self.name