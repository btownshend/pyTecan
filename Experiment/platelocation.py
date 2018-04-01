class PlateLocation(object):
    """An object representing a location on the deck of a container"""

    def __init__(self,grid, pos, slopex=0,slopey=0):
        self.grid=grid
        self.pos=pos
        self.slopex=slopex  # Slope of plate in mm/well; +ve indicates right edge is higher than left edge
        self.slopey=slopey  # Slope of plate in mm/well; +ve indicates bottom edge is higher than top edge

    def __str__(self):
        return "(%d,%d)"%(self.grid,self.pos)