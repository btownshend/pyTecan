class PlateLocation(object):
    """An object representing a location on the deck of a container"""

    def __init__(self, name: str, grid: int, pos: int, slopex:float=0, slopey:float=0, zmax:float=None, vectorName:str = None, lihaAccess:bool = True):
        self.name=name
        self.grid=grid
        self.pos=pos
        self.slopex=slopex  # Slope of plate in mm/well; +ve indicates right edge is higher than left edge
        self.slopey=slopey  # Slope of plate in mm/well; +ve indicates bottom edge is higher than top edge
        self.zmax=zmax
        self.vectorName=vectorName		# Name of vector used for RoMa to pickup plate
        self.lihaAccess=lihaAccess

    def __str__(self):
        #return "%s(%d,%d)"%(self.name,self.grid,self.pos)
        return self.name